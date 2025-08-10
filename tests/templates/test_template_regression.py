#!/usr/bin/env python3
"""
Template Regression Testing

Tests to ensure template changes don't break existing functionality.
Validates that template updates maintain backward compatibility and quality.
"""

import pytest
import asyncio
import json
import tempfile
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cookiecutter.main import cookiecutter
from tests.templates.test_template_quality_gates import TemplateQualityGates, ValidationResult


@dataclass
class TemplateSnapshot:
    """Snapshot of template validation results for regression testing"""
    template_name: str
    timestamp: datetime
    validation_score: float
    file_count: int
    total_size: int
    file_hashes: Dict[str, str]
    validation_details: Dict[str, Any]
    

class TemplateRegressionTester:
    """Regression testing system for templates"""
    
    def __init__(self, snapshots_dir: str = "template_snapshots"):
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(exist_ok=True)
        self.quality_gates = TemplateQualityGates()
        
    async def create_baseline_snapshots(self, templates_dir: Path) -> Dict[str, TemplateSnapshot]:
        """Create baseline snapshots for all templates"""
        snapshots = {}
        
        for template_dir in templates_dir.iterdir():
            if template_dir.is_dir() and (template_dir / "cookiecutter.json").exists():
                print(f"Creating baseline snapshot for: {template_dir.name}")
                snapshot = await self._create_template_snapshot(template_dir)
                snapshots[template_dir.name] = snapshot
                
                # Save snapshot to disk
                await self._save_snapshot(snapshot)
                
        return snapshots
    
    async def run_regression_tests(self, templates_dir: Path) -> Dict[str, Dict[str, Any]]:
        """Run regression tests against baseline snapshots"""
        results = {}
        
        for template_dir in templates_dir.iterdir():
            if template_dir.is_dir() and (template_dir / "cookiecutter.json").exists():
                print(f"Running regression test for: {template_dir.name}")
                result = await self._test_template_regression(template_dir)
                results[template_dir.name] = result
                
        return results
    
    async def _create_template_snapshot(self, template_path: Path) -> TemplateSnapshot:
        """Create a snapshot of a template's current state"""
        # Run validation
        validation_result = await self.quality_gates.validate_template(template_path)
        
        # Generate a test project to analyze structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Load template config
            config = self._load_template_config(template_path)
            test_context = self._generate_test_context(config)
            
            # Generate project
            project_dir = cookiecutter(
                str(template_path),
                extra_context=test_context,
                output_dir=str(temp_path),
                no_input=True,
                overwrite_if_exists=True
            )
            project_path = Path(project_dir)
            
            # Analyze generated project
            file_hashes = {}
            file_count = 0
            total_size = 0
            
            for file_path in project_path.rglob("*"):
                if file_path.is_file():
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            file_hash = hashlib.md5(content).hexdigest()
                            
                        relative_path = str(file_path.relative_to(project_path))
                        file_hashes[relative_path] = file_hash
                        file_count += 1
                        total_size += len(content)
                        
                    except Exception:
                        continue  # Skip files that can't be read
        
        return TemplateSnapshot(
            template_name=template_path.name,
            timestamp=datetime.now(),
            validation_score=validation_result.score,
            file_count=file_count,
            total_size=total_size,
            file_hashes=file_hashes,
            validation_details={
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "execution_time": validation_result.execution_time
            }
        )
    
    async def _test_template_regression(self, template_path: Path) -> Dict[str, Any]:
        """Test a template against its baseline snapshot"""
        template_name = template_path.name
        
        # Load baseline snapshot
        baseline = await self._load_snapshot(template_name)
        if not baseline:
            return {
                "status": "no_baseline",
                "message": f"No baseline snapshot found for {template_name}"
            }
        
        # Create current snapshot
        current = await self._create_template_snapshot(template_path)
        
        # Compare snapshots
        comparison = self._compare_snapshots(baseline, current)
        
        return {
            "status": "completed",
            "baseline_date": baseline.timestamp.isoformat(),
            "current_date": current.timestamp.isoformat(),
            "comparison": comparison,
            "regression_detected": comparison["has_regressions"]
        }
    
    def _compare_snapshots(self, baseline: TemplateSnapshot, current: TemplateSnapshot) -> Dict[str, Any]:
        """Compare two template snapshots for regressions"""
        comparison = {
            "has_regressions": False,
            "score_change": current.validation_score - baseline.validation_score,
            "file_count_change": current.file_count - baseline.file_count,
            "size_change": current.total_size - baseline.total_size,
            "new_files": [],
            "deleted_files": [],
            "modified_files": [],
            "validation_changes": {}
        }
        
        # Check for score regression (significant decrease)
        if comparison["score_change"] < -0.1:
            comparison["has_regressions"] = True
            
        # Check for file changes
        baseline_files = set(baseline.file_hashes.keys())
        current_files = set(current.file_hashes.keys())
        
        comparison["new_files"] = list(current_files - baseline_files)
        comparison["deleted_files"] = list(baseline_files - current_files)
        
        # Check for modified files
        common_files = baseline_files & current_files
        for file_path in common_files:
            if baseline.file_hashes[file_path] != current.file_hashes[file_path]:
                comparison["modified_files"].append(file_path)
        
        # Check validation changes
        baseline_valid = baseline.validation_details["is_valid"]
        current_valid = current.validation_details["is_valid"]
        
        if baseline_valid and not current_valid:
            comparison["has_regressions"] = True
            comparison["validation_changes"]["became_invalid"] = True
            
        # Compare error counts
        baseline_errors = len(baseline.validation_details["errors"])
        current_errors = len(current.validation_details["errors"])
        
        if current_errors > baseline_errors:
            comparison["has_regressions"] = True
            comparison["validation_changes"]["error_increase"] = current_errors - baseline_errors
            
        return comparison
    
    async def _save_snapshot(self, snapshot: TemplateSnapshot):
        """Save snapshot to disk"""
        snapshot_file = self.snapshots_dir / f"{snapshot.template_name}_baseline.json"
        
        snapshot_data = {
            "template_name": snapshot.template_name,
            "timestamp": snapshot.timestamp.isoformat(),
            "validation_score": snapshot.validation_score,
            "file_count": snapshot.file_count,
            "total_size": snapshot.total_size,
            "file_hashes": snapshot.file_hashes,
            "validation_details": snapshot.validation_details
        }
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
    
    async def _load_snapshot(self, template_name: str) -> Optional[TemplateSnapshot]:
        """Load snapshot from disk"""
        snapshot_file = self.snapshots_dir / f"{template_name}_baseline.json"
        
        if not snapshot_file.exists():
            return None
            
        try:
            with open(snapshot_file, 'r') as f:
                data = json.load(f)
                
            return TemplateSnapshot(
                template_name=data["template_name"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                validation_score=data["validation_score"],
                file_count=data["file_count"],
                total_size=data["total_size"],
                file_hashes=data["file_hashes"],
                validation_details=data["validation_details"]
            )
        except Exception:
            return None
    
    def _load_template_config(self, template_path: Path) -> Dict[str, Any]:
        """Load cookiecutter configuration"""
        config_file = template_path / "cookiecutter.json"
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def _generate_test_context(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test context for template"""
        base_context = {
            "project_name": "Test Project",
            "project_slug": "test-project",
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "version": "0.1.0"
        }
        
        # Add config-specific values
        for key, value in config.items():
            if key not in base_context:
                if isinstance(value, list) and len(value) > 0:
                    base_context[key] = value[0]
                elif isinstance(value, str) and not value.startswith("{{"):
                    base_context[key] = value
        
        return base_context
    
    def generate_regression_report(self, results: Dict[str, Dict[str, Any]]) -> str:
        """Generate regression test report"""
        report = []
        report.append("# Template Regression Test Report")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        total_templates = len(results)
        regressions_detected = sum(1 for r in results.values() 
                                 if r.get("regression_detected", False))
        
        report.append("## Summary")
        report.append(f"- Total Templates Tested: {total_templates}")
        report.append(f"- Regressions Detected: {regressions_detected}")
        report.append(f"- Templates Passing: {total_templates - regressions_detected}")
        report.append("")
        
        # Detailed results
        for template_name, result in results.items():
            if result["status"] == "no_baseline":
                status = "⚠️  NO BASELINE"
                report.append(f"## {template_name} {status}")
                report.append(f"- {result['message']}")
                report.append("")
                continue
                
            status = "❌ REGRESSION" if result.get("regression_detected", False) else "✅ PASS"
            report.append(f"## {template_name} {status}")
            
            comparison = result["comparison"]
            report.append(f"- Score Change: {comparison['score_change']:+.3f}")
            report.append(f"- File Count Change: {comparison['file_count_change']:+d}")
            report.append(f"- Size Change: {comparison['size_change']:+d} bytes")
            
            if comparison["new_files"]:
                report.append(f"- New Files: {len(comparison['new_files'])}")
                for file_path in comparison["new_files"][:5]:  # Show first 5
                    report.append(f"  - {file_path}")
                    
            if comparison["deleted_files"]:
                report.append(f"- Deleted Files: {len(comparison['deleted_files'])}")
                for file_path in comparison["deleted_files"][:5]:  # Show first 5
                    report.append(f"  - {file_path}")
                    
            if comparison["modified_files"]:
                report.append(f"- Modified Files: {len(comparison['modified_files'])}")
                
            validation_changes = comparison["validation_changes"]
            if validation_changes:
                report.append("- Validation Changes:")
                for change, value in validation_changes.items():
                    report.append(f"  - {change}: {value}")
            
            report.append("")
        
        return "\n".join(report)


# Test Suite
class TestTemplateRegression:
    """Test suite for template regression testing"""
    
    @pytest.fixture
    def regression_tester(self):
        """Regression tester instance"""
        return TemplateRegressionTester()
    
    @pytest.fixture
    def templates_dir(self):
        """Path to templates directory"""
        return Path(__file__).parent.parent.parent / "templates"
    
    @pytest.mark.asyncio
    async def test_create_baseline_snapshots(self, regression_tester, templates_dir):
        """Test creating baseline snapshots"""
        if not templates_dir.exists():
            pytest.skip("Templates directory not found")
        
        snapshots = await regression_tester.create_baseline_snapshots(templates_dir)
        
        assert isinstance(snapshots, dict)
        assert len(snapshots) > 0
        
        # Verify snapshot structure
        for template_name, snapshot in snapshots.items():
            assert isinstance(snapshot, TemplateSnapshot)
            assert snapshot.template_name == template_name
            assert 0.0 <= snapshot.validation_score <= 1.0
            assert snapshot.file_count > 0
            assert snapshot.total_size > 0
            assert len(snapshot.file_hashes) > 0
    
    @pytest.mark.asyncio
    async def test_regression_detection(self, regression_tester, templates_dir):
        """Test regression detection capabilities"""
        if not templates_dir.exists():
            pytest.skip("Templates directory not found")
        
        # First create baselines (if not exist)
        await regression_tester.create_baseline_snapshots(templates_dir)
        
        # Then run regression tests
        results = await regression_tester.run_regression_tests(templates_dir)
        
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # Check result structure
        for template_name, result in results.items():
            assert "status" in result
            assert result["status"] in ["completed", "no_baseline"]
            
            if result["status"] == "completed":
                assert "baseline_date" in result
                assert "current_date" in result
                assert "comparison" in result
                assert "regression_detected" in result
                
                comparison = result["comparison"]
                assert "has_regressions" in comparison
                assert "score_change" in comparison
                assert "file_count_change" in comparison
                assert "size_change" in comparison
        
        # Generate and print report
        report = regression_tester.generate_regression_report(results)
        print(f"\n{report}")
    
    def test_snapshot_serialization(self, regression_tester):
        """Test snapshot serialization/deserialization"""
        # Create a test snapshot
        test_snapshot = TemplateSnapshot(
            template_name="test_template",
            timestamp=datetime.now(),
            validation_score=0.85,
            file_count=10,
            total_size=1024,
            file_hashes={"file1.py": "abc123", "file2.js": "def456"},
            validation_details={"is_valid": True, "errors": [], "warnings": []}
        )
        
        # Test serialization by calling the save/load methods
        import asyncio
        
        async def test_async():
            await regression_tester._save_snapshot(test_snapshot)
            loaded_snapshot = await regression_tester._load_snapshot("test_template")
            
            assert loaded_snapshot is not None
            assert loaded_snapshot.template_name == test_snapshot.template_name
            assert loaded_snapshot.validation_score == test_snapshot.validation_score
            assert loaded_snapshot.file_count == test_snapshot.file_count
            assert loaded_snapshot.total_size == test_snapshot.total_size
            assert loaded_snapshot.file_hashes == test_snapshot.file_hashes
        
        asyncio.run(test_async())
    
    def test_snapshot_comparison(self, regression_tester):
        """Test snapshot comparison logic"""
        # Create baseline snapshot
        baseline = TemplateSnapshot(
            template_name="test_template",
            timestamp=datetime.now() - timedelta(days=1),
            validation_score=0.90,
            file_count=10,
            total_size=1024,
            file_hashes={"file1.py": "abc123", "file2.js": "def456"},
            validation_details={"is_valid": True, "errors": [], "warnings": []}
        )
        
        # Create current snapshot with changes
        current = TemplateSnapshot(
            template_name="test_template", 
            timestamp=datetime.now(),
            validation_score=0.75,  # Score decreased (regression)
            file_count=11,  # File added
            total_size=1200,  # Size increased
            file_hashes={"file1.py": "abc123", "file2.js": "xyz789", "file3.css": "new123"},
            validation_details={"is_valid": True, "errors": [], "warnings": []}
        )
        
        comparison = regression_tester._compare_snapshots(baseline, current)
        
        # Should detect regression due to score decrease
        assert comparison["has_regressions"] == True
        assert comparison["score_change"] == -0.15
        assert comparison["file_count_change"] == 1
        assert comparison["size_change"] == 176
        assert "file3.css" in comparison["new_files"]
        assert "file2.js" in comparison["modified_files"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])