#!/usr/bin/env python3
"""
ResourceAllocator - Dynamic resource allocation with conflict prevention
Manages memory, CPU, ports, and database namespaces for multiple startups.
"""

import asyncio
import logging
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Set

try:
    # Try relative imports first (package mode)
    from .core_types import (
        IResourceAllocator, ResourceAllocation, APIQuota,
        InsufficientMemoryError, PortConflictError, InsufficientResourcesError
    )
except ImportError:
    # Fall back to absolute imports (script mode)
    from core_types import (
        IResourceAllocator, ResourceAllocation, APIQuota,
        InsufficientMemoryError, PortConflictError, InsufficientResourcesError
    )


logger = logging.getLogger(__name__)


class PortAllocator:
    """Manages port allocation to prevent conflicts"""
    
    def __init__(self, base_port: int = 3000, port_range: int = 1000):
        """
        Initialize port allocator
        
        Args:
            base_port: Starting port number (default: 3000)
            port_range: Number of ports in the range (default: 1000)
        """
        self.base_port = base_port
        self.port_range = port_range
        self.allocated_ports: Set[int] = set()
        self._lock = asyncio.Lock()
        
        logger.info(f"PortAllocator initialized: ports {base_port}-{base_port + port_range - 1}")
    
    async def allocate_ports(self, count: int) -> List[int]:
        """
        Allocate a contiguous block of ports
        
        Args:
            count: Number of ports to allocate
            
        Returns:
            List[int]: Allocated port numbers
            
        Raises:
            PortConflictError: If insufficient ports available
        """
        async with self._lock:
            if count <= 0:
                raise ValueError("Port count must be positive")
            
            # Find available contiguous block
            for start_port in range(self.base_port, self.base_port + self.port_range - count + 1):
                block = list(range(start_port, start_port + count))
                
                # Check if all ports in block are available
                if not any(port in self.allocated_ports for port in block):
                    # Allocate the block
                    for port in block:
                        self.allocated_ports.add(port)
                    
                    logger.debug(f"Allocated ports: {block}")
                    return block
            
            raise PortConflictError(
                f"Cannot allocate {count} contiguous ports. "
                f"Allocated: {len(self.allocated_ports)}/{self.port_range}"
            )
    
    async def deallocate_ports(self, ports: List[int]) -> None:
        """
        Deallocate ports
        
        Args:
            ports: List of port numbers to deallocate
        """
        async with self._lock:
            for port in ports:
                self.allocated_ports.discard(port)
            
            logger.debug(f"Deallocated ports: {ports}")
    
    async def get_allocated_ports(self) -> Set[int]:
        """Get currently allocated ports"""
        return self.allocated_ports.copy()
    
    async def get_available_count(self) -> int:
        """Get number of available ports"""
        return self.port_range - len(self.allocated_ports)


