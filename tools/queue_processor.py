#!/usr/bin/env python3
"""
QueueProcessor - Parallel task processing with AI coordination
Manages intelligent task queuing, provider coordination, and result processing.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from collections import defaultdict

try:
    # Try relative imports first (package mode)
    from .core_types import (
        IQueueProcessor, Task, TaskResult, PrioritizedTask, TaskType, TaskPriority, TaskStatus,
        generate_task_id, validate_task, TaskNotFoundError, ProviderError
    )
except ImportError:
    # Fall back to absolute imports (script mode)
    from core_types import (
        IQueueProcessor, Task, TaskResult, PrioritizedTask, TaskType, TaskPriority, TaskStatus,
        generate_task_id, validate_task, TaskNotFoundError, ProviderError
    )

logger = logging.getLogger(__name__)


class LoadBalancer:
    """Intelligent load balancing for AI providers"""
    
    def __init__(self):
        self.provider_stats = defaultdict(lambda: {
            'total_requests': 0,
            'success_count': 0,
            'total_cost': 0.0,
            'avg_response_time': 0.0,
            'current_load': 0,
            'error_rate': 0.0,
            'last_error': None
        })
        self.provider_limits = {
            'openai': {'max_concurrent': 10, 'calls_per_minute': 60},
            'anthropic': {'max_concurrent': 8, 'calls_per_minute': 40},
            'perplexity': {'max_concurrent': 12, 'calls_per_minute': 50}
        }
        self._lock = asyncio.Lock()
    
    async def select_provider(self, task: Task) -> str:
        """
        Select optimal provider for a task
        
        Args:
            task: Task to execute
            
        Returns:
            str: Selected provider name
        """
        async with self._lock:
            # Use preference if specified and available
            if task.provider_preference:
                if self._is_provider_available(task.provider_preference):
                    return task.provider_preference
            
            # Default provider routing based on task type
            default_providers = {
                TaskType.MARKET_RESEARCH: 'perplexity',
                TaskType.FOUNDER_ANALYSIS: 'anthropic',
                TaskType.MVP_SPECIFICATION: 'anthropic',
                TaskType.ARCHITECTURE_DESIGN: 'anthropic',
                TaskType.CODE_GENERATION: 'openai',
                TaskType.TESTING: 'openai',
                TaskType.DEPLOYMENT: 'anthropic'
            }
            
            preferred = default_providers.get(task.type, 'anthropic')
            
            # Check if preferred provider is available
            if self._is_provider_available(preferred):
                return preferred
            
            # Find best available alternative
            available_providers = [
                provider for provider in self.provider_limits.keys()
                if self._is_provider_available(provider)
            ]
            
            if not available_providers:
                # All providers busy, select least loaded
                return min(self.provider_stats.keys(), 
                          key=lambda p: self.provider_stats[p]['current_load'])
            
            # Select provider with best success rate and lowest load
            best_provider = min(available_providers, key=lambda p: (
                self.provider_stats[p]['error_rate'],
                self.provider_stats[p]['current_load'],
                -self.provider_stats[p]['success_count']
            ))
            
            return best_provider
    
    def _is_provider_available(self, provider: str) -> bool:
        """Check if provider is available for new requests"""
        if provider not in self.provider_limits:
            return False
        
        stats = self.provider_stats[provider]
        limits = self.provider_limits[provider]
        
        return stats['current_load'] < limits['max_concurrent']
    
    async def record_request_start(self, provider: str) -> None:
        """Record start of a request"""
        async with self._lock:
            self.provider_stats[provider]['current_load'] += 1
            self.provider_stats[provider]['total_requests'] += 1
    
    async def record_request_end(self, provider: str, success: bool, cost: float, response_time: float) -> None:
        """Record completion of a request"""
        async with self._lock:
            stats = self.provider_stats[provider]
            stats['current_load'] = max(0, stats['current_load'] - 1)
            stats['total_cost'] += cost
            
            if success:
                stats['success_count'] += 1
            
            # Update average response time
            if stats['total_requests'] > 0:
                old_avg = stats['avg_response_time']
                stats['avg_response_time'] = (
                    (old_avg * (stats['total_requests'] - 1) + response_time) / 
                    stats['total_requests']
                )
            
            # Update error rate
            if stats['total_requests'] > 0:
                stats['error_rate'] = 1.0 - (stats['success_count'] / stats['total_requests'])
    
    async def get_provider_stats(self) -> Dict[str, dict]:
        """Get current provider statistics"""
        return dict(self.provider_stats)


class ProviderCoordinator:
    """Coordinates with a specific AI provider"""
    
    def __init__(self, provider: str):
        self.provider = provider
        self.active_requests: Set[str] = set()
        self._lock = asyncio.Lock()
    
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute task with this provider
        
        Args:
            task: Task to execute
            
        Returns:
            TaskResult: Execution result
        """
        async with self._lock:
            self.active_requests.add(task.id)
        
        start_time = time.time()
        
        try:
            # Simulate AI provider call (replace with actual implementation)
            result = await self._call_provider(task)
            
            execution_time = time.time() - start_time
            
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=True,
                content=result['content'],
                cost=result['cost'],
                provider_used=self.provider,
                execution_time_seconds=execution_time,
                tokens_used=result.get('tokens_used'),
                quality_score=result.get('quality_score'),
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=False,
                content="",
                cost=0.0,
                provider_used=self.provider,
                execution_time_seconds=execution_time,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
            
        finally:
            async with self._lock:
                self.active_requests.discard(task.id)
    
    async def _call_provider(self, task: Task) -> dict:
        """
        Call the actual AI provider (mock implementation)
        
        Args:
            task: Task to execute
            
        Returns:
            dict: Provider response
        """
        # This is a mock implementation
        # In real implementation, this would call the actual AI provider APIs
        
        await asyncio.sleep(0.5)  # Simulate API delay
        
        mock_responses = {
            TaskType.MARKET_RESEARCH: {
                'content': f"Market research for {task.startup_id}: Detailed analysis of target market, competition, and opportunities.",
                'cost': 0.05,
                'tokens_used': 2000,
                'quality_score': 0.85
            },
            TaskType.FOUNDER_ANALYSIS: {
                'content': f"Founder analysis for {task.startup_id}: Assessment of founder-market fit and capability analysis.",
                'cost': 0.08,
                'tokens_used': 3000,
                'quality_score': 0.90
            },
            TaskType.MVP_SPECIFICATION: {
                'content': f"MVP specification for {task.startup_id}: Detailed technical and business requirements.",
                'cost': 0.12,
                'tokens_used': 4000,
                'quality_score': 0.88
            }
        }
        
        return mock_responses.get(task.type, {
            'content': f"Generic response for {task.type.value}",
            'cost': 0.03,
            'tokens_used': 1000,
            'quality_score': 0.75
        })


