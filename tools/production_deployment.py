#!/usr/bin/env python3
"""
Production Deployment Pipeline
Automated deployment with health checks, rollback, and monitoring
"""

import asyncio
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
# Docker import - optional for testing
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
import yaml
import psutil
import sys
import os
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeploymentStatus(Enum):
    PENDING = "pending"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"

class HealthCheckStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

@dataclass
class DeploymentConfig:
    """Configuration for deployment"""
    environment: str = "production"
    replicas: int = 3
    max_memory_mb: int = 500
    max_cpu_percent: int = 25
    health_check_interval: int = 30
    health_check_timeout: int = 10
    rollback_on_failure: bool = True
    monitoring_enabled: bool = True
    backup_enabled: bool = True

@dataclass
class HealthCheck:
    """Health check configuration and results"""
    name: str
    endpoint: str
    expected_status: int = 200
    timeout: int = 10
    retries: int = 3
    status: HealthCheckStatus = HealthCheckStatus.UNKNOWN
    last_check: Optional[datetime] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None

@dataclass
class DeploymentMetrics:
    """Deployment metrics"""
    start_time: datetime
    end_time: Optional[datetime] = None
    status: DeploymentStatus = DeploymentStatus.PENDING
    build_time_seconds: Optional[float] = None
    test_time_seconds: Optional[float] = None
    deployment_time_seconds: Optional[float] = None
    health_checks: List[HealthCheck] = field(default_factory=list)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    error_logs: List[str] = field(default_factory=list)

class ResourceMonitor:
    """Monitors resource usage during deployment"""
    
    def __init__(self, max_memory_mb: int = 500, max_cpu_percent: int = 25):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.monitoring = False
        self.metrics: List[Dict[str, Any]] = []
    
    def start_monitoring(self):
        """Start resource monitoring"""
        self.monitoring = True
        self.metrics = []
        asyncio.create_task(self._monitor_loop())
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
    
    async def _monitor_loop(self):
        """Monitor resource usage in background"""
        while self.monitoring:
            try:
                memory = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=1)
                
                metric = {
                    'timestamp': datetime.now().isoformat(),
                    'memory_usage_mb': memory.used / (1024**2),
                    'memory_percent': memory.percent,
                    'cpu_percent': cpu_percent,
                    'available_memory_mb': memory.available / (1024**2)
                }
                
                self.metrics.append(metric)
                
                # Check resource limits
                if memory.percent > 90:
                    logger.warning(f"High memory usage: {memory.percent:.1f}%")
                
                if cpu_percent > 80:
                    logger.warning(f"High CPU usage: {cpu_percent:.1f}%")
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(5)
    
    def get_current_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        if not self.metrics:
            return {}
        return self.metrics[-1]
    
    def get_peak_usage(self) -> Dict[str, Any]:
        """Get peak resource usage"""
        if not self.metrics:
            return {}
        
        peak_memory = max(self.metrics, key=lambda x: x['memory_usage_mb'])
        peak_cpu = max(self.metrics, key=lambda x: x['cpu_percent'])
        
        return {
            'peak_memory_mb': peak_memory['memory_usage_mb'],
            'peak_cpu_percent': peak_cpu['cpu_percent'],
            'peak_memory_time': peak_memory['timestamp'],
            'peak_cpu_time': peak_cpu['timestamp']
        }

