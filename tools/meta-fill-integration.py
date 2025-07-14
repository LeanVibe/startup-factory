#!/usr/bin/env python3
"""
Meta-Fill Integration for MVP Orchestrator
Provides seamless integration between meta-fill tool and MVP development workflow
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console

# Import from our tools
try:
    from meta_fill import MetaFillApp, ProjectMetadata
except ImportError:
    # Handle import differently if run as script
    import sys
    sys.path.append(str(Path(__file__).parent))
    from meta_fill import MetaFillApp, ProjectMetadata

console = Console()

class MVPMetaIntegration:
    """Integration layer between Meta-Fill and MVP Orchestrator"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.meta_app = MetaFillApp(config_path)
    
    async def generate_project_from_mvp_data(
        self,
        mvp_project_data: Dict[str, Any],
        output_dir: Path
    ) -> ProjectMetadata:
        """Generate project metadata from MVP orchestrator data"""
        
        # Extract relevant data from MVP project context
        industry = mvp_project_data.get("industry", "Technology")
        category = mvp_project_data.get("category", "B2B SaaS")
        project_name = mvp_project_data.get("project_name", "Unnamed Project")
        
        # Build project idea from MVP spec if available
        mvp_spec = mvp_project_data.get("mvp_spec", {})
        if mvp_spec:
            project_idea = f"""
            Problem: {mvp_spec.get('problem', 'Problem to be defined')}
            Solution: {mvp_spec.get('solution', 'Solution to be defined')}
            Target Users: {mvp_spec.get('target_users', 'Users to be defined')}
            """
        else:
            project_idea = f"A {category} solution in the {industry} industry"
        
        # Get founder background from founder analysis
        founder_analysis = mvp_project_data.get("founder_analysis", {})
        founder_background = None
        if founder_analysis:
            founder_background = f"""
            Skills: {founder_analysis.get('skills', [])}
            Experience: {founder_analysis.get('experience', 'Experience to be defined')}
            """
        
        # Generate metadata using Meta-Fill
        metadata = await self.meta_app.generate_metadata_command(
            industry=industry,
            category=category,
            project_idea=project_idea,
            founder_background=founder_background
        )
        
        # Enhance metadata with MVP-specific data
        metadata.project_name = project_name
        metadata.project_slug = project_name.lower().replace(" ", "-").replace("_", "-")
        
        # Save enhanced metadata
        output_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = output_dir / "enhanced_metadata.json"
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata.__dict__, f, indent=2, default=str)
        
        console.print(f"✅ Enhanced metadata saved to: {metadata_file}", style="green")
        return metadata
    
    def create_startup_project(
        self,
        metadata: ProjectMetadata,
        template_name: str = "neoforge",
        project_id: str = None
    ) -> Path:
        """Create a startup project using the neoforge template"""
        
        if project_id is None:
            project_id = metadata.project_slug
        
        # Setup project path
        projects_root = Path(__file__).parent.parent / "projects"
        project_path = projects_root / project_id
        
        # Convert metadata to cookiecutter context
        context = metadata.to_cookiecutter_context()
        
        # Add startup factory specific context
        context.update({
            "project_id": project_id,
            "startup_factory_version": "1.0",
            "created_with_meta_fill": True,
            "timestamp": metadata.created_at.isoformat()
        })
        
        # Fill template
        result_path = self.meta_app.fill_template_command(
            template_name=template_name,
            project_path=str(project_path),
            context_data=context
        )
        
        # Create additional startup factory files
        self._create_startup_factory_files(result_path, metadata, project_id)
        
        return result_path
    
    def _create_startup_factory_files(
        self,
        project_path: Path,
        metadata: ProjectMetadata,
        project_id: str
    ) -> None:
        """Create additional files specific to Startup Factory workflow"""
        
        # Create .startup-factory directory
        sf_dir = project_path / ".startup-factory"
        sf_dir.mkdir(exist_ok=True)
        
        # Create project manifest
        manifest = {
            "project_id": project_id,
            "created_with": "meta-fill-integration",
            "version": "1.0",
            "metadata": metadata.__dict__,
            "workflow_status": {
                "niche_validation": "pending",
                "problem_solution_fit": "pending",
                "architecture_review": "pending",
                "development": "pending",
                "deployment": "pending"
            },
            "ai_usage": {
                "metadata_generation": True,
                "template_filling": True,
                "total_cost": 0.0
            }
        }
        
        with open(sf_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2, default=str)
        
        # Create development guide
        guide_content = f"""# {metadata.project_name} - Development Guide

## Project Overview
- **Industry**: {metadata.industry}
- **Category**: {metadata.category}
- **Target Audience**: {metadata.target_audience}
- **Business Model**: {metadata.business_model}

## Development Timeline
- **Estimated Time**: {metadata.estimated_development_time}
- **Current Phase**: MVP Development
- **Next Milestone**: Architecture Review

## Technical Stack
- **Database**: {metadata.database_type}
- **Authentication**: {'Yes' if metadata.use_auth else 'No'}
- **Payments**: {'Yes' if metadata.use_payments else 'No'}
- **AI Features**: {'Yes' if metadata.use_ai_features else 'No'}

## Quick Start
1. Review the generated architecture
2. Run `make dev` to start development environment
3. Check `docs/` for detailed documentation
4. Follow the MVP development workflow in `docs/workflow.md`

## Startup Factory Integration
This project was generated using the Startup Factory meta-fill tool.
All metadata and initial configuration has been automatically generated
based on AI analysis of your project requirements.

## Next Steps
1. **Validate Architecture**: Review generated technical architecture
2. **Customize Template**: Modify generated code to match specific requirements
3. **Setup CI/CD**: Configure deployment pipeline
4. **Begin Development**: Start implementing core features

Generated on: {metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        with open(project_path / "DEVELOPMENT_GUIDE.md", 'w') as f:
            f.write(guide_content)
        
        # Create workflow checklist
        checklist_content = f"""# {metadata.project_name} - MVP Workflow Checklist

