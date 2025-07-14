#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "anthropic>=0.45.0",
#     "openai>=1.50.0",
#     "pydantic>=2.9.0",
#     "rich>=13.9.0",
#     "aiofiles>=24.1.0",
#     "httpx>=0.28.0",
#     "pyyaml>=6.0.2",
#     "jinja2>=3.1.0",
#     "cookiecutter>=2.6.0",
# ]
# ///
"""
Meta-Fill Tool for Startup Factory
AI-powered template and metadata generation for rapid MVP development

USAGE:
    # Fill template metadata
    uv run meta-fill.py fill-template --template neoforge --project-path s-01

    # Generate project metadata
    uv run meta-fill.py generate-meta --industry "FinTech" --category "B2B SaaS"

    # Update existing project
    uv run meta-fill.py update-project --project-id s-01 --data project_data.json

FEATURES:
    - AI-powered metadata generation
    - Template variable filling
    - Project configuration management
    - Integration with MVP orchestrator
    - Cookiecutter template support
    - Custom field extraction and validation

REQUIREMENTS:
    - Python 3.10+
    - uv package manager
    - API keys configured in ../config.yaml
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import yaml
from dataclasses import dataclass, field

# Check and install dependencies automatically
try:
    import anthropic
    import openai
    from pydantic import BaseModel, Field, field_validator
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.prompt import Confirm, Prompt
    from rich.panel import Panel
    import aiofiles
    import httpx
    from jinja2 import Environment, FileSystemLoader, meta
    from cookiecutter.main import cookiecutter
    from cookiecutter.environment import StrictEnvironment
except ImportError as e:
    print(f"""
Missing dependency: {e}

This script requires uv to manage dependencies automatically.

Install uv:
  curl -LsSf https://astral.sh/uv/install.sh | sh

Then run this script with:
  uv run {__file__}
