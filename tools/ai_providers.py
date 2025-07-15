#!/usr/bin/env python3
"""
Real AI Provider Integration for Startup Factory
Integrates with actual AI provider APIs (OpenAI, Anthropic, Perplexity)
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

import openai
from anthropic import Anthropic

from core_types import Task, TaskResult, TaskType, ProviderError

logger = logging.getLogger(__name__)


@dataclass
class ProviderCall:
    """Record of a provider API call for cost tracking"""
    provider: str
    task_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float
    timestamp: datetime
    success: bool
    error: Optional[str] = None


@dataclass
class ProviderConfig:
    """Configuration for an AI provider"""
    name: str
    api_key: str
    models: Dict[str, str]
    cost_per_input_token: float
    cost_per_output_token: float
    max_tokens: int
    max_concurrent: int
    enabled: bool = True


class AIProviderInterface(ABC):
    """Abstract interface for AI providers"""
    
    @abstractmethod
    async def call_api(self, task: Task) -> TaskResult:
        """Call the provider API and return result"""
        pass
    
    @abstractmethod
    def get_model_for_task(self, task_type: TaskType) -> str:
        """Get the optimal model for a task type"""
        pass
    
    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage"""
        pass


class OpenAIProvider(AIProviderInterface):
    """OpenAI API provider implementation"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = openai.AsyncOpenAI(api_key=config.api_key)
        self.call_history: List[ProviderCall] = []
        
        # Model mapping for different task types
        self.task_models = {
            TaskType.MARKET_RESEARCH: config.models.get('research', 'gpt-4o'),
            TaskType.FOUNDER_ANALYSIS: config.models.get('analysis', 'gpt-4o'),
            TaskType.MVP_SPECIFICATION: config.models.get('specification', 'gpt-4o'),
            TaskType.ARCHITECTURE_DESIGN: config.models.get('architecture', 'gpt-4o'),
            TaskType.CODE_GENERATION: config.models.get('code', 'gpt-4o'),
            TaskType.TESTING: config.models.get('testing', 'gpt-4o'),
            TaskType.DEPLOYMENT: config.models.get('deployment', 'gpt-4o')
        }
    
    async def call_api(self, task: Task) -> TaskResult:
        """Call OpenAI API for task execution"""
        start_time = time.time()
        model = self.get_model_for_task(task.type)
        
        try:
            # Prepare the prompt with context
            system_prompt = self._get_system_prompt(task.type)
            user_prompt = self._format_prompt(task)
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=min(task.max_tokens, self.config.max_tokens),
                temperature=0.7
            )
            
            # Extract response data
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Calculate cost and timing
            cost = self.calculate_cost(input_tokens, output_tokens)
            execution_time = time.time() - start_time
            
            # Record the call
            call_record = ProviderCall(
                provider=self.config.name,
                task_id=task.id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                latency_ms=execution_time * 1000,
                timestamp=datetime.utcnow(),
                success=True
            )
            self.call_history.append(call_record)
            
            # Return successful result
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=True,
                content=content,
                cost=cost,
                provider_used=self.config.name,
                execution_time_seconds=execution_time,
                tokens_used=input_tokens + output_tokens,
                quality_score=0.85,  # Default quality score
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            # Record failed call
            call_record = ProviderCall(
                provider=self.config.name,
                task_id=task.id,
                model=model,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=execution_time * 1000,
                timestamp=datetime.utcnow(),
                success=False,
                error=error_msg
            )
            self.call_history.append(call_record)
            
            logger.error(f"OpenAI API call failed for task {task.id}: {error_msg}")
            
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=False,
                content="",
                cost=0.0,
                provider_used=self.config.name,
                execution_time_seconds=execution_time,
                completed_at=datetime.utcnow(),
                error_message=error_msg
            )
    
    def get_model_for_task(self, task_type: TaskType) -> str:
        """Get optimal model for task type"""
        return self.task_models.get(task_type, 'gpt-4o')
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage"""
        input_cost = input_tokens * self.config.cost_per_input_token
        output_cost = output_tokens * self.config.cost_per_output_token
        return input_cost + output_cost
    
    def _get_system_prompt(self, task_type: TaskType) -> str:
        """Get system prompt based on task type"""
        prompts = {
            TaskType.MARKET_RESEARCH: "You are an expert market researcher. Provide detailed, data-driven market analysis.",
            TaskType.FOUNDER_ANALYSIS: "You are an expert startup advisor. Analyze founder-market fit and provide strategic insights.",
            TaskType.MVP_SPECIFICATION: "You are a product manager. Create detailed MVP specifications with clear requirements.",
            TaskType.ARCHITECTURE_DESIGN: "You are a senior software architect. Design scalable, secure system architectures.",
            TaskType.CODE_GENERATION: "You are an expert software engineer. Write clean, efficient, well-documented code.",
            TaskType.TESTING: "You are a QA engineer. Create comprehensive test suites and testing strategies.",
            TaskType.DEPLOYMENT: "You are a DevOps engineer. Design deployment pipelines and infrastructure."
        }
        return prompts.get(task_type, "You are an AI assistant helping with startup development.")
    
    def _format_prompt(self, task: Task) -> str:
        """Format the task prompt with context"""
        context_str = ""
        if task.context:
            context_str = f"\n\nContext:\n{json.dumps(task.context, indent=2)}"
        
        return f"{task.prompt}\n\nDescription: {task.description}{context_str}"


