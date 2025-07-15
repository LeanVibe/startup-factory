#!/usr/bin/env python3
"""
Multi-Startup Enhanced Orchestrator - Central coordination for multiple startups
Integrates StartupManager, ResourceAllocator, and QueueProcessor for concurrent startup development.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .core_types import (
    StartupConfig, StartupInstance, StartupStatus, Task, TaskType, TaskPriority,
    generate_task_id, validate_startup_config
)
from .startup_manager import StartupManager
from .queue_processor import QueueProcessor

logger = logging.getLogger(__name__)


class MultiStartupOrchestrator:
    """
    Central orchestrator for multi-startup development
    
    Features:
    - Concurrent startup management (up to 5 simultaneous)
    - Intelligent task queuing and AI coordination
    - Resource conflict prevention
    - Progress tracking and monitoring
    - Cost management and optimization
    """
    
    def __init__(self, config_path: str = "./config.yaml", max_concurrent_startups: int = 5):
        """
        Initialize multi-startup orchestrator
        
        Args:
            config_path: Path to configuration file
            max_concurrent_startups: Maximum concurrent startups
        """
        self.config_path = Path(config_path)
        self.max_concurrent_startups = max_concurrent_startups
        
        # Core components
        self.startup_manager = StartupManager(max_concurrent=max_concurrent_startups)
        self.queue_processor = QueueProcessor(max_concurrent=15)
        
        # State tracking
        self.startup_workflows: Dict[str, dict] = {}  # startup_id -> workflow state
        self.workflow_results: Dict[str, dict] = {}  # startup_id -> final results
        
        # Configuration
        self.config = self._load_config()
        
        # Metrics
        self.metrics = {
            'total_startups_created': 0,
            'total_startups_completed': 0,
            'total_cost': 0.0,
            'average_completion_time': 0.0,
            'success_rate': 0.0
        }
        
        logger.info(f"MultiStartupOrchestrator initialized (max concurrent: {max_concurrent_startups})")
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            else:
                logger.warning(f"Config file {self.config_path} not found, using defaults")
                return {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    async def initialize(self) -> None:
        """Initialize the orchestrator and all components"""
        logger.info("Initializing MultiStartupOrchestrator...")
        
        # Initialize startup manager
        await self.startup_manager.initialize()
        
        # Start queue processor
        await self.queue_processor.start_processing()
        
        logger.info("MultiStartupOrchestrator initialization complete")
    
    async def create_startup(self, startup_config: dict) -> str:
        """
        Create a new startup with full workflow orchestration
        
        Args:
            startup_config: Startup configuration dictionary
            
        Returns:
            str: Startup ID
        """
        try:
            # Convert to StartupConfig
            config = StartupConfig(
                name=startup_config['name'],
                industry=startup_config['industry'],
                category=startup_config['category'],
                template=startup_config.get('template', 'neoforge'),
                founder_profile=startup_config.get('founder_profile', {}),
                resource_requirements=startup_config.get('resource_requirements', {
                    'memory_mb': 500,
                    'cpu_cores': 0.5,
                    'storage_gb': 2,
                    'port_count': 3,
                    'api_calls_per_hour': 1000,
                    'cost_per_day': 15.0
                })
            )
            
            # Create startup through manager
            startup_id = await self.startup_manager.create_startup(config)
            
            # Initialize workflow state
            self.startup_workflows[startup_id] = {
                'created_at': datetime.utcnow(),
                'current_phase': 0,
                'phases': [
                    'market_research',
                    'founder_analysis', 
                    'mvp_specification',
                    'architecture_design'
                ],
                'phase_results': {},
                'status': 'initializing'
            }
            
            # Update metrics
            self.metrics['total_startups_created'] += 1
            
            logger.info(f"Created startup '{config.name}' with ID {startup_id}")
            
            # Start workflow execution asynchronously
            asyncio.create_task(self._execute_startup_workflow(startup_id))
            
            return startup_id
            
        except Exception as e:
            logger.error(f"Failed to create startup: {e}")
            raise
    
    async def create_multiple_startups(self, startup_configs: List[dict]) -> List[str]:
        """
        Create multiple startups concurrently
        
        Args:
            startup_configs: List of startup configurations
            
        Returns:
            List[str]: List of startup IDs
        """
        logger.info(f"Creating {len(startup_configs)} startups concurrently...")
        
        # Create all startups concurrently
        tasks = [self.create_startup(config) for config in startup_configs]
        startup_ids = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log errors
        successful_ids = []
        for i, result in enumerate(startup_ids):
            if isinstance(result, Exception):
                logger.error(f"Failed to create startup {i}: {result}")
            else:
                successful_ids.append(result)
        
        logger.info(f"Successfully created {len(successful_ids)}/{len(startup_configs)} startups")
        
        return successful_ids
    
    async def _execute_startup_workflow(self, startup_id: str) -> None:
        """
        Execute the complete development workflow for a startup
        
        Args:
            startup_id: Unique startup identifier
        """
        try:
            workflow = self.startup_workflows[startup_id]
            startup = await self.startup_manager.get_startup(startup_id)
            
            logger.info(f"Starting workflow execution for startup {startup_id}")
            
            # Update startup status
            await self.startup_manager.update_startup_status(startup_id, StartupStatus.ACTIVE)
            workflow['status'] = 'active'
            
            # Execute each phase
            for i, phase in enumerate(workflow['phases']):
                try:
                    # Update current phase
                    workflow['current_phase'] = i
                    await self.startup_manager.update_startup_state(
                        startup_id, 
                        {'current_phase': i, 'current_phase_name': phase}
                    )
                    
                    logger.info(f"Executing phase {i}: {phase} for startup {startup_id}")
                    
                    # Execute phase
                    phase_result = await self._execute_phase(startup_id, phase, startup.config)
                    
                    # Store phase result
                    workflow['phase_results'][phase] = phase_result
                    
                    logger.info(f"Completed phase {phase} for startup {startup_id}")
                    
                except Exception as e:
                    logger.error(f"Phase {phase} failed for startup {startup_id}: {e}")
                    
                    # Increment error count
                    await self.startup_manager.increment_error_count(
                        startup_id, 
                        f"Phase {phase} failed: {e}"
                    )
                    
                    # Check if we should continue or fail
                    startup = await self.startup_manager.get_startup(startup_id)
                    if startup.error_count >= 3:
                        workflow['status'] = 'failed'
                        break
            
            # Finalize workflow
            if workflow['status'] != 'failed':
                workflow['status'] = 'completed'
                workflow['completed_at'] = datetime.utcnow()
                
                # Update startup status
                await self.startup_manager.update_startup_status(startup_id, StartupStatus.COMPLETED)
                
                # Calculate metrics
                completion_time = (workflow['completed_at'] - workflow['created_at']).total_seconds()
                total_cost = sum(result.get('cost', 0.0) for result in workflow['phase_results'].values())
                
                # Store final results
                self.workflow_results[startup_id] = {
                    'startup_id': startup_id,
                    'config': startup.config.__dict__,
                    'workflow': workflow,
                    'completion_time_seconds': completion_time,
                    'total_cost': total_cost,
                    'success': True
                }
                
                # Update global metrics
                self.metrics['total_startups_completed'] += 1
                self.metrics['total_cost'] += total_cost
                self._update_success_rate()
                self._update_average_completion_time(completion_time)
                
                logger.info(f"Completed startup workflow for {startup_id} "
                           f"(time: {completion_time:.1f}s, cost: ${total_cost:.4f})")
            
            else:
                # Mark as failed
                await self.startup_manager.update_startup_status(startup_id, StartupStatus.FAILED)
                
                self.workflow_results[startup_id] = {
                    'startup_id': startup_id,
                    'config': startup.config.__dict__,
                    'workflow': workflow,
                    'success': False,
                    'error': workflow.get('last_error', 'Unknown error')
                }
                
                logger.error(f"Startup workflow failed for {startup_id}")
            
        except Exception as e:
            logger.error(f"Workflow execution failed for startup {startup_id}: {e}")
            
            # Mark as failed
            try:
                await self.startup_manager.update_startup_status(startup_id, StartupStatus.FAILED)
                await self.startup_manager.increment_error_count(startup_id, f"Workflow execution failed: {e}")
            except Exception as nested_error:
                logger.error(f"Failed to update status after error: {nested_error}")
    
    async def _execute_phase(self, startup_id: str, phase: str, config: StartupConfig) -> dict:
        """
        Execute a single workflow phase
        
        Args:
            startup_id: Startup identifier
            phase: Phase name
            config: Startup configuration
            
        Returns:
            dict: Phase execution result
        """
        # Create task for the phase
        task = Task(
            id=generate_task_id(),
            startup_id=startup_id,
            type=TaskType(phase),
            description=f"Execute {phase} for {config.name}",
            prompt=self._generate_phase_prompt(phase, config),
            context={
                'startup_name': config.name,
                'industry': config.industry,
                'category': config.category,
                'founder_profile': config.founder_profile
            },
            priority=TaskPriority.HIGH,
            max_tokens=4000
        )
        
        # Submit task to queue
        task_id = await self.queue_processor.submit_task(task)
        
        # Wait for completion
        result = await self._wait_for_task_completion(task_id, timeout=300)  # 5 minutes
        
        if result and result.success:
            return {
                'phase': phase,
                'content': result.content,
                'cost': result.cost,
                'provider': result.provider_used,
                'execution_time': result.execution_time_seconds,
                'quality_score': result.quality_score,
                'completed_at': result.completed_at.isoformat()
            }
        else:
            error_msg = result.error_message if result else "Task timeout or no result"
            raise Exception(f"Phase {phase} execution failed: {error_msg}")
    
    def _generate_phase_prompt(self, phase: str, config: StartupConfig) -> str:
        """Generate AI prompt for a specific phase"""
        base_context = f"""
