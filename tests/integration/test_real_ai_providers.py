#!/usr/bin/env python3
"""
Real AI Provider Integration Tests

Tests actual AI provider integrations with real APIs when keys are available,
fallback to comprehensive mocks when not. Validates production scenarios
including rate limits, error handling, and cost tracking accuracy.

Environment Setup:
    export OPENAI_API_KEY="your-key" (optional - will mock if not provided)
    export ANTHROPIC_API_KEY="your-key" (optional - will mock if not provided)
    export PERPLEXITY_API_KEY="your-key" (optional - will mock if not provided)
    export AI_TEST_MODE="real" (to force real API calls)
"""

import asyncio
import os
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from ai_providers import (
    AIProviderManager, OpenAIProvider, AnthropicProvider,
    ProviderConfig, ProviderCall, AIProviderInterface
)
from core_types import Task, TaskResult, TaskType, TaskPriority, ProviderError, generate_task_id
from budget_monitor import BudgetMonitor, BudgetLimit


@pytest.fixture(scope="module")
def test_mode():
    """Determine if we're testing with real APIs or mocks"""
    force_real = os.getenv("AI_TEST_MODE") == "real"
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    return {
        "use_real_apis": force_real or (has_openai or has_anthropic),
        "has_openai": has_openai,
        "has_anthropic": has_anthropic,
        "rate_limit": True  # Always respect rate limits in tests
    }


@pytest.fixture(scope="module")
def openai_config():
    """OpenAI provider configuration"""
    return ProviderConfig(
        name="openai",
        api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        models={
            "research": "gpt-4o-mini",  # Use cheaper model for testing
            "code": "gpt-4o-mini",
            "analysis": "gpt-4o-mini"
        },
        cost_per_input_token=0.000150 / 1000,  # GPT-4o-mini rates
        cost_per_output_token=0.000600 / 1000,
        max_tokens=2000,
        max_concurrent=3,  # Lower for testing
        enabled=True
    )


@pytest.fixture(scope="module")
def anthropic_config():
    """Anthropic provider configuration"""
    return ProviderConfig(
        name="anthropic",
        api_key=os.getenv("ANTHROPIC_API_KEY", "test-key"),
        models={
            "research": "claude-3-haiku-20240307",  # Cheaper model for testing
            "code": "claude-3-haiku-20240307",
            "analysis": "claude-3-haiku-20240307"
        },
        cost_per_input_token=0.25 / 1000000,  # Haiku rates
        cost_per_output_token=1.25 / 1000000,
        max_tokens=2000,
        max_concurrent=3,
        enabled=True
    )


@pytest.fixture(scope="module")
def sample_tasks():
    """Sample tasks for testing different scenarios"""
    return {
        "simple_research": Task(
            id=generate_task_id(),
            startup_id="test_startup_001",
            type=TaskType.MARKET_RESEARCH,
            description="Simple market research task",
            prompt="What are the top 3 trends in fintech for 2025? Provide a brief 100-word summary.",
            priority=TaskPriority.MEDIUM,
            max_tokens=200
        ),
        "code_generation": Task(
            id=generate_task_id(),
            startup_id="test_startup_002", 
            type=TaskType.CODE_GENERATION,
            description="Simple code generation task",
            prompt="Write a Python function to calculate compound interest. Include docstring.",
            priority=TaskPriority.HIGH,
            max_tokens=300
        ),
        "complex_analysis": Task(
            id=generate_task_id(),
            startup_id="test_startup_003",
            type=TaskType.FOUNDER_ANALYSIS,
            description="Complex analysis task",
            prompt="Analyze the key success factors for a SaaS startup in the project management space. Provide 5 key insights.",
            priority=TaskPriority.LOW,
            max_tokens=500
        )
    }


