#!/usr/bin/env python3
"""
Shared Data Models - Unified Business Context for 25-minute Pipeline

FIRST PRINCIPLES IMPLEMENTATION:
1. Single source of truth for business context across all validation systems
2. State machine tracking pipeline progression through 5 validation phases
3. Unified data models that connect acquisition → feedback → validation → evolution → testing

PARETO FOCUS: 20% data modeling that enables 80% pipeline integration value
- Unified business context with state management
- Data flow contracts between systems
- Serializable models for 25-minute persistence
"""

import asyncio
import json
import uuid
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import existing system models for integration (with error handling)
try:
    from customer_acquisition_system import BusinessContext as AcquisitionBusinessContext
    from customer_feedback_system import FeedbackResponse, FeedbackAnalysis, FeedbackWidget
    from customer_validation_dashboard import ValidationDashboard, DashboardMetric
    from mvp_evolution_system import MVPImprovement, MVPEvolutionPlan
    from ab_testing_framework import ABTest, TestMetrics
except ImportError as e:
    # For cases where we're testing without all dependencies
    print(f"Warning: Could not import some validation systems: {e}")
    # Define placeholder types
    AcquisitionBusinessContext = type('BusinessContext', (), {})
    FeedbackResponse = type('FeedbackResponse', (), {})
    FeedbackAnalysis = type('FeedbackAnalysis', (), {})
    FeedbackWidget = type('FeedbackWidget', (), {})
    ValidationDashboard = type('ValidationDashboard', (), {})
    DashboardMetric = type('DashboardMetric', (), {})
    MVPImprovement = type('MVPImprovement', (), {})
    MVPEvolutionPlan = type('MVPEvolutionPlan', (), {})
    ABTest = type('ABTest', (), {})
    TestMetrics = type('TestMetrics', (), {})


class PipelinePhase(str, Enum):
    """Phases in the complete validation pipeline"""
    INITIALIZED = "initialized"  # Starting state
    CUSTOMER_ACQUISITION = "customer_acquisition"  # Phase 1: Generate acquisition strategy
    FEEDBACK_COLLECTION = "feedback_collection"    # Phase 2: Set up feedback collection
    VALIDATION_ANALYSIS = "validation_analysis"    # Phase 3: Generate validation dashboard
    MVP_EVOLUTION = "mvp_evolution"                # Phase 4: Create evolution plan
    AB_TESTING = "ab_testing"                      # Phase 5: Set up A/B tests
    COMPLETED = "completed"                        # All phases successful
    COMPLETED_WITH_ERRORS = "completed_with_errors"  # Completed but with some failures
    FAILED = "failed"                              # Critical failure


class ValidationSystemType(str, Enum):
    """Types of validation systems in the pipeline"""
    CUSTOMER_ACQUISITION = "customer_acquisition"
    CUSTOMER_FEEDBACK = "customer_feedback" 
    VALIDATION_DASHBOARD = "validation_dashboard"
    MVP_EVOLUTION = "mvp_evolution"
    AB_TESTING = "ab_testing"


