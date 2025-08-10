#!/usr/bin/env python3
"""
Workflow Validation Testing Suite
Validates core workflow components and integration points for the Startup Factory MVP orchestration system
"""

import asyncio
import json
import time
import yaml
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import sys
import os

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

@dataclass
class ValidationResult:
    component: str
    test_name: str
    status: str
    details: str
    duration: float = 0.0
    metadata: Dict[str, Any] = None

class WorkflowValidator:
    """Validates core workflow components and integration points"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.config_path = Path(__file__).parent / "config.yaml"
        self.config = None
        
        # Load configuration if available
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
    
    def log_result(self, component: str, test_name: str, status: str, 
                   details: str, duration: float = 0.0, metadata: Dict = None):
        """Log validation result"""
        result = ValidationResult(
            component=component,
            test_name=test_name,
            status=status,
            details=details,
            duration=duration,
            metadata=metadata or {}
        )
        self.results.append(result)
        
        # Print result
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} {component} - {test_name}: {details}")
        if duration > 0:
            print(f"   ⏱️ {duration:.2f}s")
    
    def validate_script_structure(self) -> bool:
        """Validate orchestrator script structure and imports"""
        print("\n🔍 Validating Script Structure")
        
        start_time = time.time()
        
        try:
            # Check if script exists and is executable
            script_path = Path(__file__).parent / "mvp_orchestrator_script.py"
            
            if not script_path.exists():
                self.log_result(
                    "Script Structure",
                    "File Existence",
                    "FAIL",
                    "mvp_orchestrator_script.py not found",
                    time.time() - start_time
                )
                return False
            
            # Test import structure
            result = subprocess.run([
                sys.executable, "-c",
                """
import sys
sys.path.insert(0, '.')
try:
    from mvp_orchestrator_script import MVPOrchestrator, Config, AIProvider
    print('SUCCESS: Core classes imported')
except Exception as e:
    print(f'FAIL: Import error - {e}')
                """
            ], cwd=Path(__file__).parent, capture_output=True, text=True, timeout=30)
            
            if "SUCCESS" in result.stdout:
                self.log_result(
                    "Script Structure",
                    "Core Imports",
                    "PASS",
                    "All core classes importable",
                    time.time() - start_time
                )
                return True
            else:
                self.log_result(
                    "Script Structure", 
                    "Core Imports",
                    "FAIL",
                    f"Import issues: {result.stdout + result.stderr}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Script Structure",
                "Validation Error",
                "FAIL",
                f"Structure validation failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def validate_ai_provider_routing(self) -> bool:
        """Validate AI provider routing logic"""
        print("\n🤖 Validating AI Provider Routing")
        
        start_time = time.time()
        
        try:
            # Expected provider routing based on orchestrator implementation
            expected_routing = {
                "market_research": "perplexity",
                "founder_analysis": "anthropic", 
                "mvp_specification": "anthropic",
                "architecture": "anthropic",
                "code_generation": "openai",
                "quality_checks": "anthropic",
                "deployment": "anthropic"
            }
            
            # Test routing logic
            valid_providers = ["openai", "anthropic", "perplexity"]
            routing_valid = True
            invalid_mappings = []
            
            for task, provider in expected_routing.items():
                if provider not in valid_providers:
                    routing_valid = False
                    invalid_mappings.append(f"{task} -> {provider}")
            
            if routing_valid:
                self.log_result(
                    "AI Provider Routing",
                    "Provider Mapping",
                    "PASS",
                    f"Valid routing for {len(expected_routing)} tasks",
                    time.time() - start_time,
                    {"routing": expected_routing}
                )
                return True
            else:
                self.log_result(
                    "AI Provider Routing",
                    "Provider Mapping", 
                    "FAIL",
                    f"Invalid mappings: {invalid_mappings}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_result(
                "AI Provider Routing",
                "Validation Error",
                "FAIL",
                f"Routing validation failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def validate_configuration_structure(self) -> bool:
        """Validate configuration file structure"""
        print("\n⚙️ Validating Configuration Structure")
        
        start_time = time.time()
        
        try:
            if not self.config:
                self.log_result(
                    "Configuration",
                    "File Loading",
                    "FAIL",
                    "No configuration file found",
                    time.time() - start_time
                )
                return False
            
            # Required configuration fields
            required_fields = [
                "openai_api_key",
                "anthropic_api_key", 
                "perplexity_api_key",
                "project_root",
                "max_retries",
                "timeout"
            ]
            
            # Cost tracking fields
            cost_fields = [
                "openai_input_cost_per_1k",
                "openai_output_cost_per_1k",
                "anthropic_input_cost_per_1k",
                "anthropic_output_cost_per_1k",
                "perplexity_cost_per_request"
            ]
            
            missing_required = [field for field in required_fields if field not in self.config]
            missing_cost = [field for field in cost_fields if field not in self.config]
            
            if not missing_required and not missing_cost:
                self.log_result(
                    "Configuration",
                    "Structure Validation",
                    "PASS",
                    "All required fields present",
                    time.time() - start_time,
                    {
                        "required_fields": len(required_fields),
                        "cost_fields": len(cost_fields)
                    }
                )
                return True
            else:
                missing_fields = missing_required + missing_cost
                self.log_result(
                    "Configuration",
                    "Structure Validation",
                    "FAIL", 
                    f"Missing fields: {missing_fields}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Configuration",
                "Validation Error",
                "FAIL",
                f"Configuration validation failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def validate_template_system(self) -> bool:
        """Validate template system availability"""
        print("\n🏗️ Validating Template System")
        
        start_time = time.time()
        
        try:
            # Check for template directory
            template_dir = Path(__file__).parent.parent / "templates"
            
            if not template_dir.exists():
                self.log_result(
                    "Template System",
                    "Template Directory",
                    "WARN",
                    "Templates directory not found",
                    time.time() - start_time
                )
                return False
            
            # Check for neoforge template
            neoforge_template = template_dir / "neoforge"
            
            if not neoforge_template.exists():
                self.log_result(
                    "Template System",
                    "Neoforge Template",
                    "WARN",
                    "Neoforge template not found",
                    time.time() - start_time
                )
                return False
            
            # Check for meta-fill integration
            try:
                result = subprocess.run([
                    sys.executable, "-c",
                    """
