#!/usr/bin/env python3
"""
Template System Performance Testing Framework

Performance benchmarks and stress tests for template system operations.
Tests template generation speed, memory usage, and concurrent processing.

Performance Categories:
1. Template Generation Speed Benchmarks
2. Memory Usage Analysis
3. Concurrent Processing Performance
4. Large Template Processing
5. Resource Efficiency Testing
"""

import pytest
import asyncio
import time
import json
import tempfile
import shutil
import psutil
import statistics
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import threading
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from template_manager import TemplateManager, TemplateInfo, TemplateProcessor
from core_types import ResourceAllocation, APIQuota


def create_test_resource_allocation(
    startup_id: str = "test",
    memory_mb: int = 512,
    cpu_cores: float = 1.0,
    storage_gb: int = 10,
    ports: List[int] = None,
    database_namespace: str = "test_db"
) -> ResourceAllocation:
    """Helper function to create ResourceAllocation for tests"""
    if ports is None:
        ports = [3000, 8000]
    
    return ResourceAllocation(
        startup_id=startup_id,
        memory_mb=memory_mb,
        cpu_cores=cpu_cores,
        storage_gb=storage_gb,
        ports=ports,
        database_namespace=database_namespace,
        api_quota=APIQuota(calls_per_hour=1000, cost_per_day=10.0),
        allocated_at=datetime.now()
    )


@dataclass
class PerformanceMetrics:
    """Performance metrics for template operations"""
    operation: str
    duration: float
    memory_before_mb: float
    memory_after_mb: float
    memory_peak_mb: float
    cpu_percent: float
    template_size_bytes: int
    generated_size_bytes: int
    success: bool
    error: Optional[str] = None


class PerformanceBenchmark:
    """Performance benchmark utilities"""
    
    @staticmethod
    def measure_memory() -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    @staticmethod
    def measure_cpu() -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=0.1)
    
    @staticmethod
    def get_directory_size(path: Path) -> int:
        """Get total size of directory in bytes"""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    @classmethod
    async def measure_async_operation(cls, operation_name: str, operation_func, *args, **kwargs) -> PerformanceMetrics:
        """Measure performance of an async operation"""
        # Start monitoring
        memory_before = cls.measure_memory()
        memory_peak = memory_before
        
        # Monitor memory during operation
        memory_monitor = threading.Event()
        
        def monitor_memory():
            nonlocal memory_peak
            while not memory_monitor.is_set():
                current_memory = cls.measure_memory()
                memory_peak = max(memory_peak, current_memory)
                time.sleep(0.01)  # Check every 10ms
        
        monitor_thread = threading.Thread(target=monitor_memory)
        monitor_thread.start()
        
        # Execute operation
        start_time = time.perf_counter()
        cpu_before = cls.measure_cpu()
        
        success = True
        error = None
        result = None
        
        try:
            result = await operation_func(*args, **kwargs)
        except Exception as e:
            success = False
            error = str(e)
        
        end_time = time.perf_counter()
        cpu_after = cls.measure_cpu()
        
        # Stop monitoring
        memory_monitor.set()
        monitor_thread.join()
        
        memory_after = cls.measure_memory()
        duration = end_time - start_time
        cpu_percent = (cpu_before + cpu_after) / 2
        
        return PerformanceMetrics(
            operation=operation_name,
            duration=duration,
            memory_before_mb=memory_before,
            memory_after_mb=memory_after,
            memory_peak_mb=memory_peak,
            cpu_percent=cpu_percent,
            template_size_bytes=0,  # To be set by caller if applicable
            generated_size_bytes=0,  # To be set by caller if applicable
            success=success,
            error=error
        ), result


