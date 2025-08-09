#!/usr/bin/env python3
"""
Quick System Health Check

A lightweight validation script that checks system components without heavy dependencies.
This provides immediate feedback on system architecture and readiness.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def check_file_exists(path: Path, description: str) -> Tuple[bool, str]:
    """Check if a file exists and return status"""
    if path.exists():
        return True, f"✅ {description}: Found"
    else:
        return False, f"❌ {description}: Missing at {path}"

def check_python_imports() -> List[Tuple[bool, str]]:
    """Check if critical Python modules can be imported"""
    results = []
    
    # Add tools directory to path
    tools_path = Path(__file__).parent
    sys.path.insert(0, str(tools_path))
    
    critical_modules = [
        ("mvp_orchestrator_script", "MVP Orchestrator"),
        ("ai_providers", "AI Providers"),
        ("budget_monitor", "Budget Monitor"),
        ("core_types", "Core Types")
    ]
    
    for module_name, description in critical_modules:
        try:
            __import__(module_name)
            results.append((True, f"✅ {description}: Importable"))
        except ImportError as e:
            results.append((False, f"❌ {description}: Import failed - {str(e)}"))
        except Exception as e:
            results.append((False, f"⚠️  {description}: Import error - {str(e)}"))
    
    return results

def check_template_system() -> List[Tuple[bool, str]]:
    """Check template system integrity"""
    results = []
    project_root = Path(__file__).parent.parent
    
    # Check template directory
    template_dir = project_root / "templates" / "neoforge"
    results.append(check_file_exists(template_dir, "NeoForge Template Directory"))
    
    # Check cookiecutter config
    cookiecutter_file = template_dir / "cookiecutter.json"
    file_exists, message = check_file_exists(cookiecutter_file, "Cookiecutter Config")
    results.append((file_exists, message))
    
    if file_exists:
        try:
            with open(cookiecutter_file) as f:
                config = json.load(f)
            
            required_vars = ["project_name", "project_slug", "author_name"]
            missing_vars = [var for var in required_vars if var not in config]
            
            if missing_vars:
                results.append((False, f"⚠️  Cookiecutter Config: Missing variables {missing_vars}"))
            else:
                results.append((True, "✅ Cookiecutter Config: All required variables present"))
        except json.JSONDecodeError:
            results.append((False, "❌ Cookiecutter Config: Invalid JSON"))
        except Exception as e:
            results.append((False, f"⚠️  Cookiecutter Config: Error reading - {str(e)}"))
    
    # Check template project structure
    template_project = template_dir / "{{cookiecutter.project_slug}}"
    results.append(check_file_exists(template_project, "Template Project Structure"))
    
    if template_project.exists():
        # Check key template files
        key_files = [
            template_project / "backend" / "Makefile",
            template_project / "frontend" / "package.json",
            template_project / "Makefile"
        ]
        
        for key_file in key_files:
            results.append(check_file_exists(key_file, f"Template {key_file.name}"))
    
    return results

def check_configuration() -> List[Tuple[bool, str]]:
    """Check system configuration"""
    results = []
    project_root = Path(__file__).parent.parent
    
    # Check main config file
    config_file = project_root / "tools" / "config.yaml"
    file_exists, message = check_file_exists(config_file, "Main Config File")
    results.append((file_exists, message))
    
    # Check config template
    config_template = project_root / "tools" / "config.template.yaml"
    results.append(check_file_exists(config_template, "Config Template"))
    
    return results

def check_test_structure() -> List[Tuple[bool, str]]:
    """Check test structure we just created"""
    results = []
    project_root = Path(__file__).parent.parent
    
    test_dirs = [
        "tests/architecture",
        "tests/components", 
        "tests/contracts",
        "tests/integration"
    ]
    
    for test_dir in test_dirs:
        test_path = project_root / test_dir
        results.append(check_file_exists(test_path, f"Test Directory: {test_dir}"))
    
    # Check specific test files we created
    test_files = [
        "tests/architecture/component_contracts.py",
        "tests/components/test_mvp_orchestrator_isolated.py",
        "tests/contracts/test_ai_provider_contracts.py",
        "tests/integration/test_critical_user_journeys.py"
    ]
    
    for test_file in test_files:
        test_path = project_root / test_file
        results.append(check_file_exists(test_path, f"Test File: {test_file.split('/')[-1]}"))
    
    return results

def check_documentation_consistency() -> List[Tuple[bool, str]]:
    """Check documentation consistency"""
    results = []
    project_root = Path(__file__).parent.parent
    
    # Check key documentation files
    doc_files = [
        ("docs/PLAN.md", "Development Plan"),
        ("docs/TODO.md", "TODO List"),
        ("CLAUDE.md", "Claude Instructions"),
        ("README.md", "README")
    ]
    
    for doc_file, description in doc_files:
        doc_path = project_root / doc_file
        results.append(check_file_exists(doc_path, description))
    
    # Check for consistency issues we identified
    plan_file = project_root / "docs" / "PLAN.md"
    todo_file = project_root / "docs" / "TODO.md"
    
    try:
        if plan_file.exists() and todo_file.exists():
            with open(plan_file) as f:
                plan_content = f.read()
            with open(todo_file) as f:
                todo_content = f.read()
            
            # Check for status inconsistencies
            if ("PRODUCTION READY" in plan_content and "85% Ready" in todo_content) or ("NEARING PRODUCTION READY" in plan_content and "85% Ready" in todo_content):
                # Check if both are now aligned at 85%
                if "85%" in plan_content and "85%" in todo_content:
                    results.append((True, "✅ Documentation Status: PLAN.md and TODO.md both show 85% status"))
                else:
                    results.append((False, "❌ Documentation Inconsistency: Status mismatch between PLAN.md and TODO.md"))
            else:
                results.append((True, "✅ Documentation Status: No obvious inconsistencies detected"))
    except Exception as e:
        results.append((False, f"⚠️  Documentation Check: Error reading files - {str(e)}"))
    
    return results

def print_section(title: str, results: List[Tuple[bool, str]]) -> Tuple[int, int]:
    """Print a section of results and return (passed, total) counts"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print('='*60)
    
    passed = 0
    total = len(results)
    
    for success, message in results:
        print(f"  {message}")
        if success:
            passed += 1
    
    print(f"\n📊 {title}: {passed}/{total} checks passed")
    return passed, total

