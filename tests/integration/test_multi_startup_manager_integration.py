#!/usr/bin/env python3
"""
Multi-Startup Manager Integration Tests

Integration tests for the complete multi-startup creation workflow including:
1. End-to-end startup creation pipeline
2. Resource isolation between concurrent startups
3. Cross-startup resource contention scenarios
4. Performance benchmarking and optimization
5. Production-like scenarios with realistic loads

These tests validate the system behavior under realistic conditions
and ensure no resource interference between concurrent startups.
"""

import pytest
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List
import tempfile

# Import the multi-startup manager
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from multi_startup_manager import (
    MultiStartupManager,
    StartupStatus
)


class TestMultiStartupManagerIntegration:
    """Integration tests for complete startup creation workflow"""
    
    @pytest.fixture
    def production_manager(self):
        """Create a manager with production-like settings"""
        return MultiStartupManager(max_concurrent=5)
    
    @pytest.mark.asyncio
    async def test_complete_startup_workflow(self, production_manager):
        """Test complete startup creation workflow from start to finish"""
        config = {
            "industry": "FinTech",
            "category": "Banking",
            "template": "neoforge",
            "features": ["payments", "accounts", "loans"],
            "scale": "enterprise"
        }
        
        # Create startup
        startup_id = await production_manager.create_startup("fintech-bank", config)
        
        # Monitor progress
        startup = await production_manager.get_startup_status(startup_id)
        initial_status = startup.status
        
        # Wait for completion
        task = production_manager.running_tasks[startup_id]
        await task
        
        # Validate final state
        final_startup = await production_manager.get_startup_status(startup_id)
        
        assert final_startup.status == StartupStatus.COMPLETED
        assert final_startup.started_at is not None
        assert final_startup.completed_at is not None
        assert final_startup.completed_at > final_startup.started_at
        
        # Verify all phases completed
        assert "market_research" in final_startup.resource_usage
        assert "mvp_spec" in final_startup.resource_usage
        assert "architecture" in final_startup.resource_usage
        assert "project_generation" in final_startup.resource_usage
        assert "deployment" in final_startup.resource_usage
        
        # Verify resource cleanup
        resource_usage = await production_manager.get_resource_usage()
        assert startup_id not in production_manager.resource_pool.temp_dirs
        if final_startup.assigned_port:
            assert final_startup.assigned_port not in resource_usage["used_ports"]
    
    @pytest.mark.asyncio
    async def test_concurrent_startup_isolation(self, production_manager):
        """Test resource isolation between concurrent startups"""
        configs = [
            {"industry": "Healthcare", "category": "Telemedicine", "template": "neoforge"},
            {"industry": "Education", "category": "E-learning", "template": "neoforge"},
            {"industry": "Retail", "category": "E-commerce", "template": "neoforge"}
        ]
        
        startup_names = ["healthtech-app", "edutech-platform", "retailtech-store"]
        startup_ids = []
        
        # Create all startups concurrently
        for name, config in zip(startup_names, configs):
            startup_id = await production_manager.create_startup(name, config)
            startup_ids.append(startup_id)
        
        # Wait for all to complete
        tasks = [production_manager.running_tasks.get(sid) for sid in startup_ids if sid in production_manager.running_tasks]
        if tasks:
            await asyncio.gather(*tasks)
        
        # Verify isolation - each startup should have unique resources
        startups = [await production_manager.get_startup_status(sid) for sid in startup_ids]
        
        # Check port isolation
        assigned_ports = [s.assigned_port for s in startups if s.assigned_port]
        assert len(assigned_ports) == len(set(assigned_ports))  # All unique
        
        # Check directory isolation
        work_dirs = [s.work_dir for s in startups if s.work_dir]
        work_dir_paths = [str(wd) for wd in work_dirs]
        assert len(work_dir_paths) == len(set(work_dir_paths))  # All unique
        
        # Verify all completed successfully (no resource conflicts)
        completed_count = sum(1 for s in startups if s.status == StartupStatus.COMPLETED)
        assert completed_count == len(startup_ids)
    
    @pytest.mark.asyncio
    async def test_resource_contention_handling(self, production_manager):
        """Test system behavior under resource contention"""
        # Create more startups than max_concurrent to test queuing
        num_startups = production_manager.max_concurrent * 2  # 10 startups, max 5 concurrent
        
        configs = [
            {"industry": f"Industry{i}", "category": f"Category{i}", "template": "neoforge"}
            for i in range(num_startups)
        ]
        
        startup_ids = []
        start_time = time.time()
        
        # Create all startups rapidly
        for i, config in enumerate(configs):
            startup_id = await production_manager.create_startup(f"contention-test-{i}", config)
            startup_ids.append(startup_id)
        
        creation_time = time.time() - start_time
        
        # Monitor concurrent execution
        max_concurrent_observed = 0
        while any(sid in production_manager.running_tasks for sid in startup_ids):
            current_running = len(production_manager.running_tasks)
            max_concurrent_observed = max(max_concurrent_observed, current_running)
            await asyncio.sleep(0.1)
        
        # Verify concurrency limits were respected
        assert max_concurrent_observed <= production_manager.max_concurrent
        
        # Verify all completed
        final_statuses = []
        for startup_id in startup_ids:
            startup = await production_manager.get_startup_status(startup_id)
            final_statuses.append(startup.status)
        
        completed_count = sum(1 for status in final_statuses if status == StartupStatus.COMPLETED)
        assert completed_count >= num_startups * 0.8  # At least 80% success rate
        
        # Verify resource cleanup
        resource_usage = await production_manager.get_resource_usage()
        assert resource_usage["active_startups"] == 0
        assert len(resource_usage["used_ports"]) == 0
        assert resource_usage["temp_dirs"] == 0
    
    @pytest.mark.asyncio
    async def test_performance_optimization_integration(self, production_manager):
        """Test performance optimizations in realistic scenarios"""
        # Pre-optimize the manager
        await production_manager.optimize_performance()
        
        # Create multiple startups with similar configurations to test caching
        base_config = {"industry": "SaaS", "category": "Productivity", "template": "neoforge"}
        
        startup_ids = []
        start_time = time.time()
        
        # Create 5 similar startups to benefit from caching
        for i in range(5):
            config = base_config.copy()
            config["name_suffix"] = f"v{i}"
            startup_id = await production_manager.create_startup(f"saas-productivity-{i}", config)
            startup_ids.append(startup_id)
        
        # Wait for all to complete
        tasks = [production_manager.running_tasks.get(sid) for sid in startup_ids if sid in production_manager.running_tasks]
        if tasks:
            await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Verify performance benefits (later startups should complete faster due to caching)
        startups = [await production_manager.get_startup_status(sid) for sid in startup_ids]
        durations = []
        
        for startup in startups:
            if startup.started_at and startup.completed_at and startup.status == StartupStatus.COMPLETED:
                duration = (startup.completed_at - startup.started_at).total_seconds()
                durations.append(duration)
        
        # Later startups should generally be faster due to caching
        if len(durations) >= 3:
            early_avg = sum(durations[:2]) / 2
            later_avg = sum(durations[-2:]) / 2
            # Allow some variance, but later ones should be faster
            assert later_avg <= early_avg * 1.2  # Within 20% variance
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, production_manager):
        """Test error recovery in complex scenarios"""
        # Create a mix of successful and failing startups
        configs = [
            {"industry": "Valid", "category": "SaaS", "template": "neoforge"},
            {"industry": "Valid", "category": "SaaS", "template": "neoforge"},
        ]
        
        startup_ids = []
        
        # Create startups
        for i, config in enumerate(configs):
            startup_id = await production_manager.create_startup(f"recovery-test-{i}", config)
            startup_ids.append(startup_id)
        
        # Simulate error in one startup by mocking a phase
        if len(startup_ids) > 1:
            # Let the first one succeed, force the second to fail
            original_phase = production_manager._phase_architecture_design
            
            call_count = 0
            async def selective_failing_phase(startup_id, config):
                nonlocal call_count
                call_count += 1
                if call_count == 2:  # Fail the second call
                    raise RuntimeError("Simulated architecture failure")
                return await original_phase(startup_id, config)
            
            production_manager._phase_architecture_design = selective_failing_phase
            
            # Wait for completion
            tasks = [production_manager.running_tasks.get(sid) for sid in startup_ids if sid in production_manager.running_tasks]
            if tasks:
                await asyncio.gather(*tasks)
            
            # Restore original method
            production_manager._phase_architecture_design = original_phase
            
            # Verify mixed results
            startups = [await production_manager.get_startup_status(sid) for sid in startup_ids]
            
            success_count = sum(1 for s in startups if s.status == StartupStatus.COMPLETED)
            failure_count = sum(1 for s in startups if s.status == StartupStatus.FAILED)
            
            assert success_count >= 1  # At least one should succeed
            assert failure_count >= 1  # At least one should fail
            
            # Verify error messages are captured
            failed_startups = [s for s in startups if s.status == StartupStatus.FAILED]
            for failed_startup in failed_startups:
                assert failed_startup.error_message is not None
                assert "architecture failure" in failed_startup.error_message
        
        # Verify resource cleanup for all startups (successful and failed)
        resource_usage = await production_manager.get_resource_usage()
        assert resource_usage["active_startups"] == 0
        assert len(resource_usage["used_ports"]) == 0
        assert resource_usage["temp_dirs"] == 0
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_production_scale_simulation(self):
        """Test production-scale scenario with realistic parameters"""
        # Create manager with production settings
        manager = MultiStartupManager(max_concurrent=3)  # Conservative for CI
        
        await manager.optimize_performance()
        
        # Simulate a day's worth of startup creation requests
        startup_configs = [
            {"industry": "FinTech", "category": "Payments", "template": "neoforge"},
            {"industry": "HealthTech", "category": "Telemedicine", "template": "neoforge"},
            {"industry": "EdTech", "category": "LMS", "template": "neoforge"},
            {"industry": "RetailTech", "category": "Inventory", "template": "neoforge"},
            {"industry": "PropTech", "category": "Management", "template": "neoforge"},
        ]
        
        # Track performance metrics
        startup_ids = []
        start_time = time.time()
        
        # Create startups in batches (simulating user requests)
        for i, config in enumerate(startup_configs):
            startup_id = await manager.create_startup(f"production-scale-{i}", config)
            startup_ids.append(startup_id)
            
            # Small delay to simulate realistic request timing
            await asyncio.sleep(0.5)
        
        # Wait for all to complete
        timeout = 300  # 5 minutes timeout
        check_start = time.time()
        
        while any(sid in manager.running_tasks for sid in startup_ids):
            if time.time() - check_start > timeout:
                break
            await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        
        # Analyze results
        startups = []
        for startup_id in startup_ids:
            startup = await manager.get_startup_status(startup_id)
            startups.append(startup)
        
        completed = [s for s in startups if s.status == StartupStatus.COMPLETED]
        failed = [s for s in startups if s.status == StartupStatus.FAILED]
        
        # Production quality metrics
        success_rate = len(completed) / len(startups)
        assert success_rate >= 0.8  # At least 80% success rate
        
        if completed:
            durations = []
            for startup in completed:
                if startup.started_at and startup.completed_at:
                    duration = (startup.completed_at - startup.started_at).total_seconds()
                    durations.append(duration)
            
            if durations:
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                
                # Performance targets
                assert avg_duration <= 30  # Average under 30 seconds
                assert max_duration <= 60   # Max under 60 seconds
        
        # Resource cleanup verification
        final_usage = await manager.get_resource_usage()
        assert final_usage["active_startups"] == 0
        assert len(final_usage["used_ports"]) == 0
        assert final_usage["temp_dirs"] == 0


@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for the test module"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])