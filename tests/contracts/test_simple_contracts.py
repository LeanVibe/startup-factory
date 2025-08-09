#!/usr/bin/env python3
"""
Simplified Contract Tests for Core Component Interactions

Tests the essential contracts between components without complex dependencies.
This validates that components can interact correctly with each other.

Focus: Test what matters most for production readiness.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add tools directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from ai_providers import AIProviderManager, OpenAIProvider, AnthropicProvider, ProviderConfig
from budget_monitor import BudgetMonitor, BudgetLimit, SpendingRecord
from core_types import Task, TaskResult, TaskType, ProviderError


class TestCoreContractInteractions:
    """Test essential contracts between core components"""
    
    @pytest.fixture
    def mock_provider_config(self):
        """Mock provider configuration"""
        return ProviderConfig(
            name="test_provider",
            api_key="test-key",
            models={"code": "test-model"},
            cost_per_input_token=0.00001,
            cost_per_output_token=0.00003,
            max_tokens=4000,
            max_concurrent=10
        )
    
    @pytest.fixture
    def sample_task(self):
        """Sample task for testing"""
        return Task(
            id="test-task-1",
            startup_id="test-startup",
            type=TaskType.CODE_GENERATION,
            description="Generate Python function",
            prompt="Create a function that adds two numbers",
            max_tokens=1000
        )
    
    def test_provider_config_contract(self, mock_provider_config):
        """Test provider configuration follows expected contract"""
        config = mock_provider_config
        
        # Verify required fields exist
        assert hasattr(config, 'name')
        assert hasattr(config, 'api_key')
        assert hasattr(config, 'models')
        assert hasattr(config, 'cost_per_input_token')
        assert hasattr(config, 'cost_per_output_token')
        assert hasattr(config, 'max_tokens')
        assert hasattr(config, 'max_concurrent')
        
        # Verify field types
        assert isinstance(config.name, str)
        assert isinstance(config.api_key, str)
        assert isinstance(config.models, dict)
        assert isinstance(config.cost_per_input_token, float)
        assert isinstance(config.cost_per_output_token, float)
        assert isinstance(config.max_tokens, int)
        assert isinstance(config.max_concurrent, int)
        
        # Verify reasonable values
        assert len(config.name) > 0
        assert len(config.api_key) > 0
        assert len(config.models) > 0
        assert config.cost_per_input_token > 0
        assert config.cost_per_output_token > 0
        assert config.max_tokens > 0
        assert config.max_concurrent > 0
    
    def test_task_contract_structure(self, sample_task):
        """Test task structure follows expected contract"""
        task = sample_task
        
        # Verify required fields
        required_fields = ['id', 'startup_id', 'type', 'description', 'prompt', 'max_tokens']
        for field in required_fields:
            assert hasattr(task, field), f"Task missing required field: {field}"
        
        # Verify field types
        assert isinstance(task.id, str)
        assert isinstance(task.startup_id, str)
        assert isinstance(task.type, TaskType)
        assert isinstance(task.description, str)
        assert isinstance(task.prompt, str)
        assert isinstance(task.max_tokens, int)
        
        # Verify field values
        assert len(task.id) > 0
        assert len(task.startup_id) > 0
        assert len(task.description) > 0
        assert len(task.prompt) > 0
        assert task.max_tokens > 0
    
    def test_task_result_contract_structure(self):
        """Test task result structure follows expected contract"""
        result = TaskResult(
            task_id="test-task-1",
            success=True,
            output="Test output",
            cost=0.05,
            tokens_used=100,
            execution_time=1.5,
            provider="test_provider"
        )
        
        # Verify required fields
        required_fields = ['task_id', 'success', 'output', 'cost', 'tokens_used', 'execution_time', 'provider']
        for field in required_fields:
            assert hasattr(result, field), f"TaskResult missing required field: {field}"
        
        # Verify field types
        assert isinstance(result.task_id, str)
        assert isinstance(result.success, bool)
        assert isinstance(result.output, str)
        assert isinstance(result.cost, float)
        assert isinstance(result.tokens_used, int)
        assert isinstance(result.execution_time, float)
        assert isinstance(result.provider, str)
        
        # Verify field values
        assert len(result.task_id) > 0
        assert result.cost >= 0
        assert result.tokens_used >= 0
        assert result.execution_time >= 0
        assert len(result.provider) > 0
    
    @pytest.mark.asyncio
    async def test_provider_interface_contract_compliance(self, mock_provider_config):
        """Test that AI providers implement the expected interface contract"""
        
        # Test OpenAI provider implements interface
        with patch('openai.resources.chat.completions.Completions.create') as mock_openai:
            mock_openai.return_value = Mock(
                choices=[Mock(message=Mock(content="Test response"))],
                usage=Mock(prompt_tokens=50, completion_tokens=100)
            )
            
            openai_provider = OpenAIProvider(mock_provider_config)
            
            # Verify interface methods exist
            assert hasattr(openai_provider, 'process_task')
            assert hasattr(openai_provider, 'calculate_cost')
            assert callable(openai_provider.process_task)
            assert callable(openai_provider.calculate_cost)
            
            # Test process_task contract
            task = Task(
                id="interface-test",
                startup_id="test-startup",
                type=TaskType.CODE_GENERATION,
                description="Test interface",
                prompt="Test prompt",
                max_tokens=1000
            )
            
            result = await openai_provider.process_task(task)
            
            # Verify result follows contract
            assert isinstance(result, TaskResult)
            assert result.task_id == task.id
            assert isinstance(result.success, bool)
            assert isinstance(result.output, str)
            assert isinstance(result.cost, float)
            assert isinstance(result.provider, str)
    
    @pytest.mark.asyncio
    async def test_budget_monitor_contract(self):
        """Test budget monitor contract compliance"""
        budget_monitor = BudgetMonitor()
        
        # Test budget limit setting contract
        budget_limit = BudgetLimit(
            startup_id="contract-test",
            daily_limit=50.0,
            monthly_limit=1000.0,
            task_limit=5.0
        )
        
        await budget_monitor.set_budget_limit("contract-test", budget_limit)
        
        # Test spending record contract
        spending_record = SpendingRecord(
            startup_id="contract-test",
            provider="test_provider",
            amount=2.50,
            task_id="test-task",
            description="Test spending"
        )
        
        # Verify spending record structure
        assert hasattr(spending_record, 'startup_id')
        assert hasattr(spending_record, 'provider')
        assert hasattr(spending_record, 'amount')
        assert hasattr(spending_record, 'task_id')
        assert hasattr(spending_record, 'timestamp')
        
        # Test budget checking contract
        can_spend = await budget_monitor.check_budget("contract-test")
        assert isinstance(can_spend, bool)
        
        # Test spending recording contract
        result = await budget_monitor.record_spending(spending_record)
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio  
    async def test_component_interaction_data_flow(self):
        """Test data flow between components follows expected patterns"""
        
        # Setup mocked components
        with patch('openai.resources.chat.completions.Completions.create') as mock_openai:
            mock_openai.return_value = Mock(
                choices=[Mock(message=Mock(content="Generated code"))],
                usage=Mock(prompt_tokens=50, completion_tokens=150)
            )
            
            # Create components
            provider_config = ProviderConfig(
                name="openai",
                api_key="test-key",
                models={"code": "gpt-4o"},
                cost_per_input_token=0.00001,
                cost_per_output_token=0.00003,
                max_tokens=4000,
                max_concurrent=10
            )
            
            provider = OpenAIProvider(provider_config)
            budget_monitor = BudgetMonitor()
            
            # Setup budget
            budget_limit = BudgetLimit(
                startup_id="data-flow-test",
                daily_limit=100.0,
                monthly_limit=2000.0,
                task_limit=10.0
            )
            await budget_monitor.set_budget_limit("data-flow-test", budget_limit)
            
            # Test data flow: Task -> Provider -> Result -> Budget
            task = Task(
                id="data-flow-test-1",
                startup_id="data-flow-test",
                type=TaskType.CODE_GENERATION,
                description="Test data flow",
                prompt="Generate a simple function",
                max_tokens=1000
            )
            
            # Process task through provider
            result = await provider.process_task(task)
            
            # Verify data transformation
            assert result.task_id == task.id
            assert result.provider == provider_config.name
            assert result.cost > 0  # Should have calculated cost
            
            # Record spending in budget monitor
            spending_record = SpendingRecord(
                startup_id=task.startup_id,
                provider=result.provider,
                amount=result.cost,
                task_id=task.id,
                description=f"Task: {task.description}"
            )
            
            budget_result = await budget_monitor.record_spending(spending_record)
            assert budget_result is True
            
            # Verify budget state updated
            remaining_budget = await budget_monitor.get_remaining_budget("data-flow-test")
            assert remaining_budget < 100.0  # Should be reduced
    
    def test_error_handling_contracts(self):
        """Test error handling follows expected contracts"""
        
        # Test ProviderError contract
        try:
            raise ProviderError("Test provider error")
        except ProviderError as e:
            assert isinstance(e, Exception)
            assert str(e) == "Test provider error"
        
        # Test budget-related errors
        from budget_monitor import BudgetExceededError
        try:
            raise BudgetExceededError("Budget limit exceeded")
        except BudgetExceededError as e:
            assert isinstance(e, Exception)
            assert str(e) == "Budget limit exceeded"
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_contract(self):
        """Test components handle concurrent operations correctly"""
        budget_monitor = BudgetMonitor()
        
        # Setup budget
        budget_limit = BudgetLimit(
            startup_id="concurrent-test",
            daily_limit=100.0,
            monthly_limit=2000.0,
            task_limit=10.0
        )
        await budget_monitor.set_budget_limit("concurrent-test", budget_limit)
        
        # Create multiple spending records concurrently
        spending_records = [
            SpendingRecord(
                startup_id="concurrent-test",
                provider="test_provider",
                amount=5.0,
                task_id=f"concurrent-task-{i}",
                description=f"Concurrent test {i}"
            )
            for i in range(5)
        ]
        
        # Record spending concurrently
        results = await asyncio.gather(*[
            budget_monitor.record_spending(record)
            for record in spending_records
        ])
        
        # Verify all succeeded
        assert all(results)
        assert len(results) == 5
        
        # Verify budget was updated correctly
        remaining_budget = await budget_monitor.get_remaining_budget("concurrent-test")
        expected_remaining = 100.0 - (5 * 5.0)  # 100 - 25 = 75
        assert abs(remaining_budget - expected_remaining) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])