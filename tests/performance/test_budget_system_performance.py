#!/usr/bin/env python3
"""
Budget System Performance Tests

Load testing and stress testing for the budget monitoring system.
Tests system performance under high-load, concurrent access scenarios.

Performance Targets:
- Handle 1000+ concurrent operations per second
- Memory usage <100MB for 100K records
- Response time <100ms for budget checks
- Support 100+ concurrent startups
- Alert processing <50ms
"""

import asyncio
import pytest
import time
import statistics
import threading
import psutil
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any, Tuple

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from budget_monitor import (
    BudgetMonitor, BudgetLimit, BudgetAlert, SpendingRecord,
    BudgetExceededError, get_global_budget_monitor
)
from core_types import generate_task_id, TaskType


@pytest.fixture(scope="function")
def performance_monitor():
    """Create a fresh budget monitor for performance testing"""
    return BudgetMonitor()


@pytest.fixture
def performance_metrics():
    """Track performance metrics during tests"""
    return {
        "start_time": None,
        "end_time": None, 
        "memory_usage": [],
        "response_times": [],
        "operation_count": 0
    }


class PerformanceTracker:
    """Helper class to track performance metrics"""
    
    def __init__(self):
        self.response_times = []
        self.memory_snapshots = []
        self.start_time = None
        self.operations_completed = 0
        
    def start_tracking(self):
        self.start_time = time.time()
        self._take_memory_snapshot()
    
    def record_operation(self, duration: float):
        self.response_times.append(duration)
        self.operations_completed += 1
        
        # Take memory snapshot every 100 operations
        if self.operations_completed % 100 == 0:
            self._take_memory_snapshot()
    
    def _take_memory_snapshot(self):
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.memory_snapshots.append(memory_mb)
    
    def get_summary(self) -> Dict[str, Any]:
        total_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            "total_operations": self.operations_completed,
            "total_time": total_time,
            "operations_per_second": self.operations_completed / max(total_time, 0.001),
            "avg_response_time": statistics.mean(self.response_times) if self.response_times else 0,
            "p95_response_time": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) >= 20 else 0,
            "p99_response_time": statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) >= 100 else 0,
            "min_response_time": min(self.response_times) if self.response_times else 0,
            "max_response_time": max(self.response_times) if self.response_times else 0,
            "peak_memory_mb": max(self.memory_snapshots) if self.memory_snapshots else 0,
            "memory_growth_mb": self.memory_snapshots[-1] - self.memory_snapshots[0] if len(self.memory_snapshots) >= 2 else 0
        }


