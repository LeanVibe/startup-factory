#!/usr/bin/env python3
"""
Multi-Startup Resource Manager
Manages resources for concurrent startup creation with optimization
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import psutil
import tempfile
import socket
from contextlib import contextmanager
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StartupStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ResourceLimits:
    """Resource limits for startup creation"""
    max_memory_mb: int = 500
    max_cpu_percent: int = 25
    max_disk_mb: int = 1000
    max_network_mb: int = 100
    timeout_minutes: int = 30

@dataclass
class StartupInstance:
    """Represents a single startup instance"""
    id: str
    name: str
    status: StartupStatus = StartupStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_port: Optional[int] = None
    work_dir: Optional[Path] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    process_id: Optional[int] = None

class ResourcePool:
    """Manages shared resources for concurrent startups"""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.available_ports = list(range(8000, 8100))  # Port pool
        self.used_ports: set = set()
        self.temp_dirs: Dict[str, Path] = {}
        self.resource_locks = asyncio.Semaphore(max_concurrent)
        
    async def acquire_port(self) -> int:
        """Acquire an available port"""
        for port in self.available_ports:
            if port not in self.used_ports and not self._is_port_in_use(port):
                self.used_ports.add(port)
                return port
        raise RuntimeError("No available ports")
    
    def release_port(self, port: int):
        """Release a port back to the pool"""
        self.used_ports.discard(port)
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    async def acquire_work_dir(self, startup_id: str) -> Path:
        """Acquire a work directory for a startup"""
        work_dir = Path(tempfile.mkdtemp(prefix=f"startup_{startup_id}_"))
        self.temp_dirs[startup_id] = work_dir
        return work_dir
    
    def release_work_dir(self, startup_id: str):
        """Release and cleanup work directory"""
        if startup_id in self.temp_dirs:
            work_dir = self.temp_dirs[startup_id]
            try:
                import shutil
                shutil.rmtree(work_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup work directory {work_dir}: {e}")
            finally:
                del self.temp_dirs[startup_id]

class PerformanceOptimizer:
    """Optimizes performance for concurrent startup creation"""
    
    def __init__(self):
        self.api_cache: Dict[str, Any] = {}
        self.template_cache: Dict[str, Any] = {}
        self.cache_ttl = 3600  # 1 hour
        
    async def cached_api_call(self, cache_key: str, api_func, *args, **kwargs) -> Any:
        """Cached API call to reduce redundant requests"""
        if cache_key in self.api_cache:
            cached_result, timestamp = self.api_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"Using cached result for {cache_key}")
                return cached_result
        
        # Make API call
        result = await api_func(*args, **kwargs)
        self.api_cache[cache_key] = (result, time.time())
        return result
    
    async def parallel_api_calls(self, calls: List[Tuple[str, Any]]) -> List[Any]:
        """Execute multiple API calls in parallel"""
        tasks = [asyncio.create_task(func(*args)) for func, args in calls]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def precompile_templates(self, template_dirs: List[Path]):
        """Precompile templates for faster processing"""
        for template_dir in template_dirs:
            if template_dir.exists():
                # Mock template precompilation
                template_key = str(template_dir)
                self.template_cache[template_key] = {
                    "compiled": True,
                    "timestamp": time.time()
                }
                logger.info(f"Precompiled template: {template_key}")

class MultiStartupManager:
    """Main manager for concurrent startup creation"""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.resource_pool = ResourcePool(max_concurrent)
        self.optimizer = PerformanceOptimizer()
        self.startups: Dict[str, StartupInstance] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.resource_limits = ResourceLimits()
        
    async def create_startup(self, name: str, config: Dict[str, Any]) -> str:
        """Create a new startup instance"""
        startup_id = str(uuid.uuid4())
        startup = StartupInstance(
            id=startup_id,
            name=name
        )
        
        self.startups[startup_id] = startup
        
        # Start startup creation task
        task = asyncio.create_task(self._create_startup_task(startup_id, config))
        self.running_tasks[startup_id] = task
        
        logger.info(f"Created startup {name} with ID {startup_id}")
        return startup_id
    
    async def _create_startup_task(self, startup_id: str, config: Dict[str, Any]):
        """Task that creates a single startup"""
        startup = self.startups[startup_id]
        
        try:
            # Acquire resources
            async with self.resource_pool.resource_locks:
                startup.status = StartupStatus.RUNNING
                startup.started_at = datetime.now()
                
                # Allocate resources
                startup.assigned_port = await self.resource_pool.acquire_port()
                startup.work_dir = await self.resource_pool.acquire_work_dir(startup_id)
                
                logger.info(f"Starting startup {startup.name} (ID: {startup_id})")
                
                # Execute startup creation phases
                await self._execute_startup_phases(startup_id, config)
                
                # Mark as completed
                startup.status = StartupStatus.COMPLETED
                startup.completed_at = datetime.now()
                
                logger.info(f"Completed startup {startup.name} in {(startup.completed_at - startup.started_at).total_seconds():.1f}s")
                
        except Exception as e:
            startup.status = StartupStatus.FAILED
            startup.error_message = str(e)
            logger.error(f"Failed to create startup {startup.name}: {e}")
        finally:
            # Release resources
            if startup.assigned_port:
                self.resource_pool.release_port(startup.assigned_port)
            if startup_id in self.resource_pool.temp_dirs:
                self.resource_pool.release_work_dir(startup_id)
            
            # Remove from running tasks
            if startup_id in self.running_tasks:
                del self.running_tasks[startup_id]
    
    async def _execute_startup_phases(self, startup_id: str, config: Dict[str, Any]):
        """Execute all phases of startup creation"""
        startup = self.startups[startup_id]
        
        # Phase 1: Market Research (optimized with caching)
        await self._phase_market_research(startup_id, config)
        
        # Phase 2: MVP Specification (parallel with other independent tasks)
        await self._phase_mvp_specification(startup_id, config)
        
        # Phase 3: Architecture Design
        await self._phase_architecture_design(startup_id, config)
        
        # Phase 4: Project Generation (optimized with template caching)
        await self._phase_project_generation(startup_id, config)
        
        # Phase 5: Deployment Preparation
        await self._phase_deployment_preparation(startup_id, config)
    
    async def _phase_market_research(self, startup_id: str, config: Dict[str, Any]):
        """Execute market research phase with caching"""
        startup = self.startups[startup_id]
        
        # Use cached result if available
        cache_key = f"market_research_{config.get('industry', 'default')}_{config.get('category', 'default')}"
        
        # Mock market research API call
        async def market_research_call():
            await asyncio.sleep(2)  # Simulate API call
            return {"market_size": "50M", "growth_rate": "15%"}
        
        result = await self.optimizer.cached_api_call(cache_key, market_research_call)
        startup.resource_usage["market_research"] = result
        
        logger.info(f"Completed market research for {startup.name}")
    
    async def _phase_mvp_specification(self, startup_id: str, config: Dict[str, Any]):
        """Execute MVP specification phase"""
        startup = self.startups[startup_id]
        
        # Mock MVP specification
        await asyncio.sleep(3)  # Simulate AI processing
        startup.resource_usage["mvp_spec"] = {"features": 5, "complexity": "medium"}
        
        logger.info(f"Completed MVP specification for {startup.name}")
    
    async def _phase_architecture_design(self, startup_id: str, config: Dict[str, Any]):
        """Execute architecture design phase"""
        startup = self.startups[startup_id]
        
        # Mock architecture design
        await asyncio.sleep(2)  # Simulate AI processing
        startup.resource_usage["architecture"] = {"components": 8, "databases": 2}
        
        logger.info(f"Completed architecture design for {startup.name}")
    
    async def _phase_project_generation(self, startup_id: str, config: Dict[str, Any]):
        """Execute project generation phase with template optimization"""
        startup = self.startups[startup_id]
        
        # Use precompiled template if available
        template_name = config.get("template", "neoforge")
        
        # Mock project generation
        await asyncio.sleep(1)  # Reduced time due to template caching
        startup.resource_usage["project_generation"] = {"files": 50, "size_mb": 10}
        
        logger.info(f"Completed project generation for {startup.name}")
    
    async def _phase_deployment_preparation(self, startup_id: str, config: Dict[str, Any]):
        """Execute deployment preparation phase"""
        startup = self.startups[startup_id]
        
        # Mock deployment preparation
        await asyncio.sleep(1)  # Simulate deployment config
        startup.resource_usage["deployment"] = {"platform": "docker", "containers": 3}
        
        logger.info(f"Completed deployment preparation for {startup.name}")
    
    async def get_startup_status(self, startup_id: str) -> Optional[StartupInstance]:
        """Get status of a specific startup"""
        return self.startups.get(startup_id)
    
    async def list_startups(self) -> List[StartupInstance]:
        """List all startups"""
        return list(self.startups.values())
    
    async def cancel_startup(self, startup_id: str) -> bool:
        """Cancel a startup creation"""
        if startup_id in self.running_tasks:
            task = self.running_tasks[startup_id]
            task.cancel()
            
            startup = self.startups[startup_id]
            startup.status = StartupStatus.CANCELLED
            
            logger.info(f"Cancelled startup {startup.name}")
            return True
        return False
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        
        return {
            "memory_usage_mb": memory.used / (1024**2),
            "memory_percent": memory.percent,
            "cpu_percent": cpu,
            "active_startups": len([s for s in self.startups.values() if s.status == StartupStatus.RUNNING]),
            "total_startups": len(self.startups),
            "used_ports": list(self.resource_pool.used_ports),
            "temp_dirs": len(self.resource_pool.temp_dirs)
        }
    
    async def optimize_performance(self):
        """Run performance optimizations"""
        # Precompile templates
        template_dirs = [
            Path("../templates/neoforge"),
            Path("../templates/reactnext")
        ]
        self.optimizer.precompile_templates(template_dirs)
        
        # Clear old cache entries
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.optimizer.api_cache.items()
            if current_time - timestamp > self.optimizer.cache_ttl
        ]
        for key in expired_keys:
            del self.optimizer.api_cache[key]
        
        logger.info("Performance optimization completed")
    
    async def benchmark_performance(self, num_startups: int = 5) -> Dict[str, Any]:
        """Benchmark performance with multiple concurrent startups"""
        logger.info(f"Starting performance benchmark with {num_startups} startups")
        
        start_time = time.time()
        startup_ids = []
        
        # Create multiple startups
        for i in range(num_startups):
            config = {
                "industry": "Tech",
                "category": "SaaS",
                "template": "neoforge"
            }
            startup_id = await self.create_startup(f"benchmark_startup_{i+1}", config)
            startup_ids.append(startup_id)
        
        # Wait for all to complete
        while any(s.status == StartupStatus.RUNNING for s in self.startups.values()):
            await asyncio.sleep(0.5)
        
        total_time = time.time() - start_time
        
        # Collect results
        results = {
            "total_time": total_time,
            "num_startups": num_startups,
            "avg_time_per_startup": total_time / num_startups,
            "successful": len([s for s in self.startups.values() if s.status == StartupStatus.COMPLETED]),
            "failed": len([s for s in self.startups.values() if s.status == StartupStatus.FAILED]),
            "resource_usage": await self.get_resource_usage(),
            "startup_details": {}
        }
        
        for startup_id in startup_ids:
            startup = self.startups[startup_id]
            if startup.started_at and startup.completed_at:
                duration = (startup.completed_at - startup.started_at).total_seconds()
                results["startup_details"][startup_id] = {
                    "name": startup.name,
                    "duration": duration,
                    "status": startup.status.value,
                    "resource_usage": startup.resource_usage
                }
        
        logger.info(f"Benchmark completed: {results['successful']}/{num_startups} successful in {total_time:.1f}s")
        return results

async def main():
    """Main function for testing"""
    print("🚀 Multi-Startup Manager Test")
    print("=" * 30)
    
    # Create manager
    manager = MultiStartupManager(max_concurrent=3)
    
    # Optimize performance
    await manager.optimize_performance()
    
    # Run benchmark
    results = await manager.benchmark_performance(num_startups=3)
    
    # Display results
    print(f"\n📊 Benchmark Results:")
    print(f"• Total time: {results['total_time']:.1f}s")
    print(f"• Average per startup: {results['avg_time_per_startup']:.1f}s")
    print(f"• Success rate: {results['successful']}/{results['num_startups']}")
    print(f"• Memory usage: {results['resource_usage']['memory_usage_mb']:.1f}MB")
    print(f"• CPU usage: {results['resource_usage']['cpu_percent']:.1f}%")
    
    # Show resource usage
    resource_usage = await manager.get_resource_usage()
    print(f"\n🔧 Resource Usage:")
    print(f"• Active startups: {resource_usage['active_startups']}")
    print(f"• Used ports: {resource_usage['used_ports']}")
    print(f"• Temp directories: {resource_usage['temp_dirs']}")

if __name__ == "__main__":
    asyncio.run(main())