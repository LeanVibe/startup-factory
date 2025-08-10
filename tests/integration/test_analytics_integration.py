#!/usr/bin/env python3
"""
Comprehensive Analytics Integration Testing
Tests integration between analytics, monitoring, and main system components
"""

import asyncio
import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from typing import Dict, List, Any

# Import the modules under test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from analytics_engine import AnalyticsEngine, StartupMetadata, PerformanceMetrics
from health_monitor import ProviderHealthMonitor, HealthStatus
from budget_monitor import BudgetMonitor, BudgetAlert
from core_types import Task, TaskType
from mvp_orchestrator_script import MVPOrchestrator
from multi_startup_manager import MultiStartupManager


# Mock external dependencies
class MockTask(Task):
    """Mock task for testing"""
    def __init__(self, task_id: str, startup_id: str, task_type: TaskType = TaskType.MARKET_RESEARCH):
        self.id = task_id
        self.startup_id = startup_id
        self.type = task_type
        self.description = f"Mock task {task_id}"
        self.prompt = "Mock prompt"
        self.max_tokens = 1000


class MockProviderResult:
    """Mock provider result"""
    def __init__(self, success: bool = True, cost: float = 0.1, tokens_used: int = 100):
        self.success = success
        self.cost = cost
        self.tokens_used = tokens_used
        self.error_message = None if success else "Mock error"
        self.latency_ms = 500.0


class MockAIProvider:
    """Mock AI provider for integration testing"""
    def __init__(self, name: str, reliability: float = 0.95, avg_cost: float = 0.1):
        self.name = name
        self.reliability = reliability  # Success rate
        self.avg_cost = avg_cost
        self.call_history = []
        self.call_count = 0
    
    async def call(self, task: Task) -> MockProviderResult:
        """Mock provider call with configurable reliability"""
        self.call_count += 1
        
        # Simulate provider reliability
        success = np.random.random() < self.reliability
        cost = self.avg_cost * (0.8 + 0.4 * np.random.random())  # ±20% variation
        tokens = int(1000 * (0.5 + np.random.random()))  # 500-1500 tokens
        
        result = MockProviderResult(success=success, cost=cost, tokens_used=tokens)
        self.call_history.append(result)
        
        return result


class MockAIProviderManager:
    """Mock provider manager for integration testing"""
    def __init__(self):
        self.providers = {
            'openai': MockAIProvider('openai', reliability=0.95, avg_cost=0.12),
            'anthropic': MockAIProvider('anthropic', reliability=0.98, avg_cost=0.08),
            'perplexity': MockAIProvider('perplexity', reliability=0.90, avg_cost=0.05)
        }
        self.call_count = 0
    
    def get_available_providers(self) -> List[str]:
        return list(self.providers.keys())
    
    def get_provider(self, name: str):
        return self.providers.get(name)
    
    async def call_provider(self, provider_name: str, task: Task) -> MockProviderResult:
        """Call provider and track metrics"""
        self.call_count += 1
        provider = self.providers.get(provider_name)
        
        if not provider:
            return MockProviderResult(success=False)
        
        return await provider.call(task)
    
    def get_cost_statistics(self) -> Dict[str, Any]:
        """Get provider cost statistics"""
        stats = {'providers': {}}
        
        for name, provider in self.providers.items():
            total_cost = sum(call.cost for call in provider.call_history if call.success)
            successful_calls = len([call for call in provider.call_history if call.success])
            
            stats['providers'][name] = {
                'cost': total_cost,
                'calls': successful_calls,
                'avg_cost': total_cost / max(1, successful_calls)
            }
        
        return stats


