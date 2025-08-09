#!/usr/bin/env python3
"""
TemplateManager - Multi-template management with resource isolation
Manages template discovery, creation, validation, and marketplace functionality.
"""

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

# Import Track A components for integration
import sys
sys.path.append(str(Path(__file__).parent / "../../track-a-core/tools"))

from core_types import ResourceAllocation, StartupConfig

logger = logging.getLogger(__name__)


@dataclass
class TemplateInfo:
    """Information about a template"""
    name: str
    description: str
    framework: str
    category: str
    required_ports: int
    resource_requirements: dict
    supported_features: List[str]
    version: str
    created_at: datetime
    path: Path


@dataclass
class TemplateValidationResult:
    """Result of template validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    score: float  # 0.0 to 1.0


class PortManager:
    """Manages port allocation for templates"""
    
    def __init__(self, base_port: int = 3000):
        self.base_port = base_port
        self.template_port_ranges = {
            'neoforge': {'frontend': 3000, 'api': 8000, 'db': 5432},
            'reactnext': {'frontend': 3001, 'api': 8001, 'db': 5433},
            'vuenuxt': {'frontend': 3002, 'api': 8002, 'db': 5434},
            'fluttermobile': {'frontend': 3003, 'api': 8003, 'db': 5435},
            'pythonml': {'frontend': 3004, 'api': 8004, 'db': 5436}
        }
    
    def get_ports_for_template(self, template_name: str, startup_index: int = 0) -> Dict[str, int]:
        """
        Get port configuration for a template with startup-specific offsets
        
        Args:
            template_name: Name of the template
            startup_index: Index of the startup (for port offset)
            
        Returns:
            Dict[str, int]: Port mapping for the startup
        """
        if template_name not in self.template_port_ranges:
            # Default port allocation
            offset = startup_index * 10
            return {
                'frontend': self.base_port + offset,
                'api': self.base_port + offset + 1,
                'db': self.base_port + offset + 2
            }
        
        base_ports = self.template_port_ranges[template_name]
        offset = startup_index * 10
        
        return {
            service: port + offset
            for service, port in base_ports.items()
        }


class TemplateProcessor:
    """Processes templates with variable substitution"""
    
    def __init__(self):
        self.processors = {
            '.json': self._process_json,
            '.yaml': self._process_yaml,
            '.yml': self._process_yaml,
            '.env': self._process_env,
            '.py': self._process_text,
            '.js': self._process_text,
            '.ts': self._process_text,
            '.md': self._process_text,
            '.txt': self._process_text,
            '.dockerfile': self._process_text,
            'Dockerfile': self._process_text
        }
    
    async def process_template_file(self, file_path: Path, context: dict) -> str:
        """
        Process a template file with context substitution
        
        Args:
            file_path: Path to template file
            context: Context variables for substitution
            
        Returns:
            str: Processed file content
        """
        try:
            # Determine processor based on file extension
            suffix = file_path.suffix.lower()
            processor = self.processors.get(suffix, self._process_text)
            
            # Special case for Dockerfile
            if file_path.name == 'Dockerfile':
                processor = self._process_text
            
            # Read and process file
            content = file_path.read_text(encoding='utf-8')
            return await processor(content, context)
            
        except Exception as e:
            logger.error(f"Failed to process template file {file_path}: {e}")
            raise
    
    async def _process_json(self, content: str, context: dict) -> str:
        """Process JSON template with context substitution"""
        try:
            # Replace template variables in JSON
            processed_content = self._substitute_variables(content, context)
            
            # Validate JSON
            json.loads(processed_content)
            
            return processed_content
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON after template processing: {e}")
    
    async def _process_yaml(self, content: str, context: dict) -> str:
        """Process YAML template with context substitution"""
        try:
            import yaml
            processed_content = self._substitute_variables(content, context)
            
            # Validate YAML
            yaml.safe_load(processed_content)
            
            return processed_content
        except Exception as e:
            raise ValueError(f"Invalid YAML after template processing: {e}")
    
    async def _process_env(self, content: str, context: dict) -> str:
        """Process environment file template"""
        return self._substitute_variables(content, context)
    
    async def _process_text(self, content: str, context: dict) -> str:
        """Process text template with variable substitution"""
        return self._substitute_variables(content, context)
    
    def _substitute_variables(self, content: str, context: dict) -> str:
        """
        Substitute template variables in content
        
        Supports formats:
        - {{variable_name}}
        - {{cookiecutter.variable_name}}
        """
        import re
        
        # Handle cookiecutter-style variables
        def replace_cookiecutter(match):
            var_name = match.group(1)
            if var_name.startswith('cookiecutter.'):
                var_name = var_name[13:]  # Remove 'cookiecutter.' prefix (13 chars)
            return str(context.get(var_name, match.group(0)))
        
        # Replace {{cookiecutter.variable}} and {{variable}}
        content = re.sub(r'\{\{([^}]+)\}\}', replace_cookiecutter, content)
        
        return content


class TemplateValidator:
    """Validates template structure and configuration"""
    
    def __init__(self):
        self.required_files = {
            'cookiecutter.json',
            'README.md'
        }
        self.required_directories = {
            'docs'
        }
    
    async def validate_template(self, template_path: Path) -> TemplateValidationResult:
        """
        Validate template structure and configuration
        
        Args:
            template_path: Path to template directory
            
        Returns:
            TemplateValidationResult: Validation result
        """
        errors = []
        warnings = []
        score = 1.0
        
        try:
            # Check if directory exists
            if not template_path.exists() or not template_path.is_dir():
                errors.append(f"Template directory does not exist: {template_path}")
                return TemplateValidationResult(False, errors, warnings, 0.0)
            
            # Check required files
            for required_file in self.required_files:
                file_path = template_path / required_file
                if not file_path.exists():
                    errors.append(f"Missing required file: {required_file}")
                    score -= 0.3
            
            # Check cookiecutter.json structure
            cookiecutter_path = template_path / 'cookiecutter.json'
            if cookiecutter_path.exists():
                try:
                    cookiecutter_config = json.loads(cookiecutter_path.read_text())
                    
                    # Validate required fields
                    required_fields = ['project_name', 'project_slug', 'description']
                    for field in required_fields:
                        if field not in cookiecutter_config:
                            errors.append(f"Missing required field in cookiecutter.json: {field}")
                            score -= 0.1
                    
                    # Check for recommended fields
                    recommended_fields = ['template_type', 'frontend_framework', 'backend_framework']
                    for field in recommended_fields:
                        if field not in cookiecutter_config:
                            warnings.append(f"Recommended field missing in cookiecutter.json: {field}")
                            score -= 0.05
                    
                except json.JSONDecodeError as e:
                    errors.append(f"Invalid JSON in cookiecutter.json: {e}")
                    score -= 0.4
            
            # Check for template project directory
            project_dirs = [d for d in template_path.iterdir() 
                           if d.is_dir() and d.name.startswith('{{')]
            
            if not project_dirs:
                errors.append("No template project directory found (should start with {{)")
                score -= 0.3
            elif len(project_dirs) > 1:
                warnings.append("Multiple template project directories found")
                score -= 0.1
            else:
                # Validate project structure
                project_dir = project_dirs[0]
                await self._validate_project_structure(project_dir, errors, warnings)
            
            # Check documentation
            docs_dir = template_path / 'docs'
            if not docs_dir.exists():
                warnings.append("No docs directory found")
                score -= 0.05
            
            readme_path = template_path / 'README.md'
            if readme_path.exists():
                readme_content = readme_path.read_text()
                if len(readme_content) < 100:
                    warnings.append("README.md is very short")
                    score -= 0.05
            
            # Final score adjustment
            score = max(0.0, min(1.0, score))
            
            is_valid = len(errors) == 0 and score >= 0.6
            
            return TemplateValidationResult(is_valid, errors, warnings, score)
            
        except Exception as e:
            errors.append(f"Validation failed: {e}")
            return TemplateValidationResult(False, errors, warnings, 0.0)
    
    async def _validate_project_structure(self, project_dir: Path, errors: List[str], warnings: List[str]) -> None:
        """Validate the generated project structure"""
        
        # Check for common project files
        common_files = ['package.json', 'requirements.txt', 'pyproject.toml', 'Makefile']
        found_files = []
        
        for file_name in common_files:
            if (project_dir / file_name).exists():
                found_files.append(file_name)
        
        if not found_files:
            warnings.append("No common project files found (package.json, requirements.txt, etc.)")
        
        # Check for Docker support
        docker_files = ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']
        has_docker = any((project_dir / f).exists() for f in docker_files)
        
        if not has_docker:
            warnings.append("No Docker configuration found")
        
        # Check for test directories
        test_dirs = ['tests', 'test', '__tests__']
        has_tests = any((project_dir / d).exists() for d in test_dirs)
        
        if not has_tests:
            warnings.append("No test directory found")


class TemplateManager:
    """
    Multi-template management system with resource isolation
    
    Features:
    - Template discovery and validation
    - Resource-aware project generation
    - Port and namespace management
    - Template marketplace functionality
    """
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize template manager
        
        Args:
            templates_dir: Directory containing templates
        """
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, TemplateInfo] = {}
        self.port_manager = PortManager()
        self.processor = TemplateProcessor()
        self.validator = TemplateValidator()
        self.startup_counter = 0  # For unique port allocation
        
        logger.info(f"TemplateManager initialized with templates directory: {self.templates_dir}")
    
    async def initialize(self) -> None:
        """Initialize template manager and discover templates"""
        logger.info("Initializing TemplateManager...")
        
        # Create templates directory if it doesn't exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Discover templates
        await self.discover_templates()
        
        logger.info(f"TemplateManager initialized with {len(self.templates)} templates")
    
    async def discover_templates(self) -> Dict[str, TemplateInfo]:
        """
        Discover all available templates
        
        Returns:
            Dict[str, TemplateInfo]: Discovered templates
        """
        logger.info("Discovering templates...")
        
        self.templates.clear()
        
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory does not exist: {self.templates_dir}")
            return self.templates
        
        # Scan for template directories
        for template_dir in self.templates_dir.iterdir():
            if not template_dir.is_dir():
                continue
            
            try:
                template_info = await self._load_template_info(template_dir)
                if template_info:
                    self.templates[template_info.name] = template_info
                    logger.debug(f"Discovered template: {template_info.name}")
            except Exception as e:
                logger.error(f"Failed to load template from {template_dir}: {e}")
        
        logger.info(f"Discovered {len(self.templates)} templates")
        return self.templates
    
    async def _load_template_info(self, template_dir: Path) -> Optional[TemplateInfo]:
        """Load template information from directory"""
        
        cookiecutter_file = template_dir / 'cookiecutter.json'
        if not cookiecutter_file.exists():
            return None
        
        try:
            # Load cookiecutter configuration
            with open(cookiecutter_file, 'r') as f:
                config = json.load(f)
            
            # Extract template information
            name = template_dir.name
            description = config.get('description', f'{name} template')
            framework = config.get('frontend_framework', 'unknown')
            category = config.get('template_type', 'general')
            version = config.get('version', '1.0.0')
            
            # Determine resource requirements
            resource_requirements = {
                'memory_mb': config.get('memory_mb', 500),
                'cpu_cores': config.get('cpu_cores', 0.5),
                'storage_gb': config.get('storage_gb', 2),
                'port_count': len(self.port_manager.get_ports_for_template(name))
            }
            
            # Extract supported features
            supported_features = config.get('supported_features', [])
            
            return TemplateInfo(
                name=name,
                description=description,
                framework=framework,
                category=category,
                required_ports=resource_requirements['port_count'],
                resource_requirements=resource_requirements,
                supported_features=supported_features,
                version=version,
                created_at=datetime.fromtimestamp(template_dir.stat().st_ctime),
                path=template_dir
            )
            
        except Exception as e:
            logger.error(f"Failed to load template info from {template_dir}: {e}")
            return None
    
    async def get_available_templates(self) -> List[TemplateInfo]:
        """
        Get list of available templates
        
        Returns:
            List[TemplateInfo]: Available templates
        """
        return list(self.templates.values())
    
    async def get_template_info(self, template_name: str) -> Optional[TemplateInfo]:
        """
        Get information about a specific template
        
        Args:
            template_name: Name of the template
            
        Returns:
            Optional[TemplateInfo]: Template information if found
        """
        return self.templates.get(template_name)
    
    async def validate_template(self, template_name: str) -> TemplateValidationResult:
        """
        Validate a template
        
        Args:
            template_name: Name of the template to validate
            
        Returns:
            TemplateValidationResult: Validation result
        """
        template_info = self.templates.get(template_name)
        if not template_info:
            return TemplateValidationResult(
                is_valid=False,
                errors=[f"Template '{template_name}' not found"],
                warnings=[],
                score=0.0
            )
        
        return await self.validator.validate_template(template_info.path)
    
    async def create_from_template(
        self,
        template_name: str,
        startup_config: dict,
        resource_allocation: ResourceAllocation,
        output_dir: Optional[Path] = None
    ) -> str:
        """
        Create a new project from template with resource isolation
        
        Args:
            template_name: Name of template to use
            startup_config: Startup configuration
            resource_allocation: Allocated resources
            output_dir: Output directory (default: generated_projects)
            
        Returns:
            str: Path to generated project
        """
        template_info = self.templates.get(template_name)
        if not template_info:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Validate template first
        validation = await self.validate_template(template_name)
        if not validation.is_valid:
            raise ValueError(f"Template validation failed: {'; '.join(validation.errors)}")
        
        if output_dir is None:
            output_dir = Path("generated_projects")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique project name
        project_name = startup_config['name']
        safe_name = project_name.lower().replace(' ', '-').replace('_', '-')
        
        # Get ports for this template and startup
        ports = self.port_manager.get_ports_for_template(template_name, self.startup_counter)
        self.startup_counter += 1
        
        # Prepare context for template processing
        context = {
            **startup_config,
            'project_name': project_name,
            'project_slug': safe_name,
            'startup_id': resource_allocation.startup_id,
            'ports': ports,
            'database_name': resource_allocation.database_namespace,
            'memory_limit': f"{resource_allocation.memory_mb}m",
            'cpu_limit': str(resource_allocation.cpu_cores),
            'allocated_ports': resource_allocation.ports,
            'timestamp': datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        }
        
        # Add port-specific context
        for service, port in ports.items():
            context[f'{service}_port'] = port
        
        # Generate project
        project_path = await self._generate_project(template_info, context, output_dir)
        
        logger.info(f"Generated project from template '{template_name}' at {project_path}")
        
        return str(project_path)
    
    async def _generate_project(self, template_info: TemplateInfo, context: dict, output_dir: Path) -> Path:
        """Generate project from template with context substitution"""
        
        # Find template project directory
        template_dir = template_info.path
        project_dirs = [d for d in template_dir.iterdir() 
                       if d.is_dir() and d.name.startswith('{{')]
        
        if not project_dirs:
            raise ValueError(f"No template project directory found in {template_dir}")
        
        template_project_dir = project_dirs[0]
        
        # Create output project directory
        project_name = context['project_slug']
        project_path = output_dir / project_name
        
        if project_path.exists():
            # Add timestamp to make unique
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            project_path = output_dir / f"{project_name}_{timestamp}"
        
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Process all files in template
        await self._copy_and_process_directory(template_project_dir, project_path, context)
        
        # Copy template-level files (README, docs, etc.)
        template_files = ['README.md', 'LICENSE', 'CHANGELOG.md']
        for file_name in template_files:
            source_file = template_dir / file_name
            if source_file.exists():
                dest_file = project_path / file_name
                processed_content = await self.processor.process_template_file(source_file, context)
                dest_file.write_text(processed_content, encoding='utf-8')
        
        return project_path
    
    async def _copy_and_process_directory(self, source_dir: Path, dest_dir: Path, context: dict) -> None:
        """Recursively copy and process directory contents"""
        
        for item in source_dir.iterdir():
            # Process item name with context
            processed_name = self.processor._substitute_variables(item.name, context)
            dest_item = dest_dir / processed_name
            
            if item.is_dir():
                # Create directory and recurse
                dest_item.mkdir(parents=True, exist_ok=True)
                await self._copy_and_process_directory(item, dest_item, context)
            
            elif item.is_file():
                # Process file content
                try:
                    if self._should_process_file(item):
                        processed_content = await self.processor.process_template_file(item, context)
                        dest_item.write_text(processed_content, encoding='utf-8')
                    else:
                        # Copy binary file as-is
                        shutil.copy2(item, dest_item)
                except Exception as e:
                    logger.error(f"Failed to process file {item}: {e}")
                    # Fallback to direct copy
                    shutil.copy2(item, dest_item)
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Determine if file should be processed or copied as-is"""
        
        # Process text files
        text_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml',
            '.md', '.txt', '.env', '.cfg', '.ini', '.conf', '.toml',
            '.html', '.css', '.scss', '.sass', '.less', '.xml', '.svg'
        }
        
        # Special files to process
        special_files = {'Dockerfile', 'Makefile', '.gitignore', '.env.example'}
        
        return (
            file_path.suffix.lower() in text_extensions or
            file_path.name in special_files or
            file_path.name.startswith('.')
        )
    
    async def get_template_marketplace_info(self) -> dict:
        """
        Get template marketplace information
        
        Returns:
            dict: Marketplace statistics and template listings
        """
        templates = await self.get_available_templates()
        
        # Categorize templates
        categories = {}
        frameworks = {}
        
        for template in templates:
            # By category
            category = template.category
            if category not in categories:
                categories[category] = []
            categories[category].append(template.name)
            
            # By framework
            framework = template.framework
            if framework not in frameworks:
                frameworks[framework] = []
            frameworks[framework].append(template.name)
        
        # Calculate validation scores
        validation_results = {}
        for template in templates:
            result = await self.validate_template(template.name)
            validation_results[template.name] = {
                'score': result.score,
                'is_valid': result.is_valid,
                'error_count': len(result.errors),
                'warning_count': len(result.warnings)
            }
        
        return {
            'total_templates': len(templates),
            'categories': categories,
            'frameworks': frameworks,
            'validation_scores': validation_results,
            'templates': [
                {
                    'name': t.name,
                    'description': t.description,
                    'framework': t.framework,
                    'category': t.category,
                    'version': t.version,
                    'required_ports': t.required_ports,
                    'supported_features': t.supported_features,
                    'created_at': t.created_at.isoformat()
                }
                for t in templates
            ]
        }
    
    async def health_check(self) -> dict:
        """
        Perform health check on template manager
        
        Returns:
            dict: Health status
        """
        try:
            issues = []
            
            # Check if templates directory exists
            if not self.templates_dir.exists():
                issues.append(f"Templates directory does not exist: {self.templates_dir}")
            
            # Check template count
            if len(self.templates) == 0:
                issues.append("No templates discovered")
            
            # Validate all templates
            invalid_templates = []
            for template_name in self.templates:
                validation = await self.validate_template(template_name)
                if not validation.is_valid:
                    invalid_templates.append(template_name)
            
            if invalid_templates:
                issues.append(f"Invalid templates: {', '.join(invalid_templates)}")
            
            return {
                'healthy': len(issues) == 0,
                'issues': issues,
                'template_count': len(self.templates),
                'templates_directory': str(self.templates_dir),
                'startup_counter': self.startup_counter,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Convenience functions for testing
async def create_test_template_manager(templates_dir: str = "test_templates") -> TemplateManager:
    """Create template manager for testing"""
    manager = TemplateManager(templates_dir)
    await manager.initialize()
    return manager


if __name__ == "__main__":
    async def main():
        """Demo usage of TemplateManager"""
        
        import logging
        logging.basicConfig(level=logging.INFO)
        
        # Create template manager
        manager = TemplateManager()
        await manager.initialize()
        
        # Get available templates
        templates = await manager.get_available_templates()
        print(f"Available templates: {len(templates)}")
        
        for template in templates:
            print(f"  - {template.name}: {template.description}")
            
            # Validate template
            validation = await manager.validate_template(template.name)
            print(f"    Valid: {validation.is_valid}, Score: {validation.score:.2f}")
            
            if validation.errors:
                print(f"    Errors: {', '.join(validation.errors)}")
        
        # Get marketplace info
        marketplace = await manager.get_template_marketplace_info()
        print(f"\nMarketplace: {marketplace['total_templates']} templates")
        print(f"Categories: {list(marketplace['categories'].keys())}")
        print(f"Frameworks: {list(marketplace['frameworks'].keys())}")
    
    asyncio.run(main())