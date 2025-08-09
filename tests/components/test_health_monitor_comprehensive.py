#!/usr/bin/env python3
"""
Comprehensive Health Monitor Testing Suite

Tests all aspects of the ProviderHealthMonitor system including:
1. Health status tracking and monitoring
2. Failure detection and alert generation
3. Recovery mechanisms and failover logic
4. Performance metric collection
5. Historical data tracking
6. Alert system integration

Coverage Target: 90%+ for critical system reliability
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any
import time

# Import the health monitor and dependencies
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from health_monitor import (
    ProviderHealthMonitor, HealthStatus, HealthMetric, 
    ProviderHealth, HealthAlert
)
from ai_providers import AIProviderManager
from core_types import Task, TaskType, TaskResult, ProviderError


class TestProviderHealthMonitorComprehensive:
    """Comprehensive tests for ProviderHealthMonitor"""
    
    @pytest.fixture
    def mock_provider_manager(self):
        """Mock AI provider manager for testing"""
        manager = Mock(spec=AIProviderManager)
        manager.get_available_providers.return_value = ['openai', 'anthropic', 'perplexity']
        
        # Mock provider objects
        manager.get_provider.return_value = Mock()
        
        return manager
    
    @pytest.fixture
    def health_monitor(self, mock_provider_manager):
        """Create health monitor instance for testing"""
        return ProviderHealthMonitor(mock_provider_manager, check_interval=0.1)
    
    @pytest.fixture
    def sample_task(self):
        """Sample task for testing"""
        return Task(
            id="test_task_001",
            startup_id="test_startup",
            type=TaskType.MARKET_RESEARCH,
            description="Test market research task",
            prompt="Analyze the market for test products"
        )

    # ========== Initialization and Setup Tests ==========
    
    def test_health_monitor_initialization(self, health_monitor, mock_provider_manager):
        """Test proper initialization of health monitor"""
        # Verify basic setup
        assert health_monitor.provider_manager == mock_provider_manager
        assert health_monitor.check_interval == 0.1
        assert not health_monitor.monitoring
        assert health_monitor.monitor_task is None
        
        # Verify provider health initialization
        assert len(health_monitor.provider_health) == 3
        assert 'openai' in health_monitor.provider_health
        assert 'anthropic' in health_monitor.provider_health
        assert 'perplexity' in health_monitor.provider_health
        
        # Verify default thresholds
        assert health_monitor.default_thresholds['latency_warning'] == 5000
        assert health_monitor.default_thresholds['success_rate_critical'] == 0.80
        
        # Verify initial health status
        for provider_health in health_monitor.provider_health.values():
            assert provider_health.overall_status == HealthStatus.UNKNOWN
            assert provider_health.uptime_percentage == 100.0
            assert provider_health.consecutive_failures == 0
    
    def test_provider_health_initialization_empty_providers(self):
        """Test health monitor initialization with no providers"""
        mock_manager = Mock(spec=AIProviderManager)
        mock_manager.get_available_providers.return_value = []
        
        monitor = ProviderHealthMonitor(mock_manager)
        
        assert len(monitor.provider_health) == 0
        assert monitor.provider_manager == mock_manager
    
    # ========== Monitoring Control Tests ==========
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, health_monitor):
        """Test starting health monitoring"""
        assert not health_monitor.monitoring
        assert health_monitor.monitor_task is None
        
        await health_monitor.start_monitoring()
        
        assert health_monitor.monitoring
        assert health_monitor.monitor_task is not None
        assert not health_monitor.monitor_task.done()
        
        # Cleanup
        await health_monitor.stop_monitoring()
    
    @pytest.mark.asyncio 
    async def test_start_monitoring_already_started(self, health_monitor, caplog):
        """Test starting monitoring when already started"""
        await health_monitor.start_monitoring()
        
        # Try to start again
        await health_monitor.start_monitoring()
        
        assert "Health monitoring already started" in caplog.text
        
        # Cleanup
        await health_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, health_monitor):
        """Test stopping health monitoring"""
        await health_monitor.start_monitoring()
        assert health_monitor.monitoring
        
        await health_monitor.stop_monitoring()
        
        assert not health_monitor.monitoring
        assert health_monitor.monitor_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring_not_started(self, health_monitor):
        """Test stopping monitoring when not started"""
        assert not health_monitor.monitoring
        
        # Should not raise an error
        await health_monitor.stop_monitoring()
        
        assert not health_monitor.monitoring
    
    # ========== Health Check Tests ==========
    
    @pytest.mark.asyncio
    async def test_perform_health_check_success(self, health_monitor, sample_task):
        """Test successful health check"""
        # Mock successful API call
        mock_result = TaskResult(
            task_id=sample_task.id,
            startup_id=sample_task.startup_id,
            success=True,
            content="Test response",
            cost=0.01,
            provider_used="openai",
            execution_time_seconds=1.5,
            tokens_used=100,
            completed_at=datetime.utcnow()
        )
        
        health_monitor.provider_manager.call_provider = AsyncMock(return_value=mock_result)
        
        # Perform health check
        await health_monitor._check_provider_health('openai')
        
        # Verify health status updated
        health = health_monitor.provider_health['openai']
        assert health.overall_status == HealthStatus.HEALTHY
        assert 'latency' in health.metrics
        assert 'success_rate' in health.metrics
        assert health.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_perform_health_check_failure(self, health_monitor, sample_task):
        """Test health check with provider failure"""
        # Mock API failure
        health_monitor.provider_manager.call_provider = AsyncMock(
            side_effect=ProviderError("Provider unavailable")
        )
        
        # Perform health check
        await health_monitor._check_provider_health('openai')
        
        # Verify health status updated
        health = health_monitor.provider_health['openai']
        assert health.overall_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
        assert health.consecutive_failures > 0
        assert len(health.recent_errors) > 0
    
    @pytest.mark.asyncio
    async def test_health_check_latency_warning(self, health_monitor, sample_task):
        """Test health check with high latency triggering warning"""
        # Mock slow response
        mock_result = TaskResult(
            task_id=sample_task.id,
            startup_id=sample_task.startup_id,
            success=True,
            content="Test response",
            cost=0.01,
            provider_used="openai",
            execution_time_seconds=7.0,  # Above warning threshold (5s)
            tokens_used=100,
            completed_at=datetime.utcnow()
        )
        
        health_monitor.provider_manager.call_provider = AsyncMock(return_value=mock_result)
        
        # Perform health check
        await health_monitor._check_provider_health('openai')
        
        # Verify warning status
        health = health_monitor.provider_health['openai']
        assert health.metrics['latency'].status == HealthStatus.WARNING
    
    @pytest.mark.asyncio
    async def test_health_check_multiple_failures_critical(self, health_monitor):
        """Test multiple consecutive failures triggering critical status"""
        # Mock repeated failures
        health_monitor.provider_manager.call_provider = AsyncMock(
            side_effect=ProviderError("Provider down")
        )
        
        # Perform multiple health checks
        for i in range(6):  # More than critical threshold (5)
            await health_monitor._check_provider_health('openai')
        
        # Verify critical status
        health = health_monitor.provider_health['openai']
        assert health.overall_status == HealthStatus.CRITICAL
        assert health.consecutive_failures >= 5
    
    # ========== Alert System Tests ==========
    
    @pytest.mark.asyncio
    async def test_alert_generation_on_failure(self, health_monitor):
        """Test alert generation when provider fails"""
        # Setup alert callback
        alert_received = []
        def alert_callback(alert: HealthAlert):
            alert_received.append(alert)
        
        health_monitor.register_alert_callback(alert_callback)
        
        # Mock failure
        health_monitor.provider_manager.call_provider = AsyncMock(
            side_effect=ProviderError("Provider down")
        )
        
        # Trigger health check
        await health_monitor._check_provider_health('openai')
        
        # Wait for alert processing
        await asyncio.sleep(0.1)
        
        # Verify alert generated
        assert len(alert_received) > 0
        alert = alert_received[0]
        assert alert.provider == 'openai'
        assert alert.severity in ['warning', 'critical']
    
    def test_register_alert_callback(self, health_monitor):
        """Test registering alert callback"""
        callback = Mock()
        
        health_monitor.register_alert_callback(callback)
        
        assert callback in health_monitor.alert_callbacks
    
    @pytest.mark.asyncio
    async def test_alert_callback_execution(self, health_monitor):
        """Test that alert callbacks are properly executed"""
        callback1 = Mock()
        callback2 = Mock()
        
        health_monitor.register_alert_callback(callback1)
        health_monitor.register_alert_callback(callback2)
        
        # Create and trigger alert
        alert = HealthAlert(
            provider='openai',
            severity='warning',
            message='Test alert',
            timestamp=datetime.utcnow()
        )
        
        await health_monitor._trigger_alert(alert)
        
        # Verify both callbacks called
        callback1.assert_called_once_with(alert)
        callback2.assert_called_once_with(alert)
    
    # ========== Recovery Mechanism Tests ==========
    
    @pytest.mark.asyncio
    async def test_provider_recovery_detection(self, health_monitor, sample_task):
        """Test detection of provider recovery after failure"""
        # First, simulate failure
        health_monitor.provider_manager.call_provider = AsyncMock(
            side_effect=ProviderError("Provider down")
        )
        await health_monitor._check_provider_health('openai')
        
        # Verify failure status
        health = health_monitor.provider_health['openai']
        assert health.overall_status != HealthStatus.HEALTHY
        assert health.consecutive_failures > 0
        
        # Now simulate recovery
        mock_result = TaskResult(
            task_id=sample_task.id,
            startup_id=sample_task.startup_id,
            success=True,
            content="Test response",
            cost=0.01,
            provider_used="openai",
            execution_time_seconds=1.0,
            tokens_used=100,
            completed_at=datetime.utcnow()
        )
        health_monitor.provider_manager.call_provider = AsyncMock(return_value=mock_result)
        
        await health_monitor._check_provider_health('openai')
        
        # Verify recovery
        health = health_monitor.provider_health['openai']
        assert health.overall_status == HealthStatus.HEALTHY
        assert health.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_gradual_recovery_tracking(self, health_monitor, sample_task):
        """Test gradual recovery tracking and status improvement"""
        # Simulate initial failures
        health_monitor.provider_manager.call_provider = AsyncMock(
            side_effect=ProviderError("Provider intermittent")
        )
        for _ in range(3):
            await health_monitor._check_provider_health('openai')
        
        initial_failures = health_monitor.provider_health['openai'].consecutive_failures
        assert initial_failures >= 3
        
        # Simulate gradual recovery with mixed success/failure
        responses = [
            TaskResult(
                task_id=sample_task.id, startup_id=sample_task.startup_id,
                success=True, content="Success", cost=0.01, provider_used="openai",
                execution_time_seconds=1.0, tokens_used=100, completed_at=datetime.utcnow()
            ),
            ProviderError("Still failing"),
            TaskResult(
                task_id=sample_task.id, startup_id=sample_task.startup_id,
                success=True, content="Success", cost=0.01, provider_used="openai",
                execution_time_seconds=1.0, tokens_used=100, completed_at=datetime.utcnow()
            )
        ]
        
        for response in responses:
            if isinstance(response, Exception):
                health_monitor.provider_manager.call_provider = AsyncMock(side_effect=response)
            else:
                health_monitor.provider_manager.call_provider = AsyncMock(return_value=response)
            
            await health_monitor._check_provider_health('openai')
        
        # Verify recovery progress
        final_failures = health_monitor.provider_health['openai'].consecutive_failures
        assert final_failures < initial_failures
    
    # ========== Performance Metric Tests ==========
    
    @pytest.mark.asyncio
    async def test_latency_metric_calculation(self, health_monitor, sample_task):
        """Test latency metric calculation and status assignment"""
        test_cases = [
            (2.0, HealthStatus.HEALTHY),    # Below warning
            (6.0, HealthStatus.WARNING),    # Above warning, below critical  
            (12.0, HealthStatus.CRITICAL),  # Above critical
        ]
        
        for execution_time, expected_status in test_cases:
            mock_result = TaskResult(
                task_id=sample_task.id, startup_id=sample_task.startup_id,
                success=True, content="Test", cost=0.01, provider_used="openai",
                execution_time_seconds=execution_time, tokens_used=100,
                completed_at=datetime.utcnow()
            )
            
            health_monitor.provider_manager.call_provider = AsyncMock(return_value=mock_result)
            await health_monitor._check_provider_health('openai')
            
            health = health_monitor.provider_health['openai']
            assert health.metrics['latency'].status == expected_status
            assert health.metrics['latency'].value == execution_time * 1000  # Convert to ms
    
    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, health_monitor, sample_task):
        """Test success rate calculation over multiple checks"""
        # Simulate mixed success/failure pattern
        results = [True, True, False, True, False]  # 60% success rate
        
        for success in results:
            if success:
                mock_result = TaskResult(
                    task_id=sample_task.id, startup_id=sample_task.startup_id,
                    success=True, content="Success", cost=0.01, provider_used="openai",
                    execution_time_seconds=1.0, tokens_used=100, completed_at=datetime.utcnow()
                )
                health_monitor.provider_manager.call_provider = AsyncMock(return_value=mock_result)
            else:
                health_monitor.provider_manager.call_provider = AsyncMock(
                    side_effect=ProviderError("Simulated failure")
                )
            
            await health_monitor._check_provider_health('openai')
        
        health = health_monitor.provider_health['openai']
        # Success rate should be around 60% (3/5), which is below critical threshold (80%)
        assert health.metrics['success_rate'].value < 0.80
        assert health.metrics['success_rate'].status == HealthStatus.CRITICAL
    
    # ========== Historical Data Tests ==========
    
    @pytest.mark.asyncio
    async def test_health_history_tracking(self, health_monitor):
        """Test that health history is properly tracked"""
        initial_history_length = len(health_monitor.health_history)
        
        # Perform health checks
        health_monitor.provider_manager.call_provider = AsyncMock(
            side_effect=ProviderError("Test failure")
        )
        
        await health_monitor._check_provider_health('openai')
        await health_monitor._check_provider_health('anthropic')
        
        # Verify history updated
        assert len(health_monitor.health_history) > initial_history_length
        
        # Verify history contains provider data
        latest_entry = health_monitor.health_history[-1]
        assert 'timestamp' in latest_entry
        assert 'providers' in latest_entry
        assert 'openai' in latest_entry['providers']
    
    def test_get_provider_uptime(self, health_monitor):
        """Test provider uptime calculation"""
        provider_name = 'openai'
        
        # Simulate some historical data
        health_monitor.provider_health[provider_name].uptime_percentage = 95.5
        
        uptime = health_monitor.get_provider_uptime(provider_name)
        
        assert uptime == 95.5
    
    def test_get_provider_uptime_unknown_provider(self, health_monitor):
        """Test uptime query for unknown provider"""
        uptime = health_monitor.get_provider_uptime('unknown_provider')
        
        assert uptime == 0.0
    
    # ========== Integration Tests ==========
    
    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self, health_monitor, sample_task):
        """Test complete monitoring cycle with real timing"""
        # Setup mixed provider responses
        responses = {
            'openai': TaskResult(
                task_id=sample_task.id, startup_id=sample_task.startup_id,
                success=True, content="Success", cost=0.01, provider_used="openai",
                execution_time_seconds=1.0, tokens_used=100, completed_at=datetime.utcnow()
            ),
            'anthropic': ProviderError("Down for maintenance"),
            'perplexity': TaskResult(
                task_id=sample_task.id, startup_id=sample_task.startup_id,
                success=True, content="Success", cost=0.02, provider_used="perplexity",
                execution_time_seconds=3.0, tokens_used=150, completed_at=datetime.utcnow()
            )
        }
        
        def mock_call_provider(provider_name, task):
            response = responses[provider_name]
            if isinstance(response, Exception):
                raise response
            return response
        
        health_monitor.provider_manager.call_provider = AsyncMock(side_effect=mock_call_provider)
        
        # Start monitoring briefly
        await health_monitor.start_monitoring()
        await asyncio.sleep(0.2)  # Let it run for a bit
        await health_monitor.stop_monitoring()
        
        # Verify results
        assert health_monitor.provider_health['openai'].overall_status == HealthStatus.HEALTHY
        assert health_monitor.provider_health['anthropic'].overall_status != HealthStatus.HEALTHY
        assert health_monitor.provider_health['perplexity'].overall_status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_error_handling_in_monitoring_loop(self, health_monitor, caplog):
        """Test error handling in the monitoring loop"""
        # Mock a method to raise an exception
        health_monitor._perform_health_checks = AsyncMock(
            side_effect=Exception("Simulated monitoring error")
        )
        
        # Start monitoring briefly
        await health_monitor.start_monitoring()
        await asyncio.sleep(0.2)
        await health_monitor.stop_monitoring()
        
        # Verify error was logged but monitoring continued
        assert "Error in health monitoring loop" in caplog.text
    
    # ========== Edge Cases and Stress Tests ==========
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, health_monitor, sample_task):
        """Test concurrent health checks don't interfere"""
        mock_result = TaskResult(
            task_id=sample_task.id, startup_id=sample_task.startup_id,
            success=True, content="Success", cost=0.01, provider_used="test",
            execution_time_seconds=1.0, tokens_used=100, completed_at=datetime.utcnow()
        )
        
        health_monitor.provider_manager.call_provider = AsyncMock(return_value=mock_result)
        
        # Run multiple concurrent health checks
        tasks = [
            health_monitor._check_provider_health('openai'),
            health_monitor._check_provider_health('anthropic'),
            health_monitor._check_provider_health('perplexity')
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all providers were checked
        for provider in ['openai', 'anthropic', 'perplexity']:
            assert health_monitor.provider_health[provider].overall_status == HealthStatus.HEALTHY
    
    def test_custom_thresholds(self):
        """Test custom threshold configuration"""
        custom_thresholds = {
            'latency_warning': 2000,
            'latency_critical': 4000,
            'success_rate_warning': 0.95,
            'success_rate_critical': 0.85
        }
        
        mock_manager = Mock(spec=AIProviderManager)
        mock_manager.get_available_providers.return_value = ['openai']
        
        monitor = ProviderHealthMonitor(mock_manager)
        monitor.default_thresholds.update(custom_thresholds)
        
        assert monitor.default_thresholds['latency_warning'] == 2000
        assert monitor.default_thresholds['success_rate_critical'] == 0.85
    
    @pytest.mark.asyncio 
    async def test_memory_management_long_running(self, health_monitor):
        """Test memory management during long-running monitoring"""
        # Simulate long-running monitoring with history accumulation
        for i in range(100):
            health_monitor.health_history.append({
                'timestamp': datetime.utcnow(),
                'providers': {'test': 'data'}
            })
        
        # Verify reasonable memory usage (basic check)
        assert len(health_monitor.health_history) == 100
        
        # Test cleanup if implemented
        if hasattr(health_monitor, '_cleanup_old_history'):
            await health_monitor._cleanup_old_history()
    
    # ========== Performance Tests ==========
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self, health_monitor, sample_task):
        """Test health check performance under load"""
        mock_result = TaskResult(
            task_id=sample_task.id, startup_id=sample_task.startup_id,
            success=True, content="Success", cost=0.01, provider_used="openai",
            execution_time_seconds=0.1, tokens_used=100, completed_at=datetime.utcnow()
        )
        
        health_monitor.provider_manager.call_provider = AsyncMock(return_value=mock_result)
        
        # Measure health check performance
        start_time = time.time()
        
        for _ in range(10):
            await health_monitor._check_provider_health('openai')
        
        execution_time = time.time() - start_time
        
        # Health checks should be fast (< 1s for 10 checks)
        assert execution_time < 1.0
        
        # Verify consistency
        health = health_monitor.provider_health['openai']
        assert health.overall_status == HealthStatus.HEALTHY

    def test_health_status_enum_values(self):
        """Test HealthStatus enum values"""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.WARNING == "warning" 
        assert HealthStatus.CRITICAL == "critical"
        assert HealthStatus.DOWN == "down"
        assert HealthStatus.UNKNOWN == "unknown"

    def test_health_metric_creation(self):
        """Test HealthMetric creation and validation"""
        metric = HealthMetric(
            name="test_latency",
            value=1500.0,
            status=HealthStatus.HEALTHY,
            threshold_warning=5000.0,
            threshold_critical=10000.0,
            unit="ms"
        )
        
        assert metric.name == "test_latency"
        assert metric.value == 1500.0
        assert metric.status == HealthStatus.HEALTHY
        assert metric.unit == "ms"
        assert isinstance(metric.timestamp, datetime)