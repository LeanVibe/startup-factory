#!/usr/bin/env python3
"""
Code Generation Service - Core Service 2/8
Consolidates: smart_code_generator.py, business_blueprint_generator.py (code gen parts)
Handles all intelligent code generation based on business blueprints.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import anthropic
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install anthropic rich")
    exit(1)

# Import from conversation service
try:
    from .conversation_service import BusinessBlueprint, BusinessModel, IndustryVertical
except ImportError:
    # Fallback for standalone usage
    import sys
    sys.path.append(str(Path(__file__).parent))
    from conversation_service import BusinessBlueprint, BusinessModel, IndustryVertical

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class CodeArtifact:
    """Generated code artifact"""
    file_path: str
    content: str
    artifact_type: str  # 'backend', 'frontend', 'database', 'config', 'docs'
    framework: str      # 'fastapi', 'lit', 'postgresql', 'docker', etc.
    size_lines: int
    created_at: datetime


class CodeGenerationService:
    """
    Consolidated service for intelligent code generation.
    Replaces smart_code_generator.py and code generation parts of business_blueprint_generator.py
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.generated_artifacts: List[CodeArtifact] = []
        
        # Industry-specific code generation templates
        self.industry_frameworks = {
            IndustryVertical.HEALTHCARE: {
                'compliance': ['HIPAA', 'HITECH'],
                'integrations': ['HL7_FHIR', 'Epic_MyChart', 'Cerner'],
                'security': ['PHI_encryption', 'audit_logging', 'access_controls']
            },
            IndustryVertical.FINANCE: {
                'compliance': ['PCI_DSS', 'SOX', 'GDPR'],
                'integrations': ['Plaid', 'Stripe', 'banking_APIs'],
                'security': ['fraud_detection', 'transaction_monitoring', 'KYC']
            }
        }
        
        # Business model specific architectures
        self.business_model_patterns = {
            BusinessModel.B2B_SAAS: {
                'architecture': 'multi_tenant',
                'auth': 'role_based_access_control',
                'billing': 'subscription_management',
                'features': ['admin_dashboard', 'user_management', 'analytics']
            },
            BusinessModel.MARKETPLACE: {
                'architecture': 'marketplace_dual_sided',
                'auth': 'multi_role_system',
                'billing': 'commission_based',
                'features': ['payment_processing', 'rating_system', 'dispute_resolution']
            }
        }
    
    async def generate_complete_mvp(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate complete MVP codebase from business blueprint"""
        console.print("🛠️ Generating intelligent code for your business...")
        
        artifacts = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            
            # Task breakdown
            tasks = [
                ("📊 Generating database models", self._generate_database_models),
                ("🔧 Creating backend API", self._generate_backend_api),
                ("🎨 Building frontend components", self._generate_frontend_components),
                ("🔐 Adding authentication system", self._generate_auth_system),
                ("💼 Implementing business logic", self._generate_business_logic),
                ("🐳 Creating deployment configs", self._generate_deployment_config),
                ("📚 Generating documentation", self._generate_documentation)
            ]
            
            for description, generator_func in tasks:
                task = progress.add_task(description, total=1)
                generated_artifacts = await generator_func(blueprint)
                artifacts.extend(generated_artifacts)
                progress.advance(task, 1)
        
        self.generated_artifacts = artifacts
        console.print(f"✅ Generated {len(artifacts)} code artifacts")
        return artifacts
    
    async def _generate_database_models(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate SQLAlchemy database models based on business requirements"""
        
        model_generation_prompt = f"""
        Generate SQLAlchemy database models for a {blueprint.business_model} business in {blueprint.industry}.

        Business Context:
        - Name: {blueprint.business_name}
        - Description: {blueprint.description}
        - Key Features: {blueprint.key_features}
        - User Personas: {[p.get('name', 'Unknown') for p in blueprint.user_personas]}
        
        Requirements:
        1. Create models that support the key features
        2. Include proper relationships and constraints
        3. Add industry-specific compliance fields if needed
        4. Follow SQLAlchemy best practices
        5. Include proper indexing for performance
        
        Generate complete Python file with all necessary models.
        """
        
        models_code = await self._ai_code_generation(model_generation_prompt, "python")
        
        return [
            CodeArtifact(
                file_path="backend/app/models.py",
                content=models_code,
                artifact_type="backend",
                framework="sqlalchemy",
                size_lines=len(models_code.split('\n')),
                created_at=datetime.utcnow()
            )
        ]
    
    async def _generate_backend_api(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate FastAPI backend with business-specific endpoints"""
        
        api_generation_prompt = f"""
        Generate a complete FastAPI backend for a {blueprint.business_model} business.
        
        Business Requirements:
        - Features: {blueprint.key_features}
        - Industry: {blueprint.industry}
        - Compliance: {blueprint.compliance_requirements}
        - Integrations: {blueprint.integration_requirements}
        
        Generate:
        1. Main FastAPI app with proper structure
        2. API endpoints for each key feature
        3. Pydantic schemas for request/response
        4. Business logic implementation
        5. Error handling and validation
        6. Industry-specific compliance measures
        
        Create multiple files: main.py, schemas.py, routes/, dependencies.py
        """
        
        # Generate multiple backend files
        artifacts = []
        
        # Main app file
        main_code = await self._ai_code_generation(api_generation_prompt + "\n\nGenerate main.py file:", "python")
        artifacts.append(CodeArtifact(
            file_path="backend/app/main.py",
            content=main_code,
            artifact_type="backend",
            framework="fastapi",
            size_lines=len(main_code.split('\n')),
            created_at=datetime.utcnow()
        ))
        
        # Schemas file
        schemas_code = await self._ai_code_generation(api_generation_prompt + "\n\nGenerate schemas.py with Pydantic models:", "python")
        artifacts.append(CodeArtifact(
            file_path="backend/app/schemas.py", 
            content=schemas_code,
            artifact_type="backend",
            framework="pydantic",
            size_lines=len(schemas_code.split('\n')),
            created_at=datetime.utcnow()
        ))
        
        return artifacts
    
    async def _generate_frontend_components(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate Lit web components for the frontend"""
        
        frontend_prompt = f"""
        Generate modern Lit web components for a {blueprint.business_model} application.
        
        Business Context:
        - Features: {blueprint.key_features}
        - Target Users: {blueprint.target_audience}
        - Value Proposition: {blueprint.value_proposition}
        
        Generate:
        1. Main application component
        2. Components for each key feature
        3. Responsive design with modern CSS
        4. Proper state management
        5. Accessibility features
        6. TypeScript definitions
        
        Create multiple component files with proper architecture.
        """
        
        artifacts = []
        
        # Main app component
        app_component = await self._ai_code_generation(frontend_prompt + "\n\nGenerate main app component:", "typescript")
        artifacts.append(CodeArtifact(
            file_path="frontend/src/components/app-main.ts",
            content=app_component,
            artifact_type="frontend", 
            framework="lit",
            size_lines=len(app_component.split('\n')),
            created_at=datetime.utcnow()
        ))
        
        # Generate feature-specific components
        for i, feature in enumerate(blueprint.key_features[:3]):  # Limit to 3 main features
            feature_prompt = f"{frontend_prompt}\n\nGenerate component for feature: {feature}"
            feature_component = await self._ai_code_generation(feature_prompt, "typescript")
            
            component_name = feature.lower().replace(' ', '-').replace('_', '-')
            artifacts.append(CodeArtifact(
                file_path=f"frontend/src/components/{component_name}-component.ts",
                content=feature_component,
                artifact_type="frontend",
                framework="lit", 
                size_lines=len(feature_component.split('\n')),
                created_at=datetime.utcnow()
            ))
        
        return artifacts
    
    async def _generate_auth_system(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate authentication and authorization system"""
        
        auth_prompt = f"""
        Generate a complete authentication system for a {blueprint.business_model} application.
        
        Requirements:
        - JWT-based authentication
        - Role-based access control
        - User management
        - Security best practices
        - Industry compliance: {blueprint.compliance_requirements}
        
        Generate both backend (FastAPI) and frontend (Lit) auth components.
        """
        
        artifacts = []
        
        # Backend auth
        auth_backend = await self._ai_code_generation(auth_prompt + "\n\nGenerate backend auth module:", "python")
        artifacts.append(CodeArtifact(
            file_path="backend/app/auth.py",
            content=auth_backend,
            artifact_type="backend",
            framework="fastapi",
            size_lines=len(auth_backend.split('\n')),
            created_at=datetime.utcnow()
        ))
        
        # Frontend auth component
        auth_frontend = await self._ai_code_generation(auth_prompt + "\n\nGenerate frontend auth component:", "typescript")
        artifacts.append(CodeArtifact(
            file_path="frontend/src/components/auth-component.ts",
            content=auth_frontend,
            artifact_type="frontend",
            framework="lit",
            size_lines=len(auth_frontend.split('\n')),
            created_at=datetime.utcnow()
        ))
        
        return artifacts
    
    async def _generate_business_logic(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate business-specific logic and services"""
        
        # Get business model specific patterns
        patterns = self.business_model_patterns.get(blueprint.business_model, {})
        industry_features = self.industry_frameworks.get(blueprint.industry, {})
        
        business_logic_prompt = f"""
        Generate business-specific service classes for a {blueprint.business_model} in {blueprint.industry}.
        
        Business Requirements:
        - Monetization: {blueprint.monetization_strategy}
        - Key Features: {blueprint.key_features}
        - Compliance: {blueprint.compliance_requirements}
        - Architecture Pattern: {patterns.get('architecture', 'standard')}
        
        Generate:
        1. Core business service classes
        2. Payment/billing logic if applicable
        3. Industry-specific compliance logic
        4. Integration service stubs
        5. Business rule validation
        
        Create modular, testable service classes.
        """
        
        business_services = await self._ai_code_generation(business_logic_prompt, "python")
        
        return [
            CodeArtifact(
                file_path="backend/app/services/business_services.py",
                content=business_services,
                artifact_type="backend",
                framework="fastapi",
                size_lines=len(business_services.split('\n')),
                created_at=datetime.utcnow()
            )
        ]
    
    async def _generate_deployment_config(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate Docker and deployment configurations"""
        
        deployment_prompt = f"""
        Generate deployment configurations for a {blueprint.business_model} application.
        
        Requirements:
        - Docker containerization
        - docker-compose for local development
        - Environment configuration
        - Health checks and monitoring
        - Security considerations for {blueprint.industry}
        
        Generate:
        1. Dockerfile for backend
        2. Dockerfile for frontend  
        3. docker-compose.yml
        4. Environment configuration files
        5. Health check endpoints
        """
        
        artifacts = []
        
        # Backend Dockerfile
        backend_dockerfile = await self._ai_code_generation(deployment_prompt + "\n\nGenerate backend Dockerfile:", "dockerfile")
        artifacts.append(CodeArtifact(
            file_path="backend/Dockerfile",
            content=backend_dockerfile,
            artifact_type="config",
            framework="docker",
            size_lines=len(backend_dockerfile.split('\n')),
            created_at=datetime.utcnow()
        ))
        
        # Docker Compose
        docker_compose = await self._ai_code_generation(deployment_prompt + "\n\nGenerate docker-compose.yml:", "yaml")
        artifacts.append(CodeArtifact(
            file_path="docker-compose.yml",
            content=docker_compose,
            artifact_type="config", 
            framework="docker",
            size_lines=len(docker_compose.split('\n')),
            created_at=datetime.utcnow()
        ))
        
        return artifacts
    
    async def _generate_documentation(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate comprehensive documentation"""
        
        docs_prompt = f"""
        Generate comprehensive documentation for {blueprint.business_name}.
        
        Business Context:
        - Description: {blueprint.description}
        - Features: {blueprint.key_features}
        - Target Users: {blueprint.target_audience}
        - Value Proposition: {blueprint.value_proposition}
        
        Generate:
        1. README.md with project overview
        2. API documentation
        3. User guide
        4. Developer setup instructions
        5. Business overview and roadmap
        """
        
        readme_content = await self._ai_code_generation(docs_prompt + "\n\nGenerate comprehensive README.md:", "markdown")
        
        return [
            CodeArtifact(
                file_path="README.md",
                content=readme_content,
                artifact_type="docs",
                framework="markdown",
                size_lines=len(readme_content.split('\n')),
                created_at=datetime.utcnow()
            )
        ]
    
    async def _ai_code_generation(self, prompt: str, language: str) -> str:
        """Generate code using AI"""
        try:
            enhanced_prompt = f"""
            {prompt}
            
            Requirements:
            - Write production-ready, well-commented code
            - Follow best practices for {language}
            - Include proper error handling
            - Make code modular and testable
            - Add type hints where applicable
            - Include security considerations
            
            Generate only the code, no explanations.
            """
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": enhanced_prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return f"# Error generating code: {e}\n# Please implement manually"
    
    def get_generation_summary(self) -> Dict[str, Any]:
        """Get summary of generated code"""
        if not self.generated_artifacts:
            return {"error": "No artifacts generated"}
        
        summary = {
            "total_artifacts": len(self.generated_artifacts),
            "total_lines": sum(artifact.size_lines for artifact in self.generated_artifacts),
            "by_type": {},
            "by_framework": {},
            "files": []
        }
        
        for artifact in self.generated_artifacts:
            # Count by type
            summary["by_type"][artifact.artifact_type] = summary["by_type"].get(artifact.artifact_type, 0) + 1
            
            # Count by framework
            summary["by_framework"][artifact.framework] = summary["by_framework"].get(artifact.framework, 0) + 1
            
            # File list
            summary["files"].append({
                "path": artifact.file_path,
                "type": artifact.artifact_type,
                "framework": artifact.framework,
                "lines": artifact.size_lines
            })
        
        return summary
    
    async def save_artifacts_to_disk(self, base_path: str) -> bool:
        """Save all generated artifacts to disk"""
        try:
            base_dir = Path(base_path)
            base_dir.mkdir(parents=True, exist_ok=True)
            
            for artifact in self.generated_artifacts:
                file_path = base_dir / artifact.file_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w') as f:
                    f.write(artifact.content)
            
            console.print(f"✅ Saved {len(self.generated_artifacts)} files to {base_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving artifacts: {e}")
            return False


# Example usage
async def main():
    """Example usage of CodeGenerationService"""
    from conversation_service import BusinessBlueprint, BusinessModel, IndustryVertical
    
    # Mock blueprint for testing
    blueprint = BusinessBlueprint(
        business_name="HealthTech MVP",
        description="Healthcare appointment scheduling system",
        industry=IndustryVertical.HEALTHCARE,
        business_model=BusinessModel.B2B_SAAS,
        target_audience="Healthcare providers",
        key_features=["Appointment scheduling", "Patient management", "Provider dashboard"],
        value_proposition="Streamline healthcare appointments",
        competitive_advantage="HIPAA compliant by design",
        tech_stack_preferences={"backend": "fastapi", "frontend": "lit"},
        database_requirements=["Patient data", "Appointment slots", "Provider info"],
        integration_requirements=["EMR systems", "Payment processing"],
        compliance_requirements=["HIPAA", "HITECH"],
        monetization_strategy={"model": "subscription", "price_per_provider": 50},
        market_analysis={},
        user_personas=[{"name": "Healthcare Provider", "description": "Busy medical professional"}],
        created_at=datetime.utcnow(),
        conversation_id="test_123",
        confidence_score=0.9
    )
    
    # Generate code
    code_service = CodeGenerationService()
    artifacts = await code_service.generate_complete_mvp(blueprint)
    
    # Print summary
    summary = code_service.get_generation_summary()
    console.print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())