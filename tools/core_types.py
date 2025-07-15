#!/usr/bin/env python3
"""
Core Types and Data Classes for Multi-Startup Infrastructure
Defines the foundational data structures and interfaces used across the platform.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class StartupStatus(str, Enum):
    """Status of a startup instance"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class TaskType(str, Enum):
    """Types of AI tasks that can be executed"""
    MARKET_RESEARCH = "market_research"
    FOUNDER_ANALYSIS = "founder_analysis"
    MVP_SPECIFICATION = "mvp_specification"
    ARCHITECTURE_DESIGN = "architecture_design"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class TaskPriority(int, Enum):
    """Task priority levels (lower number = higher priority)"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class TaskStatus(str, Enum):
    """Status of a task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class APIQuota:
    """API usage quota for a startup"""
    calls_per_hour: int
    cost_per_day: float
    current_calls: int = 0
    current_cost: float = 0.0
    reset_at: Optional[datetime] = None


@dataclass
class ResourceAllocation:
    """Resource allocation for a startup"""
    startup_id: str
    memory_mb: int
    cpu_cores: float
    storage_gb: int
    ports: List[int]
    database_namespace: str
    api_quota: APIQuota
    allocated_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class StartupConfig:
    """Configuration for a startup"""
    name: str
    industry: str
    category: str
    template: str
    founder_profile: dict
    resource_requirements: dict
    target_completion_date: Optional[datetime] = None
    budget_limit: Optional[float] = None


@dataclass
class StartupInstance:
    """Complete startup instance"""
    id: str
    config: StartupConfig
    status: StartupStatus
    resource_allocation: ResourceAllocation
    current_phase: int
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class Task:
    """AI task to be executed"""
    id: str
    startup_id: str
    type: TaskType
    description: str
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    max_tokens: int = 4000
    provider_preference: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskResult:
    """Result of an AI task execution"""
    task_id: str
    startup_id: str
    success: bool
    content: str
    cost: float
    provider_used: str
    execution_time_seconds: float
    tokens_used: Optional[int] = None
    quality_score: Optional[float] = None
    completed_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None


@dataclass
class PrioritizedTask:
    """Task with priority for queue processing"""
    priority: int
    task_id: str
    task: Task
    
    def __lt__(self, other):
        return self.priority < other.priority


class IStartupManager(ABC):
    """Interface for startup management"""
    
    @abstractmethod
    async def create_startup(self, config: StartupConfig) -> str:
        """Create new startup and return ID"""
        pass
    
    @abstractmethod
    async def get_startup(self, startup_id: str) -> StartupInstance:
        """Get startup instance by ID"""
        pass
    
    @abstractmethod
    async def get_active_startups(self) -> List[StartupInstance]:
        """Get all active startups"""
        pass
    
    @abstractmethod
    async def update_startup_status(self, startup_id: str, status: StartupStatus) -> None:
        """Update startup status"""
        pass
    
    @abstractmethod
    async def delete_startup(self, startup_id: str) -> None:
        """Delete startup and cleanup resources"""
        pass


class IResourceAllocator(ABC):
    """Interface for resource allocation"""
    
    @abstractmethod
    async def allocate(self, startup_id: str, requirements: dict) -> ResourceAllocation:
        """Allocate resources for startup"""
        pass
    
    @abstractmethod
    async def deallocate(self, startup_id: str) -> None:
        """Release startup resources"""
        pass
    
    @abstractmethod
    async def check_availability(self, requirements: dict) -> bool:
        """Check if resources are available"""
        pass
    
    @abstractmethod
    async def get_allocation(self, startup_id: str) -> Optional[ResourceAllocation]:
        """Get resource allocation for startup"""
        pass


class IQueueProcessor(ABC):
    """Interface for queue processing"""
    
    @abstractmethod
    async def submit_task(self, task: Task) -> str:
        """Submit task to queue and return task ID"""
        pass
    
    @abstractmethod
    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result by ID"""
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        pass
    
    @abstractmethod
    async def start_processing(self, max_concurrent: int = 15) -> None:
        """Start task processing"""
        pass
    
    @abstractmethod
    async def stop_processing(self) -> None:
        """Stop task processing"""
        pass


# Custom Exceptions
class StartupFactoryError(Exception):
    """Base exception for startup factory errors"""
    pass


class InvalidConfigError(StartupFactoryError):
    """Invalid configuration error"""
    pass


class ConcurrencyLimitError(StartupFactoryError):
    """Concurrency limit exceeded error"""
    pass


class InsufficientResourcesError(StartupFactoryError):
    """Insufficient resources error"""
    pass


class InsufficientMemoryError(InsufficientResourcesError):
    """Insufficient memory error"""
    pass


class PortConflictError(InsufficientResourcesError):
    """Port conflict error"""
    pass


class StartupNotFoundError(StartupFactoryError):
    """Startup not found error"""
    pass


class TaskNotFoundError(StartupFactoryError):
    """Task not found error"""
    pass


class ProviderError(StartupFactoryError):
    """AI provider error"""
    pass


def generate_startup_id() -> str:
    """Generate unique startup ID"""
    return f"startup_{uuid.uuid4().hex[:8]}"


def generate_task_id() -> str:
    """Generate unique task ID"""
    return f"task_{uuid.uuid4().hex[:8]}"


# Utility functions for validation
def validate_startup_config(config: StartupConfig) -> List[str]:
    """Validate startup configuration and return list of errors"""
    errors = []
    
    if not config.name or not config.name.strip():
        errors.append("Startup name is required")
    
    if not config.industry or not config.industry.strip():
        errors.append("Industry is required")
    
    if not config.category or not config.category.strip():
        errors.append("Category is required")
    
    if not config.template or not config.template.strip():
        errors.append("Template is required")
    
    if not isinstance(config.founder_profile, dict):
        errors.append("Founder profile must be a dictionary")
    
    if not isinstance(config.resource_requirements, dict):
        errors.append("Resource requirements must be a dictionary")
    
    # Validate resource requirements
    req = config.resource_requirements
    if req.get('memory_mb', 0) < 100:
        errors.append("Memory requirement must be at least 100MB")
    
    if req.get('cpu_cores', 0) < 0.1:
        errors.append("CPU requirement must be at least 0.1 cores")
    
    if req.get('storage_gb', 0) < 1:
        errors.append("Storage requirement must be at least 1GB")
    
    return errors


def validate_task(task: Task) -> List[str]:
    """Validate task and return list of errors"""
    errors = []
    
    if not task.startup_id:
        errors.append("Startup ID is required")
    
    if not task.description or not task.description.strip():
        errors.append("Task description is required")
    
    if not task.prompt or not task.prompt.strip():
        errors.append("Task prompt is required")
    
    if task.max_tokens < 100:
        errors.append("Max tokens must be at least 100")
    
    if task.max_retries < 0:
        errors.append("Max retries cannot be negative")
    
    return errors