Startup: {config.name}
Industry: {config.industry}
Category: {config.category}
Founder Profile: {json.dumps(config.founder_profile, indent=2)}
"""
        
        prompts = {
            'market_research': f"""
{base_context}

Conduct comprehensive market research for this startup idea. Analyze:
1. Market size and growth potential
2. Target customer segments
3. Competitive landscape
4. Market trends and opportunities
5. Potential challenges and risks

Provide detailed, actionable insights with specific data and recommendations.
""",
            'founder_analysis': f"""
{base_context}

Analyze the founder-market fit for this startup. Evaluate:
1. Founder's skills and experience alignment with the market
2. Domain expertise and credibility
3. Network and access to target customers
4. Resource requirements vs availability
5. Overall founder-market fit score (1-10)

Provide specific recommendations for strengthening the founder's position.
""",
            'mvp_specification': f"""
{base_context}

Create a detailed MVP specification including:
1. Core features and functionality
2. User stories and acceptance criteria
3. Technical requirements
4. UI/UX considerations
5. Success metrics and KPIs
6. Development timeline estimate

Focus on the minimal viable product that validates the core value proposition.
""",
            'architecture_design': f"""
{base_context}

Design the technical architecture for this MVP including:
1. System architecture overview
2. Technology stack recommendations
3. Database design
4. API structure
5. Security considerations
6. Scalability planning
7. Deployment strategy

