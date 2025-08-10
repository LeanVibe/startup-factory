#!/usr/bin/env python3
"""
Template Validator CLI

Command-line interface for validating Startup Factory templates.
Provides comprehensive validation with detailed reporting and CI/CD integration.

Usage:
    python template_validator_cli.py validate --template neoforge
    python template_validator_cli.py validate-all
    python template_validator_cli.py regression-test
    python template_validator_cli.py benchmark --template neoforge
"""

import asyncio
import argparse
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import subprocess

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.template_validation import TemplateQualityGates, ValidationResult


class TemplateValidatorCLI:
    """Command-line interface for template validation"""
    
    def __init__(self):
        self.quality_gates = TemplateQualityGates()
        self.templates_dir = project_root / "templates"
        
    async def validate_template(self, template_name: str, verbose: bool = False) -> bool:
        """Validate a specific template"""
        template_path = self.templates_dir / template_name
        
        if not template_path.exists():
            print(f"❌ Template not found: {template_name}")
            return False
            
        print(f"🔍 Validating template: {template_name}")
        
        try:
            result = await self.quality_gates.validate_template(template_path)
            
            # Print results
            status = "✅ PASS" if result.is_valid else "❌ FAIL"
            print(f"{status} {template_name}")
            print(f"   Score: {result.score:.3f}")
            print(f"   Time: {result.execution_time:.2f}s")
            
            if result.errors:
                print(f"   Errors: {len(result.errors)}")
                if verbose:
                    for error in result.errors:
                        print(f"     - {error}")
                        
            if result.warnings:
                print(f"   Warnings: {len(result.warnings)}")
                if verbose:
                    for warning in result.warnings:
                        print(f"     - {warning}")
            
            if verbose and result.details:
                print("   Details:")
                for context, details in result.details.items():
                    if isinstance(details, dict) and "validation_type" in details:
                        validation_type = details["validation_type"]
                        score_key = f"{validation_type}_score"
                        if score_key in details:
                            print(f"     {validation_type}: {details[score_key]:.3f}")
            
            return result.is_valid
            
        except Exception as e:
            print(f"❌ Validation failed: {str(e)}")
            return False
    
    async def validate_all_templates(self, min_score: float = 0.7, verbose: bool = False) -> bool:
        """Validate all available templates"""
        print("🔍 Validating all templates...")
        
        if not self.templates_dir.exists():
            print(f"❌ Templates directory not found: {self.templates_dir}")
            return False
            
        try:
            self.quality_gates.templates_dir = self.templates_dir
            results = await self.quality_gates.validate_all_templates()
            
            if not results:
                print("❌ No templates found to validate")
                return False
            
            # Print summary
            total_templates = len(results)
            passed_templates = sum(1 for r in results.values() if r.is_valid)
            avg_score = sum(r.score for r in results.values()) / total_templates
            
            print(f"\n📊 Validation Summary:")
            print(f"   Total Templates: {total_templates}")
            print(f"   Passed: {passed_templates}")
            print(f"   Failed: {total_templates - passed_templates}")
            print(f"   Average Score: {avg_score:.3f}")
            
            # Print individual results
            print(f"\n📋 Individual Results:")
            for template_name, result in results.items():
                status = "✅" if result.is_valid else "❌"
                score_status = "⭐" if result.score >= min_score else "⚠️"
                print(f"   {status} {score_status} {template_name}: {result.score:.3f}")
                
                if verbose:
                    if result.errors:
                        for error in result.errors[:3]:  # Show first 3 errors
                            print(f"        🚫 {error}")
                    if result.warnings:
                        for warning in result.warnings[:3]:  # Show first 3 warnings
                            print(f"        ⚠️  {warning}")
            
            # Generate report
            report = self.quality_gates.generate_report(results)
            report_file = f"template_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            with open(report_file, 'w') as f:
                f.write(report)
            
            print(f"\n📄 Detailed report saved: {report_file}")
            
            # Quality gate: All templates must pass and meet minimum score
            all_passed = all(r.is_valid and r.score >= min_score for r in results.values())
            
            if not all_passed:
                print(f"\n❌ Quality gate failed: Not all templates meet minimum score ({min_score})")
                return False
                
            print(f"\n✅ All templates passed quality gates!")
            return True
            
        except Exception as e:
            print(f"❌ Validation failed: {str(e)}")
            return False
    
    async def run_regression_tests(self, create_baseline: bool = False, verbose: bool = False) -> bool:
        """Run regression tests (placeholder for future implementation)"""
        print("🔄 Regression testing not yet implemented in standalone CLI")
        return True
    
    async def benchmark_template(self, template_name: str, iterations: int = 3) -> bool:
        """Benchmark template generation performance"""
        template_path = self.templates_dir / template_name
        
        if not template_path.exists():
            print(f"❌ Template not found: {template_name}")
            return False
            
        print(f"⏱️  Benchmarking template: {template_name} ({iterations} iterations)")
        
        try:
            times = []
            
            for i in range(iterations):
                print(f"   Run {i+1}/{iterations}...", end=" ")
                start_time = time.time()
                
                result = await self.quality_gates.validate_template(template_path)
                
                end_time = time.time()
                execution_time = end_time - start_time
                times.append(execution_time)
                
                print(f"{execution_time:.2f}s")
            
            # Calculate statistics
            min_time = min(times)
            max_time = max(times)
            avg_time = sum(times) / len(times)
            
            print(f"\n📊 Benchmark Results for {template_name}:")
            print(f"   Min Time: {min_time:.3f}s")
            print(f"   Max Time: {max_time:.3f}s")
            print(f"   Avg Time: {avg_time:.3f}s")
            
            # Performance thresholds
            threshold_warning = 30.0  # 30 seconds
            threshold_error = 60.0    # 1 minute
            
            if avg_time > threshold_error:
                print(f"   ❌ Performance issue: Avg time ({avg_time:.2f}s) exceeds error threshold ({threshold_error}s)")
                return False
            elif avg_time > threshold_warning:
                print(f"   ⚠️  Performance warning: Avg time ({avg_time:.2f}s) exceeds warning threshold ({threshold_warning}s)")
            else:
                print(f"   ✅ Performance: Within acceptable limits")
            
            return True
            
        except Exception as e:
            print(f"❌ Benchmarking failed: {str(e)}")
            return False
    
    def list_templates(self) -> bool:
        """List all available templates"""
        print("📋 Available Templates:")
        
        if not self.templates_dir.exists():
            print(f"❌ Templates directory not found: {self.templates_dir}")
            return False
        
        templates_found = False
        
        for template_dir in self.templates_dir.iterdir():
            if template_dir.is_dir() and (template_dir / "cookiecutter.json").exists():
                templates_found = True
                
                # Load template info
                try:
                    with open(template_dir / "cookiecutter.json", 'r') as f:
                        config = json.load(f)
                    
                    description = config.get("project_short_description", "No description")
                    print(f"   📁 {template_dir.name}")
                    print(f"      {description}")
                    
                except Exception as e:
                    print(f"   📁 {template_dir.name} (failed to read config: {str(e)})")
        
        if not templates_found:
            print("   No templates found")
            return False
            
        return True
    
    async def continuous_integration_mode(self, min_score: float = 0.8) -> bool:
        """Run in CI/CD mode with strict quality gates"""
        print("🚀 Running in Continuous Integration mode")
        print(f"   Minimum quality score: {min_score}")
        
        success = True
        
        # Run all validations
        print("\n1️⃣ Running template validation...")
        validation_success = await self.validate_all_templates(min_score=min_score)
        
        if not validation_success:
            success = False
            print("❌ Template validation failed")
        else:
            print("✅ Template validation passed")
        
        # Final result
        if success:
            print("\n🎉 All CI checks passed!")
            return True
        else:
            print("\n💥 CI checks failed!")
            return False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Template Validator CLI for Startup Factory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list
  %(prog)s validate --template neoforge
  %(prog)s validate-all --min-score 0.8
  %(prog)s regression-test --create-baseline
  %(prog)s benchmark --template neoforge --iterations 5
  %(prog)s ci --min-score 0.9
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available templates')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a specific template')
    validate_parser.add_argument('--template', required=True, help='Template name to validate')
    validate_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Validate all command
    validate_all_parser = subparsers.add_parser('validate-all', help='Validate all templates')
    validate_all_parser.add_argument('--min-score', type=float, default=0.7, help='Minimum quality score (default: 0.7)')
    validate_all_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Regression test command
    regression_parser = subparsers.add_parser('regression-test', help='Run regression tests')
    regression_parser.add_argument('--create-baseline', action='store_true', help='Create baseline snapshots')
    regression_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark template performance')
    benchmark_parser.add_argument('--template', required=True, help='Template name to benchmark')
    benchmark_parser.add_argument('--iterations', type=int, default=3, help='Number of iterations (default: 3)')
    
    # CI command
    ci_parser = subparsers.add_parser('ci', help='Run in CI/CD mode')
    ci_parser.add_argument('--min-score', type=float, default=0.8, help='Minimum quality score (default: 0.8)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = TemplateValidatorCLI()
    
    try:
        if args.command == 'list':
            success = cli.list_templates()
            
        elif args.command == 'validate':
            success = asyncio.run(cli.validate_template(args.template, args.verbose))
            
        elif args.command == 'validate-all':
            success = asyncio.run(cli.validate_all_templates(args.min_score, args.verbose))
            
        elif args.command == 'regression-test':
            success = asyncio.run(cli.run_regression_tests(args.create_baseline, args.verbose))
            
        elif args.command == 'benchmark':
            success = asyncio.run(cli.benchmark_template(args.template, args.iterations))
            
        elif args.command == 'ci':
            success = asyncio.run(cli.continuous_integration_mode(args.min_score))
            
        else:
            print(f"Unknown command: {args.command}")
            return 1
            
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())