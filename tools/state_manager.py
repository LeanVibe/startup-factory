#!/usr/bin/env python3
"""
StateManager - Persistent state management for startup instances
Handles startup state persistence, recovery, and consistency across sessions.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .core_types import StartupInstance, StartupConfig, StartupStatus, ResourceAllocation, APIQuota

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages persistent state for startup instances
    
    Features:
    - JSON-based state persistence
    - Atomic file operations
    - State validation and recovery
    - Backup and versioning
    """
    
    def __init__(self, state_dir: str = "./startup_states"):
        """
        Initialize state manager
        
        Args:
            state_dir: Directory for state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        
        logger.info(f"StateManager initialized with state directory: {self.state_dir}")
    
    async def save_startup_state(self, startup_id: str, instance: StartupInstance) -> None:
        """
        Save startup state to persistent storage
        
        Args:
            startup_id: Unique startup identifier
            instance: Startup instance to save
        """
        async with self._lock:
            try:
                # Serialize instance to dict
                state_data = self._serialize_instance(instance)
                
                # Write to temporary file first (atomic operation)
                state_file = self.state_dir / f"{startup_id}.json"
                temp_file = self.state_dir / f"{startup_id}.json.tmp"
                
                with open(temp_file, 'w') as f:
                    json.dump(state_data, f, indent=2, default=str)
                
                # Atomic rename
                temp_file.rename(state_file)
                
                logger.debug(f"Saved state for startup {startup_id}")
                
            except Exception as e:
                logger.error(f"Failed to save state for {startup_id}: {e}")
                # Clean up temp file if it exists
                temp_file = self.state_dir / f"{startup_id}.json.tmp"
                if temp_file.exists():
                    temp_file.unlink()
                raise
    
    async def load_startup_state(self, startup_id: str) -> Optional[StartupInstance]:
        """
        Load startup state from persistent storage
        
        Args:
            startup_id: Unique startup identifier
            
        Returns:
            Optional[StartupInstance]: Loaded instance or None if not found
        """
        async with self._lock:
            try:
                state_file = self.state_dir / f"{startup_id}.json"
                
                if not state_file.exists():
                    return None
                
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Deserialize instance from dict
                instance = self._deserialize_instance(state_data)
                
                logger.debug(f"Loaded state for startup {startup_id}")
                return instance
                
            except Exception as e:
                logger.error(f"Failed to load state for {startup_id}: {e}")
                return None
    
    async def delete_startup_state(self, startup_id: str) -> None:
        """
        Delete startup state from persistent storage
        
        Args:
            startup_id: Unique startup identifier
        """
        async with self._lock:
            try:
                state_file = self.state_dir / f"{startup_id}.json"
                
                if state_file.exists():
                    # Create backup before deletion
                    backup_file = self.state_dir / f"{startup_id}.json.deleted"
                    state_file.rename(backup_file)
                    
                    logger.debug(f"Deleted state for startup {startup_id} (backup created)")
                else:
                    logger.warning(f"State file for {startup_id} not found")
                    
            except Exception as e:
                logger.error(f"Failed to delete state for {startup_id}: {e}")
                raise
    
    async def restore_all_states(self) -> Dict[str, StartupInstance]:
        """
        Restore all startup states from persistent storage
        
        Returns:
            Dict[str, StartupInstance]: Mapping of startup_id to instance
        """
        restored = {}
        
        try:
            # Find all state files
            state_files = list(self.state_dir.glob("*.json"))
            
            for state_file in state_files:
                if state_file.name.endswith('.tmp') or state_file.name.endswith('.deleted'):
                    continue
                
                startup_id = state_file.stem
                
                try:
                    instance = await self.load_startup_state(startup_id)
                    if instance:
                        restored[startup_id] = instance
                        logger.debug(f"Restored startup {startup_id}")
                except Exception as e:
                    logger.error(f"Failed to restore startup {startup_id}: {e}")
            
            logger.info(f"Restored {len(restored)} startups from persistent storage")
            return restored
            
        except Exception as e:
            logger.error(f"Failed to restore states: {e}")
            return {}
    
    async def list_saved_startups(self) -> list[str]:
        """
        List all startup IDs with saved state
        
        Returns:
            List[str]: List of startup IDs
        """
        try:
            state_files = list(self.state_dir.glob("*.json"))
            startup_ids = []
            
            for state_file in state_files:
                if not state_file.name.endswith('.tmp') and not state_file.name.endswith('.deleted'):
                    startup_ids.append(state_file.stem)
            
            return sorted(startup_ids)
            
        except Exception as e:
            logger.error(f"Failed to list saved startups: {e}")
            return []
    
    async def cleanup_old_states(self, max_age_days: int = 30) -> int:
        """
        Clean up old state files
        
        Args:
            max_age_days: Maximum age of state files to keep
            
        Returns:
            int: Number of files cleaned up
        """
        try:
            cleanup_count = 0
            cutoff_time = datetime.utcnow().timestamp() - (max_age_days * 24 * 60 * 60)
            
            for state_file in self.state_dir.glob("*.json"):
                if state_file.stat().st_mtime < cutoff_time:
                    state_file.unlink()
                    cleanup_count += 1
                    logger.debug(f"Cleaned up old state file: {state_file.name}")
            
            logger.info(f"Cleaned up {cleanup_count} old state files")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old states: {e}")
            return 0
    
    def _serialize_instance(self, instance: StartupInstance) -> dict:
        """
        Serialize startup instance to dictionary
        
        Args:
            instance: StartupInstance to serialize
            
        Returns:
            dict: Serialized instance data
        """
        return {
            "id": instance.id,
            "config": {
                "name": instance.config.name,
                "industry": instance.config.industry,
                "category": instance.config.category,
                "template": instance.config.template,
                "founder_profile": instance.config.founder_profile,
                "resource_requirements": instance.config.resource_requirements,
                "target_completion_date": instance.config.target_completion_date.isoformat() if instance.config.target_completion_date else None,
                "budget_limit": instance.config.budget_limit
            },
            "status": instance.status.value,
            "resource_allocation": {
                "startup_id": instance.resource_allocation.startup_id,
                "memory_mb": instance.resource_allocation.memory_mb,
                "cpu_cores": instance.resource_allocation.cpu_cores,
                "storage_gb": instance.resource_allocation.storage_gb,
                "ports": instance.resource_allocation.ports,
                "database_namespace": instance.resource_allocation.database_namespace,
                "api_quota": {
                    "calls_per_hour": instance.resource_allocation.api_quota.calls_per_hour,
                    "cost_per_day": instance.resource_allocation.api_quota.cost_per_day,
                    "current_calls": instance.resource_allocation.api_quota.current_calls,
                    "current_cost": instance.resource_allocation.api_quota.current_cost,
                    "reset_at": instance.resource_allocation.api_quota.reset_at.isoformat() if instance.resource_allocation.api_quota.reset_at else None
                },
                "allocated_at": instance.resource_allocation.allocated_at.isoformat(),
                "expires_at": instance.resource_allocation.expires_at.isoformat() if instance.resource_allocation.expires_at else None
            },
            "current_phase": instance.current_phase,
            "state": instance.state,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
            "error_count": instance.error_count,
            "last_error": instance.last_error
        }
    
    def _deserialize_instance(self, data: dict) -> StartupInstance:
        """
        Deserialize startup instance from dictionary
        
        Args:
            data: Serialized instance data
            
        Returns:
            StartupInstance: Deserialized instance
        """
        # Deserialize config
        config_data = data["config"]
        config = StartupConfig(
            name=config_data["name"],
            industry=config_data["industry"],
            category=config_data["category"],
            template=config_data["template"],
            founder_profile=config_data["founder_profile"],
            resource_requirements=config_data["resource_requirements"],
            target_completion_date=datetime.fromisoformat(config_data["target_completion_date"]) if config_data.get("target_completion_date") else None,
            budget_limit=config_data.get("budget_limit")
        )
        
        # Deserialize resource allocation
        alloc_data = data["resource_allocation"]
        api_quota_data = alloc_data["api_quota"]
        
        api_quota = APIQuota(
            calls_per_hour=api_quota_data["calls_per_hour"],
            cost_per_day=api_quota_data["cost_per_day"],
            current_calls=api_quota_data["current_calls"],
            current_cost=api_quota_data["current_cost"],
            reset_at=datetime.fromisoformat(api_quota_data["reset_at"]) if api_quota_data.get("reset_at") else None
        )
        
        resource_allocation = ResourceAllocation(
            startup_id=alloc_data["startup_id"],
            memory_mb=alloc_data["memory_mb"],
            cpu_cores=alloc_data["cpu_cores"],
            storage_gb=alloc_data["storage_gb"],
            ports=alloc_data["ports"],
            database_namespace=alloc_data["database_namespace"],
            api_quota=api_quota,
            allocated_at=datetime.fromisoformat(alloc_data["allocated_at"]),
            expires_at=datetime.fromisoformat(alloc_data["expires_at"]) if alloc_data.get("expires_at") else None
        )
        
        # Create instance
        return StartupInstance(
            id=data["id"],
            config=config,
            status=StartupStatus(data["status"]),
            resource_allocation=resource_allocation,
            current_phase=data["current_phase"],
            state=data["state"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error")
        )
    
    async def get_state_summary(self) -> dict:
        """
        Get summary of state management information
        
        Returns:
            dict: State summary information
        """
        try:
            startup_ids = await self.list_saved_startups()
            
            # Count by status
            status_counts = {}
            for startup_id in startup_ids:
                instance = await self.load_startup_state(startup_id)
                if instance:
                    status = instance.status.value
                    status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "state_directory": str(self.state_dir),
                "total_saved_startups": len(startup_ids),
                "status_breakdown": status_counts,
                "startup_ids": startup_ids
            }
            
        except Exception as e:
            logger.error(f"Failed to get state summary: {e}")
            return {
                "state_directory": str(self.state_dir),
                "error": str(e)
            }