Provide specific technical recommendations suitable for rapid MVP development.
"""
        }
        
        return prompts.get(phase, f"Execute {phase} for {config.name}")
    
    async def _wait_for_task_completion(self, task_id: str, timeout: int = 300) -> Optional[Any]:
        """
        Wait for task completion with timeout
        
        Args:
            task_id: Task identifier
            timeout: Timeout in seconds
            
        Returns:
            Optional[TaskResult]: Task result if completed
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check if task completed
            result = await self.queue_processor.get_task_result(task_id)
            if result:
                return result
            
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.error(f"Task {task_id} timed out after {timeout} seconds")
                return None
            
            # Wait before checking again
            await asyncio.sleep(1.0)
    
    def _update_success_rate(self) -> None:
        """Update success rate metric"""
        total_attempted = self.metrics['total_startups_created']
        if total_attempted > 0:
            self.metrics['success_rate'] = self.metrics['total_startups_completed'] / total_attempted
    
    def _update_average_completion_time(self, completion_time: float) -> None:
        """Update average completion time metric"""
        completed_count = self.metrics['total_startups_completed']
        if completed_count > 0:
            old_avg = self.metrics['average_completion_time']
            self.metrics['average_completion_time'] = (
                (old_avg * (completed_count - 1) + completion_time) / completed_count
            )
    
    async def get_startup_status(self, startup_id: str) -> dict:
        """
        Get detailed status for a startup
        
        Args:
            startup_id: Startup identifier
            
        Returns:
            dict: Startup status information
        """
        try:
            startup = await self.startup_manager.get_startup(startup_id)
            workflow = self.startup_workflows.get(startup_id, {})
            
            # Get queue stats for this startup's tasks
            queue_stats = await self.queue_processor.get_queue_stats()
            
            return {
                'startup_id': startup_id,
                'name': startup.config.name,
                'status': startup.status.value,
                'current_phase': workflow.get('current_phase', 0),
                'current_phase_name': workflow.get('phases', [])[workflow.get('current_phase', 0)] if workflow.get('phases') else None,
                'phases_completed': len(workflow.get('phase_results', {})),
                'total_phases': len(workflow.get('phases', [])),
                'created_at': startup.created_at.isoformat(),
                'updated_at': startup.updated_at.isoformat(),
                'error_count': startup.error_count,
                'last_error': startup.last_error,
                'resource_allocation': {
                    'memory_mb': startup.resource_allocation.memory_mb,
                    'cpu_cores': startup.resource_allocation.cpu_cores,
                    'ports': startup.resource_allocation.ports,
                    'database_namespace': startup.resource_allocation.database_namespace
                },
                'workflow_status': workflow.get('status', 'unknown'),
                'queue_info': {
                    'processing': queue_stats['processing'],
                    'queue_size': queue_stats['queue_size']
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get startup status for {startup_id}: {e}")
            return {
                'startup_id': startup_id,
                'error': str(e)
            }
    
    async def get_all_startups_status(self) -> List[dict]:
        """
        Get status for all managed startups
        
        Returns:
            List[dict]: List of startup status information
        """
        all_startups = await self.startup_manager.get_all_startups()
        
        tasks = [self.get_startup_status(startup.id) for startup in all_startups]
        statuses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_statuses = [
            status for status in statuses 
            if not isinstance(status, Exception)
        ]
        
        return valid_statuses
    
    async def get_system_metrics(self) -> dict:
        """
        Get comprehensive system metrics
        
        Returns:
            dict: System metrics and statistics
        """
        try:
            # Get component stats
            startup_stats = await self.startup_manager.get_startup_stats()
            queue_stats = await self.queue_processor.get_queue_stats()
            
            # Get active startups count
            active_startups = await self.startup_manager.get_active_startups()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'orchestrator_metrics': self.metrics,
                'startup_manager': startup_stats,
                'queue_processor': queue_stats,
                'current_load': {
                    'active_startups': len(active_startups),
                    'max_concurrent_startups': self.max_concurrent_startups,
                    'utilization_percent': (len(active_startups) / self.max_concurrent_startups) * 100
                },
                'workflow_summary': {
                    'total_workflows': len(self.startup_workflows),
                    'completed_workflows': len([w for w in self.startup_workflows.values() if w.get('status') == 'completed']),
                    'failed_workflows': len([w for w in self.startup_workflows.values() if w.get('status') == 'failed']),
                    'active_workflows': len([w for w in self.startup_workflows.values() if w.get('status') == 'active'])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    async def health_check(self) -> dict:
        """
        Perform comprehensive health check
        
        Returns:
            dict: Health status
        """
        try:
            # Check component health
            startup_manager_health = await self.startup_manager.health_check()
            queue_processor_health = await self.queue_processor.health_check()
            
            # Overall health assessment
            component_healths = [
                startup_manager_health['healthy'],
                queue_processor_health['healthy']
            ]
            
            overall_healthy = all(component_healths)
            
            # Collect issues
            issues = []
            if not startup_manager_health['healthy']:
                issues.extend(startup_manager_health.get('issues', ['Startup manager unhealthy']))
            if not queue_processor_health['healthy']:
                issues.extend(queue_processor_health.get('issues', ['Queue processor unhealthy']))
            
            return {
                'healthy': overall_healthy,
                'timestamp': datetime.utcnow().isoformat(),
                'components': {
                    'startup_manager': startup_manager_health,
                    'queue_processor': queue_processor_health
                },
                'issues': issues,
                'system_metrics': await self.get_system_metrics()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'healthy': False,
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup orchestrator and all components"""
        logger.info("Cleaning up MultiStartupOrchestrator...")
        
        # Stop queue processor
        await self.queue_processor.cleanup()
        
        # Cleanup startup manager
        await self.startup_manager.cleanup()
        
        # Clear workflow state
        self.startup_workflows.clear()
        self.workflow_results.clear()
        
        logger.info("MultiStartupOrchestrator cleanup completed")


# Convenience functions for testing and development
async def create_demo_startup(orchestrator: MultiStartupOrchestrator, name: str = "Demo Startup") -> str:
    """Create a demo startup for testing"""
    config = {
        'name': name,
        'industry': 'technology',
        'category': 'demo',
        'template': 'neoforge',
        'founder_profile': {
            'skills': 'Full-stack development, Product management',
            'experience': '5 years in tech startups',
            'network': 'Strong connections in tech industry'
        },
        'resource_requirements': {
            'memory_mb': 500,
            'cpu_cores': 0.5,
            'storage_gb': 2,
            'port_count': 3
        }
    }
    
    return await orchestrator.create_startup(config)


async def create_multiple_demo_startups(orchestrator: MultiStartupOrchestrator, count: int = 3) -> List[str]:
    """Create multiple demo startups for testing"""
    configs = []
    
    for i in range(count):
        config = {
            'name': f"Demo Startup {i+1}",
            'industry': ['technology', 'healthcare', 'fintech'][i % 3],
            'category': ['saas', 'marketplace', 'platform'][i % 3],
            'template': 'neoforge',
            'founder_profile': {
                'skills': f'Domain expertise in {["tech", "health", "finance"][i % 3]}',
                'experience': f'{3 + i} years experience',
                'network': 'Industry connections'
            }
        }
        configs.append(config)
    
    return await orchestrator.create_multiple_startups(configs)


if __name__ == "__main__":
    async def main():
        """Demo usage of MultiStartupOrchestrator"""
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create orchestrator
        orchestrator = MultiStartupOrchestrator()
        
        try:
            # Initialize
            await orchestrator.initialize()
            
            # Create demo startups
            print("Creating demo startups...")
            startup_ids = await create_multiple_demo_startups(orchestrator, count=2)
            
            print(f"Created startups: {startup_ids}")
            
            # Monitor progress
            for _ in range(30):  # Monitor for 30 seconds
                await asyncio.sleep(1)
                
                # Get status
                statuses = await orchestrator.get_all_startups_status()
                
                print(f"\nStatus update:")
                for status in statuses:
                    print(f"  {status['name']}: {status['workflow_status']} "
                          f"(phase {status['current_phase']}/{status['total_phases']})")
                
                # Check if all completed
                if all(s['workflow_status'] in ['completed', 'failed'] for s in statuses):
                    break
            
            # Final metrics
            metrics = await orchestrator.get_system_metrics()
            print(f"\nFinal metrics:")
            print(f"  Total startups: {metrics['orchestrator_metrics']['total_startups_created']}")
            print(f"  Completed: {metrics['orchestrator_metrics']['total_startups_completed']}")
            print(f"  Success rate: {metrics['orchestrator_metrics']['success_rate']:.2%}")
            print(f"  Total cost: ${metrics['orchestrator_metrics']['total_cost']:.4f}")
            
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await orchestrator.cleanup()
    
    asyncio.run(main())