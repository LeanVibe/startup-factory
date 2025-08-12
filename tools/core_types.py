#!/usr/bin/env python3
"""
Core Types and Data Classes for Multi-Startup Infrastructure
Defines the foundational data structures and interfaces used across the platform.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
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
    # Alias to maintain backward/test compatibility
    ARCHITECTURE = "architecture_design"
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
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
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
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


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
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
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
    
    # Validate name
    if not config.name or not config.name.strip():
        errors.append("Startup name is required")
    elif len(config.name.strip()) < 2:
        errors.append("Startup name must be at least 2 characters")
    elif len(config.name.strip()) > 100:
        errors.append("Startup name must be less than 100 characters")
    elif not config.name.strip().replace(' ', '').replace('-', '').replace('_', '').isalnum():
        errors.append("Startup name can only contain alphanumeric characters, spaces, hyphens, and underscores")
    
    # Validate industry
    if not config.industry or not config.industry.strip():
        errors.append("Industry is required")
    elif len(config.industry.strip()) < 2:
        errors.append("Industry must be at least 2 characters")
    elif len(config.industry.strip()) > 50:
        errors.append("Industry must be less than 50 characters")
    
    # Validate category
    if not config.category or not config.category.strip():
        errors.append("Category is required")
    elif len(config.category.strip()) < 2:
        errors.append("Category must be at least 2 characters")
    elif len(config.category.strip()) > 50:
        errors.append("Category must be less than 50 characters")
    
    # Validate template
    valid_templates = ['neoforge', 'basic', 'advanced']
    if not config.template or not config.template.strip():
        errors.append("Template is required")
    elif config.template.strip() not in valid_templates:
        errors.append(f"Template must be one of: {', '.join(valid_templates)}")
    
    # Validate founder profile
    if not isinstance(config.founder_profile, dict):
        errors.append("Founder profile must be a dictionary")
    else:
        # Check for required founder profile fields
        required_fields = ['skills', 'experience']
        for field in required_fields:
            if field not in config.founder_profile:
                errors.append(f"Founder profile missing required field: {field}")
            elif not isinstance(config.founder_profile[field], str) or not config.founder_profile[field].strip():
                errors.append(f"Founder profile field '{field}' must be a non-empty string")
    
    # Validate resource requirements
    if not isinstance(config.resource_requirements, dict):
        errors.append("Resource requirements must be a dictionary")
    else:
        req = config.resource_requirements
        
        # Memory validation
        if 'memory_mb' not in req:
            errors.append("Memory requirement (memory_mb) is required")
        elif not isinstance(req['memory_mb'], (int, float)) or req['memory_mb'] < 100:
            errors.append("Memory requirement must be at least 100MB")
        elif req['memory_mb'] > 8192:
            errors.append("Memory requirement cannot exceed 8192MB")
        
        # CPU validation
        if 'cpu_cores' not in req:
            errors.append("CPU requirement (cpu_cores) is required")
        elif not isinstance(req['cpu_cores'], (int, float)) or req['cpu_cores'] < 0.1:
            errors.append("CPU requirement must be at least 0.1 cores")
        elif req['cpu_cores'] > 8:
            errors.append("CPU requirement cannot exceed 8 cores")
        
        # Storage validation
        if 'storage_gb' not in req:
            errors.append("Storage requirement (storage_gb) is required")
        elif not isinstance(req['storage_gb'], (int, float)) or req['storage_gb'] < 1:
            errors.append("Storage requirement must be at least 1GB")
        elif req['storage_gb'] > 100:
            errors.append("Storage requirement cannot exceed 100GB")
        
        # Port count validation
        if 'port_count' in req:
            if not isinstance(req['port_count'], int) or req['port_count'] < 1:
                errors.append("Port count must be at least 1")
            elif req['port_count'] > 10:
                errors.append("Port count cannot exceed 10")
        
        # API calls validation
        if 'api_calls_per_hour' in req:
            if not isinstance(req['api_calls_per_hour'], int) or req['api_calls_per_hour'] < 100:
                errors.append("API calls per hour must be at least 100")
            elif req['api_calls_per_hour'] > 10000:
                errors.append("API calls per hour cannot exceed 10000")
        
        # Cost validation
        if 'cost_per_day' in req:
            if not isinstance(req['cost_per_day'], (int, float)) or req['cost_per_day'] < 1:
                errors.append("Cost per day must be at least $1")
            elif req['cost_per_day'] > 100:
                errors.append("Cost per day cannot exceed $100")
    
    # Validate budget limit
    if config.budget_limit is not None:
        if not isinstance(config.budget_limit, (int, float)) or config.budget_limit < 10:
            errors.append("Budget limit must be at least $10")
        elif config.budget_limit > 50000:
            errors.append("Budget limit cannot exceed $50,000")
    
    return errors


def validate_task(task: Task) -> List[str]:
    """Validate task and return list of errors"""
    errors = []
    
    # Validate startup_id
    if not task.startup_id:
        errors.append("Startup ID is required")
    elif not isinstance(task.startup_id, str) or len(task.startup_id.strip()) < 5:
        errors.append("Startup ID must be a string with at least 5 characters")
    
    # Validate description
    if not task.description or not task.description.strip():
        errors.append("Task description is required")
    elif len(task.description.strip()) < 10:
        errors.append("Task description must be at least 10 characters")
    elif len(task.description.strip()) > 500:
        errors.append("Task description must be less than 500 characters")
    
    # Validate prompt
    if not task.prompt or not task.prompt.strip():
        errors.append("Task prompt is required")
    elif len(task.prompt.strip()) < 20:
        errors.append("Task prompt must be at least 20 characters")
    elif len(task.prompt.strip()) > 10000:
        errors.append("Task prompt must be less than 10000 characters")
    
    # Validate max_tokens
    if not isinstance(task.max_tokens, int) or task.max_tokens < 100:
        errors.append("Max tokens must be at least 100")
    elif task.max_tokens > 8192:
        errors.append("Max tokens cannot exceed 8192")
    
    # Validate max_retries
    if not isinstance(task.max_retries, int) or task.max_retries < 0:
        errors.append("Max retries cannot be negative")
    elif task.max_retries > 10:
        errors.append("Max retries cannot exceed 10")
    
    # Validate retry_count
    if not isinstance(task.retry_count, int) or task.retry_count < 0:
        errors.append("Retry count cannot be negative")
    elif task.retry_count > task.max_retries:
        errors.append("Retry count cannot exceed max retries")
    
    # Validate context
    if not isinstance(task.context, dict):
        errors.append("Task context must be a dictionary")
    
    # Validate provider_preference
    if task.provider_preference is not None:
        valid_providers = ['anthropic', 'openai', 'perplexity', 'gemini']
        if not isinstance(task.provider_preference, str) or task.provider_preference not in valid_providers:
            errors.append(f"Provider preference must be one of: {', '.join(valid_providers)}")
    
    return errors