class AnthropicProvider(AIProviderInterface):
    """Anthropic Claude API provider implementation"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = Anthropic(api_key=config.api_key)
        self.call_history: List[ProviderCall] = []
        
        # Model mapping for different task types
        self.task_models = {
            TaskType.MARKET_RESEARCH: config.models.get('research', 'claude-3-5-sonnet-20241022'),
            TaskType.FOUNDER_ANALYSIS: config.models.get('analysis', 'claude-3-5-sonnet-20241022'),
            TaskType.MVP_SPECIFICATION: config.models.get('specification', 'claude-3-5-sonnet-20241022'),
            TaskType.ARCHITECTURE_DESIGN: config.models.get('architecture', 'claude-3-5-sonnet-20241022'),
            TaskType.CODE_GENERATION: config.models.get('code', 'claude-3-5-sonnet-20241022'),
            TaskType.TESTING: config.models.get('testing', 'claude-3-5-sonnet-20241022'),
            TaskType.DEPLOYMENT: config.models.get('deployment', 'claude-3-5-sonnet-20241022')
        }
    
    async def call_api(self, task: Task) -> TaskResult:
        """Call Anthropic API for task execution"""
        start_time = time.time()
        model = self.get_model_for_task(task.type)
        
        try:
            # Prepare the prompt
            prompt = self._format_prompt(task)
            
            # Make API call (using sync client in async wrapper)
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.client.messages.create(
                    model=model,
                    max_tokens=min(task.max_tokens, self.config.max_tokens),
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            
            # Extract response data
            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            # Calculate cost and timing
            cost = self.calculate_cost(input_tokens, output_tokens)
            execution_time = time.time() - start_time
            
            # Record the call
            call_record = ProviderCall(
                provider=self.config.name,
                task_id=task.id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                latency_ms=execution_time * 1000,
                timestamp=datetime.utcnow(),
                success=True
            )
            self.call_history.append(call_record)
            
            # Return successful result
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=True,
                content=content,
                cost=cost,
                provider_used=self.config.name,
                execution_time_seconds=execution_time,
                tokens_used=input_tokens + output_tokens,
                quality_score=0.90,  # Claude typically produces high-quality output
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            # Record failed call
            call_record = ProviderCall(
                provider=self.config.name,
                task_id=task.id,
                model=model,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=execution_time * 1000,
                timestamp=datetime.utcnow(),
                success=False,
                error=error_msg
            )
            self.call_history.append(call_record)
            
            logger.error(f"Anthropic API call failed for task {task.id}: {error_msg}")
            
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=False,
                content="",
                cost=0.0,
                provider_used=self.config.name,
                execution_time_seconds=execution_time,
                completed_at=datetime.utcnow(),
                error_message=error_msg
            )
    
    def get_model_for_task(self, task_type: TaskType) -> str:
        """Get optimal model for task type"""
        return self.task_models.get(task_type, 'claude-3-5-sonnet-20241022')
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage"""
        input_cost = input_tokens * self.config.cost_per_input_token
        output_cost = output_tokens * self.config.cost_per_output_token
        return input_cost + output_cost
    
    def _format_prompt(self, task: Task) -> str:
        """Format the task prompt with context"""
        context_str = ""
        if task.context:
            context_str = f"\n\nContext:\n{json.dumps(task.context, indent=2)}"
        
        return f"{task.description}\n\n{task.prompt}{context_str}"


