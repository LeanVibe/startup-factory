#!/usr/bin/env python3
"""
Comprehensive testing for System Monitoring Components
Tests health monitoring, budget monitoring, and alert systems
"""

import asyncio
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import logging
from dataclasses import dataclass
from typing import Dict, List, Any

# Import the modules under test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from health_monitor import (
    ProviderHealthMonitor, HealthStatus, HealthMetric, ProviderHealth,
    HealthAlert, default_console_health_alert_handler
)
from budget_monitor import (
    BudgetMonitor, BudgetLimit, BudgetAlert, SpendingRecord,
    BudgetExceededError, default_console_alert_handler
)
from core_types import Task, TaskType, ProviderError


# Mock classes for testing
@dataclass
class MockProviderResult:
    """Mock provider result for testing"""
    success: bool
    error_message: str = None
    cost: float = 0.0
    tokens_used: int = 0
    latency_ms: float = 0.0


class MockAIProvider:
    """Mock AI provider for testing"""
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.call_history = []
    
    async def call(self, task: Task) -> MockProviderResult:
        """Mock provider call"""
        if self.should_fail:
            result = MockProviderResult(success=False, error_message="Mock failure")
        else:
            result = MockProviderResult(success=True, cost=0.1, tokens_used=100, latency_ms=500)
        
        self.call_history.append(result)
        return result


class MockAIProviderManager:
    """Mock AI provider manager for testing"""
    def __init__(self):
        self.providers = {
            'openai': MockAIProvider('openai'),
            'anthropic': MockAIProvider('anthropic'),
            'perplexity': MockAIProvider('perplexity')
        }
    
    def get_available_providers(self) -> List[str]:
        return list(self.providers.keys())
    
    def get_provider(self, name: str):
        return self.providers.get(name)
    
    async def call_provider(self, provider_name: str, task: Task) -> MockProviderResult:
        provider = self.providers.get(provider_name)
        if provider:
            return await provider.call(task)
        else:
            return MockProviderResult(success=False, error_message="Provider not found")
    
    def get_cost_statistics(self) -> Dict[str, Any]:
        return {
            'providers': {
                'openai': {'cost': 1.0, 'calls': 10},
                'anthropic': {'cost': 0.8, 'calls': 8},
                'perplexity': {'cost': 0.3, 'calls': 5}
            }
        }


# Create a mock ProviderHealthMonitor for testing without dependencies
class TestableProviderHealthMonitor(ProviderHealthMonitor):
    """Testable version that doesn't depend on external modules"""
    
    def __init__(self, provider_manager: MockAIProviderManager, check_interval: float = 60.0):
        """Initialize with mock provider manager"""
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


