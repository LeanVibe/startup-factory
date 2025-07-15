#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "anthropic>=0.45.0",
#     "openai>=1.50.0",
#     "pydantic>=2.9.0",
#     "pydantic-ai>=0.0.14",
#     "rich>=13.9.0",
#     "aiofiles>=24.1.0",
#     "httpx>=0.28.0",
#     "pyyaml>=6.0.2",
# ]
# ///
"""
MVP Development Orchestrator
Main agent-led orchestration: comprehensive Python script to manage AI-powered MVP development workflow.

Transition: Claude code orchestration replaced by main agent leadership. All escalation protocols, provider assignments, and human-in-the-loop gates now reference main agent as the orchestrator.

USAGE:
    # Make script executable and run directly
    chmod +x mvp-orchestrator-script.py
    ./mvp-orchestrator-script.py

    # Or use uv run (recommended)
    uv run mvp-orchestrator-script.py

FEATURES:
    - Self-contained with automatic dependency management via uv
    - Interactive workflow for MVP development
    - Human-in-the-loop gates for decision making
    - Multi-AI provider integration (OpenAI, Anthropic, Perplexity)
    - Cost tracking and project management
    - Document generation and storage

REQUIREMENTS:
    - Python 3.10+
    - uv package manager (for automatic dependency management)
    - API keys for OpenAI, Anthropic, and Perplexity

SETUP:
    1. Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh
    2. Run script: uv run mvp-orchestrator-script.py
    3. Follow prompts to configure API keys

Dependencies are automatically managed and installed in an isolated environment.
No manual pip install required when using uv.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field

# Check and install dependencies automatically
try:
    import yaml
    import anthropic
    import openai
    from pydantic import BaseModel, Field, field_validator
    from pydantic_ai import Agent
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.prompt import Confirm, Prompt
    from rich.logging import RichHandler
    import aiofiles
    import httpx
except ImportError as e:
    print(f"""
Missing dependency: {e}

This script requires uv to manage dependencies automatically.

Install uv:
  curl -LsSf https://astral.sh/uv/install.sh | sh

Then run this script with:
  uv run {__file__}

Or manually install dependencies:
  pip install anthropic openai pydantic pydantic-ai rich aiofiles httpx pyyaml
""")
    exit(1)

# Initialize rich console for beautiful output
console = Console()

# Configure logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("mvp_orchestrator")

# ===== CONFIGURATION MODELS =====


class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"


class GateStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_NEEDED = "revision_needed"


class PhaseStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Config(BaseModel):
    """Main configuration model"""

    openai_api_key: str = Field(..., description="OpenAI API key")
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    perplexity_api_key: str = Field(..., description="Perplexity API key")

    project_root: Path = Field(
        default=Path("./mvp_projects"), description="Root directory for projects"
    )
    max_retries: int = Field(default=3, description="Maximum API retry attempts")
    timeout: int = Field(default=30, description="API timeout in seconds")

    # Perplexity integration options
    use_perplexity_app: bool = Field(
        default=False, description="Use Perplexity app instead of API"
    )

    # Cost tracking
    openai_input_cost_per_1k: float = Field(
        default=0.01, description="OpenAI input cost per 1k tokens"
    )
    openai_output_cost_per_1k: float = Field(
        default=0.03, description="OpenAI output cost per 1k tokens"
    )
    anthropic_input_cost_per_1k: float = Field(
        default=0.015, description="Anthropic input cost per 1k tokens"
    )
    anthropic_output_cost_per_1k: float = Field(
        default=0.075, description="Anthropic output cost per 1k tokens"
    )
    perplexity_cost_per_request: float = Field(
        default=0.005, description="Perplexity cost per request"
    )

    @field_validator("project_root")
    @classmethod
    def create_project_root(cls, v):
        v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v


# ===== PROJECT MODELS =====


class ProjectContext(BaseModel):
    """Stores all project-related data"""

    project_id: str
    project_name: str
    industry: str
    category: str
    created_at: datetime = Field(default_factory=datetime.now)

    # Phase tracking
    current_phase: int = 1
    phase_status: Dict[str, PhaseStatus] = Field(default_factory=dict)

    # Data storage
    market_research: Optional[Dict[str, Any]] = None
    founder_analysis: Optional[Dict[str, Any]] = None
    mvp_spec: Optional[Dict[str, Any]] = None
    architecture: Optional[Dict[str, Any]] = None
    code_artifacts: Dict[str, str] = Field(default_factory=dict)
    deployment_config: Optional[Dict[str, Any]] = None

    # Gates
    gates: Dict[str, GateStatus] = Field(default_factory=dict)

    # Metrics
    api_costs: Dict[str, float] = Field(default_factory=dict)
    time_spent: Dict[str, float] = Field(default_factory=dict)


# ===== PROMPTS STORAGE =====

PROMPTS = {
    "market_research": """Analyze the market opportunity for {industry} focusing on {category}:

1. Market size and growth projections (2024-2027)
2. Top 10 emerging trends with supporting data
3. Underserved customer segments
4. Technology enablers creating new opportunities
5. Regulatory changes affecting the market

Requirements:
- Include specific statistics and sources
- Focus on B2B/B2C opportunities under $10M ARR
- Highlight gaps where solo founders can compete
- Provide revenue model examples for each opportunity

Format: Structured markdown with clear sections and bullet points""",
    "founder_fit": """<analysis_request>
<founder_profile>
Skills: {skills}
Experience: {experience}
Network: {network}
Resources: {resources}
</founder_profile>

<market_opportunities>
{opportunities}
</market_opportunities>

Evaluate founder-market fit for each opportunity:
1. Score each opportunity (1-10) on skill alignment, passion sustainability, competitive advantage
2. Provide specific recommendations for the top 2 matches
3. List skill gaps and how to address them
4. Suggest initial customer segments to target

Output format: Scoring matrix followed by detailed recommendations
</analysis_request>""",
    "mvp_spec": """<mvp_specification_request>
<solution>
Problem: {problem}
Solution: {solution}
Target Users: {target_users}
</solution>

<constraints>
Development time: 4 weeks maximum
Technical stack: {tech_stack}
</constraints>

Create comprehensive MVP specification:

1. CORE FEATURES (max 3) - User story format with acceptance criteria
2. USER JOURNEY - Onboarding flow, core workflow, success metrics
3. TECHNICAL ARCHITECTURE - System components, data model, API structure
4. DESIGN REQUIREMENTS - UI components, responsive breakpoints
5. LAUNCH CRITERIA - Quality benchmarks, performance targets