class TestAnalyticsIntegration:
    """Test suite for analytics integration with main system"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            yield Path(f.name)
            try:
                Path(f.name).unlink()
            except FileNotFoundError:
                pass
    
    @pytest.fixture
    def mock_provider_manager(self):
        """Create mock provider manager"""
        return MockAIProviderManager()
    
    @pytest.fixture
    def integrated_system(self, temp_db_path, mock_provider_manager):
        """Set up integrated analytics and monitoring system"""
        analytics_engine = AnalyticsEngine(temp_db_path)
        health_monitor = ProviderHealthMonitor(mock_provider_manager, check_interval=0.1)
        budget_monitor = BudgetMonitor()
        
        return {
            'analytics': analytics_engine,
            'health': health_monitor,
            'budget': budget_monitor,
            'providers': mock_provider_manager
        }
    
    @pytest.mark.asyncio
    async def test_startup_creation_analytics_flow(self, integrated_system):
        """Test complete startup creation with analytics tracking"""
        analytics = integrated_system['analytics']
        budget_monitor = integrated_system['budget']
        providers = integrated_system['providers']
        
        # Set up budget for tracking
        await budget_monitor.set_budget_limit(
            startup_id='analytics-test-001',
            daily_limit=50.0,
            total_limit=200.0
        )
        
        # Simulate startup creation process
        startup_data = {
            'id': 'analytics-test-001',
            'name': 'Analytics Test Startup',
            'industry': 'TestTech',
            'category': 'Integration Testing',
            'created_at': datetime.now().isoformat(),
            'status': 'in_progress'
        }
        
        # Track initial creation
        analytics.track_startup_creation(startup_data)
        
        # Simulate tasks during startup creation
        tasks = [
            MockTask('task-001', 'analytics-test-001', TaskType.MARKET_RESEARCH),
            MockTask('task-002', 'analytics-test-001', TaskType.MVP_SPECIFICATION),
            MockTask('task-003', 'analytics-test-001', TaskType.ARCHITECTURE),
            MockTask('task-004', 'analytics-test-001', TaskType.CODE_GENERATION)
        ]
        
        total_cost = 0.0
        successful_tasks = 0
        
        for i, task in enumerate(tasks):
            # Alternate between providers
            provider_name = ['openai', 'anthropic', 'perplexity'][i % 3]
            
            # Call provider
            result = await providers.call_provider(provider_name, task)
            
            # Record budget spending
            await budget_monitor.record_spending(
                startup_id=task.startup_id,
                provider=provider_name,
                task_id=task.id,
                cost=result.cost,
                tokens_used=result.tokens_used,
                task_type=task.type.value,
                success=result.success
            )
            
            # Track performance metrics
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'memory_usage_mb': 1500 + i * 200,
                'cpu_percent': 40 + i * 10,
                'concurrent_startups': 1,
                'api_call_count': i + 1,
                'error_count': 0 if result.success else 1,
                'response_time_ms': result.latency_ms
            }
            analytics.track_performance_metric(metrics_data)
            
            if result.success:
                total_cost += result.cost
                successful_tasks += 1
        
        # Complete startup
        completion_data = startup_data.copy()
        completion_data.update({
            'completed_at': datetime.now().isoformat(),
            'status': 'completed',
            'duration_minutes': 45.0,
            'api_costs': budget_monitor.get_spending_summary('analytics-test-001'),
            'success_score': successful_tasks / len(tasks),
            'bottlenecks': ['api_latency'] if total_cost > 1.0 else []
        })
        
        analytics.track_startup_creation(completion_data)
        
        # Verify analytics data
        report = analytics.generate_report(format='json')
        
        assert report['total_startups'] >= 1
        assert report['avg_creation_time'] > 0
        assert report['cost_per_startup'] > 0
        
        # Verify budget tracking
        budget_status = await budget_monitor.get_budget_status('analytics-test-001')
        assert budget_status['current_spending']['total'] > 0
        assert budget_status['current_spending']['total'] <= budget_status['limits']['daily_limit']
    
    @pytest.mark.asyncio
    async def test_health_monitoring_analytics_correlation(self, integrated_system):
        """Test correlation between health monitoring and analytics"""
        analytics = integrated_system['analytics']
        health_monitor = integrated_system['health']
        providers = integrated_system['providers']
        
        # Start health monitoring
        await health_monitor.start_monitoring()
        
        # Let health monitoring collect some data
        await asyncio.sleep(0.3)
        
        # Get health metrics
        health_summary = await health_monitor.get_health_summary()
        provider_healths = await health_monitor.get_all_provider_health()
        
        # Correlate with analytics data
        real_time_metrics = analytics.get_real_time_metrics()
        
        # Verify correlation
        assert health_summary['monitoring'] is True
        
        # Check that health metrics align with provider usage
        for provider_name, health in provider_healths.items():
            provider = providers.get_provider(provider_name)
            
            if provider and len(provider.call_history) > 0:
                # Health metrics should reflect actual provider performance
                assert health.last_check is not None
                assert health.overall_status != HealthStatus.UNKNOWN
        
        # Stop monitoring
        await health_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_budget_alert_analytics_integration(self, integrated_system):
        """Test budget alert integration with analytics tracking"""
        analytics = integrated_system['analytics']
        budget_monitor = integrated_system['budget']
        providers = integrated_system['providers']
        
        budget_alerts_received = []
        
        def budget_alert_callback(alert: BudgetAlert):
            budget_alerts_received.append(alert)
            
            # Track budget alert as an analytics event
            analytics.db.log_event(
                event_type='budget_alert',
                startup_id=alert.startup_id,
                phase='monitoring',
                details={
                    'alert_type': alert.alert_type,
                    'percentage_used': alert.percentage_used,
                    'current_spend': alert.current_spend,
                    'limit_amount': alert.limit_amount
                }
            )
        
        budget_monitor.register_alert_callback(budget_alert_callback)
        
        # Set tight budget limits for testing
        await budget_monitor.set_budget_limit(
            startup_id='budget-alert-test',
            daily_limit=2.0,  # Very low limit to trigger alerts
            warning_threshold=0.6
        )
        
        # Simulate spending that triggers alerts
        spending_amounts = [0.8, 0.5, 0.9]  # Total: 2.2, exceeds 2.0 limit
        
        for i, amount in enumerate(spending_amounts):
            try:
                await budget_monitor.record_spending(
                    startup_id='budget-alert-test',
                    provider='openai',
                    task_id=f'alert-task-{i+1}',
                    cost=amount,
                    tokens_used=100,
                    task_type='test',
                    success=True
                )
            except Exception as e:
                # Budget exceeded - this is expected
                pass
        
        # Verify alerts were generated and tracked
        assert len(budget_alerts_received) > 0
        
        # Check analytics event logging
        events_df = analytics.db.get_events_dataframe()
        budget_events = events_df[events_df['event_type'] == 'budget_alert']
        
        assert len(budget_events) > 0
        
        # Verify alert details were captured
        for _, event in budget_events.iterrows():
            details = json.loads(event['details'])
            assert 'alert_type' in details
            assert 'percentage_used' in details
            assert details['percentage_used'] > 0
    
    @pytest.mark.asyncio
    async def test_multi_startup_analytics_aggregation(self, integrated_system):
        """Test analytics aggregation across multiple startups"""
        analytics = integrated_system['analytics']
        budget_monitor = integrated_system['budget']
        providers = integrated_system['providers']
        
        # Create multiple startups
        startups = [
            {
                'id': f'multi-startup-{i+1:03d}',
                'name': f'Multi Test Startup {i+1}',
                'industry': ['FinTech', 'HealthTech', 'EdTech'][i % 3],
                'category': 'B2B SaaS',
                'created_at': (datetime.now() - timedelta(hours=i)).isoformat(),
                'status': 'in_progress'
            }
            for i in range(5)
        ]
        
        # Set budgets for all startups
        for startup in startups:
            await budget_monitor.set_budget_limit(
                startup_id=startup['id'],
                daily_limit=10.0,
                total_limit=50.0
            )
        
        # Simulate operations for each startup
        for startup in startups:
            # Track startup creation
            analytics.track_startup_creation(startup)
            
            # Simulate tasks
            task_count = np.random.randint(3, 8)  # 3-7 tasks per startup
            
            for task_i in range(task_count):
                provider_name = np.random.choice(['openai', 'anthropic', 'perplexity'])
                
                # Mock task execution
                result = MockProviderResult(
                    success=np.random.random() > 0.1,  # 90% success rate
                    cost=np.random.uniform(0.05, 0.25),
                    tokens_used=np.random.randint(50, 200)
                )
                
                # Record spending
                await budget_monitor.record_spending(
                    startup_id=startup['id'],
                    provider=provider_name,
                    task_id=f"{startup['id']}-task-{task_i+1}",
                    cost=result.cost,
                    tokens_used=result.tokens_used,
                    task_type='development',
                    success=result.success
                )
                
                # Track performance
                metrics_data = {
                    'timestamp': datetime.now().isoformat(),
                    'memory_usage_mb': np.random.uniform(1000, 3000),
                    'cpu_percent': np.random.uniform(20, 80),
                    'concurrent_startups': len(startups),
                    'api_call_count': task_i + 1,
                    'error_count': 0 if result.success else 1,
                    'response_time_ms': np.random.uniform(200, 2000)
                }
                analytics.track_performance_metric(metrics_data)
        
        # Complete some startups
        for i, startup in enumerate(startups[:3]):  # Complete first 3
            completion_data = startup.copy()
            completion_data.update({
                'completed_at': datetime.now().isoformat(),
                'status': 'completed',
                'duration_minutes': np.random.uniform(30, 90),
                'success_score': np.random.uniform(0.7, 1.0)
            })
            analytics.track_startup_creation(completion_data)
        
        # Generate comprehensive analytics report
        report = analytics.generate_report(format='json')
        
        # Verify multi-startup aggregation
        assert report['total_startups'] == 5
        assert len(report['most_successful_industries']) > 0
        
        # Check global budget status
        global_budget = await budget_monitor.get_global_budget_status()
        
        assert global_budget['active_startups'] == 5
        assert global_budget['current_spending']['total'] > 0
        assert len(global_budget['provider_breakdown']) > 0
        
        # Verify industry analysis
        if 'roi_analysis' in report and report['roi_analysis']:
            roi = report['roi_analysis']
            assert roi['total_startups_analyzed'] == 5
            assert roi['total_api_costs'] > 0
    
    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self, integrated_system):
        """Test detection of performance degradation through analytics"""
        analytics = integrated_system['analytics']
        health_monitor = integrated_system['health']
        providers = integrated_system['providers']
        
        # Start with good performance
        good_performance_metrics = []
        for i in range(10):
            metrics_data = {
                'timestamp': (datetime.now() - timedelta(minutes=i)).isoformat(),
                'memory_usage_mb': 1200 + np.random.uniform(-100, 100),
                'cpu_percent': 30 + np.random.uniform(-5, 5),
                'concurrent_startups': 2,
                'api_call_count': 10,
                'error_count': 0,
                'response_time_ms': 800 + np.random.uniform(-100, 100)
            }
            analytics.track_performance_metric(metrics_data)
            good_performance_metrics.append(metrics_data)
        
        # Simulate performance degradation
        degraded_performance_metrics = []
        for i in range(10):
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'memory_usage_mb': 3500 + np.random.uniform(-200, 200),  # Higher memory
                'cpu_percent': 75 + np.random.uniform(-5, 5),  # Higher CPU
                'concurrent_startups': 3,
                'api_call_count': 15,
                'error_count': np.random.randint(1, 3),  # More errors
                'response_time_ms': 2500 + np.random.uniform(-200, 200)  # Slower response
            }
            analytics.track_performance_metric(metrics_data)
            degraded_performance_metrics.append(metrics_data)
            
            # Small delay to simulate real-time
            await asyncio.sleep(0.01)
        
        # Analyze performance trends
        trends = analytics.performance_analyzer.analyze_trends(days=1)
        bottlenecks = analytics.performance_analyzer.identify_bottlenecks()
        
        # Should detect degradation
        assert len(bottlenecks) > 0
        
        # Check for performance-related bottlenecks
        performance_issues = [
            b for b in bottlenecks 
            if b['type'] in ['memory_usage', 'cpu_usage', 'completion_time']
        ]
        assert len(performance_issues) > 0
        
        # Verify trend detection
        if 'memory_trend' in trends:
            assert trends['memory_trend'] in ['degrading', 'stable']  # Should not be improving
        
        # Get real-time metrics
        real_time = analytics.get_real_time_metrics()
        
        # Should show current degraded state
        if 'resource_usage' in real_time and 'recent' in real_time['resource_usage']:
            recent_usage = real_time['resource_usage']['recent']
            assert recent_usage['avg_memory_usage_mb'] > 3000  # Should show high memory
            assert recent_usage['avg_cpu_percent'] > 60  # Should show high CPU
    
    @pytest.mark.asyncio
    async def test_cost_optimization_recommendations(self, integrated_system):
        """Test cost optimization recommendations based on analytics"""
        analytics = integrated_system['analytics']
        budget_monitor = integrated_system['budget']
        providers = integrated_system['providers']
        
        # Simulate expensive operations
        expensive_startups = []
        for i in range(3):
            startup_id = f'expensive-startup-{i+1}'
            
            # Set budget
            await budget_monitor.set_budget_limit(
                startup_id=startup_id,
                daily_limit=20.0,
                total_limit=100.0
            )
            
            # Create high-cost scenario
            startup_data = {
                'id': startup_id,
                'name': f'Expensive Startup {i+1}',
                'industry': 'CostlyTech',
                'category': 'Enterprise',
                'created_at': (datetime.now() - timedelta(hours=i+1)).isoformat(),
                'completed_at': datetime.now().isoformat(),
                'status': 'completed',
                'duration_minutes': 120 + i*30,  # Long duration
            }
            
            # Track expensive operations
            total_cost = 0
            for task_i in range(8):  # Many tasks
                cost = np.random.uniform(0.8, 1.5)  # High cost per task
                total_cost += cost
                
                await budget_monitor.record_spending(
                    startup_id=startup_id,
                    provider='openai',  # Expensive provider
                    task_id=f'{startup_id}-task-{task_i+1}',
                    cost=cost,
                    tokens_used=np.random.randint(800, 1500),
                    task_type='code_generation',
                    success=True
                )
            
            startup_data['api_costs'] = {'openai': total_cost}
            startup_data['success_score'] = 0.9  # Good quality but expensive
            
            analytics.track_startup_creation(startup_data)
            expensive_startups.append(startup_data)
        
        # Generate business intelligence report
        report = analytics.bi_engine.generate_comprehensive_report()
        
        # Should have high cost per startup
        assert report.cost_per_startup > 5.0  # Should be expensive
        
        # Get optimization recommendations
        recommendations = analytics.bi_engine.generate_optimization_recommendations()
        
        # Should include cost optimization recommendations
        cost_recommendations = [
            r for r in recommendations 
            if 'cost' in r['title'].lower() or 'efficiency' in r['title'].lower()
        ]
        
        assert len(cost_recommendations) > 0
        
        # Should recommend performance improvements for high duration
        performance_recommendations = [
            r for r in recommendations 
            if 'time' in r['title'].lower() or 'performance' in r['title'].lower()
        ]
        
        assert len(performance_recommendations) > 0
        
        # Verify ROI analysis shows room for improvement
        roi_analysis = analytics.bi_engine.generate_roi_analysis()
        assert roi_analysis['avg_api_cost_per_startup'] > 3.0  # High cost
        assert roi_analysis['roi_percentage'] > 0  # But still profitable
    
    @pytest.mark.asyncio
    async def test_real_time_dashboard_data(self, integrated_system):
        """Test real-time dashboard data integration"""
        analytics = integrated_system['analytics']
        health_monitor = integrated_system['health']
        budget_monitor = integrated_system['budget']
        
        # Start health monitoring
        await health_monitor.start_monitoring()
        
        # Set up multiple startups with budgets
        startup_ids = ['dashboard-test-001', 'dashboard-test-002', 'dashboard-test-003']
        
        for startup_id in startup_ids:
            await budget_monitor.set_budget_limit(
                startup_id=startup_id,
                daily_limit=15.0,
                total_limit=75.0
            )
            
            # Create and track startup
            startup_data = {
                'id': startup_id,
                'name': f'Dashboard Test {startup_id}',
                'industry': 'DashboardTech',
                'created_at': datetime.now().isoformat(),
                'status': 'running'
            }
            analytics.track_startup_creation(startup_data)
        
        # Let monitoring run briefly
        await asyncio.sleep(0.2)
        
        # Simulate ongoing operations
        for i in range(5):
            for startup_id in startup_ids:
                # Record spending
                await budget_monitor.record_spending(
                    startup_id=startup_id,
                    provider=np.random.choice(['openai', 'anthropic', 'perplexity']),
                    task_id=f'{startup_id}-rt-task-{i+1}',
                    cost=np.random.uniform(0.5, 1.5),
                    tokens_used=np.random.randint(200, 800),
                    task_type='development',
                    success=np.random.random() > 0.1
                )
                
                # Track performance
                metrics_data = {
                    'timestamp': datetime.now().isoformat(),
                    'memory_usage_mb': np.random.uniform(1500, 2500),
                    'cpu_percent': np.random.uniform(40, 70),
                    'concurrent_startups': len(startup_ids),
                    'api_call_count': (i+1) * len(startup_ids),
                    'error_count': np.random.randint(0, 2),
                    'response_time_ms': np.random.uniform(500, 1500)
                }
                analytics.track_performance_metric(metrics_data)
        
        # Get comprehensive dashboard data
        dashboard_data = {
            'analytics': analytics.get_real_time_metrics(),
            'health': await health_monitor.get_health_summary(),
            'budget': await budget_monitor.get_global_budget_status(),
            'individual_budgets': {}
        }
        
        # Get individual budget statuses
        for startup_id in startup_ids:
            dashboard_data['individual_budgets'][startup_id] = await budget_monitor.get_budget_status(startup_id)
        
        # Verify dashboard data structure
        assert 'analytics' in dashboard_data
        assert 'health' in dashboard_data
        assert 'budget' in dashboard_data
        assert 'individual_budgets' in dashboard_data
        
        # Verify analytics data
        analytics_data = dashboard_data['analytics']
        assert 'performance' in analytics_data
        assert 'resource_usage' in analytics_data
        assert 'bottlenecks' in analytics_data
        
        # Verify health data
        health_data = dashboard_data['health']
        assert 'overall_status' in health_data
        assert 'provider_counts' in health_data
        assert health_data['monitoring'] is True
        
        # Verify budget data
        budget_data = dashboard_data['budget']
        assert 'current_spending' in budget_data
        assert 'active_startups' in budget_data
        assert budget_data['active_startups'] == len(startup_ids)
        
        # Verify individual budget statuses
        for startup_id in startup_ids:
            individual_budget = dashboard_data['individual_budgets'][startup_id]
            assert individual_budget['startup_id'] == startup_id
            assert 'current_spending' in individual_budget
            assert 'utilization' in individual_budget
        
        # Stop monitoring
        await health_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_analytics_data_persistence(self, integrated_system):
        """Test analytics data persistence across system restarts"""
        analytics = integrated_system['analytics']
        budget_monitor = integrated_system['budget']
        
        # Create initial data
        startup_data = {
            'id': 'persistence-test-001',
            'name': 'Persistence Test Startup',
            'industry': 'PersistenceTech',
            'created_at': datetime.now().isoformat(),
            'status': 'completed',
            'completed_at': (datetime.now() + timedelta(hours=1)).isoformat(),
            'duration_minutes': 60.0,
            'success_score': 0.95
        }
        
        # Track data
        analytics.track_startup_creation(startup_data)
        
        # Record some spending
        await budget_monitor.record_spending(
            startup_id='persistence-test-001',
            provider='openai',
            task_id='persistence-task-001',
            cost=2.5,
            tokens_used=500,
            task_type='test',
            success=True
        )
        
        # Add performance metrics
        for i in range(5):
            metrics_data = {
                'timestamp': (datetime.now() - timedelta(minutes=i)).isoformat(),
                'memory_usage_mb': 1800,
                'cpu_percent': 50,
                'concurrent_startups': 1,
                'api_call_count': 5,
                'error_count': 0,
                'response_time_ms': 1000
            }
            analytics.track_performance_metric(metrics_data)
        
        # Get initial report
        initial_report = analytics.generate_report(format='json')
        
        # Simulate system restart by creating new engine with same DB
        new_analytics = AnalyticsEngine(analytics.db.db_path)
        
        # Get report from new engine
        persistent_report = new_analytics.generate_report(format='json')
        
        # Data should be identical
        assert persistent_report['total_startups'] == initial_report['total_startups']
        assert abs(persistent_report['success_rate'] - initial_report['success_rate']) < 0.01
        assert abs(persistent_report['avg_creation_time'] - initial_report['avg_creation_time']) < 0.1
        
        # Verify specific startup data persisted
        startups_df = new_analytics.db.get_startups_dataframe()
        persistence_startup = startups_df[startups_df['id'] == 'persistence-test-001']
        
        assert len(persistence_startup) == 1
        assert float(persistence_startup.iloc[0]['duration_minutes']) == 60.0
        assert float(persistence_startup.iloc[0]['success_score']) == 0.95


class TestAnalyticsReporting:
    """Test comprehensive analytics reporting features"""
    
    @pytest.fixture
    def temp_db_path(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            yield Path(f.name)
            try:
                Path(f.name).unlink()
            except FileNotFoundError:
                pass
    
    @pytest.fixture
    def populated_analytics(self, temp_db_path):
        """Create analytics engine with rich test data"""
        analytics = AnalyticsEngine(temp_db_path)
        
        # Create diverse startup data
        industries = ['FinTech', 'HealthTech', 'EdTech', 'PropTech', 'RetailTech']
        
        for i in range(20):
            industry = industries[i % len(industries)]
            
            # Vary success patterns by industry
            if industry == 'FinTech':
                success_prob = 0.9
                avg_duration = 35
            elif industry == 'HealthTech':
                success_prob = 0.85
                avg_duration = 50
            else:
                success_prob = 0.75
                avg_duration = 40
            
            is_successful = np.random.random() < success_prob
            
            startup_data = {
                'id': f'report-startup-{i+1:03d}',
                'name': f'{industry} Report Startup {i+1}',
                'industry': industry,
                'category': 'B2B SaaS',
                'created_at': (datetime.now() - timedelta(days=np.random.randint(1, 30))).isoformat(),
                'status': 'completed' if is_successful else 'failed',
                'duration_minutes': avg_duration + np.random.uniform(-10, 10) if is_successful else None,
                'api_costs': {
                    'openai': np.random.uniform(0.5, 2.0),
                    'anthropic': np.random.uniform(0.3, 1.5),
                    'perplexity': np.random.uniform(0.1, 0.8)
                } if is_successful else None,
                'success_score': np.random.uniform(0.7, 1.0) if is_successful else None
            }
            
            if is_successful:
                startup_data['completed_at'] = (
                    datetime.fromisoformat(startup_data['created_at']) + 
                    timedelta(minutes=startup_data['duration_minutes'])
                ).isoformat()
            
            analytics.track_startup_creation(startup_data)
        
        # Add performance metrics
        for i in range(100):
            metrics_data = {
                'timestamp': (datetime.now() - timedelta(hours=np.random.randint(0, 72))).isoformat(),
                'memory_usage_mb': np.random.uniform(1200, 4000),
                'cpu_percent': np.random.uniform(20, 90),
                'concurrent_startups': np.random.randint(0, 8),
                'api_call_count': np.random.randint(5, 50),
                'error_count': np.random.randint(0, 5),
                'response_time_ms': np.random.uniform(300, 3000)
            }
            analytics.track_performance_metric(metrics_data)
        
        return analytics
    
    def test_comprehensive_json_report(self, populated_analytics):
        """Test comprehensive JSON report generation"""
        report = populated_analytics.generate_report(format='json')
        
        # Verify all required sections
        required_fields = [
            'total_startups', 'success_rate', 'avg_creation_time', 'cost_per_startup',
            'most_successful_industries', 'common_bottlenecks', 
            'optimization_recommendations', 'roi_analysis'
        ]
        
        for field in required_fields:
            assert field in report, f"Missing required field: {field}"
        
        # Verify data quality
        assert report['total_startups'] == 20
        assert 0 <= report['success_rate'] <= 1
        assert report['avg_creation_time'] > 0
        assert report['cost_per_startup'] > 0
        
        # Verify industry analysis
        assert len(report['most_successful_industries']) > 0
        assert all(isinstance(industry, str) for industry in report['most_successful_industries'])
        
        # Verify ROI analysis
        roi = report['roi_analysis']
        assert 'total_startups_analyzed' in roi
        assert 'cost_savings' in roi
        assert 'roi_percentage' in roi
        assert roi['total_startups_analyzed'] == 20
    
    def test_summary_report_formatting(self, populated_analytics):
        """Test human-readable summary report"""
        summary = populated_analytics.generate_report(format='summary')
        
        # Verify summary structure
        assert isinstance(summary, str)
        assert len(summary) > 100  # Should be substantial
        
        # Check for key sections
        assert '📊 Startup Factory Analytics Report' in summary
        assert 'Key Performance Metrics' in summary
        assert 'Top Performing Industries' in summary
        assert 'Common Bottlenecks' in summary
        assert 'Top Recommendations' in summary
        assert 'ROI Analysis' in summary
        
        # Check for data formatting
        assert '$' in summary  # Should contain cost information
        assert '%' in summary  # Should contain percentage information
        
        # Verify the summary contains actual data
        assert 'Total Startups: 20' in summary or '20' in summary
    
    def test_real_time_metrics_completeness(self, populated_analytics):
        """Test real-time metrics data completeness"""
        metrics = populated_analytics.get_real_time_metrics()
        
        # Verify structure
        assert 'timestamp' in metrics
        assert 'performance' in metrics
        assert 'resource_usage' in metrics
        assert 'bottlenecks' in metrics
        assert 'trends' in metrics
        
        # Verify timestamp format
        timestamp = datetime.fromisoformat(metrics['timestamp'])
        assert isinstance(timestamp, datetime)
        
        # Verify performance metrics
        performance = metrics['performance']
        performance_fields = [
            'total_startups', 'completed_startups', 'failed_startups', 
            'success_rate'
        ]
        for field in performance_fields:
            assert field in performance
        
        # Verify resource usage
        resource_usage = metrics['resource_usage']
        if 'overall' in resource_usage:
            resource_fields = [
                'avg_memory_usage_mb', 'max_memory_usage_mb',
                'avg_cpu_percent', 'max_cpu_percent'
            ]
            for field in resource_fields:
                assert field in resource_usage['overall']
        
        # Verify bottlenecks
        bottlenecks = metrics['bottlenecks']
        assert isinstance(bottlenecks, list)
        
        for bottleneck in bottlenecks:
            assert 'type' in bottleneck
            assert 'severity' in bottleneck
            assert 'description' in bottleneck
            assert 'recommendation' in bottleneck
    
    def test_industry_performance_analysis(self, populated_analytics):
        """Test detailed industry performance analysis"""
        industry_analysis = populated_analytics.bi_engine.analyze_industry_success_patterns()
        
        # Verify structure
        assert 'industry_performance' in industry_analysis
        assert 'most_successful_industries' in industry_analysis
        assert 'least_successful_industries' in industry_analysis
        
        # Verify industry performance data
        industry_perf = industry_analysis['industry_performance']
        
        # Should have data for multiple industries
        assert len(industry_perf) >= 3  # We created data for 5 industries
        
        # Check each industry's metrics
        for industry, metrics in industry_perf.items():
            assert 'success_rate' in metrics
            assert 'startup_count' in metrics
            assert 0 <= metrics['success_rate'] <= 1
            assert metrics['startup_count'] > 0
            
            if 'avg_duration_minutes' in metrics and metrics['avg_duration_minutes']:
                assert metrics['avg_duration_minutes'] > 0
        
        # Verify rankings
        most_successful = industry_analysis['most_successful_industries']
        least_successful = industry_analysis['least_successful_industries']
        
        assert len(most_successful) <= 3
        assert len(least_successful) <= 3
        assert all(isinstance(industry, str) for industry in most_successful)
        assert all(isinstance(industry, str) for industry in least_successful)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])