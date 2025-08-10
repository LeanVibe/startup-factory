#!/usr/bin/env python3
"""
Standalone validation script for analytics and monitoring components
"""

import asyncio
import sys
from pathlib import Path
import tempfile

# Add tools to path
sys.path.append(str(Path(__file__).parent / "tools"))

from analytics_engine import AnalyticsEngine
from budget_monitor import BudgetMonitor
from datetime import datetime, timedelta

async def test_analytics_engine():
    """Test analytics engine basic functionality"""
    print("🔍 Testing Analytics Engine...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    try:
        # Create analytics engine
        engine = AnalyticsEngine(db_path)
        
        # Test startup tracking
        startup_data = {
            'id': 'validation-test-001',
            'name': 'Validation Test Startup',
            'industry': 'TestTech',
            'category': 'Validation',
            'created_at': datetime.now().isoformat(),
            'completed_at': (datetime.now() + timedelta(hours=1)).isoformat(),
            'status': 'completed',
            'duration_minutes': 60.0,
            'api_costs': {'openai': 0.75, 'anthropic': 0.45},
            'success_score': 0.92
        }
        
        engine.track_startup_creation(startup_data)
        print("✅ Startup tracking successful")
        
        # Test performance tracking
        metrics_data = {
            'timestamp': datetime.now().isoformat(),
            'memory_usage_mb': 2048,
            'cpu_percent': 65,
            'concurrent_startups': 1,
            'api_call_count': 10,
            'error_count': 0,
            'response_time_ms': 1200
        }
        
        engine.track_performance_metric(metrics_data)
        print("✅ Performance tracking successful")
        
        # Test report generation
        report = engine.generate_report(format='json')
        assert report['total_startups'] == 1
        assert report['success_rate'] == 1.0
        print("✅ Report generation successful")
        
        # Test real-time metrics
        metrics = engine.get_real_time_metrics()
        assert 'performance' in metrics
        assert 'resource_usage' in metrics
        print("✅ Real-time metrics successful")
        
        print("✅ Analytics Engine - All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Analytics Engine test failed: {e}")
        return False
    finally:
        # Cleanup
        try:
            db_path.unlink()
        except FileNotFoundError:
            pass


async def test_budget_monitor():
    """Test budget monitor basic functionality"""
    print("\n💰 Testing Budget Monitor...")
    
    try:
        # Create budget monitor
        monitor = BudgetMonitor()
        
        # Test budget limit setting
        await monitor.set_budget_limit(
            startup_id='validation-test-001',
            daily_limit=10.0,
            weekly_limit=50.0,
            monthly_limit=150.0,
            total_limit=500.0
        )
        print("✅ Budget limit setting successful")
        
        # Test spending recording
        await monitor.record_spending(
            startup_id='validation-test-001',
            provider='openai',
            task_id='validation-task-001',
            cost=2.5,
            tokens_used=500,
            task_type='validation',
            success=True
        )
        print("✅ Spending recording successful")
        
        # Test budget status
        status = await monitor.get_budget_status('validation-test-001')
        assert status['startup_id'] == 'validation-test-001'
        assert status['current_spending']['total'] == 2.5
        print("✅ Budget status retrieval successful")
        
        # Test global budget status
        global_status = await monitor.get_global_budget_status()
        assert global_status['active_startups'] == 1
        assert global_status['current_spending']['total'] == 2.5
        print("✅ Global budget status successful")
        
        # Test can proceed check
        can_proceed = await monitor.can_proceed_with_task('validation-test-001', 5.0)
        assert can_proceed is True  # Should be within daily limit
        print("✅ Task proceed validation successful")
        
        print("✅ Budget Monitor - All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Budget Monitor test failed: {e}")
        return False


async def test_integration():
    """Test integration between components"""
    print("\n🔗 Testing Integration...")
    
    try:
        # Create temporary database for analytics
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)
        
        # Create components
        analytics = AnalyticsEngine(db_path)
        budget_monitor = BudgetMonitor()
        
        # Set up budget
        await budget_monitor.set_budget_limit('integration-test', daily_limit=20.0, total_limit=100.0)
        
        # Simulate startup workflow
        startup_data = {
            'id': 'integration-test',
            'name': 'Integration Test Startup',
            'industry': 'IntegrationTech',
            'created_at': datetime.now().isoformat(),
            'status': 'in_progress'
        }
        
        analytics.track_startup_creation(startup_data)
        
        # Simulate multiple operations
        total_cost = 0.0
        for i in range(5):
            cost = 1.5  # $1.50 per operation
            total_cost += cost
            
            # Record spending in budget
            await budget_monitor.record_spending(
                startup_id='integration-test',
                provider='openai',
                task_id=f'integration-task-{i+1}',
                cost=cost,
                tokens_used=300,
                task_type='development',
                success=True
            )
            
            # Track performance
            analytics.track_performance_metric({
                'timestamp': datetime.now().isoformat(),
                'memory_usage_mb': 1500 + i*100,
                'cpu_percent': 50 + i*5,
                'concurrent_startups': 1,
                'api_call_count': i+1,
                'error_count': 0,
                'response_time_ms': 1000 + i*100
            })
        
        # Complete startup
        completion_data = startup_data.copy()
        completion_data.update({
            'completed_at': datetime.now().isoformat(),
            'status': 'completed',
            'duration_minutes': 45.0,
            'success_score': 0.95
        })
        
        analytics.track_startup_creation(completion_data)
        
        # Verify integration
        analytics_report = analytics.generate_report(format='json')
        budget_status = await budget_monitor.get_budget_status('integration-test')
        
        assert analytics_report['total_startups'] == 1
        assert budget_status['current_spending']['total'] == total_cost
        assert budget_status['current_spending']['total'] == 7.5  # 5 * $1.50
        
        print("✅ Integration test successful")
        print(f"   - Analytics tracked {analytics_report['total_startups']} startup")
        print(f"   - Budget tracked ${budget_status['current_spending']['total']} spending")
        
        # Cleanup
        try:
            db_path.unlink()
        except FileNotFoundError:
            pass
        
        print("✅ Integration - All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


async def main():
    """Run all validation tests"""
    print("🚀 Starting Analytics and Monitoring Validation Tests\n")
    
    tests = [
        test_analytics_engine(),
        test_budget_monitor(),
        test_integration()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    passed = sum(1 for result in results if result is True)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validation tests passed successfully!")
        return True
    else:
        print("❌ Some tests failed - check output above")
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   Test {i+1} failed with exception: {result}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)