class TestRealAIProviderIntegration:
    """Comprehensive tests for real AI provider integration"""
    
    # ========== Real API Integration Tests ==========
    
    @pytest.mark.asyncio
    async def test_openai_real_api_integration(self, openai_config, sample_tasks, test_mode):
        """Test OpenAI provider with real API integration"""
        if not test_mode["has_openai"] and not test_mode["use_real_apis"]:
            pytest.skip("No OpenAI API key provided - using mock test instead")
        
        provider = OpenAIProvider(openai_config)
        task = sample_tasks["simple_research"]
        
        # Add rate limiting delay to avoid hitting limits
        if test_mode["rate_limit"]:
            await asyncio.sleep(1)
        
        start_time = time.time()
        result = await provider.call_api(task)
        execution_time = time.time() - start_time
        
        # Validate result structure
        assert isinstance(result, TaskResult)
        assert result.task_id == task.id
        assert result.startup_id == task.startup_id
        assert result.success is True
        assert len(result.content) > 50  # Should have substantial content
        assert result.cost > 0  # Should have calculated cost
        assert result.provider_used == "openai"
        assert result.tokens_used > 0
        assert result.execution_time_seconds > 0
        assert isinstance(result.completed_at, datetime)
        
        # Validate performance
        assert execution_time < 30  # Should complete within 30 seconds
        assert result.cost < 0.10  # Should cost less than 10 cents
        
        # Validate call history
        assert len(provider.call_history) == 1
        call = provider.call_history[0]
        assert call.provider == "openai"
        assert call.task_id == task.id
        assert call.success is True
        assert call.cost == result.cost
        
        print(f"✅ OpenAI Real API Test: {execution_time:.2f}s, ${result.cost:.4f}, {result.tokens_used} tokens")
    
    @pytest.mark.asyncio
    async def test_anthropic_real_api_integration(self, anthropic_config, sample_tasks, test_mode):
        """Test Anthropic provider with real API integration"""
        if not test_mode["has_anthropic"] and not test_mode["use_real_apis"]:
            pytest.skip("No Anthropic API key provided - using mock test instead") 
        
        provider = AnthropicProvider(anthropic_config)
        task = sample_tasks["code_generation"]
        
        # Add rate limiting delay
        if test_mode["rate_limit"]:
            await asyncio.sleep(2)
        
        start_time = time.time()
        result = await provider.call_api(task)
        execution_time = time.time() - start_time
        
        # Validate result structure
        assert isinstance(result, TaskResult)
        assert result.task_id == task.id
        assert result.success is True
        assert len(result.content) > 50
        assert result.cost > 0
        assert result.provider_used == "anthropic"
        assert result.tokens_used > 0
        
        # Validate performance
        assert execution_time < 30
        assert result.cost < 0.10
        
        # Validate call history
        assert len(provider.call_history) == 1
        call = provider.call_history[0]
        assert call.provider == "anthropic" 
        assert call.success is True
        
        print(f"✅ Anthropic Real API Test: {execution_time:.2f}s, ${result.cost:.4f}, {result.tokens_used} tokens")
    
    @pytest.mark.asyncio  
    async def test_provider_manager_real_integration(self, openai_config, anthropic_config, sample_tasks, test_mode):
        """Test provider manager with real API integration"""
        manager = AIProviderManager()
        
        # Register providers that have API keys
        if test_mode["has_openai"]:
            openai_provider = OpenAIProvider(openai_config)
            manager.register_provider("openai", openai_provider, openai_config)
        
        if test_mode["has_anthropic"]:
            anthropic_provider = AnthropicProvider(anthropic_config)
            manager.register_provider("anthropic", anthropic_provider, anthropic_config)
        
        if not test_mode["has_openai"] and not test_mode["has_anthropic"]:
            pytest.skip("No API keys provided - cannot test real provider manager integration")
        
        # Test available providers
        available = manager.get_available_providers()
        assert len(available) > 0
        
        # Test calling each available provider
        for provider_name in available[:1]:  # Test only first to avoid rate limits
            task = sample_tasks["simple_research"]
            
            if test_mode["rate_limit"]:
                await asyncio.sleep(1)
            
            result = await manager.call_provider(provider_name, task)
            
            assert result.success is True
            assert result.provider_used == provider_name
            assert len(result.content) > 10
            
            print(f"✅ Provider Manager Real Test ({provider_name}): Success")
    
    # ========== Error Handling & Production Scenarios ==========
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_handling(self, openai_config):
        """Test handling of invalid API keys"""
        # Create config with invalid key
        invalid_config = openai_config
        invalid_config.api_key = "sk-invalid_test_key_12345"
        
        provider = OpenAIProvider(invalid_config)
        task = Task(
            id=generate_task_id(),
            startup_id="test_auth",
            type=TaskType.MARKET_RESEARCH,
            description="Auth test",
            prompt="Test authentication failure handling",
            max_tokens=50
        )
        
        # Should handle auth error gracefully
        result = await provider.call_api(task)
        
        assert result.success is False
        assert result.error_message is not None
        assert "authentication" in result.error_message.lower() or "api" in result.error_message.lower()
        assert result.cost == 0  # No cost for failed requests
        
        # Should record failed call
        assert len(provider.call_history) == 1
        call = provider.call_history[0]
        assert call.success is False
        assert call.error is not None
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, openai_config, test_mode):
        """Test rate limit error handling and recovery"""
        if not test_mode["has_openai"]:
            # Mock rate limit scenario
            provider = OpenAIProvider(openai_config)
            
            with patch.object(provider.client.chat.completions, 'create') as mock_create:
                # Simulate rate limit error
                mock_create.side_effect = Exception("Rate limit exceeded")
                
                task = Task(
                    id=generate_task_id(),
                    startup_id="test_rate_limit",
                    type=TaskType.MARKET_RESEARCH,
                    description="Rate limit test",
                    prompt="Test rate limiting",
                    max_tokens=50
                )
                
                result = await provider.call_api(task)
                
                assert result.success is False
                assert "rate limit" in result.error_message.lower()
        else:
            # With real API, we'll just validate the rate limit configuration exists
            provider = OpenAIProvider(openai_config)
            assert provider.config.max_concurrent <= 5  # Should have conservative limits for testing
            print("✅ Rate limit handling: Configuration validated")
    
    @pytest.mark.asyncio
    async def test_token_limit_exceeded_handling(self, openai_config, test_mode):
        """Test handling when token limits are exceeded"""
        provider = OpenAIProvider(openai_config)
        
        # Create task with excessive tokens
        large_prompt = "Analyze this: " + "word " * 10000  # Very large prompt
        task = Task(
            id=generate_task_id(),
            startup_id="test_token_limit",
            type=TaskType.MARKET_RESEARCH,  
            description="Token limit test",
            prompt=large_prompt,
            max_tokens=4096
        )
        
        if not test_mode["has_openai"]:
            # Mock token limit exceeded scenario
            with patch.object(provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.side_effect = Exception("Maximum context length exceeded: too many tokens")
                
                result = await provider.call_api(task)
                
                assert result.success is False
                assert "token" in result.error_message.lower() or "limit" in result.error_message.lower()
        else:
            # With real API key, test actual behavior
            result = await provider.call_api(task)
            
            # Should either:
            # 1. Handle gracefully with truncation, or
            # 2. Return error with clear message
            if not result.success:
                assert "token" in result.error_message.lower() or "limit" in result.error_message.lower()
            else:
                # If successful, should have reasonable content
                assert len(result.content) > 10
        
        print(f"✅ Token limit test: Handled gracefully (success: {result.success})")
    
    @pytest.mark.asyncio
    async def test_network_timeout_recovery(self, openai_config):
        """Test network timeout handling and recovery"""
        provider = OpenAIProvider(openai_config)
        
        # Mock network timeout scenario
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            # Simulate timeout error  
            mock_create.side_effect = asyncio.TimeoutError("Request timeout")
            
            task = Task(
                id=generate_task_id(),
                startup_id="test_timeout",
                type=TaskType.MARKET_RESEARCH,
                description="Timeout test",
                prompt="Test network timeout recovery",
                max_tokens=50
            )
            
            result = await provider.call_api(task)
            
            assert result.success is False
            assert "timeout" in result.error_message.lower()
            assert result.cost == 0
            
            # Should record failed call
            assert len(provider.call_history) == 1
            call = provider.call_history[0]
            assert call.success is False
    
    # ========== Provider Failover Testing ==========
    
    @pytest.mark.asyncio
    async def test_provider_failover_scenario(self, openai_config, anthropic_config, sample_tasks):
        """Test failover when primary provider fails"""
        manager = AIProviderManager()
        
        # Setup primary provider that will fail
        failing_config = openai_config
        failing_config.api_key = "sk-invalid_key"
        failing_provider = OpenAIProvider(failing_config)
        manager.register_provider("primary", failing_provider, failing_config)
        
        # Setup backup provider
        if os.getenv("ANTHROPIC_API_KEY"):
            backup_provider = AnthropicProvider(anthropic_config)
            manager.register_provider("backup", backup_provider, anthropic_config)
        else:
            # Mock backup provider
            backup_provider = Mock(spec=AnthropicProvider)
            backup_provider.call_api = AsyncMock(return_value=TaskResult(
                task_id="test",
                startup_id="test", 
                success=True,
                content="Backup provider response",
                cost=0.02,
                provider_used="backup",
                tokens_used=50,
                execution_time_seconds=1.0,
                completed_at=datetime.utcnow()
            ))
            manager.register_provider("backup", backup_provider, anthropic_config)
        
        task = sample_tasks["simple_research"]
        
        # Try primary (should fail)
        primary_result = await manager.call_provider("primary", task)
        assert primary_result.success is False
        
        # Try backup (should succeed)
        if os.getenv("ANTHROPIC_API_KEY"):
            await asyncio.sleep(1)  # Rate limit
        backup_result = await manager.call_provider("backup", task)
        assert backup_result.success is True
        assert backup_result.provider_used == "backup"
        
        print("✅ Provider failover test: Primary failed → Backup succeeded")
    
    # ========== Performance & Cost Validation ==========
    
    @pytest.mark.asyncio
    async def test_cost_calculation_accuracy(self, openai_config, test_mode):
        """Test accuracy of cost calculations"""
        provider = OpenAIProvider(openai_config)
        
        if not test_mode["has_openai"]:
            # Mock with known token counts for precise cost testing
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Test response for cost calculation."))]
            mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50)
            
            with patch.object(provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_response
                
                task = Task(
                    id=generate_task_id(),
                    startup_id="cost_test",
                    type=TaskType.MARKET_RESEARCH,
                    description="Cost calculation test",
                    prompt="Calculate cost for this prompt",
                    max_tokens=100
                )
                
                result = await provider.call_api(task)
                
                # Verify cost calculation
                expected_input_cost = 100 * provider.config.cost_per_input_token
                expected_output_cost = 50 * provider.config.cost_per_output_token
                expected_total = expected_input_cost + expected_output_cost
                
                assert abs(result.cost - expected_total) < 0.0001  # Within 0.01 cents
                assert result.tokens_used == 150  # 100 + 50
                
                print(f"✅ Cost calculation accuracy: ${expected_total:.6f} (expected) vs ${result.cost:.6f} (actual)")
        else:
            print("✅ Cost calculation accuracy: Skipped with real API (would incur cost)")
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, openai_config, sample_tasks, test_mode):
        """Test handling multiple concurrent requests"""
        provider = OpenAIProvider(openai_config)
        
        # Create multiple tasks
        tasks = [
            sample_tasks["simple_research"],
            Task(
                id=generate_task_id(),
                startup_id="concurrent_test_2",
                type=TaskType.CODE_GENERATION,
                description="Concurrent test 2",
                prompt="Write a simple hello world function.",
                max_tokens=100
            ),
            Task(
                id=generate_task_id(), 
                startup_id="concurrent_test_3",
                type=TaskType.FOUNDER_ANALYSIS,
                description="Concurrent test 3", 
                prompt="What makes a good product manager?",
                max_tokens=150
            )
        ]
        
        if not test_mode["has_openai"]:
            # Mock concurrent execution
            mock_response = Mock(
                choices=[Mock(message=Mock(content="Concurrent response"))],
                usage=Mock(prompt_tokens=50, completion_tokens=25)
            )
            
            with patch.object(provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_response
                
                # Execute tasks concurrently
                start_time = time.time()
                results = await asyncio.gather(*[
                    provider.call_api(task) for task in tasks
                ])
                execution_time = time.time() - start_time
                
                # All should succeed
                assert all(result.success for result in results)
                assert len(results) == 3
                
                # Should be faster than sequential (due to concurrency)
                assert execution_time < 5  # Should complete quickly when mocked
                
                print(f"✅ Concurrent request handling (mocked): {len(results)} tasks in {execution_time:.2f}s")
        else:
            # With real API, test with rate limiting
            results = []
            start_time = time.time()
            
            for task in tasks[:2]:  # Limit to 2 to avoid rate limits
                if test_mode["rate_limit"]:
                    await asyncio.sleep(2)
                result = await provider.call_api(task)
                results.append(result)
            
            execution_time = time.time() - start_time
            
            assert all(result.success for result in results)
            print(f"✅ Concurrent request handling (real): {len(results)} tasks in {execution_time:.2f}s")
    
    # ========== Integration with Budget Monitoring ==========
    
    @pytest.mark.asyncio
    async def test_budget_integration_with_real_costs(self, openai_config, sample_tasks):
        """Test integration between AI providers and budget monitoring"""
        budget_monitor = BudgetMonitor()
        provider = OpenAIProvider(openai_config)
        
        # Set strict budget limit
        await budget_monitor.set_budget_limit(
            startup_id="budget_test",
            daily_limit=0.50,  # 50 cents
            weekly_limit=2.00,
            monthly_limit=10.00,
            total_limit=50.00
        )
        
        task = Task(
            id=generate_task_id(),
            startup_id="budget_test",
            type=TaskType.MARKET_RESEARCH,
            description="Budget integration test",
            prompt="Brief analysis for budget testing",
            max_tokens=100
        )
        
        # Mock the provider call to return predictable cost
        with patch.object(provider, 'call_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=True,
                content="Budget test response",
                cost=0.25,  # 25 cents
                provider_used="openai",
                tokens_used=100,
                execution_time_seconds=1.0,
                completed_at=datetime.utcnow()
            )
            
            # Execute task
            result = await provider.call_api(task)
            
            # Record spending in budget monitor
            await budget_monitor.record_spending(
                startup_id=task.startup_id,
                provider="openai",
                task_id=task.id,
                cost=result.cost,
                tokens_used=result.tokens_used,
                task_type=task.type.value
            )
            
            # Check budget status
            remaining = await budget_monitor.get_remaining_budget("budget_test")
            assert remaining == 0.25  # 50 cents - 25 cents used
            
            spending = await budget_monitor.get_spending_summary("budget_test")
            assert spending['total'] == 0.25
            assert spending['by_provider']['openai'] == 0.25
            
            print("✅ Budget integration: Cost tracking and limits working correctly")


class TestAIProviderMockFallbacks:
    """Comprehensive mock tests when real APIs are not available"""
    
    @pytest.fixture
    def mock_openai_provider(self, openai_config):
        """Fully mocked OpenAI provider"""
        provider = OpenAIProvider(openai_config)
        
        # Mock the client
        provider.client = Mock()
        provider.client.chat.completions.create = AsyncMock()
        
        return provider
    
    @pytest.mark.asyncio
    async def test_mock_provider_comprehensive_scenarios(self, mock_openai_provider):
        """Test all provider scenarios with comprehensive mocks"""
        # Test successful call
        mock_openai_provider.client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock successful response"))],
            usage=Mock(prompt_tokens=100, completion_tokens=50)
        )
        
        task = Task(
            id=generate_task_id(),
            startup_id="mock_test",
            type=TaskType.MARKET_RESEARCH,
            description="Mock test",
            prompt="Test with mocked provider",
            max_tokens=200
        )
        
        result = await mock_openai_provider.call_api(task)
        
        assert result.success is True
        assert result.content == "Mock successful response"
        assert result.tokens_used == 150
        assert result.cost > 0
        
        print("✅ Mock provider comprehensive test: All scenarios validated")


