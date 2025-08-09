#!/usr/bin/env python3
"""
Integration Tests for Critical User Journeys

Tests complete user workflows end-to-end using real components with controlled inputs.
This validates that the entire system works together correctly.

User Journey Testing Strategy:
1. Test with real components (minimal mocking)
2. Use controlled/predictable inputs
3. Validate complete data flow
4. Test error handling and recovery
5. Measure performance characteristics
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock, AsyncMock
import time

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from mvp_orchestrator_script import MVPOrchestrator, Config
from template_manager import TemplateManager
from ai_providers import AIProviderManager
from budget_monitor import BudgetMonitor, BudgetLimit
from core_types import TaskType, StartupConfig
from architecture.component_contracts import UserJourney, CREATE_STARTUP_JOURNEY


class TestCriticalUserJourneys:
    """Integration tests for critical user workflows"""
    
    @pytest.fixture(scope="class")
    def test_config(self):
        """Real configuration for integration testing"""
        return Config(
            openai_api_key="test-key-integration",
            anthropic_api_key="test-key-integration", 
            perplexity_api_key="test-key-integration",
            project_root=Path(tempfile.mkdtemp()) / "integration_tests",
            max_retries=2,  # Fewer retries for faster testing
            timeout=15      # Shorter timeout for testing
        )
    
    @pytest.fixture
    def mock_external_apis(self):
        """Mock external API calls while keeping internal logic real"""
        with patch('openai.resources.chat.completions.Completions.create') as mock_openai, \
             patch('anthropic.resources.messages.Messages.create') as mock_anthropic:
            
            # Configure predictable responses
            mock_openai.return_value = Mock(
                choices=[Mock(message=Mock(content="Mocked OpenAI response"))],
                usage=Mock(prompt_tokens=50, completion_tokens=100)
            )
            
            mock_anthropic.return_value = Mock(
                content=[Mock(text="Mocked Anthropic response")],
                usage=Mock(input_tokens=50, output_tokens=100)
            )
            
            yield {
                "openai": mock_openai,
                "anthropic": mock_anthropic
            }
    
    @pytest.fixture
    def orchestrator_with_mocked_apis(self, test_config, mock_external_apis):
        """Orchestrator with real components but mocked external APIs"""
        return MVPOrchestrator(test_config)
    
    @pytest.mark.asyncio
    async def test_complete_startup_creation_journey(self, orchestrator_with_mocked_apis):
        """
        Test the complete journey: Project Creation → Market Research → Founder Analysis → Project Generation
        
        This is the most critical user journey - creating a startup from idea to generated codebase.
        """
        orchestrator = orchestrator_with_mocked_apis
        
        # Journey Step 1: Initialize Project
        start_time = time.time()
        
        project_id = await orchestrator.create_project(
            project_name="Integration Test Startup",
            industry="FinTech", 
            category="Personal Finance"
        )
        
        project_creation_time = time.time() - start_time
        
        # Assertions for Step 1
        assert project_id is not None
        assert project_id in orchestrator.projects
        assert project_creation_time < 1.0  # Should be fast
        
        project = orchestrator.projects[project_id]
        assert project.project_name == "Integration Test Startup"
        assert project.industry == "FinTech"
        assert project.category == "Personal Finance"
        assert isinstance(project.created_at, datetime)
        
        # Journey Step 2: Market Research
        market_research_start = time.time()
        
        market_research = await orchestrator.run_market_research(
            project.industry,
            project.category
        )
        
        market_research_time = time.time() - market_research_start
        
        # Assertions for Step 2
        assert 'analysis' in market_research
        assert 'cost' in market_research
        assert 'timestamp' in market_research
        assert market_research['industry'] == project.industry
        assert market_research['category'] == project.category
        assert market_research_time < 30.0  # Reasonable timeout
        
        # Journey Step 3: Founder Analysis
        founder_analysis_start = time.time()
        
        founder_analysis = await orchestrator.analyze_founder_fit(
            skills=["Python", "React", "Product Management"],
            experience="5 years software development",
            market_opportunities="Growing demand for personal finance automation"
        )
        
        founder_analysis_time = time.time() - founder_analysis_start
        
        # Assertions for Step 3
        assert 'analysis' in founder_analysis
        assert 'cost' in founder_analysis
        assert 'skills' in founder_analysis
        assert 'experience' in founder_analysis
        assert founder_analysis_time < 30.0
        
        # Journey Step 4: MVP Specification
        mvp_spec_start = time.time()
        
        mvp_spec = await orchestrator.generate_mvp_spec(
            problem="People struggle to track personal finances effectively",
            solution="AI-powered personal finance tracker with automated categorization",
            target_users="Working professionals aged 25-40"
        )
        
        mvp_spec_time = time.time() - mvp_spec_start
        
        # Assertions for Step 4
        assert 'specification' in mvp_spec
        assert 'cost' in mvp_spec
        assert 'features' in mvp_spec
        assert mvp_spec_time < 30.0
        
        # Journey Step 5: Validate Project State
        total_journey_time = time.time() - start_time
        
        # Update project with results
        project.market_research = market_research
        project.founder_analysis = founder_analysis
        project.mvp_specification = mvp_spec
        
        # Final Assertions
        assert total_journey_time < 120.0  # Complete journey under 2 minutes
        assert project.api_costs[orchestrator.AIProvider.PERPLEXITY] > 0  # Market research cost
        assert project.api_costs[orchestrator.AIProvider.ANTHROPIC] > 0   # Analysis cost
        
        total_cost = sum(project.api_costs.values())
        assert total_cost > 0
        assert total_cost < 1.0  # Reasonable cost limit
        
        # Verify persistence capability
        await orchestrator.save_project(project_id)
        project_file = orchestrator.config.project_root / project_id / "project.json"
        assert project_file.exists()
    
    @pytest.mark.asyncio
    async def test_template_generation_journey(self, test_config, mock_external_apis):
        """
        Test the template generation journey: Template Selection → Configuration → Project Generation
        """
        with patch('subprocess.run') as mock_subprocess:
            # Mock successful cookiecutter execution
            mock_subprocess.return_value = Mock(returncode=0)
            
            template_manager = TemplateManager()
            
            # Journey Step 1: List Available Templates
            templates = await template_manager.list_available_templates()
            assert len(templates) > 0
            assert "neoforge" in templates
            
            # Journey Step 2: Validate Template
            is_valid = await template_manager.validate_template("neoforge")
            assert is_valid is True
            
            # Journey Step 3: Generate Project
            project_path = await template_manager.generate_project(
                template="neoforge",
                config={
                    "project_name": "Integration Test Project",
                    "project_slug": "integration-test-project",
                    "author_name": "Test Author",
                    "author_email": "test@example.com"
                }
            )
            
            assert project_path is not None
            assert "integration-test-project" in str(project_path)
    
    @pytest.mark.asyncio
    async def test_budget_enforcement_journey(self, orchestrator_with_mocked_apis):
        """
        Test budget enforcement throughout the user journey
        """
        orchestrator = orchestrator_with_mocked_apis
        
        # Set strict budget limit
        budget_monitor = BudgetMonitor()
        budget_limit = BudgetLimit(
            startup_id="budget-test",
            daily_limit=0.10,  # Very low limit
            monthly_limit=1.0,
            task_limit=0.05
        )
        await budget_monitor.set_budget_limit("budget-test", budget_limit)
        
        # Create project
        project_id = await orchestrator.create_project(
            project_name="Budget Test Startup",
            industry="Tech",
            category="B2B"
        )
        
        # Mock high cost response
        with patch.object(orchestrator.api_manager, 'call_api') as mock_call:
            mock_call.return_value = ("Expensive response", 0.20)  # Exceeds budget
            
            # This should trigger budget enforcement
            with pytest.raises(Exception):  # Should raise budget-related error
                await orchestrator.run_market_research("Tech", "B2B")
    
    @pytest.mark.asyncio
    async def test_error_recovery_journey(self, orchestrator_with_mocked_apis):
        """
        Test error handling and recovery during user journeys
        """
        orchestrator = orchestrator_with_mocked_apis
        
        # Create project successfully
        project_id = await orchestrator.create_project(
            project_name="Error Recovery Test",
            industry="Healthcare",
            category="B2B"
        )
        
        # Simulate API failure
        with patch.object(orchestrator.api_manager, 'call_api') as mock_call:
            mock_call.side_effect = Exception("Temporary API failure")
            
            # This should handle the error gracefully
            with pytest.raises(Exception) as exc_info:
                await orchestrator.run_market_research("Healthcare", "B2B")
            
            assert "Temporary API failure" in str(exc_info.value)
            
            # Project should still exist and be recoverable
            assert project_id in orchestrator.projects
            project = orchestrator.projects[project_id]
            assert project.project_name == "Error Recovery Test"
    
    @pytest.mark.asyncio
    async def test_concurrent_startup_creation(self, test_config, mock_external_apis):
        """
        Test creating multiple startups concurrently - stress test for resource management
        """
        orchestrator = MVPOrchestrator(test_config)
        
        # Create multiple projects concurrently
        startup_configs = [
            ("Startup 1", "Tech", "B2B"),
            ("Startup 2", "Healthcare", "B2C"), 
            ("Startup 3", "Finance", "B2B"),
            ("Startup 4", "Education", "B2C"),
            ("Startup 5", "Retail", "B2B")
        ]
        
        start_time = time.time()
        
        # Execute concurrent project creation
        tasks = [
            orchestrator.create_project(name, industry, category)
            for name, industry, category in startup_configs
        ]
        
        project_ids = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Assertions
        assert len(project_ids) == 5
        
        # Check for any exceptions
        successful_ids = [pid for pid in project_ids if isinstance(pid, str)]
        assert len(successful_ids) >= 4  # At least 80% success rate
        
        # Performance assertion
        assert execution_time < 10.0  # Should handle concurrency well
        
        # Verify each project is properly created
        for project_id in successful_ids:
            assert project_id in orchestrator.projects
            project = orchestrator.projects[project_id]
            assert project.project_name is not None
            assert project.industry is not None
            assert project.category is not None
    
    @pytest.mark.asyncio
    async def test_human_gate_integration_journey(self, orchestrator_with_mocked_apis):
        """
        Test human-in-the-loop gates integration throughout journey
        """
        orchestrator = orchestrator_with_mocked_apis
        
        # Mock human approvals
        with patch('mvp_orchestrator_script.Confirm.ask') as mock_confirm:
            mock_confirm.return_value = True  # Auto-approve all gates
            
            project_id = await orchestrator.create_project(
                project_name="Human Gate Test",
                industry="AI/ML",
                category="B2B"
            )
            
            # Simulate a workflow that triggers human gates
            market_research = await orchestrator.run_market_research("AI/ML", "B2B")
            
            # Test human gate explicitly
            from mvp_orchestrator_script import GateStatus
            gate_result = await orchestrator.human_gate(
                "Problem-Solution Fit Review",
                {
                    "problem": "Complex problem statement",
                    "solution": "Innovative solution",
                    "market_research": market_research
                }
            )
            
            assert gate_result == GateStatus.APPROVED
            
            # Verify the mock was called (human input was requested)
            assert mock_confirm.called
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, orchestrator_with_mocked_apis):
        """
        Test performance benchmarks for critical operations
        """
        orchestrator = orchestrator_with_mocked_apis
        
        # Benchmark project creation
        creation_times = []
        for i in range(5):
            start = time.time()
            project_id = await orchestrator.create_project(
                f"Benchmark Project {i}",
                "Tech",
                "B2B"
            )
            end = time.time()
            creation_times.append(end - start)
            assert project_id in orchestrator.projects
        
        # Performance assertions
        avg_creation_time = sum(creation_times) / len(creation_times)
        assert avg_creation_time < 0.5  # Average under 500ms
        assert max(creation_times) < 1.0  # No single creation over 1 second
        
        # Benchmark API operations
        api_times = []
        for i in range(3):
            start = time.time()
            result = await orchestrator.run_market_research("Tech", "B2B")
            end = time.time()
            api_times.append(end - start)
            assert 'analysis' in result
        
        avg_api_time = sum(api_times) / len(api_times)
        assert avg_api_time < 15.0  # Average API call under 15 seconds with mocks


class TestEndToEndSystemValidation:
    """End-to-end system validation tests"""
    
    @pytest.mark.asyncio
    async def test_complete_system_health(self, test_config, mock_external_apis):
        """Test complete system health - all major components working together"""
        
        # Initialize all major components
        orchestrator = MVPOrchestrator(test_config)
        
        # Test system initialization
        assert orchestrator.config == test_config
        assert hasattr(orchestrator, 'api_manager')
        assert hasattr(orchestrator, 'doc_manager')
        assert isinstance(orchestrator.projects, dict)
        
        # Test basic system functions
        project_id = await orchestrator.create_project(
            "System Health Test",
            "HealthTech", 
            "B2C"
        )
        
        assert project_id is not None
        
        # Test API integration
        result = await orchestrator.run_market_research("HealthTech", "B2C")
        assert 'analysis' in result
        assert 'cost' in result
        
        # Test persistence
        await orchestrator.save_project(project_id)
        
        # Test project loading (if implemented)
        # loaded_projects = await orchestrator.load_projects()
        # assert project_id in loaded_projects
        
        print(f"✅ System health check passed - Project {project_id} created successfully")
    
    def test_system_configuration_validation(self, test_config):
        """Test system configuration is valid and complete"""
        
        # Test required configuration fields
        assert test_config.openai_api_key is not None
        assert test_config.anthropic_api_key is not None
        assert test_config.perplexity_api_key is not None
        assert test_config.project_root is not None
        
        # Test configuration values are reasonable
        assert test_config.max_retries >= 1
        assert test_config.timeout > 0
        assert isinstance(test_config.project_root, Path)
        
        print("✅ System configuration validation passed")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])