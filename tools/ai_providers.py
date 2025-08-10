#!/usr/bin/env python3
"""
Reliable AI Provider Integration for Startup Factory
Production-grade AI provider integration with retry logic, circuit breakers,
fallback mechanisms, and comprehensive error handling.
"""

import asyncio
import json
import logging
import os
import random
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

import aiohttp
import openai
from anthropic import Anthropic

from core_types import Task, TaskResult, TaskType, ProviderError

logger = logging.getLogger(__name__)

# Configure more detailed logging for reliability monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests rejected
    HALF_OPEN = "half_open" # Testing if service recovered


class RetryStrategy(str, Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    backoff_multiplier: float = 2.0
    jitter: bool = True  # Add randomization to prevent thundering herd


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5  # Failures before opening circuit
    recovery_timeout: float = 60.0  # Seconds before trying half-open
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 30.0  # Request timeout in seconds


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_minute: int = 60
    requests_per_hour: int = 3600
    concurrent_requests: int = 10
    burst_allowance: int = 5  # Allow brief bursts above limit


@dataclass
class ReliabilityConfig:
    """Combined reliability configuration"""
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    enable_fallback: bool = True
    health_check_interval: float = 30.0
    metrics_enabled: bool = True


class CircuitBreaker:
    """Circuit breaker implementation for provider reliability"""
    
    def __init__(self, config: CircuitBreakerConfig, provider_name: str):
        self.config = config
        self.provider_name = provider_name
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        
    def can_execute(self) -> bool:
        """Check if request can be executed based on circuit breaker state"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            # Check if we should try half-open
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).total_seconds() > self.config.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker for {self.provider_name} transitioning to HALF_OPEN")
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful request"""
        self.last_success_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker for {self.provider_name} closed after recovery")
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed request"""
        self.last_failure_time = datetime.utcnow()
        self.failure_count += 1
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker for {self.provider_name} opened due to {self.failure_count} failures")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Failed during testing, go back to open
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            logger.warning(f"Circuit breaker for {self.provider_name} failed recovery test, back to OPEN")


class RateLimiter:
    """Token bucket rate limiter implementation"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens_per_minute = config.requests_per_minute
        self.tokens_per_hour = config.requests_per_hour
        self.max_concurrent = config.concurrent_requests
        
        # Token buckets
        self.minute_tokens = config.requests_per_minute
        self.hour_tokens = config.requests_per_hour
        self.concurrent_requests = 0
        
        # Timestamps for token replenishment
        self.last_minute_refill = datetime.utcnow()
        self.last_hour_refill = datetime.utcnow()
        
        # Semaphore for concurrent request limiting
        self.concurrent_semaphore = asyncio.Semaphore(config.concurrent_requests)
    
    async def acquire(self) -> bool:
        """Attempt to acquire tokens for request"""
        self._refill_tokens()
        
        # Check if we have tokens available
        if self.minute_tokens > 0 and self.hour_tokens > 0:
            # Acquire concurrent request slot
            await self.concurrent_semaphore.acquire()
            
            # Consume tokens
            self.minute_tokens -= 1
            self.hour_tokens -= 1
            self.concurrent_requests += 1
            
            return True
        
        return False
    
    def release(self):
        """Release a concurrent request slot"""
        if self.concurrent_requests > 0:
            self.concurrent_requests -= 1
            self.concurrent_semaphore.release()
    
    def _refill_tokens(self):
        """Refill token buckets based on elapsed time"""
        now = datetime.utcnow()
        
        # Refill minute bucket
        minute_elapsed = (now - self.last_minute_refill).total_seconds()
        if minute_elapsed >= 60.0:
            minutes_passed = minute_elapsed / 60.0
            new_tokens = min(
                self.config.requests_per_minute,
                self.minute_tokens + int(minutes_passed * self.tokens_per_minute / 60)
            )
            self.minute_tokens = new_tokens
            self.last_minute_refill = now
        
        # Refill hour bucket
        hour_elapsed = (now - self.last_hour_refill).total_seconds()
        if hour_elapsed >= 3600.0:
            hours_passed = hour_elapsed / 3600.0
            new_tokens = min(
                self.config.requests_per_hour,
                self.hour_tokens + int(hours_passed * self.tokens_per_hour / 3600)
            )
            self.hour_tokens = new_tokens
            self.last_hour_refill = now
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status"""
        self._refill_tokens()
        return {
            "minute_tokens_available": self.minute_tokens,
            "hour_tokens_available": self.hour_tokens,
            "concurrent_requests": self.concurrent_requests,
            "max_concurrent": self.max_concurrent
        }


class ReliabilityMetrics:
    """Collect and track reliability metrics"""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.circuit_breaker_opens = 0
        self.rate_limit_hits = 0
        self.retry_attempts = 0
        self.fallback_usage = 0
        self.response_times: List[float] = []
        self.error_types: Dict[str, int] = {}
        
        # Time windows for metrics
        self.metrics_window = timedelta(minutes=5)
        self.request_timestamps: List[datetime] = []
    
    def record_request(self, success: bool, response_time: float, error_type: Optional[str] = None):
        """Record a request with its outcome"""
        now = datetime.utcnow()
        self.request_timestamps.append(now)
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        
        self.response_times.append(response_time)
        
        # Keep only recent metrics
        cutoff_time = now - self.metrics_window
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > cutoff_time]
        self.response_times = self.response_times[-1000:]  # Keep last 1000 response times
    
    def get_success_rate(self) -> float:
        """Get current success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def get_average_response_time(self) -> float:
        """Get average response time"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    def get_current_rps(self) -> float:
        """Get current requests per second"""
        if len(self.request_timestamps) < 2:
            return 0.0
        
        recent_requests = len(self.request_timestamps)
        time_span = (self.request_timestamps[-1] - self.request_timestamps[0]).total_seconds()
        
        if time_span == 0:
            return 0.0
        
        return recent_requests / time_span


@dataclass
class ProviderCall:
    """Record of a provider API call for cost tracking and reliability monitoring"""
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
    retry_attempt: int = 0
    circuit_breaker_state: Optional[str] = None
    rate_limited: bool = False
    fallback_used: bool = False


@dataclass
class ProviderConfig:
    """Configuration for an AI provider with reliability settings"""
    name: str
    api_key: str
    models: Dict[str, str]
    cost_per_input_token: float
    cost_per_output_token: float
    max_tokens: int
    max_concurrent: int
    enabled: bool = True
    priority: int = 1  # Lower number = higher priority for fallbacks
    reliability: ReliabilityConfig = field(default_factory=ReliabilityConfig)
    health_check_url: Optional[str] = None
    base_url: Optional[str] = None


class AIProviderInterface(ABC):
    """Abstract interface for AI providers with reliability features"""
    
    @abstractmethod
    async def call_api(self, task: Task) -> TaskResult:
        """Call the provider API and return result"""
        pass
    
    @abstractmethod
    async def call_api_with_reliability(self, task: Task) -> TaskResult:
        """Call API with full reliability features (retry, circuit breaker, etc.)"""
        pass
    
    @abstractmethod
    def get_model_for_task(self, task_type: TaskType) -> str:
        """Get the optimal model for a task type"""
        pass
    
    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy and responsive"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get current provider metrics"""
        pass


class ReliableAIProvider(AIProviderInterface):
    """Base class for reliable AI providers with retry, circuit breaker, and fallback"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker(config.reliability.circuit_breaker, config.name)
        self.rate_limiter = RateLimiter(config.reliability.rate_limit)
        self.metrics = ReliabilityMetrics(config.name)
        self.call_history: List[ProviderCall] = []
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_health_check: Optional[datetime] = None
        self._is_healthy = True
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with connection pooling"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.reliability.circuit_breaker.timeout)
            connector = aiohttp.TCPConnector(
                limit=self.config.max_concurrent,
                limit_per_host=self.config.max_concurrent,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
        return self.session
    
    async def _retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry"""
        retry_config = self.config.reliability.retry
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                if attempt > 0:
                    # Calculate delay with exponential backoff
                    if retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
                        delay = min(
                            retry_config.base_delay * (retry_config.backoff_multiplier ** (attempt - 1)),
                            retry_config.max_delay
                        )
                    elif retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
                        delay = min(
                            retry_config.base_delay * attempt,
                            retry_config.max_delay
                        )
                    else:  # FIXED_INTERVAL
                        delay = retry_config.base_delay
                    
                    # Add jitter to prevent thundering herd
                    if retry_config.jitter:
                        delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
                    
                    logger.info(f"Retrying {self.config.name} API call in {delay:.2f}s (attempt {attempt + 1}/{retry_config.max_attempts})")
                    await asyncio.sleep(delay)
                    self.metrics.retry_attempts += 1
                
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Log successful retry recovery
                if attempt > 0:
                    logger.info(f"{self.config.name} API call succeeded after {attempt + 1} attempts")
                
                return result
                
            except Exception as e:
                last_exception = e
                error_type = type(e).__name__
                
                # Check if this is a retryable error
                if not self._is_retryable_error(e):
                    logger.warning(f"Non-retryable error for {self.config.name}: {error_type}")
                    raise e
                
                logger.warning(f"Attempt {attempt + 1} failed for {self.config.name}: {error_type}")
                
                # If this is the last attempt, raise the exception
                if attempt == retry_config.max_attempts - 1:
                    break
        
        # All retries exhausted
        logger.error(f"All {retry_config.max_attempts} retry attempts exhausted for {self.config.name}")
        raise last_exception
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable"""
        # Network-related errors are usually retryable
        retryable_errors = [
            'ConnectionError', 'TimeoutError', 'ServerDisconnectedError',
            'ClientConnectorError', 'ClientTimeout', 'asyncio.TimeoutError'
        ]
        
        error_name = type(error).__name__
        
        # Check if it's a known retryable error
        if error_name in retryable_errors:
            return True
        
        # Check for HTTP status codes that are retryable
        if hasattr(error, 'status'):
            retryable_status_codes = [429, 500, 502, 503, 504]
            if error.status in retryable_status_codes:
                return True
        
        # Check for rate limiting errors in the message
        error_msg = str(error).lower()
        rate_limit_indicators = ['rate limit', 'quota exceeded', 'too many requests']
        if any(indicator in error_msg for indicator in rate_limit_indicators):
            return True
        
        return False
    
    async def call_api_with_reliability(self, task: Task) -> TaskResult:
        """Call API with full reliability features"""
        start_time = time.time()
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            error_msg = f"Circuit breaker is OPEN for {self.config.name}"
            logger.warning(error_msg)
            self.metrics.circuit_breaker_opens += 1
            
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=False,
                content="",
                cost=0.0,
                provider_used=self.config.name,
                execution_time_seconds=time.time() - start_time,
                completed_at=datetime.utcnow(),
                error_message=error_msg
            )
        
        # Check rate limiting
        if not await self.rate_limiter.acquire():
            error_msg = f"Rate limit exceeded for {self.config.name}"
            logger.warning(error_msg)
            self.metrics.rate_limit_hits += 1
            
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=False,
                content="",
                cost=0.0,
                provider_used=self.config.name,
                execution_time_seconds=time.time() - start_time,
                completed_at=datetime.utcnow(),
                error_message=error_msg
            )
        
        try:
            # Execute with retry logic
            result = await self._retry_with_backoff(self.call_api, task)
            
            # Record success
            self.circuit_breaker.record_success()
            execution_time = time.time() - start_time
            self.metrics.record_request(True, execution_time)
            
            # Record the call
            call_record = ProviderCall(
                provider=self.config.name,
                task_id=task.id,
                model=self.get_model_for_task(task.type),
                input_tokens=result.tokens_used or 0,
                output_tokens=0,  # Will be set by individual providers
                cost=result.cost,
                latency_ms=execution_time * 1000,
                timestamp=datetime.utcnow(),
                success=True,
                circuit_breaker_state=self.circuit_breaker.state.value,
                rate_limited=False,
                fallback_used=False
            )
            self.call_history.append(call_record)
            
            return result
            
        except Exception as e:
            # Record failure
            self.circuit_breaker.record_failure()
            execution_time = time.time() - start_time
            error_type = type(e).__name__
            self.metrics.record_request(False, execution_time, error_type)
            
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
                error=str(e),
                circuit_breaker_state=self.circuit_breaker.state.value,
                rate_limited=False,
                fallback_used=False
            )
            self.call_history.append(call_record)
            
            logger.error(f"{self.config.name} API call failed: {str(e)}")
            
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=False,
                content="",
                cost=0.0,
                provider_used=self.config.name,
                execution_time_seconds=execution_time,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
            
        finally:
            # Always release rate limiter token
            self.rate_limiter.release()
    
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        if self._last_health_check and \
           (datetime.utcnow() - self._last_health_check).total_seconds() < self.config.reliability.health_check_interval:
            return self._is_healthy
        
        try:
            # Perform a lightweight health check
            if self.config.health_check_url:
                session = await self._get_session()
                async with session.get(self.config.health_check_url) as response:
                    self._is_healthy = response.status == 200
            else:
                # Default health check based on circuit breaker state
                self._is_healthy = self.circuit_breaker.state != CircuitBreakerState.OPEN
            
            self._last_health_check = datetime.utcnow()
            return self._is_healthy
            
        except Exception as e:
            logger.warning(f"Health check failed for {self.config.name}: {str(e)}")
            self._is_healthy = False
            self._last_health_check = datetime.utcnow()
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current provider metrics"""
        return {
            "provider_name": self.config.name,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "success_rate": self.metrics.get_success_rate(),
            "average_response_time": self.metrics.get_average_response_time(),
            "current_rps": self.metrics.get_current_rps(),
            "total_requests": self.metrics.total_requests,
            "failed_requests": self.metrics.failed_requests,
            "circuit_breaker_opens": self.metrics.circuit_breaker_opens,
            "rate_limit_hits": self.metrics.rate_limit_hits,
            "retry_attempts": self.metrics.retry_attempts,
            "fallback_usage": self.metrics.fallback_usage,
            "rate_limiter_status": self.rate_limiter.get_status(),
            "is_healthy": self._is_healthy,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "error_types": self.metrics.error_types
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close()


class OpenAIProvider(ReliableAIProvider):
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
    
    async def call_api_with_reliability(self, task: Task) -> TaskResult:
        """Call API with basic reliability (AnthropicProvider doesn't have circuit breaker yet)"""
        return await self.call_api(task)
    
    async def health_check(self) -> bool:
        """Check if Anthropic provider is healthy"""
        try:
            # Create a simple test task
            test_task = Task(
                id="health-check",
                startup_id="health-check",
                type=TaskType.MARKET_RESEARCH,
                prompt="Say 'OK' if you're working correctly.",
                description="Health check",
                max_tokens=10
            )
            result = await self.call_api(test_task)
            return result.success
        except Exception as e:
            logger.error(f"Anthropic health check failed: {str(e)}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current provider metrics"""
        if not self.call_history:
            return {
                "total_calls": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "total_cost": 0.0,
                "avg_tokens": 0.0
            }
        
        successful_calls = [call for call in self.call_history if call.success]
        total_calls = len(self.call_history)
        success_rate = len(successful_calls) / total_calls if total_calls > 0 else 0.0
        
        return {
            "total_calls": total_calls,
            "success_rate": success_rate,
            "avg_latency_ms": sum(call.latency_ms for call in self.call_history) / total_calls,
            "total_cost": sum(call.cost for call in self.call_history),
            "avg_tokens": sum(call.input_tokens + call.output_tokens for call in self.call_history) / total_calls
        }


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
    
    async def process_task(self, task: Task, preferred_provider: str = None) -> TaskResult:
        """Process a task by routing to the best available provider"""
        # Define task type to provider mapping
        task_provider_mapping = {
            TaskType.MARKET_RESEARCH: "perplexity",
            TaskType.FOUNDER_ANALYSIS: "anthropic", 
            TaskType.MVP_SPECIFICATION: "anthropic",
            TaskType.ARCHITECTURE_DESIGN: "anthropic",
            TaskType.CODE_GENERATION: "openai",
            TaskType.TESTING: "openai",
            TaskType.DEPLOYMENT: "anthropic"
        }
        
        # Use preferred provider if specified, otherwise use task mapping
        target_provider = preferred_provider or task_provider_mapping.get(task.type, "openai")
        
        # Try primary provider first
        try:
            if target_provider in self.providers and self.configurations[target_provider].enabled:
                return await self.call_provider(target_provider, task)
        except Exception as e:
            logger.warning(f"Primary provider {target_provider} failed: {str(e)}")
        
        # Fallback to any available provider
        for provider_name, config in self.configurations.items():
            if config.enabled and provider_name != target_provider:
                try:
                    logger.info(f"Falling back to provider: {provider_name}")
                    return await self.call_provider(provider_name, task)
                except Exception as e:
                    logger.warning(f"Fallback provider {provider_name} failed: {str(e)}")
                    continue
        
        # If all providers fail, return error result
        return TaskResult(
            task_id=task.id,
            startup_id=task.startup_id,
            success=False,
            content="All providers failed",
            cost=0.0,
            provider_used="none",
            execution_time_seconds=0.0,
            completed_at=datetime.utcnow(),
            error_message="All AI providers are unavailable"
        )
    
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