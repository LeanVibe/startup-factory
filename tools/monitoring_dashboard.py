#!/usr/bin/env python3
"""
Real-time Multi-Startup Monitoring Dashboard
Provides live monitoring interface for all active startups
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import psutil
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import sys

# Try to import rich for better terminal UI
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.tree import Tree
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Rich not available - using basic terminal output")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MetricSnapshot:
    """Snapshot of system metrics at a point in time"""
    timestamp: datetime
    memory_usage_mb: float
    memory_percent: float
    cpu_percent: float
    disk_usage_gb: float
    network_io_mb: float
    active_processes: int

@dataclass
class StartupMetrics:
    """Metrics for a single startup"""
    id: str
    name: str
    status: str
    start_time: Optional[datetime]
    duration: Optional[float]
    memory_usage_mb: float
    cpu_percent: float
    progress_percent: float
    current_phase: str
    estimated_completion: Optional[datetime]
    resource_usage: Dict[str, Any]

class MetricsCollector:
    """Collects system and startup metrics"""
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.metrics_history: List[MetricSnapshot] = []
        self.startup_metrics: Dict[str, StartupMetrics] = {}
        self.running = False
        self.max_history = 300  # Keep 5 minutes of history at 1s intervals
        
    def start_collection(self):
        """Start metrics collection in background"""
        self.running = True
        thread = threading.Thread(target=self._collect_metrics_loop, daemon=True)
        thread.start()
        logger.info("Started metrics collection")
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.running = False
        logger.info("Stopped metrics collection")
    
    def _collect_metrics_loop(self):
        """Background loop for collecting metrics"""
        while self.running:
            try:
                snapshot = self._collect_system_metrics()
                self.metrics_history.append(snapshot)
                
                # Keep only recent history
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history = self.metrics_history[-self.max_history:]
                
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self) -> MetricSnapshot:
        """Collect current system metrics"""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=None)
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        return MetricSnapshot(
            timestamp=datetime.now(),
            memory_usage_mb=memory.used / (1024**2),
            memory_percent=memory.percent,
            cpu_percent=cpu_percent,
            disk_usage_gb=disk.used / (1024**3),
            network_io_mb=(network.bytes_sent + network.bytes_recv) / (1024**2),
            active_processes=len(psutil.pids())
        )
    
    def update_startup_metrics(self, startup_data: Dict[str, Any]):
        """Update metrics for a specific startup"""
        startup_id = startup_data.get('id')
        if not startup_id:
            return
        
        # Calculate progress based on current phase
        phase_progress = {
            'market_research': 20,
            'founder_analysis': 40,
            'mvp_specification': 60,
            'architecture': 80,
            'project_generation': 90,
            'deployment': 100
        }
        
        current_phase = startup_data.get('current_phase', 'pending')
        progress = phase_progress.get(current_phase, 0)
        
        # Estimate completion time
        estimated_completion = None
        if startup_data.get('start_time') and progress > 0:
            start_time = datetime.fromisoformat(startup_data['start_time'])
            elapsed = (datetime.now() - start_time).total_seconds()
            if progress > 0:
                total_estimated = elapsed * (100 / progress)
                remaining = total_estimated - elapsed
                estimated_completion = datetime.now() + timedelta(seconds=remaining)
        
        metrics = StartupMetrics(
            id=startup_id,
            name=startup_data.get('name', 'Unknown'),
            status=startup_data.get('status', 'unknown'),
            start_time=datetime.fromisoformat(startup_data['start_time']) if startup_data.get('start_time') else None,
            duration=startup_data.get('duration'),
            memory_usage_mb=startup_data.get('memory_usage_mb', 0),
            cpu_percent=startup_data.get('cpu_percent', 0),
            progress_percent=progress,
            current_phase=current_phase,
            estimated_completion=estimated_completion,
            resource_usage=startup_data.get('resource_usage', {})
        )
        
        self.startup_metrics[startup_id] = metrics
    
    def get_recent_metrics(self, minutes: int = 5) -> List[MetricSnapshot]:
        """Get metrics from the last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff]
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = self.get_recent_metrics(1)  # Last minute
        if not recent_metrics:
            return {}
        
        latest = recent_metrics[-1]
        
        # Calculate averages
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        
        # Startup statistics
        active_startups = len([s for s in self.startup_metrics.values() if s.status in ['running', 'pending']])
        completed_startups = len([s for s in self.startup_metrics.values() if s.status == 'completed'])
        failed_startups = len([s for s in self.startup_metrics.values() if s.status == 'failed'])
        
        return {
            'current_memory_mb': latest.memory_usage_mb,
            'avg_memory_percent': avg_memory,
            'avg_cpu_percent': avg_cpu,
            'active_startups': active_startups,
            'completed_startups': completed_startups,
            'failed_startups': failed_startups,
            'total_startups': len(self.startup_metrics),
            'disk_usage_gb': latest.disk_usage_gb,
            'timestamp': latest.timestamp
        }

