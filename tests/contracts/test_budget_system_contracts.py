#!/usr/bin/env python3
"""
Budget System Contract Tests

Tests for API contracts and data consistency of the budget monitoring system.
Ensures that the budget system maintains consistent behavior and data integrity
across all operations and scenarios.

Contract Categories:
- API Method Contracts
- Data Model Consistency
- State Transition Contracts
- Error Handling Contracts
- Concurrency Contracts
"""

import asyncio
import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch
import copy

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from budget_monitor import (
    BudgetMonitor, BudgetLimit, BudgetAlert, SpendingRecord,
    BudgetExceededError, BudgetWarningError
)
from core_types import generate_task_id, TaskType


@pytest.fixture(scope="function")
def contract_monitor():
    """Create a fresh budget monitor for contract testing"""
    return BudgetMonitor()


@pytest.fixture
def sample_budget_data():
    """Sample budget configuration data for testing"""
    return {
        "startup_id": "contract_test_startup",
        "daily_limit": 100.0,
        "weekly_limit": 500.0,
        "monthly_limit": 2000.0,
        "total_limit": 15000.0,
        "warning_threshold": 0.8,
        "hard_stop": True
    }


@pytest.fixture
def sample_spending_data():
    """Sample spending record data for testing"""
    return {
        "startup_id": "contract_test_startup",
        "provider": "openai",
        "task_id": generate_task_id(),
        "cost": 10.50,
        "tokens_used": 1000,
        "task_type": "research",
        "success": True
    }