class HealthChecker:
    """Performs health checks on deployed services"""
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
    
    def add_check(self, check: HealthCheck):
        """Add a health check"""
        self.checks.append(check)
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'total_checks': len(self.checks),
            'healthy_checks': 0,
            'unhealthy_checks': 0,
            'degraded_checks': 0,
            'overall_status': HealthCheckStatus.HEALTHY,
            'checks': []
        }
        
        for check in self.checks:
            await self._run_single_check(check)
            
            check_result = {
                'name': check.name,
                'status': check.status.value,
                'response_time_ms': check.response_time_ms,
                'error_message': check.error_message,
                'last_check': check.last_check.isoformat() if check.last_check else None
            }
            
            results['checks'].append(check_result)
            
            if check.status == HealthCheckStatus.HEALTHY:
                results['healthy_checks'] += 1
            elif check.status == HealthCheckStatus.UNHEALTHY:
                results['unhealthy_checks'] += 1
            elif check.status == HealthCheckStatus.DEGRADED:
                results['degraded_checks'] += 1
        
        # Determine overall status
        if results['unhealthy_checks'] > 0:
            results['overall_status'] = HealthCheckStatus.UNHEALTHY
        elif results['degraded_checks'] > 0:
            results['overall_status'] = HealthCheckStatus.DEGRADED
        else:
            results['overall_status'] = HealthCheckStatus.HEALTHY
        
        return results
    
    async def _run_single_check(self, check: HealthCheck):
        """Run a single health check"""
        start_time = time.time()
        check.last_check = datetime.now()
        
        try:
            # Mock health check - in reality, this would make HTTP requests
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Simulate different health states
            import random
            if random.random() > 0.9:  # 10% chance of failure
                check.status = HealthCheckStatus.UNHEALTHY
                check.error_message = "Service unavailable"
            elif random.random() > 0.95:  # 5% chance of degraded
                check.status = HealthCheckStatus.DEGRADED
                check.error_message = "Slow response"
            else:
                check.status = HealthCheckStatus.HEALTHY
                check.error_message = None
            
            check.response_time_ms = (time.time() - start_time) * 1000
            
        except Exception as e:
            check.status = HealthCheckStatus.UNHEALTHY
            check.error_message = str(e)
            check.response_time_ms = (time.time() - start_time) * 1000

