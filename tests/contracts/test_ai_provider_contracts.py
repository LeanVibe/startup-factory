#!/usr/bin/env python3
"""
Contract Tests for AI Provider Component Interactions

Tests the contracts between AI Provider Manager and its dependencies.
This ensures components interact correctly at their boundaries.

Contract Testing Strategy:
1. Test interface compliance between components
2. Validate data transformation and flow
3. Test error propagation and handling
4. Verify retry and fallback mechanisms
5. Test resource management contracts
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime
from typing import Dict, List, Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from ai_providers import (
    AIProviderManager, OpenAIProvider, AnthropicProvider, 
    ProviderConfig, ProviderCall, AIProviderInterface
)
from budget_monitor import BudgetMonitor, BudgetLimit, SpendingRecord
from health_monitor import ProviderHealthMonitor, HealthStatus
from core_types import Task, TaskResult, TaskType, ProviderError


class TestAIProviderManagerContracts:
    """Test contracts between AI Provider Manager and its dependencies"""
    
    @pytest.fixture
    def mock_openai_provider(self):
        """Mock OpenAI provider that follows interface contract"""
        mock = Mock(spec=OpenAIProvider)
        mock.process_task = AsyncMock(
            return_value=TaskResult(
                task_id="test-task-1",
                success=True,
                output="Test response",
                cost=0.05,
                tokens_used=100,
                execution_time=1.2,
                provider="openai"
            )
        )
        mock.config = ProviderConfig(
            name="openai",
            api_key="test-key",
            models={"code": "gpt-4o"},
            cost_per_input_token=0.00001,
            cost_per_output_token=0.00003,
            max_tokens=4000,
            max_concurrent=10
        )
        return mock
    
    @pytest.fixture
    def mock_budget_monitor(self):
        """Mock budget monitor that follows monitoring contract"""
        mock = Mock(spec=BudgetMonitor)
        mock.record_spending = AsyncMock(return_value=True)
        mock.check_budget = AsyncMock(return_value=True)
        mock.get_remaining_budget = AsyncMock(return_value=100.0)
        return mock
    
    @pytest.fixture
    def mock_health_monitor(self):
        """Mock health monitor that follows monitoring contract"""
        mock = Mock(spec=ProviderHealthMonitor)
        mock.check_provider_health = AsyncMock(
            return_value=HealthStatus.HEALTHY
        )
        mock.record_provider_call = AsyncMock()
        return mock
    
    @pytest.fixture
    def provider_manager(self, mock_openai_provider, mock_budget_monitor, mock_health_monitor):
        """AI Provider Manager with mocked dependencies"""
        manager = AIProviderManager()
        
        # Inject mocked dependencies
        manager.providers = {"openai": mock_openai_provider}
        manager.budget_monitor = mock_budget_monitor
        manager.health_monitor = mock_health_monitor
        
        return manager
    
    @pytest.mark.asyncio
    async def test_task_processing_contract(self, provider_manager, mock_openai_provider):
        """Test task processing follows the defined contract"""
        # Arrange
        task = Task(
            id="test-task-1",
            startup_id="test-startup",
            type=TaskType.CODE_GENERATION,
            description="Generate Python function",
            prompt="Create a function that adds two numbers",
            max_tokens=1000,
            priority=1
        )
        
        # Act
        result = await provider_manager.process_task(task)
        
        # Assert - Contract validation
        assert isinstance(result, TaskResult)
        assert result.task_id == task.id
        assert result.success is True
        assert isinstance(result.output, str)
        assert isinstance(result.cost, float)
        assert result.cost >= 0
        assert isinstance(result.tokens_used, int)
        assert result.tokens_used > 0
        assert isinstance(result.execution_time, float)
        assert result.execution_time > 0
        assert result.provider == "openai"
        
        # Verify provider was called with correct task
        mock_openai_provider.process_task.assert_called_once_with(task)
    
    @pytest.mark.asyncio
    async def test_budget_integration_contract(self, provider_manager, mock_budget_monitor):
        """Test integration with budget monitor follows contract"""
        # Arrange
        task = Task(
            id="budget-test-1",
            startup_id="test-startup",
            type=TaskType.CODE_GENERATION,
            description="Test budget integration",
            prompt="Test prompt",
            max_tokens=1000
        )
        
        # Act
        result = await provider_manager.process_task(task)
        
        # Assert - Budget contract validation
        mock_budget_monitor.check_budget.assert_called_once_with(
            startup_id="test-startup"
        )
        
        # Verify spending was recorded
        mock_budget_monitor.record_spending.assert_called_once()
        spending_call_args = mock_budget_monitor.record_spending.call_args[0][0]
        
        assert isinstance(spending_call_args, SpendingRecord)
        assert spending_call_args.startup_id == "test-startup"
        assert spending_call_args.provider == "openai"
        assert spending_call_args.amount == result.cost
        assert isinstance(spending_call_args.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_health_monitoring_contract(self, provider_manager, mock_health_monitor):
        """Test health monitoring integration follows contract"""
        # Arrange
        task = Task(
            id="health-test-1",
            startup_id="test-startup", 
            type=TaskType.CODE_GENERATION,
            description="Test health monitoring",
            prompt="Test prompt",
            max_tokens=1000
        )
        
        # Act
        result = await provider_manager.process_task(task)
        
        # Assert - Health monitoring contract validation
        mock_health_monitor.check_provider_health.assert_called_once_with("openai")
        
        # Verify provider call was recorded for health tracking
        mock_health_monitor.record_provider_call.assert_called_once()
        call_args = mock_health_monitor.record_provider_call.call_args[0]
        
        provider_call = call_args[0]
        assert isinstance(provider_call, ProviderCall)
        assert provider_call.provider == "openai"
        assert provider_call.task_id == "health-test-1"
        assert provider_call.success == True
        assert provider_call.cost == result.cost
    
    @pytest.mark.asyncio
    async def test_provider_failure_contract(self, provider_manager, mock_openai_provider):
        """Test provider failure handling follows error contract"""
        # Arrange
        task = Task(
            id="failure-test-1",
            startup_id="test-startup",
            type=TaskType.CODE_GENERATION,
            description="Test failure handling",
            prompt="Test prompt",
            max_tokens=1000
        )
        
        # Mock provider failure
        mock_openai_provider.process_task = AsyncMock(
            side_effect=ProviderError("API rate limit exceeded")
        )
        
        # Act & Assert
        with pytest.raises(ProviderError) as exc_info:
            await provider_manager.process_task(task)
        
        assert "API rate limit exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_budget_exceeded_contract(self, provider_manager, mock_budget_monitor):
        """Test budget exceeded handling follows contract"""
        # Arrange
        task = Task(
            id="budget-exceeded-test",
            startup_id="test-startup",
            type=TaskType.CODE_GENERATION,
            description="Test budget exceeded",
            prompt="Test prompt",
            max_tokens=1000
        )
        
        # Mock budget exceeded
        from budget_monitor import BudgetExceededError
        mock_budget_monitor.check_budget = AsyncMock(
            side_effect=BudgetExceededError("Budget limit exceeded")
        )
        
        # Act & Assert
        with pytest.raises(BudgetExceededError) as exc_info:
            await provider_manager.process_task(task)
        
        assert "Budget limit exceeded" in str(exc_info.value)
        
        # Verify no provider was called if budget exceeded
        provider_manager.providers["openai"].process_task.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_provider_routing_contract(self, provider_manager):
        """Test task routing to correct providers follows contract"""
        # Arrange - Add multiple providers
        mock_anthropic = Mock(spec=AnthropicProvider)
        mock_anthropic.process_task = AsyncMock(
            return_value=TaskResult(
                task_id="anthropic-task",
                success=True,
                output="Anthropic response", 
                cost=0.03,
                tokens_used=50,
                execution_time=0.8,
                provider="anthropic"
            )
        )
        provider_manager.providers["anthropic"] = mock_anthropic
        
        # Tasks that should route to different providers
        code_task = Task(
            id="code-task",
            startup_id="test-startup",
            type=TaskType.CODE_GENERATION,
            description="Code generation task",
            prompt="Generate code",
            max_tokens=1000
        )
        
        analysis_task = Task(
            id="analysis-task", 
            startup_id="test-startup",
            type=TaskType.FOUNDER_ANALYSIS,
            description="Founder analysis task",
            prompt="Analyze founder fit",
            max_tokens=1000
        )
        
        # Act
        code_result = await provider_manager.process_task(code_task)
        analysis_result = await provider_manager.process_task(analysis_task)
        
        # Assert - Verify correct routing
        assert code_result.provider == "openai"  # Code tasks go to OpenAI
        assert analysis_result.provider == "anthropic"  # Analysis tasks go to Anthropic
        
        # Verify correct providers were called
        provider_manager.providers["openai"].process_task.assert_called_with(code_task)
        provider_manager.providers["anthropic"].process_task.assert_called_with(analysis_task)
    
    @pytest.mark.asyncio
    async def test_concurrent_task_processing_contract(self, provider_manager):
        """Test concurrent task processing respects provider limits"""
        # Arrange
        tasks = [
            Task(
                id=f"concurrent-task-{i}",
                startup_id="test-startup",
                type=TaskType.CODE_GENERATION,
                description=f"Concurrent task {i}",
                prompt="Test prompt",
                max_tokens=1000
            ) for i in range(5)
        ]
        
        # Act
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*[
            provider_manager.process_task(task) for task in tasks
        ])
        end_time = asyncio.get_event_loop().time()
        
        # Assert
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.task_id == f"concurrent-task-{i}"
            assert result.success is True
        
        # Should process reasonably quickly with mocked providers
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should be fast with mocks
    
    def test_provider_configuration_contract(self, provider_manager):
        """Test provider configuration follows expected contract"""
        # Act
        openai_config = provider_manager.providers["openai"].config
        
        # Assert - Configuration contract validation
        assert isinstance(openai_config, ProviderConfig)
        assert openai_config.name == "openai"
        assert isinstance(openai_config.api_key, str)
        assert len(openai_config.api_key) > 0
        assert isinstance(openai_config.models, dict)
        assert len(openai_config.models) > 0
        assert isinstance(openai_config.cost_per_input_token, float)
        assert openai_config.cost_per_input_token > 0
        assert isinstance(openai_config.cost_per_output_token, float)
        assert openai_config.cost_per_output_token > 0
        assert isinstance(openai_config.max_tokens, int)
        assert openai_config.max_tokens > 0
        assert isinstance(openai_config.max_concurrent, int)
        assert openai_config.max_concurrent > 0


class TestAIProviderInterfaceContract:
    """Test that all AI providers follow the interface contract"""
    
    def test_openai_provider_interface_compliance(self):
        """Test OpenAI provider implements required interface"""
        config = ProviderConfig(
            name="openai",
            api_key="test-key", 
            models={"code": "gpt-4o"},
            cost_per_input_token=0.00001,
            cost_per_output_token=0.00003,
            max_tokens=4000,
            max_concurrent=10
        )
        
        provider = OpenAIProvider(config)
        
        # Assert interface compliance
        assert isinstance(provider, AIProviderInterface)
        assert hasattr(provider, 'process_task')
        assert hasattr(provider, 'calculate_cost')
        assert hasattr(provider, 'config')
        assert callable(provider.process_task)
        assert callable(provider.calculate_cost)
    
    def test_anthropic_provider_interface_compliance(self):
        """Test Anthropic provider implements required interface"""
        config = ProviderConfig(
            name="anthropic",
            api_key="test-key",
            models={"analysis": "claude-3-sonnet"},
            cost_per_input_token=0.000015,
            cost_per_output_token=0.000075,
            max_tokens=4000,
            max_concurrent=5
        )
        
        provider = AnthropicProvider(config)
        
        # Assert interface compliance
        assert isinstance(provider, AIProviderInterface)
        assert hasattr(provider, 'process_task')
        assert hasattr(provider, 'calculate_cost')
        assert hasattr(provider, 'config')
        assert callable(provider.process_task)
        assert callable(provider.calculate_cost)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])