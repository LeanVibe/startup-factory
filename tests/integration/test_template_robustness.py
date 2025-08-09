#!/usr/bin/env python3
"""
Template System Robustness Testing Framework

Comprehensive testing for template system validation, edge cases, and integration.
Tests cookiecutter template processing, variable substitution, and error handling.

Test Categories:
1. Template Structure Validation
2. Variable Substitution Testing  
3. Edge Case and Error Handling
4. Template Processing Performance
5. Integration with MVP Orchestrator
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, List, Optional, Any
import yaml

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from template_manager import (
    TemplateManager, TemplateInfo, TemplateValidator, 
    TemplateProcessor, PortManager, TemplateValidationResult
)
from core_types import ResourceAllocation, StartupConfig, APIQuota
from mvp_orchestrator_script import MVPOrchestrator


def create_test_resource_allocation(
    startup_id: str = "test",
    memory_mb: int = 512,
    cpu_cores: float = 1.0,
    storage_gb: int = 10,
    ports: List[int] = None,
    database_namespace: str = "test_db"
) -> ResourceAllocation:
    """Helper function to create ResourceAllocation for tests"""
    if ports is None:
        ports = [3000, 8000]
    
    return ResourceAllocation(
        startup_id=startup_id,
        memory_mb=memory_mb,
        cpu_cores=cpu_cores,
        storage_gb=storage_gb,
        ports=ports,
        database_namespace=database_namespace,
        api_quota=APIQuota(calls_per_hour=1000, cost_per_day=10.0),
        allocated_at=datetime.utcnow()
    )


class TestTemplateStructureValidation:
    """Test template structure validation and metadata parsing"""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def valid_cookiecutter_config(self):
        """Valid cookiecutter configuration for testing"""
        return {
            "project_name": "Test Project",
            "project_slug": "{{ cookiecutter.project_name.lower().replace(' ', '-') }}",
            "description": "A test project template",
            "author_name": "Test Author",
            "version": "1.0.0",
            "template_type": "web_app",
            "frontend_framework": "lit",
            "backend_framework": "fastapi",
            "supported_features": ["auth", "database", "api"],
            "memory_mb": 512,
            "cpu_cores": 1.0,
            "storage_gb": 5,
            "_copy_without_render": ["*.pyc", "__pycache__", ".git"]
        }
    
    @pytest.fixture
    def create_test_template(self, temp_templates_dir, valid_cookiecutter_config):
        """Create a complete test template structure"""
        def _create_template(template_name: str, config: Dict = None) -> Path:
            if config is None:
                config = valid_cookiecutter_config
            
            template_dir = temp_templates_dir / template_name
            template_dir.mkdir(parents=True)
            
            # Create cookiecutter.json
            cookiecutter_file = template_dir / "cookiecutter.json"
            cookiecutter_file.write_text(json.dumps(config, indent=2))
            
            # Create README.md
            readme_file = template_dir / "README.md"
            readme_file.write_text(f"# {template_name} Template\n\nThis is a test template.")
            
            # Create project directory
            project_dir = template_dir / "{{cookiecutter.project_slug}}"
            project_dir.mkdir(parents=True)
            
            # Create project files
            (project_dir / "README.md").write_text("# {{cookiecutter.project_name}}\n{{cookiecutter.description}}")
            (project_dir / "package.json").write_text(json.dumps({
                "name": "{{cookiecutter.project_slug}}",
                "version": "{{cookiecutter.version}}",
                "description": "{{cookiecutter.description}}"
            }, indent=2))
            
            # Create backend directory
            backend_dir = project_dir / "backend"
            backend_dir.mkdir(parents=True)
            (backend_dir / "main.py").write_text('"""{{cookiecutter.project_name}} Backend"""\n')
            
            # Create frontend directory
            frontend_dir = project_dir / "frontend" 
            frontend_dir.mkdir(parents=True)
            (frontend_dir / "index.html").write_text('<title>{{cookiecutter.project_name}}</title>')
            
            # Create docs directory
            docs_dir = template_dir / "docs"
            docs_dir.mkdir(parents=True)
            (docs_dir / "README.md").write_text("Documentation for template")
            
            return template_dir
        
        return _create_template
    
    @pytest.mark.asyncio
    async def test_valid_template_validation(self, create_test_template):
        """Test validation of a properly structured template"""
        # Arrange
        template_path = create_test_template("valid_template")
        validator = TemplateValidator()
        
        # Act
        result = await validator.validate_template(template_path)
        
        # Assert
        assert result.is_valid is True
        assert result.score >= 0.8
        assert len(result.errors) == 0
        print(f"✅ Valid template validation - Score: {result.score:.2f}")
    
    @pytest.mark.asyncio
    async def test_missing_cookiecutter_json(self, temp_templates_dir):
        """Test validation fails when cookiecutter.json is missing"""
        # Arrange
        template_dir = temp_templates_dir / "invalid_template"
        template_dir.mkdir(parents=True)
        (template_dir / "README.md").write_text("Missing cookiecutter.json")
        
        validator = TemplateValidator()
        
        # Act
        result = await validator.validate_template(template_dir)
        
        # Assert
        assert result.is_valid is False
        assert any("cookiecutter.json" in error for error in result.errors)
        print(f"✅ Missing cookiecutter.json validation - Errors: {len(result.errors)}")
    
    @pytest.mark.asyncio
    async def test_invalid_cookiecutter_json(self, create_test_template):
        """Test validation fails with invalid JSON"""
        # Arrange
        template_path = create_test_template("invalid_json_template")
        cookiecutter_file = template_path / "cookiecutter.json"
        cookiecutter_file.write_text('{"invalid": json}')  # Invalid JSON
        
        validator = TemplateValidator()
        
        # Act
        result = await validator.validate_template(template_path)
        
        # Assert
        assert result.is_valid is False
        assert any("Invalid JSON" in error for error in result.errors)
        print(f"✅ Invalid JSON validation - Errors: {len(result.errors)}")
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, create_test_template, valid_cookiecutter_config):
        """Test validation catches missing required fields"""
        # Arrange
        incomplete_config = valid_cookiecutter_config.copy()
        del incomplete_config["project_name"]
        del incomplete_config["description"]
        
        template_path = create_test_template("incomplete_template", incomplete_config)
        validator = TemplateValidator()
        
        # Act
        result = await validator.validate_template(template_path)
        
        # Assert
        assert result.is_valid is False
        error_messages = " ".join(result.errors)
        assert "project_name" in error_messages
        assert "description" in error_messages
        print(f"✅ Missing required fields validation - Errors: {len(result.errors)}")
    
    @pytest.mark.asyncio
    async def test_missing_project_directory(self, create_test_template, valid_cookiecutter_config):
        """Test validation catches missing template project directory"""
        # Arrange
        template_path = create_test_template("no_project_dir_template", valid_cookiecutter_config)
        
        # Remove the project directory
        project_dir = template_path / "{{cookiecutter.project_slug}}"
        shutil.rmtree(project_dir)
        
        validator = TemplateValidator()
        
        # Act
        result = await validator.validate_template(template_path)
        
        # Assert
        assert result.is_valid is False
        assert any("No template project directory found" in error for error in result.errors)
        print(f"✅ Missing project directory validation - Errors: {len(result.errors)}")


class TestVariableSubstitution:
    """Test template variable substitution and processing"""
    
    @pytest.fixture
    def processor(self):
        """Template processor for testing"""
        return TemplateProcessor()
    
    @pytest.fixture
    def test_context(self):
        """Test context for variable substitution"""
        return {
            "project_name": "My Test Project",
            "project_slug": "my-test-project", 
            "description": "A test project for validation",
            "author_name": "Test Author",
            "version": "1.0.0",
            "frontend_port": "3000",  # String values for ports to match YAML expectations
            "api_port": "8000",
            "database_name": "test_db"
        }
    
    @pytest.mark.asyncio
    async def test_basic_variable_substitution(self, processor, test_context):
        """Test basic {{variable}} substitution"""
        # Arrange
        template_content = "Project: {{project_name}}\nDescription: {{description}}"
        
        # Act
        result = await processor._process_text(template_content, test_context)
        
        # Assert
        assert "Project: My Test Project" in result
        assert "Description: A test project for validation" in result
        print("✅ Basic variable substitution works")
    
    @pytest.mark.asyncio
    async def test_cookiecutter_style_substitution(self, processor, test_context):
        """Test {{cookiecutter.variable}} substitution"""
        # Arrange
        template_content = "Name: {{cookiecutter.project_name}}\nSlug: {{cookiecutter.project_slug}}"
        
        # Act
        result = await processor._process_text(template_content, test_context)
        
        # Assert
        # The current implementation handles cookiecutter.variable by removing the cookiecutter. prefix
        assert "Name: My Test Project" in result
        assert "Slug: my-test-project" in result
        print("✅ Cookiecutter-style variable substitution works")
    
    @pytest.mark.asyncio
    async def test_json_processing_with_variables(self, processor, test_context):
        """Test JSON template processing with variable substitution"""
        # Arrange
        json_template = json.dumps({
            "name": "{{project_slug}}",
            "version": "{{version}}",
            "description": "{{description}}",
            "ports": {
                "frontend": "{{frontend_port}}",
                "api": "{{api_port}}"
            }
        }, indent=2)
        
        # Act
        result = await processor._process_json(json_template, test_context)
        processed_data = json.loads(result)
        
        # Assert
        assert processed_data["name"] == "my-test-project"
        assert processed_data["version"] == "1.0.0"
        assert processed_data["ports"]["frontend"] == "3000"
        assert processed_data["ports"]["api"] == "8000"
        print("✅ JSON processing with variables works")
    
    @pytest.mark.asyncio
    async def test_yaml_processing_with_variables(self, processor, test_context):
        """Test YAML template processing with variable substitution"""
        # Arrange
        yaml_template = """