class TestBudgetSystemAPIContracts:
    """Test API method contracts and return value consistency"""
    
    @pytest.mark.asyncio
    async def test_set_budget_limit_contract(self, contract_monitor, sample_budget_data):
        """Test that set_budget_limit maintains consistent contract"""
        monitor = contract_monitor
        
        # Test with all parameters
        await monitor.set_budget_limit(**sample_budget_data)
        
        # Verify budget limit was stored correctly
        stored_limit = monitor.budget_limits[sample_budget_data["startup_id"]]
        
        # Contract assertions
        assert isinstance(stored_limit, BudgetLimit)
        assert stored_limit.startup_id == sample_budget_data["startup_id"]
        assert stored_limit.daily_limit == sample_budget_data["daily_limit"]
        assert stored_limit.weekly_limit == sample_budget_data["weekly_limit"]
        assert stored_limit.monthly_limit == sample_budget_data["monthly_limit"]
        assert stored_limit.total_limit == sample_budget_data["total_limit"]
        assert stored_limit.warning_threshold == sample_budget_data["warning_threshold"]
        assert stored_limit.hard_stop == sample_budget_data["hard_stop"]
        assert isinstance(stored_limit.created_at, datetime)
        
        # Test with minimal parameters (using defaults)
        minimal_startup = "minimal_test"
        await monitor.set_budget_limit(minimal_startup)
        
        minimal_limit = monitor.budget_limits[minimal_startup]
        assert minimal_limit.startup_id == minimal_startup
        assert minimal_limit.daily_limit == 50.0  # Default value
        assert minimal_limit.warning_threshold == 0.8  # Default value
        assert minimal_limit.hard_stop is True  # Default value
        
        # Test parameter validation
        with pytest.raises((ValueError, TypeError)):
            await monitor.set_budget_limit("", daily_limit=-100.0)  # Invalid parameters
    
    @pytest.mark.asyncio
    async def test_record_spending_contract(self, contract_monitor, sample_budget_data, sample_spending_data):
        """Test that record_spending maintains consistent contract"""
        monitor = contract_monitor
        
        # Set up budget
        await monitor.set_budget_limit(**sample_budget_data)
        
        # Test normal spending record
        initial_count = len(monitor.spending_records)
        
        await monitor.record_spending(**sample_spending_data)
        
        # Contract assertions
        assert len(monitor.spending_records) == initial_count + 1
        
        record = monitor.spending_records[-1]
        assert isinstance(record, SpendingRecord)
        assert record.startup_id == sample_spending_data["startup_id"]
        assert record.provider == sample_spending_data["provider"]
        assert record.task_id == sample_spending_data["task_id"]
        assert record.cost == sample_spending_data["cost"]
        assert record.tokens_used == sample_spending_data["tokens_used"]
        assert record.task_type == sample_spending_data["task_type"]
        assert record.success == sample_spending_data["success"]
        assert isinstance(record.timestamp, datetime)
        
        # Test failed transaction
        failed_data = sample_spending_data.copy()
        failed_data["task_id"] = generate_task_id()
        failed_data["success"] = False
        
        await monitor.record_spending(**failed_data)
        
        failed_record = monitor.spending_records[-1]
        assert failed_record.success is False
        
        # Verify failed transactions don't affect budget calculations
        total_spend = await monitor._get_total_spending(sample_spending_data["startup_id"])
        assert total_spend == sample_spending_data["cost"]  # Only successful transaction
    
    @pytest.mark.asyncio
    async def test_get_budget_status_contract(self, contract_monitor, sample_budget_data):
        """Test that get_budget_status returns consistent structure"""
        monitor = contract_monitor
        startup_id = sample_budget_data["startup_id"]
        
        # Test with no budget limits set
        status_no_limits = await monitor.get_budget_status("nonexistent_startup")
        
        # Contract assertions for no limits
        assert isinstance(status_no_limits, dict)
        assert status_no_limits["startup_id"] == "nonexistent_startup"
        assert status_no_limits["has_limits"] is False
        assert "total_spent" in status_no_limits
        assert isinstance(status_no_limits["total_spent"], (int, float))
        
        # Test with budget limits set
        await monitor.set_budget_limit(**sample_budget_data)
        
        # Add some spending
        await monitor.record_spending(
            startup_id=startup_id,
            provider="openai",
            task_id=generate_task_id(),
            cost=50.0,
            tokens_used=1000,
            task_type="research"
        )
        
        status_with_limits = await monitor.get_budget_status(startup_id)
        
        # Contract assertions for budget status
        assert isinstance(status_with_limits, dict)
        assert status_with_limits["startup_id"] == startup_id
        assert status_with_limits["has_limits"] is True
        
        # Verify required structure
        required_keys = ["limits", "current_spending", "utilization", "warning_threshold", "hard_stop"]
        for key in required_keys:
            assert key in status_with_limits
        
        # Verify limits structure
        limits = status_with_limits["limits"]
        assert isinstance(limits, dict)
        for limit_type in ["daily", "weekly", "monthly", "total"]:
            assert limit_type in limits
            assert isinstance(limits[limit_type], (int, float))
        
        # Verify current_spending structure
        current_spending = status_with_limits["current_spending"]
        assert isinstance(current_spending, dict)
        for period in ["daily", "weekly", "monthly", "total"]:
            assert period in current_spending
            assert isinstance(current_spending[period], (int, float))
        
        # Verify utilization structure
        utilization = status_with_limits["utilization"]
        assert isinstance(utilization, dict)
        for period in ["daily", "weekly", "monthly", "total"]:
            assert period in utilization
            assert isinstance(utilization[period], (int, float))
            assert 0 <= utilization[period] <= 2  # Allow some buffer over 100%
    
    @pytest.mark.asyncio
    async def test_can_proceed_with_task_contract(self, contract_monitor, sample_budget_data):
        """Test that can_proceed_with_task returns consistent boolean results"""
        monitor = contract_monitor
        startup_id = sample_budget_data["startup_id"]
        
        # Test with no budget limits (should always return True)
        result_no_limits = await monitor.can_proceed_with_task("nonexistent", 1000.0)
        assert isinstance(result_no_limits, bool)
        assert result_no_limits is True
        
        # Test with budget limits
        await monitor.set_budget_limit(**sample_budget_data)
        
        # Test with cost within limits
        result_within = await monitor.can_proceed_with_task(startup_id, 50.0)
        assert isinstance(result_within, bool)
        assert result_within is True
        
        # Test with cost exceeding limits
        result_exceeding = await monitor.can_proceed_with_task(startup_id, 150.0)  # Exceeds daily limit
        assert isinstance(result_exceeding, bool)
        assert result_exceeding is False
        
        # Test edge cases
        result_zero = await monitor.can_proceed_with_task(startup_id, 0.0)
        assert isinstance(result_zero, bool)
        assert result_zero is True
        
        result_exact = await monitor.can_proceed_with_task(startup_id, 100.0)  # Exactly at limit
        assert isinstance(result_exact, bool)
        assert result_exact is True
    
    @pytest.mark.asyncio
    async def test_get_spending_summary_contract(self, contract_monitor, sample_budget_data):
        """Test that get_spending_summary returns consistent structure"""
        monitor = contract_monitor
        startup_id = sample_budget_data["startup_id"]
        
        await monitor.set_budget_limit(**sample_budget_data)
        
        # Test with no spending
        empty_summary = await monitor.get_spending_summary(startup_id)
        
        # Contract assertions for empty summary
        assert isinstance(empty_summary, dict)
        required_keys = ["total", "daily", "weekly", "monthly", "by_provider"]
        for key in required_keys:
            assert key in empty_summary
            if key == "by_provider":
                assert isinstance(empty_summary[key], dict)
            else:
                assert isinstance(empty_summary[key], (int, float))
                assert empty_summary[key] == 0.0
        
        # Set higher budget limit to avoid exceeding during test
        await monitor.set_budget_limit(startup_id, daily_limit=200.0, weekly_limit=1000.0, monthly_limit=4000.0)
        
        # Add spending from different providers
        providers = ["openai", "anthropic", "perplexity"]
        costs = [25.0, 35.0, 40.0]
        
        for provider, cost in zip(providers, costs):
            await monitor.record_spending(
                startup_id=startup_id,
                provider=provider,
                task_id=generate_task_id(),
                cost=cost,
                tokens_used=1000,
                task_type="research"
            )
        
        summary_with_data = await monitor.get_spending_summary(startup_id)
        
        # Contract assertions for populated summary
        assert isinstance(summary_with_data, dict)
        assert summary_with_data["total"] == 100.0  # Sum of all costs
        
        # Verify provider breakdown
        by_provider = summary_with_data["by_provider"]
        assert isinstance(by_provider, dict)
        for provider, expected_cost in zip(providers, costs):
            assert provider in by_provider
            assert by_provider[provider] == expected_cost
    
    @pytest.mark.asyncio
    async def test_get_remaining_budget_contract(self, contract_monitor, sample_budget_data):
        """Test that get_remaining_budget returns consistent numeric results"""
        monitor = contract_monitor
        startup_id = sample_budget_data["startup_id"]
        
        # Test with no budget limits (should return infinity)
        remaining_no_limits = await monitor.get_remaining_budget("nonexistent")
        assert isinstance(remaining_no_limits, float)
        assert remaining_no_limits == float('inf')
        
        # Test with budget limits
        await monitor.set_budget_limit(**sample_budget_data)
        
        # Test with no spending
        remaining_full = await monitor.get_remaining_budget(startup_id)
        assert isinstance(remaining_full, float)
        assert remaining_full == sample_budget_data["daily_limit"]
        
        # Test with some spending
        spending_amount = 30.0
        await monitor.record_spending(
            startup_id=startup_id,
            provider="openai",
            task_id=generate_task_id(),
            cost=spending_amount,
            tokens_used=1000,
            task_type="research"
        )
        
        remaining_partial = await monitor.get_remaining_budget(startup_id)
        assert isinstance(remaining_partial, float)
        assert remaining_partial == sample_budget_data["daily_limit"] - spending_amount
        
        # Test with spending exceeding limit
        await monitor.record_spending(
            startup_id=startup_id,
            provider="openai",
            task_id=generate_task_id(),
            cost=80.0,
            tokens_used=1000,
            task_type="research",
            success=False  # Mark as failed to avoid budget exception
        )
        
        # Add successful spending that would exceed
        try:
            await monitor.record_spending(
                startup_id=startup_id,
                provider="openai", 
                task_id=generate_task_id(),
                cost=80.0,
                tokens_used=1000,
                task_type="research"
            )
        except BudgetExceededError:
            pass  # Expected for hard_stop budget
        
        remaining_over = await monitor.get_remaining_budget(startup_id)
        assert isinstance(remaining_over, float)
        assert remaining_over >= 0.0  # Should not go negative


