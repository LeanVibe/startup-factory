#!/usr/bin/env python3
"""
AI Orchestration Service - Core Service 6/8
Consolidates: ai_providers.py, queue_processor.py, enhanced_mvp_orchestrator.py (AI parts)
Handles multi-provider AI coordination, intelligent routing, and quality scoring.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import aiohttp

try:
    import anthropic
    import openai
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install anthropic openai rich aiohttp")
    exit(1)

console = Console()
logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    PERPLEXITY = "perplexity"
    LOCAL = "local"


class TaskType(str, Enum):
    """Types of AI tasks"""
    CONVERSATION = "conversation"
    CODE_GENERATION = "code_generation"
    MARKET_RESEARCH = "market_research"
    BUSINESS_ANALYSIS = "business_analysis"
    TECHNICAL_REVIEW = "technical_review"
    DOCUMENTATION = "documentation"


class TaskPriority(int, Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class AITask:
    """AI task definition"""
    task_id: str
    task_type: TaskType
    priority: TaskPriority
    prompt: str
    context: Dict[str, Any]
    max_tokens: int = 4000
    temperature: float = 0.7
    timeout: int = 120
    retry_count: int = 0
    max_retries: int = 3
    
    # Task metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    assigned_provider: Optional[AIProvider] = None
    estimated_cost: float = 0.0


@dataclass
class AITaskResult:
    """Result from AI task execution"""
    task_id: str
    success: bool
    provider: AIProvider
    response: str
    execution_time: float
    cost: float
    quality_score: float
    
    # Metadata
    completed_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    token_usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class ProviderMetrics:
    """Performance metrics for AI providers"""
    provider: AIProvider
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    average_quality_score: float = 0.0
    total_cost: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def cost_per_request(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_cost / self.total_requests


class AIOrchestrationService:
    """
    AI orchestration service for multi-provider coordination and intelligent routing.
    Consolidates ai_providers.py, queue_processor.py, and AI orchestration logic.
    """
    
    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys
        self.providers: Dict[AIProvider, Any] = {}
        self.provider_metrics: Dict[AIProvider, ProviderMetrics] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, AITask] = {}
        self.completed_tasks: Dict[str, AITaskResult] = {}
        
        # Initialize providers
        self._initialize_providers()
        
        # Provider routing rules
        self.provider_routing = {
            TaskType.CONVERSATION: [AIProvider.ANTHROPIC, AIProvider.OPENAI],
            TaskType.CODE_GENERATION: [AIProvider.ANTHROPIC, AIProvider.OPENAI], 
            TaskType.MARKET_RESEARCH: [AIProvider.PERPLEXITY, AIProvider.ANTHROPIC],
            TaskType.BUSINESS_ANALYSIS: [AIProvider.ANTHROPIC, AIProvider.OPENAI],
            TaskType.TECHNICAL_REVIEW: [AIProvider.ANTHROPIC, AIProvider.OPENAI],
            TaskType.DOCUMENTATION: [AIProvider.ANTHROPIC, AIProvider.OPENAI]
        }
        
        # Cost per token (approximate)
        self.provider_costs = {
            AIProvider.ANTHROPIC: {"input": 0.008, "output": 0.024},  # per 1K tokens
            AIProvider.OPENAI: {"input": 0.005, "output": 0.015},
            AIProvider.PERPLEXITY: {"input": 0.002, "output": 0.002}
        }
        
        # Start task processor
        self._start_task_processor()
    
    def _initialize_providers(self):
        """Initialize AI provider clients"""
        
        # Initialize Anthropic
        if self.api_keys.get("anthropic"):
            try:
                self.providers[AIProvider.ANTHROPIC] = anthropic.Anthropic(
                    api_key=self.api_keys["anthropic"]
                )
                self.provider_metrics[AIProvider.ANTHROPIC] = ProviderMetrics(AIProvider.ANTHROPIC)
                logger.info("✅ Anthropic provider initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Anthropic: {e}")
        
        # Initialize OpenAI
        if self.api_keys.get("openai"):
            try:
                self.providers[AIProvider.OPENAI] = openai.AsyncOpenAI(
                    api_key=self.api_keys["openai"]
                )
                self.provider_metrics[AIProvider.OPENAI] = ProviderMetrics(AIProvider.OPENAI)
                logger.info("✅ OpenAI provider initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI: {e}")
        
        # Initialize Perplexity
        if self.api_keys.get("perplexity"):
            try:
                self.providers[AIProvider.PERPLEXITY] = openai.AsyncOpenAI(
                    api_key=self.api_keys["perplexity"],
                    base_url="https://api.perplexity.ai"
                )
                self.provider_metrics[AIProvider.PERPLEXITY] = ProviderMetrics(AIProvider.PERPLEXITY)
                logger.info("✅ Perplexity provider initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Perplexity: {e}")
    
    async def submit_task(self, task: AITask) -> str:
        """Submit an AI task to the queue"""
        
        # Assign optimal provider
        optimal_provider = await self._select_optimal_provider(task)
        task.assigned_provider = optimal_provider
        
        # Estimate cost
        task.estimated_cost = self._estimate_task_cost(task, optimal_provider)
        
        # Add to queue
        await self.task_queue.put(task)
        self.active_tasks[task.task_id] = task
        
        console.print(f"📝 Task queued: {task.task_id[:8]} → {optimal_provider.value}")
        
        return task.task_id
    
    async def _select_optimal_provider(self, task: AITask) -> AIProvider:
        """Select optimal AI provider based on task type and performance metrics"""
        
        # Get eligible providers for task type
        eligible_providers = self.provider_routing.get(task.task_type, list(self.providers.keys()))
        
        # Filter to available providers
        available_providers = [p for p in eligible_providers if p in self.providers]
        
        if not available_providers:
            raise Exception(f"No available providers for task type {task.task_type}")
        
        # Score providers based on multiple factors
        provider_scores = {}
        
        for provider in available_providers:
            metrics = self.provider_metrics[provider]
            
            # Scoring factors
            success_rate_score = metrics.success_rate * 40  # 40% weight
            speed_score = (1 / max(metrics.average_response_time, 0.1)) * 30  # 30% weight (inverse)
            quality_score = metrics.average_quality_score * 20  # 20% weight
            cost_score = (1 / max(metrics.cost_per_request, 0.001)) * 10  # 10% weight (inverse)
            
            total_score = success_rate_score + speed_score + quality_score + cost_score
            provider_scores[provider] = total_score
        
        # Select provider with highest score
        optimal_provider = max(provider_scores.items(), key=lambda x: x[1])[0]
        
        return optimal_provider
    
    def _estimate_task_cost(self, task: AITask, provider: AIProvider) -> float:
        """Estimate cost for a task"""
        
        # Rough token estimation (4 chars = 1 token)
        estimated_input_tokens = len(task.prompt) / 4
        estimated_output_tokens = task.max_tokens
        
        costs = self.provider_costs.get(provider, {"input": 0.01, "output": 0.01})
        
        input_cost = (estimated_input_tokens / 1000) * costs["input"]
        output_cost = (estimated_output_tokens / 1000) * costs["output"]
        
        return input_cost + output_cost
    
    def _start_task_processor(self):
        """Start background task processor"""
        
        async def process_tasks():
            while True:
                try:
                    # Get task from queue (wait up to 1 second)
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                    
                    # Process task
                    asyncio.create_task(self._process_single_task(task))
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Task processor error: {e}")
        
        # Start processor in background
        asyncio.create_task(process_tasks())
    
    async def _process_single_task(self, task: AITask):
        """Process a single AI task"""
        
        start_time = time.time()
        provider = task.assigned_provider
        
        try:
            # Execute task with provider
            if provider == AIProvider.ANTHROPIC:
                response = await self._execute_anthropic_task(task)
            elif provider == AIProvider.OPENAI:
                response = await self._execute_openai_task(task)
            elif provider == AIProvider.PERPLEXITY:
                response = await self._execute_perplexity_task(task)
            else:
                raise Exception(f"Unknown provider: {provider}")
            
            execution_time = time.time() - start_time
            
            # Calculate quality score
            quality_score = await self._calculate_quality_score(task, response)
            
            # Calculate actual cost
            actual_cost = self._calculate_actual_cost(task, response, provider)
            
            # Create result
            result = AITaskResult(
                task_id=task.task_id,
                success=True,
                provider=provider,
                response=response["content"],
                execution_time=execution_time,
                cost=actual_cost,
                quality_score=quality_score,
                token_usage=response.get("token_usage", {})
            )
            
            # Update metrics
            await self._update_provider_metrics(provider, result)
            
            # Store result
            self.completed_tasks[task.task_id] = result
            
            # Remove from active tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            
            console.print(f"✅ Task completed: {task.task_id[:8]} ({execution_time:.1f}s, ${actual_cost:.4f})")
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Create failed result
            result = AITaskResult(
                task_id=task.task_id,
                success=False,
                provider=provider,
                response="",
                execution_time=execution_time,
                cost=0.0,
                quality_score=0.0,
                error=str(e)
            )
            
            # Update metrics
            await self._update_provider_metrics(provider, result)
            
            # Store result
            self.completed_tasks[task.task_id] = result
            
            # Remove from active tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            
            # Retry if possible
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                console.print(f"🔄 Retrying task: {task.task_id[:8]} (attempt {task.retry_count + 1})")
                await self.task_queue.put(task)
                self.active_tasks[task.task_id] = task
            else:
                logger.error(f"❌ Task failed: {task.task_id[:8]} - {e}")
    
    async def _execute_anthropic_task(self, task: AITask) -> Dict[str, Any]:
        """Execute task using Anthropic Claude"""
        
        client = self.providers[AIProvider.ANTHROPIC]
        
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-3-5-sonnet-20241022",
            max_tokens=task.max_tokens,
            temperature=task.temperature,
            messages=[{"role": "user", "content": task.prompt}]
        )
        
        return {
            "content": response.content[0].text,
            "token_usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }
    
    async def _execute_openai_task(self, task: AITask) -> Dict[str, Any]:
        """Execute task using OpenAI GPT"""
        
        client = self.providers[AIProvider.OPENAI]
        
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": task.prompt}],
            max_tokens=task.max_tokens,
            temperature=task.temperature
        )
        
        return {
            "content": response.choices[0].message.content,
            "token_usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            }
        }
    
    async def _execute_perplexity_task(self, task: AITask) -> Dict[str, Any]:
        """Execute task using Perplexity"""
        
        client = self.providers[AIProvider.PERPLEXITY]
        
        response = await client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-online",
            messages=[{"role": "user", "content": task.prompt}],
            max_tokens=task.max_tokens,
            temperature=task.temperature
        )
        
        return {
            "content": response.choices[0].message.content,
            "token_usage": {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0
            }
        }
    
    async def _calculate_quality_score(self, task: AITask, response: Dict[str, Any]) -> float:
        """Calculate quality score for a response"""
        
        content = response["content"]
        
        # Basic quality scoring factors
        length_score = min(len(content) / 1000, 1.0) * 20  # Length factor (max 20 points)
        coherence_score = 40  # Placeholder - would use NLP analysis in production
        relevance_score = 30   # Placeholder - would compare to task context
        completeness_score = 10  # Placeholder - would check if task fully addressed
        
        # Adjust based on task type
        if task.task_type == TaskType.CODE_GENERATION:
            # Check for code quality indicators
            if "def " in content or "class " in content or "function" in content:
                coherence_score += 10
            if "import" in content:
                completeness_score += 5
        
        total_score = length_score + coherence_score + relevance_score + completeness_score
        return min(total_score, 100.0)  # Cap at 100
    
    def _calculate_actual_cost(self, task: AITask, response: Dict[str, Any], provider: AIProvider) -> float:
        """Calculate actual cost based on token usage"""
        
        token_usage = response.get("token_usage", {})
        input_tokens = token_usage.get("input_tokens", 0)
        output_tokens = token_usage.get("output_tokens", 0)
        
        costs = self.provider_costs.get(provider, {"input": 0.01, "output": 0.01})
        
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        
        return input_cost + output_cost
    
    async def _update_provider_metrics(self, provider: AIProvider, result: AITaskResult):
        """Update performance metrics for a provider"""
        
        metrics = self.provider_metrics[provider]
        
        # Update counters
        metrics.total_requests += 1
        if result.success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
        
        # Update averages
        if result.success:
            # Update response time (exponential moving average)
            if metrics.average_response_time == 0:
                metrics.average_response_time = result.execution_time
            else:
                metrics.average_response_time = (
                    metrics.average_response_time * 0.8 + result.execution_time * 0.2
                )
            
            # Update quality score
            if metrics.average_quality_score == 0:
                metrics.average_quality_score = result.quality_score
            else:
                metrics.average_quality_score = (
                    metrics.average_quality_score * 0.8 + result.quality_score * 0.2
                )
        
        # Update cost
        metrics.total_cost += result.cost
        metrics.last_updated = datetime.utcnow()
    
    async def get_task_result(self, task_id: str, timeout: int = 300) -> Optional[AITaskResult]:
        """Get result for a task (wait for completion if necessary)"""
        
        # Check if already completed
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        
        # Wait for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
            await asyncio.sleep(0.5)
        
        return None  # Timeout
    
    def get_provider_metrics(self) -> Dict[AIProvider, Dict[str, Any]]:
        """Get performance metrics for all providers"""
        
        metrics_data = {}
        
        for provider, metrics in self.provider_metrics.items():
            metrics_data[provider] = {
                "total_requests": metrics.total_requests,
                "success_rate": metrics.success_rate,
                "average_response_time": metrics.average_response_time,
                "average_quality_score": metrics.average_quality_score,
                "total_cost": metrics.total_cost,
                "cost_per_request": metrics.cost_per_request,
                "last_updated": metrics.last_updated.isoformat()
            }
        
        return metrics_data
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        
        return {
            "queued_tasks": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "total_tasks_processed": len(self.completed_tasks)
        }
    
    async def batch_process_tasks(self, tasks: List[AITask], max_concurrent: int = 5) -> List[AITaskResult]:
        """Process multiple tasks concurrently"""
        
        # Submit all tasks
        task_ids = []
        for task in tasks:
            task_id = await self.submit_task(task)
            task_ids.append(task_id)
        
        # Wait for all results
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def wait_for_result(task_id):
            async with semaphore:
                result = await self.get_task_result(task_id)
                return result
        
        # Gather all results
        result_tasks = [wait_for_result(task_id) for task_id in task_ids]
        results = await asyncio.gather(*result_tasks)
        
        return [r for r in results if r is not None]


# Example usage
async def main():
    """Example usage of AIOrchestrationService"""
    
    # Initialize service with API keys
    api_keys = {
        "anthropic": "your-anthropic-key",
        "openai": "your-openai-key",
        "perplexity": "your-perplexity-key"
    }
    
    ai_orchestrator = AIOrchestrationService(api_keys)
    
    # Create sample tasks
    tasks = [
        AITask(
            task_id="task_1",
            task_type=TaskType.CONVERSATION,
            priority=TaskPriority.HIGH,
            prompt="Help me brainstorm features for a healthcare startup"
        ),
        AITask(
            task_id="task_2",
            task_type=TaskType.CODE_GENERATION,
            priority=TaskPriority.MEDIUM,
            prompt="Generate a Python FastAPI endpoint for user registration"
        )
    ]
    
    # Process tasks
    results = await ai_orchestrator.batch_process_tasks(tasks)
    
    # Display results
    for result in results:
        console.print(f"Task {result.task_id}: {'✅' if result.success else '❌'}")
        console.print(f"Provider: {result.provider}")
        console.print(f"Cost: ${result.cost:.4f}")
    
    # Show provider metrics
    metrics = ai_orchestrator.get_provider_metrics()
    console.print("Provider metrics:")
    console.print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())