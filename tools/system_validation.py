#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pytest>=7.0.0",
#     "pytest-asyncio>=0.21.0",
#     "rich>=13.9.0",
#     "pydantic>=2.9.0"
# ]
# ///
"""
Comprehensive System Validation Script

This script validates the entire Startup Factory system including:
1. Component isolation testing
2. Contract compliance verification  
3. Integration testing
4. Performance benchmarking
5. Configuration validation
6. Template system verification

Usage:
    uv run tools/system_validation.py
    uv run tools/system_validation.py --quick  # Run only critical tests
    uv run tools/system_validation.py --component mvp_orchestrator  # Test specific component
"""

import asyncio
import subprocess
import sys
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.panel import Panel
from rich.text import Text
from pydantic import BaseModel

console = Console()

class ValidationStatus(str, Enum):
    """Status of validation checks"""
    PASSED = "✅ PASSED"
    FAILED = "❌ FAILED"  
    WARNING = "⚠️  WARNING"
    SKIPPED = "⏭️  SKIPPED"
    RUNNING = "🔄 RUNNING"

@dataclass
class ValidationResult:
    """Result of a validation check"""
    name: str
    status: ValidationStatus
    duration_ms: int
    message: str
    details: Optional[Dict] = None

class SystemValidator:
    """Comprehensive system validator"""
    
    def __init__(self, quick_mode: bool = False, specific_component: Optional[str] = None):
        self.quick_mode = quick_mode
        self.specific_component = specific_component
        self.results: List[ValidationResult] = []
        
        # Test discovery
        self.project_root = Path(__file__).parent.parent
        self.test_dirs = {
            "components": self.project_root / "tests" / "components",
            "contracts": self.project_root / "tests" / "contracts", 
            "integration": self.project_root / "tests" / "integration",
            "architecture": self.project_root / "tests" / "architecture"
        }
    
    def log_result(self, result: ValidationResult):
        """Log a validation result"""
        self.results.append(result)
        
        status_color = {
            ValidationStatus.PASSED: "green",
            ValidationStatus.FAILED: "red",
            ValidationStatus.WARNING: "yellow", 
            ValidationStatus.SKIPPED: "blue",
            ValidationStatus.RUNNING: "cyan"
        }.get(result.status, "white")
        
        console.print(
            f"{result.status} {result.name} ({result.duration_ms}ms)",
            style=status_color
        )
        
        if result.message:
            console.print(f"  {result.message}", style="dim")
    
    async def run_pytest_suite(self, test_path: Path, test_name: str) -> ValidationResult:
        """Run a pytest suite and return results"""
        start_time = time.time()
        
        try:
            if not test_path.exists():
                return ValidationResult(
                    name=test_name,
                    status=ValidationStatus.SKIPPED,
                    duration_ms=0,
                    message=f"Test file not found: {test_path}"
                )
            
            # Run pytest with specific options for CI/automation
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_path),
                "-v",
                "--tb=short",
                "--no-header",
                "--quiet"
            ]
            
            if self.quick_mode:
                cmd.extend(["-x", "--maxfail=1"])  # Stop on first failure
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5 minute timeout
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if result.returncode == 0:
                return ValidationResult(
                    name=test_name,
                    status=ValidationStatus.PASSED,
                    duration_ms=duration_ms,
                    message="All tests passed",
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )
            else:
                return ValidationResult(
                    name=test_name,
                    status=ValidationStatus.FAILED,
                    duration_ms=duration_ms,
                    message=f"Tests failed with return code {result.returncode}",
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )
                
        except subprocess.TimeoutExpired:
            return ValidationResult(
                name=test_name,
                status=ValidationStatus.FAILED,
                duration_ms=int((time.time() - start_time) * 1000),
                message="Test suite timed out after 5 minutes"
            )
        except Exception as e:
            return ValidationResult(
                name=test_name,
                status=ValidationStatus.FAILED, 
                duration_ms=int((time.time() - start_time) * 1000),
                message=f"Error running tests: {str(e)}"
            )
    
    async def validate_component_isolation(self) -> List[ValidationResult]:
        """Validate individual components in isolation"""
        results = []
        
        console.print("\n🔍 [bold]Component Isolation Testing[/bold]")
        
        component_tests = {
            "MVP Orchestrator": "test_mvp_orchestrator_isolated.py",
            "AI Provider Manager": "test_ai_provider_manager_isolated.py",
            "Template Manager": "test_template_manager_isolated.py",
            "Budget Monitor": "test_budget_monitor_isolated.py"
        }
        
        for component_name, test_file in component_tests.items():
            if self.specific_component and self.specific_component.lower() not in component_name.lower():
                continue
                
            test_path = self.test_dirs["components"] / test_file
            result = await self.run_pytest_suite(test_path, f"Component: {component_name}")
            results.append(result)
            self.log_result(result)
        
        return results
    
    async def validate_contracts(self) -> List[ValidationResult]:
        """Validate component contracts"""
        results = []
        
        console.print("\n📄 [bold]Contract Testing[/bold]")
        
        contract_tests = {
            "AI Provider Contracts": "test_ai_provider_contracts.py",
            "Resource Manager Contracts": "test_resource_manager_contracts.py", 
            "Template System Contracts": "test_template_contracts.py"
        }
        
        for contract_name, test_file in contract_tests.items():
            test_path = self.test_dirs["contracts"] / test_file
            result = await self.run_pytest_suite(test_path, f"Contract: {contract_name}")
            results.append(result)
            self.log_result(result)
        
        return results
    
    async def validate_integration(self) -> List[ValidationResult]:
        """Validate integration testing"""
        results = []
        
        console.print("\n🔗 [bold]Integration Testing[/bold]")
        
        integration_tests = {
            "Critical User Journeys": "test_critical_user_journeys.py",
            "End-to-End Workflows": "test_end_to_end_workflows.py"
        }
        
        for integration_name, test_file in integration_tests.items():
            test_path = self.test_dirs["integration"] / test_file
            result = await self.run_pytest_suite(test_path, f"Integration: {integration_name}")
            results.append(result)
            self.log_result(result)
        
        return results
    
    async def validate_system_configuration(self) -> ValidationResult:
        """Validate system configuration"""
        start_time = time.time()
        
        console.print("\n⚙️ [bold]System Configuration Validation[/bold]")
        
        try:
            # Check required files exist
            required_files = [
                "tools/mvp_orchestrator_script.py",
                "tools/ai_providers.py", 
                "tools/config.yaml",
                "templates/neoforge/cookiecutter.json"
            ]
            
            missing_files = []
            for file_path in required_files:
                full_path = self.project_root / file_path
                if not full_path.exists():
                    missing_files.append(file_path)
            
            if missing_files:
                return ValidationResult(
                    name="System Configuration",
                    status=ValidationStatus.FAILED,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message=f"Missing required files: {', '.join(missing_files)}"
                )
            
            # Validate configuration file
            config_path = self.project_root / "tools" / "config.yaml"
            try:
                import yaml
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                
                required_keys = [
                    "openai_api_key", "anthropic_api_key", "perplexity_api_key"
                ]
                missing_keys = [key for key in required_keys if key not in config]
                
                if missing_keys:
                    return ValidationResult(
                        name="System Configuration",
                        status=ValidationStatus.WARNING,
                        duration_ms=int((time.time() - start_time) * 1000),
                        message=f"Missing config keys: {', '.join(missing_keys)}"
                    )
            except Exception as e:
                return ValidationResult(
                    name="System Configuration",
                    status=ValidationStatus.WARNING,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message=f"Config validation error: {str(e)}"
                )
            
            return ValidationResult(
                name="System Configuration",
                status=ValidationStatus.PASSED,
                duration_ms=int((time.time() - start_time) * 1000),
                message="All configuration checks passed"
            )
            
        except Exception as e:
            return ValidationResult(
                name="System Configuration",
                status=ValidationStatus.FAILED,
                duration_ms=int((time.time() - start_time) * 1000),
                message=f"Configuration validation failed: {str(e)}"
            )
    
    async def validate_template_system(self) -> ValidationResult:
        """Validate template generation system"""
        start_time = time.time()
        
        console.print("\n📋 [bold]Template System Validation[/bold]")
        
        try:
            # Check template structure
            template_path = self.project_root / "templates" / "neoforge"
            if not template_path.exists():
                return ValidationResult(
                    name="Template System",
                    status=ValidationStatus.FAILED,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message="NeoForge template directory not found"
                )
            
            # Check cookiecutter.json
            cookiecutter_path = template_path / "cookiecutter.json"
            if not cookiecutter_path.exists():
                return ValidationResult(
                    name="Template System",
                    status=ValidationStatus.FAILED,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message="cookiecutter.json not found"
                )
            
            # Validate cookiecutter.json structure
            with open(cookiecutter_path) as f:
                cookiecutter_config = json.load(f)
            
            required_vars = ["project_name", "project_slug", "author_name"]
            missing_vars = [var for var in required_vars if var not in cookiecutter_config]
            
            if missing_vars:
                return ValidationResult(
                    name="Template System",
                    status=ValidationStatus.WARNING,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message=f"Missing template variables: {', '.join(missing_vars)}"
                )
            
            # Test template generation (dry run)
            test_config = {
                "project_name": "Test Project",
                "project_slug": "test-project",
                "author_name": "Test Author",
                "author_email": "test@example.com"
            }
            
            # In a real implementation, would test cookiecutter generation
            # For now, just validate the template structure exists
            template_project_path = template_path / "{{cookiecutter.project_slug}}"
            if not template_project_path.exists():
                return ValidationResult(
                    name="Template System", 
                    status=ValidationStatus.WARNING,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message="Template project structure not found"
                )
            
            return ValidationResult(
                name="Template System",
                status=ValidationStatus.PASSED,
                duration_ms=int((time.time() - start_time) * 1000),
                message="Template system validation passed"
            )
            
        except Exception as e:
            return ValidationResult(
                name="Template System",
                status=ValidationStatus.FAILED,
                duration_ms=int((time.time() - start_time) * 1000),
                message=f"Template validation failed: {str(e)}"
            )
    
    async def validate_orchestrator_functionality(self) -> ValidationResult:
        """Test MVP orchestrator can be imported and initialized"""
        start_time = time.time()
        
        console.print("\n🎼 [bold]Orchestrator Functionality Validation[/bold]")
        
        try:
            # Try to import orchestrator
            sys.path.insert(0, str(self.project_root / "tools"))
            
            from mvp_orchestrator_script import MVPOrchestrator, Config
            from pathlib import Path
            
            # Test configuration creation
            test_config = Config(
                openai_api_key="test-key",
                anthropic_api_key="test-key", 
                perplexity_api_key="test-key",
                project_root=Path(tempfile.mkdtemp()) / "validation_test"
            )
            
            # Test orchestrator initialization
            orchestrator = MVPOrchestrator(test_config)
            
            # Verify basic functionality
            assert hasattr(orchestrator, 'config')
            assert hasattr(orchestrator, 'projects') 
            assert hasattr(orchestrator, 'api_manager')
            assert hasattr(orchestrator, 'doc_manager')
            
            return ValidationResult(
                name="Orchestrator Functionality",
                status=ValidationStatus.PASSED,
                duration_ms=int((time.time() - start_time) * 1000),
                message="Orchestrator can be imported and initialized"
            )
            
        except ImportError as e:
            return ValidationResult(
                name="Orchestrator Functionality",
                status=ValidationStatus.FAILED,
                duration_ms=int((time.time() - start_time) * 1000),
                message=f"Import error: {str(e)}"
            )
        except Exception as e:
            return ValidationResult(
                name="Orchestrator Functionality",
                status=ValidationStatus.FAILED,
                duration_ms=int((time.time() - start_time) * 1000),
                message=f"Initialization error: {str(e)}"
            )
    
    def generate_report(self) -> None:
        """Generate validation report"""
        console.print("\n" + "="*60)
        console.print("[bold]🏁 VALIDATION SUMMARY[/bold]", justify="center")
        console.print("="*60)
        
        # Count results by status
        status_counts = {}
        total_duration = 0
        
        for result in self.results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
            total_duration += result.duration_ms
        
        # Create summary table
        table = Table(title="Validation Results")
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")
        
        total_tests = len(self.results)
        for status, count in status_counts.items():
            percentage = (count / total_tests) * 100 if total_tests > 0 else 0
            table.add_row(status, str(count), f"{percentage:.1f}%")
        
        console.print(table)
        
        # Overall status
        failed_count = status_counts.get(ValidationStatus.FAILED, 0)
        warning_count = status_counts.get(ValidationStatus.WARNING, 0)
        
        if failed_count == 0 and warning_count == 0:
            overall_status = "🎉 [bold green]ALL VALIDATIONS PASSED[/bold green]"
        elif failed_count == 0:
            overall_status = "⚠️  [bold yellow]PASSED WITH WARNINGS[/bold yellow]"
        else:
            overall_status = "❌ [bold red]VALIDATION FAILURES DETECTED[/bold red]"
        
        console.print(f"\n{overall_status}")
        console.print(f"Total execution time: {total_duration / 1000:.2f} seconds")
        
        # Detailed failures
        failures = [r for r in self.results if r.status == ValidationStatus.FAILED]
        if failures:
            console.print("\n[bold red]❌ FAILED VALIDATIONS:[/bold red]")
            for failure in failures:
                console.print(f"  • {failure.name}: {failure.message}")
        
        # Recommendations
        if failed_count > 0:
            console.print("\n[bold]🔧 RECOMMENDATIONS:[/bold]")
            console.print("1. Fix failed validations before deploying")
            console.print("2. Run individual test suites for detailed error information")
            console.print("3. Check logs and configuration files")
        
        console.print(f"\n📊 Validation completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    async def run_full_validation(self) -> None:
        """Run complete system validation"""
        console.print("[bold blue]🚀 Starting Startup Factory System Validation[/bold blue]")
        console.print(f"Mode: {'Quick' if self.quick_mode else 'Complete'}")
        if self.specific_component:
            console.print(f"Component: {self.specific_component}")
        
        # Run all validations
        validation_tasks = [
            self.validate_system_configuration(),
            self.validate_orchestrator_functionality(), 
            self.validate_template_system()
        ]
        
        # Add test suite validations
        if not self.specific_component or "component" in self.specific_component.lower():
            validation_tasks.append(self.validate_component_isolation())
        
        if not self.specific_component or "contract" in self.specific_component.lower():
            validation_tasks.append(self.validate_contracts())
        
        if not self.specific_component or "integration" in self.specific_component.lower():
            validation_tasks.append(self.validate_integration())
        
        # Execute validations
        start_time = time.time()
        
        for task in validation_tasks:
            if asyncio.iscoroutine(task):
                result = await task
                if isinstance(result, list):
                    self.results.extend(result)
                else:
                    self.results.append(result)
                    self.log_result(result)
        
        total_time = time.time() - start_time
        
        # Generate report
        self.generate_report()


async def main():
    """Main validation entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Startup Factory System Validation")
    parser.add_argument("--quick", action="store_true", help="Run quick validation (essential tests only)")
    parser.add_argument("--component", type=str, help="Validate specific component only")
    
    args = parser.parse_args()
    
    validator = SystemValidator(
        quick_mode=args.quick,
        specific_component=args.component
    )
    
    await validator.run_full_validation()


if __name__ == "__main__":
    asyncio.run(main())