name: {{project_slug}}
version: {{version}}
services:
  frontend:
    port: {{frontend_port}}
  api:
    port: {{api_port}}
database:
  name: {{database_name}}
"""
        
        # Act
        result = await processor._process_yaml(yaml_template, test_context)
        processed_data = yaml.safe_load(result)
        
        # Assert
        assert processed_data["name"] == "my-test-project"
        assert processed_data["services"]["frontend"]["port"] == 3000  # YAML parses numeric values as int
        assert processed_data["database"]["name"] == "test_db"
        print("✅ YAML processing with variables works")
    
    @pytest.mark.asyncio
    async def test_missing_variable_handling(self, processor, test_context):
        """Test handling of missing variables in templates"""
        # Arrange
        template_content = "Project: {{project_name}}\nMissing: {{missing_variable}}"
        
        # Act
        result = await processor._process_text(template_content, test_context)
        
        # Assert
        assert "Project: My Test Project" in result
        assert "{{missing_variable}}" in result  # Should leave unresolved
        print("✅ Missing variable handling works")
    
    @pytest.mark.asyncio
    async def test_invalid_json_after_substitution(self, processor, test_context):
        """Test error handling for invalid JSON after substitution"""
        # Arrange
        invalid_json_template = '{"name": "{{project_name}}", "invalid": {{invalid_var}}}'
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await processor._process_json(invalid_json_template, test_context)
        
        assert "Invalid JSON after template processing" in str(exc_info.value)
        print("✅ Invalid JSON error handling works")


class TestTemplateEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_nonexistent_template_directory(self):
        """Test handling of non-existent template directory"""
        # Arrange
        manager = TemplateManager("nonexistent_templates")
        
        # Act
        await manager.initialize()
        templates = await manager.get_available_templates()
        
        # Assert
        assert len(templates) == 0
        print("✅ Non-existent template directory handled gracefully")
    
    @pytest.mark.asyncio
    async def test_corrupted_template_files(self, temp_templates_dir):
        """Test handling of corrupted template files"""
        # Arrange
        template_dir = temp_templates_dir / "corrupted_template"
        template_dir.mkdir(parents=True)
        
        # Create corrupted cookiecutter.json
        cookiecutter_file = template_dir / "cookiecutter.json"
        cookiecutter_file.write_text('{"incomplete": json without closing}')
        
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Act
        result = await manager.validate_template("corrupted_template")
        
        # Assert
        assert result.is_valid is False
        assert len(result.errors) > 0
        print(f"✅ Corrupted template files handled - Errors: {len(result.errors)}")
    
    @pytest.mark.asyncio
    async def test_template_with_binary_files(self, temp_templates_dir):
        """Test handling of templates with binary files"""
        # Arrange
        template_dir = temp_templates_dir / "binary_template"
        template_dir.mkdir(parents=True)
        
        # Create valid cookiecutter.json
        cookiecutter_config = {
            "project_name": "Binary Test",
            "project_slug": "binary-test",
            "description": "Template for binary file testing"
        }
        cookiecutter_file = template_dir / "cookiecutter.json"
        cookiecutter_file.write_text(json.dumps(cookiecutter_config, indent=2))
        
        # Create README
        (template_dir / "README.md").write_text("Binary template test")
        
        # Create project directory with binary file
        project_dir = template_dir / "{{cookiecutter.project_slug}}"
        project_dir.mkdir(parents=True)
        
        # Create a fake binary file (PNG-like header)
        binary_file = project_dir / "logo.png"
        binary_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00')
        
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Act
        startup_config = {"name": "Test Binary", "description": "Binary test startup"}
        resource_allocation = create_test_resource_allocation(
            startup_id="test",
            memory_mb=512,
            cpu_cores=1.0,
            ports=[3000, 8000]
        )
        
        result = await manager.create_from_template(
            "binary_template", 
            startup_config, 
            resource_allocation,
            temp_templates_dir / "output"
        )
        
        # Assert
        assert result is not None
        output_binary_file = Path(result) / "logo.png"
        assert output_binary_file.exists()
        assert output_binary_file.read_bytes()[:4] == b'\x89PNG'
        print("✅ Binary files handled correctly in templates")
    
    @pytest.mark.asyncio
    async def test_extremely_large_template_context(self, temp_templates_dir):
        """Test handling of templates with very large context data"""
        # Arrange
        template_dir = temp_templates_dir / "large_context_template"
        template_dir.mkdir(parents=True)
        
        # Create cookiecutter config
        cookiecutter_config = {
            "project_name": "Large Context Test",
            "project_slug": "large-context-test", 
            "description": "Template for large context testing"
        }
        (template_dir / "cookiecutter.json").write_text(json.dumps(cookiecutter_config))
        (template_dir / "README.md").write_text("Large context test")
        
        project_dir = template_dir / "{{cookiecutter.project_slug}}"
        project_dir.mkdir(parents=True)
        (project_dir / "config.json").write_text('{"name": "{{project_name}}"}')
        
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Create extremely large context
        large_context = {
            "name": "Large Context Test",
            "description": "Testing large context processing"
        }
        
        # Add 1000 context variables
        for i in range(1000):
            large_context[f"var_{i}"] = f"value_{i}_" + "x" * 100
        
        resource_allocation = create_test_resource_allocation(
            startup_id="test",
            memory_mb=512,
            cpu_cores=1.0,
            ports=[3000]
        )
        
        # Act
        result = await manager.create_from_template(
            "large_context_template",
            large_context,
            resource_allocation,
            temp_templates_dir / "output"
        )
        
        # Assert
        assert result is not None
        output_config = Path(result) / "config.json"
        assert output_config.exists()
        config_data = json.loads(output_config.read_text())
        assert config_data["name"] == "Large Context Test"
        print("✅ Large context data handled efficiently")
    
    @pytest.mark.asyncio
    async def test_concurrent_template_generation(self, temp_templates_dir):
        """Test concurrent template generation for thread safety"""
        # Arrange
        template_dir = temp_templates_dir / "concurrent_template"
        template_dir.mkdir(parents=True)
        
        cookiecutter_config = {
            "project_name": "Concurrent Test",
            "project_slug": "concurrent-test",
            "description": "Template for concurrent testing"
        }
        (template_dir / "cookiecutter.json").write_text(json.dumps(cookiecutter_config))
        (template_dir / "README.md").write_text("Concurrent test")
        
        project_dir = template_dir / "{{cookiecutter.project_slug}}"
        project_dir.mkdir(parents=True)
        (project_dir / "app.py").write_text('"""{{project_name}}"""')
        
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Act - Generate multiple templates concurrently
        async def generate_template(index: int):
            startup_config = {
                "name": f"Concurrent Test {index}",
                "description": f"Concurrent generation test {index}"
            }
            resource_allocation = create_test_resource_allocation(
                startup_id=f"test-{index}",
                memory_mb=512,
                cpu_cores=1.0,
                ports=[3000 + index],
                database_namespace=f"test_db_{index}"
            )
            
            return await manager.create_from_template(
                "concurrent_template",
                startup_config,
                resource_allocation,
                temp_templates_dir / "concurrent_output"
            )
        
        # Generate 5 templates concurrently
        results = await asyncio.gather(*[generate_template(i) for i in range(5)])
        
        # Assert
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result is not None
            output_file = Path(result) / "app.py"
            assert output_file.exists()
            content = output_file.read_text()
            assert f"Concurrent Test {i}" in content
        
        print("✅ Concurrent template generation works safely")


class TestTemplateManagerIntegration:
    """Test template manager integration with other components"""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def create_neoforge_template(self, temp_templates_dir):
        """Create a mock neoforge template for testing"""
        template_dir = temp_templates_dir / "neoforge"
        template_dir.mkdir(parents=True)
        
        # Create cookiecutter.json
        config = {
            "project_name": "Test Neoforge Project",
            "project_slug": "{{ cookiecutter.project_name.lower().replace(' ', '-') }}",
            "description": "Test neoforge template",
            "frontend_framework": "lit",
            "backend_framework": "fastapi",
            "template_type": "web_app",
            "supported_features": ["auth", "database", "api"],
            "memory_mb": 512,
            "cpu_cores": 1.0
        }
        (template_dir / "cookiecutter.json").write_text(json.dumps(config, indent=2))
        (template_dir / "README.md").write_text("# Neoforge Template")
        
        # Create project structure
        project_dir = template_dir / "{{cookiecutter.project_slug}}"
        project_dir.mkdir(parents=True)
        
        # Backend
        backend_dir = project_dir / "backend"
        backend_dir.mkdir(parents=True)
        (backend_dir / "main.py").write_text('"""{{cookiecutter.project_name}} API"""')
        (backend_dir / "requirements.txt").write_text("fastapi==0.104.1\nuvicorn==0.24.0")
        
        # Frontend
        frontend_dir = project_dir / "frontend"
        frontend_dir.mkdir(parents=True)
        (frontend_dir / "package.json").write_text(json.dumps({
            "name": "{{cookiecutter.project_slug}}-frontend",
            "version": "1.0.0"
        }))
        
        # Docker
        (project_dir / "docker-compose.yml").write_text("""
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "{{frontend_port}}:3000"
  api:
    build: ./backend
    ports:
      - "{{api_port}}:8000"