@pytest.mark.performance
class TestBudgetSystemLoadTesting:
    """Load testing for normal operational scenarios"""
    
    @pytest.mark.asyncio
    async def test_high_volume_spending_records(self, performance_monitor):
        """Test system performance with high volume of spending records"""
        monitor = performance_monitor
        tracker = PerformanceTracker()
        
        # Set up test startup
        startup_id = "load_test_startup"
        await monitor.set_budget_limit(startup_id, daily_limit=100000.0)
        
        # Test configuration
        record_count = 10000
        batch_size = 100
        
        tracker.start_tracking()
        
        # Process records in batches for better performance measurement
        for batch_num in range(record_count // batch_size):
            batch_start = time.time()
            
            # Create batch of spending records
            batch_tasks = []
            for i in range(batch_size):
                record_id = batch_num * batch_size + i
                task = monitor.record_spending(
                    startup_id=startup_id,
                    provider=["openai", "anthropic"][i % 2],
                    task_id=f"load_task_{record_id}",
                    cost=1.0,
                    tokens_used=1000,
                    task_type=["research", "code", "analysis"][i % 3]
                )
                batch_tasks.append(task)
            
            # Execute batch
            await asyncio.gather(*batch_tasks)
            
            batch_duration = time.time() - batch_start
            tracker.record_operation(batch_duration)
        
        # Verify final state
        total_spending = await monitor._get_total_spending(startup_id)
        assert abs(total_spending - record_count) < 0.01  # Should be exactly record_count * $1
        
        assert len(monitor.spending_records) == record_count
        
        # Performance analysis
        metrics = tracker.get_summary()
        
        # Performance assertions
        assert metrics["operations_per_second"] > 50  # Should process 50+ batches per second
        assert metrics["avg_response_time"] < 2.0  # Average batch should take <2s
        assert metrics["peak_memory_mb"] < 500  # Should not exceed 500MB
        
        print(f"\nHigh Volume Load Test Results:")
        print(f"  Records processed: {record_count}")
        print(f"  Total time: {metrics['total_time']:.2f}s")
        print(f"  Throughput: {metrics['operations_per_second']:.1f} batches/s")
        print(f"  Avg response time: {metrics['avg_response_time']:.3f}s")
        print(f"  P95 response time: {metrics['p95_response_time']:.3f}s")
        print(f"  Peak memory: {metrics['peak_memory_mb']:.1f}MB")
    
    @pytest.mark.asyncio
    async def test_concurrent_startup_operations(self, performance_monitor):
        """Test performance with multiple startups operating concurrently"""
        monitor = performance_monitor
        tracker = PerformanceTracker()
        
        # Configuration
        startup_count = 100
        operations_per_startup = 100
        
        # Set up all startups
        startup_setup_start = time.time()
        for i in range(startup_count):
            startup_id = f"concurrent_startup_{i}"
            await monitor.set_budget_limit(startup_id, daily_limit=1000.0)
        
        setup_time = time.time() - startup_setup_start
        print(f"Startup setup time: {setup_time:.2f}s for {startup_count} startups")
        
        tracker.start_tracking()
        
        # Define operation for single startup
        async def startup_operations(startup_id: str):
            operation_times = []
            
            for i in range(operations_per_startup):
                op_start = time.time()
                
                # Mix of operations
                if i % 3 == 0:
                    # Budget check operation
                    await monitor.can_proceed_with_task(startup_id, 5.0)
                elif i % 3 == 1:
                    # Spending record operation
                    await monitor.record_spending(
                        startup_id=startup_id,
                        provider="openai",
                        task_id=f"{startup_id}_op_{i}",
                        cost=2.0,
                        tokens_used=1000,
                        task_type="research"
                    )
                else:
                    # Status check operation
                    await monitor.get_budget_status(startup_id)
                
                operation_times.append(time.time() - op_start)
            
            return operation_times
        
        # Execute all startups concurrently
        concurrent_start = time.time()
        startup_tasks = [startup_operations(f"concurrent_startup_{i}") for i in range(startup_count)]
        
        all_operation_times = await asyncio.gather(*startup_tasks)
        concurrent_duration = time.time() - concurrent_start
        
        # Flatten all operation times
        flat_times = [time for startup_times in all_operation_times for time in startup_times]
        
        # Performance analysis
        total_operations = startup_count * operations_per_startup
        operations_per_second = total_operations / concurrent_duration
        avg_operation_time = statistics.mean(flat_times)
        p95_operation_time = statistics.quantiles(flat_times, n=20)[18] if len(flat_times) >= 20 else 0
        
        # Verify data integrity
        successful_records = len(monitor.spending_records)
        expected_records = startup_count * (operations_per_startup // 3)  # Only 1/3 are spending operations
        
        # Performance assertions
        assert operations_per_second > 1000  # Should handle 1000+ ops/second
        assert avg_operation_time < 0.1  # Average operation should be <100ms
        assert successful_records >= expected_records * 0.9  # At least 90% success rate
        
        print(f"\nConcurrent Operations Test Results:")
        print(f"  Startups: {startup_count}")
        print(f"  Total operations: {total_operations}")
        print(f"  Execution time: {concurrent_duration:.2f}s")
        print(f"  Throughput: {operations_per_second:.1f} ops/s")
        print(f"  Avg operation time: {avg_operation_time:.4f}s")
        print(f"  P95 operation time: {p95_operation_time:.4f}s")
        print(f"  Spending records created: {successful_records}")
    
    @pytest.mark.asyncio
    async def test_budget_checking_performance(self, performance_monitor):
        """Test performance of budget checking operations"""
        monitor = performance_monitor
        startup_id = "budget_check_test"
        
        # Set up startup with some spending history
        await monitor.set_budget_limit(startup_id, daily_limit=1000.0, weekly_limit=5000.0)
        
        # Create spending history to make calculations more complex
        for i in range(1000):
            await monitor.record_spending(
                startup_id=startup_id,
                provider="openai",
                task_id=f"history_task_{i}",
                cost=0.5,
                tokens_used=100,
                task_type="research"
            )
        
        # Benchmark budget checking operations
        check_count = 5000
        response_times = []
        
        for i in range(check_count):
            start_time = time.time()
            
            # Alternate between different types of checks
            if i % 4 == 0:
                await monitor.can_proceed_with_task(startup_id, 10.0)
            elif i % 4 == 1:
                await monitor.get_budget_status(startup_id)
            elif i % 4 == 2:
                await monitor.get_remaining_budget(startup_id)
            else:
                await monitor.get_spending_summary(startup_id)
            
            response_times.append(time.time() - start_time)
        
        # Performance analysis
        avg_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
        p99_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
        max_time = max(response_times)
        
        # Performance assertions
        assert avg_time < 0.001  # Should average <1ms
        assert p95_time < 0.005  # 95th percentile should be <5ms
        assert p99_time < 0.010  # 99th percentile should be <10ms
        assert max_time < 0.050  # Maximum should be <50ms
        
        print(f"\nBudget Checking Performance Results:")
        print(f"  Operations: {check_count}")
        print(f"  Avg response time: {avg_time:.4f}s ({avg_time*1000:.2f}ms)")
        print(f"  P95 response time: {p95_time:.4f}s ({p95_time*1000:.2f}ms)")
        print(f"  P99 response time: {p99_time:.4f}s ({p99_time*1000:.2f}ms)")
        print(f"  Max response time: {max_time:.4f}s ({max_time*1000:.2f}ms)")
        print(f"  Ops per second: {check_count / sum(response_times):.1f}")


@pytest.mark.stress
class TestBudgetSystemStressTesting:
    """Stress testing for extreme load scenarios"""
    
    @pytest.mark.asyncio
    async def test_memory_stress_large_dataset(self, performance_monitor):
        """Test memory usage with very large datasets"""
        monitor = performance_monitor
        tracker = PerformanceTracker()
        
        # Configuration for stress test
        startup_count = 50
        records_per_startup = 5000
        total_records = startup_count * records_per_startup
        
        print(f"Starting memory stress test: {total_records} total records")
        
        tracker.start_tracking()
        
        # Set up startups and create records
        for startup_idx in range(startup_count):
            startup_id = f"stress_startup_{startup_idx}"
            await monitor.set_budget_limit(startup_id, daily_limit=10000.0)
            
            # Create records in batches to avoid overwhelming asyncio
            batch_size = 500
            for batch_start in range(0, records_per_startup, batch_size):
                batch_tasks = []
                batch_end = min(batch_start + batch_size, records_per_startup)
                
                for record_idx in range(batch_start, batch_end):
                    task = monitor.record_spending(
                        startup_id=startup_id,
                        provider=["openai", "anthropic", "perplexity"][record_idx % 3],
                        task_id=f"{startup_id}_record_{record_idx}",
                        cost=0.1,
                        tokens_used=100,
                        task_type=["research", "code", "analysis"][record_idx % 3]
                    )
                    batch_tasks.append(task)
                
                await asyncio.gather(*batch_tasks)
                tracker.record_operation(time.time() - tracker.start_time)
        
        # Memory analysis
        process = psutil.Process(os.getpid())
        final_memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Verify data integrity
        assert len(monitor.spending_records) == total_records
        
        # Calculate memory efficiency
        memory_per_record = final_memory_mb / total_records * 1024  # KB per record
        
        # Memory performance assertions
        assert final_memory_mb < 1000  # Should not exceed 1GB
        assert memory_per_record < 50  # Should use <50KB per record
        
        # Test that system still responds quickly
        query_start = time.time()
        for startup_idx in range(10):  # Test subset of startups
            startup_id = f"stress_startup_{startup_idx}"
            await monitor.get_budget_status(startup_id)
        query_time = time.time() - query_start
        
        assert query_time < 1.0  # Should complete 10 queries in <1s even with large dataset
        
        print(f"\nMemory Stress Test Results:")
        print(f"  Total records: {total_records}")
        print(f"  Final memory usage: {final_memory_mb:.1f}MB")
        print(f"  Memory per record: {memory_per_record:.2f}KB")
        print(f"  Query time (10 operations): {query_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_limit_breaching(self, performance_monitor):
        """Stress test with many startups simultaneously hitting budget limits"""
        monitor = performance_monitor
        
        # Configuration
        startup_count = 50
        budget_limit = 100.0
        
        # Set up all startups with the same low limit
        for i in range(startup_count):
            startup_id = f"breach_test_{i}"
            await monitor.set_budget_limit(startup_id, daily_limit=budget_limit, hard_stop=True)
        
        # Create tasks that will breach limits for each startup
        breach_tasks = []
        for startup_idx in range(startup_count):
            startup_id = f"breach_test_{startup_idx}"
            
            # Create multiple tasks per startup that together exceed limit
            for task_idx in range(10):  # 10 tasks * $15 = $150 > $100 limit
                async def breach_attempt(s_id: str, t_id: str):
                    try:
                        await monitor.record_spending(
                            startup_id=s_id,
                            provider="openai",
                            task_id=t_id,
                            cost=15.0,
                            tokens_used=1000,
                            task_type="research"
                        )
                        return "success"
                    except BudgetExceededError:
                        return "blocked"
                    except Exception as e:
                        return f"error: {e}"
                
                breach_tasks.append(breach_attempt(startup_id, f"{startup_id}_task_{task_idx}"))
        
        # Execute all breach attempts concurrently
        start_time = time.time()
        results = await asyncio.gather(*breach_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results
        successes = sum(1 for r in results if r == "success")
        blocks = sum(1 for r in results if r == "blocked")
        errors = len(results) - successes - blocks
        
        # Verify budget enforcement worked
        total_spending = 0
        over_limit_startups = 0
        
        for startup_idx in range(startup_count):
            startup_id = f"breach_test_{startup_idx}"
            spending = await monitor._get_total_spending(startup_id)
            total_spending += spending
            
            if spending > budget_limit:
                over_limit_startups += 1
        
        # Stress test assertions
        assert over_limit_startups == 0  # No startup should exceed limit
        assert blocks > 0  # Some operations should have been blocked
        assert errors < len(results) * 0.1  # Less than 10% should be errors
        assert execution_time < 30  # Should complete within 30 seconds
        
        print(f"\nConcurrent Limit Breaching Stress Test:")
        print(f"  Total operations: {len(results)}")
        print(f"  Execution time: {execution_time:.2f}s")
        print(f"  Successes: {successes}")
        print(f"  Blocked: {blocks}")
        print(f"  Errors: {errors}")
        print(f"  Total spending: ${total_spending:.2f}")
        print(f"  Startups over limit: {over_limit_startups}")
    
    @pytest.mark.asyncio
    async def test_alert_system_stress(self, performance_monitor):
        """Stress test the alert system with high volume of alerts"""
        monitor = performance_monitor
        
        # Configuration
        startup_count = 20
        
        # Set up alert tracking
        triggered_alerts = []
        alert_processing_times = []
        
        def stress_alert_callback(alert):
            start_time = time.time()
            # Simulate some processing work
            triggered_alerts.append(alert)
            processing_time = time.time() - start_time
            alert_processing_times.append(processing_time)
        
        monitor.register_alert_callback(stress_alert_callback)
        
        # Set up startups with low limits to trigger many alerts
        for i in range(startup_count):
            startup_id = f"alert_stress_{i}"
            await monitor.set_budget_limit(
                startup_id=startup_id,
                daily_limit=50.0,
                warning_threshold=0.2,  # Very low threshold to trigger many warnings
                hard_stop=False  # Allow operations to continue
            )
        
        # Generate spending that will trigger many alerts
        alert_trigger_tasks = []
        for startup_idx in range(startup_count):
            startup_id = f"alert_stress_{startup_idx}"
            
            # Create spending pattern that triggers multiple alerts
            costs = [5.0, 8.0, 12.0, 15.0, 20.0]  # Progressively trigger warnings and limits
            
            for i, cost in enumerate(costs):
                task = monitor.record_spending(
                    startup_id=startup_id,
                    provider="openai",
                    task_id=f"{startup_id}_alert_task_{i}",
                    cost=cost,
                    tokens_used=1000,
                    task_type="research"
                )
                alert_trigger_tasks.append(task)
        
        # Execute all alert-triggering operations
        start_time = time.time()
        await asyncio.gather(*alert_trigger_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Allow callbacks to complete
        await asyncio.sleep(0.5)
        
        # Analyze alert performance
        total_alerts = len(triggered_alerts)
        warning_alerts = len([a for a in triggered_alerts if a.alert_type == "warning"])
        limit_alerts = len([a for a in triggered_alerts if a.alert_type == "limit_exceeded"])
        
        avg_alert_processing = statistics.mean(alert_processing_times) if alert_processing_times else 0
        
        # Stress test assertions
        assert total_alerts > 0  # Should have generated alerts
        assert warning_alerts > 0  # Should have warning alerts
        assert avg_alert_processing < 0.001  # Alert processing should be very fast
        assert execution_time < 10  # Should complete quickly despite many alerts
        
        print(f"\nAlert System Stress Test:")
        print(f"  Execution time: {execution_time:.2f}s")
        print(f"  Total alerts: {total_alerts}")
        print(f"  Warning alerts: {warning_alerts}")
        print(f"  Limit exceeded alerts: {limit_alerts}")
        print(f"  Avg alert processing: {avg_alert_processing:.6f}s")


@pytest.mark.benchmark
class TestBudgetSystemBenchmarks:
    """Benchmark tests for performance comparison"""
    
    @pytest.mark.asyncio
    async def test_spending_record_throughput_benchmark(self, performance_monitor):
        """Benchmark spending record throughput"""
        monitor = performance_monitor
        startup_id = "benchmark_test"
        
        await monitor.set_budget_limit(startup_id, daily_limit=100000.0)
        
        # Benchmark different batch sizes
        batch_sizes = [1, 10, 50, 100, 500]
        benchmark_results = {}
        
        for batch_size in batch_sizes:
            # Test with this batch size
            iterations = 1000 // batch_size
            total_operations = iterations * batch_size
            
            start_time = time.time()
            
            for iteration in range(iterations):
                batch_tasks = []
                for i in range(batch_size):
                    task_id = f"bench_{batch_size}_{iteration}_{i}"
                    task = monitor.record_spending(
                        startup_id=startup_id,
                        provider="openai",
                        task_id=task_id,
                        cost=1.0,
                        tokens_used=1000,
                        task_type="benchmark"
                    )
                    batch_tasks.append(task)
                
                await asyncio.gather(*batch_tasks)
            
            execution_time = time.time() - start_time
            throughput = total_operations / execution_time
            
            benchmark_results[batch_size] = {
                "operations": total_operations,
                "time": execution_time,
                "throughput": throughput
            }
        
        # Find optimal batch size
        optimal_batch = max(benchmark_results.keys(), 
                           key=lambda k: benchmark_results[k]["throughput"])
        
        print(f"\nSpending Record Throughput Benchmark:")
        for batch_size, results in benchmark_results.items():
            print(f"  Batch size {batch_size:3d}: {results['throughput']:7.1f} ops/s "
                  f"({results['operations']} ops in {results['time']:.2f}s)")
        
        print(f"  Optimal batch size: {optimal_batch}")
        
        # Performance assertions
        assert benchmark_results[optimal_batch]["throughput"] > 500  # Should exceed 500 ops/s
    
    @pytest.mark.asyncio
    async def test_budget_calculation_benchmark(self, performance_monitor):
        """Benchmark budget calculation performance with varying data sizes"""
        monitor = performance_monitor
        startup_id = "calc_benchmark"
        
        await monitor.set_budget_limit(startup_id, daily_limit=10000.0)
        
        # Create different dataset sizes for benchmarking
        dataset_sizes = [100, 500, 1000, 5000, 10000]
        calculation_results = {}
        
        for size in dataset_sizes:
            # Create spending records
            for i in range(size):
                await monitor.record_spending(
                    startup_id=startup_id,
                    provider="openai",
                    task_id=f"calc_setup_{i}",
                    cost=1.0,
                    tokens_used=1000,
                    task_type="setup"
                )
            
            # Benchmark calculation performance
            calculation_times = []
            
            for _ in range(100):  # 100 iterations for statistical accuracy
                start_time = time.time()
                await monitor.get_budget_status(startup_id)
                calculation_times.append(time.time() - start_time)
            
            avg_calc_time = statistics.mean(calculation_times)
            calculation_results[size] = {
                "avg_time": avg_calc_time,
                "records": len(monitor.spending_records)
            }
        
        print(f"\nBudget Calculation Benchmark:")
        for size, results in calculation_results.items():
            print(f"  {size:5d} records: {results['avg_time']:.4f}s avg "
                  f"({results['avg_time']*1000:.2f}ms)")
        
        # Performance should not degrade significantly with dataset size
        smallest_time = calculation_results[min(dataset_sizes)]["avg_time"]
        largest_time = calculation_results[max(dataset_sizes)]["avg_time"]
        
        # Time should not increase by more than 10x for 100x data increase
        assert largest_time < smallest_time * 10
        assert largest_time < 0.1  # Should always be under 100ms


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "performance"])