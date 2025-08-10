#!/usr/bin/env python3
"""
Comprehensive tests for resilience patterns and error recovery
"""

import asyncio
import pytest
import sys
import tempfile
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

# Add tools directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from resilience import (
    ResilienceManager, GracefulDegradation, CascadeProtection, AutoRecovery,
    ChaosEngineering, ResilienceStrategy, SystemState, FallbackConfig,
    CascadeProtectionConfig, AutoRecoveryConfig, resilient_operation,
    graceful_degradation, get_global_resilience_manager
)
from core_types import StartupFactoryError


class TestGracefulDegradation:
    """Test graceful degradation pattern"""
    
    @pytest.fixture
    def degradation(self):
        """Create graceful degradation instance"""
        config = FallbackConfig(cache_ttl=60.0, max_degradation_time=300.0)
        return GracefulDegradation(config)
    
    @pytest.mark.asyncio
    async def test_successful_operation_caching(self, degradation):
        """Test successful operation with response caching"""
        async def mock_operation():
            return {"result": "success", "data": [1, 2, 3]}
        
        # First call should succeed and cache result
        result = await degradation.execute(mock_operation)
        assert result["result"] == "success"
        assert degradation.degraded_since is None
        
        # Verify caching occurred
        assert len(degradation.fallback_cache) > 0
        # Check that a cache entry exists with the expected result
        cached_values = list(degradation.fallback_cache.values())
        assert any(v.get("result") == "success" for v in cached_values)
    
    @pytest.mark.asyncio
    async def test_degraded_response_from_cache(self, degradation):
        """Test degraded response served from cache"""
        async def test_operation():
            return {"result": "cached_data"}
        
        # First successful call to populate cache
        await degradation.execute(test_operation)
        
        # Mock the same operation to fail on second call
        call_count = 0
        async def intermittent_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"result": "cached_data"}
            else:
                raise Exception("Service unavailable")
        
        # First call succeeds and caches
        result1 = await degradation.execute(intermittent_operation)
        assert result1["result"] == "cached_data"
        
        # Second call fails but should serve from cache
        result2 = await degradation.execute(intermittent_operation)
        assert result2["result"] == "cached_data"
        assert degradation.degraded_since is not None
    
    @pytest.mark.asyncio
    async def test_degraded_response_when_no_cache(self, degradation):
        """Test degraded response when no cache available"""
        async def failing_operation():
            raise Exception("Service unavailable")
        
        # Should provide degraded response
        result = await degradation.execute(failing_operation)
        assert result["status"] == "degraded"
        assert "temporarily degraded" in result["message"]
        assert degradation.degraded_since is not None
    
    @pytest.mark.asyncio
    async def test_max_degradation_time_exceeded(self, degradation):
        """Test failure when max degradation time exceeded"""
        # Set a very short max degradation time
        degradation.config.max_degradation_time = 0.1
        
        async def failing_operation():
            raise Exception("Persistent failure")
        
        # First call should provide degraded response
        result = await degradation.execute(failing_operation)
        assert result["status"] == "degraded"
        
        # Wait for max degradation time to pass
        await asyncio.sleep(0.2)
        
        # Second call should fail
        with pytest.raises(Exception, match="Persistent failure"):
            await degradation.execute(failing_operation)
    
    @pytest.mark.asyncio
    async def test_recovery_from_degraded_state(self, degradation):
        """Test recovery from degraded state"""
        call_count = 0
        
        async def intermittent_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return {"result": "recovered"}
        
        # First call fails, should provide degraded response
        result1 = await degradation.execute(intermittent_operation)
        assert result1["status"] == "degraded"
        assert degradation.degraded_since is not None
        
        # Second call succeeds, should recover
        result2 = await degradation.execute(intermittent_operation)
        assert result2["result"] == "recovered"
        assert degradation.degraded_since is None
    
    @pytest.mark.asyncio
    async def test_cache_expiry(self, degradation):
        """Test cache expiry functionality"""
        degradation.config.cache_ttl = 0.1  # Very short TTL
        
        async def mock_operation():
            return {"cached": "data"}
        
        # Populate cache
        await degradation.execute(mock_operation)
        
        # Wait for cache to expire
        await asyncio.sleep(0.2)
        
        async def failing_operation():
            raise Exception("Service down")
        
        # Should provide degraded response (not cached)
        result = await degradation.execute(failing_operation)
        assert result["status"] == "degraded"


