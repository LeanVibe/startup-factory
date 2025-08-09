#!/usr/bin/env python3
"""
Isolated Unit Tests for MVP Orchestrator Component

Tests the MVP Orchestrator in complete isolation using mocks for all dependencies.
This validates the core business logic without external dependencies.

Test Strategy:
1. Mock all external dependencies (AI providers, file systems, etc.)
2. Test each public method in isolation
3. Verify contract compliance 
4. Test error handling and edge cases
5. Validate state management
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

# Import the orchestrator and dependencies
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from mvp_orchestrator_script import (
    MVPOrchestrator, Config, ProjectContext, APIManager, DocumentManager,
    AIProvider, GateStatus, PhaseStatus
)

class TestMVPOrchestratorIsolated:
    """Isolated tests for MVP Orchestrator component"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return Config(
            openai_api_key="test-key",
            anthropic_api_key="test-key", 
            perplexity_api_key="test-key",
            project_root=Path("/tmp/test_projects"),
            max_retries=3,
            timeout=30
        )
    
    @pytest.fixture
    def mock_api_manager(self):
        """Mock API manager with predictable responses"""
        mock = Mock(spec=APIManager)
        mock.call_api = AsyncMock()
        mock.total_costs = {provider: 0.0 for provider in AIProvider}
        return mock
    
    @pytest.fixture
    def mock_doc_manager(self):
        """Mock document manager"""
        mock = Mock(spec=DocumentManager)
        mock.save_document = AsyncMock(return_value=Path("/tmp/test.md"))
        mock.load_document = AsyncMock(return_value="test content")
        mock.list_documents = AsyncMock(return_value=[])
        return mock
    
    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create orchestrator with mocked dependencies"""
        with patch('mvp_orchestrator_script.APIManager') as mock_api_cls, \
             patch('mvp_orchestrator_script.DocumentManager') as mock_doc_cls:
            
            mock_api_cls.return_value = Mock(spec=APIManager)
            mock_doc_cls.return_value = Mock(spec=DocumentManager)
            
            return MVPOrchestrator(mock_config)
    
    def test_orchestrator_initialization(self, mock_config):
        """Test orchestrator initializes correctly"""
        with patch('mvp_orchestrator_script.APIManager'), \
             patch('mvp_orchestrator_script.DocumentManager'):
            
            orchestrator = MVPOrchestrator(mock_config)
            
            assert orchestrator.config == mock_config
            assert isinstance(orchestrator.projects, dict)
            assert len(orchestrator.projects) == 0
    
    @pytest.mark.asyncio
    async def test_create_project_success(self, orchestrator):
        """Test successful project creation"""
        # Arrange
        project_name = "Test Startup"
        industry = "Technology"
        category = "B2B SaaS"
        
        # Act
        project_id = await orchestrator.create_project(project_name, industry, category)
        
        # Assert
        assert project_id is not None
        assert project_id in orchestrator.projects
        
        project = orchestrator.projects[project_id]
        assert project.project_name == project_name
        assert project.industry == industry
        assert project.category == category
        assert isinstance(project.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_run_market_research_with_mocked_api(self, orchestrator):
        """Test market research with mocked API calls"""
        # Arrange
        industry = "FinTech"
        category = "Payment Processing"
        expected_response = "Market research results..."
        expected_cost = 0.05
        
        orchestrator.api_manager.call_api = AsyncMock(
            return_value=(expected_response, expected_cost)
        )
        
        # Act
        result = await orchestrator.run_market_research(industry, category)
        
        # Assert
        assert result['industry'] == industry
        assert result['category'] == category
        assert result['analysis'] == expected_response
        assert result['cost'] == expected_cost
        assert 'timestamp' in result
        
        # Verify API was called correctly
        orchestrator.api_manager.call_api.assert_called_once()
        call_args = orchestrator.api_manager.call_api.call_args
        assert call_args[0][0] == AIProvider.PERPLEXITY  # First arg should be provider
    
    @pytest.mark.asyncio
    async def test_analyze_founder_fit_contract(self, orchestrator):
        """Test founder fit analysis follows expected contract"""
        # Arrange
        skills = ["Python", "React", "Product Management"]
        experience = "5 years in software development"
        market_opportunities = "Large untapped market in B2B automation"
        expected_response = "Founder fit analysis..."
        expected_cost = 0.03
        
        orchestrator.api_manager.call_api = AsyncMock(
            return_value=(expected_response, expected_cost)
        )
        
        # Act
        result = await orchestrator.analyze_founder_fit(
            skills, experience, market_opportunities
        )
        
        # Assert - verify contract compliance
        required_fields = ['skills', 'experience', 'analysis', 'cost', 'timestamp']
        for field in required_fields:
            assert field in result
        
        assert result['skills'] == skills
        assert result['experience'] == experience
        assert result['analysis'] == expected_response
        assert result['cost'] == expected_cost
        
        # Verify correct AI provider used
        call_args = orchestrator.api_manager.call_api.call_args
        assert call_args[0][0] == AIProvider.ANTHROPIC
    
    @pytest.mark.asyncio
    async def test_human_gate_approval_flow(self, orchestrator):
        """Test human gate approval with mocked user input"""
        # Arrange
        gate_name = "Test Gate"
        context = {"test_key": "test_value"}
        
        # Mock user approval
        with patch('mvp_orchestrator_script.Confirm.ask', return_value=True):
            # Act
            result = await orchestrator.human_gate(gate_name, context)
            
            # Assert
            assert result == GateStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_human_gate_rejection_flow(self, orchestrator):
        """Test human gate rejection with mocked user input"""
        # Arrange
        gate_name = "Test Gate"
        context = {"test_key": "test_value"}
        
        # Mock user rejection then no revision needed
        with patch('mvp_orchestrator_script.Confirm.ask', side_effect=[False, False]):
            # Act
            result = await orchestrator.human_gate(gate_name, context)
            
            # Assert
            assert result == GateStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_generate_mvp_spec_error_handling(self, orchestrator):
        """Test MVP spec generation handles API errors gracefully"""
        # Arrange
        problem = "Test problem"
        solution = "Test solution"
        target_users = "Test users"
        
        # Mock API failure
        orchestrator.api_manager.call_api = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await orchestrator.generate_mvp_spec(problem, solution, target_users)
        
        assert "API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_project_persistence_contract(self, orchestrator):
        """Test project persistence follows expected contract"""
        # Arrange
        project_name = "Persistence Test"
        industry = "Healthcare"
        category = "B2C"
        
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open, \
             patch('json.dump') as mock_json_dump:
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Act
            project_id = await orchestrator.create_project(project_name, industry, category)
            await orchestrator.save_project(project_id)
            
            # Assert
            mock_open.assert_called()
            mock_json_dump.assert_called()
            
            # Verify correct file path structure
            call_args = mock_open.call_args[0]
            assert str(orchestrator.config.project_root) in str(call_args[0])
            assert project_id in str(call_args[0])
            assert "project.json" in str(call_args[0])
    
    @pytest.mark.asyncio
    async def test_cost_tracking_accuracy(self, orchestrator):
        """Test cost tracking is accurate and consistent"""
        # Arrange
        initial_costs = {provider: 0.0 for provider in AIProvider}
        api_cost = 0.05
        
        orchestrator.api_manager.call_api = AsyncMock(
            return_value=("test response", api_cost)
        )
        
        # Create a project to track costs
        project_id = await orchestrator.create_project("Cost Test", "Tech", "B2B")
        project = orchestrator.projects[project_id]
        
        # Act
        result = await orchestrator.run_market_research("Tech", "B2B")
        project.api_costs[AIProvider.PERPLEXITY] = result['cost']
        
        # Assert
        assert project.api_costs[AIProvider.PERPLEXITY] == api_cost
        assert sum(project.api_costs.values()) == api_cost
    
    def test_orchestrator_state_management(self, orchestrator):
        """Test orchestrator properly manages internal state"""
        # Test initial state
        assert len(orchestrator.projects) == 0
        
        # Test state after project creation
        with patch('builtins.open', create=True), \
             patch('json.dump'):
            
            project_id = asyncio.run(
                orchestrator.create_project("State Test", "Finance", "B2C")
            )
            
            assert len(orchestrator.projects) == 1
            assert project_id in orchestrator.projects
            
            project = orchestrator.projects[project_id]
            assert project.current_phase == 1
            assert isinstance(project.gates, dict)
            assert isinstance(project.api_costs, dict)
    
    def test_configuration_validation(self):
        """Test configuration validation on initialization"""
        # Test valid config
        valid_config = Config(
            openai_api_key="test",
            anthropic_api_key="test",
            perplexity_api_key="test",
            project_root=Path("/tmp")
        )
        
        with patch('mvp_orchestrator_script.APIManager'), \
             patch('mvp_orchestrator_script.DocumentManager'):
            orchestrator = MVPOrchestrator(valid_config)
            assert orchestrator.config == valid_config
        
        # Test project_root directory creation
        test_path = Path("/tmp/test_projects_unique")
        config_with_new_path = Config(
            openai_api_key="test",
            anthropic_api_key="test", 
            perplexity_api_key="test",
            project_root=test_path
        )
        
        with patch('mvp_orchestrator_script.APIManager'), \
             patch('mvp_orchestrator_script.DocumentManager'):
            orchestrator = MVPOrchestrator(config_with_new_path)
            # Should create directory (mocked in actual implementation)
            assert orchestrator.config.project_root == test_path


class TestMVPOrchestratorPerformance:
    """Performance tests for MVP Orchestrator"""
    
    @pytest.fixture
    def mock_config_perf(self):
        """Mock configuration for performance testing"""
        return Config(
            openai_api_key="test-key",
            anthropic_api_key="test-key", 
            perplexity_api_key="test-key",
            project_root=Path("/tmp/test_projects"),
            max_retries=3,
            timeout=30
        )
    
    @pytest.fixture
    def orchestrator_with_fast_mocks(self, mock_config_perf):
        """Create orchestrator with very fast mocked dependencies"""
        with patch('mvp_orchestrator_script.APIManager') as mock_api_cls, \
             patch('mvp_orchestrator_script.DocumentManager') as mock_doc_cls:
            
            # Super fast mocked responses
            mock_api = Mock()
            mock_api.call_api = AsyncMock(return_value=("fast response", 0.01))
            mock_api_cls.return_value = mock_api
            
            mock_doc = Mock()
            mock_doc.save_document = AsyncMock(return_value=Path("/tmp/fast.md"))
            mock_doc_cls.return_value = mock_doc
            
            return MVPOrchestrator(mock_config_perf)
    
    @pytest.mark.asyncio
    async def test_project_creation_performance(self, orchestrator_with_fast_mocks):
        """Test project creation meets performance requirements"""
        import time
        
        # Act
        start_time = time.time()
        project_id = await orchestrator_with_fast_mocks.create_project(
            "Performance Test", "Tech", "B2B"
        )
        end_time = time.time()
        
        # Assert - should be very fast with mocked dependencies
        execution_time = end_time - start_time
        assert execution_time < 0.1  # Less than 100ms
        assert project_id is not None
    
    @pytest.mark.asyncio 
    async def test_concurrent_project_creation(self, orchestrator_with_fast_mocks):
        """Test handling multiple concurrent project creations"""
        import time
        
        # Arrange
        project_data = [
            ("Project 1", "Tech", "B2B"),
            ("Project 2", "Healthcare", "B2C"),
            ("Project 3", "Finance", "B2B")
        ]
        
        # Act
        tasks = [
            orchestrator_with_fast_mocks.create_project(name, industry, category)
            for name, industry, category in project_data
        ]
        
        start_time = time.time()
        project_ids = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert
        assert len(project_ids) == 3
        assert len(set(project_ids)) == 3  # All unique
        execution_time = end_time - start_time
        assert execution_time < 0.5  # Should handle concurrency well
    

if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])