class TestHealthMonitoring:
    """Test suite for ProviderHealthMonitor"""
    
    @pytest.fixture
    def mock_provider_manager(self):
        """Create mock provider manager for testing"""
        return MockAIProviderManager()
    
    @pytest.fixture
    def health_monitor(self, mock_provider_manager):
        """Create health monitor for testing"""
        return TestableProviderHealthMonitor(mock_provider_manager, check_interval=1.0)
    
    @pytest.mark.asyncio
    async def test_health_monitor_initialization(self, health_monitor):
        """Test health monitor initialization"""
        assert len(health_monitor.provider_health) == 3  # openai, anthropic, perplexity
        
        for provider_name in ['openai', 'anthropic', 'perplexity']:
            health = health_monitor.provider_health[provider_name]
            assert health.provider_name == provider_name
            assert health.overall_status == HealthStatus.UNKNOWN
            assert health.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_single_health_check(self, health_monitor):
        """Test single provider health check"""
        # Perform health check
        await health_monitor._check_provider_health('openai')
        
        # Verify health was updated
        health = health_monitor.provider_health['openai']
        assert health.last_check is not None
        assert health.overall_status != HealthStatus.UNKNOWN
        assert 'latency' in health.metrics
        assert 'success_rate' in health.metrics
        assert 'consecutive_failures' in health.metrics
    
    @pytest.mark.asyncio
    async def test_health_check_success_flow(self, health_monitor):
        """Test successful health check flow"""
        await health_monitor._check_provider_health('openai')
        
        health = health_monitor.provider_health['openai']
        
        # Should have successful metrics
        assert health.consecutive_failures == 0
        assert health.last_successful_call is not None
        assert health.metrics['success_rate'].value == 1.0
        assert health.metrics['success_rate'].status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_health_check_failure_flow(self, health_monitor):
        """Test failed health check flow"""
        # Make provider fail
        health_monitor.provider_manager.providers['openai'].should_fail = True
        
        await health_monitor._check_provider_health('openai')
        
        health = health_monitor.provider_health['openai']
        
        # Should have failure metrics
        assert health.consecutive_failures == 1
        assert len(health.recent_errors) > 0
        assert health.metrics['success_rate'].value == 0.0
        assert health.metrics['consecutive_failures'].status in [HealthStatus.WARNING, HealthStatus.HEALTHY]
    
    @pytest.mark.asyncio
    async def test_health_status_calculation(self, health_monitor):
        """Test overall health status calculation"""
        # Simulate high latency
        with patch.object(health_monitor, '_check_provider_health') as mock_check:
            async def mock_health_check(provider_name):
                health = health_monitor.provider_health[provider_name]
                
                # Set high latency metric
                health.metrics['latency'] = HealthMetric(
                    name='Response Latency',
                    value=15000.0,  # 15 seconds - should be critical
                    status=HealthStatus.CRITICAL,
                    threshold_warning=5000,
                    threshold_critical=10000,
                    unit='ms'
                )
                
                await health_monitor._calculate_overall_health(provider_name)
            
            mock_check.side_effect = mock_health_check
            
            await health_monitor._check_provider_health('openai')
            
            health = health_monitor.provider_health['openai']
            assert health.overall_status == HealthStatus.CRITICAL
    
    @pytest.mark.asyncio
    async def test_alert_generation(self, health_monitor):
        """Test health alert generation"""
        alerts_received = []
        
        def alert_callback(alert: HealthAlert):
            alerts_received.append(alert)
        
        health_monitor.register_alert_callback(alert_callback)
        
        # Simulate status change from UNKNOWN to HEALTHY
        health = health_monitor.provider_health['openai']
        health.overall_status = HealthStatus.UNKNOWN
        
        await health_monitor._trigger_health_alert('openai', HealthStatus.UNKNOWN, HealthStatus.HEALTHY)
        
        # Should have generated a recovery alert
        assert len(alerts_received) == 1
        alert = alerts_received[0]
        assert alert.provider_name == 'openai'
        assert alert.alert_type == 'recovery'
        assert alert.severity == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self, health_monitor):
        """Test monitoring loop start/stop"""
        # Start monitoring
        await health_monitor.start_monitoring()
        assert health_monitor.monitoring is True
        assert health_monitor.monitor_task is not None
        
        # Let it run for a short time
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        await health_monitor.stop_monitoring()
        assert health_monitor.monitoring is False
    
    @pytest.mark.asyncio
    async def test_get_healthy_providers(self, health_monitor):
        """Test getting healthy providers"""
        # Set up different health statuses
        health_monitor.provider_health['openai'].overall_status = HealthStatus.HEALTHY
        health_monitor.provider_health['anthropic'].overall_status = HealthStatus.WARNING
        health_monitor.provider_health['perplexity'].overall_status = HealthStatus.CRITICAL
        
        healthy_providers = await health_monitor.get_healthy_providers()
        
        # Should return healthy and warning providers
        assert 'openai' in healthy_providers
        assert 'anthropic' in healthy_providers
        assert 'perplexity' not in healthy_providers
    
    @pytest.mark.asyncio
    async def test_get_best_provider(self, health_monitor):
        """Test best provider selection"""
        # Set up different health metrics
        openai_health = health_monitor.provider_health['openai']
        openai_health.overall_status = HealthStatus.HEALTHY
        openai_health.metrics = {
            'latency': HealthMetric('latency', 500, HealthStatus.HEALTHY, 5000, 10000, 'ms'),
            'success_rate': HealthMetric('success_rate', 0.98, HealthStatus.HEALTHY, 0.9, 0.8, '%'),
            'cost_efficiency': HealthMetric('cost_efficiency', 1.0, HealthStatus.HEALTHY, 1.5, 2.0, 'ratio')
        }
        openai_health.uptime_percentage = 99.5
        
        anthropic_health = health_monitor.provider_health['anthropic']
        anthropic_health.overall_status = HealthStatus.WARNING
        anthropic_health.metrics = {
            'latency': HealthMetric('latency', 2000, HealthStatus.WARNING, 5000, 10000, 'ms'),
            'success_rate': HealthMetric('success_rate', 0.85, HealthStatus.WARNING, 0.9, 0.8, '%'),
            'cost_efficiency': HealthMetric('cost_efficiency', 1.8, HealthStatus.WARNING, 1.5, 2.0, 'ratio')
        }
        anthropic_health.uptime_percentage = 95.0
        
        # Perplexity is down
        health_monitor.provider_health['perplexity'].overall_status = HealthStatus.CRITICAL
        
        best_provider = await health_monitor.get_best_provider()
        
        # Should select OpenAI due to better metrics
        assert best_provider == 'openai'
    
    @pytest.mark.asyncio
    async def test_health_summary(self, health_monitor):
        """Test health summary generation"""
        # Set up various health statuses
        health_monitor.provider_health['openai'].overall_status = HealthStatus.HEALTHY
        health_monitor.provider_health['anthropic'].overall_status = HealthStatus.WARNING
        health_monitor.provider_health['perplexity'].overall_status = HealthStatus.CRITICAL
        
        summary = await health_monitor.get_health_summary()
        
        # Verify summary structure
        assert 'overall_status' in summary
        assert 'provider_counts' in summary
        assert 'monitoring' in summary
        assert 'check_interval' in summary
        
        counts = summary['provider_counts']
        assert counts['total'] == 3
        assert counts['healthy'] == 1
        assert counts['warning'] == 1
        assert counts['critical'] == 1
        
        # Overall status should be critical due to one critical provider
        assert summary['overall_status'] == HealthStatus.CRITICAL
    
    @pytest.mark.asyncio
    async def test_metric_thresholds(self, health_monitor):
        """Test health metric threshold evaluation"""
        # Test latency thresholds
        health_monitor.default_thresholds['latency_warning'] = 1000
        health_monitor.default_thresholds['latency_critical'] = 2000
        
        await health_monitor._update_health_metrics('openai', True, 1500, 0.1)  # Warning level
        
        health = health_monitor.provider_health['openai']
        latency_metric = health.metrics['latency']
        
        assert latency_metric.value == 1500
        assert latency_metric.status == HealthStatus.WARNING
        
        await health_monitor._update_health_metrics('openai', True, 2500, 0.1)  # Critical level
        
        latency_metric = health.metrics['latency']
        assert latency_metric.status == HealthStatus.CRITICAL
    
    def test_alert_handlers(self, capsys):
        """Test default alert handlers"""
        alert = HealthAlert(
            provider_name='test_provider',
            alert_type='degradation',
            severity=HealthStatus.WARNING,
            message='Test alert message'
        )
        
        # Test console handler
        default_console_health_alert_handler(alert)
        
        captured = capsys.readouterr()
        assert 'HEALTH ALERT' in captured.out
        assert 'WARNING' in captured.out
        assert 'Test alert message' in captured.out