class BackupManager:
    """Manages backups before deployment"""
    
    def __init__(self, backup_dir: Path = Path("backups")):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(exist_ok=True)
    
    async def create_backup(self, source_dirs: List[Path]) -> str:
        """Create backup of current deployment"""
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(exist_ok=True)
        
        logger.info(f"Creating backup: {backup_id}")
        
        for source_dir in source_dirs:
            if source_dir.exists():
                dest_dir = backup_path / source_dir.name
                await asyncio.get_event_loop().run_in_executor(
                    None, shutil.copytree, source_dir, dest_dir
                )
        
        # Create backup metadata
        metadata = {
            'backup_id': backup_id,
            'created_at': datetime.now().isoformat(),
            'source_dirs': [str(d) for d in source_dirs],
            'backup_path': str(backup_path)
        }
        
        with open(backup_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Backup created: {backup_path}")
        return backup_id
    
    async def restore_backup(self, backup_id: str, target_dirs: List[Path]) -> bool:
        """Restore from backup"""
        backup_path = self.backup_dir / backup_id
        
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        logger.info(f"Restoring backup: {backup_id}")
        
        try:
            # Load metadata
            with open(backup_path / "metadata.json", 'r') as f:
                metadata = json.load(f)
            
            # Restore directories
            for target_dir in target_dirs:
                source_backup = backup_path / target_dir.name
                if source_backup.exists():
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                    await asyncio.get_event_loop().run_in_executor(
                        None, shutil.copytree, source_backup, target_dir
                    )
            
            logger.info(f"Backup restored: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    backups.append(metadata)
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)

class ProductionDeploymentPipeline:
    """Main production deployment pipeline"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.resource_monitor = ResourceMonitor(config.max_memory_mb, config.max_cpu_percent)
        self.health_checker = HealthChecker()
        self.backup_manager = BackupManager()
        self.deployment_metrics = DeploymentMetrics(start_time=datetime.now())
        
        # Setup default health checks
        self._setup_default_health_checks()
    
    def _setup_default_health_checks(self):
        """Setup default health checks"""
        checks = [
            HealthCheck("API Health", "/health", 200),
            HealthCheck("Database Connection", "/db/health", 200),
            HealthCheck("MVP Orchestrator", "/mvp/health", 200),
            HealthCheck("Monitoring", "/metrics", 200),
            HealthCheck("Analytics", "/analytics/health", 200)
        ]
        
        for check in checks:
            self.health_checker.add_check(check)
    
    async def deploy(self) -> DeploymentMetrics:
        """Execute the complete deployment pipeline"""
        logger.info("🚀 Starting production deployment pipeline")
        
        self.resource_monitor.start_monitoring()
        
        try:
            # Phase 1: Pre-deployment checks
            await self._phase_pre_deployment_checks()
            
            # Phase 2: Backup current version
            await self._phase_backup()
            
            # Phase 3: Build and test
            await self._phase_build_and_test()
            
            # Phase 4: Deploy to production
            await self._phase_deploy()
            
            # Phase 5: Post-deployment validation
            await self._phase_post_deployment_validation()
            
            # Phase 6: Monitor and verify
            await self._phase_monitor_and_verify()
            
            self.deployment_metrics.status = DeploymentStatus.DEPLOYED
            self.deployment_metrics.end_time = datetime.now()
            
            logger.info("✅ Deployment completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            self.deployment_metrics.status = DeploymentStatus.FAILED
            self.deployment_metrics.error_logs.append(str(e))
            
            if self.config.rollback_on_failure:
                await self._rollback()
        
        finally:
            self.resource_monitor.stop_monitoring()
            self.deployment_metrics.resource_usage = self.resource_monitor.get_peak_usage()
        
        return self.deployment_metrics
    
    async def _phase_pre_deployment_checks(self):
        """Pre-deployment checks"""
        logger.info("Phase 1: Pre-deployment checks")
        
        # Check system resources
        memory = psutil.virtual_memory()
        if memory.percent > 85:
            raise RuntimeError(f"Insufficient memory: {memory.percent:.1f}% used")
        
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            raise RuntimeError(f"High CPU usage: {cpu_percent:.1f}%")
        
        # Check disk space
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            raise RuntimeError(f"Insufficient disk space: {disk.percent:.1f}% used")
        
        # Check ports availability
        required_ports = [8000, 8001, 9090, 3000]
        for port in required_ports:
            if self._is_port_in_use(port):
                logger.warning(f"Port {port} is already in use")
        
        logger.info("✅ Pre-deployment checks passed")
    
    async def _phase_backup(self):
        """Backup current deployment"""
        logger.info("Phase 2: Creating backup")
        
        if not self.config.backup_enabled:
            logger.info("Backup disabled - skipping")
            return
        
        source_dirs = [
            Path("tools"),
            Path("monitoring"),
            Path("scripts"),
            Path("config.yaml")
        ]
        
        # Filter existing directories
        existing_dirs = [d for d in source_dirs if d.exists()]
        
        backup_id = await self.backup_manager.create_backup(existing_dirs)
        self.deployment_metrics.resource_usage['backup_id'] = backup_id
        
        logger.info(f"✅ Backup created: {backup_id}")
    
    async def _phase_build_and_test(self):
        """Build and test phase"""
        logger.info("Phase 3: Build and test")
        
        build_start = time.time()
        
        try:
            # Mock build process
            logger.info("Building deployment package...")
            await asyncio.sleep(2)  # Simulate build time
            
            # Mock testing
            logger.info("Running tests...")
            await asyncio.sleep(3)  # Simulate test time
            
            # Simulate test results
            test_results = {
                'total_tests': 150,
                'passed_tests': 147,
                'failed_tests': 3,
                'coverage': 85.5
            }
            
            if test_results['failed_tests'] > 5:
                raise RuntimeError(f"Too many test failures: {test_results['failed_tests']}")
            
            if test_results['coverage'] < 80:
                raise RuntimeError(f"Insufficient test coverage: {test_results['coverage']:.1f}%")
            
            build_time = time.time() - build_start
            self.deployment_metrics.build_time_seconds = build_time
            self.deployment_metrics.test_time_seconds = build_time * 0.6  # 60% of time was testing
            
            logger.info(f"✅ Build and test completed in {build_time:.1f}s")
            
        except Exception as e:
            self.deployment_metrics.status = DeploymentStatus.FAILED
            raise RuntimeError(f"Build/test failed: {e}")
    
    async def _phase_deploy(self):
        """Deploy to production"""
        logger.info("Phase 4: Deploying to production")
        
        self.deployment_metrics.status = DeploymentStatus.DEPLOYING
        deploy_start = time.time()
        
        try:
            # Mock deployment steps
            steps = [
                "Stopping existing services...",
                "Updating application code...",
                "Updating configuration...",
                "Starting services...",
                "Waiting for services to stabilize..."
            ]
            
            for step in steps:
                logger.info(step)
                await asyncio.sleep(1)  # Simulate deployment time
            
            deploy_time = time.time() - deploy_start
            self.deployment_metrics.deployment_time_seconds = deploy_time
            
            logger.info(f"✅ Deployment completed in {deploy_time:.1f}s")
            
        except Exception as e:
            self.deployment_metrics.status = DeploymentStatus.FAILED
            raise RuntimeError(f"Deployment failed: {e}")
    
    async def _phase_post_deployment_validation(self):
        """Post-deployment validation"""
        logger.info("Phase 5: Post-deployment validation")
        
        # Wait for services to stabilize
        await asyncio.sleep(5)
        
        # Run health checks
        health_results = await self.health_checker.run_all_checks()
        self.deployment_metrics.health_checks = self.health_checker.checks
        
        if health_results['overall_status'] == HealthCheckStatus.UNHEALTHY:
            raise RuntimeError(f"Health checks failed: {health_results['unhealthy_checks']} unhealthy")
        
        if health_results['overall_status'] == HealthCheckStatus.DEGRADED:
            logger.warning(f"Some services are degraded: {health_results['degraded_checks']} degraded")
        
        logger.info(f"✅ Post-deployment validation completed: {health_results['healthy_checks']}/{health_results['total_checks']} healthy")
    
    async def _phase_monitor_and_verify(self):
        """Monitor and verify deployment"""
        logger.info("Phase 6: Monitoring and verification")
        
        # Monitor for 30 seconds to ensure stability
        monitor_duration = 30
        check_interval = 5
        
        for i in range(0, monitor_duration, check_interval):
            await asyncio.sleep(check_interval)
            
            # Check resource usage
            usage = self.resource_monitor.get_current_usage()
            if usage:
                memory_percent = usage.get('memory_percent', 0)
                cpu_percent = usage.get('cpu_percent', 0)
                
                if memory_percent > 90:
                    raise RuntimeError(f"Memory usage too high: {memory_percent:.1f}%")
                
                if cpu_percent > 85:
                    raise RuntimeError(f"CPU usage too high: {cpu_percent:.1f}%")
            
            # Run periodic health checks
            health_results = await self.health_checker.run_all_checks()
            if health_results['overall_status'] == HealthCheckStatus.UNHEALTHY:
                raise RuntimeError("Service became unhealthy during monitoring")
            
            logger.info(f"Monitoring: {i + check_interval}s elapsed - system stable")
        
        logger.info("✅ Monitoring and verification completed")
    
    async def _rollback(self):
        """Rollback deployment"""
        logger.info("🔄 Starting rollback procedure")
        
        self.deployment_metrics.status = DeploymentStatus.ROLLING_BACK
        
        try:
            # Get the latest backup
            backups = self.backup_manager.list_backups()
            if not backups:
                raise RuntimeError("No backups available for rollback")
            
            latest_backup = backups[0]
            backup_id = latest_backup['backup_id']
            
            # Restore from backup
            target_dirs = [Path("tools"), Path("monitoring"), Path("scripts")]
            success = await self.backup_manager.restore_backup(backup_id, target_dirs)
            
            if not success:
                raise RuntimeError("Backup restoration failed")
            
            # Restart services
            logger.info("Restarting services...")
            await asyncio.sleep(3)  # Simulate service restart
            
            # Verify rollback
            await asyncio.sleep(5)
            health_results = await self.health_checker.run_all_checks()
            
            if health_results['overall_status'] == HealthCheckStatus.UNHEALTHY:
                logger.error("❌ Rollback failed - services still unhealthy")
                self.deployment_metrics.status = DeploymentStatus.FAILED
            else:
                logger.info("✅ Rollback completed successfully")
                self.deployment_metrics.status = DeploymentStatus.ROLLED_BACK
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            self.deployment_metrics.status = DeploymentStatus.FAILED
            self.deployment_metrics.error_logs.append(f"Rollback failed: {e}")
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if port is in use"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def generate_deployment_report(self) -> Dict[str, Any]:
        """Generate deployment report"""
        total_time = (
            (self.deployment_metrics.end_time or datetime.now()) - 
            self.deployment_metrics.start_time
        ).total_seconds()
        
        report = {
            'deployment_id': f"deploy_{self.deployment_metrics.start_time.strftime('%Y%m%d_%H%M%S')}",
            'status': self.deployment_metrics.status.value,
            'total_time_seconds': total_time,
            'start_time': self.deployment_metrics.start_time.isoformat(),
            'end_time': self.deployment_metrics.end_time.isoformat() if self.deployment_metrics.end_time else None,
            'build_time_seconds': self.deployment_metrics.build_time_seconds,
            'test_time_seconds': self.deployment_metrics.test_time_seconds,
            'deployment_time_seconds': self.deployment_metrics.deployment_time_seconds,
            'health_checks': [
                {
                    'name': check.name,
                    'status': check.status.value,
                    'response_time_ms': check.response_time_ms,
                    'error_message': check.error_message
                }
                for check in self.deployment_metrics.health_checks
            ],
            'resource_usage': self.deployment_metrics.resource_usage,
            'error_logs': self.deployment_metrics.error_logs,
            'environment': self.config.environment
        }
        
        return report

async def main():
    """Main function for testing deployment pipeline"""
    print("🚀 Production Deployment Pipeline Test")
    print("=" * 40)
    
    # Create deployment configuration
    config = DeploymentConfig(
        environment="production",
        replicas=3,
        max_memory_mb=500,
        max_cpu_percent=25,
        rollback_on_failure=True,
        monitoring_enabled=True,
        backup_enabled=True
    )
    
    # Create deployment pipeline
    pipeline = ProductionDeploymentPipeline(config)
    
    # Run deployment
    metrics = await pipeline.deploy()
    
    # Generate report
    report = pipeline.generate_deployment_report()
    
    # Display results
    print(f"\n📊 Deployment Results:")
    print(f"• Status: {report['status']}")
    print(f"• Total Time: {report['total_time_seconds']:.1f}s")
    print(f"• Build Time: {report['build_time_seconds']:.1f}s")
    print(f"• Test Time: {report['test_time_seconds']:.1f}s")
    print(f"• Deploy Time: {report['deployment_time_seconds']:.1f}s")
    
    # Health check results
    healthy_checks = sum(1 for check in report['health_checks'] if check['status'] == 'healthy')
    total_checks = len(report['health_checks'])
    print(f"• Health Checks: {healthy_checks}/{total_checks} healthy")
    
    # Resource usage
    if report['resource_usage']:
        print(f"• Peak Memory: {report['resource_usage'].get('peak_memory_mb', 0):.0f}MB")
        print(f"• Peak CPU: {report['resource_usage'].get('peak_cpu_percent', 0):.1f}%")
    
    # Save report
    report_file = Path(f"deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Deployment report saved to: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())