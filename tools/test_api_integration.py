#!/usr/bin/env python3
"""
API Integration Validation Script
Tests API connectivity and configuration without making expensive calls
"""

import os
import yaml
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Mock API response classes for validation
@dataclass
class MockAPIResponse:
    status: str
    provider: str
    response_time: float
    cost_estimate: float
    details: str

class APIIntegrationTester:
    """Test API integration and configuration"""
    
    def __init__(self, config_path: str = "../config.yaml"):
        self.config_path = config_path
        self.results = []
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def log_result(self, test_name: str, status: str, details: str, cost: float = 0.0):
        """Log test result"""
        result = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "cost_estimate": cost,
            "timestamp": time.time()
        }
        self.results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {details}")
        if cost > 0:
            print(f"   💰 Cost estimate: ${cost:.4f}")
    
    def test_openai_config(self):
        """Test OpenAI API configuration"""
        try:
            api_key = self.config.get('openai_api_key', '')
            
            # Check if environment variable format
            if not api_key.startswith('${') or not api_key.endswith('}'):
                self.log_result(
                    "OpenAI Configuration",
                    "FAIL",
                    f"API key not in environment variable format: {api_key}"
                )
                return False
            
            # Check cost configuration
            input_cost = self.config.get('openai_input_cost_per_1k', 0)
            output_cost = self.config.get('openai_output_cost_per_1k', 0)
            
            if input_cost <= 0 or output_cost <= 0:
                self.log_result(
                    "OpenAI Configuration",
                    "FAIL",
                    "Cost tracking not properly configured"
                )
                return False
            
            # Simulate API call cost calculation
            test_tokens = 1000
            estimated_cost = (test_tokens * 0.6 * input_cost / 1000) + (test_tokens * 0.4 * output_cost / 1000)
            
            self.log_result(
                "OpenAI Configuration",
                "PASS",
                f"Configuration valid. Test call would cost ~${estimated_cost:.4f}",
                estimated_cost
            )
            return True
            
        except Exception as e:
            self.log_result(
                "OpenAI Configuration",
                "FAIL",
                f"Configuration error: {str(e)}"
            )
            return False
    
    def test_anthropic_config(self):
        """Test Anthropic API configuration"""
        try:
            api_key = self.config.get('anthropic_api_key', '')
            
            # Check if environment variable format
            if not api_key.startswith('${') or not api_key.endswith('}'):
                self.log_result(
                    "Anthropic Configuration",
                    "FAIL",
                    f"API key not in environment variable format: {api_key}"
                )
                return False
            
            # Check cost configuration
            input_cost = self.config.get('anthropic_input_cost_per_1k', 0)
            output_cost = self.config.get('anthropic_output_cost_per_1k', 0)
            
            if input_cost <= 0 or output_cost <= 0:
                self.log_result(
                    "Anthropic Configuration",
                    "FAIL",
                    "Cost tracking not properly configured"
                )
                return False
            
            # Simulate API call cost calculation
            test_tokens = 1000
            estimated_cost = (test_tokens * 0.6 * input_cost / 1000) + (test_tokens * 0.4 * output_cost / 1000)
            
            self.log_result(
                "Anthropic Configuration",
                "PASS",
                f"Configuration valid. Test call would cost ~${estimated_cost:.4f}",
                estimated_cost
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Anthropic Configuration",
                "FAIL",
                f"Configuration error: {str(e)}"
            )
            return False
    
    def test_perplexity_config(self):
        """Test Perplexity API configuration"""
        try:
            api_key = self.config.get('perplexity_api_key', '')
            
            # Check if environment variable format
            if not api_key.startswith('${') or not api_key.endswith('}'):
                self.log_result(
                    "Perplexity Configuration",
                    "FAIL",
                    f"API key not in environment variable format: {api_key}"
                )
                return False
            
            # Check cost configuration
            cost_per_request = self.config.get('perplexity_cost_per_request', 0)
            
            if cost_per_request <= 0:
                self.log_result(
                    "Perplexity Configuration",
                    "FAIL",
                    "Cost tracking not properly configured"
                )
                return False
            
            # Check if Perplexity app integration is available
            use_app = self.config.get('use_perplexity_app', False)
            app_status = "enabled" if use_app else "disabled"
            
            self.log_result(
                "Perplexity Configuration",
                "PASS",
                f"Configuration valid. App integration: {app_status}. Cost per request: ${cost_per_request}",
                cost_per_request
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Perplexity Configuration",
                "FAIL",
                f"Configuration error: {str(e)}"
            )
            return False
    
    def test_mvp_orchestrator_compatibility(self):
        """Test MVP orchestrator script compatibility"""
        try:
            script_path = Path("mvp-orchestrator-script.py")
            
            if not script_path.exists():
                self.log_result(
                    "MVP Orchestrator Compatibility",
                    "FAIL",
                    "MVP orchestrator script not found"
                )
                return False
            
            # Check if script is executable
            if not os.access(script_path, os.X_OK):
                self.log_result(
                    "MVP Orchestrator Compatibility",
                    "WARN",
                    "Script is not executable (run: chmod +x mvp-orchestrator-script.py)"
                )
            
            # Validate project structure compatibility
            project_root = self.config.get('project_root', './production_projects')
            if not Path('../' + project_root).exists():
                self.log_result(
                    "MVP Orchestrator Compatibility",
                    "FAIL",
                    f"Project root directory does not exist: {project_root}"
                )
                return False
            
            self.log_result(
                "MVP Orchestrator Compatibility",
                "PASS",
                "MVP orchestrator script and project structure compatible"
            )
            return True
            
        except Exception as e:
            self.log_result(
                "MVP Orchestrator Compatibility",
                "FAIL",
                f"Compatibility check error: {str(e)}"
            )
            return False
    
    def test_workflow_cost_estimation(self):
        """Test complete workflow cost estimation"""
        try:
            # Simulate a complete MVP development workflow
            workflow_steps = [
                ("Market Research", "perplexity", 0, 1, self.config.get('perplexity_cost_per_request', 0.005)),
                ("Founder Analysis", "anthropic", 800, 400, None),
                ("MVP Specification", "anthropic", 1200, 600, None),
                ("Architecture Design", "claude", 1500, 750, None),
                ("Code Generation", "openai", 2000, 1000, None),
                ("Testing Strategy", "anthropic", 600, 300, None),
                ("Deployment Config", "claude", 400, 200, None)
            ]
            
            total_cost = 0.0
            workflow_details = []
            
            for step_name, provider, input_tokens, output_tokens, fixed_cost in workflow_steps:
                if fixed_cost:
                    step_cost = fixed_cost
                else:
                    if provider in ["anthropic", "claude"]:
                        input_cost = input_tokens * (self.config.get('anthropic_input_cost_per_1k', 0.015) / 1000)
                        output_cost = output_tokens * (self.config.get('anthropic_output_cost_per_1k', 0.075) / 1000)
                        step_cost = input_cost + output_cost
                    elif provider == "openai":
                        input_cost = input_tokens * (self.config.get('openai_input_cost_per_1k', 0.01) / 1000)
                        output_cost = output_tokens * (self.config.get('openai_output_cost_per_1k', 0.03) / 1000)
                        step_cost = input_cost + output_cost
                    else:
                        step_cost = 0.0
                
                total_cost += step_cost
                workflow_details.append(f"{step_name} ({provider}): ${step_cost:.4f}")
                print(f"   📋 {step_name} ({provider}): ~{input_tokens + output_tokens} tokens, ${step_cost:.4f}")
            
            # Check against budget
            max_budget = self.config.get('max_budget_per_startup', 15.0)
            
            if total_cost > max_budget:
                self.log_result(
                    "Workflow Cost Estimation",
                    "FAIL",
                    f"Total workflow cost ${total_cost:.2f} exceeds budget ${max_budget}",
                    total_cost
                )
                return False
            
            budget_utilization = (total_cost / max_budget) * 100
            
            self.log_result(
                "Workflow Cost Estimation",
                "PASS",
                f"Total cost: ${total_cost:.2f}, Budget utilization: {budget_utilization:.1f}%",
                total_cost
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Workflow Cost Estimation",
                "FAIL",
                f"Cost estimation error: {str(e)}"
            )
            return False
    
    def test_error_handling_config(self):
        """Test error handling and retry configuration"""
        try:
            max_retries = self.config.get('max_retries', 0)
            timeout = self.config.get('timeout', 0)
            
            if max_retries <= 0:
                self.log_result(
                    "Error Handling Configuration",
                    "FAIL",
                    "Max retries not properly configured"
                )
                return False
            
            if timeout <= 0:
                self.log_result(
                    "Error Handling Configuration",
                    "FAIL",
                    "Timeout not properly configured"
                )
                return False
            
            # Validate rate limiting if configured
            rate_limit = self.config.get('rate_limit_per_minute', None)
            max_concurrent = self.config.get('max_concurrent_requests', None)
            
            rate_limit_status = "configured" if rate_limit and rate_limit > 0 else "not configured"
            concurrent_status = "configured" if max_concurrent and max_concurrent > 0 else "not configured"
            
            self.log_result(
                "Error Handling Configuration",
                "PASS",
                f"Retries: {max_retries}, Timeout: {timeout}s, Rate limiting: {rate_limit_status}, Concurrency: {concurrent_status}"
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Error Handling Configuration",
                "FAIL",
                f"Error handling validation error: {str(e)}"
            )
            return False
    
    def run_api_tests(self):
        """Run complete API integration test suite"""
        print("🔌 Starting API Integration Validation")
        print("=" * 60)
        
        test_methods = [
            self.test_openai_config,
            self.test_anthropic_config,
            self.test_perplexity_config,
            self.test_mvp_orchestrator_compatibility,
            self.test_workflow_cost_estimation,
            self.test_error_handling_config
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
                else:
                    failed_tests += 1
            except Exception as e:
                self.log_result(
                    test_method.__name__,
                    "FAIL",
                    f"Test execution error: {str(e)}"
                )
                failed_tests += 1
        
        # Generate summary
        total_cost = sum(result.get('cost_estimate', 0) for result in self.results)
        
        print("\n" + "=" * 60)
        print("🔌 API Integration Test Summary")
        print("=" * 60)
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"💰 Total estimated cost for test workflow: ${total_cost:.4f}")
        
        if failed_tests == 0:
            print("\n🎉 All API integration tests passed! Ready for live testing.")
            return True
        else:
            print(f"\n⚠️ {failed_tests} tests failed. Review configuration before live testing.")
            return False
    
    def generate_report(self, output_file: str = "api_integration_report.json"):
        """Generate detailed API integration report"""
        report = {
            "timestamp": time.time(),
            "total_tests": len(self.results),
            "passed": len([r for r in self.results if r["status"] == "PASS"]),
            "failed": len([r for r in self.results if r["status"] == "FAIL"]),
            "total_cost_estimate": sum(r.get('cost_estimate', 0) for r in self.results),
            "results": self.results
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {output_file}")

if __name__ == "__main__":
    tester = APIIntegrationTester()
    success = tester.run_api_tests()
    tester.generate_report()
    
    # Exit with appropriate code
    exit(0 if success else 1)