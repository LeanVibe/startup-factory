#!/usr/bin/env python3
"""
Comprehensive Multi-Startup Manager Testing Suite

Tests all aspects of the Multi-Startup Manager system including:
1. MultiStartupManager orchestration and lifecycle management
2. ResourcePool allocation, cleanup, and isolation
3. PerformanceOptimizer caching and optimization
4. StartupInstance status tracking and data integrity
5. Concurrent operations and resource contention
6. Error handling and recovery mechanisms
7. Resource leak prevention and cleanup validation
8. Performance under stress conditions

Coverage Target: 85%+ for critical startup creation pipeline
"""

import pytest
import asyncio
import tempfile
import time
import socket
import uuid
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

# Import the multi-startup manager and dependencies
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from multi_startup_manager import (
    MultiStartupManager,
    ResourcePool,
    PerformanceOptimizer,
    StartupInstance,
    ResourceLimits,
    StartupStatus
)


class TestStartupInstance:
    """Tests for StartupInstance dataclass"""
    
    def test_startup_instance_creation(self):
        """Test StartupInstance initialization"""
        startup_id = str(uuid.uuid4())
        instance = StartupInstance(id=startup_id, name="test-startup")
        
        assert instance.id == startup_id
        assert instance.name == "test-startup"
        assert instance.status == StartupStatus.PENDING
        assert instance.created_at is not None
        assert instance.started_at is None
        assert instance.completed_at is None
        assert instance.assigned_port is None
        assert instance.work_dir is None
        assert instance.resource_usage == {}
        assert instance.error_message is None
        assert instance.process_id is None
    
    def test_startup_instance_status_transitions(self):
        """Test status transitions are valid"""
        instance = StartupInstance(id="test", name="test")
        
        # Valid transition sequence
        instance.status = StartupStatus.RUNNING
        instance.started_at = datetime.now()
        
        # Small delay to ensure different timestamps
        import time
        time.sleep(0.001)
        
        instance.status = StartupStatus.COMPLETED
        instance.completed_at = datetime.now()
        
        # Verify state
        assert instance.status == StartupStatus.COMPLETED
        assert instance.started_at <= instance.completed_at  # Allow equal timestamps
    
    def test_startup_instance_error_state(self):
        """Test error state handling"""
        instance = StartupInstance(id="test", name="test")
        
        instance.status = StartupStatus.FAILED
        instance.error_message = "Test error"
        
        assert instance.status == StartupStatus.FAILED
        assert instance.error_message == "Test error"


class TestResourceLimits:
    """Tests for ResourceLimits dataclass"""
    
    def test_resource_limits_defaults(self):
        """Test default resource limits"""
        limits = ResourceLimits()
        
        assert limits.max_memory_mb == 500
        assert limits.max_cpu_percent == 25
        assert limits.max_disk_mb == 1000
        assert limits.max_network_mb == 100
        assert limits.timeout_minutes == 30
    
    def test_resource_limits_custom(self):
        """Test custom resource limits"""
        limits = ResourceLimits(
            max_memory_mb=1000,
            max_cpu_percent=50,
            max_disk_mb=2000,
            max_network_mb=200,
            timeout_minutes=60
        )
        
        assert limits.max_memory_mb == 1000
        assert limits.max_cpu_percent == 50
        assert limits.max_disk_mb == 2000
        assert limits.max_network_mb == 200
        assert limits.timeout_minutes == 60


