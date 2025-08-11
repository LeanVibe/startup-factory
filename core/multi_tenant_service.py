#!/usr/bin/env python3
"""
Multi-Tenant Service - Core Service 5/8
Consolidates: multi_startup_manager.py, resource_allocator.py, budget_monitor.py
Handles resource isolation, cost allocation, and concurrent startup management.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import threading

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    import psutil
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install rich psutil")
    exit(1)

# Import from other core services
try:
    from .conversation_service import BusinessBlueprint
except ImportError:
    # Fallback for standalone usage
    import sys
    sys.path.append(str(Path(__file__).parent))
    from conversation_service import BusinessBlueprint

console = Console()
logger = logging.getLogger(__name__)


class TenantStatus(str, Enum):
    """Tenant status states"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"


class ResourceType(str, Enum):
    """Types of resources that can be allocated"""
    MEMORY = "memory"
    CPU = "cpu"
    STORAGE = "storage"
    NETWORK_PORTS = "network_ports"
    DATABASE_CONNECTIONS = "database_connections"
    API_CALLS = "api_calls"


@dataclass
class ResourceLimits:
    """Resource limits for a tenant"""
    memory_mb: int = 512
    cpu_cores: float = 0.5
    storage_gb: int = 2
    max_ports: int = 10
    max_db_connections: int = 10
    api_calls_per_hour: int = 1000
    cost_limit_per_day: float = 15.0


@dataclass
class ResourceAllocation:
    """Current resource allocation for a tenant"""
    tenant_id: str
    allocated_at: datetime
    expires_at: Optional[datetime]
    
    # Allocated resources
    memory_mb: int = 0
    cpu_cores: float = 0.0
    storage_gb: int = 0
    allocated_ports: List[int] = field(default_factory=list)
    db_connections: int = 0
    
    # Usage tracking
    current_memory_usage: int = 0
    current_cpu_usage: float = 0.0
    current_storage_usage: int = 0
    api_calls_used: int = 0
    
    # Cost tracking
    hourly_cost: float = 0.0
    daily_cost: float = 0.0


@dataclass
class Tenant:
    """Multi-tenant startup instance"""
    tenant_id: str
    business_name: str
    founder_email: str
    status: TenantStatus
    blueprint: Optional[BusinessBlueprint]
    
    # Resource management
    resource_limits: ResourceLimits
    resource_allocation: Optional[ResourceAllocation]
    
    # Tenant isolation
    database_namespace: str
    storage_path: str
    network_namespace: str
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    # Cost and billing
    total_cost: float = 0.0
    billing_cycle: str = "monthly"