class TestDataModelConsistency:
    """Test data model consistency and state integrity"""
    
    @pytest.mark.asyncio
    async def test_budget_limit_data_integrity(self, contract_monitor):
        """Test that BudgetLimit objects maintain data integrity"""
        monitor = contract_monitor
        
        # Create budget limit with specific values
        test_data = {
            "startup_id": "integrity_test",
            "daily_limit": 123.45,
            "weekly_limit": 678.90,
            "monthly_limit": 2345.67,
            "total_limit": 12345.67,
            "warning_threshold": 0.75,
            "hard_stop": False
        }
        
        await monitor.set_budget_limit(**test_data)
        
        # Retrieve and verify data integrity
        stored_limit = monitor.budget_limits[test_data["startup_id"]]
        
        # Test all fields maintain exact values
        assert stored_limit.startup_id == test_data["startup_id"]
        assert stored_limit.daily_limit == test_data["daily_limit"]
        assert stored_limit.weekly_limit == test_data["weekly_limit"]
        assert stored_limit.monthly_limit == test_data["monthly_limit"]
        assert stored_limit.total_limit == test_data["total_limit"]
        assert stored_limit.warning_threshold == test_data["warning_threshold"]
        assert stored_limit.hard_stop == test_data["hard_stop"]
        
        # Test timestamp precision
        creation_time = stored_limit.created_at
        assert isinstance(creation_time, datetime)
        assert creation_time <= datetime.utcnow()
        
        # Test that modifications don't affect stored data
        original_daily = stored_limit.daily_limit
        test_data["daily_limit"] = 999.99
        assert stored_limit.daily_limit == original_daily  # Should be unchanged
    
    @pytest.mark.asyncio
    async def test_spending_record_data_integrity(self, contract_monitor):
        """Test that SpendingRecord objects maintain data integrity"""
        monitor = contract_monitor
        startup_id = "spending_integrity_test"
        
        await monitor.set_budget_limit(startup_id, daily_limit=1000.0)
        
        # Test with precise decimal values
        precise_data = {
            "startup_id": startup_id,
            "provider": "test_provider",
            "task_id": "precise_task_123",
            "cost": 123.456789,  # High precision
            "tokens_used": 12345,
            "task_type": "precision_test",
            "success": True
        }
        
        await monitor.record_spending(**precise_data)
        
        # Verify data precision is maintained
        record = monitor.spending_records[-1]
        
        assert record.startup_id == precise_data["startup_id"]
        assert record.provider == precise_data["provider"]
        assert record.task_id == precise_data["task_id"]
        assert record.cost == precise_data["cost"]  # Exact precision
        assert record.tokens_used == precise_data["tokens_used"]
        assert record.task_type == precise_data["task_type"]
        assert record.success == precise_data["success"]
        
        # Test timestamp is reasonable
        record_time = record.timestamp
        assert isinstance(record_time, datetime)
        assert record_time <= datetime.utcnow()
        assert record_time >= datetime.utcnow() - timedelta(seconds=10)
    
    @pytest.mark.asyncio
    async def test_alert_data_consistency(self, contract_monitor):
        """Test that BudgetAlert objects maintain consistent data"""
        monitor = contract_monitor
        startup_id = "alert_consistency_test"
        
        # Set budget to trigger alerts
        await monitor.set_budget_limit(startup_id, daily_limit=50.0, warning_threshold=0.6)
        
        # Trigger warning alert
        await monitor.record_spending(startup_id, "openai", generate_task_id(), 35.0, 1000, "research")
        
        # Check alert data
        recent_alerts = await monitor.get_recent_alerts(hours=1)
        warning_alerts = [a for a in recent_alerts if a.alert_type == "warning"]
        
        assert len(warning_alerts) > 0
        
        alert = warning_alerts[0]
        assert isinstance(alert, BudgetAlert)
        assert alert.startup_id == startup_id
        assert alert.alert_type == "warning"
        assert isinstance(alert.message, str)
        assert len(alert.message) > 0
        assert isinstance(alert.current_spend, (int, float))
        assert alert.current_spend > 0
        assert isinstance(alert.limit_amount, (int, float))
        assert alert.limit_amount > 0
        assert isinstance(alert.percentage_used, (int, float))
        assert 0 <= alert.percentage_used <= 2  # Allow some buffer
        assert isinstance(alert.timestamp, datetime)