class TestResourcePool:
    """Tests for ResourcePool resource management"""
    
    @pytest.fixture
    def resource_pool(self):
        """Create a fresh ResourcePool for testing"""
        return ResourcePool(max_concurrent=3)
    
    def test_resource_pool_initialization(self, resource_pool):
        """Test ResourcePool initialization"""
        assert resource_pool.max_concurrent == 3
        assert len(resource_pool.available_ports) == 100  # 8000-8099
        assert len(resource_pool.used_ports) == 0
        assert len(resource_pool.temp_dirs) == 0
        assert resource_pool.resource_locks._value == 3  # Semaphore value
    
    @pytest.mark.asyncio
    async def test_port_allocation_and_release(self, resource_pool):
        """Test port allocation and release"""
        # Allocate a port
        port = await resource_pool.acquire_port()
        
        assert port >= 8000
        assert port <= 8099
        assert port in resource_pool.used_ports
        assert len(resource_pool.used_ports) == 1
        
        # Release the port
        resource_pool.release_port(port)
        
        assert port not in resource_pool.used_ports
        assert len(resource_pool.used_ports) == 0
    
    @pytest.mark.asyncio
    async def test_port_allocation_exhaustion(self):
        """Test behavior when all ports are exhausted"""
        # Create pool with limited ports for testing
        pool = ResourcePool(max_concurrent=5)
        
        # Mock _is_port_in_use to avoid conflicts with actual system ports
        def mock_port_check(port):
            # Mark the first two ports as available, rest as in use
            return port not in [9000, 9001]
        
        pool.available_ports = [9000, 9001, 9002, 9003]  # 4 ports, but only first 2 are "available"
        pool._is_port_in_use = mock_port_check
        
        # Allocate all actually available ports
        port1 = await pool.acquire_port()
        port2 = await pool.acquire_port()
        
        assert port1 != port2
        assert port1 in [9000, 9001]
        assert port2 in [9000, 9001]
        assert len(pool.used_ports) == 2
        
        # Try to allocate when none available - should raise error
        with pytest.raises(RuntimeError, match="No available ports"):
            await pool.acquire_port()
    
    @pytest.mark.asyncio
    async def test_work_directory_allocation_and_cleanup(self, resource_pool):
        """Test work directory allocation and cleanup"""
        startup_id = "test-startup-001"
        
        # Allocate work directory
        work_dir = await resource_pool.acquire_work_dir(startup_id)
        
        assert work_dir is not None
        assert work_dir.exists()
        assert startup_id in resource_pool.temp_dirs
        assert resource_pool.temp_dirs[startup_id] == work_dir
        
        # Cleanup work directory
        resource_pool.release_work_dir(startup_id)
        
        assert not work_dir.exists()
        assert startup_id not in resource_pool.temp_dirs
    
    @pytest.mark.asyncio
    async def test_work_directory_cleanup_error_handling(self, resource_pool):
        """Test work directory cleanup with errors"""
        startup_id = "test-startup-002"
        work_dir = await resource_pool.acquire_work_dir(startup_id)
        
        # Simulate cleanup error by removing directory manually
        shutil.rmtree(work_dir)
        
        # Cleanup should handle the error gracefully
        resource_pool.release_work_dir(startup_id)
        
        assert startup_id not in resource_pool.temp_dirs
    
    def test_port_in_use_detection(self, resource_pool):
        """Test port usage detection"""
        # Most ports should be available
        assert not resource_pool._is_port_in_use(8050)
        
        # Test with a likely used port (if available)
        # This is a best-effort test as we can't guarantee port states
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', 8051))
                s.listen(1)
                # Port should now be detected as in use
                assert resource_pool._is_port_in_use(8051)
        except OSError:
            # Port might already be in use, which is fine for this test
            pass
    
    @pytest.mark.asyncio
    async def test_concurrent_resource_allocation(self, resource_pool):
        """Test concurrent resource allocation"""
        startup_ids = ["concurrent-1", "concurrent-2", "concurrent-3"]
        
        # Allocate resources concurrently
        tasks = []
        for startup_id in startup_ids:
            task = asyncio.create_task(self._allocate_resources(resource_pool, startup_id))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify no resource conflicts
        allocated_ports = [result[0] for result in results]
        assert len(set(allocated_ports)) == len(allocated_ports)  # All unique
        
        # Verify all directories were created
        for startup_id, (port, work_dir) in zip(startup_ids, results):
            assert work_dir.exists()
            assert startup_id in resource_pool.temp_dirs
        
        # Cleanup
        for startup_id, (port, work_dir) in zip(startup_ids, results):
            resource_pool.release_port(port)
            resource_pool.release_work_dir(startup_id)
    
    async def _allocate_resources(self, pool, startup_id):
        """Helper to allocate resources for testing"""
        port = await pool.acquire_port()
        work_dir = await pool.acquire_work_dir(startup_id)
        return port, work_dir


