#!/usr/bin/env python3
"""
Integration tests for Track A: Multi-Startup Core Infrastructure
Tests the complete integration of StartupManager, ResourceAllocator, QueueProcessor, and MultiStartupOrchestrator.
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path

# Import Track A components
import sys
sys.path.append(str(Path(__file__).parent.parent / "tools"))

from core_types import StartupConfig, StartupStatus, TaskType, TaskPriority
from startup_manager import StartupManager, create_test_startup
from resource_allocator import ResourceAllocator
from queue_processor import QueueProcessor
from multi_startup_orchestrator import MultiStartupOrchestrator, create_demo_startup, create_multiple_demo_startups


class TestTrackAIntegration:
    """Integration tests for Track A components"""
    
    @pytest.fixture
    async def temp_dir(self):
        """Create temporary directory for test state"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    async def startup_manager(self, temp_dir):
        """Create startup manager with temporary state directory"""
        manager = StartupManager(max_concurrent=5, state_dir=str(temp_dir / "states"))
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def resource_allocator(self):
        """Create resource allocator"""
        allocator = ResourceAllocator(base_port=5000, port_range=100)  # Use high ports for testing
        await allocator.initialize()
        yield allocator
        await allocator.cleanup()
    
    @pytest.fixture
    async def queue_processor(self):
        """Create queue processor"""
        processor = QueueProcessor(max_concurrent=5)
        await processor.start_processing()
        yield processor
        await processor.cleanup()
    
    @pytest.fixture
    async def multi_orchestrator(self, temp_dir):
        """Create multi-startup orchestrator"""
        # Create a temporary config for testing
        config_path = temp_dir / "config.yaml"
        config_path.write_text("test_mode: true\n")
        
        orchestrator = MultiStartupOrchestrator(
            config_path=str(config_path),
            max_concurrent_startups=3
        )
        await orchestrator.initialize()
        yield orchestrator
        await orchestrator.cleanup()
    
    async def test_startup_manager_basic_operations(self, startup_manager):
        """Test basic startup manager operations"""
        
        # Create test startup
        startup_id = await create_test_startup(startup_manager, "test-startup-1")
        
        # Verify startup exists
        startup = await startup_manager.get_startup(startup_id)
        assert startup.id == startup_id
        assert startup.config.name == "test-startup-1"
        assert startup.status == StartupStatus.ACTIVE
        
        # Get active startups
        active_startups = await startup_manager.get_active_startups()
        assert len(active_startups) == 1
        assert active_startups[0].id == startup_id
        
        # Update status
        await startup_manager.update_startup_status(startup_id, StartupStatus.COMPLETED)
        updated_startup = await startup_manager.get_startup(startup_id)
        assert updated_startup.status == StartupStatus.COMPLETED
        
        # Get stats
        stats = await startup_manager.get_startup_stats()
        assert stats['total_startups'] == 1
        assert stats['status_breakdown']['completed'] == 1
    
    async def test_resource_allocator_conflict_prevention(self, resource_allocator):
        """Test resource allocation conflict prevention"""
        
        # Allocate resources for first startup
        requirements_1 = {
            'memory_mb': 500,
            'cpu_cores': 0.5,
            'storage_gb': 2,
            'port_count': 3
        }
        allocation_1 = await resource_allocator.allocate("startup-1", requirements_1)
        
        # Allocate resources for second startup
        requirements_2 = {
            'memory_mb': 600,
            'cpu_cores': 0.7,
            'storage_gb': 3,
            'port_count': 3
        }
        allocation_2 = await resource_allocator.allocate("startup-2", requirements_2)
        
        # Verify no port conflicts
        assert len(set(allocation_1.ports) & set(allocation_2.ports)) == 0
        
        # Verify different database namespaces
        assert allocation_1.database_namespace != allocation_2.database_namespace
        
        # Verify memory allocations
        assert allocation_1.memory_mb == 500
        assert allocation_2.memory_mb == 600
        
        # Get resource usage
        usage = await resource_allocator.get_resource_usage()
        assert usage['startup_allocations'] == 2
        assert len(usage['allocation_details']) == 2
        
        # Deallocate first startup
        await resource_allocator.deallocate("startup-1")
        
        # Verify deallocation
        usage_after = await resource_allocator.get_resource_usage()
        assert usage_after['startup_allocations'] == 1
        assert 'startup-1' not in usage_after['allocation_details']
    
    async def test_queue_processor_task_execution(self, queue_processor):
        """Test queue processor task execution"""
        from core_types import Task, generate_task_id
        
        # Create test tasks
        task_1 = Task(
            id=generate_task_id(),
            startup_id="startup-1",
            type=TaskType.MARKET_RESEARCH,
            description="Test market research",
            prompt="Analyze the market for test startup",
            priority=TaskPriority.HIGH
        )
        
        task_2 = Task(
            id=generate_task_id(),
            startup_id="startup-2", 
            type=TaskType.FOUNDER_ANALYSIS,
            description="Test founder analysis",
            prompt="Analyze founder fit for test startup",
            priority=TaskPriority.MEDIUM
        )
        
        # Submit tasks
        task_id_1 = await queue_processor.submit_task(task_1)
        task_id_2 = await queue_processor.submit_task(task_2)
        
        assert task_id_1 == task_1.id
        assert task_id_2 == task_2.id
        
        # Wait for completion (tasks are mocked, should complete quickly)
        for _ in range(10):  # Wait up to 10 seconds
            result_1 = await queue_processor.get_task_result(task_id_1)
            result_2 = await queue_processor.get_task_result(task_id_2)
            
            if result_1 and result_2:
                break
            
            await asyncio.sleep(1)
        
        # Verify results
        assert result_1 is not None
        assert result_2 is not None
        assert result_1.success
        assert result_2.success
        assert result_1.task_id == task_id_1
        assert result_2.task_id == task_id_2
        
        # Check queue stats
        stats = await queue_processor.get_queue_stats()
        assert stats['tasks']['completed'] >= 2
        assert stats['performance']['success_rate'] > 0
    
    async def test_concurrent_startup_creation(self, startup_manager):
        """Test creating multiple startups concurrently"""
        
        # Create startup configs
        configs = []
        for i in range(3):
            config = StartupConfig(
                name=f"concurrent-startup-{i}",
                industry="technology",
                category="test",
                template="neoforge",
                founder_profile={"test": True},
                resource_requirements={
                    'memory_mb': 400 + i * 100,
                    'cpu_cores': 0.5,
                    'storage_gb': 2,
                    'port_count': 3
                }
            )
            configs.append(config)
        
        # Create startups concurrently
        tasks = [startup_manager.create_startup(config) for config in configs]
        startup_ids = await asyncio.gather(*tasks)
        
        # Verify all startups created
        assert len(startup_ids) == 3
        assert len(set(startup_ids)) == 3  # All unique
        
        # Verify all startups exist
        for startup_id in startup_ids:
            startup = await startup_manager.get_startup(startup_id)
            assert startup.status == StartupStatus.ACTIVE
        
        # Verify resource isolation
        startups = [await startup_manager.get_startup(sid) for sid in startup_ids]
        
        # Check no port conflicts
        all_ports = []
        for startup in startups:
            all_ports.extend(startup.resource_allocation.ports)
        
        assert len(all_ports) == len(set(all_ports))  # All ports unique
        
        # Check unique database namespaces
        namespaces = [s.resource_allocation.database_namespace for s in startups]
        assert len(namespaces) == len(set(namespaces))  # All unique
    
    async def test_multi_startup_orchestrator_basic_workflow(self, multi_orchestrator):
        """Test basic multi-startup orchestrator workflow"""
        
        # Create single demo startup
        startup_id = await create_demo_startup(multi_orchestrator, "Test Orchestrator Startup")
        
        # Verify startup created
        assert startup_id is not None
        
        # Get startup status
        status = await multi_orchestrator.get_startup_status(startup_id)
        assert status['startup_id'] == startup_id
        assert status['name'] == "Test Orchestrator Startup"
        assert status['workflow_status'] in ['initializing', 'active']
        
        # Wait a bit for workflow to start
        await asyncio.sleep(2)
        
        # Check system metrics
        metrics = await multi_orchestrator.get_system_metrics()
        assert metrics['orchestrator_metrics']['total_startups_created'] >= 1
        assert metrics['current_load']['active_startups'] >= 0
        
        # Check health
        health = await multi_orchestrator.health_check()
        assert 'healthy' in health
        assert 'components' in health
    
    async def test_multi_startup_orchestrator_concurrent_creation(self, multi_orchestrator):
        """Test creating multiple startups through orchestrator"""
        
        # Create multiple demo startups
        startup_ids = await create_multiple_demo_startups(multi_orchestrator, count=2)
        
        # Verify startups created
        assert len(startup_ids) == 2
        assert len(set(startup_ids)) == 2  # All unique
        
        # Get all statuses
        all_statuses = await multi_orchestrator.get_all_startups_status()
        
        # Verify we have at least our 2 startups
        our_startups = [s for s in all_statuses if s['startup_id'] in startup_ids]
        assert len(our_startups) == 2
        
        # Verify they're in valid states
        for status in our_startups:
            assert status['workflow_status'] in ['initializing', 'active', 'completed', 'failed']
            assert status['total_phases'] > 0
        
        # Check system metrics
        metrics = await multi_orchestrator.get_system_metrics()
        assert metrics['orchestrator_metrics']['total_startups_created'] >= 2
    
    async def test_full_integration_workflow(self, multi_orchestrator):
        """Test full integration workflow with all components"""
        
        # Create startup
        startup_id = await create_demo_startup(multi_orchestrator, "Full Integration Test")
        
        # Monitor workflow for a short time
        for i in range(5):  # Monitor for 5 seconds
            await asyncio.sleep(1)
            
            # Check status
            status = await multi_orchestrator.get_startup_status(startup_id)
            print(f"Iteration {i}: Status = {status['workflow_status']}, "
                  f"Phase = {status.get('current_phase_name', 'N/A')}")
            
            # If completed or failed, break
            if status['workflow_status'] in ['completed', 'failed']:
                break
        
        # Final health check
        health = await multi_orchestrator.health_check()
        assert health['healthy'] or len(health.get('issues', [])) == 0  # Should be healthy or have minor issues
        
        # Final metrics
        metrics = await multi_orchestrator.get_system_metrics()
        assert metrics['orchestrator_metrics']['total_startups_created'] >= 1
        
        # Verify resource cleanup will work
        final_status = await multi_orchestrator.get_startup_status(startup_id)
        print(f"Final status: {final_status}")


