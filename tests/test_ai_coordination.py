#!/usr/bin/env python3
"""
Comprehensive tests for AI coordination features
Tests real provider integration, cost tracking, and health monitoring.
"""

import asyncio
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from tools.ai_providers import (
    AIProviderManager, OpenAIProvider, AnthropicProvider, 
    ProviderConfig, create_default_provider_manager
)
from tools.budget_monitor import BudgetMonitor, BudgetExceededError, BudgetAlert
from tools.health_monitor import ProviderHealthMonitor, HealthStatus, HealthAlert
from tools.queue_processor import QueueProcessor
from tools.core_types import Task, TaskType, TaskPriority


class TestAIProviders:
    """Test suite for AI provider integration"""
    
    @pytest.fixture
    def mock_openai_config(self):
        """Mock OpenAI configuration for testing"""
        return ProviderConfig(
            name='openai',
            api_key='test-key',
            models={'code': 'gpt-4o', 'research': 'gpt-4o'},
            cost_per_input_token=0.00001,
            cost_per_output_token=0.00003,
            max_tokens=4000,
            max_concurrent=10
        )
    
    @pytest.fixture
    def sample_task(self):
        """Sample task for testing"""
        return Task(
            id='test-task-1',
            startup_id='test-startup',
            type=TaskType.CODE_GENERATION,
            description='Generate a simple Python function',
            prompt='Create a function that adds two numbers',
            max_tokens=1000
        )
    
    def test_provider_config_creation(self, mock_openai_config):
        """Test provider configuration creation"""
        assert mock_openai_config.name == 'openai'
        assert mock_openai_config.api_key == 'test-key'
        assert mock_openai_config.max_tokens == 4000
        assert mock_openai_config.enabled is True
    
    @patch('tools.ai_providers.openai.AsyncOpenAI')
    async def test_openai_provider_call(self, mock_client, mock_openai_config, sample_task):
        """Test OpenAI provider API call"""
        # Mock the OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = 'def add(a, b): return a + b'
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Create provider and test call
        provider = OpenAIProvider(mock_openai_config)
        result = await provider.call_api(sample_task)
        
        assert result.success is True
        assert result.content == 'def add(a, b): return a + b'
        assert result.provider_used == 'openai'
        assert result.cost > 0
        assert result.tokens_used == 150
    
    def test_provider_manager_registration(self, mock_openai_config):
        """Test provider manager registration"""
        manager = AIProviderManager()
        provider = OpenAIProvider(mock_openai_config)
        
        manager.register_provider('openai', provider, mock_openai_config)
        
        assert 'openai' in manager.providers
        assert manager.get_provider('openai') is provider
        assert 'openai' in manager.get_available_providers()


class TestBudgetMonitor:
    """Test suite for budget monitoring"""
    
    @pytest.fixture
    def budget_monitor(self):
        """Budget monitor fixture"""
        return BudgetMonitor()
    
    @pytest.fixture
    def startup_id(self):
        """Test startup ID"""
        return 'test-startup-1'
    
    async def test_budget_limit_setting(self, budget_monitor, startup_id):
        """Test setting budget limits"""
        await budget_monitor.set_budget_limit(
            startup_id=startup_id,
            daily_limit=100.0,
            monthly_limit=1000.0,
            total_limit=5000.0
        )
        
        assert startup_id in budget_monitor.budget_limits
        limit = budget_monitor.budget_limits[startup_id]
        assert limit.daily_limit == 100.0
        assert limit.monthly_limit == 1000.0
        assert limit.total_limit == 5000.0
    
    async def test_spending_recording(self, budget_monitor, startup_id):
        """Test spending recording"""
        await budget_monitor.set_budget_limit(startup_id, daily_limit=100.0)
        
        await budget_monitor.record_spending(
            startup_id=startup_id,
            provider='openai',
            task_id='task-1',
            cost=10.50,
            tokens_used=1000,
            task_type='code_generation',
            success=True
        )
        
        assert len(budget_monitor.spending_records) == 1
        record = budget_monitor.spending_records[0]
        assert record.startup_id == startup_id
        assert record.cost == 10.50
        assert record.tokens_used == 1000
        assert record.success is True
    
    async def test_budget_limit_checking(self, budget_monitor, startup_id):
        """Test budget limit enforcement"""
        await budget_monitor.set_budget_limit(startup_id, daily_limit=50.0)
        
        # First spending should be fine
        await budget_monitor.record_spending(
            startup_id, 'openai', 'task-1', 30.0, 1000, 'code_generation', True
        )
        
        # Second spending should trigger budget exceeded error
        with pytest.raises(BudgetExceededError):
            await budget_monitor.record_spending(
                startup_id, 'openai', 'task-2', 25.0, 1000, 'code_generation', True
            )


