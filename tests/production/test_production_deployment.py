#!/usr/bin/env python3
"""
Comprehensive Test Suite for Production Deployment Pipeline
Fixed version with proper async/await handling and realistic test scenarios.
"""

import asyncio
import json
import pytest
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import psutil
import shutil

# Import the modules under test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from production_deployment import (
    DeploymentStatus, HealthCheckStatus, DeploymentConfig, HealthCheck,
    DeploymentMetrics, ResourceMonitor, HealthChecker, BackupManager,
    ProductionDeploymentPipeline
)


class TestDeploymentConfig:
    """Test suite for DeploymentConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = DeploymentConfig()
        
        assert config.environment == "production"
        assert config.replicas == 3
        assert config.max_memory_mb == 500
        assert config.max_cpu_percent == 25
        assert config.health_check_interval == 30
        assert config.health_check_timeout == 10
        assert config.rollback_on_failure is True
        assert config.monitoring_enabled is True
        assert config.backup_enabled is True
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = DeploymentConfig(
            environment="staging",
            replicas=2,
            max_memory_mb=1024,
            max_cpu_percent=50,
            health_check_interval=60,
            rollback_on_failure=False
        )
        
        assert config.environment == "staging"
        assert config.replicas == 2
        assert config.max_memory_mb == 1024
        assert config.max_cpu_percent == 50
        assert config.health_check_interval == 60
        assert config.rollback_on_failure is False


class TestHealthCheck:
    """Test suite for HealthCheck dataclass"""
    
    def test_default_health_check(self):
        """Test default health check values"""
        check = HealthCheck(name="Test Check", endpoint="/health")
        
        assert check.name == "Test Check"
        assert check.endpoint == "/health"
        assert check.expected_status == 200
        assert check.timeout == 10
        assert check.retries == 3
        assert check.status == HealthCheckStatus.UNKNOWN
        assert check.last_check is None
        assert check.response_time_ms is None
        assert check.error_message is None
    
    def test_custom_health_check(self):
        """Test custom health check configuration"""
        check = HealthCheck(
            name="Custom API Check",
            endpoint="/api/health",
            expected_status=201,
            timeout=20,
            retries=5
        )
        
        assert check.name == "Custom API Check"
        assert check.endpoint == "/api/health"
        assert check.expected_status == 201
        assert check.timeout == 20
        assert check.retries == 5


class TestDeploymentMetrics:
    """Test suite for DeploymentMetrics dataclass"""
    
    def test_default_metrics(self):
        """Test default metrics initialization"""
        start_time = datetime.now()
        metrics = DeploymentMetrics(start_time=start_time)
        
        assert metrics.start_time == start_time
        assert metrics.end_time is None
        assert metrics.status == DeploymentStatus.PENDING
        assert metrics.build_time_seconds is None
        assert metrics.test_time_seconds is None
        assert metrics.deployment_time_seconds is None
        assert metrics.health_checks == []
        assert metrics.resource_usage == {}
        assert metrics.error_logs == []


class TestResourceMonitor:
    """Test suite for ResourceMonitor"""
    
    @pytest.fixture
    def monitor(self):
        """Create ResourceMonitor instance for testing"""
        return ResourceMonitor(max_memory_mb=1000, max_cpu_percent=50)
    
    def test_initialization(self, monitor):
        """Test resource monitor initialization"""
        assert monitor.max_memory_mb == 1000
        assert monitor.max_cpu_percent == 50
        assert monitor.monitoring is False
        assert monitor.metrics == []
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """Test start and stop monitoring functions"""
        # Mock asyncio.create_task to avoid actual task creation
        with patch('asyncio.create_task') as mock_create_task:
            monitor.start_monitoring()
            assert monitor.monitoring is True
            assert monitor.metrics == []
            mock_create_task.assert_called_once()
        
        monitor.stop_monitoring()
        assert monitor.monitoring is False
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    async def test_monitor_loop_single_iteration(self, mock_cpu, mock_memory, monitor):
        """Test single iteration of monitor loop"""
        # Mock system resources
        mock_memory_obj = Mock()
        mock_memory_obj.used = 1024 * 1024 * 1024  # 1GB
        mock_memory_obj.percent = 75.0
        mock_memory_obj.available = 256 * 1024 * 1024  # 256MB
        mock_memory.return_value = mock_memory_obj
        mock_cpu.return_value = 45.5
        
        # Set monitoring to True but stop after one iteration
        monitor.monitoring = True
        
        # Mock asyncio.sleep to control the loop
        sleep_call_count = 0
        async def mock_sleep(duration):
            nonlocal sleep_call_count
            sleep_call_count += 1
            if sleep_call_count >= 1:
                monitor.monitoring = False  # Stop after first iteration
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await monitor._monitor_loop()
        
        # Verify metrics were collected
        assert len(monitor.metrics) >= 1
        
        latest_metric = monitor.metrics[-1]
        assert 'timestamp' in latest_metric
        assert 'memory_usage_mb' in latest_metric
        assert 'memory_percent' in latest_metric
        assert 'cpu_percent' in latest_metric
        assert 'available_memory_mb' in latest_metric
        
        assert latest_metric['memory_percent'] == 75.0
        assert latest_metric['cpu_percent'] == 45.5
    
    def test_get_current_usage_empty(self, monitor):
        """Test get_current_usage with no metrics"""
        usage = monitor.get_current_usage()
        assert usage == {}
    
    def test_get_current_usage_with_data(self, monitor):
        """Test get_current_usage with metrics data"""
        # Add mock metric
        monitor.metrics.append({
            'timestamp': datetime.now().isoformat(),
            'memory_usage_mb': 512.0,
            'memory_percent': 50.0,
            'cpu_percent': 25.0,
            'available_memory_mb': 512.0
        })
        
        usage = monitor.get_current_usage()
        assert usage['memory_usage_mb'] == 512.0
        assert usage['cpu_percent'] == 25.0
    
    def test_get_peak_usage_empty(self, monitor):
        """Test get_peak_usage with no metrics"""
        peak = monitor.get_peak_usage()
        assert peak == {}
    
    def test_get_peak_usage_with_data(self, monitor):
        """Test get_peak_usage with multiple metrics"""
        # Add multiple metrics
        base_time = datetime.now()
        metrics = [
            {
                'timestamp': (base_time + timedelta(seconds=i)).isoformat(),
                'memory_usage_mb': 100.0 + i * 50,
                'cpu_percent': 20.0 + i * 10
            }
            for i in range(5)
        ]
        monitor.metrics.extend(metrics)
        
        peak = monitor.get_peak_usage()
        assert peak['peak_memory_mb'] == 300.0  # Last metric has highest memory
        assert peak['peak_cpu_percent'] == 60.0  # Last metric has highest CPU
        assert 'peak_memory_time' in peak
        assert 'peak_cpu_time' in peak


class TestHealthChecker:
    """Test suite for HealthChecker"""
    
    @pytest.fixture
    def health_checker(self):
        """Create HealthChecker instance for testing"""
        return HealthChecker()
    
    def test_initialization(self, health_checker):
        """Test health checker initialization"""
        assert health_checker.checks == []
    
    def test_add_check(self, health_checker):
        """Test adding health checks"""
        check1 = HealthCheck("API Health", "/health")
        check2 = HealthCheck("DB Health", "/db/health")
        
        health_checker.add_check(check1)
        health_checker.add_check(check2)
        
        assert len(health_checker.checks) == 2
        assert health_checker.checks[0] == check1
        assert health_checker.checks[1] == check2
    
    @pytest.mark.asyncio
    async def test_run_single_check_healthy(self, health_checker):
        """Test running a single healthy check"""
        check = HealthCheck("Test Check", "/health")
        health_checker.add_check(check)
        
        # Mock the random results to be healthy (both calls return <= 0.9)
        with patch('random.random', return_value=0.8):  # <= 0.9 for both calls = healthy
            await health_checker._run_single_check(check)
        
        assert check.status == HealthCheckStatus.HEALTHY
        assert check.error_message is None
        assert check.response_time_ms is not None
        assert check.response_time_ms > 0
        assert check.last_check is not None
    
    @pytest.mark.asyncio
    async def test_run_single_check_unhealthy(self, health_checker):
        """Test running a single unhealthy check"""
        check = HealthCheck("Test Check", "/health")
        health_checker.add_check(check)
        
        # Mock the random result to be unhealthy (> 0.9 on first call)
        with patch('random.random', return_value=0.95):  # > 0.9 = unhealthy
            await health_checker._run_single_check(check)
        
        assert check.status == HealthCheckStatus.UNHEALTHY
        assert check.error_message == "Service unavailable"
        assert check.response_time_ms is not None
        assert check.last_check is not None
    
    @pytest.mark.asyncio
    async def test_run_single_check_degraded(self, health_checker):
        """Test running a single degraded check"""
        check = HealthCheck("Test Check", "/health")
        health_checker.add_check(check)
        
        # Mock to get degraded result (first <= 0.9, then > 0.95)
        with patch('random.random', side_effect=[0.8, 0.96]):  # First healthy, second degraded
            await health_checker._run_single_check(check)
        
        assert check.status == HealthCheckStatus.DEGRADED
        assert check.error_message == "Slow response"
        assert check.response_time_ms is not None
        assert check.last_check is not None
    
    @pytest.mark.asyncio
    async def test_run_all_checks_mixed_results(self, health_checker):
        """Test running all checks - verify basic functionality"""
        # Configure checks
        checks = [
            HealthCheck("Check 1", "/health1"),
            HealthCheck("Check 2", "/health2"),
            HealthCheck("Check 3", "/health3"),
        ]
        
        for check in checks:
            health_checker.add_check(check)
        
        # Run the checks (with natural randomness)
        results = await health_checker.run_all_checks()
        
        # Verify overall results structure
        assert 'total_checks' in results
        assert 'healthy_checks' in results
        assert 'unhealthy_checks' in results
        assert 'degraded_checks' in results
        assert 'overall_status' in results
        assert 'checks' in results
        
        # Verify basic counts
        assert results['total_checks'] == 3
        assert results['healthy_checks'] + results['unhealthy_checks'] + results['degraded_checks'] == 3
        
        # Verify each check has proper structure
        for check_result in results['checks']:
            assert 'name' in check_result
            assert 'status' in check_result
            assert 'response_time_ms' in check_result
            assert check_result['status'] in ['healthy', 'unhealthy', 'degraded']
    
    @pytest.mark.asyncio
    async def test_run_all_checks_empty(self, health_checker):
        """Test running all checks when no checks are configured"""
        results = await health_checker.run_all_checks()
        
        assert results['total_checks'] == 0
        assert results['healthy_checks'] == 0
        assert results['unhealthy_checks'] == 0
        assert results['degraded_checks'] == 0
        assert results['overall_status'] == HealthCheckStatus.HEALTHY
        assert results['checks'] == []


class TestBackupManager:
    """Test suite for BackupManager"""
    
    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def backup_manager(self, temp_backup_dir):
        """Create BackupManager instance with temp directory"""
        return BackupManager(backup_dir=temp_backup_dir / "backups")
    
    @pytest.fixture
    def sample_source_dirs(self, temp_backup_dir):
        """Create sample source directories for backup testing"""
        source1 = temp_backup_dir / "source1"
        source2 = temp_backup_dir / "source2"
        
        source1.mkdir()
        source2.mkdir()
        
        # Create some test files
        (source1 / "file1.txt").write_text("Content 1")
        (source1 / "subdir").mkdir()
        (source1 / "subdir" / "file2.txt").write_text("Content 2")
        
        (source2 / "file3.txt").write_text("Content 3")
        
        return [source1, source2]
    
    def test_initialization(self, temp_backup_dir):
        """Test backup manager initialization"""
        backup_dir = temp_backup_dir / "test_backups"
        manager = BackupManager(backup_dir)
        
        assert manager.backup_dir == backup_dir
        assert backup_dir.exists()  # Should be created during init
    
    @pytest.mark.asyncio
    async def test_create_backup(self, backup_manager, sample_source_dirs):
        """Test creating a backup"""
        backup_id = await backup_manager.create_backup(sample_source_dirs)
        
        # Verify backup ID format
        assert backup_id.startswith("backup_")
        assert len(backup_id.split("_")) == 3  # backup_YYYYMMDD_HHMMSS
        
        # Verify backup directory was created
        backup_path = backup_manager.backup_dir / backup_id
        assert backup_path.exists()
        assert backup_path.is_dir()
        
        # Verify source directories were copied
        assert (backup_path / "source1").exists()
        assert (backup_path / "source2").exists()
        
        # Verify file contents
        assert (backup_path / "source1" / "file1.txt").read_text() == "Content 1"
        assert (backup_path / "source1" / "subdir" / "file2.txt").read_text() == "Content 2"
        assert (backup_path / "source2" / "file3.txt").read_text() == "Content 3"
        
        # Verify metadata file
        metadata_file = backup_path / "metadata.json"
        assert metadata_file.exists()
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata['backup_id'] == backup_id
        assert 'created_at' in metadata
        assert 'source_dirs' in metadata
        assert 'backup_path' in metadata
        assert len(metadata['source_dirs']) == 2
    
    def test_list_backups_empty(self, backup_manager):
        """Test listing backups when none exist"""
        backups = backup_manager.list_backups()
        assert backups == []


class TestProductionDeploymentPipeline:
    """Test suite for main ProductionDeploymentPipeline"""
    
    @pytest.fixture
    def deployment_config(self):
        """Create deployment configuration for testing"""
        return DeploymentConfig(
            environment="test",
            replicas=2,
            max_memory_mb=1000,
            max_cpu_percent=50,
            health_check_interval=10,
            rollback_on_failure=True,
            monitoring_enabled=True,
            backup_enabled=True
        )
    
    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def deployment_pipeline(self, deployment_config, temp_backup_dir):
        """Create ProductionDeploymentPipeline for testing"""
        pipeline = ProductionDeploymentPipeline(deployment_config)
        # Override backup manager to use temp directory
        pipeline.backup_manager = BackupManager(backup_dir=temp_backup_dir / "backups")
        return pipeline
    
    def test_initialization(self, deployment_pipeline, deployment_config):
        """Test pipeline initialization"""
        assert deployment_pipeline.config == deployment_config
        assert isinstance(deployment_pipeline.resource_monitor, ResourceMonitor)
        assert isinstance(deployment_pipeline.health_checker, HealthChecker)
        assert isinstance(deployment_pipeline.backup_manager, BackupManager)
        assert isinstance(deployment_pipeline.deployment_metrics, DeploymentMetrics)
        
        # Verify default health checks were added
        assert len(deployment_pipeline.health_checker.checks) == 5
        expected_checks = ["API Health", "Database Connection", "MVP Orchestrator", "Monitoring", "Analytics"]
        actual_checks = [check.name for check in deployment_pipeline.health_checker.checks]
        for expected in expected_checks:
            assert expected in actual_checks
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.disk_usage')
    async def test_phase_pre_deployment_checks_success(self, mock_disk, mock_cpu, mock_memory, deployment_pipeline):
        """Test successful pre-deployment checks"""
        # Mock system resources within acceptable ranges
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 70.0  # Below 85% threshold
        mock_memory.return_value = mock_memory_obj
        
        mock_cpu.return_value = 60.0  # Below 80% threshold
        
        mock_disk_obj = Mock()
        mock_disk_obj.percent = 75.0  # Below 90% threshold
        mock_disk.return_value = mock_disk_obj
        
        # Should complete without raising exception
        await deployment_pipeline._phase_pre_deployment_checks()
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    async def test_phase_pre_deployment_checks_high_memory(self, mock_memory, deployment_pipeline):
        """Test pre-deployment checks with high memory usage"""
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 90.0  # Above 85% threshold
        mock_memory.return_value = mock_memory_obj
        
        with pytest.raises(RuntimeError, match="Insufficient memory: 90.0% used"):
            await deployment_pipeline._phase_pre_deployment_checks()
    
    @pytest.mark.asyncio
    async def test_phase_backup_disabled(self, deployment_pipeline):
        """Test backup phase when backup is disabled"""
        deployment_pipeline.config.backup_enabled = False
        
        # Should complete quickly without creating backup
        await deployment_pipeline._phase_backup()
        
        # Verify no backup was created
        backups = deployment_pipeline.backup_manager.list_backups()
        assert len(backups) == 0
    
    @pytest.mark.asyncio
    async def test_phase_build_and_test_success(self, deployment_pipeline):
        """Test successful build and test phase"""
        await deployment_pipeline._phase_build_and_test()
        
        # Verify metrics were recorded
        assert deployment_pipeline.deployment_metrics.build_time_seconds is not None
        assert deployment_pipeline.deployment_metrics.build_time_seconds > 0
        assert deployment_pipeline.deployment_metrics.test_time_seconds is not None
        assert deployment_pipeline.deployment_metrics.test_time_seconds > 0
    
    @pytest.mark.asyncio
    async def test_phase_deploy_success(self, deployment_pipeline):
        """Test successful deployment phase"""
        await deployment_pipeline._phase_deploy()
        
        # Verify deployment metrics
        assert deployment_pipeline.deployment_metrics.status == DeploymentStatus.DEPLOYING
        assert deployment_pipeline.deployment_metrics.deployment_time_seconds is not None
        assert deployment_pipeline.deployment_metrics.deployment_time_seconds > 0
    
    @pytest.mark.asyncio
    async def test_phase_post_deployment_validation_success(self, deployment_pipeline):
        """Test successful post-deployment validation"""
        with patch('random.random', return_value=0.8):  # All health checks will be healthy (< 0.9)
            await deployment_pipeline._phase_post_deployment_validation()
        
        # Verify health checks were stored
        assert len(deployment_pipeline.deployment_metrics.health_checks) > 0
    
    @pytest.mark.asyncio
    async def test_phase_post_deployment_validation_unhealthy(self, deployment_pipeline):
        """Test post-deployment validation with unhealthy services"""
        with patch('random.random', return_value=0.95):  # All health checks will be unhealthy (> 0.9)
            with pytest.raises(RuntimeError, match="Health checks failed"):
                await deployment_pipeline._phase_post_deployment_validation()
    
    def test_is_port_in_use_free_port(self, deployment_pipeline):
        """Test port checking with free port"""
        # Use a high port number that's likely to be free
        is_used = deployment_pipeline._is_port_in_use(65432)
        # Could be either True or False depending on system state
        assert isinstance(is_used, bool)
    
    def test_generate_deployment_report_basic(self, deployment_pipeline):
        """Test basic deployment report generation"""
        report = deployment_pipeline.generate_deployment_report()
        
        # Verify required fields
        assert 'deployment_id' in report
        assert 'status' in report
        assert 'total_time_seconds' in report
        assert 'start_time' in report
        assert 'end_time' in report
        assert 'build_time_seconds' in report
        assert 'test_time_seconds' in report
        assert 'deployment_time_seconds' in report
        assert 'health_checks' in report
        assert 'resource_usage' in report
        assert 'error_logs' in report
        assert 'environment' in report
        
        # Verify data types and values
        assert report['deployment_id'].startswith('deploy_')
        assert report['status'] == DeploymentStatus.PENDING.value
        assert report['total_time_seconds'] >= 0
        assert report['environment'] == deployment_pipeline.config.environment
        assert isinstance(report['health_checks'], list)
        assert isinstance(report['resource_usage'], dict)
        assert isinstance(report['error_logs'], list)
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.disk_usage')
    async def test_full_deployment_success(self, mock_disk, mock_cpu, mock_memory, deployment_pipeline):
        """Test complete successful deployment workflow"""
        # Mock system resources
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 70.0
        mock_memory.return_value = mock_memory_obj
        mock_cpu.return_value = 60.0
        mock_disk_obj = Mock()
        mock_disk_obj.percent = 75.0
        mock_disk.return_value = mock_disk_obj
        
        # Mock healthy health checks
        with patch('random.random', return_value=0.8), \
             patch('pathlib.Path.exists', return_value=False), \
             patch('asyncio.sleep'):  # Speed up sleep calls
            
            metrics = await deployment_pipeline.deploy()
        
        assert metrics.status == DeploymentStatus.DEPLOYED
        assert metrics.end_time is not None
        assert metrics.build_time_seconds is not None
        assert metrics.test_time_seconds is not None
        assert metrics.deployment_time_seconds is not None


# Performance and Load Testing
class TestDeploymentPerformance:
    """Performance tests for deployment system"""
    
    @pytest.fixture
    def performance_config(self):
        """High-performance deployment configuration"""
        return DeploymentConfig(
            environment="performance_test",
            replicas=5,
            max_memory_mb=2048,
            max_cpu_percent=75,
            health_check_interval=5,
            rollback_on_failure=False,  # Don't rollback during perf tests
            backup_enabled=False  # Skip backup for performance
        )
    
    @pytest.fixture
    def performance_pipeline(self, performance_config):
        """High-performance deployment pipeline"""
        return ProductionDeploymentPipeline(performance_config)
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self, performance_pipeline):
        """Test health check performance with many checks"""
        # Add many health checks
        for i in range(50):
            check = HealthCheck(f"Performance Check {i}", f"/health{i}")
            performance_pipeline.health_checker.add_check(check)
        
        # Measure health check execution time
        start_time = time.time()
        
        with patch('random.random', return_value=0.8):  # All healthy
            await performance_pipeline.health_checker.run_all_checks()
        
        execution_time = time.time() - start_time
        
        # Should complete 50 health checks in reasonable time (< 10 seconds)
        # Each check has 0.1s delay, so 50 checks = ~5s + overhead
        assert execution_time < 10.0
        # Pipeline already has 5 default checks + 50 we added = 55 total
        assert len(performance_pipeline.health_checker.checks) == 55
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.disk_usage')
    async def test_pre_deployment_checks_performance(self, mock_disk, mock_cpu, mock_memory, performance_pipeline):
        """Test pre-deployment checks performance"""
        # Mock system resources
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 50.0
        mock_memory.return_value = mock_memory_obj
        mock_cpu.return_value = 40.0
        mock_disk_obj = Mock()
        mock_disk_obj.percent = 60.0
        mock_disk.return_value = mock_disk_obj
        
        # Measure pre-deployment check time
        start_time = time.time()
        
        await performance_pipeline._phase_pre_deployment_checks()
        
        execution_time = time.time() - start_time
        
        # Pre-deployment checks should be fast (< 1 second)
        assert execution_time < 1.0


# Integration Testing
class TestDeploymentIntegration:
    """Integration tests combining multiple components"""
    
    @pytest.mark.asyncio
    async def test_complete_deployment_workflow_integration(self):
        """Test complete deployment workflow from start to finish"""
        # Create a fully configured deployment
        config = DeploymentConfig(
            environment="integration_test",
            replicas=2,
            rollback_on_failure=True,
            backup_enabled=True
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline = ProductionDeploymentPipeline(config)
            pipeline.backup_manager = BackupManager(backup_dir=Path(temp_dir) / "backups")
            
            # Mock all external dependencies
            with patch('psutil.virtual_memory') as mock_memory, \
                 patch('psutil.cpu_percent') as mock_cpu, \
                 patch('psutil.disk_usage') as mock_disk, \
                 patch('random.random') as mock_random, \
                 patch('asyncio.sleep'), \
                 patch('pathlib.Path.exists', return_value=False):
                
                # Setup mocks for successful deployment
                mock_memory_obj = Mock()
                mock_memory_obj.percent = 60.0
                mock_memory.return_value = mock_memory_obj
                mock_cpu.return_value = 45.0
                mock_disk_obj = Mock()
                mock_disk_obj.percent = 70.0
                mock_disk.return_value = mock_disk_obj
                mock_random.return_value = 0.8  # Healthy checks
                
                # Execute deployment
                metrics = await pipeline.deploy()
                
                # Verify complete workflow
                assert metrics.status == DeploymentStatus.DEPLOYED
                assert metrics.build_time_seconds is not None
                assert metrics.test_time_seconds is not None
                assert metrics.deployment_time_seconds is not None
                assert len(metrics.health_checks) > 0
                
                # Generate and verify report
                report = pipeline.generate_deployment_report()
                assert report['status'] == 'deployed'
                assert report['total_time_seconds'] > 0
                assert len(report['health_checks']) > 0


if __name__ == "__main__":
    # Run the tests with coverage reporting
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=production_deployment",
        "--cov-report=term-missing"
    ])