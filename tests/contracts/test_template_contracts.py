#!/usr/bin/env python3
"""
Template System Contract Testing Framework

Contract tests for template system component interactions.
Validates interfaces, data flow, and integration points.

Contract Testing Strategy:
1. Test interface compliance between template components
2. Validate data transformation contracts
3. Test error propagation and handling contracts
4. Verify resource management contracts
5. Test template system integration contracts
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from template_manager import (
    TemplateManager, TemplateInfo, TemplateValidator, 
    TemplateProcessor, PortManager, TemplateValidationResult
)
from core_types import ResourceAllocation, StartupConfig, Task, TaskResult


class TestTemplateManagerContracts:
    """Test contracts for TemplateManager with its dependencies"""
    
    @pytest.fixture
    def mock_template_validator(self):
        """Mock template validator following interface contract"""
        mock = Mock(spec=TemplateValidator)
        mock.validate_template = AsyncMock(
            return_value=TemplateValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                score=0.95
            )
        )
        return mock
    
    @pytest.fixture
    def mock_template_processor(self):
        """Mock template processor following interface contract"""
        mock = Mock(spec=TemplateProcessor)
        mock.process_template_file = AsyncMock(
            return_value="processed content"
        )
        mock._substitute_variables = Mock(
            return_value="processed variables"
        )
        return mock
    
    @pytest.fixture
    def mock_port_manager(self):
        """Mock port manager following interface contract"""
        mock = Mock(spec=PortManager)
        mock.get_ports_for_template = Mock(
            return_value={"frontend": 3000, "api": 8000, "db": 5432}
        )
        return mock
    
    @pytest.fixture
    def template_manager_with_mocks(self, mock_template_validator, mock_template_processor, mock_port_manager):
        """Template manager with mocked dependencies"""
        manager = TemplateManager("test_templates")
        manager.validator = mock_template_validator
        manager.processor = mock_template_processor
        manager.port_manager = mock_port_manager
        return manager
    
    @pytest.mark.asyncio
    async def test_template_discovery_contract(self):
        """Test template discovery follows expected contract"""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create valid template structure
            template_dir = temp_path / "test_template"
            template_dir.mkdir(parents=True)
            
            cookiecutter_config = {
                "project_name": "Test Template",
                "description": "A test template"
            }
            (template_dir / "cookiecutter.json").write_text(json.dumps(cookiecutter_config))
            (template_dir / "README.md").write_text("Test template")
            
            manager = TemplateManager(str(temp_path))
            
            # Act
            await manager.initialize()
            templates = await manager.get_available_templates()
            
            # Assert - Contract validation
            assert isinstance(templates, list)
            if len(templates) > 0:
                template = templates[0]
                assert isinstance(template, TemplateInfo)
                assert hasattr(template, 'name')
                assert hasattr(template, 'description')
                assert hasattr(template, 'framework')
                assert hasattr(template, 'category')
                assert hasattr(template, 'required_ports')
                assert hasattr(template, 'resource_requirements')
                assert hasattr(template, 'supported_features')
                assert hasattr(template, 'version')
                assert hasattr(template, 'created_at')
                assert hasattr(template, 'path')
                
                # Validate data types
                assert isinstance(template.name, str)
                assert isinstance(template.description, str)
                assert isinstance(template.framework, str)
                assert isinstance(template.category, str)
                assert isinstance(template.required_ports, int)
                assert isinstance(template.resource_requirements, dict)
                assert isinstance(template.supported_features, list)
                assert isinstance(template.version, str)
                assert isinstance(template.created_at, datetime)
                assert isinstance(template.path, Path)
    
    @pytest.mark.asyncio
    async def test_template_validation_contract(self, template_manager_with_mocks, mock_template_validator):
        """Test template validation contract compliance"""
        # Arrange
        template_name = "test_template"
        template_info = TemplateInfo(
            name=template_name,
            description="Test template",
            framework="test",
            category="test",
            required_ports=3,
            resource_requirements={},
            supported_features=[],
            version="1.0.0",
            created_at=datetime.now(),
            path=Path("test_path")
        )
        template_manager_with_mocks.templates = {template_name: template_info}
        
        # Act
        result = await template_manager_with_mocks.validate_template(template_name)
        
        # Assert - Contract validation
        assert isinstance(result, TemplateValidationResult)
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'score')
        
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0
        
        # Verify mock was called with correct template path
        mock_template_validator.validate_template.assert_called_once_with(template_info.path)
    
    @pytest.mark.asyncio
    async def test_port_allocation_contract(self, template_manager_with_mocks, mock_port_manager):
        """Test port allocation contract compliance"""
        # Arrange
        template_name = "test_template"
        startup_index = 2
        
        # Act
        ports = template_manager_with_mocks.port_manager.get_ports_for_template(template_name, startup_index)
        
        # Assert - Contract validation
        assert isinstance(ports, dict)
        assert len(ports) > 0
        
        for service, port in ports.items():
            assert isinstance(service, str)
            assert isinstance(port, int)
            assert 1 <= port <= 65535  # Valid port range
        
        # Verify mock was called correctly
        mock_port_manager.get_ports_for_template.assert_called_once_with(template_name, startup_index)
    
    @pytest.mark.asyncio
    async def test_template_generation_contract(self, template_manager_with_mocks):
        """Test template generation contract compliance"""
        # Arrange
        template_name = "test_template"
        template_info = TemplateInfo(
            name=template_name,
            description="Test template",
            framework="test",
            category="test", 
            required_ports=2,
            resource_requirements={},
            supported_features=[],
            version="1.0.0",
            created_at=datetime.now(),
            path=Path("test_path")
        )
        template_manager_with_mocks.templates = {template_name: template_info}
        
        startup_config = {
            "name": "Test Startup",
            "description": "A test startup"
        }
        
        from core_types import APIQuota
        resource_allocation = ResourceAllocation(
            startup_id="test_startup",
            memory_mb=512,
            cpu_cores=1.0,
            storage_gb=10,
            ports=[3000, 8000],
            database_namespace="test_db",
            api_quota=APIQuota(calls_per_hour=1000, cost_per_day=10.0),
            allocated_at=datetime.now()
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            with patch.object(template_manager_with_mocks, '_generate_project') as mock_generate:
                mock_generate.return_value = output_dir / "test_project"
                
                # Act
                result = await template_manager_with_mocks.create_from_template(
                    template_name, startup_config, resource_allocation, output_dir
                )
                
                # Assert - Contract validation
                assert isinstance(result, str)
                assert len(result) > 0
                
                # Verify generation method was called with correct parameters
                mock_generate.assert_called_once()
                call_args = mock_generate.call_args
                template_info_arg = call_args[0][0]
                context_arg = call_args[0][1]
                output_dir_arg = call_args[0][2]
                
                assert template_info_arg == template_info
                assert isinstance(context_arg, dict)
                assert "project_name" in context_arg
                assert "startup_id" in context_arg
                assert "ports" in context_arg
                assert output_dir_arg == output_dir
    
    @pytest.mark.asyncio
    async def test_error_handling_contract(self, template_manager_with_mocks, mock_template_validator):
        """Test error handling contract compliance"""
        # Arrange
        template_name = "invalid_template"
        
        # Mock validation failure
        mock_template_validator.validate_template = AsyncMock(
            return_value=TemplateValidationResult(
                is_valid=False,
                errors=["Missing cookiecutter.json", "Invalid template structure"],
                warnings=["Missing documentation"],
                score=0.2
            )
        )
        
        template_info = TemplateInfo(
            name=template_name,
            description="Invalid template",
            framework="test",
            category="test",
            required_ports=1,
            resource_requirements={},
            supported_features=[],
            version="1.0.0",
            created_at=datetime.now(),
            path=Path("invalid_path")
        )
        template_manager_with_mocks.templates = {template_name: template_info}
        
        startup_config = {"name": "Test Startup"}
        from core_types import APIQuota
        resource_allocation = ResourceAllocation(
            startup_id="test",
            memory_mb=256,
            cpu_cores=0.5,
            storage_gb=5,
            ports=[3000],
            database_namespace="test_db",
            api_quota=APIQuota(calls_per_hour=500, cost_per_day=5.0),
            allocated_at=datetime.now()
        )
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await template_manager_with_mocks.create_from_template(
                template_name, startup_config, resource_allocation
            )
        
        # Verify error message contains validation failures
        error_message = str(exc_info.value)
        assert "Template validation failed" in error_message
        assert "Missing cookiecutter.json" in error_message


class TestTemplateProcessorContracts:
    """Test contracts for TemplateProcessor"""
    
    @pytest.fixture
    def processor(self):
        """Template processor for testing"""
        return TemplateProcessor()
    
    @pytest.mark.asyncio
    async def test_file_processing_contract(self, processor):
        """Test file processing contract compliance"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write("Hello {{name}}, welcome to {{project}}!")
            temp_file_path = Path(temp_file.name)
        
        try:
            context = {"name": "World", "project": "Test Project"}
            
            # Act
            result = await processor.process_template_file(temp_file_path, context)
            
            # Assert - Contract validation
            assert isinstance(result, str)
            assert "Hello World" in result
            assert "Test Project" in result
            assert len(result) > 0
            
        finally:
            temp_file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_json_processing_contract(self, processor):
        """Test JSON processing contract compliance"""
        # Arrange
        json_content = json.dumps({
            "name": "{{project_name}}",
            "version": "{{version}}",
            "config": {
                "port": "{{port}}",
                "debug": "{{debug_mode}}"
            }
        })
        
        context = {
            "project_name": "Test Project",
            "version": "1.0.0",
            "port": "3000",
            "debug_mode": "true"
        }
        
        # Act
        result = await processor._process_json(json_content, context)
        
        # Assert - Contract validation
        assert isinstance(result, str)
        
        # Verify result is valid JSON
        parsed_result = json.loads(result)
        assert isinstance(parsed_result, dict)
        assert parsed_result["name"] == "Test Project"
        assert parsed_result["version"] == "1.0.0" 
        assert parsed_result["config"]["port"] == "3000"
        assert parsed_result["config"]["debug"] == "true"
    
    @pytest.mark.asyncio
    async def test_variable_substitution_contract(self, processor):
        """Test variable substitution contract compliance"""
        # Arrange
        content = "Project: {{project_name}}\nAuthor: {{cookiecutter.author}}\nPort: {{port}}"
        context = {
            "project_name": "My Project",
            "author": "Test Author", 
            "port": "8000"
        }
        
        # Act
        result = processor._substitute_variables(content, context)
        
        # Assert - Contract validation
        assert isinstance(result, str)
        assert "Project: My Project" in result
        assert "Author: Test Author" in result  # cookiecutter. prefix removed
        assert "Port: 8000" in result
        
        # Variables not in context should remain unchanged
        content_with_unknown = content + "\nUnknown: {{unknown_var}}"
        result_with_unknown = processor._substitute_variables(content_with_unknown, context)
        assert "{{unknown_var}}" in result_with_unknown
    
    @pytest.mark.asyncio
    async def test_invalid_json_error_contract(self, processor):
        """Test invalid JSON error handling contract"""
        # Arrange
        invalid_json = '{"name": "{{name}}", "invalid": json}'
        context = {"name": "Test"}
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await processor._process_json(invalid_json, context)
        
        assert "Invalid JSON after template processing" in str(exc_info.value)


