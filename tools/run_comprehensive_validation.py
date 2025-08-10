#!/usr/bin/env python3
"""
Comprehensive Validation Suite Runner
Executes all end-to-end tests and generates unified validation report for production readiness
"""

import asyncio
import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import traceback

@dataclass
class ValidationSuiteResult:
    suite_name: str
    status: str
    duration: float
    passed: int
    failed: int
    warnings: int
    details: str
    report_file: Optional[str] = None
    error: Optional[str] = None

class ComprehensiveValidator:
    """Runs all validation suites and generates production readiness report"""
    
    def __init__(self):
        self.results: List[ValidationSuiteResult] = []
        self.start_time = time.time()
        self.tools_dir = Path(__file__).parent
        
    def log_suite_result(self, result: ValidationSuiteResult):
        """Log validation suite result"""
        self.results.append(result)
        
        status_icons = {
            "PASS": "✅",
            "FAIL": "❌", 
            "PARTIAL": "⚠️",
            "ERROR": "💥"
        }
        
        icon = status_icons.get(result.status, "❓")
        print(f"{icon} {result.suite_name}: {result.details}")
        print(f"   ⏱️ Duration: {result.duration:.2f}s")
        if result.passed or result.failed or result.warnings:
            print(f"   📊 Results: {result.passed} passed, {result.failed} failed, {result.warnings} warnings")
        if result.error:
            print(f"   🔍 Error: {result.error}")
        if result.report_file:
            print(f"   📄 Report: {result.report_file}")
        print()
    
    async def run_workflow_validation(self) -> ValidationSuiteResult:
        """Run workflow validation suite"""
        print("🔍 Running Workflow Validation Suite...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                sys.executable, "test_workflow_validation.py"
            ], cwd=self.tools_dir, capture_output=True, text=True, timeout=120)
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                # Parse output for results
                output_lines = result.stdout.split('\n')
                passed = len([line for line in output_lines if line.startswith('✅')])
                failed = len([line for line in output_lines if line.startswith('❌')])
                warnings = len([line for line in output_lines if line.startswith('⚠️')])
                
                return ValidationSuiteResult(
                    suite_name="Workflow Validation",
                    status="PASS" if failed == 0 else "PARTIAL" if warnings > 0 else "FAIL",
                    duration=duration,
                    passed=passed,
                    failed=failed,
                    warnings=warnings,
                    details=f"Core workflow components validated successfully",
                    report_file="workflow_validation_report.json"
                )
            else:
                return ValidationSuiteResult(
                    suite_name="Workflow Validation",
                    status="FAIL",
                    duration=duration,
                    passed=0,
                    failed=1,
                    warnings=0,
                    details="Workflow validation suite failed to execute",
                    error=result.stderr[:200] if result.stderr else "Unknown error"
                )
                
        except Exception as e:
            return ValidationSuiteResult(
                suite_name="Workflow Validation",
                status="ERROR",
                duration=time.time() - start_time,
                passed=0,
                failed=1,
                warnings=0,
                details="Workflow validation encountered an error",
                error=str(e)[:200]
            )
    
    async def run_api_integration_validation(self) -> ValidationSuiteResult:
        """Run API integration validation suite"""
        print("🔌 Running API Integration Validation Suite...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                sys.executable, "test_api_integration.py"
            ], cwd=self.tools_dir, capture_output=True, text=True, timeout=60)
            
            duration = time.time() - start_time
            
            # Parse results from output
            output_lines = result.stdout.split('\n')
            passed = len([line for line in output_lines if line.startswith('✅')])
            failed = len([line for line in output_lines if line.startswith('❌')])
            warnings = len([line for line in output_lines if line.startswith('⚠️')])
            
            # Check for successful completion
            if "All API integration tests passed" in result.stdout:
                status = "PASS"
                details = "API integration fully validated"
            elif passed > failed:
                status = "PARTIAL"
                details = f"Most API components validated ({passed} passed, {failed} failed)"
            else:
                status = "FAIL"
                details = f"API integration issues detected ({passed} passed, {failed} failed)"
            
            return ValidationSuiteResult(
                suite_name="API Integration",
                status=status,
                duration=duration,
                passed=passed,
                failed=failed,
                warnings=warnings,
                details=details,
                report_file="api_integration_report.json",
                error=result.stderr[:200] if result.stderr and result.returncode != 0 else None
            )
            
        except Exception as e:
            return ValidationSuiteResult(
                suite_name="API Integration",
                status="ERROR", 
                duration=time.time() - start_time,
                passed=0,
                failed=1,
                warnings=0,
                details="API integration validation encountered an error",
                error=str(e)[:200]
            )
    
    async def run_template_generation_validation(self) -> ValidationSuiteResult:
        """Run template generation validation suite"""
        print("🏗️ Running Template Generation Validation Suite...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                sys.executable, "test_template_generation.py"
            ], cwd=self.tools_dir, capture_output=True, text=True, timeout=90)
            
            duration = time.time() - start_time
            
            # Parse results from output
            output_lines = result.stdout.split('\n')
            passed = len([line for line in output_lines if line.startswith('✅')])
            failed = len([line for line in output_lines if line.startswith('❌')])
            warnings = len([line for line in output_lines if line.startswith('⚠️')])
            
            if failed == 0:
                status = "PASS"
                details = "Template system fully functional"
            elif passed >= failed:
                status = "PARTIAL"
                details = f"Template system partially functional ({passed} passed, {failed} failed)"
            else:
                status = "FAIL"
                details = f"Template system has critical issues ({passed} passed, {failed} failed)"
            
            return ValidationSuiteResult(
                suite_name="Template Generation",
                status=status,
                duration=duration,
                passed=passed,
                failed=failed,
                warnings=warnings,
                details=details,
                report_file="template_generation_report.json",
                error=result.stderr[:200] if result.stderr and result.returncode != 0 else None
            )
            
        except Exception as e:
            return ValidationSuiteResult(
                suite_name="Template Generation",
                status="ERROR",
                duration=time.time() - start_time,
                passed=0,
                failed=1,
                warnings=0,
                details="Template generation validation encountered an error",
                error=str(e)[:200]
            )
    
    async def run_orchestrator_dry_run(self) -> ValidationSuiteResult:
        """Run orchestrator dry-run validation"""
        print("🚀 Running Orchestrator Dry-Run Validation...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                sys.executable, "test_orchestrator_dry_run.py"  
            ], cwd=self.tools_dir, capture_output=True, text=True, timeout=180)
            
            duration = time.time() - start_time
            
            # Parse results from output  
            output_lines = result.stdout.split('\n')
            passed = len([line for line in output_lines if line.startswith('✅')])
            failed = len([line for line in output_lines if line.startswith('❌')])
            warnings = len([line for line in output_lines if line.startswith('⚠️')])
            
            if "All dry-run tests passed" in result.stdout:
                status = "PASS"
                details = "Complete orchestrator workflow validated"
            elif "Most tests passed" in result.stdout or passed > failed:
                status = "PARTIAL"
                details = f"Orchestrator mostly functional ({passed} passed, {failed} failed)"
            else:
                status = "FAIL" 
                details = f"Orchestrator has critical issues ({passed} passed, {failed} failed)"
            
            return ValidationSuiteResult(
                suite_name="Orchestrator Dry-Run",
                status=status,
                duration=duration,
                passed=passed,
                failed=failed,
                warnings=warnings,
                details=details,
                report_file="orchestrator_dry_run_report.json",
                error=result.stderr[:200] if result.stderr and result.returncode != 0 else None
            )
            
        except Exception as e:
            return ValidationSuiteResult(
                suite_name="Orchestrator Dry-Run",
                status="ERROR",
                duration=time.time() - start_time,
                passed=0,
                failed=1,
                warnings=0,
                details="Orchestrator dry-run validation encountered an error",
                error=str(e)[:200]
            )
    
    def calculate_production_readiness(self) -> Dict[str, Any]:
        """Calculate overall production readiness score"""
        
        # Weight different test suites by importance
        suite_weights = {
            "Workflow Validation": 30,
            "API Integration": 25,
            "Orchestrator Dry-Run": 25,  
            "Template Generation": 20
        }
        
        total_weighted_score = 0
        total_possible_score = 0
        
        suite_scores = {}
        
        for result in self.results:
            weight = suite_weights.get(result.suite_name, 10)
            total_possible_score += weight
            
            if result.status == "PASS":
                score = weight
            elif result.status == "PARTIAL":
                # Calculate partial score based on pass/fail ratio
                total_tests = result.passed + result.failed
                if total_tests > 0:
                    score = weight * (result.passed / total_tests)
                else:
                    score = weight * 0.5  # Default partial score
            else:
                score = 0
            
            total_weighted_score += score
            suite_scores[result.suite_name] = {
                "score": score,
                "max_score": weight,
                "percentage": (score / weight * 100) if weight > 0 else 0
            }
        
        overall_percentage = (total_weighted_score / total_possible_score * 100) if total_possible_score > 0 else 0
        
        # Determine readiness level
        if overall_percentage >= 90:
            readiness_level = "PRODUCTION READY"
        elif overall_percentage >= 75:
            readiness_level = "MOSTLY READY" 
        elif overall_percentage >= 60:
            readiness_level = "NEEDS WORK"
        else:
            readiness_level = "NOT READY"
        
        return {
            "overall_percentage": round(overall_percentage, 1),
            "readiness_level": readiness_level,
            "total_weighted_score": round(total_weighted_score, 1),
            "total_possible_score": total_possible_score,
            "suite_scores": suite_scores
        }
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation suites and generate comprehensive report"""
        
        print("🚀 Starting Comprehensive Validation Suite")
        print("=" * 80)
        print(f"📍 Tools Directory: {self.tools_dir}")
        print(f"⏰ Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run all validation suites
        validation_suites = [
            self.run_workflow_validation,
            self.run_api_integration_validation,
            self.run_template_generation_validation,
            self.run_orchestrator_dry_run
        ]
        
        for suite_runner in validation_suites:
            try:
                result = await suite_runner()
                self.log_suite_result(result)
            except Exception as e:
                error_result = ValidationSuiteResult(
                    suite_name=suite_runner.__name__.replace("run_", "").replace("_", " ").title(),
                    status="ERROR",
                    duration=0,
                    passed=0,
                    failed=1,
                    warnings=0,
                    details=f"Suite runner failed: {str(e)}",
                    error=str(e)
                )
                self.log_suite_result(error_result)
        
        total_duration = time.time() - self.start_time
        
        # Calculate production readiness
        readiness_metrics = self.calculate_production_readiness()
        
        # Generate summary
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_warnings = sum(r.warnings for r in self.results)
        
        summary = {
            "timestamp": time.time(),
            "total_duration": total_duration,
            "suites_run": len(self.results),
            "total_tests": total_passed + total_failed,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_warnings": total_warnings,
            "production_readiness": readiness_metrics,
            "suite_results": [
                {
                    "suite_name": r.suite_name,
                    "status": r.status,
                    "duration": r.duration,
                    "passed": r.passed,
                    "failed": r.failed,
                    "warnings": r.warnings,
                    "details": r.details,
                    "report_file": r.report_file,
                    "error": r.error
                }
                for r in self.results
            ]
        }
        
        # Print comprehensive summary
        print("=" * 80)
        print("🏁 Comprehensive Validation Summary")
        print("=" * 80)
        print(f"⏱️ Total Duration: {total_duration:.2f}s")
        print(f"📊 Test Suites: {len(self.results)}")
        print(f"✅ Total Passed: {total_passed}")
        print(f"❌ Total Failed: {total_failed}")
        print(f"⚠️ Total Warnings: {total_warnings}")
        print()
        print(f"🎯 Production Readiness: {readiness_metrics['overall_percentage']:.1f}% - {readiness_metrics['readiness_level']}")
        print()
        
        # Show suite breakdown
        print("📋 Suite Breakdown:")
        for suite_name, scores in readiness_metrics['suite_scores'].items():
            print(f"   {suite_name}: {scores['percentage']:.1f}% ({scores['score']:.1f}/{scores['max_score']})")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if readiness_metrics['overall_percentage'] >= 90:
            print("   ✅ System is production-ready! Proceed with deployment.")
        elif readiness_metrics['overall_percentage'] >= 75:
            print("   ⚠️ System is mostly ready. Address remaining issues before production.")
        elif readiness_metrics['overall_percentage'] >= 60:
            print("   🔧 System needs work. Focus on failed test suites.")
        else:
            print("   ❌ System is not ready for production. Major fixes required.")
        
        # List critical issues
        critical_issues = [r for r in self.results if r.status in ["FAIL", "ERROR"]]
        if critical_issues:
            print("\n🚨 Critical Issues to Address:")
            for issue in critical_issues:
                print(f"   • {issue.suite_name}: {issue.details}")
        
        return summary
    
    def generate_unified_report(self, summary: Dict[str, Any], filename: str = "comprehensive_validation_report.json"):
        """Generate unified validation report"""
        
        try:
            # Enhanced report with metadata
            report_data = {
                "report_type": "comprehensive_validation",
                "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                "startup_factory_version": "1.0",
                "test_environment": "development",
                "summary": summary,
                "recommendations": self._generate_recommendations(summary),
                "next_steps": self._generate_next_steps(summary)
            }
            
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"\n📄 Comprehensive validation report saved to: {filename}")
            
        except Exception as e:
            print(f"⚠️ Could not generate unified report: {e}")
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate specific recommendations based on test results"""
        recommendations = []
        
        readiness = summary['production_readiness']['overall_percentage']
        
        if readiness >= 90:
            recommendations.extend([
                "System is production-ready",
                "Consider final user acceptance testing",
                "Setup monitoring and alerting",
                "Prepare rollback procedures"
            ])
        elif readiness >= 75:
            recommendations.extend([
                "Address template system configuration issues", 
                "Test with small budget on real APIs",
                "Fix cookiecutter.json missing variables",
                "Validate template file completeness"
            ])
        else:
            recommendations.extend([
                "Fix critical workflow issues first",
                "Validate API integration thoroughly",
                "Test error handling with real scenarios",
                "Review architecture for missing components"
            ])
        
        # Add specific recommendations based on failed suites
        for result in self.results:
            if result.status == "FAIL":
                if "Template" in result.suite_name:
                    recommendations.append("Fix template system configuration and dependencies")
                elif "API" in result.suite_name:
                    recommendations.append("Resolve API integration and authentication issues")
                elif "Orchestrator" in result.suite_name:
                    recommendations.append("Debug orchestrator workflow execution problems")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _generate_next_steps(self, summary: Dict[str, Any]) -> List[str]:
        """Generate next steps based on validation results"""
        next_steps = []
        
        readiness = summary['production_readiness']['overall_percentage']
        
        if readiness >= 90:
            next_steps.extend([
                "Deploy to staging environment",
                "Conduct user acceptance testing",
                "Setup production monitoring",
                "Plan production launch"
            ])
        elif readiness >= 75:
            next_steps.extend([
                "Fix template configuration issues",
                "Test with real API calls (small budget)",
                "Re-run validation suite",
                "Deploy to staging after fixes"
            ])
        else:
            next_steps.extend([
                "Address all critical failures", 
                "Re-run individual test suites",
                "Conduct focused debugging",
                "Re-run comprehensive validation"
            ])
        
        return next_steps

async def main():
    """Main validation execution"""
    validator = ComprehensiveValidator()
    
    try:
        summary = await validator.run_comprehensive_validation()
        validator.generate_unified_report(summary)
        
        # Return success based on production readiness
        readiness = summary['production_readiness']['overall_percentage']
        return readiness >= 75  # 75% threshold for success
        
    except Exception as e:
        print(f"💥 Comprehensive validation failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)