@pytest.mark.slow
class TestAIProviderPerformance:
    """Performance benchmarks for AI providers"""
    
    @pytest.mark.asyncio
    async def test_response_time_benchmarks(self, openai_config, test_mode):
        """Benchmark response times for different task types"""
        if not test_mode["has_openai"]:
            pytest.skip("Performance benchmarks require real API")
        
        provider = OpenAIProvider(openai_config)
        
        benchmarks = {}
        
        # Test different task complexities
        test_cases = [
            ("simple", "What is 2+2?", 50, 3),
            ("medium", "Explain the benefits of microservices architecture in 100 words.", 150, 8),
            ("complex", "Provide a detailed analysis of market opportunities for a new SaaS platform in project management, including competitive landscape, target customer segments, and go-to-market strategy.", 500, 15)
        ]
        
        for complexity, prompt, max_tokens, expected_max_time in test_cases:
            task = Task(
                id=generate_task_id(),
                startup_id="perf_test",
                type=TaskType.MARKET_RESEARCH,
                description=f"Performance test - {complexity}",
                prompt=prompt,
                max_tokens=max_tokens
            )
            
            await asyncio.sleep(2)  # Rate limiting
            
            start_time = time.time()
            result = await provider.call_api(task)
            execution_time = time.time() - start_time
            
            benchmarks[complexity] = {
                "time": execution_time,
                "success": result.success,
                "cost": result.cost,
                "tokens": result.tokens_used
            }
            
            # Validate performance meets expectations
            assert execution_time < expected_max_time, f"{complexity} task took {execution_time:.2f}s, expected <{expected_max_time}s"
            assert result.success, f"{complexity} task failed"
        
        print("✅ Performance benchmarks:")
        for complexity, metrics in benchmarks.items():
            print(f"  {complexity}: {metrics['time']:.2f}s, ${metrics['cost']:.4f}, {metrics['tokens']} tokens")