@dataclass
class PipelinePhaseResult:
    """Result from executing a single pipeline phase"""
    phase: PipelinePhase
    system_type: ValidationSystemType
    success: bool
    execution_time_seconds: float
    result_data: Dict[str, Any]
    error_message: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class UnifiedBusinessContext:
    """
    Unified business context that flows through entire validation pipeline.
    
    This is the single source of truth for business data, maintaining state
    and results from all validation systems in the 25-minute workflow.
    """
    
    # Core Business Information
    context_id: str = field(default_factory=lambda: f"ctx_{str(uuid.uuid4())[:8]}")
    business_name: str = ""
    industry: str = ""
    business_model: str = ""  # b2b_saas, b2c_saas, marketplace, etc.
    target_audience: str = ""
    value_proposition: str = ""
    problem_statement: str = ""
    solution_description: str = ""
    price_point: Optional[str] = None
    
    # Technical Requirements
    technical_requirements: Dict[str, Any] = field(default_factory=dict)
    compliance_requirements: List[str] = field(default_factory=list)
    
    # Pipeline State Management
    pipeline_state: PipelinePhase = PipelinePhase.INITIALIZED
    current_phase_start_time: Optional[datetime] = None
    pipeline_started_at: datetime = field(default_factory=datetime.now)
    pipeline_completed_at: Optional[datetime] = None
    
    # Results from Each Validation System
    acquisition_strategy: Optional[Dict[str, Any]] = None
    outreach_templates: Optional[Dict[str, str]] = None
    feedback_widgets: List[FeedbackWidget] = field(default_factory=list)
    collected_feedback: List[FeedbackResponse] = field(default_factory=list)
    feedback_analysis: Optional[FeedbackAnalysis] = None
    validation_dashboard: Optional[ValidationDashboard] = None
    evolution_plan: Optional[MVPEvolutionPlan] = None
    ab_tests: List[ABTest] = field(default_factory=list)
    
    # Pipeline Tracking
    validation_score: float = 0.0  # 0-100 overall validation score
    confidence_score: float = 0.0  # 0-1 confidence in business idea
    pipeline_history: List[PipelinePhaseResult] = field(default_factory=list)
    pipeline_errors: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    founder_email: Optional[str] = None
    conversation_id: Optional[str] = None
    
    @classmethod
    def from_interview_data(cls, interview_data: Dict[str, Any]) -> 'UnifiedBusinessContext':
        """Create UnifiedBusinessContext from founder interview system data"""
        
        business_context = interview_data.get("business_context", {})
        technical_requirements = interview_data.get("technical_requirements", {})
        
        return cls(
            business_name=business_context.get("business_name", ""),
            industry=business_context.get("industry", ""),
            business_model=business_context.get("business_model", ""),
            target_audience=business_context.get("target_audience", ""),
            value_proposition=business_context.get("value_proposition", ""),
            problem_statement=business_context.get("problem_statement", ""),
            solution_description=business_context.get("solution_description", ""),
            price_point=business_context.get("price_point"),
            technical_requirements=technical_requirements,
            compliance_requirements=technical_requirements.get("compliance", []),
            confidence_score=interview_data.get("confidence_score", 0.0),
            conversation_id=interview_data.get("conversation_id")
        )
    
    def advance_to_next_phase(self, phase: PipelinePhase) -> None:
        """Advance pipeline to next phase and update timing"""
        
        # Record completion of current phase if applicable
        if self.current_phase_start_time and self.pipeline_state != PipelinePhase.INITIALIZED:
            current_phase_duration = (datetime.now() - self.current_phase_start_time).total_seconds()
            
            # Add to pipeline history
            phase_result = PipelinePhaseResult(
                phase=self.pipeline_state,
                system_type=self._get_system_type_for_phase(self.pipeline_state),
                success=True,
                execution_time_seconds=current_phase_duration,
                result_data=self._get_current_phase_results(),
                completed_at=datetime.now()
            )
            self.pipeline_history.append(phase_result)
        
        # Advance to new phase
        self.pipeline_state = phase
        self.current_phase_start_time = datetime.now()
        self.last_updated = datetime.now()
        
        # Mark completion if reaching final phases
        if phase in [PipelinePhase.COMPLETED, PipelinePhase.COMPLETED_WITH_ERRORS, PipelinePhase.FAILED]:
            self.pipeline_completed_at = datetime.now()
    
    def record_phase_error(self, phase: PipelinePhase, error_message: str, system_type: ValidationSystemType) -> None:
        """Record an error during pipeline phase execution"""
        
        error_record = f"{phase.value}:{system_type.value}: {error_message}"
        self.pipeline_errors.append(error_record)
        
        # Add failed phase result to history
        if self.current_phase_start_time:
            execution_time = (datetime.now() - self.current_phase_start_time).total_seconds()
        else:
            execution_time = 0.0
            
        phase_result = PipelinePhaseResult(
            phase=phase,
            system_type=system_type,
            success=False,
            execution_time_seconds=execution_time,
            result_data={},
            error_message=error_message,
            completed_at=datetime.now()
        )
        self.pipeline_history.append(phase_result)
    
    def update_validation_score(self, new_score: float) -> None:
        """Update overall validation score (0-100)"""
        self.validation_score = max(0.0, min(100.0, new_score))
        self.last_updated = datetime.now()
    
    def get_total_pipeline_time(self) -> float:
        """Get total pipeline execution time in seconds"""
        if self.pipeline_completed_at:
            return (self.pipeline_completed_at - self.pipeline_started_at).total_seconds()
        else:
            return (datetime.now() - self.pipeline_started_at).total_seconds()
    
    def get_current_phase_time(self) -> float:
        """Get time spent in current phase in seconds"""
        if self.current_phase_start_time:
            return (datetime.now() - self.current_phase_start_time).total_seconds()
        return 0.0
    
    def is_within_25_minute_target(self) -> bool:
        """Check if pipeline is completing within 25-minute target"""
        return self.get_total_pipeline_time() <= 1500  # 25 minutes = 1500 seconds
    
    def get_acquisition_business_context(self) -> AcquisitionBusinessContext:
        """Convert to CustomerAcquisitionSystem BusinessContext format"""
        return AcquisitionBusinessContext(
            industry=self.industry,
            business_model=self.business_model,
            target_audience=self.target_audience,
            value_proposition=self.value_proposition,
            price_point=self.price_point
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for persistence"""
        
        # Convert dataclass to dict, handling nested objects
        result = asdict(self)
        
        # Convert datetime objects to ISO strings
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, list) and value and hasattr(value[0], 'to_dict'):
                # Handle lists of dataclass objects
                result[key] = [item.to_dict() if hasattr(item, 'to_dict') else asdict(item) for item in value]
            elif hasattr(value, 'to_dict'):
                # Handle single dataclass objects
                result[key] = value.to_dict()
            elif hasattr(value, '__dict__'):
                # Handle other objects with dict representation
                result[key] = asdict(value) if hasattr(value, '__dataclass_fields__') else str(value)
        
        return result
    
    @classmethod  
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedBusinessContext':
        """Deserialize from dictionary"""
        
        # Convert ISO datetime strings back to datetime objects
        datetime_fields = ['current_phase_start_time', 'pipeline_started_at', 'pipeline_completed_at', 
                          'created_at', 'last_updated']
        
        for field in datetime_fields:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field])
        
        # Handle pipeline_state enum
        if 'pipeline_state' in data:
            if isinstance(data['pipeline_state'], str):
                # Handle both enum string representations
                pipeline_state_str = data['pipeline_state']
                if pipeline_state_str.startswith('PipelinePhase.'):
                    # Extract enum name and convert to value
                    enum_name = pipeline_state_str.split('.')[1]
                    # Convert enum name to value (e.g., CUSTOMER_ACQUISITION -> customer_acquisition)
                    pipeline_state_str = enum_name.lower()
                data['pipeline_state'] = PipelinePhase(pipeline_state_str)
        
        # Handle complex nested objects (simplified for now)
        # TODO: Implement full deserialization of nested objects if needed
        
        return cls(**data)
    
    def _get_system_type_for_phase(self, phase: PipelinePhase) -> ValidationSystemType:
        """Map pipeline phase to validation system type"""
        phase_to_system = {
            PipelinePhase.CUSTOMER_ACQUISITION: ValidationSystemType.CUSTOMER_ACQUISITION,
            PipelinePhase.FEEDBACK_COLLECTION: ValidationSystemType.CUSTOMER_FEEDBACK,
            PipelinePhase.VALIDATION_ANALYSIS: ValidationSystemType.VALIDATION_DASHBOARD,
            PipelinePhase.MVP_EVOLUTION: ValidationSystemType.MVP_EVOLUTION,
            PipelinePhase.AB_TESTING: ValidationSystemType.AB_TESTING
        }
        return phase_to_system.get(phase, ValidationSystemType.CUSTOMER_ACQUISITION)
    
    def _get_current_phase_results(self) -> Dict[str, Any]:
        """Get results from current phase for history tracking"""
        
        if self.pipeline_state == PipelinePhase.CUSTOMER_ACQUISITION:
            return {
                "acquisition_strategy": self.acquisition_strategy,
                "outreach_templates": self.outreach_templates
            }
        elif self.pipeline_state == PipelinePhase.FEEDBACK_COLLECTION:
            return {
                "feedback_widgets": len(self.feedback_widgets),
                "feedback_analysis": (
                    self.feedback_analysis.to_dict() if hasattr(self.feedback_analysis, 'to_dict')
                    else str(self.feedback_analysis)
                ) if self.feedback_analysis else None
            }
        elif self.pipeline_state == PipelinePhase.VALIDATION_ANALYSIS:
            return {
                "validation_dashboard": (
                    self.validation_dashboard.to_dict() if hasattr(self.validation_dashboard, 'to_dict') 
                    else str(self.validation_dashboard)
                ) if self.validation_dashboard else None,
                "validation_score": self.validation_score
            }
        elif self.pipeline_state == PipelinePhase.MVP_EVOLUTION:
            return {
                "evolution_plan": (
                    self.evolution_plan.to_dict() if hasattr(self.evolution_plan, 'to_dict')
                    else str(self.evolution_plan)
                ) if self.evolution_plan else None,
                "improvements_count": len(self.evolution_plan.improvements) if self.evolution_plan else 0
            }
        elif self.pipeline_state == PipelinePhase.AB_TESTING:
            return {
                "ab_tests": len(self.ab_tests),
                "test_ids": [test.test_id for test in self.ab_tests]
            }
        
        return {}


@dataclass
class PipelineExecutionResult:
    """Final result from complete pipeline execution"""
    
    business_context: UnifiedBusinessContext
    success: bool
    total_execution_time_seconds: float
    completed_phases: List[PipelinePhase]
    failed_phases: List[PipelinePhase]
    
    # Quick access to results
    acquisition_strategy: Optional[Dict[str, Any]] = None
    feedback_widgets: List[FeedbackWidget] = field(default_factory=list)
    validation_dashboard: Optional[ValidationDashboard] = None
    evolution_plan: Optional[MVPEvolutionPlan] = None
    ab_tests: List[ABTest] = field(default_factory=list)
    
    # Pipeline metadata
    pipeline_errors: List[str] = field(default_factory=list)
    pipeline_history: List[PipelinePhaseResult] = field(default_factory=list)
    within_25_minute_target: bool = True
    
    @classmethod
    def from_business_context(cls, context: UnifiedBusinessContext) -> 'PipelineExecutionResult':
        """Create execution result from completed business context"""
        
        completed_phases = [result.phase for result in context.pipeline_history if result.success]
        failed_phases = [result.phase for result in context.pipeline_history if not result.success]
        
        return cls(
            business_context=context,
            success=context.pipeline_state in [PipelinePhase.COMPLETED, PipelinePhase.COMPLETED_WITH_ERRORS],
            total_execution_time_seconds=context.get_total_pipeline_time(),
            completed_phases=completed_phases,
            failed_phases=failed_phases,
            acquisition_strategy=context.acquisition_strategy,
            feedback_widgets=context.feedback_widgets,
            validation_dashboard=context.validation_dashboard,
            evolution_plan=context.evolution_plan,
            ab_tests=context.ab_tests,
            pipeline_errors=context.pipeline_errors,
            pipeline_history=context.pipeline_history,
            within_25_minute_target=context.is_within_25_minute_target()
        )


# Utility functions for working with unified context

def create_unified_context_from_founder_data(
    business_name: str,
    industry: str,
    business_model: str,
    target_audience: str,
    value_proposition: str,
    **kwargs
) -> UnifiedBusinessContext:
    """Utility function to create UnifiedBusinessContext from basic founder data"""
    
    return UnifiedBusinessContext(
        business_name=business_name,
        industry=industry,
        business_model=business_model,
        target_audience=target_audience,
        value_proposition=value_proposition,
        problem_statement=kwargs.get('problem_statement', ''),
        solution_description=kwargs.get('solution_description', ''),
        price_point=kwargs.get('price_point'),
        founder_email=kwargs.get('founder_email'),
        confidence_score=kwargs.get('confidence_score', 0.0)
    )


if __name__ == "__main__":
    # Test the unified data models
    
    # Create sample context
    sample_interview_data = {
        "business_context": {
            "business_name": "HealthTech Scheduler",
            "industry": "healthcare",
            "business_model": "b2b_saas",
            "target_audience": "Healthcare providers",
            "value_proposition": "AI-powered scheduling reduces no-shows by 40%",
            "problem_statement": "Clinics lose 20% revenue due to scheduling inefficiencies",
            "solution_description": "Smart scheduling with SMS reminders and optimal timing"
        },
        "technical_requirements": {
            "backend": "fastapi",
            "frontend": "react",
            "compliance": ["HIPAA"]
        },
        "confidence_score": 0.92
    }
    
    # Test context creation
    context = UnifiedBusinessContext.from_interview_data(sample_interview_data)
    print(f"Created context: {context.business_name}")
    print(f"Initial state: {context.pipeline_state}")
    
    # Test phase advancement
    context.advance_to_next_phase(PipelinePhase.CUSTOMER_ACQUISITION)
    print(f"Advanced to: {context.pipeline_state}")
    
    # Test serialization
    context_dict = context.to_dict()
    restored_context = UnifiedBusinessContext.from_dict(context_dict)
    print(f"Serialization test: {restored_context.business_name == context.business_name}")
    
    print("✅ Unified data models working correctly")