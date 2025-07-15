#!/usr/bin/env python3
"""
Multi-Startup Core Infrastructure Tools
Core AI orchestration and management tools for rapid startup development.
"""

# Import core types for easy access
from .core_types import (
    StartupConfig, StartupInstance, StartupStatus, ResourceAllocation, APIQuota,
    Task, TaskType, TaskPriority, TaskStatus, TaskResult, 
    StartupFactoryError, InvalidConfigError, ConcurrencyLimitError, 
    InsufficientResourcesError, StartupNotFoundError, TaskNotFoundError,
    generate_startup_id, generate_task_id, validate_startup_config, validate_task
)

# Import main orchestrator
from .multi_startup_orchestrator import MultiStartupOrchestrator

# Import core components
from .startup_manager import StartupManager
from .resource_allocator import ResourceAllocator
from .queue_processor import QueueProcessor
from .state_manager import StateManager

__version__ = "0.1.0"
__all__ = [
    # Core types
    "StartupConfig", "StartupInstance", "StartupStatus", "ResourceAllocation", "APIQuota",
    "Task", "TaskType", "TaskPriority", "TaskStatus", "TaskResult",
    "StartupFactoryError", "InvalidConfigError", "ConcurrencyLimitError",
    "InsufficientResourcesError", "StartupNotFoundError", "TaskNotFoundError",
    "generate_startup_id", "generate_task_id", "validate_startup_config", "validate_task",
    
    # Main orchestrator
    "MultiStartupOrchestrator",
    
    # Core components
    "StartupManager", "ResourceAllocator", "QueueProcessor", "StateManager"
]