class TestStateTransitionContracts:
    """Test state transition consistency and invariants"""
    
    @pytest.mark.asyncio
    async def test_budget_state_transitions(self, contract_monitor):
        """Test that budget state transitions maintain consistency"""
        monitor = contract_monitor
        startup_id = "transition_test"
        
        # Initial state: no budget set
        initial_status = await monitor.get_budget_status(startup_id)
        assert initial_status["has_limits"] is False
        
        # Transition: set budget limits
        await monitor.set_budget_limit(startup_id, daily_limit=100.0)
        
        post_setup_status = await monitor.get_budget_status(startup_id)
        assert post_setup_status["has_limits"] is True
        assert post_setup_status["current_spending"]["total"] == 0.0
        
        # Transition: add spending
        spending_amount = 25.0
        await monitor.record_spending(startup_id, "openai", generate_task_id(), spending_amount, 1000, "research")
        
        post_spending_status = await monitor.get_budget_status(startup_id)
        assert post_spending_status["current_spending"]["total"] == spending_amount
        assert 0 < post_spending_status["utilization"]["daily"] < 1.0
        
        # Transition: approach warning threshold
        await monitor.record_spending(startup_id, "openai", generate_task_id(), 55.0, 1000, "research")  # Total: 80.0
        
        warning_status = await monitor.get_budget_status(startup_id)
        assert warning_status["utilization"]["daily"] >= 0.8  # Should trigger warning
        
        # Verify alerts were generated
        alerts = await monitor.get_recent_alerts()
        warning_alerts = [a for a in alerts if a.startup_id == startup_id and a.alert_type == "warning"]
        assert len(warning_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_state_consistency(self, contract_monitor):
        """Test that concurrent operations maintain state consistency"""
        monitor = contract_monitor
        startup_id = "concurrent_consistency_test"
        
        await monitor.set_budget_limit(startup_id, daily_limit=1000.0, weekly_limit=5000.0, monthly_limit=20000.0)
        
        # Create concurrent operations
        concurrent_operations = []
        for i in range(50):
            op = monitor.record_spending(
                startup_id=startup_id,
                provider="openai",
                task_id=f"concurrent_task_{i}",
                cost=10.0,
                tokens_used=1000,
                task_type="concurrent_test"
            )
            concurrent_operations.append(op)
        
        # Execute concurrently
        await asyncio.gather(*concurrent_operations)
        
        # Verify final state consistency
        final_status = await monitor.get_budget_status(startup_id)
        expected_total = 50 * 10.0  # 50 operations * $10 each
        
        assert abs(final_status["current_spending"]["total"] - expected_total) < 0.01
        
        # Verify record count matches
        startup_records = [r for r in monitor.spending_records if r.startup_id == startup_id]
        assert len(startup_records) == 50


class TestErrorHandlingContracts:
    """Test error handling consistency and contracts"""
    
    @pytest.mark.asyncio
    async def test_budget_exceeded_error_contract(self, contract_monitor):
        """Test that budget exceeded errors are consistent"""
        monitor = contract_monitor
        startup_id = "error_contract_test"
        
        # Set low budget with hard stop
        await monitor.set_budget_limit(startup_id, daily_limit=50.0, hard_stop=True)
        
        # Approach limit
        await monitor.record_spending(startup_id, "openai", generate_task_id(), 40.0, 1000, "research")
        
        # Exceed limit - should raise BudgetExceededError
        with pytest.raises(BudgetExceededError) as exc_info:
            await monitor.record_spending(startup_id, "openai", generate_task_id(), 20.0, 1000, "research")
        
        # Verify error properties
        error = exc_info.value
        assert isinstance(error, BudgetExceededError)
        assert startup_id in str(error)
        assert "limit exceeded" in str(error).lower() or "budget" in str(error).lower()
        
        # Verify system state after error
        post_error_status = await monitor.get_budget_status(startup_id)
        assert post_error_status["current_spending"]["total"] <= 50.0  # Should not exceed limit
        
        # Verify failed transaction was not recorded
        successful_records = [r for r in monitor.spending_records 
                            if r.startup_id == startup_id and r.success]
        total_successful_cost = sum(r.cost for r in successful_records)
        assert total_successful_cost <= 50.0
    
    @pytest.mark.asyncio
    async def test_soft_limit_warning_contract(self, contract_monitor):
        """Test that soft limit warnings maintain consistent behavior"""
        monitor = contract_monitor
        startup_id = "soft_limit_test"
        
        # Set budget with soft limit (hard_stop=False)
        await monitor.set_budget_limit(startup_id, daily_limit=50.0, hard_stop=False)
        
        # Exceed limit - should not raise error but create alert
        await monitor.record_spending(startup_id, "openai", generate_task_id(), 40.0, 1000, "research")
        await monitor.record_spending(startup_id, "openai", generate_task_id(), 20.0, 1000, "research")  # Total: 60.0
        
        # Should not have raised exception
        total_spend = await monitor._get_total_spending(startup_id)
        assert total_spend == 60.0  # Both transactions should have succeeded
        
        # Should have generated limit exceeded alert
        alerts = await monitor.get_recent_alerts()
        limit_alerts = [a for a in alerts 
                       if a.startup_id == startup_id and a.alert_type == "limit_exceeded"]
        assert len(limit_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_parameter_handling(self, contract_monitor):
        """Test consistent handling of invalid parameters"""
        monitor = contract_monitor
        
        # Test invalid budget limit parameters
        with pytest.raises((ValueError, TypeError)):
            await monitor.set_budget_limit("", daily_limit=-100.0)
        
        with pytest.raises((ValueError, TypeError)):
            await monitor.set_budget_limit("test", warning_threshold=1.5)  # > 1.0
        
        # Test invalid spending record parameters
        await monitor.set_budget_limit("valid_startup", daily_limit=100.0)
        
        with pytest.raises((ValueError, TypeError)):
            await monitor.record_spending("valid_startup", "", "task", 10.0, 1000, "research")  # Empty provider
        
        with pytest.raises((ValueError, TypeError)):
            await monitor.record_spending("valid_startup", "openai", "task", -10.0, 1000, "research")  # Negative cost


class TestConcurrencyContracts:
    """Test concurrency handling and thread safety contracts"""
    
    @pytest.mark.asyncio
    async def test_async_lock_consistency(self, contract_monitor):
        """Test that async locks maintain data consistency"""
        monitor = contract_monitor
        startup_id = "lock_test"
        
        await monitor.set_budget_limit(startup_id, daily_limit=1000.0)
        
        # Create operations that modify shared state
        async def modify_budget_state():
            # Multiple operations that could race
            await monitor.record_spending(startup_id, "openai", generate_task_id(), 1.0, 100, "test")
            await monitor.get_budget_status(startup_id)
            await monitor.can_proceed_with_task(startup_id, 5.0)
        
        # Execute many concurrent state-modifying operations
        concurrent_tasks = [modify_budget_state() for _ in range(100)]
        await asyncio.gather(*concurrent_tasks)
        
        # Verify final state is consistent
        final_status = await monitor.get_budget_status(startup_id)
        startup_records = [r for r in monitor.spending_records if r.startup_id == startup_id and r.success]
        
        # Should have exactly 100 records
        assert len(startup_records) == 100
        
        # Total spending should be exactly 100 * $1.00
        assert abs(final_status["current_spending"]["total"] - 100.0) < 0.01
    
    @pytest.mark.asyncio
    async def test_alert_callback_isolation(self, contract_monitor):
        """Test that alert callbacks don't interfere with each other"""
        monitor = contract_monitor
        startup_id = "callback_isolation_test"
        
        # Track callback executions
        callback1_calls = []
        callback2_calls = []
        
        def callback1(alert):
            callback1_calls.append(alert)
            # Simulate some processing time
            import time
            time.sleep(0.001)
        
        def callback2(alert):
            callback2_calls.append(alert)
            # Different processing
            import time
            time.sleep(0.002)
        
        monitor.register_alert_callback(callback1)
        monitor.register_alert_callback(callback2)
        
        # Set up to trigger alerts
        await monitor.set_budget_limit(startup_id, daily_limit=50.0, warning_threshold=0.5)
        
        # Trigger multiple alerts
        await monitor.record_spending(startup_id, "openai", generate_task_id(), 30.0, 1000, "research")  # Warning
        
        try:
            await monitor.record_spending(startup_id, "openai", generate_task_id(), 25.0, 1000, "research")  # Exceeded
        except BudgetExceededError:
            pass
        
        # Allow callbacks to complete
        await asyncio.sleep(0.1)
        
        # Both callbacks should have been called
        assert len(callback1_calls) > 0
        assert len(callback2_calls) > 0
        
        # Should have received same alerts
        assert len(callback1_calls) == len(callback2_calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])