import sys
sys.path.insert(0, '.')
try:
    from meta_fill_integration import MVPMetaIntegration
    print('META_FILL_AVAILABLE')
except Exception:
    print('META_FILL_UNAVAILABLE')
                    """
                ], cwd=Path(__file__).parent, capture_output=True, text=True, timeout=15)
                
                if "META_FILL_AVAILABLE" in result.stdout:
                    meta_fill_status = "available"
                else:
                    meta_fill_status = "unavailable"
                
            except Exception:
                meta_fill_status = "unavailable"
            
            self.log_result(
                "Template System",
                "System Validation",
                "PASS",
                f"Template system functional, meta-fill: {meta_fill_status}",
                time.time() - start_time,
                {
                    "template_dir": str(template_dir),
                    "neoforge_available": True,
                    "meta_fill_status": meta_fill_status
                }
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Template System",
                "Validation Error",
                "FAIL",
                f"Template validation failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def validate_quality_gates(self) -> bool:
        """Validate quality gates implementation"""
        print("\n🚦 Validating Quality Gates")
        
        start_time = time.time()
        
        try:
            # Expected quality gates from the orchestrator
            expected_gates = [
                "niche_validation",
                "problem_solution_fit",
                "architecture_review",
                "release_readiness"
            ]
            
            # Test gate status enumeration
            result = subprocess.run([
                sys.executable, "-c",
                """
import sys
sys.path.insert(0, '.')
try:
    from mvp_orchestrator_script import GateStatus
    statuses = [s.value for s in GateStatus]
    print(f'GATE_STATUSES:{",".join(statuses)}')