class RichDashboard:
    """Rich-based dashboard for beautiful terminal UI"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        if not RICH_AVAILABLE:
            raise ImportError("Rich library not available")
        
        self.metrics_collector = metrics_collector
        self.console = Console()
        self.layout = Layout()
        self._setup_layout()
    
    def _setup_layout(self):
        """Setup dashboard layout"""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        self.layout["left"].split_column(
            Layout(name="system_metrics", ratio=1),
            Layout(name="startup_list", ratio=2)
        )
        
        self.layout["right"].split_column(
            Layout(name="summary", ratio=1),
            Layout(name="alerts", ratio=1)
        )
    
    def create_header(self) -> Panel:
        """Create dashboard header"""
        title = Text("🚀 Startup Factory - Multi-Startup Dashboard", style="bold cyan")
        subtitle = Text(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
        return Panel(title + "\n" + subtitle, style="bright_blue")
    
    def create_system_metrics_panel(self) -> Panel:
        """Create system metrics panel"""
        stats = self.metrics_collector.get_summary_stats()
        if not stats:
            return Panel("Collecting metrics...", title="System Metrics")
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Usage", style="yellow")
        
        # Memory usage
        memory_mb = stats.get('current_memory_mb', 0)
        memory_percent = stats.get('avg_memory_percent', 0)
        memory_bar = "█" * int(memory_percent / 5) + "░" * (20 - int(memory_percent / 5))
        table.add_row("Memory", f"{memory_mb:.0f}MB", f"{memory_bar} {memory_percent:.1f}%")
        
        # CPU usage
        cpu_percent = stats.get('avg_cpu_percent', 0)
        cpu_bar = "█" * int(cpu_percent / 5) + "░" * (20 - int(cpu_percent / 5))
        table.add_row("CPU", f"{cpu_percent:.1f}%", f"{cpu_bar} {cpu_percent:.1f}%")
        
        # Disk usage
        disk_gb = stats.get('disk_usage_gb', 0)
        table.add_row("Disk", f"{disk_gb:.1f}GB", "")
        
        return Panel(table, title="System Metrics", border_style="green")
    
    def create_startup_list_panel(self) -> Panel:
        """Create startup list panel"""
        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Progress", style="yellow")
        table.add_column("Phase", style="blue")
        table.add_column("Duration", style="magenta")
        table.add_column("ETA", style="dim")
        
        for startup in self.metrics_collector.startup_metrics.values():
            # Status color
            status_style = {
                'running': 'green',
                'completed': 'bright_green',
                'failed': 'red',
                'pending': 'yellow',
                'cancelled': 'dim'
            }.get(startup.status, 'white')
            
            # Progress bar
            progress_chars = int(startup.progress_percent / 5)
            progress_bar = "█" * progress_chars + "░" * (20 - progress_chars)
            
            # Duration
            duration_str = ""
            if startup.start_time:
                elapsed = datetime.now() - startup.start_time
                duration_str = f"{elapsed.total_seconds():.0f}s"
            
            # ETA
            eta_str = ""
            if startup.estimated_completion:
                remaining = startup.estimated_completion - datetime.now()
                if remaining.total_seconds() > 0:
                    eta_str = f"{remaining.total_seconds():.0f}s"
            
            table.add_row(
                startup.name[:20],
                f"[{status_style}]{startup.status}[/{status_style}]",
                f"{progress_bar} {startup.progress_percent:.0f}%",
                startup.current_phase,
                duration_str,
                eta_str
            )
        
        return Panel(table, title=f"Active Startups ({len(self.metrics_collector.startup_metrics)})", border_style="blue")
    
    def create_summary_panel(self) -> Panel:
        """Create summary statistics panel"""
        stats = self.metrics_collector.get_summary_stats()
        if not stats:
            return Panel("No data", title="Summary")
        
        summary_text = f"""