class TestHealthMonitor:
    """Test suite for provider health monitoring"""
    
    @pytest.fixture
    def provider_manager(self):
        """Mock provider manager for testing"""
        manager = AIProviderManager()
        
        # Add mock providers
        mock_config = ProviderConfig(
            name='test-provider',
            api_key='test-key',
            models={},
            cost_per_input_token=0.00001,
            cost_per_output_token=0.00003,
            max_tokens=4000,
            max_concurrent=10
        )
        
        mock_provider = Mock()
        manager.register_provider('test-provider', mock_provider, mock_config)
        
        return manager
    
    @pytest.fixture
    def health_monitor(self, provider_manager):
        """Health monitor fixture"""
        return ProviderHealthMonitor(provider_manager, check_interval=1.0)
    
    def test_health_monitor_initialization(self, health_monitor):
        """Test health monitor initialization"""
        assert len(health_monitor.provider_health) > 0
        assert 'test-provider' in health_monitor.provider_health
        
        health = health_monitor.provider_health['test-provider']
        assert health.provider_name == 'test-provider'
        assert health.overall_status == HealthStatus.UNKNOWN


class TestIntegratedAICoordination:
    """Integration tests for complete AI coordination system"""
    
    @pytest.fixture
    async def coordinator_system(self):
        """Complete coordinator system fixture"""
        # Create provider manager with mock providers
        provider_manager = AIProviderManager()
        
        mock_config = ProviderConfig(
            name='mock-provider',
            api_key='test-key',
            models={},
            cost_per_input_token=0.00001,
            cost_per_output_token=0.00003,
            max_tokens=4000,
            max_concurrent=10
        )
        
        mock_provider = Mock()
        async def mock_call_api(task):
            from tools.core_types import TaskResult
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=True,
                content='Mock response',
                cost=0.05,
                provider_used='mock-provider',
                execution_time_seconds=0.5,
                tokens_used=100
            )
        
        mock_provider.call_api = mock_call_api
        provider_manager.register_provider('mock-provider', mock_provider, mock_config)
        
        # Create budget monitor
        budget_monitor = BudgetMonitor()
        
        # Create health monitor
        health_monitor = ProviderHealthMonitor(provider_manager, check_interval=1.0)
        
        # Create queue processor
        queue_processor = QueueProcessor(
            max_concurrent=5,
            provider_manager=provider_manager,
            budget_monitor=budget_monitor
        )
        
        return {
            'provider_manager': provider_manager,
            'budget_monitor': budget_monitor,
            'health_monitor': health_monitor,
            'queue_processor': queue_processor
        }
    
    async def test_end_to_end_task_processing(self, coordinator_system):
        """Test end-to-end task processing with all coordination features"""
        system = coordinator_system
        queue_processor = system['queue_processor']
        budget_monitor = system['budget_monitor']
        
        # Set up budget limits
        await budget_monitor.set_budget_limit(
            'test-startup', daily_limit=100.0, total_limit=1000.0
        )
        
        # Create test task
        task = Task(
            id='integration-test-1',
            startup_id='test-startup',
            type=TaskType.CODE_GENERATION,
            description='Integration test task',
            prompt='Generate a simple function',
            priority=TaskPriority.HIGH
        )
        
        # Start processing
        await queue_processor.start_processing()
        
        try:
            # Submit task
            task_id = await queue_processor.submit_task(task)
            assert task_id == task.id
            
            # Wait for task completion
            max_wait = 10  # seconds
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < max_wait:
                result = await queue_processor.get_task_result(task_id)
                if result:
                    break
                await asyncio.sleep(0.1)
            
            # Verify task completion
            assert result is not None
            assert result.success is True
            assert result.content == 'Mock response'
            assert result.cost > 0
            
        finally:
            await queue_processor.stop_processing()


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])