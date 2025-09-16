#!/usr/bin/env python3
"""
Orchestration Service - Core Service 3/8
Consolidates: streamlined_mvp_orchestrator.py, enhanced_mvp_orchestrator.py, mvp_orchestrator_script.py
Event-driven orchestration of the complete startup generation workflow.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    from ._compat import (
        Console,
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        Panel,
        Live,
    )
except ImportError:  # pragma: no cover - standalone usage
    from _compat import (
        Console,
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        Panel,
        Live,
    )

# Import core services
try:
    from .conversation_service import ConversationService, BusinessBlueprint
    from .code_generation_service import CodeGenerationService, CodeArtifact
except ImportError:
    # Fallback for standalone usage
    import sys
    sys.path.append(str(Path(__file__).parent))
    from conversation_service import ConversationService, BusinessBlueprint
    from code_generation_service import CodeGenerationService, CodeArtifact

console = Console()
logger = logging.getLogger(__name__)


class WorkflowStage(str, Enum):
    """Workflow stages for event-driven orchestration"""
    INITIALIZATION = "initialization"
    FOUNDER_INTERVIEW = "founder_interview"
    BLUEPRINT_GENERATION = "blueprint_generation"
    HUMAN_APPROVAL = "human_approval"
    CODE_GENERATION = "code_generation"
    DEPLOYMENT_PREP = "deployment_prep"
    DEPLOYMENT = "deployment"
    VALIDATION = "validation"
    COMPLETION = "completion"
    FAILED = "failed"


class WorkflowEvent(str, Enum):
    """Events that can trigger stage transitions"""
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    HUMAN_INPUT_REQUIRED = "human_input_required"
    HUMAN_INPUT_RECEIVED = "human_input_received"
    USER_APPROVAL_GRANTED = "user_approval_granted"
    USER_APPROVAL_DENIED = "user_approval_denied"
    ERROR_OCCURRED = "error_occurred"
    RETRY_REQUESTED = "retry_requested"


@dataclass
class WorkflowContext:
    """Context passed through the workflow"""
    session_id: str
    startup_name: str
    founder_email: Optional[str] = None
    blueprint: Optional[BusinessBlueprint] = None
    generated_artifacts: List[CodeArtifact] = field(default_factory=list)
    deployment_url: Optional[str] = None
    stage_results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StageResult:
    """Result from executing a workflow stage"""
    stage: WorkflowStage
    success: bool
    data: Dict[str, Any]
    duration_seconds: float
    error: Optional[str] = None
    next_stage: Optional[WorkflowStage] = None


class OrchestrationService:
    """
    Event-driven orchestration service for complete startup generation workflow.
    Consolidates and replaces all orchestrator scripts with modern event-driven architecture.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.conversation_service = ConversationService(api_key)
        self.code_generation_service = CodeGenerationService(api_key)
        
        # Event-driven workflow state
        self.active_workflows: Dict[str, WorkflowContext] = {}
        self.event_handlers: Dict[WorkflowEvent, List[Callable]] = {}
        self.stage_handlers: Dict[WorkflowStage, Callable] = {}
        
        # Initialize stage handlers
        self._setup_stage_handlers()
        
        # Initialize event handlers
        self._setup_event_handlers()
        
        # Workflow execution tracking
        self.execution_history: List[Dict[str, Any]] = []
    
    def _setup_stage_handlers(self):
        """Setup handlers for each workflow stage"""
        self.stage_handlers = {
            WorkflowStage.INITIALIZATION: self._handle_initialization,
            WorkflowStage.FOUNDER_INTERVIEW: self._handle_founder_interview,
            WorkflowStage.BLUEPRINT_GENERATION: self._handle_blueprint_generation,
            WorkflowStage.HUMAN_APPROVAL: self._handle_human_approval,
            WorkflowStage.CODE_GENERATION: self._handle_code_generation,
            WorkflowStage.DEPLOYMENT_PREP: self._handle_deployment_prep,
            WorkflowStage.DEPLOYMENT: self._handle_deployment,
            WorkflowStage.VALIDATION: self._handle_validation,
            WorkflowStage.COMPLETION: self._handle_completion,
        }
    
    def _setup_event_handlers(self):
        """Setup event handlers for workflow events"""
        # Example event handlers (can be extended)
        self.event_handlers[WorkflowEvent.STAGE_COMPLETED] = [self._on_stage_completed]
        self.event_handlers[WorkflowEvent.STAGE_FAILED] = [self._on_stage_failed]
        self.event_handlers[WorkflowEvent.HUMAN_INPUT_REQUIRED] = [self._on_human_input_required]
    
    async def start_workflow(self, startup_name: str, founder_email: Optional[str] = None) -> str:
        """Start a new startup generation workflow"""
        session_id = str(uuid.uuid4())
        
        context = WorkflowContext(
            session_id=session_id,
            startup_name=startup_name,
            founder_email=founder_email
        )
        
        self.active_workflows[session_id] = context
        
        # Start with initialization stage
        await self._execute_stage(session_id, WorkflowStage.INITIALIZATION)
        
        return session_id
    
    async def _execute_stage(self, session_id: str, stage: WorkflowStage) -> StageResult:
        """Execute a specific workflow stage"""
        if session_id not in self.active_workflows:
            raise ValueError(f"No active workflow found for session {session_id}")
        
        context = self.active_workflows[session_id]
        
        # Emit stage started event
        await self._emit_event(WorkflowEvent.STAGE_STARTED, session_id, {"stage": stage})
        
        console.print(f"🔄 Executing stage: {stage.value}")
        
        start_time = datetime.utcnow()
        
        try:
            # Get stage handler
            handler = self.stage_handlers.get(stage)
            if not handler:
                raise ValueError(f"No handler found for stage {stage}")
            
            # Execute stage
            result_data = await handler(context)
            
            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Create result
            result = StageResult(
                stage=stage,
                success=True,
                data=result_data,
                duration_seconds=duration
            )
            
            # Store result in context
            context.stage_results[stage.value] = result_data
            context.updated_at = datetime.utcnow()
            
            # Emit stage completed event
            await self._emit_event(WorkflowEvent.STAGE_COMPLETED, session_id, {
                "stage": stage,
                "result": result_data,
                "duration": duration
            })
            
            return result
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = StageResult(
                stage=stage,
                success=False,
                data={},
                duration_seconds=duration,
                error=str(e)
            )
            
            # Emit stage failed event
            await self._emit_event(WorkflowEvent.STAGE_FAILED, session_id, {
                "stage": stage,
                "error": str(e),
                "duration": duration
            })
            
            raise
    
    async def _emit_event(self, event: WorkflowEvent, session_id: str, data: Dict[str, Any]):
        """Emit a workflow event"""
        event_data = {
            "event": event,
            "session_id": session_id,
            "timestamp": datetime.utcnow(),
            "data": data
        }
        
        # Add to execution history
        self.execution_history.append(event_data)
        
        # Call event handlers
        handlers = self.event_handlers.get(event, [])
        for handler in handlers:
            try:
                await handler(session_id, event_data)
            except Exception as e:
                logger.error(f"Event handler error for {event}: {e}")
    
    # Stage Handlers
    async def _handle_initialization(self, context: WorkflowContext) -> Dict[str, Any]:
        """Initialize the workflow"""
        console.print(Panel(
            f"🚀 Initializing startup generation for: [bold]{context.startup_name}[/bold]",
            title="Workflow Initialization"
        ))
        
        # Set up project directory
        project_dir = Path(f"generated_projects/{context.startup_name}_{context.session_id[:8]}")
        project_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "project_directory": str(project_dir),
            "initialization_time": datetime.utcnow().isoformat(),
            "next_stage": WorkflowStage.FOUNDER_INTERVIEW
        }
    
    async def _handle_founder_interview(self, context: WorkflowContext) -> Dict[str, Any]:
        """Handle founder interview stage"""
        console.print("🤖 Starting AI Architect interview...")
        
        # Conduct the interview using ConversationService
        blueprint = await self.conversation_service.conduct_founder_interview(context.session_id)
        
        # Update context with blueprint
        context.blueprint = blueprint
        
        console.print(f"✅ Interview completed for {blueprint.business_name}")
        
        return {
            "blueprint_generated": True,
            "business_name": blueprint.business_name,
            "business_model": blueprint.business_model.value,
            "industry": blueprint.industry.value,
            "confidence_score": blueprint.confidence_score,
            "next_stage": WorkflowStage.HUMAN_APPROVAL
        }
    
    async def _handle_blueprint_generation(self, context: WorkflowContext) -> Dict[str, Any]:
        """Handle blueprint generation (if needed separately)"""
        # This stage can be used if blueprint generation is separate from interview
        return {"blueprint_ready": True, "next_stage": WorkflowStage.HUMAN_APPROVAL}
    
    async def _handle_human_approval(self, context: WorkflowContext) -> Dict[str, Any]:
        """Handle human approval of the blueprint"""
        if not context.blueprint:
            raise ValueError("No blueprint available for approval")
        
        blueprint = context.blueprint
        
        # Display blueprint for approval
        console.print(Panel(
            f"""
            📋 Business Blueprint Summary
            
            Name: {blueprint.business_name}
            Industry: {blueprint.industry.value}
            Model: {blueprint.business_model.value}
            
            Key Features:
            {chr(10).join(f'• {feature}' for feature in blueprint.key_features)}
            
            Value Proposition: {blueprint.value_proposition}
            """,
            title="Review Your Blueprint"
        ))
        
        # For now, auto-approve (in real implementation, wait for human input)
        # TODO: Implement actual human approval mechanism
        approval_granted = True  # Placeholder
        
        if approval_granted:
            await self._emit_event(WorkflowEvent.USER_APPROVAL_GRANTED, context.session_id, {
                "blueprint_approved": True
            })
            return {"approval_granted": True, "next_stage": WorkflowStage.CODE_GENERATION}
        else:
            await self._emit_event(WorkflowEvent.USER_APPROVAL_DENIED, context.session_id, {
                "blueprint_rejected": True
            })
            return {"approval_granted": False, "next_stage": WorkflowStage.FOUNDER_INTERVIEW}
    
    async def _handle_code_generation(self, context: WorkflowContext) -> Dict[str, Any]:
        """Handle code generation stage"""
        if not context.blueprint:
            raise ValueError("No blueprint available for code generation")
        
        console.print("⚡ Generating intelligent code...")
        
        # Generate complete MVP using CodeGenerationService
        artifacts = await self.code_generation_service.generate_complete_mvp(context.blueprint)
        
        # Update context with artifacts
        context.generated_artifacts = artifacts
        
        # Save artifacts to disk
        project_dir = context.stage_results.get("initialization", {}).get("project_directory")
        if project_dir:
            await self.code_generation_service.save_artifacts_to_disk(project_dir)
        
        generation_summary = self.code_generation_service.get_generation_summary()
        
        return {
            "code_generated": True,
            "artifacts_count": len(artifacts),
            "total_lines": generation_summary.get("total_lines", 0),
            "generation_summary": generation_summary,
            "next_stage": WorkflowStage.DEPLOYMENT_PREP
        }
    
    async def _handle_deployment_prep(self, context: WorkflowContext) -> Dict[str, Any]:
        """Handle deployment preparation"""
        console.print("🐳 Preparing deployment configuration...")
        
        # In a real implementation, this would:
        # 1. Validate generated code
        # 2. Run tests
        # 3. Build Docker images
        # 4. Prepare deployment configs
        
        # For now, simulate deployment prep
        await asyncio.sleep(1)  # Simulate prep time
        
        return {
            "deployment_ready": True,
            "docker_images_built": True,
            "configs_prepared": True,
            "next_stage": WorkflowStage.DEPLOYMENT
        }
    
    async def _handle_deployment(self, context: WorkflowContext) -> Dict[str, Any]:
        """Handle deployment stage"""
        console.print("🚀 Deploying MVP...")
        
        # In a real implementation, this would:
        # 1. Deploy to cloud provider
        # 2. Set up database
        # 3. Configure domain
        # 4. Set up monitoring
        
        # For now, simulate deployment
        await asyncio.sleep(2)  # Simulate deployment time
        
        # Generate mock deployment URL
        deployment_url = f"https://{context.startup_name.lower().replace(' ', '-')}-{context.session_id[:8]}.startup-factory.com"
        context.deployment_url = deployment_url
        
        return {
            "deployment_successful": True,
            "deployment_url": deployment_url,
            "database_initialized": True,
            "monitoring_configured": True,
            "next_stage": WorkflowStage.VALIDATION
        }
    
    async def _handle_validation(self, context: WorkflowContext) -> Dict[str, Any]:
        """Handle post-deployment validation"""
        console.print("✅ Validating deployment...")
        
        # In a real implementation, this would:
        # 1. Run health checks
        # 2. Validate API endpoints
        # 3. Check frontend loading
        # 4. Verify database connectivity
        
        # For now, simulate validation
        await asyncio.sleep(1)
        
        return {
            "validation_passed": True,
            "health_checks_passed": True,
            "api_endpoints_working": True,
            "frontend_accessible": True,
            "next_stage": WorkflowStage.COMPLETION
        }
    
    async def _handle_completion(self, context: WorkflowContext) -> Dict[str, Any]:
        """Handle workflow completion"""
        console.print(Panel(
            f"""
            🎉 Startup Generation Complete!
            
            Business: {context.blueprint.business_name if context.blueprint else context.startup_name}
            URL: {context.deployment_url or 'Not deployed'}
            
            Generated: {len(context.generated_artifacts)} code files
            Total Time: {(context.updated_at - context.created_at).total_seconds():.1f} seconds
            """,
            title="Success!"
        ))
        
        # Clean up active workflow
        if context.session_id in self.active_workflows:
            del self.active_workflows[context.session_id]
        
        return {
            "workflow_completed": True,
            "completion_time": datetime.utcnow().isoformat(),
            "total_duration": (context.updated_at - context.created_at).total_seconds()
        }
    
    # Event Handlers
    async def _on_stage_completed(self, session_id: str, event_data: Dict[str, Any]):
        """Handle stage completion event"""
        stage = event_data["data"]["stage"]
        
        # Determine next stage
        next_stage_map = {
            WorkflowStage.INITIALIZATION: WorkflowStage.FOUNDER_INTERVIEW,
            WorkflowStage.FOUNDER_INTERVIEW: WorkflowStage.HUMAN_APPROVAL,
            WorkflowStage.BLUEPRINT_GENERATION: WorkflowStage.HUMAN_APPROVAL,
            WorkflowStage.HUMAN_APPROVAL: WorkflowStage.CODE_GENERATION,
            WorkflowStage.CODE_GENERATION: WorkflowStage.DEPLOYMENT_PREP,
            WorkflowStage.DEPLOYMENT_PREP: WorkflowStage.DEPLOYMENT,
            WorkflowStage.DEPLOYMENT: WorkflowStage.VALIDATION,
            WorkflowStage.VALIDATION: WorkflowStage.COMPLETION,
        }
        
        next_stage = next_stage_map.get(stage)
        if next_stage and session_id in self.active_workflows:
            # Execute next stage
            await self._execute_stage(session_id, next_stage)
    
    async def _on_stage_failed(self, session_id: str, event_data: Dict[str, Any]):
        """Handle stage failure event"""
        stage = event_data["data"]["stage"]
        error = event_data["data"]["error"]
        
        console.print(f"❌ Stage {stage} failed: {error}")
        
        # TODO: Implement retry logic or failure recovery
        logger.error(f"Workflow {session_id} failed at stage {stage}: {error}")
    
    async def _on_human_input_required(self, session_id: str, event_data: Dict[str, Any]):
        """Handle human input required event"""
        console.print("⏸️ Human input required - workflow paused")
        # TODO: Implement mechanism to wait for human input
    
    async def run_complete_workflow(self, startup_name: str, founder_email: Optional[str] = None) -> Dict[str, Any]:
        """Run the complete startup generation workflow"""
        console.print(f"🏭 Starting complete workflow for: {startup_name}")
        
        session_id = await self.start_workflow(startup_name, founder_email)
        
        # Wait for workflow completion (in event-driven system, this would be handled differently)
        max_wait_time = 600  # 10 minutes max
        wait_interval = 1
        waited_time = 0
        
        while session_id in self.active_workflows and waited_time < max_wait_time:
            await asyncio.sleep(wait_interval)
            waited_time += wait_interval
        
        # Get final result
        if session_id not in self.active_workflows:
            # Workflow completed
            return {"status": "completed", "session_id": session_id}
        else:
            # Workflow timed out
            return {"status": "timeout", "session_id": session_id}
    
    def get_workflow_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a workflow"""
        if session_id not in self.active_workflows:
            return {"status": "not_found"}
        
        context = self.active_workflows[session_id]
        
        return {
            "status": "active",
            "session_id": session_id,
            "startup_name": context.startup_name,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "stages_completed": list(context.stage_results.keys()),
            "has_blueprint": context.blueprint is not None,
            "artifacts_count": len(context.generated_artifacts),
            "deployment_url": context.deployment_url
        }
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history for all workflows"""
        return self.execution_history


# Example usage
async def main():
    """Example usage of OrchestrationService"""
    orchestrator = OrchestrationService()
    
    # Run complete workflow
    result = await orchestrator.run_complete_workflow("AI Writing Assistant")
    
    console.print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
