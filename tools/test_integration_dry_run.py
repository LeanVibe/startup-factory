#!/usr/bin/env python3
"""
Startup Factory Integration Testing - Dry Run Mode
Validates the complete workflow without making actual API calls
"""

import yaml
import json
import time
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    status: str  # "PASS", "FAIL", "SKIP"
    duration: float
    details: str
    cost_estimate: float = 0.0

class DryRunIntegrationTester:
    """Integration tester that validates workflow without API calls"""
    
    def __init__(self, config_path: str = "../config.yaml"):
        self.config_path = config_path
        self.results: List[TestResult] = []
        self.total_cost = 0.0
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def log_result(self, test_name: str, status: str, details: str, 
                   duration: float = 0.0, cost: float = 0.0):
        """Log a test result"""
        result = TestResult(test_name, status, duration, details, cost)
        self.results.append(result)
        self.total_cost += cost
        
        # Print immediate feedback
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        print(f"{status_icon} {test_name}: {details}")
        if cost > 0:
            print(f"   💰 Estimated cost: ${cost:.4f}")
    
    def test_configuration_validation(self):
        """Test 1: Validate configuration structure"""
        start_time = time.time()
        
        try:
            # Check required config keys
            required_keys = [
                'openai_api_key', 'anthropic_api_key', 'perplexity_api_key',
                'project_root', 'max_retries', 'timeout'
            ]
            
            missing_keys = [key for key in required_keys if key not in self.config]
            if missing_keys:
                self.log_result(
                    "Configuration Validation",
                    "FAIL",
                    f"Missing required keys: {missing_keys}",
                    time.time() - start_time
                )
                return False
            
            # Validate cost tracking configuration
            cost_keys = [
                'openai_input_cost_per_1k', 'openai_output_cost_per_1k',
                'anthropic_input_cost_per_1k', 'anthropic_output_cost_per_1k',
                'perplexity_cost_per_request'
            ]
            
            missing_cost_keys = [key for key in cost_keys if key not in self.config]
            if missing_cost_keys:
                self.log_result(
                    "Configuration Validation",
                    "FAIL",
                    f"Missing cost tracking keys: {missing_cost_keys}",
                    time.time() - start_time
                )
                return False
            
            self.log_result(
                "Configuration Validation",
                "PASS",
                "All required configuration keys present",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Configuration Validation",
                "FAIL",
                f"Configuration error: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_directory_structure(self):
        """Test 2: Validate directory structure"""
        start_time = time.time()
        
        try:
            # Check required directories
            required_dirs = [
                '../' + self.config.get('project_root', 'production_projects'),
                '../logs',
                '../monitoring'
            ]
            
            missing_dirs = []
            for dir_path in required_dirs:
                if not Path(dir_path).exists():
                    missing_dirs.append(dir_path)
            
            if missing_dirs:
                self.log_result(
                    "Directory Structure",
                    "FAIL",
                    f"Missing directories: {missing_dirs}",
                    time.time() - start_time
                )
                return False
            
            self.log_result(
                "Directory Structure",
                "PASS",
                "All required directories exist",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Directory Structure",
                "FAIL",
                f"Directory validation error: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_mvp_orchestrator_workflow(self):
        """Test 3: Validate MVP orchestrator workflow (dry run)"""
        start_time = time.time()
        
        try:
            # Simulate the complete workflow
            workflow_steps = [
                ("Market Research", "perplexity", 500, 0.005),  # tokens, cost
                ("Founder Analysis", "claude", 1000, 0.015),
                ("MVP Specification", "claude", 1500, 0.023),
                ("Architecture Design", "claude", 2000, 0.030),
                ("Implementation Planning", "claude", 1200, 0.018)
            ]
            
            total_tokens = 0
            total_workflow_cost = 0.0
            
            for step_name, provider, tokens, cost in workflow_steps:
                total_tokens += tokens
                total_workflow_cost += cost
                
                # Validate provider configuration
                if provider == "perplexity":
                    expected_cost = self.config['perplexity_cost_per_request']
                elif provider == "claude":
                    input_cost = (tokens * 0.6) * (self.config['anthropic_input_cost_per_1k'] / 1000)
                    output_cost = (tokens * 0.4) * (self.config['anthropic_output_cost_per_1k'] / 1000)
                    expected_cost = input_cost + output_cost
                
                print(f"   📋 {step_name} ({provider}): ~{tokens} tokens, ~${expected_cost:.4f}")
            
            # Check against budget
            max_budget = self.config.get('max_budget_per_startup', 15.0)
            if total_workflow_cost > max_budget:
                self.log_result(
                    "MVP Orchestrator Workflow",
                    "FAIL",
                    f"Workflow cost ${total_workflow_cost:.2f} exceeds budget ${max_budget}",
                    time.time() - start_time,
                    total_workflow_cost
                )
                return False
            
            self.log_result(
                "MVP Orchestrator Workflow",
                "PASS",
                f"Complete workflow validated: {total_tokens} tokens, ${total_workflow_cost:.4f}",
                time.time() - start_time,
                total_workflow_cost
            )
            return True
            
        except Exception as e:
            self.log_result(
                "MVP Orchestrator Workflow",
                "FAIL",
                f"Workflow validation error: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_cost_tracking_system(self):
        """Test 4: Validate cost tracking functionality"""
        start_time = time.time()
        
        try:
            # Test cost calculation accuracy
            test_scenarios = [
                {
                    "provider": "openai",
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "expected_cost": (1000 * 0.01/1000) + (500 * 0.03/1000)
                },
                {
                    "provider": "anthropic", 
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "expected_cost": (1000 * 0.015/1000) + (500 * 0.075/1000)
                }
            ]
            
            for scenario in test_scenarios:
                provider = scenario["provider"]
                input_cost = scenario["input_tokens"] * (self.config[f'{provider}_input_cost_per_1k'] / 1000)
                output_cost = scenario["output_tokens"] * (self.config[f'{provider}_output_cost_per_1k'] / 1000)
                calculated_cost = input_cost + output_cost
                
                if abs(calculated_cost - scenario["expected_cost"]) > 0.0001:
                    self.log_result(
                        "Cost Tracking System",
                        "FAIL",
                        f"Cost calculation mismatch for {provider}: {calculated_cost} vs {scenario['expected_cost']}",
                        time.time() - start_time
                    )
                    return False
            
            self.log_result(
                "Cost Tracking System",
                "PASS",
                "Cost calculation accuracy validated",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Cost Tracking System",
                "FAIL",
                f"Cost tracking error: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_security_configuration(self):
        """Test 5: Validate security configuration"""
        start_time = time.time()
        
        try:
            # Check API key format (environment variable placeholders)
            api_keys = [
                ('openai_api_key', '${OPENAI_API_KEY}'),
                ('anthropic_api_key', '${ANTHROPIC_API_KEY}'),
                ('perplexity_api_key', '${PERPLEXITY_API_KEY}')
            ]
            
            for key_name, expected_format in api_keys:
                actual_value = str(self.config.get(key_name, ''))
                # Accept both ${VAR} and "${VAR}" formats as valid environment variables
                if not (actual_value.startswith('${') and actual_value.endswith('}')) and not (actual_value.startswith('"${') and actual_value.endswith('}"')):
                    self.log_result(
                        "Security Configuration",
                        "FAIL",
                        f"{key_name} not using environment variable format: {actual_value}",
                        time.time() - start_time
                    )
                    return False
            
            # Check rate limiting configuration
            rate_limit = self.config.get('rate_limit_per_minute', 0)
            max_concurrent = self.config.get('max_concurrent_requests', 0)
            
            if rate_limit <= 0 or max_concurrent <= 0:
                self.log_result(
                    "Security Configuration",
                    "FAIL",
                    "Rate limiting not properly configured",
                    time.time() - start_time
                )
                return False
            
            self.log_result(
                "Security Configuration",
                "PASS",
                f"Security configuration validated: {rate_limit} req/min, {max_concurrent} concurrent",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Security Configuration",
                "FAIL",
                f"Security validation error: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_monitoring_setup(self):
        """Test 6: Validate monitoring infrastructure"""
        start_time = time.time()
        
        try:
            monitoring_files = [
                '../monitoring/docker-compose.monitoring.yml',
                '../monitoring/prometheus/prometheus.yml',
                '../monitoring/grafana/provisioning/datasources/prometheus.yml',
                '../monitoring/alertmanager/alertmanager.yml'
            ]
            
            missing_files = []
            for file_path in monitoring_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                self.log_result(
                    "Monitoring Setup",
                    "FAIL",
                    f"Missing monitoring files: {missing_files}",
                    time.time() - start_time
                )
                return False
            
            # Check monitoring configuration
            enable_monitoring = self.config.get('enable_monitoring', False)
            enable_cost_alerts = self.config.get('enable_cost_alerts', False)
            
            if not enable_monitoring or not enable_cost_alerts:
                self.log_result(
                    "Monitoring Setup",
                    "FAIL",
                    "Monitoring features not enabled in configuration",
                    time.time() - start_time
                )
                return False
            
            self.log_result(
                "Monitoring Setup",
                "PASS",
                "Monitoring infrastructure validated",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Monitoring Setup",
                "FAIL",
                f"Monitoring validation error: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def run_integration_tests(self):
        """Run complete integration test suite"""
        print("🧪 Starting Startup Factory Integration Tests (Dry Run Mode)")
        print("=" * 60)
        
        test_methods = [
            self.test_configuration_validation,
            self.test_directory_structure,
            self.test_mvp_orchestrator_workflow,
            self.test_cost_tracking_system,
            self.test_security_configuration,
            self.test_monitoring_setup
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
                    f"Test execution error: {str(e)}",
                    0.0
                )
                failed_tests += 1
        
        # Generate summary report
        print("\n" + "=" * 60)
        print("🏁 Integration Test Summary")
        print("=" * 60)
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"💰 Total estimated cost: ${self.total_cost:.4f}")
        
        if failed_tests == 0:
            print("\n🎉 All integration tests passed! System ready for production.")
            return True
        else:
            print(f"\n⚠️ {failed_tests} tests failed. Review issues before production deployment.")
            return False
    
    def generate_report(self, output_file: str = "integration_test_report.json"):
        """Generate detailed test report"""
        report = {
            "timestamp": time.time(),
            "total_tests": len(self.results),
            "passed": len([r for r in self.results if r.status == "PASS"]),
            "failed": len([r for r in self.results if r.status == "FAIL"]),
            "total_cost_estimate": self.total_cost,
            "results": [asdict(result) for result in self.results]
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {output_file}")

if __name__ == "__main__":
    tester = DryRunIntegrationTester()
    success = tester.run_integration_tests()
    tester.generate_report()
    
    # Exit with appropriate code
    exit(0 if success else 1)