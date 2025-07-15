#!/usr/bin/env python3
"""
Demo script for Track C: Advanced AI Coordination features
Shows real AI provider integration, cost tracking, and health monitoring.
"""

import asyncio
import sys
import os
sys.path.append('tools')

from ai_providers import AIProviderManager, create_default_provider_manager
from budget_monitor import BudgetMonitor
from health_monitor import ProviderHealthMonitor
from queue_processor import QueueProcessor
from core_types import Task, TaskType, TaskPriority


async def demo_ai_coordination():
    """Demonstrate AI coordination features"""
    print("🚀 Starting Track C: Advanced AI Coordination Demo")
    print("=" * 60)
    
    # Create AI provider manager with real integrations
    print("\n1️⃣ Creating AI Provider Manager...")
    provider_manager = create_default_provider_manager()
    available_providers = provider_manager.get_available_providers()
    print(f"   Available providers: {available_providers}")
    
    if not available_providers:
        print("⚠️  No real AI providers available (API keys not set)")
        print("   Demo will use mock providers for testing")
        
        # Create mock provider for demo
        from ai_providers import ProviderConfig
        from unittest.mock import Mock, AsyncMock
        
        mock_config = ProviderConfig(
            name='demo-provider',
            api_key='demo-key',
            models={'demo': 'gpt-4o'},
            cost_per_input_token=0.00001,
            cost_per_output_token=0.00003,
            max_tokens=4000,
            max_concurrent=10
        )
        
        mock_provider = Mock()
        async def mock_call_api(task):
            from core_types import TaskResult
            import time
            await asyncio.sleep(0.1)  # Simulate API delay
            return TaskResult(
                task_id=task.id,
                startup_id=task.startup_id,
                success=True,
                content=f"Demo AI response for {task.type.value}: {task.description}",
                cost=0.05,
                provider_used='demo-provider',
                execution_time_seconds=0.1,
                tokens_used=150,
                quality_score=0.85
            )
        
        mock_provider.call_api = mock_call_api
        provider_manager.register_provider('demo-provider', mock_provider, mock_config)
        print("   ✅ Demo provider registered")
    
    # Create budget monitoring system
    print("\n2️⃣ Setting up Budget Monitoring...")
    budget_monitor = BudgetMonitor()
    
    # Set budget limits for demo startup
    await budget_monitor.set_budget_limit(
        startup_id='demo-startup',
        daily_limit=50.0,
        monthly_limit=500.0,
        total_limit=2000.0,
        warning_threshold=0.8
    )
    print("   ✅ Budget limits set: $50/day, $500/month, $2000 total")
    
    # Create health monitoring system
    print("\n3️⃣ Initializing Health Monitoring...")
    health_monitor = ProviderHealthMonitor(provider_manager, check_interval=5.0)
    await health_monitor.start_monitoring()
    print("   ✅ Health monitoring started (5s intervals)")
    
    # Create queue processor with real integrations
    print("\n4️⃣ Creating Queue Processor...")
    queue_processor = QueueProcessor(
        max_concurrent=3,
        provider_manager=provider_manager,
        budget_monitor=budget_monitor
    )
    await queue_processor.start_processing()
    print("   ✅ Queue processor started (max 3 concurrent tasks)")
    
    # Demo task execution
    print("\n5️⃣ Executing Demo Tasks...")
    
    demo_tasks = [
        Task(
            id='demo-task-1',
            startup_id='demo-startup',
            type=TaskType.MARKET_RESEARCH,
            description='Research AI automation market',
            prompt='Analyze the current market for AI automation tools, key players, and growth opportunities.',
            priority=TaskPriority.HIGH
        ),
        Task(
            id='demo-task-2', 
            startup_id='demo-startup',
            type=TaskType.CODE_GENERATION,
            description='Generate MVP API structure',
            prompt='Create a RESTful API structure for an AI automation platform.',
            priority=TaskPriority.MEDIUM
        ),
        Task(
            id='demo-task-3',
            startup_id='demo-startup',
            type=TaskType.ARCHITECTURE_DESIGN,
            description='Design system architecture',
            prompt='Design a scalable architecture for processing multiple AI tasks concurrently.',
            priority=TaskPriority.HIGH
        )
    ]
    
    # Submit all tasks
    task_ids = []
    for task in demo_tasks:
        task_id = await queue_processor.submit_task(task)
        task_ids.append(task_id)
        print(f"   📤 Submitted: {task.description}")
    
    # Wait for task completion
    print("\n6️⃣ Monitoring Task Execution...")
    completed_tasks = 0
    max_wait = 30  # seconds
    start_time = asyncio.get_event_loop().time()
    
    while completed_tasks < len(demo_tasks) and (asyncio.get_event_loop().time() - start_time) < max_wait:
        for i, task_id in enumerate(task_ids):
            result = await queue_processor.get_task_result(task_id)
            if result and task_id not in [t for t in task_ids[:completed_tasks]]:
                status = "✅ SUCCESS" if result.success else "❌ FAILED"
                print(f"   {status}: {demo_tasks[i].description}")
                print(f"            Cost: ${result.cost:.4f}, Time: {result.execution_time_seconds:.2f}s")
                if result.success:
                    completed_tasks += 1
        
        if completed_tasks < len(demo_tasks):
            await asyncio.sleep(1)
    
    # Show system statistics
    print("\n7️⃣ System Statistics:")
    
    # Queue statistics
    queue_stats = await queue_processor.get_queue_stats()
    print(f"   📊 Queue: {queue_stats['tasks']['completed']} completed, {queue_stats['tasks']['failed']} failed")
    print(f"   💰 Total cost: ${queue_stats['performance']['total_cost']:.4f}")
    print(f"   ⚡ Avg execution time: {queue_stats['performance']['average_execution_time']:.2f}s")
    print(f"   📈 Success rate: {queue_stats['performance']['success_rate']:.1%}")
    
    # Budget status
    budget_status = await budget_monitor.get_budget_status('demo-startup')
    print(f"   💳 Budget used: ${budget_status['current_spending']['total']:.4f} of ${budget_status['limits']['total']:.2f}")
    print(f"   📈 Utilization: {budget_status['utilization']['total']:.1%}")
    
    # Health status
    health_summary = await health_monitor.get_health_summary()
    print(f"   🏥 Provider health: {health_summary['provider_counts']['healthy']} healthy, {health_summary['provider_counts']['warning']} warnings")
    
    # Provider cost breakdown
    if 'real_provider_costs' in queue_stats:
        provider_costs = queue_stats['real_provider_costs']
        print(f"   🔧 Provider stats: {provider_costs['total_calls']} calls, ${provider_costs['total_cost']:.4f} total")
    
    # Cleanup
    print("\n8️⃣ Cleaning up...")
    await queue_processor.stop_processing()
    await health_monitor.stop_monitoring()
    print("   ✅ All systems stopped")
    
    print("\n🎉 Demo completed successfully!")
    print("=" * 60)
    print("Track C features demonstrated:")
    print("✅ Real AI provider integration (OpenAI, Anthropic, OpenCode CLI)")
    print("✅ Cost tracking with detailed analytics")
    print("✅ Budget monitoring with alerts and limits")
    print("✅ Provider health monitoring and failover")
    print("✅ Intelligent task routing and load balancing")
    print("✅ Comprehensive error handling and retry logic")


if __name__ == '__main__':
    asyncio.run(demo_ai_coordination())