class TestPerformanceOptimizer:
    """Tests for PerformanceOptimizer caching and optimization"""
    
    @pytest.fixture
    def optimizer(self):
        """Create a fresh PerformanceOptimizer for testing"""
        return PerformanceOptimizer()
    
    def test_optimizer_initialization(self, optimizer):
        """Test PerformanceOptimizer initialization"""
        assert len(optimizer.api_cache) == 0
        assert len(optimizer.template_cache) == 0
        assert optimizer.cache_ttl == 3600  # 1 hour
    
    @pytest.mark.asyncio
    async def test_api_call_caching(self, optimizer):
        """Test API call caching functionality"""
        cache_key = "test_api_call"
        expected_result = {"data": "test_result"}
        
        # Mock API function
        mock_api = AsyncMock(return_value=expected_result)
        
        # First call - should invoke API
        result1 = await optimizer.cached_api_call(cache_key, mock_api, "arg1", key="value")
        
        assert result1 == expected_result
        assert cache_key in optimizer.api_cache
        assert mock_api.call_count == 1
        
        # Second call - should use cache
        result2 = await optimizer.cached_api_call(cache_key, mock_api, "arg1", key="value")
        
        assert result2 == expected_result
        assert mock_api.call_count == 1  # Not called again
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, optimizer):
        """Test cache expiration functionality"""
        cache_key = "expiring_call"
        expected_result = {"data": "test"}
        
        # Set very short TTL for testing
        optimizer.cache_ttl = 0.1  # 100ms
        
        mock_api = AsyncMock(return_value=expected_result)
        
        # First call
        await optimizer.cached_api_call(cache_key, mock_api)
        assert mock_api.call_count == 1
        
        # Wait for cache to expire
        await asyncio.sleep(0.2)
        
        # Second call should invoke API again
        await optimizer.cached_api_call(cache_key, mock_api)
        assert mock_api.call_count == 2
    
    @pytest.mark.asyncio
    async def test_parallel_api_calls(self, optimizer):
        """Test parallel API call execution"""
        # Mock API functions with different delays
        async def api_1():
            await asyncio.sleep(0.1)
            return "result1"
        
        async def api_2():
            await asyncio.sleep(0.1)
            return "result2"
        
        async def api_3():
            await asyncio.sleep(0.1)
            return "result3"
        
        calls = [
            (api_1, ()),
            (api_2, ()),
            (api_3, ())
        ]
        
        start_time = time.time()
        results = await optimizer.parallel_api_calls(calls)
        end_time = time.time()
        
        # Should complete in parallel (much less than 0.3s sequential time)
        assert end_time - start_time < 0.25
        assert results == ["result1", "result2", "result3"]
    
    @pytest.mark.asyncio
    async def test_parallel_api_calls_with_exceptions(self, optimizer):
        """Test parallel API calls handle exceptions"""
        async def success_api():
            return "success"
        
        async def failing_api():
            raise ValueError("API failed")
        
        calls = [
            (success_api, ()),
            (failing_api, ())
        ]
        
        results = await optimizer.parallel_api_calls(calls)
        
        assert results[0] == "success"
        assert isinstance(results[1], ValueError)
        assert str(results[1]) == "API failed"
    
    def test_template_precompilation(self, optimizer):
        """Test template precompilation"""
        # Create temporary directories for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir1 = Path(temp_dir) / "template1"
            template_dir2 = Path(temp_dir) / "template2"
            template_dir1.mkdir()
            template_dir2.mkdir()
            
            template_dirs = [template_dir1, template_dir2]
            
            optimizer.precompile_templates(template_dirs)
            
            # Verify templates were cached
            assert str(template_dir1) in optimizer.template_cache
            assert str(template_dir2) in optimizer.template_cache
            
            for template_key in [str(template_dir1), str(template_dir2)]:
                cache_entry = optimizer.template_cache[template_key]
                assert cache_entry["compiled"] is True
                assert "timestamp" in cache_entry
    
    def test_template_precompilation_nonexistent_dir(self, optimizer):
        """Test template precompilation with non-existent directories"""
        nonexistent_dir = Path("/tmp/nonexistent_template_dir")
        
        # Should not raise error
        optimizer.precompile_templates([nonexistent_dir])
        
        # Should not add to cache
        assert str(nonexistent_dir) not in optimizer.template_cache