def main():
    """Run quick system health check"""
    print("🚀 Startup Factory - Quick System Health Check")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # Run all checks
    checks = [
        ("Configuration Files", check_configuration()),
        ("Python Module Imports", check_python_imports()),
        ("Template System", check_template_system()),
        ("Test Structure", check_test_structure()),
        ("Documentation", check_documentation_consistency())
    ]
    
    total_passed = 0
    total_checks = 0
    
    for section_name, results in checks:
        passed, total = print_section(section_name, results)
        total_passed += passed
        total_checks += total
    
    # Summary
    execution_time = time.time() - start_time
    success_rate = (total_passed / total_checks) * 100 if total_checks > 0 else 0
    
    print(f"\n{'='*60}")
    print("🏁 SYSTEM HEALTH SUMMARY")
    print('='*60)
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_checks - total_passed}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    print(f"⏱️  Execution Time: {execution_time:.2f} seconds")
    
    # Overall status
    if success_rate >= 90:
        status = "🎉 EXCELLENT - System is healthy!"
        exit_code = 0
    elif success_rate >= 75:
        status = "✅ GOOD - Minor issues detected"
        exit_code = 0
    elif success_rate >= 50:
        status = "⚠️  WARNING - Several issues need attention"
        exit_code = 1
    else:
        status = "❌ CRITICAL - Major issues detected"
        exit_code = 2
    
    print(f"\n{status}")
    
    if success_rate < 100:
        print("\n🔧 NEXT STEPS:")
        print("1. Address failed checks above")
        print("2. Run full validation: uv run tools/system_validation.py")
        print("3. Check individual test suites")
    
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)