""")
    exit(1)

# Initialize rich console
console = Console()

# ===== CONFIGURATION MODELS =====

@dataclass
class ProjectMetadata:
    """Project metadata structure"""
    project_name: str
    project_slug: str
    industry: str
    category: str
    description: str
    target_audience: str
    
    # Technical metadata
    tech_stack: Dict[str, str] = field(default_factory=dict)
    database_type: str = "postgresql"
    use_auth: bool = True
    use_payments: bool = False
    use_ai_features: bool = False
    
    # Business metadata
    business_model: str = "SaaS"
    pricing_model: str = "subscription"
    target_market_size: str = ""
    competitive_advantage: str = ""
    
    # Development metadata
    development_phase: str = "mvp"
    estimated_development_time: str = "4 weeks"
    team_size: int = 1
    
    # Contact and legal
    author_name: str = ""
    author_email: str = ""
    company_name: str = ""
    license: str = "MIT"
    
    # Generated fields
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "0.1.0"
    
    def to_cookiecutter_context(self) -> Dict[str, Any]:
        """Convert to cookiecutter context variables"""
        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "project_short_description": self.description,
            "author_name": self.author_name or "Startup Founder",
            "author_email": self.author_email or f"founder@{self.project_slug}.com",
            "version": self.version,
            "use_pytest": "y",
            "use_black": "y",
            "use_mypy": "y", 
            "create_author_file": "y",
            "open_source_license": self.license,
            # Additional metadata for future template extensions
            "company_name": self.company_name,
            "database_type": self.database_type,
            "use_auth": self.use_auth,
            "use_payments": self.use_payments,
            "use_ai_features": self.use_ai_features,
            "business_model": self.business_model,
            "industry": self.industry,
            "category": self.category,
            "target_audience": self.target_audience,
        }

class AIConfig(BaseModel):
    """AI configuration for metadata generation"""
    openai_api_key: str
    anthropic_api_key: str
    use_openai_for_generation: bool = True
    use_anthropic_for_validation: bool = True
    max_tokens: int = 2000
    temperature: float = 0.7

# ===== AI METADATA GENERATOR =====

class MetadataGenerator:
    """AI-powered metadata generation"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.openai_client = openai.AsyncOpenAI(api_key=config.openai_api_key)
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
    
    async def generate_project_metadata(
        self,
        industry: str,
        category: str,
        project_idea: str,
        founder_background: Optional[str] = None
    ) -> ProjectMetadata:
        """Generate comprehensive project metadata using AI"""
        
        console.print("🤖 Generating project metadata with AI...", style="cyan")
        
        prompt = self._build_metadata_prompt(industry, category, project_idea, founder_background)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating metadata...", total=None)
            
            if self.config.use_openai_for_generation:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )
                ai_response = response.choices[0].message.content
            else:
                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.config.max_tokens
                )
                ai_response = response.content[0].text
            
            progress.update(task, completed=True)
        
        # Parse AI response into metadata structure
        metadata = self._parse_ai_response(ai_response, industry, category)
        
        # Validate with second AI if configured
        if self.config.use_anthropic_for_validation:
            metadata = await self._validate_metadata(metadata)
        
        console.print("✅ Metadata generation complete!", style="green")
        return metadata
    
    def _build_metadata_prompt(
        self,
        industry: str,
        category: str,
        project_idea: str,
        founder_background: Optional[str]
    ) -> str:
        """Build comprehensive prompt for metadata generation"""
        
        founder_context = f"\\nFounder Background: {founder_background}" if founder_background else ""
        
        return f"""Generate comprehensive project metadata for a startup MVP:

Industry: {industry}
Category: {category}
Project Idea: {project_idea}{founder_context}

Please provide the following metadata in JSON format:

{{
  "project_name": "Human-readable project name",
  "project_slug": "machine-readable-slug-name",
  "description": "Clear 1-2 sentence description",
  "target_audience": "Specific target user description",
  "tech_stack": {{
    "frontend": "recommended frontend tech",
    "backend": "recommended backend tech",
    "database": "recommended database",
    "deployment": "recommended deployment platform"
  }},
  "database_type": "postgresql|mysql|sqlite",
  "use_auth": true|false,
  "use_payments": true|false,
  "use_ai_features": true|false,
  "business_model": "SaaS|Marketplace|E-commerce|Other",
  "pricing_model": "subscription|one-time|freemium|usage-based",
  "target_market_size": "market size estimate",
  "competitive_advantage": "unique value proposition",
  "estimated_development_time": "realistic timeline",
  "author_name": "founder name if provided",
  "company_name": "suggested company name"
}}

Guidelines:
- Keep names professional and brandable
- Choose appropriate tech stack for MVP development
- Be realistic about development timeline (2-6 weeks for MVP)
- Consider technical complexity vs. time constraints
- Ensure metadata is consistent and logical
- Focus on MVP viability, not full product vision"""

    def _parse_ai_response(self, ai_response: str, industry: str, category: str) -> ProjectMetadata:
        """Parse AI response into ProjectMetadata object"""
        try:
            # Extract JSON from AI response
            start = ai_response.find('{')
            end = ai_response.rfind('}') + 1
            json_str = ai_response[start:end]
            
            data = json.loads(json_str)
            
            # Create ProjectMetadata with fallbacks
            return ProjectMetadata(
                project_name=data.get("project_name", "Unnamed Project"),
                project_slug=data.get("project_slug", "unnamed-project"),
                industry=industry,
                category=category,
                description=data.get("description", "A new startup project"),
                target_audience=data.get("target_audience", "General users"),
                tech_stack=data.get("tech_stack", {}),
                database_type=data.get("database_type", "postgresql"),
                use_auth=data.get("use_auth", True),
                use_payments=data.get("use_payments", False),
                use_ai_features=data.get("use_ai_features", False),
                business_model=data.get("business_model", "SaaS"),
                pricing_model=data.get("pricing_model", "subscription"),
                target_market_size=data.get("target_market_size", ""),
                competitive_advantage=data.get("competitive_advantage", ""),
                estimated_development_time=data.get("estimated_development_time", "4 weeks"),
                author_name=data.get("author_name", ""),
                company_name=data.get("company_name", ""),
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            console.print(f"[red]Error parsing AI response: {e}[/red]")
            console.print(f"[yellow]AI Response:[/yellow] {ai_response}")
            
            # Return basic metadata as fallback
            return ProjectMetadata(
                project_name="AI Generated Project",
                project_slug="ai-generated-project",
                industry=industry,
                category=category,
                description="An AI-generated startup project",
                target_audience="Target users to be defined",
            )
    
    async def _validate_metadata(self, metadata: ProjectMetadata) -> ProjectMetadata:
        """Validate and improve metadata using second AI"""
        console.print("🔍 Validating metadata...", style="yellow")
        
        validation_prompt = f"""Review and validate this project metadata for consistency and viability:

{json.dumps(metadata.__dict__, indent=2, default=str)}

Check for:
1. Logical consistency between fields
2. Realistic development timeline
3. Appropriate technology choices
4. Market viability
5. Clear target audience definition

Provide a refined version with the same JSON structure, improving any issues found."""

        response = await self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": validation_prompt}],
            max_tokens=2000
        )
        
        # Parse validation response and update metadata
        try:
            validated_data = json.loads(response.content[0].text)
            # Update metadata with validated values
            for key, value in validated_data.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
        except Exception as e:
            console.print(f"[yellow]Validation parsing failed: {e}[/yellow]")
        
        return metadata