class TestTemplateGenerationPerformance:
    """Test template generation performance benchmarks"""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def create_performance_template(self, temp_templates_dir):
        """Create template optimized for performance testing"""
        def _create_template(name: str, file_count: int = 10, file_size_kb: int = 1) -> Path:
            template_dir = temp_templates_dir / name
            template_dir.mkdir(parents=True)
            
            # Create cookiecutter config
            config = {
                "project_name": "Performance Test",
                "project_slug": "performance-test",
                "description": "Template for performance testing",
                "version": "1.0.0"
            }
            (template_dir / "cookiecutter.json").write_text(json.dumps(config, indent=2))
            (template_dir / "README.md").write_text("Performance testing template")
            
            # Create project directory with multiple files
            project_dir = template_dir / "{{cookiecutter.project_slug}}"
            project_dir.mkdir(parents=True)
            
            # Generate files of specified size
            content = "# {{cookiecutter.project_name}}\n" + "x" * (file_size_kb * 1024 - 50)
            
            for i in range(file_count):
                file_path = project_dir / f"file_{i}.py"
                file_path.write_text(f'"""File {i} for {{{{cookiecutter.project_name}}}}"""\n{content}')
            
            # Add some directories with files
            for dir_i in range(3):
                sub_dir = project_dir / f"subdir_{dir_i}"
                sub_dir.mkdir(parents=True)
                for file_i in range(5):
                    sub_file = sub_dir / f"subfile_{file_i}.py"
                    sub_file.write_text(f"# {{{{cookiecutter.project_name}}}} subdir {dir_i} file {file_i}")
            
            return template_dir
        
        return _create_template
    
    @pytest.mark.asyncio
    async def test_single_template_generation_speed(self, temp_templates_dir, create_performance_template):
        """Test speed of single template generation"""
        # Arrange
        create_performance_template("speed_test", file_count=50, file_size_kb=2)
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        startup_config = {
            "name": "Speed Test Project",
            "description": "Testing generation speed"
        }
        resource_allocation = create_test_resource_allocation(
            startup_id="speed_test",
            memory_mb=512,
            cpu_cores=1.0,
            ports=[3000],
            database_namespace="speed_test_db"
        )
        
        output_dir = temp_templates_dir / "speed_output"
        
        # Act
        metrics, result = await PerformanceBenchmark.measure_async_operation(
            "single_template_generation",
            manager.create_from_template,
            "speed_test", startup_config, resource_allocation, output_dir
        )
        
        # Calculate sizes
        template_path = temp_templates_dir / "speed_test" / "{{cookiecutter.project_slug}}"
        metrics.template_size_bytes = PerformanceBenchmark.get_directory_size(template_path)
        if result:
            metrics.generated_size_bytes = PerformanceBenchmark.get_directory_size(Path(result))
        
        # Assert performance benchmarks
        assert metrics.success is True
        assert metrics.duration < 5.0  # Should complete within 5 seconds
        assert metrics.memory_peak_mb - metrics.memory_before_mb < 100  # Should use <100MB additional memory
        
        print(f"✅ Single template generation:")
        print(f"  Duration: {metrics.duration:.3f}s")
        print(f"  Memory used: {metrics.memory_peak_mb - metrics.memory_before_mb:.1f}MB")
        print(f"  Template size: {metrics.template_size_bytes / 1024:.1f}KB")
        print(f"  Generated size: {metrics.generated_size_bytes / 1024:.1f}KB")
    
    @pytest.mark.asyncio
    async def test_concurrent_template_generation_performance(self, temp_templates_dir, create_performance_template):
        """Test performance with concurrent template generation"""
        # Arrange
        create_performance_template("concurrent_test", file_count=20, file_size_kb=1)
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        output_dir = temp_templates_dir / "concurrent_output"
        
        async def generate_template(index: int):
            startup_config = {
                "name": f"Concurrent Test {index}",
                "description": f"Concurrent generation test {index}"
            }
            resource_allocation = create_test_resource_allocation(
                startup_id=f"concurrent_test_{index}",
                memory_mb=256,
                cpu_cores=0.5,
                ports=[3000 + index],
                database_namespace=f"concurrent_db_{index}"
            )
            
            return await manager.create_from_template(
                "concurrent_test", startup_config, resource_allocation, output_dir
            )
        
        concurrent_count = 10
        
        # Act
        metrics, results = await PerformanceBenchmark.measure_async_operation(
            "concurrent_template_generation",
            lambda: asyncio.gather(*[generate_template(i) for i in range(concurrent_count)])
        )
        
        # Assert
        assert metrics.success is True
        assert len(results) == concurrent_count
        assert all(result is not None for result in results)
        
        # Performance expectations for concurrent generation
        assert metrics.duration < 15.0  # Should complete within 15 seconds
        assert metrics.memory_peak_mb - metrics.memory_before_mb < 500  # Should use <500MB for 10 concurrent
        
        print(f"✅ Concurrent template generation ({concurrent_count} templates):")
        print(f"  Duration: {metrics.duration:.3f}s")
        print(f"  Memory used: {metrics.memory_peak_mb - metrics.memory_before_mb:.1f}MB")
        print(f"  Throughput: {concurrent_count / metrics.duration:.1f} templates/second")
    
    @pytest.mark.asyncio
    async def test_large_template_processing_performance(self, temp_templates_dir, create_performance_template):
        """Test performance with large templates"""
        # Arrange - Create a large template
        create_performance_template("large_test", file_count=200, file_size_kb=10)  # ~2MB template
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        startup_config = {
            "name": "Large Template Test",
            "description": "Testing large template processing"
        }
        resource_allocation = create_test_resource_allocation(
            startup_id="large_test",
            memory_mb=1024,
            cpu_cores=2.0,
            ports=[3000, 8000],
            database_namespace="large_test_db"
        )
        
        output_dir = temp_templates_dir / "large_output"
        
        # Act
        metrics, result = await PerformanceBenchmark.measure_async_operation(
            "large_template_processing",
            manager.create_from_template,
            "large_test", startup_config, resource_allocation, output_dir
        )
        
        # Calculate sizes
        template_path = temp_templates_dir / "large_test" / "{{cookiecutter.project_slug}}"
        metrics.template_size_bytes = PerformanceBenchmark.get_directory_size(template_path)
        if result:
            metrics.generated_size_bytes = PerformanceBenchmark.get_directory_size(Path(result))
        
        # Assert
        assert metrics.success is True
        assert metrics.duration < 30.0  # Should complete within 30 seconds even for large templates
        assert metrics.memory_peak_mb - metrics.memory_before_mb < 200  # Should use reasonable memory
        
        print(f"✅ Large template processing:")
        print(f"  Duration: {metrics.duration:.3f}s")
        print(f"  Memory used: {metrics.memory_peak_mb - metrics.memory_before_mb:.1f}MB")
        print(f"  Template size: {metrics.template_size_bytes / 1024 / 1024:.1f}MB")
        print(f"  Generated size: {metrics.generated_size_bytes / 1024 / 1024:.1f}MB")
    
    @pytest.mark.asyncio
    async def test_template_validation_performance(self, temp_templates_dir, create_performance_template):
        """Test template validation performance"""
        # Arrange
        create_performance_template("validation_test", file_count=100, file_size_kb=1)
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Act
        metrics, result = await PerformanceBenchmark.measure_async_operation(
            "template_validation",
            manager.validate_template,
            "validation_test"
        )
        
        # Assert
        assert metrics.success is True
        assert result.is_valid is True
        assert metrics.duration < 2.0  # Validation should be very fast
        assert metrics.memory_peak_mb - metrics.memory_before_mb < 50  # Should use minimal memory
        
        print(f"✅ Template validation performance:")
        print(f"  Duration: {metrics.duration:.3f}s")
        print(f"  Memory used: {metrics.memory_peak_mb - metrics.memory_before_mb:.1f}MB")
        print(f"  Validation score: {result.score:.2f}")


