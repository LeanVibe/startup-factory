#!/usr/bin/env python3
"""
StartupManager - Central coordination for multi-startup orchestration
Manages creation, lifecycle, and coordination of multiple startups with resource isolation.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .core_types import (
    IStartupManager, IResourceAllocator,
    StartupConfig, StartupInstance, StartupStatus, ResourceAllocation,
    InvalidConfigError, ConcurrencyLimitError, StartupNotFoundError,
    generate_startup_id, validate_startup_config
)
from .resource_allocator import ResourceAllocator
from .state_manager import StateManager


logger = logging.getLogger(__name__)


class StartupManager(IStartupManager):
    """
    Central manager for multi-startup orchestration with resource isolation
    
    Features:
    - Supports up to 5 concurrent startups
    - Resource conflict prevention
    - State persistence and recovery
    - Comprehensive validation and error handling
    """
    
    def __init__(self, max_concurrent: int = 5, state_dir: str = "./startup_states"):
        """
        Initialize StartupManager
        
        Args:
            max_concurrent: Maximum number of concurrent startups (default: 5)
            state_dir: Directory for state persistence
        """
        self.max_concurrent = max_concurrent
        self.registry: Dict[str, StartupInstance] = {}
        self.resource_allocator = ResourceAllocator()
        self.state_manager = StateManager(state_dir)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self._lock = asyncio.Lock()
        
        # Track startup names to prevent duplicates
        self._startup_names: Set[str] = set()
        
        logger.info(f"StartupManager initialized with max_concurrent={max_concurrent}")
    
    async def initialize(self) -> None:
        """Initialize the startup manager and restore state"""
        logger.info("Initializing StartupManager...")
        
        # Initialize resource allocator
        await self.resource_allocator.initialize()
        
        # Restore state from persistence
        await self._restore_state()
        
        logger.info(f"StartupManager initialized with {len(self.registry)} existing startups")
    
    async def create_startup(self, config: StartupConfig) -> str:
        """
        Create new startup with resource allocation and validation
        
        Args:
            config: Startup configuration
            
        Returns:
            str: Unique startup ID
            
        Raises:
            InvalidConfigError: If configuration is invalid
            ConcurrencyLimitError: If maximum concurrent startups exceeded
            InsufficientResourcesError: If resources unavailable
        """
        async with self._lock:
            # Validate configuration
            validation_errors = validate_startup_config(config)
            if validation_errors:
                raise InvalidConfigError(f"Configuration errors: {'; '.join(validation_errors)}")
            
            # Check concurrency limit
            active_count = len([s for s in self.registry.values() 
                              if s.status in [StartupStatus.INITIALIZING, StartupStatus.ACTIVE]])
            if active_count >= self.max_concurrent:
                raise ConcurrencyLimitError(
                    f"Maximum {self.max_concurrent} concurrent startups allowed. "
                    f"Currently active: {active_count}"
                )
            
            # Check for duplicate names
            if config.name.lower() in self._startup_names:
                raise InvalidConfigError(f"Startup name '{config.name}' already exists")
            
            # Check resource availability
            if not await self.resource_allocator.check_availability(config.resource_requirements):
                raise InsufficientResourcesError("Insufficient resources available")
            
            # Generate unique ID
            startup_id = generate_startup_id()
            
            try:
                # Allocate resources
                allocation = await self.resource_allocator.allocate(startup_id, config.resource_requirements)
                
                # Create startup instance
                instance = StartupInstance(
                    id=startup_id,
                    config=config,
                    status=StartupStatus.INITIALIZING,
                    resource_allocation=allocation,
                    current_phase=0,
                    state={"initialized": True},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # Register startup
                self.registry[startup_id] = instance
                self._startup_names.add(config.name.lower())
                
                # Persist state
                await self.state_manager.save_startup_state(startup_id, instance)
                
                logger.info(f"Created startup '{config.name}' with ID {startup_id}")
                
                # Update status to ACTIVE
                await self.update_startup_status(startup_id, StartupStatus.ACTIVE)
                
                return startup_id
                
            except Exception as e:
                # Cleanup on failure
                if startup_id in self.registry:
                    del self.registry[startup_id]
                self._startup_names.discard(config.name.lower())
                
                try:
                    await self.resource_allocator.deallocate(startup_id)
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup resources for {startup_id}: {cleanup_error}")
                
                logger.error(f"Failed to create startup '{config.name}': {e}")
                raise
    
    async def get_startup(self, startup_id: str) -> StartupInstance:
        """
        Get startup instance by ID
        
        Args:
            startup_id: Unique startup identifier
            
        Returns:
            StartupInstance: The startup instance
            
        Raises:
            StartupNotFoundError: If startup not found
        """
        if startup_id not in self.registry:
            raise StartupNotFoundError(f"Startup {startup_id} not found")
        
        return self.registry[startup_id]
    
    async def get_active_startups(self) -> List[StartupInstance]:
        """
        Get all active startups
        
        Returns:
            List[StartupInstance]: List of active startup instances
        """
        return [
            startup for startup in self.registry.values()
            if startup.status in [StartupStatus.INITIALIZING, StartupStatus.ACTIVE]
        ]
    
    async def get_all_startups(self) -> List[StartupInstance]:
        """
        Get all startups regardless of status
        
        Returns:
            List[StartupInstance]: List of all startup instances
        """
        return list(self.registry.values())
    
    async def update_startup_status(self, startup_id: str, status: StartupStatus) -> None:
        """
        Update startup status
        
        Args:
            startup_id: Unique startup identifier
            status: New status
            
        Raises:
            StartupNotFoundError: If startup not found
        """
        if startup_id not in self.registry:
            raise StartupNotFoundError(f"Startup {startup_id} not found")
        
        startup = self.registry[startup_id]
        old_status = startup.status
        startup.status = status
        startup.updated_at = datetime.utcnow()
        
        # Persist state change
        await self.state_manager.save_startup_state(startup_id, startup)
        
        logger.info(f"Updated startup {startup_id} status: {old_status} -> {status}")
    
    async def update_startup_state(self, startup_id: str, state_updates: Dict[str, any]) -> None:
        """
        Update startup state data
        
        Args:
            startup_id: Unique startup identifier
            state_updates: Dictionary of state updates
            
        Raises:
            StartupNotFoundError: If startup not found
        """
        if startup_id not in self.registry:
            raise StartupNotFoundError(f"Startup {startup_id} not found")
        
        startup = self.registry[startup_id]
        startup.state.update(state_updates)
        startup.updated_at = datetime.utcnow()
        
        # Persist state change
        await self.state_manager.save_startup_state(startup_id, startup)
        
        logger.debug(f"Updated state for startup {startup_id}: {list(state_updates.keys())}")
    
    async def increment_error_count(self, startup_id: str, error_message: str) -> None:
        """
        Increment error count for a startup
        
        Args:
            startup_id: Unique startup identifier
            error_message: Error message
        """
        if startup_id not in self.registry:
            raise StartupNotFoundError(f"Startup {startup_id} not found")
        
        startup = self.registry[startup_id]
        startup.error_count += 1
        startup.last_error = error_message
        startup.updated_at = datetime.utcnow()
        
        # Auto-suspend if too many errors
        if startup.error_count >= 5:
            await self.update_startup_status(startup_id, StartupStatus.FAILED)
            logger.warning(f"Startup {startup_id} failed due to excessive errors")
        
        await self.state_manager.save_startup_state(startup_id, startup)
        
        logger.warning(f"Error in startup {startup_id} (count: {startup.error_count}): {error_message}")
    
    async def delete_startup(self, startup_id: str) -> None:
        """
        Delete startup and cleanup resources
        
        Args:
            startup_id: Unique startup identifier
            
        Raises:
            StartupNotFoundError: If startup not found
        """
        if startup_id not in self.registry:
            raise StartupNotFoundError(f"Startup {startup_id} not found")
        
        startup = self.registry[startup_id]
        
        try:
            # Deallocate resources
            await self.resource_allocator.deallocate(startup_id)
        except Exception as e:
            logger.error(f"Failed to deallocate resources for {startup_id}: {e}")
        
        try:
            # Remove from state persistence
            await self.state_manager.delete_startup_state(startup_id)
        except Exception as e:
            logger.error(f"Failed to delete state for {startup_id}: {e}")
        
        # Remove from registry
        self._startup_names.discard(startup.config.name.lower())
        del self.registry[startup_id]
        
        logger.info(f"Deleted startup {startup_id} ({startup.config.name})")
    
    async def get_startup_stats(self) -> Dict[str, any]:
        """
        Get statistics about managed startups
        
        Returns:
            Dict with startup statistics
        """
        startups = list(self.registry.values())
        
        status_counts = {}
        for status in StartupStatus:
            status_counts[status.value] = len([s for s in startups if s.status == status])
        
        total_memory = sum(s.resource_allocation.memory_mb for s in startups)
        total_cpu = sum(s.resource_allocation.cpu_cores for s in startups)
        
        return {
            "total_startups": len(startups),
            "status_breakdown": status_counts,
            "active_startups": status_counts[StartupStatus.ACTIVE.value] + status_counts[StartupStatus.INITIALIZING.value],
            "max_concurrent": self.max_concurrent,
            "resource_usage": {
                "total_memory_mb": total_memory,
                "total_cpu_cores": total_cpu,
                "allocated_ports": sum(len(s.resource_allocation.ports) for s in startups)
            }
        }
    
    async def health_check(self) -> Dict[str, any]:
        """
        Perform health check on the startup manager
        
        Returns:
            Dict with health status
        """
        try:
            stats = await self.get_startup_stats()
            resource_health = await self.resource_allocator.health_check()
            
            # Check for any failed startups
            failed_startups = [s for s in self.registry.values() if s.status == StartupStatus.FAILED]
            
            health_status = {
                "healthy": True,
                "startup_manager": {
                    "active_startups": stats["active_startups"],
                    "failed_startups": len(failed_startups),
                    "registry_size": len(self.registry)
                },
                "resource_allocator": resource_health,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Mark unhealthy if too many failures
            if len(failed_startups) > 2:
                health_status["healthy"] = False
                health_status["issues"] = [f"Too many failed startups: {len(failed_startups)}"]
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _restore_state(self) -> None:
        """Restore startup state from persistence"""
        try:
            restored_startups = await self.state_manager.restore_all_states()
            
            for startup_id, instance in restored_startups.items():
                self.registry[startup_id] = instance
                self._startup_names.add(instance.config.name.lower())
                
                # Restore resource allocation
                try:
                    await self.resource_allocator.restore_allocation(startup_id, instance.resource_allocation)
                except Exception as e:
                    logger.error(f"Failed to restore resources for {startup_id}: {e}")
                    # Mark startup as failed if resources can't be restored
                    instance.status = StartupStatus.FAILED
                    instance.last_error = f"Resource restoration failed: {e}"
            
            logger.info(f"Restored {len(restored_startups)} startups from persistence")
            
        except Exception as e:
            logger.error(f"Failed to restore state: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup resources and save state"""
        logger.info("Cleaning up StartupManager...")
        
        # Save all current states
        for startup_id, instance in self.registry.items():
            try:
                await self.state_manager.save_startup_state(startup_id, instance)
            except Exception as e:
                logger.error(f"Failed to save state for {startup_id}: {e}")
        
        # Cleanup resource allocator
        await self.resource_allocator.cleanup()
        
        logger.info("StartupManager cleanup completed")


# Convenience functions for common operations
async def create_test_startup(manager: StartupManager, name: str = "test-startup") -> str:
    """Create a test startup for development/testing"""
    config = StartupConfig(
        name=name,
        industry="technology",
        category="test",
        template="neoforge",
        founder_profile={
            "skills": "Software development",
            "experience": "Testing environment"
        },
        resource_requirements={
            "memory_mb": 500,
            "cpu_cores": 0.5,
            "storage_gb": 2,
            "port_count": 3
        }
    )
    
    return await manager.create_startup(config)