# ===== TEMPLATE MANAGER =====

class TemplateManager:
    """Manages template operations and variable filling"""
    
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.env = Environment(loader=FileSystemLoader(str(templates_dir)))
    
    def get_template_variables(self, template_name: str) -> List[str]:
        """Extract variables from template"""
        template_path = self.templates_dir / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template {template_name} not found")
        
        variables = set()
        
        # Walk through template directory
        for root, dirs, files in os.walk(template_path):
            for file in files:
                if file.endswith(('.py', '.js', '.html', '.md', '.yaml', '.yml', '.json')):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Extract Jinja2 variables
                            ast = self.env.parse(content)
                            variables.update(meta.find_undeclared_variables(ast))
                    except Exception:
                        continue  # Skip files that can't be parsed
        
        return sorted(list(variables))
    
    def fill_template(
        self,
        template_name: str,
        output_path: Path,
        context: Dict[str, Any],
        no_input: bool = True
    ) -> Path:
        """Fill template with provided context"""
        
        console.print(f"📝 Filling template: {template_name}", style="cyan")
        
        template_path = self.templates_dir / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template {template_name} not found at {template_path}")
        
        # Use cookiecutter to generate project
        result_path = cookiecutter(
            str(template_path),
            extra_context=context,
            output_dir=str(output_path.parent),
            no_input=no_input,
            overwrite_if_exists=True
        )
        
        console.print(f"✅ Template filled: {result_path}", style="green")
        return Path(result_path)

# ===== PROJECT MANAGER =====

class ProjectManager:
    """Manages project operations and metadata"""
    
    def __init__(self, projects_root: Path):
        self.projects_root = projects_root
        self.projects_root.mkdir(parents=True, exist_ok=True)
    
    def create_project_structure(self, metadata: ProjectMetadata, project_id: str) -> Path:
        """Create project directory structure"""
        project_path = self.projects_root / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        metadata_file = project_path / "project_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata.__dict__, f, indent=2, default=str)
        
        console.print(f"📁 Created project structure: {project_path}", style="green")
        return project_path
    
    def load_project_metadata(self, project_id: str) -> Optional[ProjectMetadata]:
        """Load project metadata from file"""
        metadata_file = self.projects_root / project_id / "project_metadata.json"
        
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct ProjectMetadata object
        return ProjectMetadata(**data)
    
    def update_project_metadata(self, project_id: str, metadata: ProjectMetadata) -> None:
        """Update project metadata"""
        project_path = self.projects_root / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        
        metadata_file = project_path / "project_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata.__dict__, f, indent=2, default=str)
        
        console.print(f"💾 Updated metadata for project: {project_id}", style="green")

# ===== MAIN APPLICATION =====