class TestTemplateProcessorPerformance:
    """Test template processor performance for variable substitution"""
    
    @pytest.fixture
    def processor(self):
        """Template processor for testing"""
        return TemplateProcessor()
    
    @pytest.mark.asyncio
    async def test_variable_substitution_performance(self, processor):
        """Test performance of variable substitution"""
        # Arrange
        large_context = {
            f"var_{i}": f"value_{i}" for i in range(1000)
        }
        
        # Create template with many variables
        template_content = "\n".join([f"Variable {i}: {{{{var_{i}}}}}" for i in range(100)])
        
        # Act
        metrics, result = await PerformanceBenchmark.measure_async_operation(
            "variable_substitution",
            processor._process_text,
            template_content, large_context
        )
        
        # Assert
        assert metrics.success is True
        assert result is not None
        assert metrics.duration < 1.0  # Should be very fast
        assert "value_50" in result  # Verify substitution worked
        
        print(f"✅ Variable substitution performance:")
        print(f"  Duration: {metrics.duration:.3f}s")
        print(f"  Variables processed: 100")
        print(f"  Context size: 1000 variables")
    
    @pytest.mark.asyncio
    async def test_json_processing_performance(self, processor):
        """Test performance of JSON template processing"""
        # Arrange
        context = {f"key_{i}": f"value_{i}" for i in range(500)}
        
        # Create large JSON template
        json_template = {
            f"field_{i}": f"{{{{key_{i % 500}}}}}" for i in range(1000)
        }
        template_content = json.dumps(json_template, indent=2)
        
        # Act
        metrics, result = await PerformanceBenchmark.measure_async_operation(
            "json_processing",
            processor._process_json,
            template_content, context
        )
        
        # Assert
        assert metrics.success is True
        processed_data = json.loads(result)
        assert len(processed_data) == 1000
        assert "value_0" in str(processed_data)
        assert metrics.duration < 2.0  # Should complete quickly
        
        print(f"✅ JSON processing performance:")
        print(f"  Duration: {metrics.duration:.3f}s")
        print(f"  JSON fields: 1000")
        print(f"  Template size: {len(template_content) / 1024:.1f}KB")