class TestTemplateValidatorContracts:
    """Test contracts for TemplateValidator"""
    
    @pytest.fixture
    def validator(self):
        """Template validator for testing"""
        return TemplateValidator()
    
    @pytest.mark.asyncio
    async def test_validation_result_contract(self, validator):
        """Test validation result contract compliance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a minimal valid template
            (temp_path / "cookiecutter.json").write_text(json.dumps({
                "project_name": "Test",
                "project_slug": "test",
                "description": "Test template"
            }))
            (temp_path / "README.md").write_text("Test template")
            
            project_dir = temp_path / "{{cookiecutter.project_slug}}"
            project_dir.mkdir()
            (project_dir / "app.py").write_text("# Test app")
            
            # Act
            result = await validator.validate_template(temp_path)
            
            # Assert - Contract validation
            assert isinstance(result, TemplateValidationResult)
            assert hasattr(result, 'is_valid')
            assert hasattr(result, 'errors')
            assert hasattr(result, 'warnings')
            assert hasattr(result, 'score')
            
            assert isinstance(result.is_valid, bool)
            assert isinstance(result.errors, list)
            assert isinstance(result.warnings, list)
            assert isinstance(result.score, float)
            
            # Score should be between 0 and 1
            assert 0.0 <= result.score <= 1.0
            
            # Errors and warnings should contain strings
            for error in result.errors:
                assert isinstance(error, str)
            for warning in result.warnings:
                assert isinstance(warning, str)
    
    @pytest.mark.asyncio
    async def test_nonexistent_template_contract(self, validator):
        """Test handling of non-existent templates"""
        # Arrange
        nonexistent_path = Path("nonexistent_template")
        
        # Act
        result = await validator.validate_template(nonexistent_path)
        
        # Assert - Contract validation
        assert isinstance(result, TemplateValidationResult)
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert result.score == 0.0
        assert any("does not exist" in error for error in result.errors)


class TestPortManagerContracts:
    """Test contracts for PortManager"""
    
    @pytest.fixture
    def port_manager(self):
        """Port manager for testing"""
        return PortManager(base_port=3000)
    
    def test_port_allocation_contract(self, port_manager):
        """Test port allocation contract compliance"""
        # Act
        ports = port_manager.get_ports_for_template("neoforge", startup_index=0)
        
        # Assert - Contract validation
        assert isinstance(ports, dict)
        assert len(ports) > 0
        
        for service, port in ports.items():
            assert isinstance(service, str)
            assert isinstance(port, int)
            assert 1 <= port <= 65535
            assert len(service) > 0
    
    def test_port_uniqueness_contract(self, port_manager):
        """Test port uniqueness across startup instances"""
        # Act - Get ports for multiple startup instances
        ports_0 = port_manager.get_ports_for_template("neoforge", 0)
        ports_1 = port_manager.get_ports_for_template("neoforge", 1)
        ports_2 = port_manager.get_ports_for_template("neoforge", 2)
        
        # Assert - Ports should be unique across instances
        all_ports = []
        for ports in [ports_0, ports_1, ports_2]:
            all_ports.extend(ports.values())
        
        # No duplicate ports
        assert len(all_ports) == len(set(all_ports))
        
        # Ports should increase for higher startup indices
        assert ports_1["frontend"] > ports_0["frontend"]
        assert ports_2["frontend"] > ports_1["frontend"]
    
    def test_unknown_template_contract(self, port_manager):
        """Test handling of unknown templates"""
        # Act
        ports = port_manager.get_ports_for_template("unknown_template", 0)
        
        # Assert - Should provide default ports
        assert isinstance(ports, dict)
        assert len(ports) >= 3  # At minimum: frontend, api, db
        assert "frontend" in ports
        assert all(isinstance(port, int) for port in ports.values())


class TestResourceAllocationContract:
    """Test resource allocation contract compliance"""
    
    def test_resource_allocation_structure(self):
        """Test ResourceAllocation data structure contract"""
        # Arrange & Act
        from core_types import APIQuota
        allocation = ResourceAllocation(
            startup_id="test_startup",
            memory_mb=512,
            cpu_cores=1.5,
            storage_gb=10,
            ports=[3000, 8000, 5432],
            database_namespace="test_db",
            api_quota=APIQuota(calls_per_hour=2000, cost_per_day=20.0),
            allocated_at=datetime.now()
        )
        
        # Assert - Contract validation
        assert hasattr(allocation, 'startup_id')
        assert hasattr(allocation, 'memory_mb')
        assert hasattr(allocation, 'cpu_cores')
        assert hasattr(allocation, 'ports')
        assert hasattr(allocation, 'database_namespace')
        
        assert isinstance(allocation.startup_id, str)
        assert isinstance(allocation.memory_mb, int)
        assert isinstance(allocation.cpu_cores, float)
        assert isinstance(allocation.ports, list)
        assert isinstance(allocation.database_namespace, str)
        
        assert allocation.memory_mb > 0
        assert allocation.cpu_cores > 0
        assert len(allocation.ports) > 0
        assert all(isinstance(port, int) for port in allocation.ports)
        assert all(1 <= port <= 65535 for port in allocation.ports)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])