class QueueProcessor(IQueueProcessor):
    """
    Intelligent task queue processor with AI coordination
    
    Features:
    - Priority-based task queuing
    - Parallel execution with concurrency limits
    - Provider load balancing and fallback
    - Task retry logic and error handling
    - Real-time metrics and monitoring
    """
    
    def __init__(self, max_concurrent: int = 15):
        """
        Initialize queue processor
        
        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self.task_queue = asyncio.PriorityQueue()
        self.result_store: Dict[str, TaskResult] = {}
        self.task_status: Dict[str, TaskStatus] = {}
        
        # Provider coordination
        self.load_balancer = LoadBalancer()
        self.provider_coordinators = {
            'openai': ProviderCoordinator('openai'),
            'anthropic': ProviderCoordinator('anthropic'),
            'perplexity': ProviderCoordinator('perplexity')
        }
        
        # Processing control
        self.processing = False
        self.processor_task: Optional[asyncio.Task] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Metrics
        self.metrics = {
            'total_tasks_submitted': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'average_execution_time': 0.0,
            'total_cost': 0.0
        }
        
        logger.info(f"QueueProcessor initialized with max_concurrent={max_concurrent}")
    
    async def submit_task(self, task: Task) -> str:
        """
        Submit task to queue
        
        Args:
            task: Task to submit
            
        Returns:
            str: Task ID
        """
        # Validate task
        validation_errors = validate_task(task)
        if validation_errors:
            raise ValueError(f"Task validation failed: {'; '.join(validation_errors)}")
        
        # Generate ID if not provided
        if not task.id:
            task.id = generate_task_id()
        
        # Create prioritized task
        prioritized_task = PrioritizedTask(
            priority=task.priority.value,
            task_id=task.id,
            task=task
        )
        
        # Add to queue
        await self.task_queue.put(prioritized_task)
        self.task_status[task.id] = TaskStatus.PENDING
        self.metrics['total_tasks_submitted'] += 1
        
        logger.info(f"Submitted task {task.id} (type: {task.type.value}, priority: {task.priority.value})")
        
        return task.id
    
    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Get task result by ID
        
        Args:
            task_id: Task identifier
            
        Returns:
            Optional[TaskResult]: Task result if available
        """
        return self.result_store.get(task_id)
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get task status by ID
        
        Args:
            task_id: Task identifier
            
        Returns:
            Optional[TaskStatus]: Task status if found
        """
        return self.task_status.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task
        
        Args:
            task_id: Task identifier
            
        Returns:
            bool: True if successfully cancelled
        """
        if task_id in self.task_status:
            status = self.task_status[task_id]
            
            if status == TaskStatus.PENDING:
                self.task_status[task_id] = TaskStatus.CANCELLED
                logger.info(f"Cancelled task {task_id}")
                return True
            
            elif status == TaskStatus.IN_PROGRESS:
                # Cannot cancel in-progress tasks
                logger.warning(f"Cannot cancel in-progress task {task_id}")
                return False
        
        return False
    
    async def start_processing(self, max_concurrent: int = None) -> None:
        """
        Start task processing
        
        Args:
            max_concurrent: Override max concurrent tasks
        """
        if self.processing:
            logger.warning("Task processing already started")
            return
        
        if max_concurrent:
            self.max_concurrent = max_concurrent
            self.semaphore = asyncio.Semaphore(max_concurrent)
        
        self.processing = True
        self.processor_task = asyncio.create_task(self._process_tasks())
        
        logger.info(f"Started task processing with max_concurrent={self.max_concurrent}")
    
    async def stop_processing(self) -> None:
        """Stop task processing"""
        if not self.processing:
            return
        
        self.processing = False
        
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped task processing")
    
    async def _process_tasks(self) -> None:
        """Main task processing loop"""
        logger.info("Task processing loop started")
        
        while self.processing:
            try:
                # Get next task from queue
                prioritized_task = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1.0
                )
                
                # Check if task was cancelled
                if self.task_status.get(prioritized_task.task_id) == TaskStatus.CANCELLED:
                    continue
                
                # Process task concurrently
                asyncio.create_task(self._execute_single_task(prioritized_task))
                
            except asyncio.TimeoutError:
                # No tasks in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error in task processing loop: {e}")
                await asyncio.sleep(1.0)
        
        logger.info("Task processing loop stopped")
    
    async def _execute_single_task(self, prioritized_task: PrioritizedTask) -> None:
        """
        Execute a single task with concurrency control
        
        Args:
            prioritized_task: Task to execute
        """
        task = prioritized_task.task
        
        async with self.semaphore:
            try:
                # Update status
                self.task_status[task.id] = TaskStatus.IN_PROGRESS
                
                # Select provider
                provider = await self.load_balancer.select_provider(task)
                coordinator = self.provider_coordinators[provider]
                
                # Record request start
                await self.load_balancer.record_request_start(provider)
                
                # Execute task with retry logic
                result = await self._execute_with_retry(coordinator, task)
                
                # Record request completion
                await self.load_balancer.record_request_end(
                    provider, result.success, result.cost, result.execution_time_seconds
                )
                
                # Store result
                self.result_store[task.id] = result
                self.task_status[task.id] = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                
                # Update metrics
                self._update_metrics(result)
                
                logger.info(f"Completed task {task.id} (success: {result.success}, "
                           f"cost: ${result.cost:.4f}, time: {result.execution_time_seconds:.2f}s)")
                
            except Exception as e:
                # Create error result
                error_result = TaskResult(
                    task_id=task.id,
                    startup_id=task.startup_id,
                    success=False,
                    content="",
                    cost=0.0,
                    provider_used="unknown",
                    execution_time_seconds=0.0,
                    completed_at=datetime.utcnow(),
                    error_message=str(e)
                )
                
                self.result_store[task.id] = error_result
                self.task_status[task.id] = TaskStatus.FAILED
                self._update_metrics(error_result)
                
                logger.error(f"Failed to execute task {task.id}: {e}")
    
    async def _execute_with_retry(self, coordinator: ProviderCoordinator, task: Task) -> TaskResult:
        """
        Execute task with retry logic
        
        Args:
            coordinator: Provider coordinator
            task: Task to execute
            
        Returns:
            TaskResult: Execution result
        """
        last_error = None
        
        for attempt in range(task.max_retries + 1):
            try:
                result = await coordinator.execute_task(task)
                
                if result.success:
                    return result
                
                last_error = result.error_message
                
                if attempt < task.max_retries:
                    # Exponential backoff
                    delay = 2 ** attempt
                    logger.warning(f"Task {task.id} attempt {attempt + 1} failed, "
                                 f"retrying in {delay}s: {last_error}")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                last_error = str(e)
                
                if attempt < task.max_retries:
                    delay = 2 ** attempt
                    logger.warning(f"Task {task.id} attempt {attempt + 1} error, "
                                 f"retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
        
        # All retries failed
        raise ProviderError(f"Task failed after {task.max_retries + 1} attempts: {last_error}")
    
    def _update_metrics(self, result: TaskResult) -> None:
        """Update processing metrics"""
        if result.success:
            self.metrics['total_tasks_completed'] += 1
        else:
            self.metrics['total_tasks_failed'] += 1
        
        self.metrics['total_cost'] += result.cost
        
        # Update average execution time
        total_tasks = self.metrics['total_tasks_completed'] + self.metrics['total_tasks_failed']
        if total_tasks > 0:
            old_avg = self.metrics['average_execution_time']
            self.metrics['average_execution_time'] = (
                (old_avg * (total_tasks - 1) + result.execution_time_seconds) / total_tasks
            )
    
    async def get_queue_stats(self) -> dict:
        """
        Get queue processing statistics
        
        Returns:
            dict: Processing statistics
        """
        pending_count = sum(1 for status in self.task_status.values() 
                           if status == TaskStatus.PENDING)
        in_progress_count = sum(1 for status in self.task_status.values() 
                               if status == TaskStatus.IN_PROGRESS)
        
        provider_stats = await self.load_balancer.get_provider_stats()
        
        return {
            "processing": self.processing,
            "max_concurrent": self.max_concurrent,
            "queue_size": self.task_queue.qsize(),
            "tasks": {
                "pending": pending_count,
                "in_progress": in_progress_count,
                "completed": self.metrics['total_tasks_completed'],
                "failed": self.metrics['total_tasks_failed'],
                "total_submitted": self.metrics['total_tasks_submitted']
            },
            "performance": {
                "average_execution_time": self.metrics['average_execution_time'],
                "total_cost": self.metrics['total_cost'],
                "success_rate": (
                    self.metrics['total_tasks_completed'] / 
                    max(1, self.metrics['total_tasks_completed'] + self.metrics['total_tasks_failed'])
                )
            },
            "providers": provider_stats
        }
    
    async def health_check(self) -> dict:
        """
        Perform health check on queue processor
        
        Returns:
            dict: Health status
        """
        try:
            stats = await self.get_queue_stats()
            
            # Check for issues
            issues = []
            
            if not self.processing:
                issues.append("Task processing not started")
            
            if stats["tasks"]["pending"] > 100:
                issues.append(f"Large queue backlog: {stats['tasks']['pending']} pending tasks")
            
            if stats["performance"]["success_rate"] < 0.8:
                issues.append(f"Low success rate: {stats['performance']['success_rate']:.2%}")
            
            return {
                "healthy": len(issues) == 0,
                "issues": issues,
                "stats": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def cleanup(self) -> None:
        """Cleanup queue processor"""
        logger.info("Cleaning up QueueProcessor...")
        
        # Stop processing
        await self.stop_processing()
        
        # Clear queues and stores
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        self.result_store.clear()
        self.task_status.clear()
        
        logger.info("QueueProcessor cleanup completed")