class MemoryMonitor:
    """Monitors system memory usage and availability"""
    
    def __init__(self, safety_margin_mb: int = 1024):
        """
        Initialize memory monitor
        
        Args:
            safety_margin_mb: Safety margin to keep free (default: 1GB)
        """
        self.safety_margin_mb = safety_margin_mb
        self.allocated_memory: Dict[str, int] = {}  # startup_id -> memory_mb
        self._lock = asyncio.Lock()
        
        logger.info(f"MemoryMonitor initialized with {safety_margin_mb}MB safety margin")
    
    async def get_system_memory_info(self) -> Dict[str, int]:
        """Get system memory information in MB"""
        memory = psutil.virtual_memory()
        return {
            "total_mb": memory.total // (1024 * 1024),
            "available_mb": memory.available // (1024 * 1024),
            "used_mb": memory.used // (1024 * 1024),
            "percent_used": memory.percent
        }
    
    async def get_available_memory(self) -> int:
        """Get available memory for allocation in MB"""
        memory_info = await self.get_system_memory_info()
        allocated_total = sum(self.allocated_memory.values())
        
        # Available = system available - safety margin - already allocated
        available = memory_info["available_mb"] - self.safety_margin_mb - allocated_total
        return max(0, available)
    
    async def allocate_memory(self, startup_id: str, memory_mb: int) -> None:
        """
        Allocate memory for a startup
        
        Args:
            startup_id: Unique startup identifier
            memory_mb: Memory to allocate in MB
            
        Raises:
            InsufficientMemoryError: If insufficient memory available
        """
        async with self._lock:
            available = await self.get_available_memory()
            
            if memory_mb > available:
                memory_info = await self.get_system_memory_info()
                raise InsufficientMemoryError(
                    f"Insufficient memory: requested {memory_mb}MB, "
                    f"available {available}MB (system: {memory_info})"
                )
            
            self.allocated_memory[startup_id] = memory_mb
            logger.debug(f"Allocated {memory_mb}MB for startup {startup_id}")
    
    async def deallocate_memory(self, startup_id: str) -> None:
        """
        Deallocate memory for a startup
        
        Args:
            startup_id: Unique startup identifier
        """
        async with self._lock:
            if startup_id in self.allocated_memory:
                memory_mb = self.allocated_memory.pop(startup_id)
                logger.debug(f"Deallocated {memory_mb}MB for startup {startup_id}")
    
    async def get_allocation_info(self) -> Dict[str, any]:
        """Get memory allocation information"""
        memory_info = await self.get_system_memory_info()
        allocated_total = sum(self.allocated_memory.values())
        
        return {
            "system_memory": memory_info,
            "allocated_by_factory": allocated_total,
            "available_for_allocation": await self.get_available_memory(),
            "allocations": dict(self.allocated_memory),
            "safety_margin_mb": self.safety_margin_mb
        }


class DatabaseNamespaceManager:
    """Manages database namespaces for startup isolation"""
    
    def __init__(self):
        self.allocated_namespaces: Set[str] = set()
        self._lock = asyncio.Lock()
        
        logger.info("DatabaseNamespaceManager initialized")
    
    async def allocate_namespace(self, startup_id: str) -> str:
        """
        Allocate a unique database namespace
        
        Args:
            startup_id: Unique startup identifier
            
        Returns:
            str: Database namespace
        """
        async with self._lock:
            # Create namespace from startup ID
            namespace = f"startup_{startup_id.replace('-', '_').replace(' ', '_').lower()}"
            
            # Ensure uniqueness
            counter = 1
            original_namespace = namespace
            while namespace in self.allocated_namespaces:
                namespace = f"{original_namespace}_{counter}"
                counter += 1
            
            self.allocated_namespaces.add(namespace)
            logger.debug(f"Allocated database namespace: {namespace}")
            
            return namespace
    
    async def deallocate_namespace(self, namespace: str) -> None:
        """
        Deallocate a database namespace
        
        Args:
            namespace: Database namespace to deallocate
        """
        async with self._lock:
            self.allocated_namespaces.discard(namespace)
            logger.debug(f"Deallocated database namespace: {namespace}")
    
    async def get_allocated_namespaces(self) -> Set[str]:
        """Get currently allocated namespaces"""
        return self.allocated_namespaces.copy()