class MultiTenantService:
    """
    Multi-tenant service for resource isolation and concurrent startup management.
    Consolidates multi_startup_manager.py, resource_allocator.py, budget_monitor.py
    """
    
    def __init__(self, max_concurrent_tenants: int = 10):
        self.max_concurrent_tenants = max_concurrent_tenants
        self.tenants: Dict[str, Tenant] = {}
        self.resource_pool = self._initialize_resource_pool()
        self.allocation_lock = threading.Lock()
        
        # Port management
        self.port_pool = set(range(3000, 3100))  # 100 ports available
        self.allocated_ports: Set[int] = set()
        
        # Cost tracking
        self.cost_per_resource = {
            ResourceType.MEMORY: 0.001,      # $0.001 per MB per hour
            ResourceType.CPU: 0.05,          # $0.05 per core per hour
            ResourceType.STORAGE: 0.0002,    # $0.0002 per GB per hour
            ResourceType.API_CALLS: 0.0001   # $0.0001 per API call
        }
        
        # Start background monitoring
        self._start_monitoring_tasks()
    
    def _initialize_resource_pool(self) -> Dict[str, Any]:
        """Initialize system resource pool"""
        # Get system resources
        memory_total = psutil.virtual_memory().total // (1024 * 1024)  # MB
        cpu_count = psutil.cpu_count()
        disk_total = psutil.disk_usage('/').total // (1024 * 1024 * 1024)  # GB
        
        # Reserve resources for system
        available_memory = int(memory_total * 0.7)  # Use 70% of system memory
        available_cpu = cpu_count * 0.8             # Use 80% of CPU cores
        available_storage = int(disk_total * 0.5)   # Use 50% of disk space
        
        return {
            "total_memory_mb": available_memory,
            "total_cpu_cores": available_cpu,
            "total_storage_gb": available_storage,
            "allocated_memory_mb": 0,
            "allocated_cpu_cores": 0.0,
            "allocated_storage_gb": 0
        }
    
    async def create_tenant(
        self,
        business_name: str,
        founder_email: str,
        resource_limits: Optional[ResourceLimits] = None
    ) -> str:
        """Create a new tenant with resource isolation"""
        
        if len(self.tenants) >= self.max_concurrent_tenants:
            raise Exception(f"Maximum concurrent tenants ({self.max_concurrent_tenants}) reached")
        
        tenant_id = str(uuid.uuid4())
        
        # Set default resource limits if not provided
        if resource_limits is None:
            resource_limits = ResourceLimits()
        
        # Create isolated tenant
        tenant = Tenant(
            tenant_id=tenant_id,
            business_name=business_name,
            founder_email=founder_email,
            status=TenantStatus.PENDING,
            blueprint=None,
            resource_limits=resource_limits,
            resource_allocation=None,
            database_namespace=f"tenant_{tenant_id.replace('-', '_')}",
            storage_path=f"tenants/{tenant_id}",
            network_namespace=f"net_{tenant_id[:8]}"
        )
        
        # Allocate resources
        allocation = await self._allocate_resources(tenant_id, resource_limits)
        tenant.resource_allocation = allocation
        tenant.status = TenantStatus.ACTIVE
        
        # Store tenant
        self.tenants[tenant_id] = tenant
        
        console.print(f"✅ Created tenant: {business_name} ({tenant_id[:8]})")
        
        return tenant_id
    
    async def _allocate_resources(self, tenant_id: str, limits: ResourceLimits) -> ResourceAllocation:
        """Allocate resources for a tenant with isolation guarantees"""
        
        with self.allocation_lock:
            # Check resource availability
            available_memory = (
                self.resource_pool["total_memory_mb"] - 
                self.resource_pool["allocated_memory_mb"]
            )
            available_cpu = (
                self.resource_pool["total_cpu_cores"] - 
                self.resource_pool["allocated_cpu_cores"]
            )
            available_storage = (
                self.resource_pool["total_storage_gb"] - 
                self.resource_pool["allocated_storage_gb"]
            )
            
            # Validate resource availability
            if available_memory < limits.memory_mb:
                raise Exception(f"Insufficient memory: need {limits.memory_mb}MB, available {available_memory}MB")
            
            if available_cpu < limits.cpu_cores:
                raise Exception(f"Insufficient CPU: need {limits.cpu_cores} cores, available {available_cpu}")
            
            if available_storage < limits.storage_gb:
                raise Exception(f"Insufficient storage: need {limits.storage_gb}GB, available {available_storage}GB")
            
            # Allocate ports
            allocated_ports = []
            available_ports = self.port_pool - self.allocated_ports
            
            if len(available_ports) < limits.max_ports:
                raise Exception(f"Insufficient ports: need {limits.max_ports}, available {len(available_ports)}")
            
            for _ in range(limits.max_ports):
                port = available_ports.pop()
                allocated_ports.append(port)
                self.allocated_ports.add(port)
            
            # Update resource pool
            self.resource_pool["allocated_memory_mb"] += limits.memory_mb
            self.resource_pool["allocated_cpu_cores"] += limits.cpu_cores
            self.resource_pool["allocated_storage_gb"] += limits.storage_gb
            
            # Calculate hourly cost
            hourly_cost = (
                limits.memory_mb * self.cost_per_resource[ResourceType.MEMORY] +
                limits.cpu_cores * self.cost_per_resource[ResourceType.CPU] +
                limits.storage_gb * self.cost_per_resource[ResourceType.STORAGE]
            )
            
            # Create allocation
            allocation = ResourceAllocation(
                tenant_id=tenant_id,
                allocated_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=1),  # 24-hour default
                memory_mb=limits.memory_mb,
                cpu_cores=limits.cpu_cores,
                storage_gb=limits.storage_gb,
                allocated_ports=allocated_ports,
                db_connections=limits.max_db_connections,
                hourly_cost=hourly_cost,
                daily_cost=hourly_cost * 24
            )
            
            return allocation
    
    async def deallocate_resources(self, tenant_id: str) -> bool:
        """Deallocate resources for a tenant"""
        
        if tenant_id not in self.tenants:
            return False
        
        tenant = self.tenants[tenant_id]
        allocation = tenant.resource_allocation
        
        if not allocation:
            return True
        
        with self.allocation_lock:
            # Return resources to pool
            self.resource_pool["allocated_memory_mb"] -= allocation.memory_mb
            self.resource_pool["allocated_cpu_cores"] -= allocation.cpu_cores
            self.resource_pool["allocated_storage_gb"] -= allocation.storage_gb
            
            # Return ports to pool
            for port in allocation.allocated_ports:
                self.allocated_ports.discard(port)
            
            # Clear allocation
            tenant.resource_allocation = None
            tenant.status = TenantStatus.TERMINATED
            
            console.print(f"✅ Deallocated resources for tenant {tenant_id[:8]}")
            
            return True
    
    async def update_tenant_blueprint(self, tenant_id: str, blueprint: BusinessBlueprint) -> bool:
        """Update tenant with business blueprint"""
        
        if tenant_id not in self.tenants:
            return False
        
        tenant = self.tenants[tenant_id]
        tenant.blueprint = blueprint
        tenant.last_activity = datetime.utcnow()
        
        # Update business name if different
        if blueprint.business_name != tenant.business_name:
            tenant.business_name = blueprint.business_name
        
        return True
    
    async def monitor_resource_usage(self) -> Dict[str, Any]:
        """Monitor system-wide resource usage"""
        
        # Get current system usage
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk_usage = psutil.disk_usage('/')
        
        # Calculate tenant usage
        total_allocated_memory = self.resource_pool["allocated_memory_mb"]
        total_allocated_cpu = self.resource_pool["allocated_cpu_cores"]
        total_allocated_storage = self.resource_pool["allocated_storage_gb"]
        
        usage_data = {
            "system": {
                "memory_percent": memory_info.percent,
                "cpu_percent": cpu_percent,
                "disk_percent": (disk_usage.used / disk_usage.total) * 100
            },
            "tenant_allocation": {
                "allocated_memory_mb": total_allocated_memory,
                "allocated_cpu_cores": total_allocated_cpu,
                "allocated_storage_gb": total_allocated_storage,
                "active_tenants": len([t for t in self.tenants.values() if t.status == TenantStatus.ACTIVE])
            },
            "resource_pool": {
                "available_memory_mb": (
                    self.resource_pool["total_memory_mb"] - 
                    self.resource_pool["allocated_memory_mb"]
                ),
                "available_cpu_cores": (
                    self.resource_pool["total_cpu_cores"] - 
                    self.resource_pool["allocated_cpu_cores"]
                ),
                "available_storage_gb": (
                    self.resource_pool["total_storage_gb"] - 
                    self.resource_pool["allocated_storage_gb"]
                )
            }
        }
        
        return usage_data
    
    async def track_tenant_costs(self, tenant_id: str) -> Dict[str, Any]:
        """Track costs for a specific tenant"""
        
        if tenant_id not in self.tenants:
            return {"error": "Tenant not found"}
        
        tenant = self.tenants[tenant_id]
        allocation = tenant.resource_allocation
        
        if not allocation:
            return {"error": "No resource allocation found"}
        
        # Calculate runtime costs
        runtime_hours = (datetime.utcnow() - allocation.allocated_at).total_seconds() / 3600
        
        # Base resource costs
        resource_cost = allocation.hourly_cost * runtime_hours
        
        # API usage costs
        api_cost = allocation.api_calls_used * self.cost_per_resource[ResourceType.API_CALLS]
        
        total_cost = resource_cost + api_cost
        
        # Update tenant total cost
        tenant.total_cost = total_cost
        
        cost_breakdown = {
            "tenant_id": tenant_id,
            "business_name": tenant.business_name,
            "runtime_hours": round(runtime_hours, 2),
            "costs": {
                "memory": allocation.memory_mb * self.cost_per_resource[ResourceType.MEMORY] * runtime_hours,
                "cpu": allocation.cpu_cores * self.cost_per_resource[ResourceType.CPU] * runtime_hours,
                "storage": allocation.storage_gb * self.cost_per_resource[ResourceType.STORAGE] * runtime_hours,
                "api_calls": api_cost
            },
            "total_cost": round(total_cost, 4),
            "daily_estimate": round(allocation.hourly_cost * 24, 2),
            "within_budget": total_cost <= tenant.resource_limits.cost_limit_per_day
        }
        
        return cost_breakdown
    
    def _start_monitoring_tasks(self):
        """Start background monitoring tasks"""
        
        async def monitoring_loop():
            while True:
                try:
                    # Monitor resource usage
                    usage_data = await self.monitor_resource_usage()
                    
                    # Check for over-budget tenants
                    for tenant_id in list(self.tenants.keys()):
                        cost_data = await self.track_tenant_costs(tenant_id)
                        
                        if not cost_data.get("within_budget", True):
                            logger.warning(f"Tenant {tenant_id[:8]} exceeding budget")
                            # Could implement auto-suspension here
                    
                    # Clean up expired allocations
                    await self._cleanup_expired_tenants()
                    
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                
                # Wait 60 seconds between monitoring cycles
                await asyncio.sleep(60)
        
        # Start monitoring in background
        asyncio.create_task(monitoring_loop())
    
    async def _cleanup_expired_tenants(self):
        """Clean up expired tenant allocations"""
        
        expired_tenants = []
        current_time = datetime.utcnow()
        
        for tenant_id, tenant in self.tenants.items():
            if (tenant.resource_allocation and 
                tenant.resource_allocation.expires_at and
                current_time > tenant.resource_allocation.expires_at):
                expired_tenants.append(tenant_id)
        
        for tenant_id in expired_tenants:
            logger.info(f"Cleaning up expired tenant: {tenant_id[:8]}")
            await self.deallocate_resources(tenant_id)
    
    def get_tenant_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get detailed status of a tenant"""
        
        if tenant_id not in self.tenants:
            return {"error": "Tenant not found"}
        
        tenant = self.tenants[tenant_id]
        
        status_data = {
            "tenant_id": tenant_id,
            "business_name": tenant.business_name,
            "founder_email": tenant.founder_email,
            "status": tenant.status.value,
            "created_at": tenant.created_at.isoformat(),
            "last_activity": tenant.last_activity.isoformat(),
            "has_blueprint": tenant.blueprint is not None,
            "database_namespace": tenant.database_namespace,
            "storage_path": tenant.storage_path,
            "total_cost": round(tenant.total_cost, 4)
        }
        
        if tenant.resource_allocation:
            status_data["resource_allocation"] = {
                "memory_mb": tenant.resource_allocation.memory_mb,
                "cpu_cores": tenant.resource_allocation.cpu_cores,
                "storage_gb": tenant.resource_allocation.storage_gb,
                "allocated_ports": tenant.resource_allocation.allocated_ports,
                "hourly_cost": tenant.resource_allocation.hourly_cost,
                "expires_at": tenant.resource_allocation.expires_at.isoformat() if tenant.resource_allocation.expires_at else None
            }
        
        return status_data
    
    def list_active_tenants(self) -> List[Dict[str, Any]]:
        """List all active tenants"""
        
        active_tenants = []
        
        for tenant_id, tenant in self.tenants.items():
            if tenant.status == TenantStatus.ACTIVE:
                active_tenants.append({
                    "tenant_id": tenant_id,
                    "business_name": tenant.business_name,
                    "founder_email": tenant.founder_email,
                    "created_at": tenant.created_at.isoformat(),
                    "total_cost": round(tenant.total_cost, 4),
                    "resource_usage": {
                        "memory_mb": tenant.resource_allocation.memory_mb if tenant.resource_allocation else 0,
                        "cpu_cores": tenant.resource_allocation.cpu_cores if tenant.resource_allocation else 0
                    }
                })
        
        return active_tenants
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide overview"""
        
        overview = {
            "total_tenants": len(self.tenants),
            "active_tenants": len([t for t in self.tenants.values() if t.status == TenantStatus.ACTIVE]),
            "resource_utilization": {
                "memory_utilization": (
                    self.resource_pool["allocated_memory_mb"] / 
                    self.resource_pool["total_memory_mb"] * 100
                ),
                "cpu_utilization": (
                    self.resource_pool["allocated_cpu_cores"] / 
                    self.resource_pool["total_cpu_cores"] * 100
                ),
                "storage_utilization": (
                    self.resource_pool["allocated_storage_gb"] / 
                    self.resource_pool["total_storage_gb"] * 100
                )
            },
            "port_usage": {
                "allocated_ports": len(self.allocated_ports),
                "available_ports": len(self.port_pool - self.allocated_ports)
            },
            "total_system_cost": sum(tenant.total_cost for tenant in self.tenants.values())
        }
        
        return overview
    
    def display_system_status(self):
        """Display system status in a nice table"""
        
        overview = self.get_system_overview()
        
        # System overview table
        overview_table = Table(title="Multi-Tenant System Overview")
        overview_table.add_column("Metric", style="cyan")
        overview_table.add_column("Value", style="green")
        
        overview_table.add_row("Total Tenants", str(overview["total_tenants"]))
        overview_table.add_row("Active Tenants", str(overview["active_tenants"]))
        overview_table.add_row("Memory Utilization", f"{overview['resource_utilization']['memory_utilization']:.1f}%")
        overview_table.add_row("CPU Utilization", f"{overview['resource_utilization']['cpu_utilization']:.1f}%")
        overview_table.add_row("Storage Utilization", f"{overview['resource_utilization']['storage_utilization']:.1f}%")
        overview_table.add_row("Total Cost", f"${overview['total_system_cost']:.4f}")
        
        console.print(overview_table)
        
        # Active tenants table
        if overview["active_tenants"] > 0:
            tenants_table = Table(title="Active Tenants")
            tenants_table.add_column("ID", style="cyan")
            tenants_table.add_column("Business Name", style="green")
            tenants_table.add_column("Memory (MB)", style="yellow")
            tenants_table.add_column("CPU Cores", style="yellow")
            tenants_table.add_column("Cost", style="red")
            
            for tenant_data in self.list_active_tenants():
                tenants_table.add_row(
                    tenant_data["tenant_id"][:8],
                    tenant_data["business_name"],
                    str(tenant_data["resource_usage"]["memory_mb"]),
                    str(tenant_data["resource_usage"]["cpu_cores"]),
                    f"${tenant_data['total_cost']:.4f}"
                )
            
            console.print(tenants_table)


# Example usage
async def main():
    """Example usage of MultiTenantService"""
    
    multi_tenant = MultiTenantService(max_concurrent_tenants=5)
    
    # Create a few tenants
    tenant1_id = await multi_tenant.create_tenant("HealthTech Startup", "founder@healthtech.com")
    tenant2_id = await multi_tenant.create_tenant("FinTech App", "founder@fintech.com")
    
    # Display system status
    multi_tenant.display_system_status()
    
    # Monitor costs
    await asyncio.sleep(2)  # Simulate some runtime
    cost_data = await multi_tenant.track_tenant_costs(tenant1_id)
    console.print(f"Cost data for tenant 1: {json.dumps(cost_data, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())