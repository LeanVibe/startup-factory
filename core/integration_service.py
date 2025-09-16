#!/usr/bin/env python3
"""
Integration Service - Core Service 8/8
Consolidates: startup_factory.py, all CLI interfaces, and external integrations
Unified interface for all startup factory operations and third-party integrations.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from ._compat import (
    Console,
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    Panel,
    Prompt,
    Confirm,
    Table,
)

# Import all core services (handle both package and standalone contexts)
try:
    # Try relative imports first (when used as package)
    from .conversation_service import ConversationService, BusinessBlueprint
    from .code_generation_service import CodeGenerationService, CodeArtifact
    from .orchestration_service import OrchestrationService, WorkflowStage
    from .deployment_service import DeploymentService, DeploymentConfig, CloudProvider
    from .multi_tenant_service import MultiTenantService, ResourceLimits
    from .ai_orchestration_service import AIOrchestrationService, AITask, TaskType, TaskPriority
    from .observability_service import ObservabilityService, MetricType
except ImportError:
    # Fallback to absolute imports (when used as standalone)
    try:
        import sys
        sys.path.append(str(Path(__file__).parent))
        from conversation_service import ConversationService, BusinessBlueprint
        from code_generation_service import CodeGenerationService, CodeArtifact
        from orchestration_service import OrchestrationService, WorkflowStage
        from deployment_service import DeploymentService, DeploymentConfig, CloudProvider
        from multi_tenant_service import MultiTenantService, ResourceLimits
        from ai_orchestration_service import AIOrchestrationService, AITask, TaskType, TaskPriority
        from observability_service import ObservabilityService, MetricType
    except ImportError as e:
        raise ImportError(
            f"Missing core service dependency: {e}. Ensure all core services are available."
        )

console = Console()
logger = logging.getLogger(__name__)


class OperationMode(str, Enum):
    """Operation modes for the integration service"""
    INTERACTIVE = "interactive"
    BATCH = "batch"
    API = "api"
    CLI = "cli"


class IntegrationStatus(str, Enum):
    """Status of external integrations"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class SystemConfiguration:
    """System-wide configuration"""
    api_keys: Dict[str, str]
    max_concurrent_startups: int = 10
    default_resource_limits: ResourceLimits = None
    enable_monitoring: bool = True
    enable_multi_tenant: bool = True
    operation_mode: OperationMode = OperationMode.INTERACTIVE


@dataclass
class StartupSession:
    """Complete startup generation session"""
    session_id: str
    tenant_id: Optional[str]
    blueprint: Optional[BusinessBlueprint]
    artifacts: List[CodeArtifact]
    deployment_result: Optional[Dict[str, Any]]
    
    # Session metadata
    created_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "active"
    total_cost: float = 0.0