📊 Startup Statistics:
  • Active: {stats.get('active_startups', 0)}
  • Completed: {stats.get('completed_startups', 0)}
  • Failed: {stats.get('failed_startups', 0)}
  • Total: {stats.get('total_startups', 0)}

🎯 Performance Targets:
  • Target: <30 min/startup
  • Memory: <500MB/startup
  • CPU: <25%/startup
  • Concurrent: 5 startups
        """
        
        return Panel(summary_text.strip(), title="Summary", border_style="yellow")
    
    def create_alerts_panel(self) -> Panel:
        """Create alerts panel"""
        alerts = []
        stats = self.metrics_collector.get_summary_stats()
        
        if stats:
            # Check for high resource usage
            if stats.get('avg_memory_percent', 0) > 80:
                alerts.append("⚠️ High memory usage")
            
            if stats.get('avg_cpu_percent', 0) > 70:
                alerts.append("⚠️ High CPU usage")
            
            # Check for failed startups
            if stats.get('failed_startups', 0) > 0:
                alerts.append(f"❌ {stats['failed_startups']} startup(s) failed")
            
            # Check for long-running startups
            for startup in self.metrics_collector.startup_metrics.values():
                if startup.start_time and startup.status == 'running':
                    elapsed = datetime.now() - startup.start_time
                    if elapsed.total_seconds() > 1800:  # 30 minutes
                        alerts.append(f"🐌 {startup.name} running >30min")
        
        if not alerts:
            alerts = ["✅ All systems normal"]
        
        alert_text = "\n".join(alerts)
        return Panel(alert_text, title="Alerts", border_style="red" if len(alerts) > 1 else "green")
    
    def create_footer(self) -> Panel:
        """Create dashboard footer"""
        return Panel(
            "Press Ctrl+C to exit | Dashboard updates every second",
            style="dim"
        )
    
    def render_dashboard(self):
        """Render the complete dashboard"""
        self.layout["header"].update(self.create_header())
        self.layout["system_metrics"].update(self.create_system_metrics_panel())
        self.layout["startup_list"].update(self.create_startup_list_panel())
        self.layout["summary"].update(self.create_summary_panel())
        self.layout["alerts"].update(self.create_alerts_panel())
        self.layout["footer"].update(self.create_footer())
        
        return self.layout

class BasicDashboard:
    """Basic text-based dashboard for when Rich is not available"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
    
    def render_dashboard(self) -> str:
        """Render dashboard as text"""
        stats = self.metrics_collector.get_summary_stats()
        
        output = []
        output.append("=" * 60)
        output.append("🚀 Startup Factory - Multi-Startup Dashboard")
        output.append(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("=" * 60)
        
        if stats:
            output.append(f"📊 System Metrics:")
            output.append(f"  Memory: {stats.get('current_memory_mb', 0):.0f}MB ({stats.get('avg_memory_percent', 0):.1f}%)")
            output.append(f"  CPU: {stats.get('avg_cpu_percent', 0):.1f}%")
            output.append(f"  Disk: {stats.get('disk_usage_gb', 0):.1f}GB")
            output.append("")
            
            output.append(f"🎯 Startup Statistics:")
            output.append(f"  Active: {stats.get('active_startups', 0)}")
            output.append(f"  Completed: {stats.get('completed_startups', 0)}")
            output.append(f"  Failed: {stats.get('failed_startups', 0)}")
            output.append(f"  Total: {stats.get('total_startups', 0)}")
            output.append("")
        
        output.append("📋 Active Startups:")
        for startup in self.metrics_collector.startup_metrics.values():
            duration_str = ""
            if startup.start_time:
                elapsed = datetime.now() - startup.start_time
                duration_str = f" ({elapsed.total_seconds():.0f}s)"
            
            output.append(f"  • {startup.name}: {startup.status} - {startup.current_phase} ({startup.progress_percent:.0f}%){duration_str}")
        
        output.append("")
        output.append("Press Ctrl+C to exit")
        output.append("=" * 60)
        
        return "\n".join(output)

class MonitoringDashboard:
    """Main monitoring dashboard controller"""
    
    def __init__(self, use_rich: bool = True):
        self.metrics_collector = MetricsCollector()
        self.use_rich = use_rich and RICH_AVAILABLE
        
        if self.use_rich:
            self.dashboard = RichDashboard(self.metrics_collector)
        else:
            self.dashboard = BasicDashboard(self.metrics_collector)
    
    async def start_monitoring(self):
        """Start the monitoring dashboard"""
        self.metrics_collector.start_collection()
        
        try:
            if self.use_rich:
                await self._run_rich_dashboard()
            else:
                await self._run_basic_dashboard()
        finally:
            self.metrics_collector.stop_collection()
    
    async def _run_rich_dashboard(self):
        """Run Rich-based dashboard"""
        with Live(self.dashboard.render_dashboard(), refresh_per_second=1, screen=True) as live:
            try:
                while True:
                    live.update(self.dashboard.render_dashboard())
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass
    
    async def _run_basic_dashboard(self):
        """Run basic text dashboard"""
        try:
            while True:
                # Clear screen
                print("\033[2J\033[H")
                print(self.dashboard.render_dashboard())
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
    
    def update_startup_data(self, startup_data: Dict[str, Any]):
        """Update startup data in the dashboard"""
        self.metrics_collector.update_startup_metrics(startup_data)
    
    def simulate_startup_data(self):
        """Simulate startup data for testing"""
        # Add some test startups
        test_startups = [
            {
                'id': 'startup_1',
                'name': 'FinTech MVP',
                'status': 'running',
                'start_time': (datetime.now() - timedelta(minutes=15)).isoformat(),
                'current_phase': 'mvp_specification',
                'memory_usage_mb': 420,
                'cpu_percent': 23
            },
            {
                'id': 'startup_2',
                'name': 'HealthTech App',
                'status': 'running',
                'start_time': (datetime.now() - timedelta(minutes=8)).isoformat(),
                'current_phase': 'architecture',
                'memory_usage_mb': 380,
                'cpu_percent': 18
            },
            {
                'id': 'startup_3',
                'name': 'EdTech Platform',
                'status': 'completed',
                'start_time': (datetime.now() - timedelta(minutes=25)).isoformat(),
                'current_phase': 'deployment',
                'memory_usage_mb': 0,
                'cpu_percent': 0,
                'duration': 1450
            }
        ]
        
        for startup_data in test_startups:
            self.update_startup_data(startup_data)

async def main():
    """Main function for testing the dashboard"""
    print("🚀 Starting Multi-Startup Monitoring Dashboard")
    
    # Create dashboard
    dashboard = MonitoringDashboard(use_rich=RICH_AVAILABLE)
    
    # Add some test data
    dashboard.simulate_startup_data()
    
    # Start monitoring
    await dashboard.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())