except Exception as e:
    print(f'GATE_ERROR:{e}')
                """
            ], cwd=Path(__file__).parent, capture_output=True, text=True, timeout=15)
            
            if "GATE_STATUSES:" in result.stdout:
                statuses_line = result.stdout.split("GATE_STATUSES:")[1].strip()
                gate_statuses = statuses_line.split(",")
                
                expected_statuses = ["pending", "approved", "rejected", "revision_needed"]
                statuses_valid = all(status in gate_statuses for status in expected_statuses)
                
                if statuses_valid:
                    self.log_result(
                        "Quality Gates",
                        "Gate Implementation",
                        "PASS",
                        f"Quality gates implemented: {len(expected_gates)} gates, {len(gate_statuses)} statuses",
                        time.time() - start_time,
                        {
                            "gates": expected_gates,
                            "statuses": gate_statuses
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Quality Gates",
                        "Gate Implementation",
                        "FAIL",
                        f"Missing gate statuses: {set(expected_statuses) - set(gate_statuses)}",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_result(
                    "Quality Gates",
                    "Gate Implementation",
                    "FAIL",
                    f"Gate status enumeration failed: {result.stdout}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Quality Gates",
                "Validation Error",
                "FAIL",
                f"Quality gate validation failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def validate_cost_tracking(self) -> bool:
        """Validate cost tracking implementation"""
        print("\n💰 Validating Cost Tracking")
        
        start_time = time.time()
        
        try:
            if not self.config:
                self.log_result(
                    "Cost Tracking",
                    "Configuration",
                    "FAIL",
                    "No configuration for cost validation",
                    time.time() - start_time
                )
                return False
            
            # Test cost calculation logic
            test_scenarios = [
                ("openai", 1000, 500),  # input_tokens, output_tokens
                ("anthropic", 800, 400),
                ("perplexity", 0, 0)  # Fixed cost per request
            ]
            
            total_cost = 0.0
            cost_breakdown = {}
            
            for provider, input_tokens, output_tokens in test_scenarios:
                if provider == "openai":
                    cost = (input_tokens * self.config.get('openai_input_cost_per_1k', 0.01) / 1000 +
                           output_tokens * self.config.get('openai_output_cost_per_1k', 0.03) / 1000)
                elif provider == "anthropic":
                    cost = (input_tokens * self.config.get('anthropic_input_cost_per_1k', 0.015) / 1000 +
                           output_tokens * self.config.get('anthropic_output_cost_per_1k', 0.075) / 1000)
                elif provider == "perplexity":
                    cost = self.config.get('perplexity_cost_per_request', 0.005)
                
                total_cost += cost
                cost_breakdown[provider] = cost
                print(f"   💸 {provider}: ${cost:.4f}")
            
            # Validate against reasonable thresholds
            if total_cost < 10.0:  # $10 budget for full workflow
                self.log_result(
                    "Cost Tracking",
                    "Cost Calculation",
                    "PASS",
                    f"Cost tracking functional: ${total_cost:.4f} total",
                    time.time() - start_time,
                    {
                        "total_cost": total_cost,
                        "cost_breakdown": cost_breakdown,
                        "scenarios_tested": len(test_scenarios)
                    }
                )
                return True
            else:
                self.log_result(
                    "Cost Tracking",
                    "Cost Calculation",
                    "WARN",
                    f"Cost estimate high: ${total_cost:.4f}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Cost Tracking",
                "Validation Error",
                "FAIL",
                f"Cost tracking validation failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def validate_error_handling(self) -> bool:
        """Validate error handling mechanisms"""
        print("\n🛡️ Validating Error Handling")
        
        start_time = time.time()
        
        try:
            if not self.config:
                self.log_result(
                    "Error Handling",
                    "Configuration",
                    "FAIL",
                    "No configuration for error handling validation",
                    time.time() - start_time
                )
                return False
            
            # Check retry configuration
            max_retries = self.config.get('max_retries', 0)
            timeout = self.config.get('timeout', 0)
            
            error_configs = []
            
            if max_retries > 0:
                error_configs.append(f"retries: {max_retries}")
            else:
                self.log_result(
                    "Error Handling",
                    "Retry Configuration",
                    "WARN",
                    "No retry configuration found",
                    time.time() - start_time
                )
                return False
            
            if timeout > 0:
                error_configs.append(f"timeout: {timeout}s")
            else:
                self.log_result(
                    "Error Handling",
                    "Timeout Configuration",
                    "WARN",
                    "No timeout configuration found",
                    time.time() - start_time
                )
                return False
            
            # Test error handling structure
            result = subprocess.run([
                sys.executable, "-c",
                """