class TestCascadeProtection:
    """Test cascade failure protection"""
    
    @pytest.fixture
    def protection(self):
        """Create cascade protection instance"""
        config = CascadeProtectionConfig(
            failure_threshold=0.5,
            isolation_timeout=1.0,  # Short for testing
            dependency_limits={"test_service": 2}
        )
        return CascadeProtection(config)
    
    @pytest.mark.asyncio
    async def test_component_isolation(self, protection):
        """Test component isolation after failures"""
        component = "test_component"
        
        # Component should be available initially
        assert await protection.is_component_available(component)
        
        # Record enough failures to trigger isolation
        for _ in range(3):
            await protection.record_failure(component)
        
        # Component should now be isolated
        assert not await protection.is_component_available(component)
        
        # Wait for isolation to expire
        await asyncio.sleep(1.1)
        
        # Component should be available again
        assert await protection.is_component_available(component)
    
    @pytest.mark.asyncio
    async def test_dependency_limits(self, protection):
        """Test dependency concurrency limits"""
        dependency = "test_service"
        
        # Should be able to acquire up to the limit
        acquired1 = await protection.acquire_dependency_limit(dependency)
        assert acquired1 is True
        
        acquired2 = await protection.acquire_dependency_limit(dependency)
        assert acquired2 is True
        
        # Third acquisition should fail (limit is 2)
        acquired3 = await protection.acquire_dependency_limit(dependency)
        assert acquired3 is False
        
        # Release one and try again
        protection.release_dependency_limit(dependency)
        acquired4 = await protection.acquire_dependency_limit(dependency)
        assert acquired4 is True
    
    @pytest.mark.asyncio
    async def test_failure_threshold_calculation(self, protection):
        """Test failure threshold calculation for cascade protection"""
        # Add components
        components = ["comp1", "comp2", "comp3", "comp4"]
        
        # Record failures for half the components (should trigger protection)
        for component in components[:2]:
            await protection.record_failure(component)
        
        # Check that failure threshold logic is working
        total_components = len(protection.component_states)
        failed_components = sum(1 for state in protection.component_states.values() 
                              if state == SystemState.CRITICAL)
        failure_rate = failed_components / max(1, total_components)
        
        assert failure_rate >= protection.config.failure_threshold
    
    @pytest.mark.asyncio
    async def test_component_recovery(self, protection):
        """Test component recovery from failures"""
        component = "recovering_component"
        
        # Record failure
        await protection.record_failure(component)
        assert protection.component_states[component] == SystemState.CRITICAL
        
        # Record success (recovery)
        await protection.record_success(component)
        assert protection.component_states[component] == SystemState.HEALTHY
        assert protection.failure_counts[component] == 0


class TestAutoRecovery:
    """Test automatic recovery system"""
    
    @pytest.fixture
    def recovery(self):
        """Create auto recovery instance"""
        config = AutoRecoveryConfig(
            health_check_interval=0.1,  # Fast for testing
            recovery_validation_attempts=2,
            gradual_recovery=True,
            recovery_traffic_percentage=0.5
        )
        return AutoRecovery(config)
    
    @pytest.mark.asyncio
    async def test_health_check_registration(self, recovery):
        """Test health check registration"""
        component = "test_component"
        
        async def health_check():
            return True
        
        recovery.register_health_check(component, health_check)
        assert component in recovery.health_checks
    
    @pytest.mark.asyncio
    async def test_recovery_attempt(self, recovery):
        """Test automatic recovery attempt"""
        component = "failing_component"
        
        async def health_check():
            return True  # Always return healthy for successful recovery
        
        recovery.register_health_check(component, health_check)
        recovery.recovery_state[component] = SystemState.CRITICAL
        
        # Attempt recovery
        await recovery._attempt_recovery(component)
        
        # Should succeed after validation calls
        assert recovery.recovery_state[component] == SystemState.HEALTHY
        assert recovery.recovery_traffic[component] == 1.0
    
    @pytest.mark.asyncio
    async def test_gradual_recovery_traffic(self, recovery):
        """Test gradual traffic increase during recovery"""
        component = "gradual_component"
        
        recovery.recovery_state[component] = SystemState.RECOVERY
        recovery.recovery_traffic[component] = 0.5
        
        # Should route approximately 50% of traffic
        route_count = 0
        total_checks = 100
        
        for _ in range(total_checks):
            if recovery.should_route_to_component(component):
                route_count += 1
        
        # Allow some variance in random routing
        assert 0.3 * total_checks <= route_count <= 0.7 * total_checks
    
    @pytest.mark.asyncio
    async def test_recovery_monitoring_loop(self, recovery):
        """Test recovery monitoring loop"""
        component = "monitored_component"
        recovery_attempted = False
        
        async def health_check():
            return True
        
        recovery.register_health_check(component, health_check)
        recovery.recovery_state[component] = SystemState.CRITICAL
        
        # Mock the recovery attempt to track if it's called
        async def mock_attempt_recovery(comp_name):
            nonlocal recovery_attempted
            recovery_attempted = True
            recovery.recovery_state[comp_name] = SystemState.HEALTHY
        
        recovery._attempt_recovery = mock_attempt_recovery
        
        # Start monitoring briefly
        await recovery.start_monitoring()
        await asyncio.sleep(0.15)  # Let it run for one cycle
        await recovery.stop_monitoring()
        
        assert recovery_attempted