## Phase 1: Project Setup ✅
- [x] Project metadata generated
- [x] Template filled and customized
- [x] Initial project structure created
- [ ] Architecture review completed
- [ ] Development environment setup

## Phase 2: MVP Development
- [ ] Core features identified and prioritized
- [ ] Database schema designed
- [ ] API endpoints defined
- [ ] Frontend components planned
- [ ] Authentication system implemented
- [ ] Core business logic implemented

## Phase 3: Testing & Validation
- [ ] Unit tests written (target: 80% coverage)
- [ ] Integration tests implemented
- [ ] User acceptance testing completed
- [ ] Performance optimization
- [ ] Security review completed

## Phase 4: Deployment
- [ ] Production environment setup
- [ ] CI/CD pipeline configured
- [ ] Monitoring and logging implemented
- [ ] Backup and disaster recovery setup
- [ ] Go-live checklist completed

## Key Metrics to Track
- Development velocity
- Test coverage percentage
- Bug discovery rate
- Performance benchmarks
- User feedback scores

## Human Gates Required
- [ ] Architecture Review (Gate 3)
- [ ] Security Review
- [ ] Performance Review
- [ ] Go-Live Approval

Last updated: {metadata.created_at.strftime('%Y-%m-%d')}
"""
        
        with open(sf_dir / "workflow_checklist.md", 'w') as f:
            f.write(checklist_content)
        
        console.print(f"📁 Created Startup Factory files in: {sf_dir}", style="green")

# ===== INTEGRATION EXAMPLES =====

async def example_mvp_to_project():
    """Example: Convert MVP orchestrator data to full project"""
    
    # Sample MVP project data (as would come from MVP orchestrator)
    mvp_data = {
        "project_id": "ai_writing_assistant_20250706_120000",
        "project_name": "AI Writing Assistant",
        "industry": "Content Creation",
        "category": "B2B SaaS",
        "market_research": {
            "analysis": "Market analysis shows growing demand for AI writing tools..."
        },
        "founder_analysis": {
            "skills": ["Python", "React", "NLP", "API Development"],
            "experience": "5 years in software development, 2 years in AI/ML"
        },
        "mvp_spec": {
            "problem": "Content creators struggle with writer's block and need assistance",
            "solution": "AI-powered writing assistant with templates and suggestions",
            "target_users": "Bloggers, marketers, and content creators"
        }
    }
    
    # Create integration instance
    integration = MVPMetaIntegration()
    
    # Generate enhanced metadata
    metadata = await integration.generate_project_from_mvp_data(
        mvp_data,
        Path("./output")
    )
    
    # Create full project
    project_path = integration.create_startup_project(
        metadata=metadata,
        template_name="neoforge",
        project_id="ai-writing-assistant"
    )
    
    console.print(f"🚀 Complete project created at: {project_path}", style="bold green")

if __name__ == "__main__":
    asyncio.run(example_mvp_to_project())