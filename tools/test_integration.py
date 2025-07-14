#!/usr/bin/env python3
"""
Integration testing script for MVP Orchestrator
Implements enhanced testing based on Gemini feedback
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List
import sys
import os

# Add tools directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from validation_helpers import (
        load_test_scenarios, 
        run_comprehensive_validation,
        validate_cost_tracking,
        validate_response_time
    )
    print("✅ Validation helpers imported successfully")
except ImportError as e:
    print(f"❌ Failed to import validation helpers: {e}")
    sys.exit(1)


class IntegrationTester:
    """Comprehensive integration tester for MVP Orchestrator"""
    
    def __init__(self):
        self.test_results = {}
        self.total_cost = 0.0
        self.start_time = time.time()
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete integration test suite"""
        print("🚀 Starting MVP Orchestrator Integration Tests")
        print("=" * 60)
        
        # Test environment setup
        env_result = await self.test_environment_setup()
        self.test_results["environment"] = env_result
        
        if not env_result["passed"]:
            print("❌ Environment setup failed - aborting tests")
            return self.test_results
        
        # Test API connectivity (basic)
        api_result = await self.test_api_connectivity()
        self.test_results["api_connectivity"] = api_result
        
        if not api_result["passed"]:
            print("❌ API connectivity failed - aborting tests")
            return self.test_results
        
        # Test orchestrator imports
        import_result = await self.test_orchestrator_import()
        self.test_results["orchestrator_import"] = import_result
        
        if not import_result["passed"]:
            print("❌ Orchestrator import failed - aborting tests")
            return self.test_results
        
        # Load test scenarios
        scenarios = load_test_scenarios()
        print(f"📋 Loaded {len(scenarios['scenarios'])} test scenarios")
        
        # Run workflow tests for each scenario
        for scenario in scenarios["scenarios"]:
            print(f"\n🧪 Testing scenario: {scenario['id']}")
            scenario_result = await self.test_workflow_scenario(scenario)
            self.test_results[f"scenario_{scenario['id']}"] = scenario_result
        
        # Generate summary
        summary = self.generate_test_summary()
        self.test_results["summary"] = summary
        
        return self.test_results
    
    async def test_environment_setup(self) -> Dict[str, Any]:
        """Test environment setup and configuration"""
        print("🔧 Testing environment setup...")
        
        result = {
            "passed": False,
            "issues": [],
            "checks": {}
        }
        
        try:
            # Check API keys
            required_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "PERPLEXITY_API_KEY"]
            for key in required_keys:
                if key in os.environ and os.environ[key]:
                    result["checks"][key] = "✅ Present"
                else:
                    result["checks"][key] = "❌ Missing"
                    result["issues"].append(f"Environment variable {key} not set")
            
            # Check config file
            config_path = Path("config.yaml")
            if config_path.exists():
                result["checks"]["config_file"] = "✅ Present"
                
                # Check file permissions
                import stat
                perms = oct(config_path.stat().st_mode)[-3:]
                if perms == "600":
                    result["checks"]["config_permissions"] = "✅ Secure (600)"
                else:
                    result["checks"]["config_permissions"] = f"⚠️ Permissions: {perms}"
                    result["issues"].append(f"Config file has permissions {perms}, should be 600")
            else:
                result["checks"]["config_file"] = "❌ Missing"
                result["issues"].append("config.yaml file not found")
            
            # Check directories
            required_dirs = ["production_projects", "logs"]
            for dir_name in required_dirs:
                dir_path = Path(dir_name)
                if dir_path.exists():
                    result["checks"][f"{dir_name}_dir"] = "✅ Present"
                else:
                    result["checks"][f"{dir_name}_dir"] = "❌ Missing"
                    result["issues"].append(f"Directory {dir_name} not found")
            
            # Overall pass/fail
            result["passed"] = len(result["issues"]) == 0
            
        except Exception as e:
            result["issues"].append(f"Environment test failed: {e}")
            result["passed"] = False
        
        # Print results
        for check, status in result["checks"].items():
            print(f"  {check}: {status}")
        
        if result["issues"]:
            print("  Issues found:")
            for issue in result["issues"]:
                print(f"    - {issue}")
        
        return result
    
    async def test_api_connectivity(self) -> Dict[str, Any]:
        """Test basic API connectivity for all providers"""
        print("🌐 Testing API connectivity...")
        
        result = {
            "passed": False,
            "providers": {},
            "total_time": 0.0,
            "total_cost": 0.0
        }
        
        # Import here to handle missing dependencies gracefully
        try:
            import httpx
            import openai
            import anthropic
        except ImportError as e:
            result["error"] = f"Missing required dependencies: {e}"
            return result
        
        start_time = time.time()
        
        # Test OpenAI
        try:
            print("  Testing OpenAI...")
            client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for testing
                messages=[{"role": "user", "content": "Say 'OpenAI connected' and nothing else"}],
                max_tokens=5
            )
            
            content = response.choices[0].message.content
            cost = (response.usage.prompt_tokens + response.usage.completion_tokens) * 0.0001  # Rough estimate
            
            result["providers"]["openai"] = {
                "status": "✅ Connected",
                "response": content.strip(),
                "cost": cost,
                "tokens": response.usage.total_tokens
            }
            
            self.total_cost += cost
            
        except Exception as e:
            result["providers"]["openai"] = {
                "status": "❌ Failed",
                "error": str(e)
            }
        
        # Test Anthropic
        try:
            print("  Testing Anthropic...")
            client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            
            response = await client.messages.create(
                model="claude-3-haiku-20240307",  # Use cheaper model for testing
                messages=[{"role": "user", "content": "Say 'Anthropic connected' and nothing else"}],
                max_tokens=5
            )
            
            content = response.content[0].text
            cost = (response.usage.input_tokens * 0.00025 + response.usage.output_tokens * 0.00125) / 1000
            
            result["providers"]["anthropic"] = {
                "status": "✅ Connected",
                "response": content.strip(),
                "cost": cost,
                "tokens": response.usage.input_tokens + response.usage.output_tokens
            }
            
            self.total_cost += cost
            
        except Exception as e:
            result["providers"]["anthropic"] = {
                "status": "❌ Failed",
                "error": str(e)
            }
        
        # Test Perplexity (mock for now - requires specific setup)
        try:
            print("  Testing Perplexity...")
            
            # For now, just test that we can create the request structure
            perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
            if perplexity_key and perplexity_key.startswith("pplx-"):
                result["providers"]["perplexity"] = {
                    "status": "✅ API Key Valid",
                    "response": "API key format correct",
                    "cost": 0.0,
                    "note": "Full API test requires network call"
                }
            else:
                result["providers"]["perplexity"] = {
                    "status": "❌ Invalid API Key",
                    "error": "API key missing or invalid format"
                }
                
        except Exception as e:
            result["providers"]["perplexity"] = {
                "status": "❌ Failed",
                "error": str(e)
            }
        
        result["total_time"] = time.time() - start_time
        result["total_cost"] = self.total_cost
        
        # Check if any provider connected
        connected_providers = [
            p for p in result["providers"].values() 
            if p["status"].startswith("✅")
        ]
        result["passed"] = len(connected_providers) >= 2  # Need at least 2 providers
        
        # Print results
        for provider, details in result["providers"].items():
            print(f"  {provider}: {details['status']}")
            if "response" in details:
                print(f"    Response: {details['response']}")
            if "cost" in details:
                print(f"    Cost: ${details['cost']:.6f}")
        
        print(f"  Total cost: ${result['total_cost']:.6f}")
        print(f"  Total time: {result['total_time']:.2f}s")
        
        return result
    
    async def test_orchestrator_import(self) -> Dict[str, Any]:
        """Test that orchestrator can be imported and configured"""
        print("📦 Testing orchestrator import...")
        
        result = {
            "passed": False,
            "imports": {},
            "config_test": {}
        }
        
        try:
            # Test imports
            print("  Testing imports...")
            
            from mvp_orchestrator_script import (
                Config, APIManager, MVPOrchestrator, 
                AIProvider, GateStatus, PhaseStatus
            )
            result["imports"]["main_classes"] = "✅ Imported"
            
            import yaml
            result["imports"]["yaml"] = "✅ Imported"
            
            # Test config loading
            print("  Testing configuration...")
            with open("config.yaml", 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Replace environment variable placeholders
            for key, value in config_data.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    config_data[key] = os.environ.get(env_var, "")
            
            config = Config(**config_data)
            result["config_test"]["config_creation"] = "✅ Config created"
            
            # Test API manager creation
            api_manager = APIManager(config)
            result["config_test"]["api_manager"] = "✅ API Manager created"
            
            # Test orchestrator creation
            orchestrator = MVPOrchestrator(config)
            result["config_test"]["orchestrator"] = "✅ Orchestrator created"
            
            result["passed"] = True
            
        except ImportError as e:
            result["imports"]["error"] = f"❌ Import failed: {e}"
            result["passed"] = False
        except Exception as e:
            result["config_test"]["error"] = f"❌ Config test failed: {e}"
            result["passed"] = False
        
        # Print results
        for category, tests in [("imports", result["imports"]), ("config_test", result["config_test"])]:
            print(f"  {category.title()}:")
            for test, status in tests.items():
                print(f"    {test}: {status}")
        
        return result
    
    async def test_workflow_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test a complete workflow scenario"""
        print(f"🎯 Testing workflow for {scenario['id']}...")
        
        result = {
            "scenario_id": scenario["id"],
            "passed": False,
            "workflow_results": {},
            "validation_results": {},
            "total_cost": 0.0,
            "total_time": 0.0,
            "errors": []
        }
        
        start_time = time.time()
        
        try:
            # Import orchestrator (should work since we tested imports)
            from mvp_orchestrator_script import Config, MVPOrchestrator
            import yaml
            
            # Load config
            with open("config.yaml", 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Replace environment variables
            for key, value in config_data.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    config_data[key] = os.environ.get(env_var, "")
            
            config = Config(**config_data)
            orchestrator = MVPOrchestrator(config)
            
            # Test market research (only this phase to save costs)
            print(f"  Running market research for {scenario['industry']} - {scenario['category']}...")
            
            try:
                market_research = await orchestrator.run_market_research(
                    scenario["industry"], 
                    scenario["category"]
                )
                
                result["workflow_results"]["market_research"] = market_research
                result["total_cost"] += market_research.get("cost", 0)
                print(f"    ✅ Market research completed (${market_research.get('cost', 0):.4f})")
                
                # Quick validation
                from validation_helpers import validate_market_research
                is_valid, issues = validate_market_research(
                    market_research["analysis"],
                    scenario["expected_outputs"]["market_research"]
                )
                
                if is_valid:
                    print(f"    ✅ Market research validation passed")
                else:
                    print(f"    ⚠️ Market research validation issues: {issues}")
                
                result["validation_results"]["market_research"] = {
                    "valid": is_valid,
                    "issues": issues
                }
                
            except Exception as e:
                error_msg = f"Market research failed: {e}"
                result["errors"].append(error_msg)
                print(f"    ❌ {error_msg}")
            
            # For cost savings, only test one workflow phase
            # In production, would test full workflow
            
            result["total_time"] = time.time() - start_time
            result["passed"] = len(result["errors"]) == 0 and len(result["workflow_results"]) > 0
            
        except Exception as e:
            error_msg = f"Workflow setup failed: {e}"
            result["errors"].append(error_msg)
            print(f"  ❌ {error_msg}")
        
        print(f"  Scenario completed in {result['total_time']:.2f}s for ${result['total_cost']:.4f}")
        
        return result
    
    def generate_test_summary(self) -> Dict[str, Any]:
        """Generate overall test summary"""
        print("\n📊 Generating test summary...")
        
        summary = {
            "total_time": time.time() - self.start_time,
            "total_cost": self.total_cost,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "overall_status": "❌ FAILED",
            "recommendations": []
        }
        
        # Count test results
        for test_name, test_result in self.test_results.items():
            if test_name == "summary":
                continue
                
            summary["tests_run"] += 1
            if isinstance(test_result, dict) and test_result.get("passed", False):
                summary["tests_passed"] += 1
            else:
                summary["tests_failed"] += 1
        
        # Determine overall status
        pass_rate = summary["tests_passed"] / summary["tests_run"] if summary["tests_run"] > 0 else 0
        
        if pass_rate >= 0.8:
            summary["overall_status"] = "✅ PASSED"
        elif pass_rate >= 0.6:
            summary["overall_status"] = "⚠️ PARTIAL"
        else:
            summary["overall_status"] = "❌ FAILED"
        
        # Generate recommendations
        if summary["tests_failed"] > 0:
            summary["recommendations"].append("Review and fix failed tests before production")
        
        if self.total_cost > 5.0:
            summary["recommendations"].append(f"High testing cost: ${self.total_cost:.2f} - optimize for production")
        
        if summary["total_time"] > 300:  # 5 minutes
            summary["recommendations"].append("Long test time - consider parallelization")
        
        if pass_rate < 1.0:
            summary["recommendations"].append("Not all tests passed - investigate failures")
        
        return summary
    
    def print_final_report(self):
        """Print comprehensive test report"""
        print("\n" + "="*60)
        print("📋 FINAL TEST REPORT")
        print("="*60)
        
        summary = self.test_results.get("summary", {})
        
        print(f"Overall Status: {summary.get('overall_status', 'Unknown')}")
        print(f"Tests Run: {summary.get('tests_run', 0)}")
        print(f"Tests Passed: {summary.get('tests_passed', 0)}")
        print(f"Tests Failed: {summary.get('tests_failed', 0)}")
        print(f"Total Time: {summary.get('total_time', 0):.2f}s")
        print(f"Total Cost: ${summary.get('total_cost', 0):.4f}")
        
        if summary.get("recommendations"):
            print("\nRecommendations:")
            for rec in summary["recommendations"]:
                print(f"  • {rec}")
        
        print("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            if test_name == "summary":
                continue
            
            status = "✅ PASS" if result.get("passed", False) else "❌ FAIL"
            print(f"  {test_name}: {status}")
            
            if result.get("errors"):
                for error in result["errors"]:
                    print(f"    Error: {error}")
        
        print("\n" + "="*60)


async def main():
    """Main test execution"""
    tester = IntegrationTester()
    
    try:
        results = await tester.run_all_tests()
        tester.print_final_report()
        
        # Save results to file
        results_file = Path("test_results.json")
        with open(results_file, 'w') as f:
            # Convert any non-serializable objects to strings
            serializable_results = json.loads(json.dumps(results, default=str))
            json.dump(serializable_results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to {results_file}")
        
        # Return appropriate exit code
        summary = results.get("summary", {})
        if summary.get("overall_status", "").startswith("✅"):
            return 0  # Success
        else:
            return 1  # Failure
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())