class TestMemoryEfficiency:
    """Test memory efficiency and resource cleanup"""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_after_generation(self, temp_templates_dir):
        """Test that memory is properly cleaned up after template generation"""
        # Arrange
        template_dir = temp_templates_dir / "memory_test"
        template_dir.mkdir(parents=True)
        
        config = {"project_name": "Memory Test", "project_slug": "memory-test"}
        (template_dir / "cookiecutter.json").write_text(json.dumps(config))
        (template_dir / "README.md").write_text("Memory test template")
        
        project_dir = template_dir / "{{cookiecutter.project_slug}}"
        project_dir.mkdir(parents=True)
        
        # Create large files to test memory usage
        large_content = "x" * (100 * 1024)  # 100KB per file
        for i in range(50):
            (project_dir / f"large_file_{i}.txt").write_text(f"File {i}\n{large_content}")
        
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Measure baseline memory
        baseline_memory = PerformanceBenchmark.measure_memory()
        
        # Act - Generate template multiple times
        for i in range(5):
            startup_config = {
                "name": f"Memory Test {i}",
                "description": f"Memory test {i}"
            }
            resource_allocation = create_test_resource_allocation(
                startup_id=f"memory_test_{i}",
                memory_mb=256,
                cpu_cores=0.5,
                ports=[3000 + i],
                database_namespace=f"memory_db_{i}"
            )
            
            await manager.create_from_template(
                "memory_test", startup_config, resource_allocation, 
                temp_templates_dir / f"memory_output_{i}"
            )
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Measure final memory
        final_memory = PerformanceBenchmark.measure_memory()
        memory_increase = final_memory - baseline_memory
        
        # Assert
        assert memory_increase < 100  # Should not leak more than 100MB
        
        print(f"✅ Memory cleanup test:")
        print(f"  Baseline memory: {baseline_memory:.1f}MB")
        print(f"  Final memory: {final_memory:.1f}MB")
        print(f"  Memory increase: {memory_increase:.1f}MB")
    
    @pytest.mark.asyncio
    async def test_concurrent_memory_usage(self, temp_templates_dir):
        """Test memory usage with concurrent operations"""
        # Arrange
        template_dir = temp_templates_dir / "concurrent_memory_test"
        template_dir.mkdir(parents=True)
        
        config = {"project_name": "Concurrent Memory Test"}
        (template_dir / "cookiecutter.json").write_text(json.dumps(config))
        (template_dir / "README.md").write_text("Concurrent memory test")
        
        project_dir = template_dir / "{{cookiecutter.project_slug}}"
        project_dir.mkdir(parents=True)
        (project_dir / "app.py").write_text('"""{{project_name}}"""')
        
        manager = TemplateManager(str(temp_templates_dir))
        await manager.initialize()
        
        # Monitor memory during concurrent operations
        baseline_memory = PerformanceBenchmark.measure_memory()
        peak_memory = baseline_memory
        
        async def monitor_memory():
            nonlocal peak_memory
            for _ in range(100):  # Monitor for 10 seconds
                current_memory = PerformanceBenchmark.measure_memory()
                peak_memory = max(peak_memory, current_memory)
                await asyncio.sleep(0.1)
        
        async def generate_templates():
            tasks = []
            for i in range(20):
                startup_config = {"name": f"Concurrent Memory {i}", "description": "Concurrent memory test"}
                resource_allocation = create_test_resource_allocation(
                    startup_id=f"concurrent_memory_{i}",
                    memory_mb=128,
                    cpu_cores=0.25,
                    ports=[3000 + i],
                    database_namespace=f"concurrent_db_{i}"
                )
                
                task = manager.create_from_template(
                    "concurrent_memory_test", startup_config, resource_allocation,
                    temp_templates_dir / "concurrent_memory_output"
                )
                tasks.append(task)
            
            return await asyncio.gather(*tasks)
        
        # Act - Run concurrent generation with memory monitoring
        results = await asyncio.gather(
            monitor_memory(),
            generate_templates()
        )
        
        templates = results[1]
        memory_peak_usage = peak_memory - baseline_memory
        
        # Assert
        assert len(templates) == 20
        assert all(template is not None for template in templates)
        assert memory_peak_usage < 300  # Should use reasonable memory for 20 concurrent templates
        
        print(f"✅ Concurrent memory usage test:")
        print(f"  Baseline memory: {baseline_memory:.1f}MB")
        print(f"  Peak memory: {peak_memory:.1f}MB")
        print(f"  Peak usage: {memory_peak_usage:.1f}MB")
        print(f"  Templates generated: {len(templates)}")


class TestPerformanceRegression:
    """Test for performance regressions"""
    
    @pytest.fixture
    def performance_targets(self):
        """Define performance targets for regression testing"""
        return {
            "single_template_generation": {"max_duration": 5.0, "max_memory_mb": 100},
            "template_validation": {"max_duration": 2.0, "max_memory_mb": 50},
            "concurrent_generation_10": {"max_duration": 15.0, "max_memory_mb": 500},
            "large_template_processing": {"max_duration": 30.0, "max_memory_mb": 200}
        }
    
    def test_performance_targets_defined(self, performance_targets):
        """Verify performance targets are properly defined"""
        assert len(performance_targets) > 0
        for operation, targets in performance_targets.items():
            assert "max_duration" in targets
            assert "max_memory_mb" in targets
            assert targets["max_duration"] > 0
            assert targets["max_memory_mb"] > 0
        print("✅ Performance targets defined and valid")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])