class TestBudgetMonitoring:
    """Test suite for BudgetMonitor"""
    
    @pytest.fixture
    def budget_monitor(self):
        """Create budget monitor for testing"""
        return BudgetMonitor()
    
    @pytest.mark.asyncio
    async def test_budget_limit_setting(self, budget_monitor):
        """Test setting budget limits"""
        await budget_monitor.set_budget_limit(
            startup_id='test-startup',
            daily_limit=100.0,
            weekly_limit=500.0,
            monthly_limit=1500.0,
            total_limit=5000.0,
            warning_threshold=0.8
        )
        
        # Verify limit was stored
        assert 'test-startup' in budget_monitor.budget_limits
        limit = budget_monitor.budget_limits['test-startup']
        
        assert limit.startup_id == 'test-startup'
        assert limit.daily_limit == 100.0
        assert limit.weekly_limit == 500.0
        assert limit.monthly_limit == 1500.0
        assert limit.total_limit == 5000.0
        assert limit.warning_threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_budget_limit_validation(self, budget_monitor):
        """Test budget limit validation"""
        # Test invalid inputs
        with pytest.raises(ValueError, match="Startup ID cannot be empty"):
            await budget_monitor.set_budget_limit('', daily_limit=100.0)
        
        with pytest.raises(ValueError, match="Daily limit cannot be negative"):
            await budget_monitor.set_budget_limit('test', daily_limit=-10.0)
        
        with pytest.raises(ValueError, match="Warning threshold must be between 0 and 1.0"):
            await budget_monitor.set_budget_limit('test', warning_threshold=1.5)
    
    @pytest.mark.asyncio
    async def test_spending_recording(self, budget_monitor):
        """Test recording spending transactions"""
        await budget_monitor.record_spending(
            startup_id='test-startup',
            provider='openai',
            task_id='task-001',
            cost=2.50,
            tokens_used=1000,
            task_type='market_research',
            success=True
        )
        
        # Verify spending was recorded
        assert len(budget_monitor.spending_records) == 1
        record = budget_monitor.spending_records[0]
        
        assert record.startup_id == 'test-startup'
        assert record.provider == 'openai'
        assert record.task_id == 'task-001'
        assert record.cost == 2.50
        assert record.tokens_used == 1000
        assert record.task_type == 'market_research'
        assert record.success is True
    
    @pytest.mark.asyncio
    async def test_spending_validation(self, budget_monitor):
        """Test spending record validation"""
        with pytest.raises(ValueError, match="Startup ID cannot be empty"):
            await budget_monitor.record_spending('', 'openai', 'task', 1.0, 100, 'test')
        
        with pytest.raises(ValueError, match="Cost cannot be negative"):
            await budget_monitor.record_spending('test', 'openai', 'task', -1.0, 100, 'test')
        
        with pytest.raises(ValueError, match="Tokens used cannot be negative"):
            await budget_monitor.record_spending('test', 'openai', 'task', 1.0, -100, 'test')
    
    @pytest.mark.asyncio
    async def test_budget_limit_checking(self, budget_monitor):
        """Test budget limit checking and alerts"""
        # Set up budget limits
        await budget_monitor.set_budget_limit(
            startup_id='test-startup',
            daily_limit=10.0,
            total_limit=50.0,
            warning_threshold=0.8  # 80% warning
        )
        
        alerts_received = []
        
        def alert_callback(alert: BudgetAlert):
            alerts_received.append(alert)
        
        budget_monitor.register_alert_callback(alert_callback)
        
        # Record spending approaching warning threshold
        await budget_monitor.record_spending('test-startup', 'openai', 'task1', 8.5, 100, 'test')
        
        # Should trigger warning alert
        assert len(alerts_received) == 1
        alert = alerts_received[0]
        assert alert.alert_type == 'warning'
        assert alert.startup_id == 'test-startup'
        assert alert.percentage_used >= 0.8
    
    @pytest.mark.asyncio
    async def test_budget_exceeded_error(self, budget_monitor):
        """Test budget exceeded error handling"""
        # Set strict budget limits
        await budget_monitor.set_budget_limit(
            startup_id='test-startup',
            daily_limit=5.0,
            hard_stop=True
        )
        
        # Record spending that exceeds limit
        with pytest.raises(BudgetExceededError):
            await budget_monitor.record_spending('test-startup', 'openai', 'task1', 6.0, 100, 'test')
    
    @pytest.mark.asyncio
    async def test_can_proceed_with_task(self, budget_monitor):
        """Test task proceed validation"""
        await budget_monitor.set_budget_limit(
            startup_id='test-startup',
            daily_limit=10.0,
            total_limit=50.0
        )
        
        # Should be able to proceed with small cost
        can_proceed = await budget_monitor.can_proceed_with_task('test-startup', 2.0)
        assert can_proceed is True
        
        # Record some spending
        await budget_monitor.record_spending('test-startup', 'openai', 'task1', 8.0, 100, 'test')
        
        # Should not be able to proceed with large cost
        can_proceed = await budget_monitor.can_proceed_with_task('test-startup', 5.0)
        assert can_proceed is False
        
        # Should be able to proceed with small cost
        can_proceed = await budget_monitor.can_proceed_with_task('test-startup', 1.5)
        assert can_proceed is True
    
    @pytest.mark.asyncio
    async def test_budget_status_reporting(self, budget_monitor):
        """Test budget status reporting"""
        await budget_monitor.set_budget_limit(
            startup_id='test-startup',
            daily_limit=10.0,
            weekly_limit=50.0,
            monthly_limit=150.0,
            total_limit=500.0
        )
        
        # Record some spending
        await budget_monitor.record_spending('test-startup', 'openai', 'task1', 3.0, 100, 'test')
        await budget_monitor.record_spending('test-startup', 'anthropic', 'task2', 2.5, 150, 'test')
        
        status = await budget_monitor.get_budget_status('test-startup')
        
        # Verify status structure
        assert status['startup_id'] == 'test-startup'
        assert status['has_limits'] is True
        
        limits = status['limits']
        assert limits['daily'] == 10.0
        assert limits['weekly'] == 50.0
        assert limits['monthly'] == 150.0
        assert limits['total'] == 500.0
        
        current = status['current_spending']
        assert current['total'] == 5.5  # 3.0 + 2.5
        
        utilization = status['utilization']
        assert utilization['daily'] == 0.55  # 5.5 / 10.0
        assert utilization['total'] == 0.011  # 5.5 / 500.0
    
    @pytest.mark.asyncio
    async def test_global_budget_status(self, budget_monitor):
        """Test global budget status across all startups"""
        # Record spending for multiple startups
        await budget_monitor.record_spending('startup-1', 'openai', 'task1', 2.0, 100, 'research')
        await budget_monitor.record_spending('startup-1', 'anthropic', 'task2', 1.5, 150, 'analysis')
        await budget_monitor.record_spending('startup-2', 'openai', 'task3', 3.0, 200, 'research')
        
        global_status = await budget_monitor.get_global_budget_status()
        
        # Verify global metrics
        assert global_status['current_spending']['total'] == 6.5
        assert global_status['total_transactions'] == 3
        assert global_status['successful_transactions'] == 3
        assert global_status['active_startups'] == 2
        
        # Verify provider breakdown
        provider_breakdown = global_status['provider_breakdown']
        assert provider_breakdown['openai'] == 5.0  # 2.0 + 3.0
        assert provider_breakdown['anthropic'] == 1.5
        
        # Verify task type breakdown
        task_breakdown = global_status['task_type_breakdown']
        assert task_breakdown['research'] == 5.0
        assert task_breakdown['analysis'] == 1.5
    
    @pytest.mark.asyncio
    async def test_spending_summary(self, budget_monitor):
        """Test spending summary generation"""
        # Record spending over time
        base_time = datetime.utcnow()
        
        # Manually add records with specific timestamps
        records = [
            SpendingRecord('test-startup', 'openai', 'task1', 1.0, 100, 
                         base_time - timedelta(hours=2), 'research', True),
            SpendingRecord('test-startup', 'anthropic', 'task2', 2.0, 200, 
                         base_time - timedelta(days=2), 'analysis', True),
            SpendingRecord('test-startup', 'openai', 'task3', 1.5, 150, 
                         base_time - timedelta(weeks=2), 'development', True)
        ]
        
        budget_monitor.spending_records.extend(records)
        
        summary = await budget_monitor.get_spending_summary('test-startup')
        
        assert summary['total'] == 4.5
        assert summary['daily'] == 1.0  # Only task1 in last 24 hours
        assert summary['by_provider']['openai'] == 2.5
        assert summary['by_provider']['anthropic'] == 2.0
    
    @pytest.mark.asyncio
    async def test_export_spending_report(self, budget_monitor):
        """Test detailed spending report export"""
        # Add test data
        await budget_monitor.record_spending('startup-1', 'openai', 'task1', 2.0, 100, 'research', True)
        await budget_monitor.record_spending('startup-1', 'openai', 'task2', 1.0, 50, 'analysis', False)  # Failed
        await budget_monitor.record_spending('startup-2', 'anthropic', 'task3', 3.0, 200, 'development', True)
        
        # Export report
        report = await budget_monitor.export_spending_report()
        
        # Verify report structure
        assert 'summary' in report
        assert 'provider_breakdown' in report
        assert 'transactions' in report
        
        summary = report['summary']
        assert summary['total_cost'] == 5.0  # Only successful transactions
        assert summary['total_transactions'] == 3
        assert summary['success_rate'] == 2/3  # 2 successful out of 3
        
        # Verify provider breakdown
        provider_stats = report['provider_breakdown']
        assert provider_stats['openai']['successful_calls'] == 1
        assert provider_stats['openai']['failed_calls'] == 1
        assert provider_stats['anthropic']['successful_calls'] == 1
        assert provider_stats['anthropic']['failed_calls'] == 0
    
    @pytest.mark.asyncio
    async def test_recent_alerts(self, budget_monitor):
        """Test recent alerts retrieval"""
        # Manually add alerts
        old_alert = BudgetAlert(
            startup_id='test',
            alert_type='warning',
            message='Old alert',
            current_spend=10.0,
            limit_amount=15.0,
            percentage_used=0.67,
            timestamp=datetime.utcnow() - timedelta(hours=25)  # Older than 24 hours
        )
        
        recent_alert = BudgetAlert(
            startup_id='test',
            alert_type='warning',
            message='Recent alert',
            current_spend=12.0,
            limit_amount=15.0,
            percentage_used=0.8,
            timestamp=datetime.utcnow() - timedelta(hours=1)  # Recent
        )
        
        budget_monitor.alerts.extend([old_alert, recent_alert])
        
        # Get recent alerts (last 24 hours)
        recent = await budget_monitor.get_recent_alerts(hours=24)
        
        assert len(recent) == 1
        assert recent[0].message == 'Recent alert'
    
    def test_console_alert_handler(self, capsys):
        """Test default console alert handler"""
        alert = BudgetAlert(
            startup_id='test-startup',
            alert_type='warning',
            message='Test budget alert',
            current_spend=80.0,
            limit_amount=100.0,
            percentage_used=0.8
        )
        
        default_console_alert_handler(alert)
        
        captured = capsys.readouterr()
        assert 'BUDGET ALERT' in captured.out
        assert 'WARNING' in captured.out
        assert 'Test budget alert' in captured.out


