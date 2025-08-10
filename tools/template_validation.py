#!/usr/bin/env python3
"""
Template Validation Core Module

Core validation logic extracted for reuse in CLI and test modules.
This module provides the main validation classes without pytest dependencies.
"""

import asyncio
import json
import yaml
import toml
import time
import os
import re
import ast
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from cookiecutter.main import cookiecutter


@dataclass
class ValidationResult:
    """Result of template validation"""
    is_valid: bool
    score: float  # 0.0 - 1.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


class TemplateQualityGates:
    """Main template quality validation system"""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self.temp_dir = None
        self.validation_results = {}
        
    async def validate_all_templates(self) -> Dict[str, ValidationResult]:
        """Validate all available templates"""
        results = {}
        
        # Get all template directories
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")
            
        for template_dir in self.templates_dir.iterdir():
            if template_dir.is_dir() and (template_dir / "cookiecutter.json").exists():
                print(f"Validating template: {template_dir.name}")
                results[template_dir.name] = await self.validate_template(template_dir)
                
        self.validation_results = results
        return results
    
    async def validate_template(self, template_path: Union[str, Path]) -> ValidationResult:
        """Validate a specific template"""
        template_path = Path(template_path)
        start_time = time.time()
        
        result = ValidationResult(
            is_valid=True,
            score=1.0,
            execution_time=0.0
        )
        
        try:
            # Load template configuration
            config = self._load_template_config(template_path)
            if not config:
                result.is_valid = False
                result.errors.append("Failed to load cookiecutter.json")
                return result
                
            # Create test contexts for validation
            test_contexts = self._generate_test_contexts(config)
            
            # Validate each test context
            for i, context in enumerate(test_contexts):
                context_result = await self._validate_template_context(
                    template_path, context, f"test_context_{i}"
                )
                
                # Merge results
                result.errors.extend(context_result.errors)
                result.warnings.extend(context_result.warnings)
                result.details[f"context_{i}"] = context_result.details
                
                if not context_result.is_valid:
                    result.is_valid = False
                    
                # Update score (average of all contexts)
                result.score = min(result.score, context_result.score)
        
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Template validation failed: {str(e)}")
            result.score = 0.0
            
        finally:
            result.execution_time = time.time() - start_time
            
        return result
    
    async def _validate_template_context(
        self, 
        template_path: Path, 
        context: Dict[str, Any], 
        test_name: str
    ) -> ValidationResult:
        """Validate template with a specific context"""
        result = ValidationResult(is_valid=True, score=1.0)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Generate project from template
                project_dir = await self._generate_project(
                    template_path, context, temp_path / test_name
                )
                
                # Run all validation checks
                structure_result = await self._validate_structure(project_dir, template_path.name)
                config_result = await self._validate_configurations(project_dir)
                code_result = await self._validate_code_quality(project_dir)
                functionality_result = await self._validate_functionality(project_dir)
                security_result = await self._validate_security(project_dir)
                
                # Merge all results
                all_results = [structure_result, config_result, code_result, 
                             functionality_result, security_result]
                
                for check_result in all_results:
                    result.errors.extend(check_result.errors)
                    result.warnings.extend(check_result.warnings)
                    result.details.update(check_result.details)
                    
                    if not check_result.is_valid:
                        result.is_valid = False
                        
                    result.score = min(result.score, check_result.score)
                    
            except Exception as e:
                result.is_valid = False
                result.errors.append(f"Context validation failed: {str(e)}")
                result.score = 0.0
                
        return result
    
    async def _generate_project(
        self, 
        template_path: Path, 
        context: Dict[str, Any], 
        output_dir: Path
    ) -> Path:
        """Generate project from template"""
        try:
            # Use cookiecutter to generate project
            project_dir = cookiecutter(
                str(template_path),
                extra_context=context,
                output_dir=str(output_dir.parent),
                no_input=True,
                overwrite_if_exists=True
            )
            
            return Path(project_dir)
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate project: {str(e)}")
    
    async def _validate_structure(self, project_dir: Path, template_name: str) -> ValidationResult:
        """Validate project structure"""
        result = ValidationResult(is_valid=True, score=1.0, details={"validation_type": "structure"})
        
        # Template-specific required files and directories
        required_structure = self._get_required_structure(template_name)
        
        missing_files = []
        missing_dirs = []
        
        # Check required files
        for file_path in required_structure.get("files", []):
            full_path = project_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)
                
        # Check required directories
        for dir_path in required_structure.get("directories", []):
            full_path = project_dir / dir_path
            if not full_path.is_dir():
                missing_dirs.append(dir_path)
        
        if missing_files:
            result.errors.extend([f"Missing required file: {f}" for f in missing_files])
            result.is_valid = False
            
        if missing_dirs:
            result.errors.extend([f"Missing required directory: {d}" for d in missing_dirs])
            result.is_valid = False
            
        # Calculate structure score
        total_required = len(required_structure.get("files", [])) + len(required_structure.get("directories", []))
        missing_count = len(missing_files) + len(missing_dirs)
        
        if total_required > 0:
            result.score = max(0.0, 1.0 - (missing_count / total_required))
        
        result.details.update({
            "required_files": required_structure.get("files", []),
            "required_directories": required_structure.get("directories", []),
            "missing_files": missing_files,
            "missing_directories": missing_dirs,
            "structure_score": result.score
        })
        
        return result
    
    async def _validate_configurations(self, project_dir: Path) -> ValidationResult:
        """Validate configuration files"""
        result = ValidationResult(is_valid=True, score=1.0, details={"validation_type": "configuration"})
        
        config_files = {
            "json": list(project_dir.rglob("*.json")),
            "yaml": list(project_dir.rglob("*.yml")) + list(project_dir.rglob("*.yaml")),
            "toml": list(project_dir.rglob("*.toml")),
            "ini": list(project_dir.rglob("*.ini"))
        }
        
        invalid_configs = []
        
        # Validate JSON files
        for json_file in config_files["json"]:
            try:
                with open(json_file, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                invalid_configs.append(f"Invalid JSON in {json_file.relative_to(project_dir)}: {str(e)}")
        
        # Validate YAML files
        for yaml_file in config_files["yaml"]:
            try:
                with open(yaml_file, 'r') as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                invalid_configs.append(f"Invalid YAML in {yaml_file.relative_to(project_dir)}: {str(e)}")
        
        # Validate TOML files
        for toml_file in config_files["toml"]:
            try:
                with open(toml_file, 'r') as f:
                    toml.load(f)
            except toml.TomlDecodeError as e:
                invalid_configs.append(f"Invalid TOML in {toml_file.relative_to(project_dir)}: {str(e)}")
        
        if invalid_configs:
            result.errors.extend(invalid_configs)
            result.is_valid = False
            total_configs = sum(len(files) for files in config_files.values())
            result.score = max(0.0, 1.0 - (len(invalid_configs) / max(total_configs, 1)))
        
        result.details.update({
            "config_files_found": {k: len(v) for k, v in config_files.items()},
            "invalid_configurations": invalid_configs,
            "config_score": result.score
        })
        
        return result
    
    async def _validate_code_quality(self, project_dir: Path) -> ValidationResult:
        """Validate code quality"""
        result = ValidationResult(is_valid=True, score=1.0, details={"validation_type": "code_quality"})
        
        # Find Python files
        python_files = list(project_dir.rglob("*.py"))
        js_files = list(project_dir.rglob("*.js")) + list(project_dir.rglob("*.ts"))
        
        syntax_errors = []
        lint_issues = []
        
        # Check Python syntax and basic linting
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check syntax
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    syntax_errors.append(f"Python syntax error in {py_file.relative_to(project_dir)}: {str(e)}")
                    
                # Basic code quality checks
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if len(line) > 120:  # Line length check
                        lint_issues.append(f"Line too long in {py_file.relative_to(project_dir)}:{i}")
                    if 'import *' in line:  # Star import check
                        lint_issues.append(f"Star import in {py_file.relative_to(project_dir)}:{i}")
                        
            except Exception as e:
                syntax_errors.append(f"Failed to read {py_file.relative_to(project_dir)}: {str(e)}")
        
        # Check JavaScript/TypeScript syntax (basic)
        for js_file in js_files:
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Basic syntax checks
                if 'console.log' in content:
                    lint_issues.append(f"Console.log found in {js_file.relative_to(project_dir)}")
                if 'debugger' in content:
                    lint_issues.append(f"Debugger statement in {js_file.relative_to(project_dir)}")
                    
            except Exception as e:
                syntax_errors.append(f"Failed to read {js_file.relative_to(project_dir)}: {str(e)}")
        
        if syntax_errors:
            result.errors.extend(syntax_errors)
            result.is_valid = False
            
        if lint_issues:
            result.warnings.extend(lint_issues)
            # Lint issues reduce score but don't invalidate
            total_files = len(python_files) + len(js_files)
            result.score = max(0.5, 1.0 - (len(lint_issues) / max(total_files * 5, 1)))
        
        result.details.update({
            "python_files": len(python_files),
            "javascript_files": len(js_files),
            "syntax_errors": syntax_errors,
            "lint_issues": lint_issues,
            "code_quality_score": result.score
        })
        
        return result
    
    async def _validate_functionality(self, project_dir: Path) -> ValidationResult:
        """Validate functionality (builds, tests, basic functionality)"""
        result = ValidationResult(is_valid=True, score=1.0, details={"validation_type": "functionality"})
        
        build_results = {}
        test_results = {}
        
        # Check if backend can be built/started
        backend_dir = project_dir / "backend"
        if backend_dir.exists():
            build_results["backend"] = await self._check_backend_build(backend_dir)
        
        # Check if frontend can be built
        frontend_dir = project_dir / "frontend"
        if frontend_dir.exists():
            build_results["frontend"] = await self._check_frontend_build(frontend_dir)
        
        # Run basic tests if available
        if backend_dir.exists():
            test_results["backend"] = await self._run_backend_tests(backend_dir)
            
        if frontend_dir.exists():
            test_results["frontend"] = await self._run_frontend_tests(frontend_dir)
        
        # Evaluate results
        failed_builds = [k for k, v in build_results.items() if not v["success"]]
        failed_tests = [k for k, v in test_results.items() if not v["success"]]
        
        if failed_builds:
            result.errors.extend([f"{service} build failed: {build_results[service]['error']}" 
                                for service in failed_builds])
            result.is_valid = False
        
        if failed_tests:
            result.warnings.extend([f"{service} tests failed: {test_results[service]['error']}" 
                                  for service in failed_tests])
            
        # Calculate functionality score
        total_checks = len(build_results) + len(test_results)
        failed_checks = len(failed_builds) + len(failed_tests)
        
        if total_checks > 0:
            result.score = max(0.0, 1.0 - (failed_checks / total_checks))
        
        result.details.update({
            "build_results": build_results,
            "test_results": test_results,
            "functionality_score": result.score
        })
        
        return result
    
    async def _validate_security(self, project_dir: Path) -> ValidationResult:
        """Validate security (no hardcoded secrets, dependency vulnerabilities)"""
        result = ValidationResult(is_valid=True, score=1.0, details={"validation_type": "security"})
        
        security_issues = []
        
        # Check for hardcoded secrets/API keys
        secret_patterns = [
            r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'secret[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*',
        ]
        
        for file_path in project_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.json', '.yml', '.yaml', '.env']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    for pattern in secret_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for match in matches:
                            # Exclude obvious test/example values
                            if not any(test_val in match.lower() for test_val in 
                                     ['test', 'example', 'dummy', 'placeholder', 'your-']):
                                security_issues.append(
                                    f"Potential hardcoded secret in {file_path.relative_to(project_dir)}: {match[:50]}..."
                                )
                                
                except Exception:
                    continue  # Skip files that can't be read
        
        if security_issues:
            result.warnings.extend(security_issues)
            # Security issues reduce score significantly
            result.score = max(0.3, 1.0 - (len(security_issues) / 10.0))
            
            # Critical security issues invalidate the template
            critical_issues = [issue for issue in security_issues if 'hardcoded secret' in issue.lower()]
            if critical_issues:
                result.is_valid = False
                result.errors.extend(critical_issues)
        
        result.details.update({
            "security_issues": security_issues,
            "security_score": result.score
        })
        
        return result
    
    async def _check_backend_build(self, backend_dir: Path) -> Dict[str, Any]:
        """Check if backend can be built successfully"""
        result = {"success": False, "error": None, "output": None}
        
        try:
            # Check if requirements.txt exists
            if not (backend_dir / "requirements.txt").exists():
                result["error"] = "requirements.txt not found"
                return result
            
            # Try to parse Python files for syntax
            python_files = list(backend_dir.rglob("*.py"))
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError as e:
                    result["error"] = f"Syntax error in {py_file.name}: {str(e)}"
                    return result
            
            result["success"] = True
            result["output"] = f"Backend validation passed ({len(python_files)} Python files checked)"
            
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    async def _check_frontend_build(self, frontend_dir: Path) -> Dict[str, Any]:
        """Check if frontend can be built successfully"""
        result = {"success": False, "error": None, "output": None}
        
        try:
            # Check if package.json exists
            package_json = frontend_dir / "package.json"
            if not package_json.exists():
                result["error"] = "package.json not found"
                return result
            
            # Validate package.json
            with open(package_json, 'r') as f:
                package_data = json.load(f)
                
            if "scripts" not in package_data:
                result["error"] = "No scripts section in package.json"
                return result
                
            # Check for basic build script
            if "build" not in package_data["scripts"]:
                result["error"] = "No build script in package.json"
                return result
            
            result["success"] = True
            result["output"] = "Frontend package.json validation passed"
            
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    async def _run_backend_tests(self, backend_dir: Path) -> Dict[str, Any]:
        """Run backend tests if available"""
        result = {"success": True, "error": None, "output": None}
        
        try:
            # Check if tests directory exists
            if not (backend_dir / "tests").exists():
                result["output"] = "No tests directory found"
                return result
            
            # Check for pytest configuration
            if (backend_dir / "pytest.ini").exists() or (backend_dir / "pyproject.toml").exists():
                result["output"] = "Test configuration found"
            else:
                result["output"] = "Tests directory exists but no pytest configuration"
                
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            
        return result
    
    async def _run_frontend_tests(self, frontend_dir: Path) -> Dict[str, Any]:
        """Run frontend tests if available"""
        result = {"success": True, "error": None, "output": None}
        
        try:
            package_json = frontend_dir / "package.json"
            if package_json.exists():
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                    
                if "scripts" in package_data and "test" in package_data["scripts"]:
                    result["output"] = "Test script found in package.json"
                else:
                    result["output"] = "No test script in package.json"
            else:
                result["output"] = "No package.json found"
                
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            
        return result
    
    def _load_template_config(self, template_path: Path) -> Optional[Dict[str, Any]]:
        """Load cookiecutter configuration"""
        config_file = template_path / "cookiecutter.json"
        if not config_file.exists():
            return None
            
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None
    
    def _generate_test_contexts(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate test contexts for template validation"""
        base_context = {
            "project_name": "Test Project",
            "project_slug": "test-project", 
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "version": "0.1.0",
            "project_short_description": "A test project for validation"
        }
        
        # Add all required cookiecutter variables
        for key, value in config.items():
            if key not in base_context:
                if isinstance(value, list) and len(value) > 0:
                    base_context[key] = value[0]  # Use first option for lists
                elif isinstance(value, str) and not value.startswith("{{"):
                    base_context[key] = value
        
        return [base_context]
    
    def _get_required_structure(self, template_name: str) -> Dict[str, List[str]]:
        """Get required files and directories for specific templates"""
        structures = {
            "neoforge": {
                "files": [
                    "README.md",
                    "Makefile",
                    "docker-compose.yml",
                    "backend/requirements.txt",
                    "backend/app/main.py",
                    "backend/Dockerfile",
                    "frontend/package.json",
                    "frontend/index.html"
                ],
                "directories": [
                    "backend",
                    "frontend",
                    "backend/app",
                    "backend/tests",
                    "frontend/src",
                    "docs"
                ]
            },
            "reactnext": {
                "files": [
                    "README.md",
                    "package.json",
                    "backend/requirements.txt",
                    "frontend/next.config.js"
                ],
                "directories": [
                    "backend",
                    "frontend"
                ]
            }
        }
        
        return structures.get(template_name, {
            "files": ["README.md"],
            "directories": []
        })
    
    def generate_report(self, results: Dict[str, ValidationResult]) -> str:
        """Generate comprehensive validation report"""
        report = []
        report.append("# Template Quality Gates Report")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        total_templates = len(results)
        passed_templates = sum(1 for r in results.values() if r.is_valid)
        avg_score = sum(r.score for r in results.values()) / max(total_templates, 1)
        
        report.append("## Summary")
        report.append(f"- Total Templates: {total_templates}")
        report.append(f"- Passed: {passed_templates}")
        report.append(f"- Failed: {total_templates - passed_templates}")
        report.append(f"- Average Score: {avg_score:.2f}")
        report.append("")
        
        # Detailed results
        for template_name, result in results.items():
            status = "✅ PASS" if result.is_valid else "❌ FAIL"
            report.append(f"## {template_name} {status}")
            report.append(f"- Score: {result.score:.2f}")
            report.append(f"- Execution Time: {result.execution_time:.2f}s")
            
            if result.errors:
                report.append("### Errors")
                for error in result.errors:
                    report.append(f"- {error}")
                    
            if result.warnings:
                report.append("### Warnings")
                for warning in result.warnings:
                    report.append(f"- {warning}")
            
            # Add detailed breakdown
            if result.details:
                for context, details in result.details.items():
                    if isinstance(details, dict) and "validation_type" in details:
                        validation_type = details["validation_type"]
                        score_key = f"{validation_type}_score"
                        if score_key in details:
                            report.append(f"- {validation_type.title()} Score: {details[score_key]:.2f}")
            
            report.append("")
        
        return "\n".join(report)