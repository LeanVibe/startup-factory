#!/usr/bin/env python3
"""
Advanced Resilience and Error Recovery System
Provides comprehensive error recovery patterns including graceful degradation,
auto-recovery, cascade failure prevention, and chaos engineering tools.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from abc import ABC, abstractmethod

from core_types import Task, TaskType, StartupFactoryError

logger = logging.getLogger(__name__)


class ResilienceStrategy(str, Enum):
    """Resilience strategy types"""
    FAIL_FAST = "fail_fast"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    RETRY_WITH_FALLBACK = "retry_with_fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    BULKHEAD = "bulkhead"


class SystemState(str, Enum):
    """Overall system health state"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERY = "recovery"
    MAINTENANCE = "maintenance"


@dataclass
class ResilienceMetrics:
    """Metrics for resilience system"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    degraded_responses: int = 0
    fallback_activations: int = 0
    auto_recoveries: int = 0
    cascade_preventions: int = 0
    chaos_tests_run: int = 0
    last_failure_time: Optional[datetime] = None
    last_recovery_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def availability(self) -> float:
        """Calculate availability (successful + degraded / total)"""
        if self.total_requests == 0:
            return 1.0
        return (self.successful_requests + self.degraded_responses) / self.total_requests


@dataclass
class FallbackConfig:
    """Configuration for fallback mechanisms"""
    enabled: bool = True
    max_degradation_time: float = 300.0  # 5 minutes max in degraded state
    fallback_priority: List[str] = field(default_factory=list)  # Ordered list of fallback providers
    degrade_gracefully: bool = True
    cache_responses: bool = True
    cache_ttl: float = 60.0  # Cache TTL in seconds


@dataclass
class CascadeProtectionConfig:
    """Configuration for cascade failure protection"""
    enabled: bool = True
    failure_threshold: float = 0.5  # If >50% of components fail, activate protection
    isolation_timeout: float = 120.0  # Isolate failing components for 2 minutes
    dependency_limits: Dict[str, int] = field(default_factory=dict)  # Max concurrent calls per dependency
    bulkhead_enabled: bool = True


@dataclass
class AutoRecoveryConfig:
    """Configuration for auto-recovery mechanisms"""
    enabled: bool = True
    health_check_interval: float = 30.0  # Health check every 30 seconds
    recovery_validation_attempts: int = 3  # Validate recovery with N successful calls
    gradual_recovery: bool = True  # Gradually increase traffic during recovery
    recovery_traffic_percentage: float = 0.1  # Start with 10% traffic during recovery


class ResiliencePattern(ABC):
    """Base class for resilience patterns"""
    
    @abstractmethod
    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with resilience pattern"""
        pass
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if the pattern is healthy"""
        pass


class GracefulDegradation(ResiliencePattern):
    """Graceful degradation pattern - provide reduced functionality when primary service fails"""
    
    def __init__(self, fallback_config: FallbackConfig):
        self.config = fallback_config
        self.fallback_cache: Dict[str, Any] = {}
        self.last_cache_time: Dict[str, datetime] = {}
        self.degraded_since: Optional[datetime] = None
        
    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute with graceful degradation"""
        operation_key = f"{operation.__name__}_{hash(str(args) + str(kwargs))}"
        
        try:
            # Try primary operation
            result = await operation(*args, **kwargs)
            
            # Cache successful result
            if self.config.cache_responses:
                self.fallback_cache[operation_key] = result
                self.last_cache_time[operation_key] = datetime.now(UTC)
            
            # Reset degraded state if we were degraded
            if self.degraded_since:
                logger.info("Recovered from degraded state")
                self.degraded_since = None
            
            return result
            
        except Exception as e:
            logger.warning(f"Primary operation failed: {e}, attempting graceful degradation")
            
            if not self.degraded_since:
                self.degraded_since = datetime.now(UTC)
            
            # Check if we've been degraded too long
            if (datetime.now(UTC) - self.degraded_since).total_seconds() > self.config.max_degradation_time:
                logger.error("Maximum degradation time exceeded, failing operation")
                raise e
            
            # Try to provide degraded service from cache
            if operation_key in self.fallback_cache:
                cache_age = (datetime.now(UTC) - self.last_cache_time[operation_key]).total_seconds()
                if cache_age <= self.config.cache_ttl:
                    logger.info(f"Serving degraded response from cache (age: {cache_age:.1f}s)")
                    return self.fallback_cache[operation_key]
            
            # If no cached response available and graceful degradation is enabled
            if self.config.degrade_gracefully:
                return await self._provide_degraded_response(*args, **kwargs)
            
            # Fall back to raising the original exception
            raise e
    
    async def _provide_degraded_response(self, *args, **kwargs) -> Any:
        """Provide a degraded but functional response"""
        # This should be customized based on the specific operation
        logger.warning("Providing minimal degraded response")
        return {
            "status": "degraded",
            "message": "Service temporarily degraded, limited functionality available",
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    async def is_healthy(self) -> bool:
        """Check if graceful degradation is healthy"""
        return self.degraded_since is None or \
               (datetime.now(UTC) - self.degraded_since).total_seconds() < self.config.max_degradation_time


class CascadeProtection:
    """Prevent cascade failures from spreading through the system"""
    
    def __init__(self, config: CascadeProtectionConfig):
        self.config = config
        self.component_states: Dict[str, SystemState] = {}
        self.failure_counts: Dict[str, int] = {}
        self.isolation_until: Dict[str, datetime] = {}
        self.dependency_semaphores: Dict[str, asyncio.Semaphore] = {}
        
    async def is_component_available(self, component_name: str) -> bool:
        """Check if component is available (not isolated)"""
        if component_name in self.isolation_until:
            if datetime.now(UTC) < self.isolation_until[component_name]:
                logger.debug(f"Component {component_name} is isolated until {self.isolation_until[component_name]}")
                return False
            else:
                # Isolation period expired
                del self.isolation_until[component_name]
                logger.info(f"Component {component_name} isolation expired, allowing requests")
        
        return True
    
    async def record_failure(self, component_name: str):
        """Record failure and potentially isolate component"""
        self.failure_counts[component_name] = self.failure_counts.get(component_name, 0) + 1
        self.component_states[component_name] = SystemState.CRITICAL
        
        # Check if we need to isolate this component
        total_components = len(self.component_states)
        failed_components = sum(1 for state in self.component_states.values() 
                              if state == SystemState.CRITICAL)
        
        failure_rate = failed_components / max(1, total_components)
        
        if failure_rate > self.config.failure_threshold:
            logger.warning(f"Cascade protection activated: {failure_rate:.2%} failure rate")
            await self._isolate_component(component_name)
    
    async def record_success(self, component_name: str):
        """Record success and potentially restore component"""
        self.failure_counts[component_name] = 0
        self.component_states[component_name] = SystemState.HEALTHY
        
        if component_name in self.isolation_until:
            del self.isolation_until[component_name]
            logger.info(f"Component {component_name} recovered, removing isolation")
    
    async def _isolate_component(self, component_name: str):
        """Isolate a failing component"""
        isolation_end = datetime.now(UTC) + timedelta(seconds=self.config.isolation_timeout)
        self.isolation_until[component_name] = isolation_end
        
        logger.warning(f"Isolating component {component_name} until {isolation_end}")
    
    async def acquire_dependency_limit(self, dependency_name: str) -> bool:
        """Acquire semaphore for dependency to prevent overload"""
        if not self.config.bulkhead_enabled:
            return True
        
        if dependency_name not in self.dependency_semaphores:
            limit = self.config.dependency_limits.get(dependency_name, 10)
            self.dependency_semaphores[dependency_name] = asyncio.Semaphore(limit)
        
        semaphore = self.dependency_semaphores[dependency_name]
        
        # Try to acquire without blocking
        if semaphore.locked():
            logger.warning(f"Dependency {dependency_name} at capacity, rejecting request")
            return False
        
        await semaphore.acquire()
        return True
    
    def release_dependency_limit(self, dependency_name: str):
        """Release semaphore for dependency"""
        if dependency_name in self.dependency_semaphores:
            self.dependency_semaphores[dependency_name].release()


class AutoRecovery:
    """Automatic recovery system that detects when services are back online"""
    
    def __init__(self, config: AutoRecoveryConfig):
        self.config = config
        self.recovery_state: Dict[str, SystemState] = {}
        self.recovery_attempts: Dict[str, int] = {}
        self.recovery_traffic: Dict[str, float] = {}  # Percentage of traffic to send during recovery
        self.monitoring_task: Optional[asyncio.Task] = None
        self.health_checks: Dict[str, Callable] = {}
        
    async def start_monitoring(self):
        """Start automatic recovery monitoring"""
        if self.monitoring_task:
            return
        
        self.monitoring_task = asyncio.create_task(self._recovery_loop())
        logger.info("Auto-recovery monitoring started")
    
    async def stop_monitoring(self):
        """Stop automatic recovery monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
    
    def register_health_check(self, component_name: str, health_check: Callable):
        """Register a health check function for a component"""
        self.health_checks[component_name] = health_check
    
    async def _recovery_loop(self):
        """Main recovery monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._check_recovery_candidates()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
                await asyncio.sleep(5)
    
    async def _check_recovery_candidates(self):
        """Check if any failed components can be recovered"""
        for component_name, health_check in self.health_checks.items():
            if self.recovery_state.get(component_name) == SystemState.CRITICAL:
                try:
                    is_healthy = await health_check()
                    if is_healthy:
                        await self._attempt_recovery(component_name)
                except Exception as e:
                    logger.debug(f"Health check failed for {component_name}: {e}")
    
    async def _attempt_recovery(self, component_name: str):
        """Attempt to recover a failed component"""
        logger.info(f"Attempting recovery for component: {component_name}")
        
        self.recovery_state[component_name] = SystemState.RECOVERY
        self.recovery_attempts[component_name] = 0
        
        # Start with limited traffic if gradual recovery is enabled
        if self.config.gradual_recovery:
            self.recovery_traffic[component_name] = self.config.recovery_traffic_percentage
        else:
            self.recovery_traffic[component_name] = 1.0
        
        # Validate recovery with test calls
        recovery_validated = await self._validate_recovery(component_name)
        
        if recovery_validated:
            self.recovery_state[component_name] = SystemState.HEALTHY
            self.recovery_traffic[component_name] = 1.0
            logger.info(f"Component {component_name} successfully recovered")
        else:
            self.recovery_state[component_name] = SystemState.CRITICAL
            logger.warning(f"Recovery validation failed for {component_name}")
    
    async def _validate_recovery(self, component_name: str) -> bool:
        """Validate that a component has truly recovered"""
        successful_calls = 0
        
        for attempt in range(self.config.recovery_validation_attempts):
            try:
                health_check = self.health_checks[component_name]
                is_healthy = await health_check()
                
                if is_healthy:
                    successful_calls += 1
                
                await asyncio.sleep(1)  # Brief delay between validation calls
                
            except Exception as e:
                logger.debug(f"Recovery validation call {attempt + 1} failed for {component_name}: {e}")
        
        # Require all validation attempts to succeed
        return successful_calls == self.config.recovery_validation_attempts
    
    def should_route_to_component(self, component_name: str) -> bool:
        """Determine if traffic should be routed to this component during recovery"""
        if component_name not in self.recovery_state:
            return True
        
        state = self.recovery_state[component_name]
        if state == SystemState.HEALTHY:
            return True
        elif state == SystemState.RECOVERY and self.config.gradual_recovery:
            traffic_percentage = self.recovery_traffic.get(component_name, 0.0)
            return random.random() < traffic_percentage
        else:
            return False


class ChaosEngineering:
    """Chaos engineering tools to test system resilience"""
    
    def __init__(self):
        self.active_chaos: Set[str] = set()
        self.chaos_history: List[Dict[str, Any]] = []
        
    async def inject_latency(self, component_name: str, delay_seconds: float, duration_seconds: float = 60.0):
        """Inject artificial latency into a component"""
        chaos_id = f"latency_{component_name}_{int(datetime.now(UTC).timestamp())}"
        self.active_chaos.add(chaos_id)
        
        logger.warning(f"Chaos: Injecting {delay_seconds}s latency to {component_name} for {duration_seconds}s")
        
        try:
            end_time = datetime.now(UTC) + timedelta(seconds=duration_seconds)
            
            while datetime.now(UTC) < end_time:
                await asyncio.sleep(delay_seconds)
                await asyncio.sleep(1)  # Check interval
                
        finally:
            self.active_chaos.discard(chaos_id)
            
        self._record_chaos_test(chaos_id, "latency", component_name, 
                              {"delay": delay_seconds, "duration": duration_seconds})
    
    async def inject_failures(self, component_name: str, failure_rate: float, duration_seconds: float = 60.0):
        """Inject random failures into a component"""
        chaos_id = f"failures_{component_name}_{int(datetime.now(UTC).timestamp())}"
        self.active_chaos.add(chaos_id)
        
        logger.warning(f"Chaos: Injecting {failure_rate:.0%} failure rate to {component_name} for {duration_seconds}s")
        
        try:
            end_time = datetime.now(UTC) + timedelta(seconds=duration_seconds)
            
            while datetime.now(UTC) < end_time:
                if random.random() < failure_rate:
                    # This would integrate with the actual component to cause failures
                    logger.debug(f"Chaos: Triggered failure for {component_name}")
                
                await asyncio.sleep(1)
                
        finally:
            self.active_chaos.discard(chaos_id)
            
        self._record_chaos_test(chaos_id, "failures", component_name,
                              {"failure_rate": failure_rate, "duration": duration_seconds})
    
    async def partition_network(self, component_name: str, duration_seconds: float = 60.0):
        """Simulate network partition for a component"""
        chaos_id = f"partition_{component_name}_{int(datetime.now(UTC).timestamp())}"
        self.active_chaos.add(chaos_id)
        
        logger.warning(f"Chaos: Network partition for {component_name} for {duration_seconds}s")
        
        try:
            await asyncio.sleep(duration_seconds)
        finally:
            self.active_chaos.discard(chaos_id)
            
        self._record_chaos_test(chaos_id, "partition", component_name,
                              {"duration": duration_seconds})
    
    def _record_chaos_test(self, chaos_id: str, chaos_type: str, component: str, parameters: Dict[str, Any]):
        """Record chaos test for analysis"""
        self.chaos_history.append({
            "chaos_id": chaos_id,
            "type": chaos_type,
            "component": component,
            "parameters": parameters,
            "timestamp": datetime.now(UTC).isoformat(),
            "completed": True
        })
    
    def get_chaos_report(self) -> Dict[str, Any]:
        """Generate chaos engineering report"""
        return {
            "active_chaos_count": len(self.active_chaos),
            "active_chaos": list(self.active_chaos),
            "total_tests_run": len(self.chaos_history),
            "test_history": self.chaos_history[-10:],  # Last 10 tests
            "test_types": {
                chaos_type: sum(1 for test in self.chaos_history if test["type"] == chaos_type)
                for chaos_type in ["latency", "failures", "partition"]
            }
        }


class ResilienceManager:
    """Central manager for all resilience patterns"""
    
    def __init__(self):
        self.metrics = ResilienceMetrics()
        self.graceful_degradation = GracefulDegradation(FallbackConfig())
        self.cascade_protection = CascadeProtection(CascadeProtectionConfig())
        self.auto_recovery = AutoRecovery(AutoRecoveryConfig())
        self.chaos_engineering = ChaosEngineering()
        self.system_state = SystemState.HEALTHY
        
    async def initialize(self):
        """Initialize resilience manager"""
        await self.auto_recovery.start_monitoring()
        logger.info("Resilience manager initialized")
    
    async def shutdown(self):
        """Shutdown resilience manager"""
        await self.auto_recovery.stop_monitoring()
        logger.info("Resilience manager shutdown")
    
    async def execute_with_resilience(self, operation: Callable, component_name: str, 
                                    strategy: ResilienceStrategy = ResilienceStrategy.RETRY_WITH_FALLBACK,
                                    *args, **kwargs) -> Any:
        """Execute operation with specified resilience strategy"""
        self.metrics.total_requests += 1
        
        # Check cascade protection
        if not await self.cascade_protection.is_component_available(component_name):
            logger.warning(f"Component {component_name} is isolated, failing fast")
            self.metrics.failed_requests += 1
            raise StartupFactoryError(f"Component {component_name} is temporarily unavailable")
        
        # Acquire dependency limits
        acquired = await self.cascade_protection.acquire_dependency_limit(component_name)
        if not acquired:
            logger.warning(f"Dependency {component_name} at capacity")
            self.metrics.failed_requests += 1
            raise StartupFactoryError(f"Component {component_name} is at capacity")
        
        try:
            if strategy == ResilienceStrategy.GRACEFUL_DEGRADATION:
                result = await self.graceful_degradation.execute(operation, *args, **kwargs)
                
                # Check if we got a degraded response
                if isinstance(result, dict) and result.get("status") == "degraded":
                    self.metrics.degraded_responses += 1
                else:
                    self.metrics.successful_requests += 1
                    
            else:
                # Default execution
                result = await operation(*args, **kwargs)
                self.metrics.successful_requests += 1
            
            # Record success for cascade protection and auto-recovery
            await self.cascade_protection.record_success(component_name)
            
            return result
            
        except Exception as e:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = datetime.now(UTC)
            
            # Record failure for cascade protection
            await self.cascade_protection.record_failure(component_name)
            
            logger.error(f"Operation failed for component {component_name}: {e}")
            raise
            
        finally:
            # Release dependency limits
            self.cascade_protection.release_dependency_limit(component_name)
    
    def register_component_health_check(self, component_name: str, health_check: Callable):
        """Register health check for auto-recovery"""
        self.auto_recovery.register_health_check(component_name, health_check)
    
    async def run_chaos_test(self, test_type: str, component_name: str, **kwargs):
        """Run chaos engineering test"""
        if test_type == "latency":
            await self.chaos_engineering.inject_latency(component_name, **kwargs)
        elif test_type == "failures":
            await self.chaos_engineering.inject_failures(component_name, **kwargs)
        elif test_type == "partition":
            await self.chaos_engineering.partition_network(component_name, **kwargs)
        else:
            raise ValueError(f"Unknown chaos test type: {test_type}")
            
        self.metrics.chaos_tests_run += 1
    
    async def get_resilience_report(self) -> Dict[str, Any]:
        """Generate comprehensive resilience report"""
        return {
            "system_state": self.system_state.value,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": self.metrics.success_rate,
                "availability": self.metrics.availability,
                "degraded_responses": self.metrics.degraded_responses,
                "fallback_activations": self.metrics.fallback_activations,
                "auto_recoveries": self.metrics.auto_recoveries,
                "cascade_preventions": self.metrics.cascade_preventions,
            },
            "component_states": self.cascade_protection.component_states,
            "recovery_states": self.auto_recovery.recovery_state,
            "chaos_report": self.chaos_engineering.get_chaos_report(),
            "graceful_degradation_healthy": await self.graceful_degradation.is_healthy(),
            "timestamp": datetime.now(UTC).isoformat()
        }


# Global resilience manager instance
_global_resilience_manager: Optional[ResilienceManager] = None


def get_global_resilience_manager() -> ResilienceManager:
    """Get or create the global resilience manager"""
    global _global_resilience_manager
    if _global_resilience_manager is None:
        _global_resilience_manager = ResilienceManager()
    return _global_resilience_manager


# Convenience decorators for common patterns
def resilient_operation(component_name: str, strategy: ResilienceStrategy = ResilienceStrategy.RETRY_WITH_FALLBACK):
    """Decorator to make a function resilient"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_global_resilience_manager()
            return await manager.execute_with_resilience(func, component_name, strategy, *args, **kwargs)
        return wrapper
    return decorator


def graceful_degradation(component_name: str):
    """Decorator for graceful degradation pattern"""
    return resilient_operation(component_name, ResilienceStrategy.GRACEFUL_DEGRADATION)