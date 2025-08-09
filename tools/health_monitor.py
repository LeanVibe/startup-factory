#!/usr/bin/env python3
"""
Provider Health Monitoring System
Monitors AI provider availability, performance, and automatically handles failover.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any

from .core_types import Task, TaskType, ProviderError
from .ai_providers import AIProviderManager

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: float
    status: HealthStatus
    threshold_warning: float
    threshold_critical: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProviderHealth:
    """Complete health status for a provider"""
    provider_name: str
    overall_status: HealthStatus
    last_check: datetime
    uptime_percentage: float
    metrics: Dict[str, HealthMetric]
    recent_errors: List[str]
    consecutive_failures: int
    last_successful_call: Optional[datetime] = None
    next_check: Optional[datetime] = None


@dataclass
class HealthAlert:
    """Health monitoring alert"""
    provider_name: str
    alert_type: str  # 'degradation', 'failure', 'recovery'
    severity: HealthStatus
    message: str
    metric_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ProviderHealthMonitor:
    """
    Comprehensive provider health monitoring system
    
    Features:
    - Real-time health checks for all providers
    - Performance metric tracking (latency, success rate, cost)
    - Automatic failover when providers become unhealthy
    - Alert system for health degradation
    - Historical health data tracking
    """
    
    def __init__(self, provider_manager: AIProviderManager, check_interval: float = 60.0):
        """
        Initialize health monitor
        
        Args:
            provider_manager: AI provider manager to monitor
            check_interval: Health check interval in seconds
        """
        self.provider_manager = provider_manager
        self.check_interval = check_interval
        
        # Health tracking
        self.provider_health: Dict[str, ProviderHealth] = {}
        self.health_history: List[Dict[str, Any]] = []
        self.alerts: List[HealthAlert] = []
        self.alert_callbacks: List[Callable[[HealthAlert], None]] = []
        
        # Monitoring control
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Thresholds (can be customized per provider)
        self.default_thresholds = {
            'latency_warning': 5000,  # 5 seconds
            'latency_critical': 10000,  # 10 seconds
            'success_rate_warning': 0.90,  # 90%
            'success_rate_critical': 0.80,  # 80%
            'cost_efficiency_warning': 1.5,  # 50% above baseline
            'cost_efficiency_critical': 2.0,  # 100% above baseline
            'consecutive_failures_warning': 3,
            'consecutive_failures_critical': 5
        }
        
        # Initialize health status for all providers
        self._initialize_provider_health()
        
        logger.info(f"Health monitor initialized for {len(self.provider_health)} providers")
    
    def _initialize_provider_health(self) -> None:
        """Initialize health status for all providers"""
        for provider_name in self.provider_manager.get_available_providers():
            self.provider_health[provider_name] = ProviderHealth(
                provider_name=provider_name,
                overall_status=HealthStatus.UNKNOWN,
                last_check=datetime.utcnow(),
                uptime_percentage=100.0,
                metrics={},
                recent_errors=[],
                consecutive_failures=0
            )
    
    async def start_monitoring(self) -> None:
        """Start health monitoring"""
        if self.monitoring:
            logger.warning("Health monitoring already started")
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Started provider health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped provider health monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info("Health monitoring loop started")
        
        while self.monitoring:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5.0)  # Short delay before retrying
        
        logger.info("Health monitoring loop stopped")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all providers"""
        check_tasks = []
        
        for provider_name in self.provider_health.keys():
            task = asyncio.create_task(self._check_provider_health(provider_name))
            check_tasks.append(task)
        
        # Run all health checks concurrently
        await asyncio.gather(*check_tasks, return_exceptions=True)
    
    async def _check_provider_health(self, provider_name: str) -> None:
        """
        Check health of a specific provider
        
        Args:
            provider_name: Name of provider to check
        """
        health = self.provider_health[provider_name]
        
        try:
            # Create a simple test task
            test_task = Task(
                id=f"health_check_{provider_name}_{int(time.time())}",
                startup_id="health_check",
                type=TaskType.MARKET_RESEARCH,
                description="Health check task",
                prompt="Please respond with 'OK' to confirm you are functioning properly.",
                max_tokens=50
            )
            
            # Perform health check call
            start_time = time.time()
            result = await self.provider_manager.call_provider(provider_name, test_task)
            end_time = time.time()
            
            # Calculate metrics
            latency_ms = (end_time - start_time) * 1000
            
            # Update health metrics
            await self._update_health_metrics(provider_name, result.success, latency_ms, result.cost)
            
            # Update last successful call if successful
            if result.success:
                health.last_successful_call = datetime.utcnow()
                health.consecutive_failures = 0
            else:
                health.consecutive_failures += 1
                health.recent_errors.append(result.error_message or "Unknown error")
                
                # Keep only recent errors (last 10)
                health.recent_errors = health.recent_errors[-10:]
        
        except Exception as e:
            logger.error(f"Health check failed for {provider_name}: {e}")
            health.consecutive_failures += 1
            health.recent_errors.append(str(e))
            health.recent_errors = health.recent_errors[-10:]
            
            # Update health metrics with failure
            await self._update_health_metrics(provider_name, False, 0, 0)
        
        # Update overall health status
        health.last_check = datetime.utcnow()
        health.next_check = health.last_check + timedelta(seconds=self.check_interval)
        await self._calculate_overall_health(provider_name)
    
    async def _update_health_metrics(self, provider_name: str, success: bool, 
                                   latency_ms: float, cost: float) -> None:
        """
        Update health metrics for a provider
        
        Args:
            provider_name: Provider name
            success: Whether the call was successful
            latency_ms: Response latency in milliseconds
            cost: Cost of the call
        """
        health = self.provider_health[provider_name]
        now = datetime.utcnow()
        
        # Get cost statistics for comparison
        cost_stats = self.provider_manager.get_cost_statistics()
        provider_stats = cost_stats.get('providers', {}).get(provider_name, {})
        baseline_cost = provider_stats.get('cost', 0) / max(1, provider_stats.get('calls', 1))
        
        # Update latency metric
        latency_status = HealthStatus.HEALTHY
        if latency_ms > self.default_thresholds['latency_critical']:
            latency_status = HealthStatus.CRITICAL
        elif latency_ms > self.default_thresholds['latency_warning']:
            latency_status = HealthStatus.WARNING
        
        health.metrics['latency'] = HealthMetric(
            name='Response Latency',
            value=latency_ms,
            status=latency_status,
            threshold_warning=self.default_thresholds['latency_warning'],
            threshold_critical=self.default_thresholds['latency_critical'],
            unit='ms',
            timestamp=now
        )
        
        # Update success rate metric (calculate from recent history)
        recent_calls = self._get_recent_call_history(provider_name, hours=1)
        if recent_calls:
            success_rate = sum(1 for call in recent_calls if call.get('success', False)) / len(recent_calls)
        else:
            success_rate = 1.0 if success else 0.0
        
        success_status = HealthStatus.HEALTHY
        if success_rate < self.default_thresholds['success_rate_critical']:
            success_status = HealthStatus.CRITICAL
        elif success_rate < self.default_thresholds['success_rate_warning']:
            success_status = HealthStatus.WARNING
        
        health.metrics['success_rate'] = HealthMetric(
            name='Success Rate',
            value=success_rate,
            status=success_status,
            threshold_warning=self.default_thresholds['success_rate_warning'],
            threshold_critical=self.default_thresholds['success_rate_critical'],
            unit='%',
            timestamp=now
        )
        
        # Update cost efficiency metric
        cost_efficiency = cost / max(0.001, baseline_cost) if baseline_cost > 0 else 1.0
        
        cost_status = HealthStatus.HEALTHY
        if cost_efficiency > self.default_thresholds['cost_efficiency_critical']:
            cost_status = HealthStatus.WARNING  # Cost issues are warnings, not critical
        elif cost_efficiency > self.default_thresholds['cost_efficiency_warning']:
            cost_status = HealthStatus.WARNING
        
        health.metrics['cost_efficiency'] = HealthMetric(
            name='Cost Efficiency',
            value=cost_efficiency,
            status=cost_status,
            threshold_warning=self.default_thresholds['cost_efficiency_warning'],
            threshold_critical=self.default_thresholds['cost_efficiency_critical'],
            unit='ratio',
            timestamp=now
        )\n        \n        # Update consecutive failures metric\n        failure_status = HealthStatus.HEALTHY\n        if health.consecutive_failures >= self.default_thresholds['consecutive_failures_critical']:\n            failure_status = HealthStatus.CRITICAL\n        elif health.consecutive_failures >= self.default_thresholds['consecutive_failures_warning']:\n            failure_status = HealthStatus.WARNING\n        \n        health.metrics['consecutive_failures'] = HealthMetric(\n            name='Consecutive Failures',\n            value=health.consecutive_failures,\n            status=failure_status,\n            threshold_warning=self.default_thresholds['consecutive_failures_warning'],\n            threshold_critical=self.default_thresholds['consecutive_failures_critical'],\n            unit='count',\n            timestamp=now\n        )\n    \n    def _get_recent_call_history(self, provider_name: str, hours: int = 1) -> List[Dict[str, Any]]:\n        \"\"\"Get recent call history for a provider\"\"\"\n        cutoff_time = datetime.utcnow() - timedelta(hours=hours)\n        \n        # Get from provider manager's call history if available\n        provider = self.provider_manager.get_provider(provider_name)\n        if hasattr(provider, 'call_history'):\n            return [\n                {\n                    'success': call.success,\n                    'timestamp': call.timestamp,\n                    'latency_ms': call.latency_ms,\n                    'cost': call.cost\n                }\n                for call in provider.call_history\n                if call.timestamp >= cutoff_time\n            ]\n        \n        return []\n    \n    async def _calculate_overall_health(self, provider_name: str) -> None:\n        \"\"\"Calculate overall health status for a provider\"\"\"\n        health = self.provider_health[provider_name]\n        \n        if not health.metrics:\n            health.overall_status = HealthStatus.UNKNOWN\n            return\n        \n        # Count status levels\n        status_counts = {\n            HealthStatus.CRITICAL: 0,\n            HealthStatus.WARNING: 0,\n            HealthStatus.HEALTHY: 0\n        }\n        \n        for metric in health.metrics.values():\n            if metric.status in status_counts:\n                status_counts[metric.status] += 1\n        \n        # Determine overall status\n        if status_counts[HealthStatus.CRITICAL] > 0:\n            new_status = HealthStatus.CRITICAL\n        elif status_counts[HealthStatus.WARNING] > 1:  # Multiple warnings = critical\n            new_status = HealthStatus.CRITICAL\n        elif status_counts[HealthStatus.WARNING] > 0:\n            new_status = HealthStatus.WARNING\n        else:\n            new_status = HealthStatus.HEALTHY\n        \n        # Check for status changes and trigger alerts\n        old_status = health.overall_status\n        health.overall_status = new_status\n        \n        if old_status != new_status:\n            await self._trigger_health_alert(provider_name, old_status, new_status)\n        \n        # Calculate uptime percentage\n        health.uptime_percentage = await self._calculate_uptime(provider_name)\n    \n    async def _calculate_uptime(self, provider_name: str, hours: int = 24) -> float:\n        \"\"\"Calculate uptime percentage for a provider\"\"\"\n        # This is a simplified calculation\n        # In a real implementation, you'd track detailed uptime/downtime periods\n        health = self.provider_health[provider_name]\n        \n        if health.consecutive_failures == 0:\n            return 100.0\n        elif health.consecutive_failures < 3:\n            return 95.0\n        elif health.consecutive_failures < 5:\n            return 80.0\n        else:\n            return 50.0\n    \n    async def _trigger_health_alert(self, provider_name: str, \n                                  old_status: HealthStatus, new_status: HealthStatus) -> None:\n        \"\"\"Trigger a health status change alert\"\"\"\n        if new_status == HealthStatus.CRITICAL and old_status != HealthStatus.CRITICAL:\n            alert = HealthAlert(\n                provider_name=provider_name,\n                alert_type='degradation',\n                severity=HealthStatus.CRITICAL,\n                message=f\"Provider {provider_name} health degraded to CRITICAL\"\n            )\n        elif new_status == HealthStatus.WARNING and old_status == HealthStatus.HEALTHY:\n            alert = HealthAlert(\n                provider_name=provider_name,\n                alert_type='degradation',\n                severity=HealthStatus.WARNING,\n                message=f\"Provider {provider_name} health degraded to WARNING\"\n            )\n        elif new_status == HealthStatus.HEALTHY and old_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:\n            alert = HealthAlert(\n                provider_name=provider_name,\n                alert_type='recovery',\n                severity=HealthStatus.HEALTHY,\n                message=f\"Provider {provider_name} health recovered to HEALTHY\"\n            )\n        else:\n            return  # No alert needed\n        \n        self.alerts.append(alert)\n        \n        # Call registered alert callbacks\n        for callback in self.alert_callbacks:\n            try:\n                await asyncio.get_event_loop().run_in_executor(None, callback, alert)\n            except Exception as e:\n                logger.error(f\"Error in health alert callback: {e}\")\n        \n        # Log the alert\n        if alert.severity == HealthStatus.CRITICAL:\n            logger.error(alert.message)\n        elif alert.severity == HealthStatus.WARNING:\n            logger.warning(alert.message)\n        else:\n            logger.info(alert.message)\n    \n    def register_alert_callback(self, callback: Callable[[HealthAlert], None]) -> None:\n        \"\"\"Register a callback to be called when health alerts are triggered\"\"\"\n        self.alert_callbacks.append(callback)\n    \n    async def get_provider_health(self, provider_name: str) -> Optional[ProviderHealth]:\n        \"\"\"Get health status for a specific provider\"\"\"\n        return self.provider_health.get(provider_name)\n    \n    async def get_all_provider_health(self) -> Dict[str, ProviderHealth]:\n        \"\"\"Get health status for all providers\"\"\"\n        return self.provider_health.copy()\n    \n    async def get_healthy_providers(self) -> List[str]:\n        \"\"\"Get list of currently healthy providers\"\"\"\n        return [\n            name for name, health in self.provider_health.items()\n            if health.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]\n        ]\n    \n    async def get_best_provider(self, task_type: Optional[TaskType] = None) -> Optional[str]:\n        \"\"\"\n        Get the best available provider based on health metrics\n        \n        Args:\n            task_type: Optional task type for provider optimization\n            \n        Returns:\n            str: Best provider name, or None if no healthy providers\n        \"\"\"\n        healthy_providers = await self.get_healthy_providers()\n        \n        if not healthy_providers:\n            return None\n        \n        # Score providers based on health metrics\n        provider_scores = {}\n        \n        for provider_name in healthy_providers:\n            health = self.provider_health[provider_name]\n            score = 0\n            \n            # Health status score\n            if health.overall_status == HealthStatus.HEALTHY:\n                score += 100\n            elif health.overall_status == HealthStatus.WARNING:\n                score += 70\n            else:\n                score += 30\n            \n            # Latency score (lower is better)\n            if 'latency' in health.metrics:\n                latency = health.metrics['latency'].value\n                score += max(0, 50 - (latency / 100))  # Penalize high latency\n            \n            # Success rate score\n            if 'success_rate' in health.metrics:\n                score += health.metrics['success_rate'].value * 50\n            \n            # Cost efficiency score (lower cost is better)\n            if 'cost_efficiency' in health.metrics:\n                efficiency = health.metrics['cost_efficiency'].value\n                score += max(0, 50 - (efficiency - 1) * 25)  # Penalize high cost\n            \n            # Uptime score\n            score += health.uptime_percentage * 0.5\n            \n            provider_scores[provider_name] = score\n        \n        # Return provider with highest score\n        best_provider = max(provider_scores.items(), key=lambda x: x[1])\n        return best_provider[0]\n    \n    async def get_recent_alerts(self, hours: int = 24) -> List[HealthAlert]:\n        \"\"\"Get recent health alerts\"\"\"\n        cutoff_time = datetime.utcnow() - timedelta(hours=hours)\n        return [\n            alert for alert in self.alerts\n            if alert.timestamp >= cutoff_time\n        ]\n    \n    async def get_health_summary(self) -> Dict[str, Any]:\n        \"\"\"Get overall health summary\"\"\"\n        healthy_count = sum(\n            1 for health in self.provider_health.values()\n            if health.overall_status == HealthStatus.HEALTHY\n        )\n        warning_count = sum(\n            1 for health in self.provider_health.values()\n            if health.overall_status == HealthStatus.WARNING\n        )\n        critical_count = sum(\n            1 for health in self.provider_health.values()\n            if health.overall_status == HealthStatus.CRITICAL\n        )\n        \n        total_providers = len(self.provider_health)\n        recent_alerts = await self.get_recent_alerts(hours=24)\n        \n        return {\n            \"overall_status\": (\n                HealthStatus.CRITICAL if critical_count > 0\n                else HealthStatus.WARNING if warning_count > 0\n                else HealthStatus.HEALTHY\n            ),\n            \"provider_counts\": {\n                \"total\": total_providers,\n                \"healthy\": healthy_count,\n                \"warning\": warning_count,\n                \"critical\": critical_count\n            },\n            \"monitoring\": self.monitoring,\n            \"check_interval\": self.check_interval,\n            \"recent_alerts\": len(recent_alerts),\n            \"last_check\": max(\n                (health.last_check for health in self.provider_health.values()),\n                default=datetime.utcnow()\n            ).isoformat()\n        }\n\n\n# Default alert handlers\ndef default_console_health_alert_handler(alert: HealthAlert) -> None:\n    \"\"\"Default console health alert handler\"\"\"\n    emoji = {\n        'degradation': '🔴',\n        'recovery': '🟢',\n        'failure': '❌'\n    }.get(alert.alert_type, '⚠️')\n    \n    print(f\"{emoji} HEALTH ALERT [{alert.severity.upper()}]: {alert.message}\")\n\n\ndef default_file_health_alert_handler(alert: HealthAlert, log_file: str = \"health_alerts.log\") -> None:\n    \"\"\"Default file health alert handler\"\"\"\n    with open(log_file, 'a') as f:\n        f.write(f\"{alert.timestamp.isoformat()} [{alert.alert_type}] {alert.provider_name}: {alert.message}\\n\")\n\n\n# Global health monitor instance\n_global_health_monitor: Optional[ProviderHealthMonitor] = None\n\n\ndef get_global_health_monitor(provider_manager: AIProviderManager) -> ProviderHealthMonitor:\n    \"\"\"Get or create the global health monitor instance\"\"\"\n    global _global_health_monitor\n    if _global_health_monitor is None:\n        _global_health_monitor = ProviderHealthMonitor(provider_manager)\n        _global_health_monitor.register_alert_callback(default_console_health_alert_handler)\n    return _global_health_monitor