class OpenCodeCLIProvider(AIProviderInterface):
    """OpenCode CLI provider implementation"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.call_history: List[ProviderCall] = []
        self.cli_path = config.models.get('cli_path', '/Users/bogdan/.opencode/bin/opencode')
    
    async def call_api(self, task: Task) -> TaskResult:
        """Call OpenCode CLI for task execution"""
        start_time = time.time()
        
        try:
            # Prepare the prompt
            prompt = self._format_prompt(task)
            
            # Create temporary file for prompt
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name
            
            try:
                # Execute OpenCode CLI
                cmd = [
                    self.cli_path,
                    '--prompt-file', prompt_file,
                    '--model', self.get_model_for_task(task.type),
                    '--max-tokens', str(min(task.max_tokens, self.config.max_tokens)),
                    '--json'
                ]
                
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    # Parse JSON response
                    response_data = json.loads(stdout.decode())
                    content = response_data.get('content', '')
                    
                    # Estimate tokens and cost (since CLI might not provide exact numbers)
                    estimated_input_tokens = len(prompt) // 4  # Rough estimation
                    estimated_output_tokens = len(content) // 4  # Rough estimation
                    cost = self.calculate_cost(estimated_input_tokens, estimated_output_tokens)
                    
                    execution_time = time.time() - start_time
                    
                    # Record the call
                    call_record = ProviderCall(
                        provider=self.config.name,
                        task_id=task.id,
                        model=self.get_model_for_task(task.type),
                        input_tokens=estimated_input_tokens,
                        output_tokens=estimated_output_tokens,
                        cost=cost,
                        latency_ms=execution_time * 1000,
                        timestamp=datetime.utcnow(),
                        success=True
                    )
                    self.call_history.append(call_record)
                    
                    return TaskResult(
                        task_id=task.id,
                        startup_id=task.startup_id,
                        success=True,
                        content=content,
                        cost=cost,
                        provider_used=self.config.name,
                        execution_time_seconds=execution_time,
                        tokens_used=estimated_input_tokens + estimated_output_tokens,
                        quality_score=0.80,
                        completed_at=datetime.utcnow()
                    )
                else:
                    raise Exception(f"CLI failed with code {result.returncode}: {stderr.decode()}")
                    
            finally:
                # Clean up temporary file
                os.unlink(prompt_file)
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            # Record failed call
            call_record = ProviderCall(
                provider=self.config.name,
                task_id=task.id,
                model=self.get_model_for_task(task.type),
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=execution_time * 1000,
                timestamp=datetime.utcnow(),
                success=False,
                error=error_msg
            )
            self.call_history.append(call_record)
            
            logger.error(f"OpenCode CLI call failed for task {task.id}: {error_msg}")
            
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=False,
                content="",
                cost=0.0,
                provider_used=self.config.name,
                execution_time_seconds=execution_time,
                completed_at=datetime.utcnow(),
                error_message=error_msg
            )
    
    def get_model_for_task(self, task_type: TaskType) -> str:
        """Get optimal model for task type"""
        # OpenCode typically uses GPT models
        return self.config.models.get(task_type.value, 'gpt-4o')
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost based on token usage"""
        input_cost = input_tokens * self.config.cost_per_input_token
        output_cost = output_tokens * self.config.cost_per_output_token
        return input_cost + output_cost
    
    def _format_prompt(self, task: Task) -> str:
        """Format the task prompt with context"""
        context_str = ""
        if task.context:
            context_str = f"\n\nContext:\n{json.dumps(task.context, indent=2)}"
        
        return f"Task: {task.description}\n\n{task.prompt}{context_str}"