class TestChaosEngineering:
    """Test chaos engineering functionality"""
    
    @pytest.fixture
    def chaos(self):
        """Create chaos engineering instance"""
        return ChaosEngineering()
    
    @pytest.mark.asyncio
    async def test_latency_injection(self, chaos):
        """Test latency injection"""
        component = "test_service"
        delay = 0.1
        duration = 0.2
        
        # Start latency injection
        latency_task = asyncio.create_task(
            chaos.inject_latency(component, delay, duration)
        )
        
        # Check that chaos is active
        await asyncio.sleep(0.05)
        assert len(chaos.active_chaos) > 0
        
        # Wait for completion
        await latency_task
        
        # Check that chaos completed and was recorded
        assert len(chaos.active_chaos) == 0
        assert len(chaos.chaos_history) == 1
        
        test_record = chaos.chaos_history[0]
        assert test_record["type"] == "latency"
        assert test_record["component"] == component
        assert test_record["parameters"]["delay"] == delay
    
    @pytest.mark.asyncio
    async def test_failure_injection(self, chaos):
        """Test failure injection"""
        component = "failing_service"
        failure_rate = 0.8
        duration = 0.1
        
        # Inject failures
        await chaos.inject_failures(component, failure_rate, duration)
        
        # Check that test was recorded
        assert len(chaos.chaos_history) == 1
        test_record = chaos.chaos_history[0]
        assert test_record["type"] == "failures"
        assert test_record["parameters"]["failure_rate"] == failure_rate
    
    @pytest.mark.asyncio
    async def test_network_partition(self, chaos):
        """Test network partition simulation"""
        component = "partitioned_service"
        duration = 0.1
        
        # Simulate partition
        await chaos.partition_network(component, duration)
        
        # Check that test was recorded
        assert len(chaos.chaos_history) == 1
        test_record = chaos.chaos_history[0]
        assert test_record["type"] == "partition"
        assert test_record["parameters"]["duration"] == duration
    
    def test_chaos_report_generation(self, chaos):
        """Test chaos engineering report generation"""
        # Add some test history
        chaos.chaos_history = [
            {"type": "latency", "component": "svc1", "timestamp": "2024-01-01T00:00:00Z"},
            {"type": "failures", "component": "svc2", "timestamp": "2024-01-01T01:00:00Z"},
            {"type": "partition", "component": "svc3", "timestamp": "2024-01-01T02:00:00Z"},
        ]
        
        report = chaos.get_chaos_report()
        
        assert report["total_tests_run"] == 3
        assert report["test_types"]["latency"] == 1
        assert report["test_types"]["failures"] == 1
        assert report["test_types"]["partition"] == 1


