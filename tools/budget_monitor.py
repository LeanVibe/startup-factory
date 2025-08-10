#!/usr/bin/env python3
"""
Budget Monitoring System for AI Provider Usage
Tracks costs, enforces limits, and provides alerts for startup factory operations.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any

from core_types import StartupFactoryError

logger = logging.getLogger(__name__)


class BudgetExceededError(StartupFactoryError):
    """Raised when budget limits are exceeded"""
    pass


class BudgetWarningError(StartupFactoryError):
    """Raised when budget warnings are triggered"""
    pass


@dataclass
class BudgetLimit:
    """Budget limit configuration"""
    startup_id: str
    daily_limit: float
    weekly_limit: float
    monthly_limit: float
    total_limit: float
    warning_threshold: float = 0.8  # Warn at 80% of limit
    hard_stop: bool = True  # Stop processing when limit exceeded
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class BudgetAlert:
    """Budget alert notification"""
    startup_id: str
    alert_type: str  # 'warning', 'limit_exceeded', 'emergency_stop'
    message: str
    current_spend: float
    limit_amount: float
    percentage_used: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SpendingRecord:
    """Record of spending for cost tracking"""
    startup_id: str
    provider: str
    task_id: str
    cost: float
    tokens_used: int
    timestamp: datetime
    task_type: str
    success: bool


class BudgetMonitor:
    """
    Comprehensive budget monitoring system
    
    Features:
    - Real-time cost tracking per startup
    - Multiple budget limit types (daily, weekly, monthly, total)
    - Alert system with configurable thresholds
    - Automatic shutdown on budget exceeded
    - Detailed spending analytics
    """
    
    def __init__(self):
        self.budget_limits: Dict[str, BudgetLimit] = {}
        self.spending_records: List[SpendingRecord] = []
        self.alerts: List[BudgetAlert] = []
        self.alert_callbacks: List[Callable[[BudgetAlert], None]] = []
        self._lock = asyncio.Lock()
        
        # Global limits
        self.global_daily_limit = 1000.0  # $1000 per day across all startups
        self.global_monthly_limit = 15000.0  # $15k per month across all startups
        
        logger.info("Budget monitor initialized")
    
    async def set_budget_limit(self, startup_id: str, 
                              daily_limit: float = 50.0,
                              weekly_limit: float = 300.0,
                              monthly_limit: float = 1000.0,
                              total_limit: float = 15000.0,
                              warning_threshold: float = 0.8,
                              hard_stop: bool = True) -> None:
        """
        Set budget limits for a startup
        
        Args:
            startup_id: Startup identifier
            daily_limit: Maximum spend per day
            weekly_limit: Maximum spend per week
            monthly_limit: Maximum spend per month
            total_limit: Maximum total spend for the startup
            warning_threshold: Percentage at which to issue warnings
            hard_stop: Whether to stop processing when limit exceeded
        """
        # Validate inputs
        if not startup_id or not startup_id.strip():
            raise ValueError("Startup ID cannot be empty")
        if daily_limit < 0:
            raise ValueError("Daily limit cannot be negative")
        if weekly_limit < 0:
            raise ValueError("Weekly limit cannot be negative")
        if monthly_limit < 0:
            raise ValueError("Monthly limit cannot be negative")
        if total_limit < 0:
            raise ValueError("Total limit cannot be negative")
        if not 0 <= warning_threshold <= 1.0:
            raise ValueError("Warning threshold must be between 0 and 1.0")
        
        async with self._lock:
            self.budget_limits[startup_id] = BudgetLimit(
                startup_id=startup_id,
                daily_limit=daily_limit,
                weekly_limit=weekly_limit,
                monthly_limit=monthly_limit,
                total_limit=total_limit,
                warning_threshold=warning_threshold,
                hard_stop=hard_stop
            )
        
        logger.info(f"Set budget limits for {startup_id}: daily=${daily_limit}, "
                   f"monthly=${monthly_limit}, total=${total_limit}")
    
    async def record_spending(self, startup_id: str, provider: str, task_id: str,
                             cost: float, tokens_used: int, task_type: str,
                             success: bool = True) -> None:
        """
        Record a spending transaction
        
        Args:
            startup_id: Startup identifier
            provider: AI provider name
            task_id: Task identifier
            cost: Cost of the operation
            tokens_used: Number of tokens consumed
            task_type: Type of task executed
            success: Whether the task was successful
        """
        # Validate inputs
        if not startup_id or not startup_id.strip():
            raise ValueError("Startup ID cannot be empty")
        if not provider or not provider.strip():
            raise ValueError("Provider cannot be empty")
        if cost < 0:
            raise ValueError("Cost cannot be negative")
        if tokens_used < 0:
            raise ValueError("Tokens used cannot be negative")
        
        async with self._lock:
            # Record the spending
            record = SpendingRecord(
                startup_id=startup_id,
                provider=provider,
                task_id=task_id,
                cost=cost,
                tokens_used=tokens_used,
                timestamp=datetime.now(UTC),
                task_type=task_type,
                success=success
            )
            self.spending_records.append(record)
            
            # Check budget limits after recording (only for successful transactions)
            if success:
                await self._check_budget_limits(startup_id, cost)
        
        logger.debug(f"Recorded spending: {startup_id} ${cost:.4f} via {provider}")
    
    async def _check_budget_limits(self, startup_id: str, new_cost: float) -> None:
        """Check if budget limits are exceeded and trigger alerts"""
        budget_limit = self.budget_limits.get(startup_id)
        if not budget_limit:
            # No limits set for this startup
            return
        
        now = datetime.now(UTC)
        
        # Calculate current spending in different time periods
        daily_spend = await self._get_spending_in_period(startup_id, now - timedelta(days=1), now)
        weekly_spend = await self._get_spending_in_period(startup_id, now - timedelta(weeks=1), now)
        monthly_spend = await self._get_spending_in_period(startup_id, now - timedelta(days=30), now)
        total_spend = await self._get_total_spending(startup_id)
        
        # Check each limit type
        limits_to_check = [
            ('daily', daily_spend, budget_limit.daily_limit),
            ('weekly', weekly_spend, budget_limit.weekly_limit),
            ('monthly', monthly_spend, budget_limit.monthly_limit),
            ('total', total_spend, budget_limit.total_limit)
        ]
        
        for limit_type, current_spend, limit_amount in limits_to_check:
            if limit_amount <= 0:
                continue  # Skip if no limit set
            
            percentage_used = current_spend / limit_amount
            
            # Check for warnings
            if percentage_used >= budget_limit.warning_threshold and percentage_used < 1.0:
                alert = BudgetAlert(
                    startup_id=startup_id,
                    alert_type='warning',
                    message=f"{limit_type.title()} budget warning: ${current_spend:.2f} of ${limit_amount:.2f} used ({percentage_used:.1%})",
                    current_spend=current_spend,
                    limit_amount=limit_amount,
                    percentage_used=percentage_used
                )
                await self._trigger_alert(alert)
            
            # Check for limit exceeded
            elif percentage_used >= 1.0:
                alert = BudgetAlert(
                    startup_id=startup_id,
                    alert_type='limit_exceeded',
                    message=f"{limit_type.title()} budget exceeded: ${current_spend:.2f} exceeds ${limit_amount:.2f} limit",
                    current_spend=current_spend,
                    limit_amount=limit_amount,
                    percentage_used=percentage_used
                )
                await self._trigger_alert(alert)
                
                if budget_limit.hard_stop:
                    raise BudgetExceededError(
                        f"Budget limit exceeded for {startup_id}: {limit_type} "
                        f"${current_spend:.2f} > ${limit_amount:.2f}"
                    )
    
    async def _get_spending_in_period(self, startup_id: str, start_time: datetime, 
                                     end_time: datetime) -> float:
        """Get total spending for a startup in a time period"""
        return sum(
            record.cost for record in self.spending_records
            if (record.startup_id == startup_id and 
                start_time <= record.timestamp <= end_time and
                record.success)
        )
    
    async def _get_total_spending(self, startup_id: str) -> float:
        """Get total spending for a startup"""
        return sum(
            record.cost for record in self.spending_records
            if record.startup_id == startup_id and record.success
        )
    
    async def _trigger_alert(self, alert: BudgetAlert) -> None:
        """Trigger a budget alert"""
        self.alerts.append(alert)
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    # Run synchronous callback in executor to avoid blocking
                    await asyncio.get_event_loop().run_in_executor(None, callback, alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        # Log the alert
        if alert.alert_type == 'warning':
            logger.warning(alert.message)
        else:
            logger.error(alert.message)
    
    def register_alert_callback(self, callback: Callable[[BudgetAlert], None]) -> None:
        """Register a callback to be called when alerts are triggered"""
        self.alert_callbacks.append(callback)
    
    async def can_proceed_with_task(self, startup_id: str, estimated_cost: float) -> bool:
        """
        Check if a task can proceed without exceeding budget limits
        
        Args:
            startup_id: Startup identifier
            estimated_cost: Estimated cost of the task
            
        Returns:
            bool: True if task can proceed, False otherwise
        """
        budget_limit = self.budget_limits.get(startup_id)
        if not budget_limit:
            return True  # No limits set
        
        now = datetime.now(UTC)
        
        # Calculate current spending + estimated cost
        daily_spend = await self._get_spending_in_period(startup_id, now - timedelta(days=1), now)
        weekly_spend = await self._get_spending_in_period(startup_id, now - timedelta(weeks=1), now)
        monthly_spend = await self._get_spending_in_period(startup_id, now - timedelta(days=30), now)
        total_spend = await self._get_total_spending(startup_id)
        
        # Check if adding estimated cost would exceed any limits
        if (budget_limit.daily_limit > 0 and 
            daily_spend + estimated_cost > budget_limit.daily_limit):
            return False
        
        if (budget_limit.weekly_limit > 0 and 
            weekly_spend + estimated_cost > budget_limit.weekly_limit):
            return False
        
        if (budget_limit.monthly_limit > 0 and 
            monthly_spend + estimated_cost > budget_limit.monthly_limit):
            return False
        
        if (budget_limit.total_limit > 0 and 
            total_spend + estimated_cost > budget_limit.total_limit):
            return False
        
        return True
    
    async def get_budget_status(self, startup_id: str) -> Dict[str, Any]:
        """
        Get current budget status for a startup
        
        Args:
            startup_id: Startup identifier
            
        Returns:
            dict: Budget status information
        """
        budget_limit = self.budget_limits.get(startup_id)
        if not budget_limit:
            return {
                "startup_id": startup_id,
                "has_limits": False,
                "total_spent": await self._get_total_spending(startup_id)
            }
        
        now = datetime.now(UTC)
        
        daily_spend = await self._get_spending_in_period(startup_id, now - timedelta(days=1), now)
        weekly_spend = await self._get_spending_in_period(startup_id, now - timedelta(weeks=1), now)
        monthly_spend = await self._get_spending_in_period(startup_id, now - timedelta(days=30), now)
        total_spend = await self._get_total_spending(startup_id)
        
        return {
            "startup_id": startup_id,
            "has_limits": True,
            "limits": {
                "daily": budget_limit.daily_limit,
                "weekly": budget_limit.weekly_limit,
                "monthly": budget_limit.monthly_limit,
                "total": budget_limit.total_limit
            },
            "current_spending": {
                "daily": daily_spend,
                "weekly": weekly_spend,
                "monthly": monthly_spend,
                "total": total_spend
            },
            "utilization": {
                "daily": daily_spend / max(0.01, budget_limit.daily_limit) if budget_limit.daily_limit > 0 else 0,
                "weekly": weekly_spend / max(0.01, budget_limit.weekly_limit) if budget_limit.weekly_limit > 0 else 0,
                "monthly": monthly_spend / max(0.01, budget_limit.monthly_limit) if budget_limit.monthly_limit > 0 else 0,
                "total": total_spend / max(0.01, budget_limit.total_limit) if budget_limit.total_limit > 0 else 0
            },
            "warning_threshold": budget_limit.warning_threshold,
            "hard_stop": budget_limit.hard_stop
        }
    
    async def get_global_budget_status(self) -> Dict[str, Any]:
        """Get global budget status across all startups"""
        now = datetime.now(UTC)
        
        # Calculate global spending
        daily_records = [
            record for record in self.spending_records
            if record.timestamp >= now - timedelta(days=1) and record.success
        ]
        monthly_records = [
            record for record in self.spending_records
            if record.timestamp >= now - timedelta(days=30) and record.success
        ]
        
        daily_spend = sum(record.cost for record in daily_records)
        monthly_spend = sum(record.cost for record in monthly_records)
        total_spend = sum(record.cost for record in self.spending_records if record.success)
        
        # Provider breakdown
        provider_spending = {}
        for record in self.spending_records:
            if record.success:
                if record.provider not in provider_spending:
                    provider_spending[record.provider] = 0
                provider_spending[record.provider] += record.cost
        
        # Task type breakdown
        task_type_spending = {}
        for record in self.spending_records:
            if record.success:
                if record.task_type not in task_type_spending:
                    task_type_spending[record.task_type] = 0
                task_type_spending[record.task_type] += record.cost
        
        return {
            "global_limits": {
                "daily": self.global_daily_limit,
                "monthly": self.global_monthly_limit
            },
            "current_spending": {
                "daily": daily_spend,
                "monthly": monthly_spend,
                "total": total_spend
            },
            "utilization": {
                "daily": daily_spend / max(0.01, self.global_daily_limit),
                "monthly": monthly_spend / max(0.01, self.global_monthly_limit)
            },
            "provider_breakdown": provider_spending,
            "task_type_breakdown": task_type_spending,
            "total_transactions": len(self.spending_records),
            "successful_transactions": len([r for r in self.spending_records if r.success]),
            "active_startups": len(set(record.startup_id for record in self.spending_records))
        }
    
    async def get_recent_alerts(self, hours: int = 24) -> List[BudgetAlert]:
        """Get recent alerts within specified hours"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        return [
            alert for alert in self.alerts
            if alert.timestamp >= cutoff_time
        ]
    
    async def get_remaining_budget(self, startup_id: str) -> float:
        """
        Get remaining budget for a startup (based on daily limit)
        
        Args:
            startup_id: Startup identifier
            
        Returns:
            float: Remaining daily budget amount
        """
        budget_limit = self.budget_limits.get(startup_id)
        if not budget_limit or budget_limit.daily_limit <= 0:
            return float('inf')  # No limit set
        
        now = datetime.now(UTC)
        daily_spend = await self._get_spending_in_period(startup_id, now - timedelta(days=1), now)
        return max(0.0, budget_limit.daily_limit - daily_spend)
    
    async def get_spending_summary(self, startup_id: str) -> Dict[str, Any]:
        """
        Get spending summary for a startup
        
        Args:
            startup_id: Startup identifier
            
        Returns:
            dict: Spending summary by provider and time period
        """
        now = datetime.now(UTC)
        
        # Calculate spending by time period
        daily_spend = await self._get_spending_in_period(startup_id, now - timedelta(days=1), now)
        weekly_spend = await self._get_spending_in_period(startup_id, now - timedelta(weeks=1), now)
        monthly_spend = await self._get_spending_in_period(startup_id, now - timedelta(days=30), now)
        total_spend = await self._get_total_spending(startup_id)
        
        # Calculate spending by provider
        provider_spending = {}
        for record in self.spending_records:
            if record.startup_id == startup_id and record.success:
                if record.provider not in provider_spending:
                    provider_spending[record.provider] = 0
                provider_spending[record.provider] += record.cost
        
        return {
            'total': total_spend,
            'daily': daily_spend,
            'weekly': weekly_spend,
            'monthly': monthly_spend,
            'by_provider': provider_spending
        }
    
    async def export_spending_report(self, startup_id: Optional[str] = None,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Export detailed spending report
        
        Args:
            startup_id: Filter by startup (optional)
            start_date: Start date for report (optional)
            end_date: End date for report (optional)
            
        Returns:
            dict: Detailed spending report
        """
        filtered_records = self.spending_records
        
        # Apply filters
        if startup_id:
            filtered_records = [r for r in filtered_records if r.startup_id == startup_id]
        
        if start_date:
            filtered_records = [r for r in filtered_records if r.timestamp >= start_date]
        
        if end_date:
            filtered_records = [r for r in filtered_records if r.timestamp <= end_date]
        
        # Calculate statistics
        total_cost = sum(r.cost for r in filtered_records if r.success)
        total_tokens = sum(r.tokens_used for r in filtered_records if r.success)
        success_rate = (
            len([r for r in filtered_records if r.success]) / max(1, len(filtered_records))
        )
        
        # Group by provider
        provider_stats = {}
        for record in filtered_records:
            if record.provider not in provider_stats:
                provider_stats[record.provider] = {
                    'total_cost': 0,
                    'total_tokens': 0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'total_calls': 0
                }
            
            stats = provider_stats[record.provider]
            stats['total_calls'] += 1
            
            if record.success:
                stats['successful_calls'] += 1
                stats['total_cost'] += record.cost
                stats['total_tokens'] += record.tokens_used
            else:
                stats['failed_calls'] += 1
        
        return {
            "report_period": {
                "start": start_date.isoformat() if start_date else "beginning",
                "end": end_date.isoformat() if end_date else "now"
            },
            "filter": {
                "startup_id": startup_id
            },
            "summary": {
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "total_transactions": len(filtered_records),
                "success_rate": success_rate,
                "average_cost_per_transaction": total_cost / max(1, len(filtered_records))
            },
            "provider_breakdown": provider_stats,
            "transactions": [
                {
                    "startup_id": r.startup_id,
                    "provider": r.provider,
                    "task_id": r.task_id,
                    "cost": r.cost,
                    "tokens_used": r.tokens_used,
                    "task_type": r.task_type,
                    "success": r.success,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in filtered_records[-100:]  # Last 100 transactions
            ]
        }


# Default alert handlers
def default_console_alert_handler(alert: BudgetAlert) -> None:
    """Default console alert handler"""
    print(f"🚨 BUDGET ALERT [{alert.alert_type.upper()}]: {alert.message}")


def default_file_alert_handler(alert: BudgetAlert, log_file: str = "budget_alerts.log") -> None:
    """Default file alert handler"""
    with open(log_file, 'a') as f:
        f.write(f"{alert.timestamp.isoformat()} [{alert.alert_type}] {alert.startup_id}: {alert.message}\n")


# Global budget monitor instance
_global_budget_monitor: Optional[BudgetMonitor] = None


def get_global_budget_monitor() -> BudgetMonitor:
    """Get or create the global budget monitor instance"""
    global _global_budget_monitor
    if _global_budget_monitor is None:
        _global_budget_monitor = BudgetMonitor()
        _global_budget_monitor.register_alert_callback(default_console_alert_handler)
    return _global_budget_monitor