class AIProviderManager:
    """Manages multiple AI providers with load balancing and failover"""
    
    def __init__(self):
        self.providers: Dict[str, AIProviderInterface] = {}
        self.configurations: Dict[str, ProviderConfig] = {}
        self.all_calls: List[ProviderCall] = []
        
    def register_provider(self, provider_name: str, provider: AIProviderInterface, config: ProviderConfig):
        """Register an AI provider"""
        self.providers[provider_name] = provider
        self.configurations[provider_name] = config
        logger.info(f"Registered AI provider: {provider_name}")
    
    def get_provider(self, provider_name: str) -> Optional[AIProviderInterface]:
        """Get a provider by name"""
        return self.providers.get(provider_name)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [name for name, config in self.configurations.items() if config.enabled]
    
    async def call_provider(self, provider_name: str, task: Task) -> TaskResult:
        """Call a specific provider"""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ProviderError(f"Provider '{provider_name}' not found")
        
        config = self.configurations[provider_name]
        if not config.enabled:
            raise ProviderError(f"Provider '{provider_name}' is disabled")
        
        result = await provider.call_api(task)
        
        # Record the call in global history
        if hasattr(provider, 'call_history') and provider.call_history:
            self.all_calls.extend(provider.call_history[-1:])  # Add the latest call
        
        return result
    
    def get_cost_statistics(self) -> Dict[str, Any]:
        """Get cost statistics across all providers"""
        stats = {
            'total_calls': len(self.all_calls),
            'total_cost': sum(call.cost for call in self.all_calls),
            'successful_calls': sum(1 for call in self.all_calls if call.success),
            'failed_calls': sum(1 for call in self.all_calls if not call.success),
            'average_latency_ms': sum(call.latency_ms for call in self.all_calls) / max(1, len(self.all_calls)),
            'providers': {}
        }
        
        # Per-provider statistics
        for provider_name in self.providers.keys():
            provider_calls = [call for call in self.all_calls if call.provider == provider_name]
            if provider_calls:
                stats['providers'][provider_name] = {
                    'calls': len(provider_calls),
                    'cost': sum(call.cost for call in provider_calls),
                    'success_rate': sum(1 for call in provider_calls if call.success) / len(provider_calls),
                    'average_latency_ms': sum(call.latency_ms for call in provider_calls) / len(provider_calls),
                    'input_tokens': sum(call.input_tokens for call in provider_calls),
                    'output_tokens': sum(call.output_tokens for call in provider_calls)
                }
        
        return stats


def create_default_provider_manager() -> AIProviderManager:
    """Create a default provider manager with common configurations"""
    manager = AIProviderManager()
    
    # OpenAI configuration
    if os.getenv('OPENAI_API_KEY'):
        openai_config = ProviderConfig(
            name='openai',
            api_key=os.getenv('OPENAI_API_KEY'),
            models={
                'code': 'gpt-4o',
                'research': 'gpt-4o',
                'analysis': 'gpt-4o',
                'specification': 'gpt-4o',
                'architecture': 'gpt-4o',
                'testing': 'gpt-4o',
                'deployment': 'gpt-4o'
            },
            cost_per_input_token=0.00001,  # $0.01 per 1K tokens for GPT-4o
            cost_per_output_token=0.00003,  # $0.03 per 1K tokens for GPT-4o
            max_tokens=4000,
            max_concurrent=10
        )
        
        openai_provider = OpenAIProvider(openai_config)
        manager.register_provider('openai', openai_provider, openai_config)
    
    # Anthropic configuration
    if os.getenv('ANTHROPIC_API_KEY'):
        anthropic_config = ProviderConfig(
            name='anthropic',
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            models={
                'research': 'claude-3-5-sonnet-20241022',
                'analysis': 'claude-3-5-sonnet-20241022',
                'specification': 'claude-3-5-sonnet-20241022',
                'architecture': 'claude-3-5-sonnet-20241022',
                'code': 'claude-3-5-sonnet-20241022',
                'testing': 'claude-3-5-sonnet-20241022',
                'deployment': 'claude-3-5-sonnet-20241022'
            },
            cost_per_input_token=0.000003,  # $3 per 1M tokens for Claude 3.5 Sonnet
            cost_per_output_token=0.000015,  # $15 per 1M tokens for Claude 3.5 Sonnet
            max_tokens=4000,
            max_concurrent=8
        )
        
        anthropic_provider = AnthropicProvider(anthropic_config)
        manager.register_provider('anthropic', anthropic_provider, anthropic_config)
    
    # OpenCode CLI configuration (if available)
    if os.path.exists('/Users/bogdan/.opencode/bin/opencode'):
        opencode_config = ProviderConfig(
            name='opencode',
            api_key=os.getenv('OPENAI_API_KEY', ''),  # OpenCode uses OpenAI API
            models={
                'cli_path': '/Users/bogdan/.opencode/bin/opencode',
                'code': 'gpt-4o',
                'research': 'gpt-4o',
                'analysis': 'gpt-4o'
            },
            cost_per_input_token=0.00001,
            cost_per_output_token=0.00003,
            max_tokens=4000,
            max_concurrent=5
        )
        
        opencode_provider = OpenCodeCLIProvider(opencode_config)
        manager.register_provider('opencode', opencode_provider, opencode_config)
    
    logger.info(f"Created provider manager with {len(manager.providers)} providers")
    return manager