class TestMonitoringIntegration:
    """Integration tests for monitoring components"""
    
    @pytest.fixture
    def mock_provider_manager(self):
        return MockAIProviderManager()
    
    @pytest.fixture
    def monitoring_system(self, mock_provider_manager):
        """Set up complete monitoring system"""
        health_monitor = ProviderHealthMonitor(mock_provider_manager, check_interval=0.1)
        budget_monitor = BudgetMonitor()
        
        return {
            'health': health_monitor,
            'budget': budget_monitor,
            'providers': mock_provider_manager
        }
    
    @pytest.mark.asyncio
    async def test_integrated_monitoring_workflow(self, monitoring_system):
        """Test integrated monitoring workflow"""
        health_monitor = monitoring_system['health']
        budget_monitor = monitoring_system['budget']
        
        # Set up budget limits
        await budget_monitor.set_budget_limit(
            startup_id='integration-test',
            daily_limit=20.0,
            total_limit=100.0
        )
        
        # Start health monitoring
        await health_monitor.start_monitoring()
        
        # Simulate some operations
        await asyncio.sleep(0.2)  # Let health monitoring run
        
        # Record some spending
        await budget_monitor.record_spending(
            'integration-test', 'openai', 'task1', 5.0, 500, 'research'
        )
        
        # Check that both systems are working
        health_summary = await health_monitor.get_health_summary()
        budget_status = await budget_monitor.get_budget_status('integration-test')
        
        assert health_summary['monitoring'] is True
        assert budget_status['current_spending']['total'] == 5.0
        
        # Stop monitoring
        await health_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_monitoring_with_failures(self, monitoring_system):
        """Test monitoring behavior with provider failures"""
        health_monitor = monitoring_system['health']
        budget_monitor = monitoring_system['budget']
        
        # Make a provider fail
        monitoring_system['providers'].providers['openai'].should_fail = True
        
        # Perform health check
        await health_monitor._check_provider_health('openai')
        
        # Check health status
        openai_health = await health_monitor.get_provider_health('openai')
        assert openai_health.consecutive_failures > 0
        
        # Try to get best provider (should avoid failed one)
        best_provider = await health_monitor.get_best_provider()
        assert best_provider != 'openai'  # Should select a healthy provider
    
    @pytest.mark.asyncio
    async def test_alert_coordination(self, monitoring_system):
        """Test alert coordination between systems"""
        health_monitor = monitoring_system['health']
        budget_monitor = monitoring_system['budget']
        
        health_alerts = []
        budget_alerts = []
        
        def health_alert_callback(alert):
            health_alerts.append(alert)
        
        def budget_alert_callback(alert):
            budget_alerts.append(alert)
        
        # Register alert handlers
        health_monitor.register_alert_callback(health_alert_callback)
        budget_monitor.register_alert_callback(budget_alert_callback)
        
        # Set strict budget
        await budget_monitor.set_budget_limit('test', daily_limit=1.0)
        
        # Trigger budget alert
        await budget_monitor.record_spending('test', 'openai', 'task', 0.9, 100, 'test')  # Warning
        
        # Trigger health alert by simulating status change
        await health_monitor._trigger_health_alert('openai', HealthStatus.UNKNOWN, HealthStatus.HEALTHY)
        
        # Verify alerts were received
        assert len(budget_alerts) > 0
        assert len(health_alerts) > 0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])