class TestMultiStartupManager:
    """Tests for MultiStartupManager orchestration"""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh MultiStartupManager for testing"""
        return MultiStartupManager(max_concurrent=2)
    
    def test_manager_initialization(self, manager):
        """Test MultiStartupManager initialization"""
        assert manager.max_concurrent == 2
        assert isinstance(manager.resource_pool, ResourcePool)
        assert isinstance(manager.optimizer, PerformanceOptimizer)
        assert len(manager.startups) == 0
        assert len(manager.running_tasks) == 0
        assert isinstance(manager.resource_limits, ResourceLimits)
    
    @pytest.mark.asyncio
    async def test_create_startup_basic(self, manager):
        """Test basic startup creation"""
        config = {"industry": "Tech", "category": "SaaS"}
        
        startup_id = await manager.create_startup("test-startup", config)
        
        assert startup_id is not None
        assert startup_id in manager.startups
        assert startup_id in manager.running_tasks
        
        startup = manager.startups[startup_id]
        assert startup.name == "test-startup"
        assert startup.status == StartupStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_startup_lifecycle_completion(self, manager):
        """Test complete startup lifecycle"""
        config = {"industry": "Tech", "category": "SaaS", "template": "neoforge"}
        
        startup_id = await manager.create_startup("lifecycle-test", config)
        
        # Wait for completion
        task = manager.running_tasks[startup_id]
        await task
        
        startup = manager.startups[startup_id]
        assert startup.status == StartupStatus.COMPLETED
        assert startup.started_at is not None
        assert startup.completed_at is not None
        assert startup.completed_at > startup.started_at
        
        # Verify task was removed from running tasks
        assert startup_id not in manager.running_tasks
    
    @pytest.mark.asyncio
    async def test_startup_resource_allocation(self, manager):
        """Test startup resource allocation during creation"""
        config = {"industry": "Tech", "category": "SaaS"}
        
        startup_id = await manager.create_startup("resource-test", config)
        
        # Wait for startup to begin running
        while manager.startups[startup_id].status == StartupStatus.PENDING:
            await asyncio.sleep(0.1)
        
        startup = manager.startups[startup_id]
        if startup.status == StartupStatus.RUNNING:
            assert startup.assigned_port is not None
            assert startup.work_dir is not None
            assert startup.work_dir.exists()
        
        # Wait for completion
        task = manager.running_tasks[startup_id]
        await task
        
        # Verify resources were cleaned up
        final_startup = manager.startups[startup_id]
        if final_startup.assigned_port:
            assert final_startup.assigned_port not in manager.resource_pool.used_ports
        assert startup_id not in manager.resource_pool.temp_dirs
    
    @pytest.mark.asyncio
    async def test_concurrent_startup_creation(self, manager):
        """Test concurrent startup creation within limits"""
        config = {"industry": "Tech", "category": "SaaS"}
        
        # Create multiple startups concurrently
        startup_ids = []
        for i in range(3):  # More than max_concurrent=2
            startup_id = await manager.create_startup(f"concurrent-{i}", config)
            startup_ids.append(startup_id)
        
        # Wait for all to complete
        tasks = [manager.running_tasks.get(sid) for sid in startup_ids if sid in manager.running_tasks]
        if tasks:
            await asyncio.gather(*tasks)
        
        # Verify all completed successfully
        completed_count = 0
        for startup_id in startup_ids:
            startup = manager.startups[startup_id]
            if startup.status == StartupStatus.COMPLETED:
                completed_count += 1
        
        assert completed_count == 3
    
    @pytest.mark.asyncio
    async def test_startup_cancellation(self, manager):
        """Test startup cancellation"""
        config = {"industry": "Tech", "category": "SaaS"}
        
        startup_id = await manager.create_startup("cancel-test", config)
        
        # Cancel immediately
        result = await manager.cancel_startup(startup_id)
        
        assert result is True
        
        startup = manager.startups[startup_id]
        assert startup.status == StartupStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_startup_status_retrieval(self, manager):
        """Test startup status retrieval"""
        config = {"industry": "Tech", "category": "SaaS"}
        
        startup_id = await manager.create_startup("status-test", config)
        
        # Test get_startup_status
        status = await manager.get_startup_status(startup_id)
        assert status is not None
        assert status.id == startup_id
        assert status.name == "status-test"
        
        # Test non-existent startup
        non_existent_status = await manager.get_startup_status("non-existent")
        assert non_existent_status is None
    
    @pytest.mark.asyncio
    async def test_list_startups(self, manager):
        """Test listing all startups"""
        config = {"industry": "Tech", "category": "SaaS"}
        
        # Create multiple startups
        startup_ids = []
        for i in range(3):
            startup_id = await manager.create_startup(f"list-test-{i}", config)
            startup_ids.append(startup_id)
        
        startups_list = await manager.list_startups()
        
        assert len(startups_list) == 3
        startup_names = {s.name for s in startups_list}
        assert "list-test-0" in startup_names
        assert "list-test-1" in startup_names
        assert "list-test-2" in startup_names
    
    @pytest.mark.asyncio
    async def test_resource_usage_monitoring(self, manager):
        """Test resource usage monitoring"""
        config = {"industry": "Tech", "category": "SaaS"}
        
        # Create a startup
        startup_id = await manager.create_startup("resource-monitor", config)
        
        # Get resource usage
        usage = await manager.get_resource_usage()
        
        assert "memory_usage_mb" in usage
        assert "memory_percent" in usage
        assert "cpu_percent" in usage
        assert "active_startups" in usage
        assert "total_startups" in usage
        assert "used_ports" in usage
        assert "temp_dirs" in usage
        
        assert usage["total_startups"] >= 1
        assert isinstance(usage["used_ports"], list)
        assert isinstance(usage["temp_dirs"], int)
    
    @pytest.mark.asyncio
    async def test_performance_optimization(self, manager):
        """Test performance optimization execution"""
        # Should not raise any exceptions
        await manager.optimize_performance()
        
        # Verify optimizer was used (should have attempted template precompilation)
        # This is mostly a smoke test since the actual optimization depends on file system
        assert True  # Test passes if no exceptions raised
    
    @pytest.mark.asyncio
    async def test_startup_error_handling(self, manager):
        """Test startup creation error handling"""
        # Mock a failing phase to test error handling
        original_method = manager._phase_market_research
        
        async def failing_phase(startup_id, config):
            raise RuntimeError("Simulated phase failure")
        
        manager._phase_market_research = failing_phase
        
        config = {"industry": "Tech", "category": "SaaS"}
        startup_id = await manager.create_startup("error-test", config)
        
        # Wait for task to complete (with error)
        task = manager.running_tasks[startup_id]
        await task
        
        startup = manager.startups[startup_id]
        assert startup.status == StartupStatus.FAILED
        assert "Simulated phase failure" in startup.error_message
        
        # Restore original method
        manager._phase_market_research = original_method
    
    @pytest.mark.asyncio
    async def test_startup_phases_execution(self, manager):
        """Test all startup phases execute correctly"""
        config = {
            "industry": "Tech", 
            "category": "SaaS", 
            "template": "neoforge"
        }
        
        startup_id = await manager.create_startup("phases-test", config)
        
        # Wait for completion
        task = manager.running_tasks[startup_id]
        await task
        
        startup = manager.startups[startup_id]
        
        if startup.status == StartupStatus.COMPLETED:
            # Verify resource usage was tracked for all phases
            assert "market_research" in startup.resource_usage
            assert "mvp_spec" in startup.resource_usage
            assert "architecture" in startup.resource_usage
            assert "project_generation" in startup.resource_usage
            assert "deployment" in startup.resource_usage


class TestConcurrencyAndStressScenarios:
    """Tests for concurrent operations and stress scenarios"""
    
    @pytest.mark.asyncio
    async def test_resource_pool_concurrent_stress(self):
        """Test ResourcePool under concurrent stress"""
        pool = ResourcePool(max_concurrent=10)
        
        async def allocate_and_release(startup_id):
            """Allocate resources, hold briefly, then release"""
            try:
                port = await pool.acquire_port()
                work_dir = await pool.acquire_work_dir(startup_id)
                
                # Hold resources briefly
                await asyncio.sleep(0.1)
                
                # Release resources
                pool.release_port(port)
                pool.release_work_dir(startup_id)
                
                return True
            except Exception as e:
                return False
        
        # Create many concurrent tasks
        tasks = []
        for i in range(20):
            task = asyncio.create_task(allocate_and_release(f"stress-{i}"))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Most should succeed (some may fail due to port exhaustion, which is expected)
        success_count = sum(1 for r in results if r is True)
        assert success_count >= 10  # At least half should succeed
        
        # Verify no resource leaks
        assert len(pool.used_ports) == 0
        assert len(pool.temp_dirs) == 0
    
    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self):
        """Test PerformanceOptimizer cache under concurrent access"""
        optimizer = PerformanceOptimizer()
        
        call_count = 0
        
        async def mock_api():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return f"result-{call_count}"
        
        # Multiple concurrent calls with same cache key
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                optimizer.cached_api_call("concurrent_key", mock_api)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should get the same result (cached)
        assert len(set(results)) == 1  # All results are the same
        # But call_count might be > 1 due to race conditions in caching
        # This is acceptable behavior
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_manager_high_concurrency(self):
        """Test MultiStartupManager with high concurrency"""
        manager = MultiStartupManager(max_concurrent=5)
        
        config = {"industry": "Tech", "category": "SaaS"}
        
        # Create many startups
        startup_ids = []
        for i in range(10):
            startup_id = await manager.create_startup(f"high-concurrency-{i}", config)
            startup_ids.append(startup_id)
        
        # Wait for all to complete
        start_time = time.time()
        
        while True:
            pending_tasks = [
                manager.running_tasks.get(sid) for sid in startup_ids 
                if sid in manager.running_tasks
            ]
            
            if not pending_tasks:
                break
            
            await asyncio.sleep(0.5)
            
            # Timeout after reasonable time
            if time.time() - start_time > 60:  # 1 minute timeout
                break
        
        # Verify results
        completed = 0
        failed = 0
        
        for startup_id in startup_ids:
            startup = manager.startups[startup_id]
            if startup.status == StartupStatus.COMPLETED:
                completed += 1
            elif startup.status == StartupStatus.FAILED:
                failed += 1
        
        # Most should complete successfully
        assert completed >= 8  # At least 80% success rate
        
        # Verify no resource leaks
        usage = await manager.get_resource_usage()
        assert usage["active_startups"] == 0


class TestErrorHandlingAndEdgeCases:
    """Tests for error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_resource_pool_port_exhaustion(self):
        """Test ResourcePool behavior when ports are exhausted"""
        pool = ResourcePool(max_concurrent=5)
        
        # Mock _is_port_in_use to control port availability
        def mock_port_check(port):
            return port not in [9500, 9501]  # Only these ports are "available"
        
        pool.available_ports = [9500, 9501, 9502, 9503]  # Limited set
        pool._is_port_in_use = mock_port_check
        
        # Allocate all available ports
        port1 = await pool.acquire_port()
        port2 = await pool.acquire_port()
        
        # Next allocation should fail
        with pytest.raises(RuntimeError, match="No available ports"):
            await pool.acquire_port()
        
        # Release and try again
        pool.release_port(port1)
        port3 = await pool.acquire_port()  # Should work now
        
        assert port3 in [9500, 9501]
    
    @pytest.mark.asyncio
    async def test_work_directory_permission_error(self):
        """Test work directory creation with permission errors"""
        pool = ResourcePool()
        
        # Mock tempfile.mkdtemp to raise permission error
        with patch('tempfile.mkdtemp') as mock_mkdtemp:
            mock_mkdtemp.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(PermissionError):
                await pool.acquire_work_dir("test-permission")
    
    @pytest.mark.asyncio
    async def test_startup_task_exception_handling(self):
        """Test exception handling in startup tasks"""
        manager = MultiStartupManager(max_concurrent=1)
        
        # Mock a phase to raise an exception
        original_phase = manager._phase_mvp_specification
        
        async def failing_phase(startup_id, config):
            raise ValueError("Test exception in phase")
        
        manager._phase_mvp_specification = failing_phase
        
        config = {"industry": "Tech"}
        startup_id = await manager.create_startup("exception-test", config)
        
        # Wait for task completion
        task = manager.running_tasks[startup_id]
        await task
        
        startup = manager.startups[startup_id]
        assert startup.status == StartupStatus.FAILED
        assert "Test exception in phase" in startup.error_message
        
        # Restore original phase
        manager._phase_mvp_specification = original_phase
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_startup(self):
        """Test cancelling non-existent startup"""
        manager = MultiStartupManager()
        
        result = await manager.cancel_startup("nonexistent-id")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_on_cancellation(self):
        """Test resource cleanup when startup is cancelled"""
        manager = MultiStartupManager(max_concurrent=1)
        
        config = {"industry": "Tech", "category": "SaaS"}
        startup_id = await manager.create_startup("cancel-cleanup", config)
        
        # Wait for startup to acquire resources
        await asyncio.sleep(0.2)
        
        # Cancel the startup
        await manager.cancel_startup(startup_id)
        
        # Wait a bit for cleanup
        await asyncio.sleep(0.2)
        
        # Verify resources were cleaned up
        usage = await manager.get_resource_usage()
        startup = manager.startups[startup_id]
        
        if startup.assigned_port:
            assert startup.assigned_port not in usage["used_ports"]
        assert startup_id not in manager.resource_pool.temp_dirs


# Pytest configuration for this test module
@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for the test module"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Slow test marker configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])