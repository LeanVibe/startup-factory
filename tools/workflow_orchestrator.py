#!/usr/bin/env python3
"""
Workflow Orchestrator - Complete 25-minute Validation Pipeline

FIRST PRINCIPLES IMPLEMENTATION:
1. Single orchestrator manages end-to-end workflow across all 5 validation systems
2. Pipeline must complete in 25 minutes with 95%+ success rate
3. Error handling enables graceful degradation without cascade failures

PARETO FOCUS: 20% orchestration logic that delivers 80% pipeline integration value
- Sequential execution of validation systems with state management
- Error recovery and continuation strategies
- Performance monitoring and optimization for 25-minute target
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Import shared models and validation systems
import sys
from pathlib import Path

# Add paths for imports
sys.path.append(str(Path(__file__).parent))  # For shared_models
sys.path.append(str(Path(__file__).parent.parent))  # For validation systems

from shared_models import (
    UnifiedBusinessContext, 
    PipelinePhase, 
    ValidationSystemType,
    PipelineExecutionResult,
    PipelinePhaseResult
)

from customer_acquisition_system import CustomerAcquisitionSystem
from customer_feedback_system import CustomerFeedbackSystem  
from customer_validation_dashboard import CustomerValidationDashboard
from mvp_evolution_system import MVPEvolutionSystem
from ab_testing_framework import ABTestingFramework

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates complete customer validation pipeline in 25 minutes.
    
    WORKFLOW PHASES:
    1. Customer Acquisition (5 min) - Generate industry-specific acquisition strategy
    2. Feedback Collection (5 min) - Set up feedback widgets and analysis
    3. Validation Analysis (5 min) - Create unified validation dashboard
    4. MVP Evolution (5 min) - Generate improvement recommendations  
    5. A/B Testing (5 min) - Set up validation experiments
    
    SUCCESS CRITERIA: 95%+ completion rate within 25-minute target
    """
    
    def __init__(self):
        """Initialize orchestrator with all validation systems"""
        
        # Initialize all validation systems
        self.acquisition_system = CustomerAcquisitionSystem()
        self.feedback_system = CustomerFeedbackSystem()
        self.dashboard_system = CustomerValidationDashboard()
        self.evolution_system = MVPEvolutionSystem()
        self.ab_testing_system = ABTestingFramework()
        
        # Performance tracking
        self.max_pipeline_time_seconds = 1500  # 25 minutes
        self.max_phase_time_seconds = 300      # 5 minutes per phase
        
        logger.info("WorkflowOrchestrator initialized with all validation systems")
    
    async def execute_complete_pipeline(self, interview_data: Dict[str, Any]) -> PipelineExecutionResult:
        """
        Execute complete 25-minute validation pipeline end-to-end.
        
        Args:
            interview_data: Data from founder interview system
            
        Returns:
            PipelineExecutionResult with complete validation data
        """
        
        start_time = time.time()
        logger.info("Starting complete validation pipeline execution")
        
        # Create unified business context from interview data
        business_context = UnifiedBusinessContext.from_interview_data(interview_data)
        
        try:
            # Phase 1: Customer Acquisition (Target: 5 minutes)
            await self._execute_customer_acquisition_phase(business_context)
            
            # Phase 2: Feedback Collection (Target: 5 minutes) 
            await self._execute_feedback_collection_phase(business_context)
            
            # Phase 3: Validation Analysis (Target: 5 minutes)
            await self._execute_validation_analysis_phase(business_context)
            
            # Phase 4: MVP Evolution (Target: 5 minutes)
            await self._execute_mvp_evolution_phase(business_context)
            
            # Phase 5: A/B Testing (Target: 5 minutes)
            await self._execute_ab_testing_phase(business_context)
            
            # Mark pipeline as completed
            business_context.advance_to_next_phase(
                PipelinePhase.COMPLETED_WITH_ERRORS if business_context.pipeline_errors 
                else PipelinePhase.COMPLETED
            )
            
            execution_time = time.time() - start_time
            logger.info(f"Pipeline completed successfully in {execution_time:.2f} seconds")
            
        except Exception as e:
            # Handle critical pipeline failure
            logger.error(f"Critical pipeline failure: {str(e)}")
            business_context.record_phase_error(
                business_context.pipeline_state, 
                f"Critical failure: {str(e)}", 
                ValidationSystemType.CUSTOMER_ACQUISITION
            )
            business_context.advance_to_next_phase(PipelinePhase.FAILED)
            execution_time = time.time() - start_time
        
        # Create final execution result
        result = PipelineExecutionResult.from_business_context(business_context)
        
        # Log performance metrics
        logger.info(f"Pipeline execution completed: {result.success}")
        logger.info(f"Total time: {result.total_execution_time_seconds:.2f}s")
        logger.info(f"Within 25-min target: {result.within_25_minute_target}")
        logger.info(f"Completed phases: {len(result.completed_phases)}")
        logger.info(f"Failed phases: {len(result.failed_phases)}")
        
        return result
    
    async def _execute_customer_acquisition_phase(self, context: UnifiedBusinessContext) -> None:
        """Execute customer acquisition strategy generation phase"""
        
        phase_start = time.time()
        context.advance_to_next_phase(PipelinePhase.CUSTOMER_ACQUISITION)
        
        try:
            logger.info("Executing customer acquisition phase")
            
            # Convert to acquisition system format
            acquisition_context = context.get_acquisition_business_context()
            
            # Generate acquisition strategy
            strategy = self.acquisition_system.generate_customer_discovery_strategy(acquisition_context)
            context.acquisition_strategy = strategy
            
            # Generate outreach templates
            templates = self.acquisition_system.generate_outreach_templates(acquisition_context)
            context.outreach_templates = templates
            
            execution_time = time.time() - phase_start
            logger.info(f"Customer acquisition phase completed in {execution_time:.2f}s")
            
            # Check phase timing
            if execution_time > self.max_phase_time_seconds:
                logger.warning(f"Customer acquisition exceeded 5-minute target: {execution_time:.2f}s")
            
        except Exception as e:
            error_msg = f"Customer acquisition failed: {str(e)}"
            logger.error(error_msg)
            context.record_phase_error(
                PipelinePhase.CUSTOMER_ACQUISITION,
                error_msg,
                ValidationSystemType.CUSTOMER_ACQUISITION
            )
            # Continue pipeline with partial data
    
    async def _execute_feedback_collection_phase(self, context: UnifiedBusinessContext) -> None:
        """Execute feedback collection setup phase"""
        
        phase_start = time.time()
        context.advance_to_next_phase(PipelinePhase.FEEDBACK_COLLECTION)
        
        try:
            logger.info("Executing feedback collection phase")
            
            # Generate MVP-specific feedback widgets
            business_data = {
                "business_name": context.business_name,
                "industry": context.industry,
                "business_model": context.business_model,
                "target_audience": context.target_audience,
                "compliance_requirements": context.compliance_requirements
            }
            
            # Create feedback widgets using existing method
            widget_types = ["nps", "feature_request", "rating"]
            widgets = []
            for widget_type in widget_types:
                try:
                    widget = self.feedback_system.create_feedback_widget(
                        feedback_type=widget_type,
                        business_context=business_data
                    )
                    if widget:
                        widgets.append(widget)
                except Exception as e:
                    logger.warning(f"Could not create {widget_type} widget: {e}")
            
            context.feedback_widgets = widgets
            
            # If we have existing feedback data, analyze it
            if context.collected_feedback:
                analysis = self.feedback_system.analyze_feedback_batch(context.collected_feedback)
                context.feedback_analysis = analysis
            
            execution_time = time.time() - phase_start
            logger.info(f"Feedback collection phase completed in {execution_time:.2f}s")
            
            if execution_time > self.max_phase_time_seconds:
                logger.warning(f"Feedback collection exceeded 5-minute target: {execution_time:.2f}s")
            
        except Exception as e:
            error_msg = f"Feedback collection failed: {str(e)}"
            logger.error(error_msg)
            context.record_phase_error(
                PipelinePhase.FEEDBACK_COLLECTION,
                error_msg,
                ValidationSystemType.CUSTOMER_FEEDBACK
            )
    
    async def _execute_validation_analysis_phase(self, context: UnifiedBusinessContext) -> None:
        """Execute validation dashboard generation phase"""
        
        phase_start = time.time()
        context.advance_to_next_phase(PipelinePhase.VALIDATION_ANALYSIS)
        
        try:
            logger.info("Executing validation analysis phase")
            
            # Prepare data for dashboard generation
            business_data = {
                "business_name": context.business_name,
                "industry": context.industry,
                "business_model": context.business_model,
                "target_audience": context.target_audience,
                "value_proposition": context.value_proposition
            }
            
            # Prepare acquisition data
            acquisition_data = context.acquisition_strategy
            
            # Generate unified validation dashboard
            dashboard = self.dashboard_system.generate_dashboard(
                business_context=business_data,
                acquisition_data=acquisition_data,
                feedback_data=context.collected_feedback
            )
            
            context.validation_dashboard = dashboard
            context.update_validation_score(dashboard.overall_validation_score)
            
            execution_time = time.time() - phase_start
            logger.info(f"Validation analysis phase completed in {execution_time:.2f}s")
            logger.info(f"Overall validation score: {dashboard.overall_validation_score}")
            
            if execution_time > self.max_phase_time_seconds:
                logger.warning(f"Validation analysis exceeded 5-minute target: {execution_time:.2f}s")
            
        except Exception as e:
            error_msg = f"Validation analysis failed: {str(e)}"
            logger.error(error_msg)
            context.record_phase_error(
                PipelinePhase.VALIDATION_ANALYSIS,
                error_msg,
                ValidationSystemType.VALIDATION_DASHBOARD
            )
    
    async def _execute_mvp_evolution_phase(self, context: UnifiedBusinessContext) -> None:
        """Execute MVP evolution planning phase"""
        
        phase_start = time.time()
        context.advance_to_next_phase(PipelinePhase.MVP_EVOLUTION)
        
        try:
            logger.info("Executing MVP evolution phase")
            
            # Generate evolution plan from validation data
            if context.validation_dashboard:
                evolution_plan = self.evolution_system.generate_evolution_plan(
                    context.validation_dashboard,
                    context.collected_feedback
                )
                context.evolution_plan = evolution_plan
                
                execution_time = time.time() - phase_start
                logger.info(f"MVP evolution phase completed in {execution_time:.2f}s")
                logger.info(f"Generated {len(evolution_plan.improvements)} improvement recommendations")
                
                if execution_time > self.max_phase_time_seconds:
                    logger.warning(f"MVP evolution exceeded 5-minute target: {execution_time:.2f}s")
            else:
                logger.warning("No validation dashboard available for MVP evolution")
            
        except Exception as e:
            error_msg = f"MVP evolution failed: {str(e)}"
            logger.error(error_msg)
            context.record_phase_error(
                PipelinePhase.MVP_EVOLUTION,
                error_msg,
                ValidationSystemType.MVP_EVOLUTION
            )
    
    async def _execute_ab_testing_phase(self, context: UnifiedBusinessContext) -> None:
        """Execute A/B testing setup phase"""
        
        phase_start = time.time()
        context.advance_to_next_phase(PipelinePhase.AB_TESTING)
        
        try:
            logger.info("Executing A/B testing phase")
            
            # Create A/B tests from evolution recommendations
            if context.evolution_plan and context.evolution_plan.improvements:
                # Select top 2-3 improvements for A/B testing
                top_improvements = sorted(
                    context.evolution_plan.improvements,
                    key=lambda x: x.confidence_score,
                    reverse=True
                )[:3]
                
                ab_tests = []
                for improvement in top_improvements:
                    if improvement.priority in ["critical", "high"]:
                        test = self.ab_testing_system.create_test_from_improvement(improvement)
                        ab_tests.append(test)
                
                context.ab_tests = ab_tests
                
                execution_time = time.time() - phase_start
                logger.info(f"A/B testing phase completed in {execution_time:.2f}s")
                logger.info(f"Created {len(ab_tests)} A/B tests")
                
                if execution_time > self.max_phase_time_seconds:
                    logger.warning(f"A/B testing exceeded 5-minute target: {execution_time:.2f}s")
            else:
                logger.warning("No evolution plan available for A/B testing")
            
        except Exception as e:
            error_msg = f"A/B testing failed: {str(e)}"
            logger.error(error_msg)
            context.record_phase_error(
                PipelinePhase.AB_TESTING,
                error_msg,
                ValidationSystemType.AB_TESTING
            )
    
    def get_pipeline_status(self, context: UnifiedBusinessContext) -> Dict[str, Any]:
        """Get current pipeline execution status"""
        
        return {
            "pipeline_state": context.pipeline_state.value,
            "total_time_seconds": context.get_total_pipeline_time(),
            "current_phase_time_seconds": context.get_current_phase_time(),
            "validation_score": context.validation_score,
            "within_25_minute_target": context.is_within_25_minute_target(),
            "completed_phases": len(context.pipeline_history),
            "errors_count": len(context.pipeline_errors),
            "business_name": context.business_name,
            "industry": context.industry
        }
    
    async def execute_single_phase(self, 
                                 context: UnifiedBusinessContext, 
                                 phase: PipelinePhase) -> bool:
        """Execute a single pipeline phase (useful for testing and recovery)"""
        
        phase_mapping = {
            PipelinePhase.CUSTOMER_ACQUISITION: self._execute_customer_acquisition_phase,
            PipelinePhase.FEEDBACK_COLLECTION: self._execute_feedback_collection_phase,
            PipelinePhase.VALIDATION_ANALYSIS: self._execute_validation_analysis_phase,
            PipelinePhase.MVP_EVOLUTION: self._execute_mvp_evolution_phase,
            PipelinePhase.AB_TESTING: self._execute_ab_testing_phase
        }
        
        if phase in phase_mapping:
            try:
                await phase_mapping[phase](context)
                return True
            except Exception as e:
                logger.error(f"Failed to execute phase {phase.value}: {str(e)}")
                return False
        
        logger.error(f"Unknown phase: {phase.value}")
        return False