class TestResilienceManager:
    """Test resilience manager integration"""
    
    @pytest.fixture
    def manager(self):
        """Create resilience manager"""
        return ResilienceManager()
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager):
        """Test resilience manager initialization"""
        await manager.initialize()
        
        # Check that auto-recovery monitoring started
        assert manager.auto_recovery.monitoring_task is not None
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_execute_with_resilience_success(self, manager):
        """Test successful execution with resilience"""
        component = "test_component"
        
        async def successful_operation():
            return {"status": "success"}
        
        result = await manager.execute_with_resilience(
            successful_operation, component, ResilienceStrategy.GRACEFUL_DEGRADATION
        )
        
        assert result["status"] == "success"
        assert manager.metrics.successful_requests == 1
        assert manager.metrics.total_requests == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_resilience_failure(self, manager):
        """Test failure handling with resilience"""
        component = "failing_component"
        
        async def failing_operation():
            raise Exception("Operation failed")
        
        with pytest.raises(Exception, match="Operation failed"):
            await manager.execute_with_resilience(
                failing_operation, component, ResilienceStrategy.FAIL_FAST
            )
        
        assert manager.metrics.failed_requests == 1
        assert manager.metrics.total_requests == 1
    
    @pytest.mark.asyncio
    async def test_component_isolation_integration(self, manager):
        """Test component isolation through resilience manager"""
        component = "isolated_component"
        
        async def failing_operation():
            raise Exception("Persistent failure")
        
        # Cause multiple failures to trigger isolation
        for _ in range(6):  # Exceed failure threshold
            try:
                await manager.execute_with_resilience(
                    failing_operation, component, ResilienceStrategy.FAIL_FAST
                )
            except:
                pass
        
        # Component should now be isolated
        is_available = await manager.cascade_protection.is_component_available(component)
        assert not is_available
    
    @pytest.mark.asyncio
    async def test_chaos_test_execution(self, manager):
        """Test chaos test execution through manager"""
        component = "chaos_target"
        
        # Run latency chaos test
        await manager.run_chaos_test("latency", component, delay_seconds=0.1, duration_seconds=0.1)
        
        assert manager.metrics.chaos_tests_run == 1
        assert len(manager.chaos_engineering.chaos_history) == 1
    
    @pytest.mark.asyncio
    async def test_resilience_report_generation(self, manager):
        """Test comprehensive resilience report"""
        # Execute some operations to generate metrics
        async def test_operation():
            return "success"
        
        await manager.execute_with_resilience(test_operation, "test_comp")
        
        report = await manager.get_resilience_report()
        
        assert "system_state" in report
        assert "metrics" in report
        assert "component_states" in report
        assert report["metrics"]["total_requests"] == 1
        assert report["metrics"]["success_rate"] == 1.0
    
    def test_global_manager_singleton(self):
        """Test global resilience manager singleton"""
        manager1 = get_global_resilience_manager()
        manager2 = get_global_resilience_manager()
        
        assert manager1 is manager2


class TestResilienceDecorators:
    """Test resilience decorators"""
    
    @pytest.mark.asyncio
    async def test_resilient_operation_decorator(self):
        """Test @resilient_operation decorator"""
        @resilient_operation("test_service")
        async def decorated_function():
            return "decorated_result"
        
        result = await decorated_function()
        assert result == "decorated_result"
        
        # Check that operation was tracked
        manager = get_global_resilience_manager()
        assert manager.metrics.total_requests > 0
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_decorator(self):
        """Test @graceful_degradation decorator"""
        @graceful_degradation("degraded_service")
        async def degraded_function():
            raise Exception("Service unavailable")
        
        # Should provide degraded response instead of failing
        result = await degraded_function()
        assert result["status"] == "degraded"


class TestResilienceIntegration:
    """Integration tests for resilience patterns"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_resilience_scenario(self):
        """Test comprehensive resilience scenario"""
        manager = ResilienceManager()
        await manager.initialize()
        
        component = "integration_service"
        call_count = 0
        
        async def intermittent_service():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception(f"Failure {call_count}")
            elif call_count <= 5:
                return {"status": "recovered", "attempt": call_count}
            else:
                return {"status": "stable", "attempt": call_count}
        
        # Register health check for auto-recovery
        async def health_check():
            try:
                await intermittent_service()
                return True
            except:
                return False
        
        manager.register_component_health_check(component, health_check)
        
        # Execute operations with resilience
        results = []
        for i in range(8):
            try:
                result = await manager.execute_with_resilience(
                    intermittent_service, component, ResilienceStrategy.GRACEFUL_DEGRADATION
                )
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
            
            await asyncio.sleep(0.05)  # Small delay between calls
        
        # Verify resilience patterns worked
        assert len(results) == 8
        
        # First few should be degraded responses
        degraded_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "degraded")
        assert degraded_count > 0
        
        # Later ones should show recovery
        recovered_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") in ["recovered", "stable"])
        assert recovered_count > 0
        
        # Check final metrics
        report = await manager.get_resilience_report()
        assert report["metrics"]["total_requests"] == 8
        assert report["metrics"]["availability"] > 0  # Should have some availability despite failures
        
        await manager.shutdown()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])