Format: Structured markdown with clear sections
</mvp_specification_request>""",
}

# ===== API MANAGER =====


class APIManager:
    """Manages all AI API interactions with retry logic and cost tracking"""

    def __init__(self, config: Config):
        self.config = config
        self.clients = {
            AIProvider.OPENAI: openai.AsyncOpenAI(api_key=config.openai_api_key),
            AIProvider.ANTHROPIC: anthropic.AsyncAnthropic(
                api_key=config.anthropic_api_key
            ),
        }
        self.total_costs = {provider: 0.0 for provider in AIProvider}

    async def call_api(
        self,
        provider: AIProvider,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000,
    ) -> Tuple[str, float]:
        """Call AI API with retry logic and cost tracking"""

        if provider == AIProvider.PERPLEXITY:
            return await self._call_perplexity(prompt)

        # Default models
        if model is None:
            model = (
                "gpt-4o"
                if provider == AIProvider.OPENAI
                else "claude-3-5-sonnet-20241022"
            )

        for attempt in range(self.config.max_retries):
            try:
                if provider == AIProvider.OPENAI:
                    response = await self.clients[provider].chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=0.7,
                    )
                    content = response.choices[0].message.content
                    cost = self._calculate_openai_cost(response.usage)

                elif provider == AIProvider.ANTHROPIC:
                    response = await self.clients[provider].messages.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                    )
                    content = response.content[0].text
                    cost = self._calculate_anthropic_cost(response.usage)

                self.total_costs[provider] += cost
                return content, cost

            except Exception as e:
                logger.warning(f"API call failed (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff

    async def _call_perplexity(self, prompt: str) -> Tuple[str, float]:
        """Call Perplexity API or use app integration"""
        # Check if user prefers app integration
        use_app = getattr(self.config, "use_perplexity_app", False)

        if use_app:
            return await self._call_perplexity_app(prompt)
        else:
            return await self._call_perplexity_api(prompt)

    async def _call_perplexity_api(self, prompt: str) -> Tuple[str, float]:
        """Call Perplexity API"""
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.perplexity_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                url,
                headers=headers,
                json={
                    "model": "llama-3.1-sonar-large-128k-online",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        cost = self.config.perplexity_cost_per_request
        self.total_costs[AIProvider.PERPLEXITY] += cost

        return content, cost

    async def _call_perplexity_app(self, prompt: str) -> Tuple[str, float]:
        """Use Perplexity app integration"""
        try:
            # Import the app integration
            import sys

            sys.path.append(str(Path(__file__).parent))
            from perplexity_app_integration import PerplexityAppManager

            manager = PerplexityAppManager()

            # Search in app
            result, cost = manager.search_in_app(prompt)
            console.print(result)

            # Get user input after they review results
            import asyncio

            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None, manager.get_user_input_after_search, prompt
            )

            self.total_costs[AIProvider.PERPLEXITY] += cost
            return content, cost

        except Exception as e:
            console.print(f"[red]App integration failed: {e}[/red]")
            console.print("[yellow]Falling back to API...[/yellow]")
            return await self._call_perplexity_api(prompt)

    def _calculate_openai_cost(self, usage) -> float:
        """Calculate OpenAI API cost"""
        input_cost = (usage.prompt_tokens / 1000) * self.config.openai_input_cost_per_1k
        output_cost = (
            usage.completion_tokens / 1000
        ) * self.config.openai_output_cost_per_1k
        return input_cost + output_cost

    def _calculate_anthropic_cost(self, usage) -> float:
        """Calculate Anthropic API cost"""
        input_cost = (
            usage.input_tokens / 1000
        ) * self.config.anthropic_input_cost_per_1k
        output_cost = (
            usage.output_tokens / 1000
        ) * self.config.anthropic_output_cost_per_1k
        return input_cost + output_cost


# ===== DOCUMENT MANAGER =====


class DocumentManager:
    """Manages markdown document storage and retrieval"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    async def save_document(self, project_id: str, doc_type: str, content: str) -> Path:
        """Save document to project folder"""
        project_dir = self.project_root / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{doc_type}_{timestamp}.md"
        filepath = project_dir / filename

        async with aiofiles.open(filepath, "w") as f:
            await f.write(content)

        logger.info(f"Saved {doc_type} to {filepath}")
        return filepath

    async def load_document(self, filepath: Path) -> str:
        """Load document from file"""
        async with aiofiles.open(filepath, "r") as f:
            return await f.read()

    async def list_documents(
        self, project_id: str, doc_type: Optional[str] = None
    ) -> List[Path]:
        """List all documents for a project"""
        project_dir = self.project_root / project_id
        if not project_dir.exists():
            return []

        pattern = f"{doc_type}_*.md" if doc_type else "*.md"
        return list(project_dir.glob(pattern))


# ===== WORKFLOW ORCHESTRATOR =====