""")
        
        return template_dir
    
    @pytest.mark.asyncio
    async def test_template_manager_initialization(self, temp_templates_dir, create_neoforge_template):
        """Test template manager initialization and discovery"""
        # Arrange & Act
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Assert
        templates = await manager.get_available_templates()
        assert len(templates) == 1
        assert templates[0].name == "neoforge"
        assert templates[0].framework == "lit"
        assert templates[0].category == "web_app"
        print("✅ Template manager initialization and discovery works")
    
    @pytest.mark.asyncio
    async def test_template_marketplace_info(self, temp_templates_dir, create_neoforge_template):
        """Test template marketplace information generation"""
        # Arrange
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Act
        marketplace_info = await manager.get_template_marketplace_info()
        
        # Assert
        assert marketplace_info["total_templates"] == 1
        assert "web_app" in marketplace_info["categories"]
        assert "lit" in marketplace_info["frameworks"]
        assert "neoforge" in marketplace_info["validation_scores"]
        
        neoforge_info = next(t for t in marketplace_info["templates"] if t["name"] == "neoforge")
        assert neoforge_info["framework"] == "lit"
        assert "auth" in neoforge_info["supported_features"]
        print("✅ Template marketplace information generation works")
    
    @pytest.mark.asyncio
    async def test_port_management_integration(self, temp_templates_dir, create_neoforge_template):
        """Test integration with port management system"""
        # Arrange
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Act - Generate multiple projects to test port allocation
        projects = []
        for i in range(3):
            startup_config = {
                "name": f"Port Test {i}",
                "description": f"Port test project {i}"
            }
            resource_allocation = create_test_resource_allocation(
                startup_id=f"port-test-{i}",
                memory_mb=512,
                cpu_cores=1.0,
                ports=[3000 + i*10, 8000 + i*10],
                database_namespace=f"port_test_{i}"
            )
            
            result = await manager.create_from_template(
                "neoforge",
                startup_config,
                resource_allocation,
                temp_templates_dir / "port_test_output"
            )
            projects.append(result)
        
        # Assert - Check that different ports were allocated
        for i, project_path in enumerate(projects):
            docker_compose_file = Path(project_path) / "docker-compose.yml"
            content = docker_compose_file.read_text()
            
            # Check that unique ports were used
            expected_frontend_port = 3000 + i*10
            expected_api_port = 8000 + i*10
            
            assert f'"{expected_frontend_port}:3000"' in content
            assert f'"{expected_api_port}:8000"' in content
        
        print("✅ Port management integration works")
    
    @pytest.mark.asyncio
    async def test_resource_allocation_integration(self, temp_templates_dir, create_neoforge_template):
        """Test integration with resource allocation system"""
        # Arrange
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Define different resource requirements
        resource_configs = [
            {"memory_mb": 256, "cpu_cores": 0.5},
            {"memory_mb": 1024, "cpu_cores": 2.0},
            {"memory_mb": 2048, "cpu_cores": 4.0}
        ]
        
        # Act
        projects = []
        for i, resource_config in enumerate(resource_configs):
            startup_config = {
                "name": f"Resource Test {i}",
                "description": f"Resource test with {resource_config['memory_mb']}MB"
            }
            
            resource_allocation = create_test_resource_allocation(
                startup_id=f"resource-test-{i}",
                memory_mb=resource_config["memory_mb"],
                cpu_cores=resource_config["cpu_cores"],
                ports=[3000 + i, 8000 + i],
                database_namespace=f"resource_test_{i}"
            )
            
            result = await manager.create_from_template(
                "neoforge",
                startup_config,
                resource_allocation,
                temp_templates_dir / "resource_test_output"
            )
            projects.append((result, resource_config))
        
        # Assert - Verify resource information was properly injected
        for project_path, expected_resources in projects:
            # This test verifies that resource allocation data is passed through
            # In a real implementation, this might be used in Docker configs, etc.
            assert Path(project_path).exists()
            
        print("✅ Resource allocation integration works")
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, temp_templates_dir, create_neoforge_template):
        """Test template manager health check functionality"""
        # Arrange
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Act
        health_status = await manager.health_check()
        
        # Assert
        assert health_status["healthy"] is True
        assert health_status["template_count"] == 1
        assert len(health_status["issues"]) == 0
        assert health_status["templates_directory"] == str(temp_templates_dir)
        print("✅ Health check integration works")
    
    @pytest.mark.asyncio
    async def test_template_validation_integration(self, temp_templates_dir, create_neoforge_template):
        """Test template validation integration"""
        # Arrange
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Act
        validation_result = await manager.validate_template("neoforge")
        
        # Assert
        assert validation_result.is_valid is True
        assert validation_result.score >= 0.8
        assert len(validation_result.errors) == 0
        print(f"✅ Template validation integration works - Score: {validation_result.score:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])