class MetaFillApp:
    """Main application class"""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
        self.config = self._load_config(config_path)
        self.metadata_generator = MetadataGenerator(self.config)
        
        # Setup paths
        self.project_root = Path(__file__).parent.parent
        self.templates_dir = self.project_root / "templates"
        self.projects_dir = self.project_root / "projects"
        
        self.template_manager = TemplateManager(self.templates_dir)
        self.project_manager = ProjectManager(self.projects_dir)
    
    def _load_config(self, config_path: Path) -> AIConfig:
        """Load configuration from file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return AIConfig(
            openai_api_key=data.get("openai_api_key", ""),
            anthropic_api_key=data.get("anthropic_api_key", ""),
            use_openai_for_generation=data.get("use_openai_for_generation", True),
            use_anthropic_for_validation=data.get("use_anthropic_for_validation", True)
        )
    
    async def generate_metadata_command(
        self,
        industry: str,
        category: str,
        project_idea: str,
        founder_background: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> ProjectMetadata:
        """Generate project metadata command"""
        console.print(Panel.fit(
            f"🚀 Generating Metadata\n\n"
            f"Industry: {industry}\n"
            f"Category: {category}\n"
            f"Idea: {project_idea}",
            title="Meta-Fill Generator"
        ))
        
        metadata = await self.metadata_generator.generate_project_metadata(
            industry, category, project_idea, founder_background
        )
        
        # Display generated metadata
        self._display_metadata(metadata)
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(metadata.__dict__, f, indent=2, default=str)
            console.print(f"💾 Saved metadata to: {output_file}", style="green")
        
        return metadata
    
    def fill_template_command(
        self,
        template_name: str,
        project_path: str,
        metadata_file: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Fill template command"""
        console.print(Panel.fit(
            f"📝 Filling Template\n\n"
            f"Template: {template_name}\n"
            f"Output: {project_path}",
            title="Template Filler"
        ))
        
        # Load metadata or use provided context
        if metadata_file:
            with open(metadata_file, 'r') as f:
                metadata_dict = json.load(f)
            metadata = ProjectMetadata(**metadata_dict)
            context = metadata.to_cookiecutter_context()
        elif context_data:
            context = context_data
        else:
            raise ValueError("Either metadata_file or context_data must be provided")
        
        # Fill template
        output_path = Path(project_path)
        result_path = self.template_manager.fill_template(
            template_name, output_path, context
        )
        
        return result_path
    
    def update_project_command(
        self,
        project_id: str,
        data_file: str
    ) -> None:
        """Update project metadata command"""
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        metadata = ProjectMetadata(**data)
        self.project_manager.update_project_metadata(project_id, metadata)
    
    def _display_metadata(self, metadata: ProjectMetadata) -> None:
        """Display metadata in a formatted table"""
        table = Table(title="Generated Project Metadata")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        # Core fields
        table.add_row("Project Name", metadata.project_name)
        table.add_row("Project Slug", metadata.project_slug)
        table.add_row("Industry", metadata.industry)
        table.add_row("Category", metadata.category)
        table.add_row("Description", metadata.description)
        table.add_row("Target Audience", metadata.target_audience)
        
        # Technical fields
        table.add_row("Database", metadata.database_type)
        table.add_row("Use Auth", str(metadata.use_auth))
        table.add_row("Use Payments", str(metadata.use_payments))
        table.add_row("Use AI Features", str(metadata.use_ai_features))
        
        # Business fields
        table.add_row("Business Model", metadata.business_model)
        table.add_row("Pricing Model", metadata.pricing_model)
        table.add_row("Development Time", metadata.estimated_development_time)
        
        console.print(table)

# ===== CLI INTERFACE =====

async def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Meta-Fill Tool for Startup Factory")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate metadata command
    gen_parser = subparsers.add_parser("generate-meta", help="Generate project metadata")
    gen_parser.add_argument("--industry", required=True, help="Industry category")
    gen_parser.add_argument("--category", required=True, help="Business category")
    gen_parser.add_argument("--idea", required=True, help="Project idea description")
    gen_parser.add_argument("--founder-background", help="Founder background")
    gen_parser.add_argument("--output", help="Output file for metadata")
    
    # Fill template command
    fill_parser = subparsers.add_parser("fill-template", help="Fill project template")
    fill_parser.add_argument("--template", required=True, help="Template name")
    fill_parser.add_argument("--project-path", required=True, help="Output project path")
    fill_parser.add_argument("--metadata-file", help="Metadata JSON file")
    
    # Update project command
    update_parser = subparsers.add_parser("update-project", help="Update project metadata")
    update_parser.add_argument("--project-id", required=True, help="Project ID")
    update_parser.add_argument("--data", required=True, help="Data file to update from")
    
    # List templates command
    list_parser = subparsers.add_parser("list-templates", help="List available templates")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        app = MetaFillApp()
        
        if args.command == "generate-meta":
            await app.generate_metadata_command(
                industry=args.industry,
                category=args.category,
                project_idea=args.idea,
                founder_background=args.founder_background,
                output_file=args.output
            )
        
        elif args.command == "fill-template":
            app.fill_template_command(
                template_name=args.template,
                project_path=args.project_path,
                metadata_file=args.metadata_file
            )
        
        elif args.command == "update-project":
            app.update_project_command(
                project_id=args.project_id,
                data_file=args.data
            )
        
        elif args.command == "list-templates":
            templates = list(app.templates_dir.iterdir())
            console.print("📁 Available Templates:")
            for template in templates:
                if template.is_dir():
                    console.print(f"  - {template.name}")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))