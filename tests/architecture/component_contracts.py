#!/usr/bin/env python3
"""
Component Architecture and Contract Definitions
Defines all system components and their interaction contracts for testing.

This file serves as the single source of truth for:
1. Component identification and responsibilities
2. Interface contracts between components
3. Data flow specifications
4. Error handling contracts
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Protocol
from enum import Enum

# === CORE SYSTEM COMPONENTS ===

class ComponentType(str, Enum):
    """Types of system components"""
    # Core Orchestration
    MVP_ORCHESTRATOR = "mvp_orchestrator"
    AI_PROVIDER_MANAGER = "ai_provider_manager" 
    TASK_QUEUE_PROCESSOR = "task_queue_processor"
    
    # Resource Management
    STARTUP_MANAGER = "startup_manager"
    RESOURCE_ALLOCATOR = "resource_allocator"
    TEMPLATE_MANAGER = "template_manager"
    
    # Monitoring & Control
    BUDGET_MONITOR = "budget_monitor"
    HEALTH_MONITOR = "health_monitor"
    ANALYTICS_ENGINE = "analytics_engine"
    
    # External Integration
    COOKIECUTTER_INTEGRATION = "cookiecutter_integration"
    PROJECT_GENERATOR = "project_generator"

@dataclass
class ComponentDefinition:
    """Definition of a system component"""
    name: str
    type: ComponentType
    responsibilities: List[str]
    dependencies: List[str]
    interfaces: List[str]
    state_requirements: Optional[Dict[str, Any]] = None

# === INTERFACE CONTRACTS ===

class TaskProcessorContract(Protocol):
    """Contract for task processing components"""
    
    async def process_task(self, task: 'Task') -> 'TaskResult':
        """Process a single task and return result"""
        ...
    
    async def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status"""
        ...
    
    def supports_task_type(self, task_type: str) -> bool:
        """Check if processor supports task type"""
        ...

class ResourceManagerContract(Protocol):
    """Contract for resource management components"""
    
    async def allocate_resources(self, startup_id: str, requirements: Dict) -> 'ResourceAllocation':
        """Allocate resources for a startup"""
        ...
    
    async def deallocate_resources(self, startup_id: str) -> bool:
        """Deallocate resources for a startup"""
        ...
    
    async def get_resource_usage(self, startup_id: str) -> Dict[str, Any]:
        """Get current resource usage"""
        ...

class MonitoringContract(Protocol):
    """Contract for monitoring components"""
    
    async def collect_metrics(self, component: str) -> Dict[str, float]:
        """Collect metrics from component"""
        ...
    
    async def check_health(self, component: str) -> 'HealthStatus':
        """Check component health"""
        ...
    
    def register_alert(self, condition: str, callback: callable) -> str:
        """Register alert condition"""
        ...

class ProjectGeneratorContract(Protocol):
    """Contract for project generation components"""
    
    async def generate_project(self, template: str, config: Dict) -> str:
        """Generate project from template"""
        ...
    
    async def validate_template(self, template: str) -> bool:
        """Validate template integrity"""
        ...
    
    async def list_available_templates(self) -> List[str]:
        """List available templates"""
        ...

# === DATA FLOW CONTRACTS ===

@dataclass
class DataFlowContract:
    """Defines how data flows between components"""
    source_component: str
    target_component: str
    data_type: str
    validation_rules: List[str]
    error_handling: str
    retry_policy: Optional[Dict] = None

# === CRITICAL USER JOURNEYS ===

class UserJourney(Enum):
    """Critical user journeys that must be tested end-to-end"""
    CREATE_NEW_STARTUP = "create_new_startup"
    GENERATE_MVP_SPEC = "generate_mvp_spec" 
    DEPLOY_GENERATED_PROJECT = "deploy_generated_project"
    MONITOR_STARTUP_HEALTH = "monitor_startup_health"
    HANDLE_RESOURCE_EXHAUSTION = "handle_resource_exhaustion"

@dataclass
class JourneyStep:
    """Single step in a user journey"""
    step_name: str
    component: str
    input_contract: Dict[str, Any]
    expected_output: Dict[str, Any]
    error_conditions: List[str]
    timeout_seconds: int

# === COMPONENT REGISTRY ===