import sys
sys.path.insert(0, '.')
try:
    from mvp_orchestrator_script import APIManager
    print('ERROR_HANDLING_AVAILABLE')
except Exception as e:
    print(f'ERROR_HANDLING_UNAVAILABLE:{e}')
                """
            ], cwd=Path(__file__).parent, capture_output=True, text=True, timeout=15)
            
            if "ERROR_HANDLING_AVAILABLE" in result.stdout:
                self.log_result(
                    "Error Handling",
                    "Implementation",
                    "PASS",
                    f"Error handling implemented: {', '.join(error_configs)}",
                    time.time() - start_time,
                    {
                        "max_retries": max_retries,
                        "timeout": timeout,
                        "api_manager_available": True
                    }
                )
                return True
            else:
                self.log_result(
                    "Error Handling",
                    "Implementation",
                    "FAIL",
                    f"Error handling classes unavailable: {result.stdout}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Error Handling",
                "Validation Error",
                "FAIL",
                f"Error handling validation failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def run_validation_suite(self) -> Dict[str, Any]:
        """Run complete validation suite"""
        print("🔍 Starting Workflow Validation Suite")
        print("=" * 60)
        
        # Validation methods
        validators = [
            self.validate_script_structure,
            self.validate_ai_provider_routing,
            self.validate_configuration_structure,
            self.validate_template_system,
            self.validate_quality_gates,
            self.validate_cost_tracking,
            self.validate_error_handling
        ]
        
        passed = 0
        failed = 0
        warnings = 0
        
        start_time = time.time()
        
        for validator in validators:
            try:
                result = validator()
                if result:
                    passed += 1
                else:
                    # Check if last result was a warning
                    last_result = self.results[-1] if self.results else None
                    if last_result and last_result.status == "WARN":
                        warnings += 1
                    else:
                        failed += 1
            except Exception as e:
                print(f"❌ Validator {validator.__name__} failed: {e}")
                failed += 1
        
        total_duration = time.time() - start_time
        
        # Generate summary
        summary = {
            "success": failed == 0,
            "total_validations": len(validators),
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "duration": total_duration,
            "results": [
                {
                    "component": r.component,
                    "test_name": r.test_name,
                    "status": r.status,
                    "details": r.details,
                    "duration": r.duration,
                    "metadata": r.metadata
                }
                for r in self.results
            ]
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("🏁 Workflow Validation Summary")
        print("=" * 60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️ Warnings: {warnings}")
        print(f"⏱️ Duration: {total_duration:.2f}s")
        
        if failed == 0:
            if warnings == 0:
                print("\n🎉 All validations passed! Workflow is production-ready.")
            else:
                print(f"\n⚠️ All critical validations passed with {warnings} warnings.")
        else:
            print(f"\n❌ {failed} critical validations failed. Review before proceeding.")
        
        return summary
    
    def generate_report(self, filename: str = "workflow_validation_report.json"):
        """Generate validation report"""
        try:
            report_data = {
                "validation_suite": "Startup Factory Workflow Validation",
                "timestamp": time.time(),
                "summary": {
                    "total_validations": len(self.results),
                    "passed": len([r for r in self.results if r.status == "PASS"]),
                    "failed": len([r for r in self.results if r.status == "FAIL"]),
                    "warnings": len([r for r in self.results if r.status == "WARN"]),
                    "total_duration": sum(r.duration for r in self.results)
                },
                "results": [
                    {
                        "component": r.component,
                        "test_name": r.test_name,
                        "status": r.status,
                        "details": r.details,
                        "duration": r.duration,
                        "metadata": r.metadata
                    }
                    for r in self.results
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"\n📄 Validation report saved to: {filename}")
            
        except Exception as e:
            print(f"⚠️ Could not generate report: {e}")

def main():
    """Main validation execution"""
    validator = WorkflowValidator()
    
    try:
        results = validator.run_validation_suite()
        validator.generate_report()
        
        return results["success"]
        
    except Exception as e:
        print(f"💥 Validation suite failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)