class ResourceAllocator(IResourceAllocator):
    """
    Dynamic resource allocator with conflict prevention
    
    Features:
    - Port allocation with conflict detection
    - Memory monitoring and allocation
    - Database namespace management
    - Resource usage tracking and limits
    """
    
    def __init__(self, base_port: int = 3000, port_range: int = 1000, safety_margin_mb: int = 1024):
        """
        Initialize resource allocator
        
        Args:
            base_port: Base port for allocation range
            port_range: Size of port allocation range
            safety_margin_mb: Memory safety margin in MB
        """
        self.port_allocator = PortAllocator(base_port, port_range)
        self.memory_monitor = MemoryMonitor(safety_margin_mb)
        self.namespace_manager = DatabaseNamespaceManager()
        self.allocations: Dict[str, ResourceAllocation] = {}
        self._lock = asyncio.Lock()
        
        logger.info("ResourceAllocator initialized")
    
    async def initialize(self) -> None:
        """Initialize the resource allocator"""
        logger.info("Initializing ResourceAllocator...")
        
        # Log initial system state
        memory_info = await self.memory_monitor.get_system_memory_info()
        available_ports = await self.port_allocator.get_available_count()
        
        logger.info(f"System memory: {memory_info['total_mb']}MB total, "
                   f"{memory_info['available_mb']}MB available")
        logger.info(f"Port range: {available_ports} ports available")
    
    async def check_availability(self, requirements: dict) -> bool:
        """
        Check if resources are available for allocation
        
        Args:
            requirements: Resource requirements dict
            
        Returns:
            bool: True if resources are available
        """
        try:
            # Check memory
            required_memory = requirements.get('memory_mb', 500)
            available_memory = await self.memory_monitor.get_available_memory()
            if required_memory > available_memory:
                logger.debug(f"Insufficient memory: need {required_memory}MB, have {available_memory}MB")
                return False
            
            # Check ports
            required_ports = requirements.get('port_count', 3)
            available_ports = await self.port_allocator.get_available_count()
            if required_ports > available_ports:
                logger.debug(f"Insufficient ports: need {required_ports}, have {available_ports}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking resource availability: {e}")
            return False
    
    async def allocate(self, startup_id: str, requirements: dict) -> ResourceAllocation:
        """
        Allocate resources for a startup
        
        Args:
            startup_id: Unique startup identifier
            requirements: Resource requirements dict
            
        Returns:
            ResourceAllocation: Allocated resources
            
        Raises:
            InsufficientResourcesError: If resources unavailable
        """
        async with self._lock:
            if startup_id in self.allocations:
                raise ValueError(f"Resources already allocated for startup {startup_id}")
            
            # Extract requirements with defaults
            memory_mb = requirements.get('memory_mb', 500)
            cpu_cores = requirements.get('cpu_cores', 0.5)
            storage_gb = requirements.get('storage_gb', 2)
            port_count = requirements.get('port_count', 3)
            api_calls_per_hour = requirements.get('api_calls_per_hour', 1000)
            cost_per_day = requirements.get('cost_per_day', 15.0)
            
            try:
                # Allocate memory
                await self.memory_monitor.allocate_memory(startup_id, memory_mb)
                
                # Allocate ports
                allocated_ports = await self.port_allocator.allocate_ports(port_count)
                
                # Allocate database namespace
                db_namespace = await self.namespace_manager.allocate_namespace(startup_id)
                
                # Create API quota
                api_quota = APIQuota(
                    calls_per_hour=api_calls_per_hour,
                    cost_per_day=cost_per_day,
                    current_calls=0,
                    current_cost=0.0,
                    reset_at=None
                )
                
                # Create allocation record
                allocation = ResourceAllocation(
                    startup_id=startup_id,
                    memory_mb=memory_mb,
                    cpu_cores=cpu_cores,
                    storage_gb=storage_gb,
                    ports=allocated_ports,
                    database_namespace=db_namespace,
                    api_quota=api_quota,
                    allocated_at=datetime.utcnow()
                )
                
                # Store allocation
                self.allocations[startup_id] = allocation
                
                logger.info(f"Allocated resources for startup {startup_id}: "
                           f"{memory_mb}MB, {cpu_cores} cores, ports {allocated_ports}, "
                           f"namespace {db_namespace}")
                
                return allocation
                
            except Exception as e:
                # Cleanup partial allocations on failure
                try:
                    await self.memory_monitor.deallocate_memory(startup_id)
                    if 'allocated_ports' in locals():
                        await self.port_allocator.deallocate_ports(allocated_ports)
                    if 'db_namespace' in locals():
                        await self.namespace_manager.deallocate_namespace(db_namespace)
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup after allocation failure: {cleanup_error}")
                
                logger.error(f"Failed to allocate resources for {startup_id}: {e}")
                raise InsufficientResourcesError(f"Resource allocation failed: {e}")
    
    async def deallocate(self, startup_id: str) -> None:
        """
        Release all resources for a startup
        
        Args:
            startup_id: Unique startup identifier
        """
        async with self._lock:
            if startup_id not in self.allocations:
                logger.warning(f"No allocation found for startup {startup_id}")
                return
            
            allocation = self.allocations[startup_id]
            
            try:
                # Deallocate memory
                await self.memory_monitor.deallocate_memory(startup_id)
                
                # Deallocate ports
                await self.port_allocator.deallocate_ports(allocation.ports)
                
                # Deallocate database namespace
                await self.namespace_manager.deallocate_namespace(allocation.database_namespace)
                
                # Remove allocation record
                del self.allocations[startup_id]
                
                logger.info(f"Deallocated all resources for startup {startup_id}")
                
            except Exception as e:
                logger.error(f"Failed to deallocate resources for {startup_id}: {e}")
                raise
    
    async def get_allocation(self, startup_id: str) -> Optional[ResourceAllocation]:
        """
        Get resource allocation for a startup
        
        Args:
            startup_id: Unique startup identifier
            
        Returns:
            Optional[ResourceAllocation]: Allocation if exists
        """
        return self.allocations.get(startup_id)
    
    async def restore_allocation(self, startup_id: str, allocation: ResourceAllocation) -> None:
        """
        Restore a resource allocation (used during state restoration)
        
        Args:
            startup_id: Unique startup identifier
            allocation: Resource allocation to restore
        """
        async with self._lock:
            try:
                # Restore memory allocation
                await self.memory_monitor.allocate_memory(startup_id, allocation.memory_mb)
                
                # Restore port allocation
                for port in allocation.ports:
                    self.port_allocator.allocated_ports.add(port)
                
                # Restore namespace allocation
                self.namespace_manager.allocated_namespaces.add(allocation.database_namespace)
                
                # Store allocation
                self.allocations[startup_id] = allocation
                
                logger.info(f"Restored resource allocation for startup {startup_id}")
                
            except Exception as e:
                logger.error(f"Failed to restore allocation for {startup_id}: {e}")
                raise
    
    async def get_resource_usage(self) -> Dict[str, any]:
        """
        Get current resource usage statistics
        
        Returns:
            Dict with resource usage information
        """
        memory_info = await self.memory_monitor.get_allocation_info()
        allocated_ports = await self.port_allocator.get_allocated_ports()
        allocated_namespaces = await self.namespace_manager.get_allocated_namespaces()
        
        return {
            "memory": memory_info,
            "ports": {
                "allocated_count": len(allocated_ports),
                "available_count": await self.port_allocator.get_available_count(),
                "allocated_ports": sorted(list(allocated_ports))
            },
            "database_namespaces": {
                "allocated_count": len(allocated_namespaces),
                "namespaces": sorted(list(allocated_namespaces))
            },
            "startup_allocations": len(self.allocations),
            "allocation_details": {
                startup_id: {
                    "memory_mb": alloc.memory_mb,
                    "cpu_cores": alloc.cpu_cores,
                    "ports": alloc.ports,
                    "namespace": alloc.database_namespace
                }
                for startup_id, alloc in self.allocations.items()
            }
        }
    
    async def health_check(self) -> Dict[str, any]:
        """
        Perform health check on resource allocator
        
        Returns:
            Dict with health status
        """
        try:
            usage = await self.get_resource_usage()
            memory_info = usage["memory"]["system_memory"]
            
            # Check for concerning resource usage
            issues = []
            if memory_info["percent_used"] > 90:
                issues.append(f"High memory usage: {memory_info['percent_used']}%")
            
            if usage["ports"]["available_count"] < 50:
                issues.append(f"Low port availability: {usage['ports']['available_count']} remaining")
            
            return {
                "healthy": len(issues) == 0,
                "issues": issues,
                "resource_usage": usage,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def cleanup(self) -> None:
        """Cleanup all resources"""
        logger.info("Cleaning up ResourceAllocator...")
        
        # Deallocate all resources
        startup_ids = list(self.allocations.keys())
        for startup_id in startup_ids:
            try:
                await self.deallocate(startup_id)
            except Exception as e:
                logger.error(f"Failed to cleanup resources for {startup_id}: {e}")
        
        logger.info("ResourceAllocator cleanup completed")