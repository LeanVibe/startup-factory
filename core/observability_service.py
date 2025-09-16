#!/usr/bin/env python3
"""
Observability Service - Core Service 7/8
Consolidates: health_monitor.py, monitoring_dashboard.py, analytics_engine.py
Production-grade monitoring, metrics, logging, and business intelligence.
"""

import asyncio
import json
import logging
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading

from ._compat import Console, Table, Panel, Live

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - psutil optional
    psutil = None  # type: ignore

console = Console()
logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


class MetricType(str, Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    check_function: Callable
    interval_seconds: int = 60
    timeout_seconds: int = 10
    enabled: bool = True
    last_check: Optional[datetime] = None
    status: HealthStatus = HealthStatus.HEALTHY
    error_message: Optional[str] = None


@dataclass
class Metric:
    """System metric"""
    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class Alert:
    """System alert"""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    source: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None


@dataclass
class BusinessMetrics:
    """Business intelligence metrics"""
    startups_created_today: int = 0
    startups_created_total: int = 0
    successful_deployments: int = 0
    failed_deployments: int = 0
    active_tenants: int = 0
    total_revenue: float = 0.0
    average_time_to_mvp: float = 0.0
    user_satisfaction_score: float = 0.0
    
    # Conversion metrics
    conversation_completion_rate: float = 0.0
    blueprint_approval_rate: float = 0.0
    deployment_success_rate: float = 0.0


class ObservabilityService:
    """
    Production-grade observability service for monitoring, metrics, and business intelligence.
    Consolidates health_monitor.py, monitoring_dashboard.py, analytics_engine.py
    """
    
    def __init__(self, db_path: str = "observability.db"):
        self.db_path = db_path
        self.health_checks: Dict[str, HealthCheck] = {}
        self.metrics_buffer: List[Metric] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Business metrics tracking
        self.business_metrics = BusinessMetrics()
        
        # Monitoring state
        self.monitoring_enabled = True
        self.monitoring_tasks: List[asyncio.Task] = []
        
        # Initialize database
        self._init_database()
        
        # Register default health checks
        self._register_default_health_checks()
        
        # Start monitoring
        self._start_monitoring()
    
    def _init_database(self):
        """Initialize SQLite database for metrics storage"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    labels TEXT,
                    description TEXT
                )
            """)
            
            # Alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    source TEXT NOT NULL,
                    triggered_at TEXT NOT NULL,
                    resolved_at TEXT,
                    metadata TEXT
                )
            """)
            
            # Business metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS business_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    startups_created_today INTEGER,
                    startups_created_total INTEGER,
                    successful_deployments INTEGER,
                    failed_deployments INTEGER,
                    active_tenants INTEGER,
                    total_revenue REAL,
                    average_time_to_mvp REAL,
                    user_satisfaction_score REAL,
                    conversation_completion_rate REAL,
                    blueprint_approval_rate REAL,
                    deployment_success_rate REAL
                )
            """)
            
            conn.commit()
    
    def _register_default_health_checks(self):
        """Register default system health checks"""
        
        # System health checks
        self.register_health_check("system_memory", self._check_system_memory, 30)
        self.register_health_check("system_cpu", self._check_system_cpu, 30)
        self.register_health_check("system_disk", self._check_system_disk, 60)
        self.register_health_check("database", self._check_database, 60)
        
        # Application health checks
        self.register_health_check("ai_providers", self._check_ai_providers, 120)
        self.register_health_check("docker", self._check_docker, 120)
    
    def register_health_check(
        self,
        name: str,
        check_function: Callable,
        interval_seconds: int = 60,
        timeout_seconds: int = 10
    ):
        """Register a new health check"""
        
        health_check = HealthCheck(
            name=name,
            check_function=check_function,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds
        )
        
        self.health_checks[name] = health_check
        logger.info(f"Registered health check: {name}")
    
    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE, 
                     labels: Optional[Dict[str, str]] = None, description: str = ""):
        """Record a metric"""
        
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            labels=labels or {},
            description=description
        )
        
        self.metrics_buffer.append(metric)
        
        # Flush buffer if it gets too large
        if len(self.metrics_buffer) > 1000:
            asyncio.create_task(self._flush_metrics())
    
    async def _flush_metrics(self):
        """Flush metrics buffer to database"""
        
        if not self.metrics_buffer:
            return
        
        metrics_to_flush = self.metrics_buffer.copy()
        self.metrics_buffer.clear()
        
        with sqlite3.connect(self.db_path) as conn:
            for metric in metrics_to_flush:
                conn.execute("""
                    INSERT INTO metrics (name, metric_type, value, timestamp, labels, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    metric.name,
                    metric.metric_type.value,
                    metric.value,
                    metric.timestamp.isoformat(),
                    json.dumps(metric.labels),
                    metric.description
                ))
            
            conn.commit()
    
    def trigger_alert(self, name: str, message: str, severity: AlertSeverity = AlertSeverity.WARNING,
                     source: str = "system", metadata: Optional[Dict[str, Any]] = None):
        """Trigger a system alert"""
        
        alert_id = f"{name}_{int(time.time())}"
        
        alert = Alert(
            alert_id=alert_id,
            name=name,
            severity=severity,
            message=message,
            source=source,
            metadata=metadata or {}
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alerts (alert_id, name, severity, message, source, triggered_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.name,
                alert.severity.value,
                alert.message,
                alert.source,
                alert.triggered_at.isoformat(),
                json.dumps(alert.metadata)
            ))
            conn.commit()
        
        console.print(f"🚨 Alert: {severity.value.upper()} - {message}")
        logger.warning(f"Alert triggered: {name} - {message}")
    
    def resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved_at = datetime.utcnow()
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE alerts SET resolved_at = ? WHERE alert_id = ?
                """, (alert.resolved_at.isoformat(), alert_id))
                conn.commit()
            
            del self.active_alerts[alert_id]
            console.print(f"✅ Alert resolved: {alert.name}")
    
    def update_business_metrics(self, **metrics):
        """Update business metrics"""
        
        for key, value in metrics.items():
            if hasattr(self.business_metrics, key):
                setattr(self.business_metrics, key, value)
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            metrics_data = asdict(self.business_metrics)
            columns = list(metrics_data.keys())
            values = [metrics_data[col] for col in columns]
            
            placeholders = ", ".join(["?"] * len(columns))
            column_names = ", ".join(columns)
            
            conn.execute(f"""
                INSERT INTO business_metrics (timestamp, {column_names})
                VALUES (?, {placeholders})
            """, [datetime.utcnow().isoformat()] + values)
            
            conn.commit()
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        
        # Run all health checks
        health_results = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, health_check in self.health_checks.items():
            try:
                if health_check.enabled:
                    # Run health check with timeout
                    result = await asyncio.wait_for(
                        health_check.check_function(),
                        timeout=health_check.timeout_seconds
                    )
                    
                    health_check.status = result.get("status", HealthStatus.HEALTHY)
                    health_check.error_message = result.get("error")
                    health_check.last_check = datetime.utcnow()
                    
                    health_results[name] = {
                        "status": health_check.status.value,
                        "last_check": health_check.last_check.isoformat(),
                        "error": health_check.error_message,
                        "details": result.get("details", {})
                    }
                    
                    # Update overall status
                    if health_check.status == HealthStatus.CRITICAL:
                        overall_status = HealthStatus.CRITICAL
                    elif health_check.status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.WARNING
                
            except asyncio.TimeoutError:
                health_check.status = HealthStatus.CRITICAL
                health_check.error_message = "Health check timeout"
                health_results[name] = {
                    "status": HealthStatus.CRITICAL.value,
                    "error": "Health check timeout"
                }
                overall_status = HealthStatus.CRITICAL
                
            except Exception as e:
                health_check.status = HealthStatus.CRITICAL
                health_check.error_message = str(e)
                health_results[name] = {
                    "status": HealthStatus.CRITICAL.value,
                    "error": str(e)
                }
                overall_status = HealthStatus.CRITICAL
        
        return {
            "overall_status": overall_status.value,
            "health_checks": health_results,
            "active_alerts": len(self.active_alerts),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the specified time period"""
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get recent metrics
            cursor = conn.execute("""
                SELECT name, AVG(value) as avg_value, COUNT(*) as count
                FROM metrics 
                WHERE timestamp > ? 
                GROUP BY name 
                ORDER BY name
            """, (since.isoformat(),))
            
            metrics_data = {row[0]: {"average": row[1], "count": row[2]} for row in cursor.fetchall()}
            
            # Get business metrics
            cursor = conn.execute("""
                SELECT * FROM business_metrics 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (since.isoformat(),))
            
            business_data = cursor.fetchone()
            
        return {
            "time_period_hours": hours,
            "system_metrics": metrics_data,
            "business_metrics": dict(zip([
                "timestamp", "startups_created_today", "startups_created_total",
                "successful_deployments", "failed_deployments", "active_tenants",
                "total_revenue", "average_time_to_mvp", "user_satisfaction_score",
                "conversation_completion_rate", "blueprint_approval_rate", "deployment_success_rate"
            ], business_data)) if business_data else {}
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        
        return [
            {
                "alert_id": alert.alert_id,
                "name": alert.name,
                "severity": alert.severity.value,
                "message": alert.message,
                "source": alert.source,
                "triggered_at": alert.triggered_at.isoformat(),
                "duration_minutes": (datetime.utcnow() - alert.triggered_at).total_seconds() / 60
            }
            for alert in self.active_alerts.values()
        ]
    
    def _start_monitoring(self):
        """Start background monitoring tasks"""
        
        async def health_check_loop():
            while self.monitoring_enabled:
                try:
                    # Run health checks
                    health_status = await self.get_system_health()
                    
                    # Check for critical issues
                    if health_status["overall_status"] == HealthStatus.CRITICAL.value:
                        self.trigger_alert(
                            "system_health",
                            "System health is critical",
                            AlertSeverity.CRITICAL,
                            "health_monitor"
                        )
                    
                    # Record health metrics
                    for name, check in health_status["health_checks"].items():
                        status_value = 1 if check["status"] == "healthy" else 0
                        self.record_metric(f"health_check_{name}", status_value, MetricType.GAUGE)
                    
                except Exception as e:
                    logger.error(f"Health check loop error: {e}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
        
        async def metrics_flush_loop():
            while self.monitoring_enabled:
                try:
                    await self._flush_metrics()
                except Exception as e:
                    logger.error(f"Metrics flush error: {e}")
                
                await asyncio.sleep(60)  # Flush every minute
        
        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(health_check_loop()),
            asyncio.create_task(metrics_flush_loop())
        ]
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        
        self.monitoring_enabled = False
        
        for task in self.monitoring_tasks:
            task.cancel()
    
    # Health Check Functions
    async def _check_system_memory(self) -> Dict[str, Any]:
        """Check system memory usage"""
        if not psutil:
            return {
                "status": HealthStatus.HEALTHY,
                "details": {"percent": 0.0, "available_gb": 0.0}
            }

        memory = psutil.virtual_memory()
        
        if memory.percent > 90:
            return {
                "status": HealthStatus.CRITICAL,
                "error": f"Memory usage critical: {memory.percent}%",
                "details": {"percent": memory.percent, "available_gb": memory.available / (1024**3)}
            }
        elif memory.percent > 80:
            return {
                "status": HealthStatus.WARNING,
                "error": f"Memory usage high: {memory.percent}%",
                "details": {"percent": memory.percent, "available_gb": memory.available / (1024**3)}
            }
        
        return {
            "status": HealthStatus.HEALTHY,
            "details": {"percent": memory.percent, "available_gb": memory.available / (1024**3)}
        }
    
    async def _check_system_cpu(self) -> Dict[str, Any]:
        """Check system CPU usage"""
        if not psutil:
            return {
                "status": HealthStatus.HEALTHY,
                "details": {"percent": 0.0}
            }

        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent > 95:
            return {
                "status": HealthStatus.CRITICAL,
                "error": f"CPU usage critical: {cpu_percent}%",
                "details": {"percent": cpu_percent}
            }
        elif cpu_percent > 85:
            return {
                "status": HealthStatus.WARNING,
                "error": f"CPU usage high: {cpu_percent}%",
                "details": {"percent": cpu_percent}
            }
        
        return {
            "status": HealthStatus.HEALTHY,
            "details": {"percent": cpu_percent}
        }
    
    async def _check_system_disk(self) -> Dict[str, Any]:
        """Check system disk usage"""
        if not psutil:
            return {
                "status": HealthStatus.HEALTHY,
                "details": {"percent": 0.0, "free_gb": 0.0}
            }

        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        if disk_percent > 95:
            return {
                "status": HealthStatus.CRITICAL,
                "error": f"Disk usage critical: {disk_percent:.1f}%",
                "details": {"percent": disk_percent, "free_gb": disk.free / (1024**3)}
            }
        elif disk_percent > 85:
            return {
                "status": HealthStatus.WARNING,
                "error": f"Disk usage high: {disk_percent:.1f}%",
                "details": {"percent": disk_percent, "free_gb": disk.free / (1024**3)}
            }
        
        return {
            "status": HealthStatus.HEALTHY,
            "details": {"percent": disk_percent, "free_gb": disk.free / (1024**3)}
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM metrics")
                count = cursor.fetchone()[0]
            
            return {
                "status": HealthStatus.HEALTHY,
                "details": {"metrics_count": count}
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.CRITICAL,
                "error": f"Database connection failed: {e}",
                "details": {}
            }
    
    async def _check_ai_providers(self) -> Dict[str, Any]:
        """Check AI provider availability (placeholder)"""
        
        # In a real implementation, this would check API connectivity
        return {
            "status": HealthStatus.HEALTHY,
            "details": {"anthropic": "available", "openai": "available"}
        }
    
    async def _check_docker(self) -> Dict[str, Any]:
        """Check Docker daemon availability (placeholder)"""
        
        try:
            # In a real implementation, this would check Docker connectivity
            import docker
            client = docker.from_env()
            client.ping()
            
            return {
                "status": HealthStatus.HEALTHY,
                "details": {"docker_daemon": "running"}
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.WARNING,
                "error": f"Docker not available: {e}",
                "details": {"docker_daemon": "unavailable"}
            }
    
    def display_dashboard(self):
        """Display real-time monitoring dashboard"""
        
        def create_dashboard():
            # System health panel
            health_data = asyncio.create_task(self.get_system_health())
            
            # Create tables and panels
            health_table = Table(title="System Health")
            health_table.add_column("Component", style="cyan")
            health_table.add_column("Status", style="green")
            health_table.add_column("Details")
            
            # Add sample data (in real implementation, use actual health data)
            health_table.add_row("Memory", "🟢 Healthy", "65% used")
            health_table.add_row("CPU", "🟡 Warning", "82% used")
            health_table.add_row("Disk", "🟢 Healthy", "45% used")
            
            # Business metrics panel
            business_panel = Panel(
                f"""
Startups Created Today: {self.business_metrics.startups_created_today}
Total Startups: {self.business_metrics.startups_created_total}
Active Tenants: {self.business_metrics.active_tenants}
Success Rate: {self.business_metrics.deployment_success_rate:.1f}%
Avg Time to MVP: {self.business_metrics.average_time_to_mvp:.1f}min
                """.strip(),
                title="Business Metrics"
            )
            
            # Alerts panel
            alerts_table = Table(title="Active Alerts")
            alerts_table.add_column("Alert", style="red")
            alerts_table.add_column("Severity")
            alerts_table.add_column("Age")
            
            for alert in list(self.active_alerts.values())[:5]:  # Show top 5
                age_minutes = (datetime.utcnow() - alert.triggered_at).total_seconds() / 60
                alerts_table.add_row(
                    alert.name,
                    alert.severity.value,
                    f"{age_minutes:.0f}m"
                )
            
            return health_table, business_panel, alerts_table
        
        # Display dashboard
        health_table, business_panel, alerts_table = create_dashboard()
        
        console.print(health_table)
        console.print(business_panel)
        console.print(alerts_table)


# Example usage
async def main():
    """Example usage of ObservabilityService"""
    
    obs_service = ObservabilityService()
    
    # Record some metrics
    obs_service.record_metric("startup_creation_time", 25.5, MetricType.TIMER)
    obs_service.record_metric("active_users", 150, MetricType.GAUGE)
    
    # Update business metrics
    obs_service.update_business_metrics(
        startups_created_today=5,
        startups_created_total=127,
        active_tenants=23,
        deployment_success_rate=95.2
    )
    
    # Trigger an alert
    obs_service.trigger_alert(
        "high_cpu", 
        "CPU usage is above 85%", 
        AlertSeverity.WARNING
    )
    
    # Get system health
    health = await obs_service.get_system_health()
    console.print("System Health:", health["overall_status"])
    
    # Display dashboard
    obs_service.display_dashboard()
    
    # Clean up
    await asyncio.sleep(2)
    obs_service.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