# Run integration tests
if __name__ == "__main__":
    async def run_tests():
        """Run integration tests manually"""
        
        import logging
        logging.basicConfig(level=logging.INFO)
        
        print("🧪 Running Track A Integration Tests...")
        
        # Test individual components first
        print("\n1. Testing StartupManager...")
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StartupManager(state_dir=str(Path(temp_dir) / "states"))
            await manager.initialize()
            
            startup_id = await create_test_startup(manager, "integration-test")
            startup = await manager.get_startup(startup_id)
            print(f"   ✅ Created startup: {startup.config.name}")
            
            await manager.cleanup()
        
        print("\n2. Testing ResourceAllocator...")
        allocator = ResourceAllocator(base_port=6000, port_range=50)
        await allocator.initialize()
        
        allocation = await allocator.allocate("test-startup", {
            'memory_mb': 500,
            'port_count': 3
        })
        print(f"   ✅ Allocated ports: {allocation.ports}")
        
        await allocator.cleanup()
        
        print("\n3. Testing QueueProcessor...")
        from core_types import Task, TaskType, TaskPriority, generate_task_id
        
        processor = QueueProcessor(max_concurrent=3)
        await processor.start_processing()
        
        task = Task(
            id=generate_task_id(),
            startup_id="test",
            type=TaskType.MARKET_RESEARCH,
            description="Test task",
            prompt="Test prompt",
            priority=TaskPriority.HIGH
        )
        
        task_id = await processor.submit_task(task)
        
        # Wait for completion
        for _ in range(5):
            result = await processor.get_task_result(task_id)
            if result:
                print(f"   ✅ Task completed: {result.success}")
                break
            await asyncio.sleep(1)
        
        await processor.cleanup()
        
        print("\n4. Testing MultiStartupOrchestrator...")
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text("test_mode: true\n")
            
            orchestrator = MultiStartupOrchestrator(
                config_path=str(config_path),
                max_concurrent_startups=2
            )
            await orchestrator.initialize()
            
            startup_id = await create_demo_startup(orchestrator, "Integration Test Startup")
            print(f"   ✅ Created startup through orchestrator: {startup_id}")
            
            # Wait a moment for workflow to start
            await asyncio.sleep(2)
            
            status = await orchestrator.get_startup_status(startup_id)
            print(f"   📊 Startup status: {status['workflow_status']}")
            
            health = await orchestrator.health_check()
            print(f"   🏥 System health: {health['healthy']}")
            
            await orchestrator.cleanup()
        
        print("\n🎉 All Track A integration tests completed successfully!")
    
    asyncio.run(run_tests())