SYSTEM_COMPONENTS: Dict[str, ComponentDefinition] = {
    "mvp_orchestrator": ComponentDefinition(
        name="MVP Orchestrator",
        type=ComponentType.MVP_ORCHESTRATOR,
        responsibilities=[
            "Coordinate entire MVP development workflow",
            "Manage human-in-the-loop gates", 
            "Track project state and progress",
            "Cost tracking and budget enforcement"
        ],
        dependencies=["ai_provider_manager", "template_manager", "budget_monitor"],
        interfaces=["TaskProcessorContract", "MonitoringContract"]
    ),
    
    "ai_provider_manager": ComponentDefinition(
        name="AI Provider Manager",
        type=ComponentType.AI_PROVIDER_MANAGER,
        responsibilities=[
            "Route tasks to appropriate AI providers",
            "Manage provider health and failover",
            "Cost calculation and tracking",
            "Rate limiting and quota management"
        ],
        dependencies=["health_monitor", "budget_monitor"],
        interfaces=["TaskProcessorContract", "MonitoringContract"]
    ),
    
    "template_manager": ComponentDefinition(
        name="Template Manager", 
        type=ComponentType.TEMPLATE_MANAGER,
        responsibilities=[
            "Manage cookiecutter templates",
            "Validate template integrity",
            "Generate projects from templates",
            "Handle template customization"
        ],
        dependencies=["cookiecutter_integration"],
        interfaces=["ProjectGeneratorContract"]
    ),
    
    "startup_manager": ComponentDefinition(
        name="Startup Manager",
        type=ComponentType.STARTUP_MANAGER,
        responsibilities=[
            "Manage startup lifecycle",
            "Track startup state and metadata", 
            "Coordinate resource allocation",
            "Handle startup-level operations"
        ],
        dependencies=["resource_allocator", "template_manager"],
        interfaces=["ResourceManagerContract", "MonitoringContract"]
    ),
    
    "budget_monitor": ComponentDefinition(
        name="Budget Monitor",
        type=ComponentType.BUDGET_MONITOR,
        responsibilities=[
            "Track AI provider costs",
            "Enforce budget limits",
            "Generate budget alerts",
            "Cost forecasting and optimization"
        ],
        dependencies=[],
        interfaces=["MonitoringContract"]
    )
}

# === CRITICAL DATA FLOWS ===

CRITICAL_DATA_FLOWS: List[DataFlowContract] = [
    DataFlowContract(
        source_component="mvp_orchestrator",
        target_component="ai_provider_manager", 
        data_type="Task",
        validation_rules=["task_id_required", "valid_task_type", "prompt_not_empty"],
        error_handling="retry_with_backoff",
        retry_policy={"max_retries": 3, "base_delay": 1.0}
    ),
    
    DataFlowContract(
        source_component="ai_provider_manager",
        target_component="budget_monitor",
        data_type="ProviderCall",
        validation_rules=["cost_positive", "tokens_positive", "provider_valid"],
        error_handling="log_and_continue",
    ),
    
    DataFlowContract(
        source_component="mvp_orchestrator", 
        target_component="template_manager",
        data_type="ProjectConfig",
        validation_rules=["template_exists", "config_complete"],
        error_handling="fail_fast",
    ),
]

# === USER JOURNEY DEFINITIONS ===

CREATE_STARTUP_JOURNEY: List[JourneyStep] = [
    JourneyStep(
        step_name="initialize_project",
        component="mvp_orchestrator",
        input_contract={"project_name": str, "industry": str, "category": str},
        expected_output={"project_id": str, "status": "initialized"},
        error_conditions=["invalid_name", "duplicate_project"],
        timeout_seconds=30
    ),
    
    JourneyStep(
        step_name="market_research", 
        component="ai_provider_manager",
        input_contract={"industry": str, "category": str},
        expected_output={"research_report": str, "cost": float},
        error_conditions=["provider_unavailable", "budget_exceeded"],
        timeout_seconds=120
    ),
    
    JourneyStep(
        step_name="generate_project",
        component="template_manager", 
        input_contract={"template": str, "config": dict},
        expected_output={"project_path": str, "files_created": list},
        error_conditions=["template_invalid", "generation_failed"],
        timeout_seconds=60
    )
]

# === TEST CONTRACTS ===

class ComponentTestContract:
    """Defines what must be tested for each component"""
    
    @abstractmethod
    def test_component_isolation(self):
        """Test component works in isolation with mocked dependencies"""
        pass
    
    @abstractmethod  
    def test_interface_contracts(self):
        """Test all interface contracts are properly implemented"""
        pass
    
    @abstractmethod
    def test_error_handling(self):
        """Test error conditions and recovery"""
        pass
    
    @abstractmethod
    def test_performance_requirements(self):
        """Test component meets performance requirements"""
        pass

# === CONTRACT VALIDATION HELPERS ===

def validate_component_contracts() -> Dict[str, List[str]]:
    """Validate all component contracts are properly defined"""
    errors = {}
    
    for name, component in SYSTEM_COMPONENTS.items():
        component_errors = []
        
        # Check dependencies exist
        for dep in component.dependencies:
            if dep not in SYSTEM_COMPONENTS:
                component_errors.append(f"Unknown dependency: {dep}")
        
        # Check interfaces are defined
        # (Implementation would check actual interface existence)
        
        if component_errors:
            errors[name] = component_errors
    
    return errors

def get_component_dependency_graph() -> Dict[str, List[str]]:
    """Get component dependency graph for testing order"""
    return {name: comp.dependencies for name, comp in SYSTEM_COMPONENTS.items()}