class IntegrationService:
    """
    Unified integration service for all startup factory operations.
    Consolidates startup_factory.py, CLI interfaces, and external integrations.
    """
    
    def __init__(self, config: SystemConfiguration):
        self.config = config
        
        # Initialize core services
        self._initialize_core_services()
        
        # External integrations status
        self.integrations_status = {
            "anthropic": IntegrationStatus.UNKNOWN,
            "openai": IntegrationStatus.UNKNOWN,
            "docker": IntegrationStatus.UNKNOWN,
            "github": IntegrationStatus.UNKNOWN
        }
        
        # Session management
        self.active_sessions: Dict[str, StartupSession] = {}
        self.session_history: List[StartupSession] = []
        
        # System startup
        asyncio.create_task(self._initialize_system())
    
    def _initialize_core_services(self):
        """Initialize all core services"""
        
        # Core services
        self.conversation_service = ConversationService(self.config.api_keys.get("anthropic"))
        self.code_generation_service = CodeGenerationService(self.config.api_keys.get("anthropic"))
        self.orchestration_service = OrchestrationService(self.config.api_keys.get("anthropic"))
        self.deployment_service = DeploymentService()
        
        # Multi-tenant service (optional)
        if self.config.enable_multi_tenant:
            self.multi_tenant_service = MultiTenantService(self.config.max_concurrent_startups)
        else:
            self.multi_tenant_service = None
        
        # AI orchestration
        self.ai_orchestration_service = AIOrchestrationService(self.config.api_keys)
        
        # Observability service (optional)
        if self.config.enable_monitoring:
            self.observability_service = ObservabilityService()
        else:
            self.observability_service = None
    
    async def _initialize_system(self):
        """Initialize system and check integrations"""
        
        console.print("🚀 Initializing Startup Factory...")
        
        # Check API integrations
        await self._check_integrations()
        
        # Validate system requirements
        await self._validate_system()
        
        # Load previous sessions (if any)
        await self._load_session_history()
        
        console.print("✅ System initialization complete")
    
    async def _check_integrations(self):
        """Check status of external integrations"""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Check Anthropic
            task = progress.add_task("Checking Anthropic API...", total=1)
            try:
                # Test API connection
                test_task = AITask(
                    task_id="init_test",
                    task_type=TaskType.CONVERSATION,
                    priority=TaskPriority.LOW,
                    prompt="Hello",
                    context={},
                    max_tokens=10
                )
                await self.ai_orchestration_service.submit_task(test_task)
                result = await self.ai_orchestration_service.get_task_result("init_test", timeout=30)
                
                if result and result.success:
                    self.integrations_status["anthropic"] = IntegrationStatus.CONNECTED
                else:
                    self.integrations_status["anthropic"] = IntegrationStatus.ERROR
                    
            except Exception:
                self.integrations_status["anthropic"] = IntegrationStatus.ERROR
            
            progress.advance(task, 1)
            
            # Check Docker
            task = progress.add_task("Checking Docker...", total=1)
            try:
                import docker
                client = docker.from_env()
                client.ping()
                self.integrations_status["docker"] = IntegrationStatus.CONNECTED
            except Exception:
                self.integrations_status["docker"] = IntegrationStatus.DISCONNECTED
            
            progress.advance(task, 1)
    
    async def _validate_system(self):
        """Validate system requirements and configuration"""
        
        # Check Python version
        if sys.version_info < (3, 10):
            console.print("⚠️ Python 3.10+ recommended for optimal performance")
        
        # Check resource availability
        if self.multi_tenant_service:
            overview = self.multi_tenant_service.get_system_overview()
            if overview["resource_utilization"]["memory_utilization"] > 80:
                console.print("⚠️ High memory utilization detected")
        
        # Check observability
        if self.observability_service:
            health = await self.observability_service.get_system_health()
            if health["overall_status"] != "healthy":
                console.print(f"⚠️ System health: {health['overall_status']}")
    
    async def _load_session_history(self):
        """Load previous session history"""
        
        # In a real implementation, this would load from persistent storage
        # For now, start with empty history
        self.session_history = []
    
    async def start_complete_workflow(
        self,
        business_name: str,
        founder_email: Optional[str] = None,
        resource_limits: Optional[ResourceLimits] = None
    ) -> StartupSession:
        """Start complete 25-minute startup generation workflow"""
        
        console.print(Panel(
            f"🏭 Starting complete workflow for: [bold]{business_name}[/bold]",
            title="Startup Factory"
        ))
        
        # Create tenant if multi-tenant enabled
        tenant_id = None
        if self.multi_tenant_service:
            tenant_id = await self.multi_tenant_service.create_tenant(
                business_name, 
                founder_email or "unknown@example.com",
                resource_limits or self.config.default_resource_limits
            )
        
        # Create session
        session = StartupSession(
            session_id=f"session_{int(datetime.utcnow().timestamp())}",
            tenant_id=tenant_id,
            blueprint=None,
            artifacts=[],
            deployment_result=None,
            created_at=datetime.utcnow(),
            status="running"
        )
        
        self.active_sessions[session.session_id] = session
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console,
            ) as progress:
                
                # Step 1: Founder Interview (15 minutes)
                interview_task = progress.add_task("🤖 Conducting AI Architect interview...", total=1)
                blueprint = await self.conversation_service.conduct_founder_interview(session.session_id)
                session.blueprint = blueprint
                
                # Update tenant with blueprint
                if self.multi_tenant_service and tenant_id:
                    await self.multi_tenant_service.update_tenant_blueprint(tenant_id, blueprint)
                
                progress.advance(interview_task, 1)
                
                # Record metrics
                if self.observability_service:
                    self.observability_service.record_metric(
                        "founder_interview_completed", 1, MetricType.COUNTER
                    )
                
                # Step 2: Code Generation (5 minutes)
                codegen_task = progress.add_task("⚡ Generating intelligent code...", total=1)
                artifacts = await self.code_generation_service.generate_complete_mvp(blueprint)
                session.artifacts = artifacts
                progress.advance(codegen_task, 1)
                
                # Step 3: Deployment (3 minutes)
                deploy_task = progress.add_task("🚀 Deploying to production...", total=1)
                
                deploy_config = DeploymentConfig(
                    provider=CloudProvider.DOCKER_LOCAL,
                    environment="dev",
                    resource_limits={"memory": "1G", "cpu": "0.5"},
                    environment_variables={}
                )
                
                # Create temporary project directory
                project_path = f"/tmp/{business_name.lower().replace(' ', '_')}_{session.session_id}"
                
                deployment_result = await self.deployment_service.deploy_complete_mvp(
                    project_path=project_path,
                    blueprint=blueprint,
                    artifacts=artifacts,
                    config=deploy_config
                )
                
                session.deployment_result = {
                    "success": deployment_result.success,
                    "urls": deployment_result.urls,
                    "deployment_id": deployment_result.deployment_id
                }
                
                progress.advance(deploy_task, 1)
        
            # Complete session
            session.completed_at = datetime.utcnow()
            session.status = "completed"
            
            # Calculate total cost
            if self.multi_tenant_service and tenant_id:
                cost_data = await self.multi_tenant_service.track_tenant_costs(tenant_id)
                session.total_cost = cost_data.get("total_cost", 0.0)
            
            # Update business metrics
            if self.observability_service:
                self.observability_service.update_business_metrics(
                    startups_created_today=1,  # Increment
                    successful_deployments=1 if session.deployment_result["success"] else 0
                )
            
            # Move to history
            self.session_history.append(session)
            if session.session_id in self.active_sessions:
                del self.active_sessions[session.session_id]
            
            return session
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            session.status = "failed"
            
            # Move to history
            self.session_history.append(session)
            if session.session_id in self.active_sessions:
                del self.active_sessions[session.session_id]
            
            raise
    
    async def run_interactive_mode(self):
        """Run interactive command-line interface"""
        
        console.print(Panel(
            """
🏭 Welcome to Startup Factory!
Transform your business idea into a live MVP in 25 minutes.

Choose an option below to get started.
            """.strip(),
            title="Startup Factory v2.0",
            border_style="blue"
        ))
        
        while True:
            # Display menu
            menu_table = Table(title="What would you like to do?")
            menu_table.add_column("Option", style="cyan")
            menu_table.add_column("Description", style="green")
            menu_table.add_column("Time", style="yellow")
            
            menu_table.add_row("1", "🎯 Complete Day One Experience", "25 minutes")
            menu_table.add_row("2", "🤖 Founder Interview Only", "15 minutes")
            menu_table.add_row("3", "📊 System Status & Health", "1 minute")
            menu_table.add_row("4", "🏢 Multi-Tenant Dashboard", "2 minutes")
            menu_table.add_row("5", "📈 Business Analytics", "2 minutes")
            menu_table.add_row("6", "🎥 Show Demonstration", "5 minutes")
            menu_table.add_row("0", "❌ Exit", "-")
            
            console.print(menu_table)
            
            choice = Prompt.ask("Enter your choice", choices=["0", "1", "2", "3", "4", "5", "6"])
            
            if choice == "0":
                console.print("👋 Thanks for using Startup Factory!")
                break
            elif choice == "1":
                await self._handle_complete_workflow()
            elif choice == "2":
                await self._handle_founder_interview()
            elif choice == "3":
                await self._show_system_status()
            elif choice == "4":
                self._show_multi_tenant_dashboard()
            elif choice == "5":
                self._show_business_analytics()
            elif choice == "6":
                self._show_demonstration()
    
    async def _handle_complete_workflow(self):
        """Handle complete workflow from interactive mode"""
        
        business_name = Prompt.ask("What's your business name/idea?")
        founder_email = Prompt.ask("Your email (optional)", default="")
        
        if not founder_email:
            founder_email = None
        
        try:
            session = await self.start_complete_workflow(business_name, founder_email)
            
            # Display results
            console.print(Panel(
                f"""
🎉 Success! Your startup is live!

Business: {session.blueprint.business_name if session.blueprint else business_name}
Industry: {session.blueprint.industry.value if session.blueprint else 'Unknown'}
Model: {session.blueprint.business_model.value if session.blueprint else 'Unknown'}

Generated Files: {len(session.artifacts)}
Deployment: {'✅ Success' if session.deployment_result and session.deployment_result['success'] else '❌ Failed'}
URLs: {json.dumps(session.deployment_result.get('urls', {}), indent=2) if session.deployment_result else 'None'}

Total Time: {(session.completed_at - session.created_at).total_seconds():.1f} seconds
Cost: ${session.total_cost:.4f}
                """.strip(),
                title="🚀 Startup Generated!",
                border_style="green"
            ))
            
        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")
    
    async def _handle_founder_interview(self):
        """Handle founder interview only"""
        
        console.print("🤖 Starting AI Architect interview...")
        
        session_id = f"interview_{int(datetime.utcnow().timestamp())}"
        blueprint = await self.conversation_service.conduct_founder_interview(session_id)
        
        console.print(Panel(
            f"""
📋 Business Blueprint Generated

Name: {blueprint.business_name}
Industry: {blueprint.industry.value}
Business Model: {blueprint.business_model.value}
Target Audience: {blueprint.target_audience}

Key Features:
{chr(10).join(f'• {feature}' for feature in blueprint.key_features)}

Value Proposition: {blueprint.value_proposition}
Competitive Advantage: {blueprint.competitive_advantage}

Confidence Score: {blueprint.confidence_score:.1f}/1.0
            """.strip(),
            title="Blueprint Complete",
            border_style="blue"
        ))
        
        # Ask if they want to continue to full workflow
        if Confirm.ask("Would you like to generate code and deploy this startup?"):
            session = await self.start_complete_workflow(
                blueprint.business_name, 
                "interview@example.com"  # Placeholder
            )
            console.print("🎉 Complete workflow finished! Check the results above.")
    
    async def _show_system_status(self):
        """Show comprehensive system status"""
        
        console.print("📊 Checking system status...")
        
        # Integration status
        integration_table = Table(title="Integration Status")
        integration_table.add_column("Service", style="cyan")
        integration_table.add_column("Status", style="green")
        
        for service, status in self.integrations_status.items():
            status_icon = {
                IntegrationStatus.CONNECTED: "🟢 Connected",
                IntegrationStatus.DISCONNECTED: "🔴 Disconnected", 
                IntegrationStatus.ERROR: "🟡 Error",
                IntegrationStatus.UNKNOWN: "⚪ Unknown"
            }.get(status, "❓ Unknown")
            
            integration_table.add_row(service.title(), status_icon)
        
        console.print(integration_table)
        
        # System health
        if self.observability_service:
            health = await self.observability_service.get_system_health()
            
            health_panel = Panel(
                f"""
Overall Status: {health['overall_status'].upper()}
Active Alerts: {health['active_alerts']}
Last Updated: {health['last_updated']}
            """.strip(),
                title="System Health"
            )
            
            console.print(health_panel)
    
    def _show_multi_tenant_dashboard(self):
        """Show multi-tenant system dashboard"""
        
        if not self.multi_tenant_service:
            console.print("❌ Multi-tenant service not enabled")
            return
        
        console.print("🏢 Multi-Tenant System Dashboard")
        self.multi_tenant_service.display_system_status()
    
    def _show_business_analytics(self):
        """Show business analytics and metrics"""
        
        if not self.observability_service:
            console.print("❌ Analytics service not enabled")
            return
        
        console.print("📈 Business Analytics")
        
        # Session history
        session_table = Table(title="Recent Sessions")
        session_table.add_column("Session", style="cyan")
        session_table.add_column("Business", style="green")
        session_table.add_column("Status", style="yellow")
        session_table.add_column("Cost", style="red")
        
        for session in self.session_history[-10:]:  # Last 10 sessions
            session_table.add_row(
                session.session_id[:12],
                session.blueprint.business_name if session.blueprint else "Unknown",
                session.status,
                f"${session.total_cost:.4f}"
            )
        
        console.print(session_table)
        
        # Business metrics
        business_metrics = Panel(
            f"""
Total Sessions: {len(self.session_history)}
Active Sessions: {len(self.active_sessions)}
Success Rate: {len([s for s in self.session_history if s.status == 'completed'])/max(len(self.session_history), 1)*100:.1f}%
Avg Cost per Session: ${sum(s.total_cost for s in self.session_history)/max(len(self.session_history), 1):.4f}
            """.strip(),
            title="Business Metrics"
        )
        
        console.print(business_metrics)
    
    def _show_demonstration(self):
        """Show system demonstration"""
        
        demo_panel = Panel(
            """
🎥 Startup Factory Demonstration

The Transformation:
FROM: Complex 95-file infrastructure requiring technical expertise
TO: Conversational AI system generating live MVPs in 25 minutes

The Process:
1. 🤖 AI Interview (15 min) - Natural conversation about your business
2. 🧠 Intelligence (2 min) - AI generates business-specific logic  
3. ⚡ Code Gen (5 min) - Complete MVP with frontend, backend, database
4. 🚀 Deploy (3 min) - Live URL with admin dashboard

What You Get:
• Live MVP with public URL for customer validation
• Complete codebase with production-ready architecture
• Admin dashboard with real business analytics
• Industry-specific compliance (HIPAA, PCI, FERPA)
• Docker deployment ready for scaling
• Complete documentation and API docs

Zero technical knowledge required. Just bring your business idea.

Ready to experience it? Choose option 1 from the main menu!
            """.strip(),
            title="System Demonstration",
            border_style="magenta"
        )
        
        console.print(demo_panel)
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview"""
        
        overview = {
            "integrations": dict(self.integrations_status),
            "active_sessions": len(self.active_sessions),
            "total_sessions": len(self.session_history),
            "success_rate": len([s for s in self.session_history if s.status == "completed"]) / max(len(self.session_history), 1) * 100,
            "system_health": "unknown",
            "multi_tenant": {
                "enabled": self.multi_tenant_service is not None,
                "active_tenants": 0,
                "resource_utilization": {}
            },
            "observability": {
                "enabled": self.observability_service is not None,
                "active_alerts": 0
            }
        }
        
        # Get health status
        if self.observability_service:
            health = await self.observability_service.get_system_health()
            overview["system_health"] = health["overall_status"]
            overview["observability"]["active_alerts"] = health["active_alerts"]
        
        # Get multi-tenant stats
        if self.multi_tenant_service:
            mt_overview = self.multi_tenant_service.get_system_overview()
            overview["multi_tenant"]["active_tenants"] = mt_overview["active_tenants"]
            overview["multi_tenant"]["resource_utilization"] = mt_overview["resource_utilization"]
        
        return overview
    
    def shutdown(self):
        """Gracefully shutdown all services"""
        
        console.print("🔄 Shutting down Startup Factory...")
        
        # Stop observability
        if self.observability_service:
            self.observability_service.stop_monitoring()
        
        console.print("✅ Shutdown complete")


# Main CLI interface
async def main():
    """Main CLI interface"""
    
    # Load configuration
    config = SystemConfiguration(
        api_keys={
            "anthropic": "your-anthropic-key-here",
            "openai": "your-openai-key-here",
            "perplexity": "your-perplexity-key-here"
        },
        max_concurrent_startups=5,
        default_resource_limits=ResourceLimits(
            memory_mb=512,
            cpu_cores=0.5,
            storage_gb=2
        )
    )
    
    # Initialize integration service
    integration_service = IntegrationService(config)
    
    try:
        # Run interactive mode
        await integration_service.run_interactive_mode()
        
    finally:
        # Cleanup
        integration_service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