if __name__ == "__main__":
    # Test the workflow orchestrator
    
    async def test_orchestrator():
        """Test orchestrator with sample data"""
        
        sample_interview_data = {
            "business_context": {
                "business_name": "HealthTech Scheduler",
                "industry": "healthcare",
                "business_model": "b2b_saas", 
                "target_audience": "Healthcare providers",
                "value_proposition": "AI-powered scheduling reduces no-shows by 40%",
                "problem_statement": "Clinics lose 20% revenue due to scheduling inefficiencies",
                "solution_description": "Smart scheduling with SMS reminders"
            },
            "technical_requirements": {
                "backend": "fastapi",
                "frontend": "react",
                "compliance": ["HIPAA"]
            },
            "confidence_score": 0.92
        }
        
        orchestrator = WorkflowOrchestrator()
        
        print("Testing workflow orchestrator...")
        result = await orchestrator.execute_complete_pipeline(sample_interview_data)
        
        print(f"Pipeline success: {result.success}")
        print(f"Execution time: {result.total_execution_time_seconds:.2f}s")
        print(f"Within 25-min target: {result.within_25_minute_target}")
        print(f"Validation score: {result.business_context.validation_score}")
        print(f"Completed phases: {len(result.completed_phases)}")
        
        if result.pipeline_errors:
            print(f"Errors: {result.pipeline_errors}")
        
        print("✅ Workflow orchestrator test completed")
    
    # Run test
    asyncio.run(test_orchestrator())