class MVPOrchestrator:
    """Main orchestrator for MVP development workflow"""

    def __init__(self, config: Config):
        self.config = config
        self.api_manager = APIManager(config)
        self.doc_manager = DocumentManager(config.project_root)
        self.projects: Dict[str, ProjectContext] = {}

    # ===== PHASE 1: MARKET RESEARCH =====

    async def run_market_research(self, industry: str, category: str) -> Dict[str, Any]:
        """Phase 1.1: Run comprehensive market research"""
        console.print("\n[bold cyan]🔍 Phase 1.1: Market Research[/bold cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing market opportunities...", total=None)

            prompt = PROMPTS["market_research"].format(
                industry=industry, category=category
            )

            content, cost = await self.api_manager.call_api(
                AIProvider.PERPLEXITY, prompt
            )

            progress.update(task, completed=True)

        console.print(f"✅ Market research complete (Cost: ${cost:.3f})")

        return {
            "industry": industry,
            "category": category,
            "analysis": content,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }

    async def analyze_founder_fit(
        self,
        skills: List[str],
        experience: str,
        market_opportunities: str,
        network: Optional[str] = "Limited",
        resources: Optional[str] = "Bootstrapped",
    ) -> Dict[str, Any]:
        """Phase 1.2: Analyze founder-market fit"""
        console.print(
            "\n[bold cyan]🎯 Phase 1.2: Founder-Market Fit Analysis[/bold cyan]"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Evaluating founder-market fit...", total=None)

            prompt = PROMPTS["founder_fit"].format(
                skills=", ".join(skills),
                experience=experience,
                network=network,
                resources=resources,
                opportunities=market_opportunities,
            )

            content, cost = await self.api_manager.call_api(
                AIProvider.ANTHROPIC, prompt
            )

            progress.update(task, completed=True)

        console.print(f"✅ Founder analysis complete (Cost: ${cost:.3f})")

        return {
            "skills": skills,
            "experience": experience,
            "analysis": content,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }

    # ===== PHASE 2: MVP SPECIFICATION =====

    async def generate_mvp_spec(
        self,
        problem: str,
        solution: str,
        target_users: str,
        tech_stack: Optional[str] = "React, Node.js, PostgreSQL",
    ) -> Dict[str, Any]:
        """Phase 2.4: Generate comprehensive MVP specification"""
        console.print("\n[bold cyan]📋 Phase 2.4: MVP Specification[/bold cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating MVP specification...", total=None)

            prompt = PROMPTS["mvp_spec"].format(
                problem=problem,
                solution=solution,
                target_users=target_users,
                tech_stack=tech_stack,
            )

            content, cost = await self.api_manager.call_api(
                AIProvider.ANTHROPIC, prompt
            )

            progress.update(task, completed=True)

        console.print(f"✅ MVP specification complete (Cost: ${cost:.3f})")

        return {
            "problem": problem,
            "solution": solution,
            "specification": content,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }

    # ===== PHASE 3: DEVELOPMENT =====

    async def create_architecture(self, spec: str, tech_stack: str) -> Dict[str, Any]:
        """Phase 3.1: Create technical architecture"""
        console.print("\n[bold cyan]🏗️ Phase 3.1: Technical Architecture[/bold cyan]")

        architecture_prompt = f"""
        Based on this MVP specification:
        {spec}
        
        Using tech stack: {tech_stack}
        
        Design production-ready architecture including:
        1. System architecture with component diagram
        2. Database schema with relationships
        3. API design (RESTful or GraphQL)
        4. Security measures
        5. DevOps setup and deployment strategy
        
        Include specific code snippets for critical components.
        """

        content, cost = await self.api_manager.call_api(
            AIProvider.ANTHROPIC, architecture_prompt, max_tokens=4000
        )

        console.print(f"✅ Architecture design complete (Cost: ${cost:.3f})")

        return {
            "architecture": content,
            "tech_stack": tech_stack,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }

    async def generate_code(self, feature: str, context: str) -> Dict[str, Any]:
        """Phase 3.3: Generate code for specific feature"""
        console.print(f"\n[bold cyan]💻 Generating code for: {feature}[/bold cyan]")

        code_prompt = f"""
        Generate production-ready code for: {feature}
        
        Context:
        {context}
        
        Requirements:
        - Include comprehensive error handling
        - Add detailed comments and documentation
        - Include unit tests with >80% coverage
        - Follow security best practices
        - Optimize for performance
        
        Provide complete, runnable code.
        """

        content, cost = await self.api_manager.call_api(
            AIProvider.OPENAI, code_prompt, model="gpt-4o"
        )

        console.print(f"✅ Code generation complete (Cost: ${cost:.3f})")

        return {
            "feature": feature,
            "code": content,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }

    # ===== PHASE 4: QUALITY CHECKS =====

    async def run_quality_checks(
        self, code: str, test_requirements: str
    ) -> Dict[str, Any]:
        """Phase 3.4: Run quality checks on code"""
        console.print("\n[bold cyan]🧪 Running Quality Checks[/bold cyan]")

        quality_prompt = f"""
        Review this code for quality issues:
        
        {code}
        
        Test requirements: {test_requirements}
        
        Check for:
        1. Security vulnerabilities (OWASP Top 10)
        2. Performance bottlenecks
        3. Error handling completeness
        4. Code maintainability
        5. Test coverage gaps
        
        Provide specific improvements with code examples.
        """

        content, cost = await self.api_manager.call_api(
            AIProvider.ANTHROPIC, quality_prompt
        )

        console.print(f"✅ Quality checks complete (Cost: ${cost:.3f})")

        return {
            "review": content,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }

    # ===== PHASE 5: PROJECT GENERATION =====

    async def generate_complete_project(
        self, project_id: str, template_name: str = "neoforge"
    ) -> Dict[str, Any]:
        """Phase 5.1: Generate complete project using Meta-Fill integration"""
        console.print("\n[bold cyan]🏗️ Generating Complete Project[/bold cyan]")

        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        try:
            # Import meta-fill integration
            from pathlib import Path
            import sys

            sys.path.append(str(Path(__file__).parent))
            from meta_fill_integration import MVPMetaIntegration

            # Create integration instance
            meta_integration = MVPMetaIntegration()

            # Convert project data to meta-fill format
            mvp_data = {
                "project_id": project_id,
                "project_name": project.project_name,
                "industry": project.market_research.get("industry")
                if project.market_research
                else "Technology",
                "category": project.market_research.get("category")
                if project.market_research
                else "B2B SaaS",
                "market_research": project.market_research,
                "founder_analysis": project.founder_analysis,
                "mvp_spec": project.mvp_spec,
                "architecture": project.architecture,
            }

            # Generate enhanced metadata
            output_dir = self.config.project_root / project_id
            metadata = await meta_integration.generate_project_from_mvp_data(
                mvp_data, output_dir
            )

            # Create complete project
            project_path = meta_integration.create_startup_project(
                metadata=metadata, template_name=template_name, project_id=project_id
            )

            console.print(f"✅ Complete project generated at: {project_path}")

            return {
                "project_path": str(project_path),
                "metadata": metadata.__dict__,
                "template_used": template_name,
                "timestamp": datetime.now().isoformat(),
            }

        except ImportError:
            console.print(
                "[yellow]Meta-Fill integration not available. Generating basic project structure...[/yellow]"
            )
            return await self._generate_basic_project(project_id)
        except Exception as e:
            console.print(f"[red]Project generation failed: {e}[/red]")
            return await self._generate_basic_project(project_id)

    async def _generate_basic_project(self, project_id: str) -> Dict[str, Any]:
        """Fallback: Generate basic project structure without Meta-Fill"""
        project = self.projects[project_id]
        project_dir = self.config.project_root / project_id / "generated_project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create basic project files
        readme_content = f"""# {project.project_name}

Generated by MVP Orchestrator

## Project Overview
- Industry: {project.market_research.get('industry') if project.market_research else 'TBD'}
- Category: {project.market_research.get('category') if project.market_research else 'TBD'}

## Development Status
- Architecture: {'Completed' if project.architecture else 'Pending'}
- MVP Spec: {'Completed' if project.mvp_spec else 'Pending'}

## Next Steps
1. Review generated architecture
2. Set up development environment
3. Begin implementation

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        with open(project_dir / "README.md", "w") as f:
            f.write(readme_content)

        console.print(f"✅ Basic project structure created at: {project_dir}")

        return {
            "project_path": str(project_dir),
            "type": "basic",
            "timestamp": datetime.now().isoformat(),
        }

    # ===== PHASE 6: DEPLOYMENT =====

    async def prepare_deployment(
        self, platform: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 5.2: Prepare deployment configuration"""
        console.print("\n[bold cyan]🚀 Preparing Deployment[/bold cyan]")

        deployment_prompt = f"""
        Generate production deployment configuration for {platform}:
        
        Architecture: {json.dumps(config, indent=2)}
        
        Include:
        1. Infrastructure as Code (Terraform/CDK)
        2. Environment variables management
        3. Monitoring setup (APM, logging, alerts)
        4. Backup and disaster recovery
        5. Auto-scaling configuration
        6. CI/CD pipeline
        
        Provide complete configuration files.
        """

        content, cost = await self.api_manager.call_api(
            AIProvider.ANTHROPIC, deployment_prompt
        )

        console.print(f"✅ Deployment configuration ready (Cost: ${cost:.3f})")

        return {
            "platform": platform,
            "configuration": content,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }

    # ===== METRICS & TRACKING =====

    async def track_metrics(
        self, project_id: str, kpis: Dict[str, Any], timeframe: str
    ) -> None:
        """Track project metrics and generate reports"""
        project = self.projects.get(project_id)
        if not project:
            return

        # Create metrics table
        table = Table(title=f"Project Metrics: {project.project_name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        # Add KPIs
        for key, value in kpis.items():
            table.add_row(key, str(value))

        # Add costs
        table.add_row("Total API Costs", f"${sum(project.api_costs.values()):.2f}")
        for provider, cost in project.api_costs.items():
            table.add_row(f"  - {provider}", f"${cost:.2f}")

        console.print(table)

        # Save metrics to file
        metrics_path = await self.doc_manager.save_document(
            project_id, "metrics", f"# Metrics Report - {timeframe}\n\n{table}"
        )

    # ===== HUMAN GATES =====

    async def human_gate(self, gate_name: str, context: Dict[str, Any]) -> GateStatus:
        """Handle human approval gates"""
        console.print(f"\n[bold yellow]🚦 Human Gate: {gate_name}[/bold yellow]")

        # Display context
        console.print("\n[bold]Review the following:[/bold]")
        for key, value in context.items():
            if isinstance(value, str) and len(value) > 200:
                console.print(f"\n[cyan]{key}:[/cyan]\n{value[:200]}...")
            else:
                console.print(f"[cyan]{key}:[/cyan] {value}")

        # Get approval
        if Confirm.ask("\n[bold]Do you approve this gate?[/bold]"):
            return GateStatus.APPROVED

        if Confirm.ask("Does this need revision?"):
            return GateStatus.REVISION_NEEDED

        return GateStatus.REJECTED

    # ===== PROJECT MANAGEMENT =====

    async def create_project(self, name: str, industry: str, category: str) -> str:
        """Create a new project"""
        project_id = f"{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        project = ProjectContext(
            project_id=project_id,
            project_name=name,
            industry=industry,
            category=category,
        )

        self.projects[project_id] = project

        # Save project context
        project_path = self.config.project_root / project_id / "project.json"
        project_path.parent.mkdir(parents=True, exist_ok=True)

        with open(project_path, "w") as f:
            json.dump(project.dict(), f, indent=2, default=str)

        console.print(
            f"\n✅ Created project: [bold green]{name}[/bold green] (ID: {project_id})"
        )
        return project_id

    async def load_project(self, project_id: str) -> Optional[ProjectContext]:
        """Load existing project"""
        project_path = self.config.project_root / project_id / "project.json"

        if not project_path.exists():
            return None

        with open(project_path, "r") as f:
            data = json.load(f)

        project = ProjectContext(**data)
        self.projects[project_id] = project

        return project

    async def save_project(self, project_id: str) -> None:
        """Save project state"""
        project = self.projects.get(project_id)
        if not project:
            return

        project_path = self.config.project_root / project_id / "project.json"

        with open(project_path, "w") as f:
            json.dump(project.dict(), f, indent=2, default=str)

    # ===== MAIN WORKFLOW =====

    async def run_complete_workflow(
        self,
        project_name: str,
        industry: str,
        category: str,
        skills: List[str],
        experience: str,
    ) -> str:
        """Run the complete MVP development workflow"""
        console.print(
            f"\n[bold magenta]🚀 Starting MVP Development Workflow[/bold magenta]"
        )
        console.print(f"Project: {project_name}")
        console.print(f"Industry: {industry} | Category: {category}")

        # Create project
        project_id = await self.create_project(project_name, industry, category)
        project = self.projects[project_id]

        try:
            # Phase 1: Market Research
            console.print(
                "\n[bold]═══ PHASE 1: NICHE SELECTION & PROBLEM DISCOVERY ═══[/bold]"
            )

            # 1.1 Market Research
            market_research = await self.run_market_research(industry, category)
            project.market_research = market_research
            await self.doc_manager.save_document(
                project_id, "market_research", market_research["analysis"]
            )
            project.api_costs[AIProvider.PERPLEXITY] = market_research["cost"]

            # 1.2 Founder Fit Analysis
            founder_analysis = await self.analyze_founder_fit(
                skills,
                experience,
                market_research["analysis"][:1000],  # First 1000 chars
            )
            project.founder_analysis = founder_analysis
            await self.doc_manager.save_document(
                project_id, "founder_analysis", founder_analysis["analysis"]
            )
            project.api_costs[AIProvider.ANTHROPIC] = (
                project.api_costs.get(AIProvider.ANTHROPIC, 0)
                + founder_analysis["cost"]
            )

            # Human Gate 1: Niche Validation
            gate_status = await self.human_gate(
                "Niche Validation",
                {
                    "Market Opportunities": market_research["analysis"][:500],
                    "Founder Fit Score": "See founder analysis document",
                },
            )

            if gate_status != GateStatus.APPROVED:
                console.print(
                    "[bold red]❌ Niche validation not approved. Ending workflow.[/bold red]"
                )
                return project_id

            project.gates["niche_validation"] = gate_status
            await self.save_project(project_id)

            # Phase 2: Idea Development
            console.print(
                "\n[bold]═══ PHASE 2: IDEA DEVELOPMENT & VALIDATION ═══[/bold]"
            )

            # Get problem and solution from user
            problem = Prompt.ask("What specific problem are you solving?")
            solution = Prompt.ask("What's your proposed solution?")
            target_users = Prompt.ask("Who are your target users?")

            # 2.4 Generate MVP Spec
            mvp_spec = await self.generate_mvp_spec(problem, solution, target_users)
            project.mvp_spec = mvp_spec
            await self.doc_manager.save_document(
                project_id, "mvp_spec", mvp_spec["specification"]
            )
            project.api_costs[AIProvider.ANTHROPIC] = (
                project.api_costs.get(AIProvider.ANTHROPIC, 0) + mvp_spec["cost"]
            )

            # Human Gate 2: Problem-Solution Fit
            gate_status = await self.human_gate(
                "Problem-Solution Fit",
                {
                    "Problem": problem,
                    "Solution": solution,
                    "MVP Features": "See MVP specification document",
                },
            )

            if gate_status != GateStatus.APPROVED:
                console.print(
                    "[bold red]❌ Problem-Solution fit not approved. Ending workflow.[/bold red]"
                )
                return project_id

            project.gates["problem_solution_fit"] = gate_status
            await self.save_project(project_id)

            # Phase 3: Development
            console.print(
                "\n[bold]═══ PHASE 3: DEVELOPMENT & IMPLEMENTATION ═══[/bold]"
            )

            tech_stack = Prompt.ask("Tech stack?", default="React, Node.js, PostgreSQL")

            # 3.1 Create Architecture
            architecture = await self.create_architecture(
                mvp_spec["specification"], tech_stack
            )
            project.architecture = architecture
            await self.doc_manager.save_document(
                project_id, "architecture", architecture["architecture"]
            )
            project.api_costs[AIProvider.ANTHROPIC] = (
                project.api_costs.get(AIProvider.ANTHROPIC, 0) + architecture["cost"]
            )

            # Development Gate 1: Architecture Review
            gate_status = await self.human_gate(
                "Architecture Review",
                {"Tech Stack": tech_stack, "Architecture": "See architecture document"},
            )

            if gate_status == GateStatus.APPROVED:
                console.print("[bold green]✅ Ready for development![/bold green]")

                # Phase 5: Generate Complete Project
                console.print("\\n[bold]═══ PHASE 5: PROJECT GENERATION ═══[/bold]")

                if Confirm.ask("Generate complete project from template?"):
                    project_generation = await self.generate_complete_project(
                        project_id
                    )
                    console.print(
                        f"[bold green]✅ Project generated at: {project_generation['project_path']}[/bold green]"
                    )

                    # Save project generation info
                    project.code_artifacts["project_generation"] = project_generation

            project.gates["architecture_review"] = gate_status
            await self.save_project(project_id)

            # Final metrics
            await self.track_metrics(
                project_id,
                {
                    "Phases Completed": 3,
                    "Documents Generated": len(
                        await self.doc_manager.list_documents(project_id)
                    ),
                    "Human Gates Passed": len(
                        [g for g in project.gates.values() if g == GateStatus.APPROVED]
                    ),
                },
                "Initial Development",
            )

            console.print(
                f"\n[bold green]✨ Workflow complete! Project ID: {project_id}[/bold green]"
            )
            return project_id

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            project.phase_status[f"phase_{project.current_phase}"] = PhaseStatus.FAILED
            await self.save_project(project_id)
            raise


# ===== CONFIGURATION TEMPLATE =====


def create_config_template():
    """Create a configuration file template"""
    template = """# MVP Orchestrator Configuration
# Copy this to config.yaml and fill in your API keys

# API Keys (required)
openai_api_key: "sk-..."
anthropic_api_key: "sk-ant-..."
perplexity_api_key: "pplx-..."

# Project Settings
project_root: "./mvp_projects"
max_retries: 3
timeout: 30

# Perplexity Integration (macOS only)
# Set to true to use Perplexity app instead of API
use_perplexity_app: false

# Cost Tracking (update based on current pricing)
openai_input_cost_per_1k: 0.01
openai_output_cost_per_1k: 0.03
anthropic_input_cost_per_1k: 0.015
anthropic_output_cost_per_1k: 0.075
perplexity_cost_per_request: 0.005
"""

    with open("config.template.yaml", "w") as f:
        f.write(template)

    console.print(
        "✅ Created config.template.yaml - Copy to config.yaml and add your API keys"
    )


# ===== USAGE EXAMPLES =====


async def example_usage():
    """Example usage of the orchestrator"""

    # Load configuration
    with open("config.yaml", "r") as f:
        config_data = yaml.safe_load(f)

    config = Config(**config_data)
    orchestrator = MVPOrchestrator(config)

    # Example 1: Run complete workflow
    project_id = await orchestrator.run_complete_workflow(
        project_name="AI Writing Assistant",
        industry="Content Creation",
        category="B2B SaaS",
        skills=["Python", "React", "NLP", "API Development"],
        experience="5 years in software development, 2 years in AI/ML",
    )

    # Example 2: Run individual phases
    # market_data = await orchestrator.run_market_research("FinTech", "Payment Processing")
    # await orchestrator.human_gate("Market Validation", {"data": market_data})

    # Example 3: Load existing project
    # project = await orchestrator.load_project(project_id)
    # if project:
    #     console.print(f"Loaded project: {project.project_name}")


# ===== MAIN ENTRY POINT =====


async def main():
    """Main entry point"""
    console.print("[bold magenta]MVP Development Orchestrator v1.0[/bold magenta]")

    # Check for config file
    if not Path("config.yaml").exists():
        console.print("[yellow]No config.yaml found. Creating template...[/yellow]")
        create_config_template()
        console.print("Please edit config.yaml with your API keys and run again.")
        return

    # Load configuration
    try:
        with open("config.yaml", "r") as f:
            config_data = yaml.safe_load(f)
        config = Config(**config_data)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        return

    orchestrator = MVPOrchestrator(config)

    # Interactive menu
    while True:
        console.print("\n[bold]Choose an option:[/bold]")
        console.print("1. Start new MVP workflow")
        console.print("2. Load existing project")
        console.print("3. Run specific phase")
        console.print("4. View cost summary")
        console.print("5. Exit")

        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"])

        if choice == "1":
            # New workflow
            project_name = Prompt.ask("Project name")
            industry = Prompt.ask("Industry")
            category = Prompt.ask("Category")
            skills = Prompt.ask("Your skills (comma-separated)").split(",")
            experience = Prompt.ask("Your experience")

            await orchestrator.run_complete_workflow(
                project_name=project_name,
                industry=industry,
                category=category,
                skills=[s.strip() for s in skills],
                experience=experience,
            )

        elif choice == "2":
            # Load project
            projects = list((orchestrator.config.project_root).iterdir())
            if not projects:
                console.print("[yellow]No projects found[/yellow]")
                continue

            console.print("\n[bold]Available projects:[/bold]")
            for i, p in enumerate(projects):
                console.print(f"{i+1}. {p.name}")

            idx = int(Prompt.ask("Select project number")) - 1
            project = await orchestrator.load_project(projects[idx].name)

            if project:
                console.print(f"✅ Loaded: {project.project_name}")

        elif choice == "3":
            # Run specific phase
            console.print("\n[bold]Available phases:[/bold]")
            console.print("1. Market Research")
            console.print("2. Founder Fit Analysis")
            console.print("3. MVP Specification")
            console.print("4. Architecture Design")
            console.print("5. Code Generation")

            phase = Prompt.ask("Select phase", choices=["1", "2", "3", "4", "5"])

            # Implement phase-specific logic here
            console.print("[yellow]Phase execution coming soon![/yellow]")

        elif choice == "4":
            # Cost summary
            table = Table(title="API Cost Summary")
            table.add_column("Provider", style="cyan")
            table.add_column("Total Cost", style="green")

            for provider, cost in orchestrator.api_manager.total_costs.items():
                table.add_row(provider.value, f"${cost:.3f}")

            table.add_row(
                "TOTAL",
                f"${sum(orchestrator.api_manager.total_costs.values()):.3f}",
                style="bold",
            )
            console.print(table)

        elif choice == "5":
            console.print("[bold green]Goodbye! 🚀[/bold green]")
            break


if __name__ == "__main__":
    asyncio.run(main())
