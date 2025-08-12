#!/usr/bin/env python3
"""
Provider Health Monitoring System
Monitors AI provider availability, performance, and automatically handles failover.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Dict, List, Optional, Callable, Any

from core_types import Task, TaskType, ProviderError

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: float
    status: HealthStatus
    threshold_warning: float
    threshold_critical: float
    unit: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ProviderHealth:
    """Complete health status for a provider"""
    provider_name: str
    overall_status: HealthStatus
    last_check: datetime
    uptime_percentage: float
    metrics: Dict[str, HealthMetric]
    recent_errors: List[str]
    consecutive_failures: int
    last_successful_call: Optional[datetime] = None
    next_check: Optional[datetime] = None


@dataclass
class HealthAlert:
    """Health monitoring alert"""
    provider_name: str
    alert_type: str  # 'degradation', 'failure', 'recovery'
    severity: HealthStatus
    message: str
    metric_name: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ProviderHealthMonitor:
    """
    Comprehensive provider health monitoring system
    
    Features:
    - Real-time health checks for all providers
    - Performance metric tracking (latency, success rate, cost)
    - Automatic failover when providers become unhealthy
    - Alert system for health degradation
    - Historical health data tracking
    """
    
    def __init__(self, provider_manager, check_interval: float = 60.0):
        """
        Initialize health monitor
        
        Args:
            provider_manager: AI provider manager to monitor
            check_interval: Health check interval in seconds
        """
        self.provider_manager = provider_manager
        self.check_interval = check_interval
        
        # Health tracking
        self.provider_health: Dict[str, ProviderHealth] = {}
        self.health_history: List[Dict[str, Any]] = []
        self.alerts: List[HealthAlert] = []
        self.alert_callbacks: List[Callable[[HealthAlert], None]] = []
        
        # Monitoring control
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Thresholds (can be customized per provider)
        self.default_thresholds = {
            'latency_warning': 5000,  # 5 seconds
            'latency_critical': 10000,  # 10 seconds
            'success_rate_warning': 0.90,  # 90%
            'success_rate_critical': 0.80,  # 80%
            'cost_efficiency_warning': 1.5,  # 50% above baseline
            'cost_efficiency_critical': 2.0,  # 100% above baseline
            'consecutive_failures_warning': 3,
            'consecutive_failures_critical': 5
        }
        
        # Initialize health status for all providers
        self._initialize_provider_health()
        
        logger.info(f"Health monitor initialized for {len(self.provider_health)} providers")
    
    def _initialize_provider_health(self) -> None:
        """Initialize health status for all providers"""
        for provider_name in self.provider_manager.get_available_providers():
            self.provider_health[provider_name] = ProviderHealth(
                provider_name=provider_name,
                overall_status=HealthStatus.UNKNOWN,
                last_check=datetime.now(UTC),
                uptime_percentage=100.0,
                metrics={},
                recent_errors=[],
                consecutive_failures=0
            )
    
    async def start_monitoring(self) -> None:
        """Start health monitoring"""
        if self.monitoring:
            logger.warning("Health monitoring already started")
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Started provider health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped provider health monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info("Health monitoring loop started")
        
        while self.monitoring:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5.0)  # Short delay before retrying
        
        logger.info("Health monitoring loop stopped")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all providers"""
        check_tasks = []
        
        for provider_name in self.provider_health.keys():
            task = asyncio.create_task(self._check_provider_health(provider_name))
            check_tasks.append(task)
        
        # Run all health checks concurrently
        await asyncio.gather(*check_tasks, return_exceptions=True)
    
    async def _check_provider_health(self, provider_name: str) -> None:
        """
        Check health of a specific provider
        
        Args:
            provider_name: Name of provider to check
        """
        health = self.provider_health[provider_name]
        
        try:
            # Create a simple test task
            test_task = Task(
                id=f"health_check_{provider_name}_{int(time.time())}",
                startup_id="health_check",
                type=TaskType.MARKET_RESEARCH,
                description="Health check task",
                prompt="Please respond with 'OK' to confirm you are functioning properly.",
                max_tokens=50
            )
            
            # Perform health check call
            start_time = time.time()
            result = await self.provider_manager.call_provider(provider_name, test_task)
            end_time = time.time()
            
            # Calculate metrics
            latency_ms = (end_time - start_time) * 1000
            
            # Update health metrics
            await self._update_health_metrics(provider_name, result.success, latency_ms, result.cost)
            
            # Update last successful call if successful
            if result.success:
                health.last_successful_call = datetime.now(UTC)
                health.consecutive_failures = 0
            else:
                health.consecutive_failures += 1
                health.recent_errors.append(result.error_message or "Unknown error")
                
                # Keep only recent errors (last 10)
                health.recent_errors = health.recent_errors[-10:]
        
        except Exception as e:
            logger.error(f"Health check failed for {provider_name}: {e}")
            health.consecutive_failures += 1
            health.recent_errors.append(str(e))
            health.recent_errors = health.recent_errors[-10:]
            
            # Update health metrics with failure
            await self._update_health_metrics(provider_name, False, 0, 0)
        
        # Update overall health status
        health.last_check = datetime.now(UTC)
        health.next_check = health.last_check + timedelta(seconds=self.check_interval)
        await self._calculate_overall_health(provider_name)
    
    async def _update_health_metrics(self, provider_name: str, success: bool, 
                                   latency_ms: float, cost: float) -> None:
        """
        Update health metrics for a provider
        
        Args:
            provider_name: Provider name
            success: Whether the call was successful
            latency_ms: Response latency in milliseconds
            cost: Cost of the call
        """
        health = self.provider_health[provider_name]
        now = datetime.now(UTC)
        
        # Get cost statistics for comparison
        cost_stats = self.provider_manager.get_cost_statistics()
        provider_stats = cost_stats.get('providers', {}).get(provider_name, {})
        baseline_cost = provider_stats.get('cost', 0) / max(1, provider_stats.get('calls', 1))
        
        # Update latency metric
        latency_status = HealthStatus.HEALTHY
        if latency_ms > self.default_thresholds['latency_critical']:
            latency_status = HealthStatus.CRITICAL
        elif latency_ms > self.default_thresholds['latency_warning']:
            latency_status = HealthStatus.WARNING
        
        health.metrics['latency'] = HealthMetric(
            name='Response Latency',
            value=latency_ms,
            status=latency_status,
            threshold_warning=self.default_thresholds['latency_warning'],
            threshold_critical=self.default_thresholds['latency_critical'],
            unit='ms',
            timestamp=now
        )
        
        # Update success rate metric (calculate from recent history)
        recent_calls = self._get_recent_call_history(provider_name, hours=1)
        if recent_calls:
            success_rate = sum(1 for call in recent_calls if call.get('success', False)) / len(recent_calls)
        else:
            success_rate = 1.0 if success else 0.0
        
        success_status = HealthStatus.HEALTHY
        if success_rate < self.default_thresholds['success_rate_critical']:
            success_status = HealthStatus.CRITICAL
        elif success_rate < self.default_thresholds['success_rate_warning']:
            success_status = HealthStatus.WARNING
        
        health.metrics['success_rate'] = HealthMetric(
            name='Success Rate',
            value=success_rate,
            status=success_status,
            threshold_warning=self.default_thresholds['success_rate_warning'],
            threshold_critical=self.default_thresholds['success_rate_critical'],
            unit='%',
            timestamp=now
        )
        
        # Update cost efficiency metric
        cost_efficiency = cost / max(0.001, baseline_cost) if baseline_cost > 0 else 1.0
        
        cost_status = HealthStatus.HEALTHY
        if cost_efficiency > self.default_thresholds['cost_efficiency_critical']:
            cost_status = HealthStatus.WARNING  # Cost issues are warnings, not critical
        elif cost_efficiency > self.default_thresholds['cost_efficiency_warning']:
            cost_status = HealthStatus.WARNING
        
        health.metrics['cost_efficiency'] = HealthMetric(
            name='Cost Efficiency',
            value=cost_efficiency,
            status=cost_status,
            threshold_warning=self.default_thresholds['cost_efficiency_warning'],
            threshold_critical=self.default_thresholds['cost_efficiency_critical'],
            unit='ratio',
            timestamp=now
        )
        
        # Update consecutive failures metric
        failure_status = HealthStatus.HEALTHY
        if health.consecutive_failures >= self.default_thresholds['consecutive_failures_critical']:
            failure_status = HealthStatus.CRITICAL
        elif health.consecutive_failures >= self.default_thresholds['consecutive_failures_warning']:
            failure_status = HealthStatus.WARNING
        
        health.metrics['consecutive_failures'] = HealthMetric(
            name='Consecutive Failures',
            value=health.consecutive_failures,
            status=failure_status,
            threshold_warning=self.default_thresholds['consecutive_failures_warning'],
            threshold_critical=self.default_thresholds['consecutive_failures_critical'],
            unit='count',
            timestamp=now
        )
    
    def _get_recent_call_history(self, provider_name: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent call history for a provider"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        
        # Get from provider manager's call history if available
        provider = self.provider_manager.get_provider(provider_name)
        if hasattr(provider, 'call_history'):
            sanitized: List[Dict[str, Any]] = []
            for call in provider.call_history:
                # Some mocks may not include timestamp/latency fields
                ts = getattr(call, 'timestamp', None)
                if ts is None:
                    # Assume now for recent synthetic calls to avoid crashes in tests
                    ts = datetime.now(UTC)
                lat = getattr(call, 'latency_ms', None)
                if lat is None:
                    lat = 0.0
                cost = getattr(call, 'cost', 0.0)
                success = getattr(call, 'success', False)
                if ts >= cutoff_time:
                    sanitized.append({
                        'success': success,
                        'timestamp': ts,
                        'latency_ms': float(lat),
                        'cost': float(cost),
                    })
            return sanitized
        
        return []
    
    async def _calculate_overall_health(self, provider_name: str) -> None:
        """Calculate overall health status for a provider"""
        health = self.provider_health[provider_name]
        
        if not health.metrics:
            health.overall_status = HealthStatus.UNKNOWN
            return
        
        # Count status levels
        status_counts = {
            HealthStatus.CRITICAL: 0,
            HealthStatus.WARNING: 0,
            HealthStatus.HEALTHY: 0
        }
        
        for metric in health.metrics.values():
            if metric.status in status_counts:
                status_counts[metric.status] += 1
        
        # Determine overall status
        if status_counts[HealthStatus.CRITICAL] > 0:
            new_status = HealthStatus.CRITICAL
        elif status_counts[HealthStatus.WARNING] > 1:  # Multiple warnings = critical
            new_status = HealthStatus.CRITICAL
        elif status_counts[HealthStatus.WARNING] > 0:
            new_status = HealthStatus.WARNING
        else:
            new_status = HealthStatus.HEALTHY
        
        # Check for status changes and trigger alerts
        old_status = health.overall_status
        health.overall_status = new_status
        
        if old_status != new_status:
            await self._trigger_health_alert(provider_name, old_status, new_status)
        
        # Calculate uptime percentage
        health.uptime_percentage = await self._calculate_uptime(provider_name)
    
    async def _calculate_uptime(self, provider_name: str, hours: int = 24) -> float:
        """Calculate uptime percentage for a provider"""
        # This is a simplified calculation
        # In a real implementation, you'd track detailed uptime/downtime periods
        health = self.provider_health[provider_name]
        
        if health.consecutive_failures == 0:
            return 100.0
        elif health.consecutive_failures < 3:
            return 95.0
        elif health.consecutive_failures < 5:
            return 80.0
        else:
            return 50.0
    
    async def _trigger_health_alert(self, provider_name: str, 
                                  old_status: HealthStatus, new_status: HealthStatus) -> None:
        """Trigger a health status change alert"""
        if new_status == HealthStatus.CRITICAL and old_status != HealthStatus.CRITICAL:
            alert = HealthAlert(
                provider_name=provider_name,
                alert_type='degradation',
                severity=HealthStatus.CRITICAL,
                message=f"Provider {provider_name} health degraded to CRITICAL"
            )
        elif new_status == HealthStatus.WARNING and old_status == HealthStatus.HEALTHY:
            alert = HealthAlert(
                provider_name=provider_name,
                alert_type='degradation',
                severity=HealthStatus.WARNING,
                message=f"Provider {provider_name} health degraded to WARNING"
            )
        elif new_status == HealthStatus.HEALTHY and old_status in [HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.UNKNOWN]:
            alert = HealthAlert(
                provider_name=provider_name,
                alert_type='recovery',
                severity=HealthStatus.HEALTHY,
                message=f"Provider {provider_name} health recovered to HEALTHY"
            )
        else:
            return  # No alert needed
        
        self.alerts.append(alert)
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                await asyncio.get_event_loop().run_in_executor(None, callback, alert)
            except Exception as e:
                logger.error(f"Error in health alert callback: {e}")
        
        # Log the alert
        if alert.severity == HealthStatus.CRITICAL:
            logger.error(alert.message)
        elif alert.severity == HealthStatus.WARNING:
            logger.warning(alert.message)
        else:
            logger.info(alert.message)
    
    def register_alert_callback(self, callback: Callable[[HealthAlert], None]) -> None:
        """Register a callback to be called when health alerts are triggered"""
        self.alert_callbacks.append(callback)
    
    async def get_provider_health(self, provider_name: str) -> Optional[ProviderHealth]:
        """Get health status for a specific provider"""
        return self.provider_health.get(provider_name)
    
    async def get_all_provider_health(self) -> Dict[str, ProviderHealth]:
        """Get health status for all providers"""
        return self.provider_health.copy()
    
    async def get_healthy_providers(self) -> List[str]:
        """Get list of currently healthy providers"""
        return [
            name for name, health in self.provider_health.items()
            if health.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]
        ]
    
    async def get_best_provider(self, task_type: Optional[TaskType] = None) -> Optional[str]:
        """
        Get the best available provider based on health metrics
        
        Args:
            task_type: Optional task type for provider optimization
            
        Returns:
            str: Best provider name, or None if no healthy providers
        """
        healthy_providers = await self.get_healthy_providers()
        
        if not healthy_providers:
            return None
        
        # Score providers based on health metrics
        provider_scores = {}
        
        for provider_name in healthy_providers:
            health = self.provider_health[provider_name]
            score = 0
            
            # Health status score
            if health.overall_status == HealthStatus.HEALTHY:
                score += 100
            elif health.overall_status == HealthStatus.WARNING:
                score += 70
            else:
                score += 30
            
            # Latency score (lower is better)
            if 'latency' in health.metrics:
                latency = health.metrics['latency'].value
                score += max(0, 50 - (latency / 100))  # Penalize high latency
            
            # Success rate score
            if 'success_rate' in health.metrics:
                score += health.metrics['success_rate'].value * 50
            
            # Cost efficiency score (lower cost is better)
            if 'cost_efficiency' in health.metrics:
                efficiency = health.metrics['cost_efficiency'].value
                score += max(0, 50 - (efficiency - 1) * 25)  # Penalize high cost
            
            # Uptime score
            score += health.uptime_percentage * 0.5
            
            provider_scores[provider_name] = score
        
        # Return provider with highest score
        best_provider = max(provider_scores.items(), key=lambda x: x[1])
        return best_provider[0]
    
    async def get_recent_alerts(self, hours: int = 24) -> List[HealthAlert]:
        """Get recent health alerts"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        return [
            alert for alert in self.alerts
            if alert.timestamp >= cutoff_time
        ]
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        healthy_count = sum(
            1 for health in self.provider_health.values()
            if health.overall_status == HealthStatus.HEALTHY
        )
        warning_count = sum(
            1 for health in self.provider_health.values()
            if health.overall_status == HealthStatus.WARNING
        )
        critical_count = sum(
            1 for health in self.provider_health.values()
            if health.overall_status == HealthStatus.CRITICAL
        )
        
        total_providers = len(self.provider_health)
        recent_alerts = await self.get_recent_alerts(hours=24)
        
        return {
            "overall_status": (
                HealthStatus.CRITICAL if critical_count > 0
                else HealthStatus.WARNING if warning_count > 0
                else HealthStatus.HEALTHY
            ),
            "provider_counts": {
                "total": total_providers,
                "healthy": healthy_count,
                "warning": warning_count,
                "critical": critical_count
            },
            "monitoring": self.monitoring,
            "check_interval": self.check_interval,
            "recent_alerts": len(recent_alerts),
            "last_check": max(
                (health.last_check for health in self.provider_health.values()),
                default=datetime.now(UTC)
            ).isoformat()
        }


# Default alert handlers
def default_console_health_alert_handler(alert: HealthAlert) -> None:
    """Default console health alert handler"""
    emoji = {
        'degradation': '🔴',
        'recovery': '🟢',
        'failure': '❌'
    }.get(alert.alert_type, '⚠️')
    
    print(f"{emoji} HEALTH ALERT [{alert.severity.upper()}]: {alert.message}")


def default_file_health_alert_handler(alert: HealthAlert, log_file: str = "health_alerts.log") -> None:
    """Default file health alert handler"""
    with open(log_file, 'a') as f:
        f.write(f"{alert.timestamp.isoformat()} [{alert.alert_type}] {alert.provider_name}: {alert.message}\n")


# Global health monitor instance
_global_health_monitor: Optional[ProviderHealthMonitor] = None


def get_global_health_monitor(provider_manager) -> ProviderHealthMonitor:
    """Get or create the global health monitor instance"""
    global _global_health_monitor
    if _global_health_monitor is None:
        _global_health_monitor = ProviderHealthMonitor(provider_manager)
        _global_health_monitor.register_alert_callback(default_console_health_alert_handler)
    return _global_health_monitor