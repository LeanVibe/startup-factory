#!/usr/bin/env python3
"""
AI Provider Performance Benchmarks

Comprehensive performance testing for AI providers including:
- Response time benchmarks across different task complexities
- Cost efficiency analysis
- Throughput testing under various loads
- Provider comparison metrics
- Production performance validation

Usage:
    # Run all benchmarks
    pytest tests/performance/test_ai_provider_benchmarks.py -v
    
    # Run only fast benchmarks (skip slow/expensive tests)
    pytest tests/performance/test_ai_provider_benchmarks.py -m "not slow"
    
    # Run with real APIs (requires API keys)
    AI_TEST_MODE=real pytest tests/performance/test_ai_provider_benchmarks.py
"""

import asyncio
import os
import pytest
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from ai_providers import (
    AIProviderManager, OpenAIProvider, AnthropicProvider,
    ProviderConfig, ProviderCall
)
from core_types import Task, TaskResult, TaskType, TaskPriority, generate_task_id


class PerformanceBenchmarks:
    """Performance benchmark utilities"""
    
    @staticmethod
    def calculate_stats(times: List[float]) -> Dict[str, float]:
        """Calculate performance statistics"""
        if not times:
            return {}
        
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
            "p99": statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times)
        }
    
    @staticmethod
    def generate_benchmark_report(results: Dict[str, Dict]) -> str:
        """Generate formatted benchmark report"""
        report = ["# AI Provider Performance Benchmark Report", f"Generated: {datetime.now().isoformat()}", ""]
        
        for test_name, data in results.items():
            report.append(f"## {test_name}")
            report.append(f"- **Mean Response Time**: {data['stats']['mean']:.2f}s")
            report.append(f"- **P95 Response Time**: {data['stats']['p95']:.2f}s") 
            report.append(f"- **Success Rate**: {data['success_rate']:.1%}")
            report.append(f"- **Average Cost**: ${data['avg_cost']:.4f}")
            report.append(f"- **Tokens/Second**: {data['tokens_per_second']:.1f}")
            report.append("")
        
        return "\n".join(report)


@pytest.fixture(scope="module")
def benchmark_config():
    """Configuration for benchmarks"""
    return {
        "iterations": 3,  # Number of iterations per test
        "timeout": 30,    # Max time per request
        "rate_limit_delay": 1,  # Delay between requests
        "save_results": True    # Save results to file
    }


@pytest.fixture
def openai_benchmark_config():
    """OpenAI configuration optimized for benchmarking"""
    return ProviderConfig(
        name="openai-benchmark",
        api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        models={
            "research": "gpt-4o-mini",
            "code": "gpt-4o",
            "analysis": "gpt-4o-mini"
        },
        cost_per_input_token=0.000150 / 1000,
        cost_per_output_token=0.000600 / 1000,
        max_tokens=4000,
        max_concurrent=5,
        enabled=True
    )


@pytest.fixture  
def anthropic_benchmark_config():
    """Anthropic configuration optimized for benchmarking"""
    return ProviderConfig(
        name="anthropic-benchmark",
        api_key=os.getenv("ANTHROPIC_API_KEY", "test-key"),
        models={
            "research": "claude-3-haiku-20240307",
            "code": "claude-3-sonnet-20240229",
            "analysis": "claude-3-haiku-20240307"
        },
        cost_per_input_token=0.25 / 1000000,
        cost_per_output_token=1.25 / 1000000,
        max_tokens=4000,
        max_concurrent=5,
        enabled=True
    )


class TestAIProviderPerformanceBenchmarks:
    """Comprehensive performance benchmarks for AI providers"""
    
    # ========== Response Time Benchmarks ==========
    
    @pytest.mark.asyncio
    async def test_response_time_by_complexity(self, openai_benchmark_config, benchmark_config):
        """Benchmark response times across different task complexities"""
        has_api_key = bool(os.getenv("OPENAI_API_KEY"))
        
        provider = OpenAIProvider(openai_benchmark_config)
        
        # Define complexity test cases
        complexity_tests = [
            {
                "name": "simple_query",
                "prompt": "What is machine learning?",
                "max_tokens": 100,
                "expected_max_time": 5
            },
            {
                "name": "medium_analysis", 
                "prompt": "Analyze the key trends in artificial intelligence for 2025. Provide 5 specific trends with brief explanations.",
                "max_tokens": 300,
                "expected_max_time": 10
            },
            {
                "name": "complex_research",
                "prompt": "Conduct a comprehensive market analysis for a new SaaS startup in the project management space. Include market size, key competitors, target customer segments, pricing strategies, and go-to-market recommendations. Provide detailed insights for each area.",
                "max_tokens": 800,
                "expected_max_time": 20
            }
        ]
        
        results = {}
        
        for test_case in complexity_tests:
            times = []
            costs = []
            tokens = []
            successes = 0
            
            print(f"\n🔍 Benchmarking: {test_case['name']}")
            
            for iteration in range(benchmark_config["iterations"]):
                task = Task(
                    id=generate_task_id(),
                    startup_id="benchmark_complexity",
                    type=TaskType.MARKET_RESEARCH,
                    description=f"Complexity benchmark - {test_case['name']}",
                    prompt=test_case["prompt"],
                    max_tokens=test_case["max_tokens"],
                    priority=TaskPriority.MEDIUM
                )
                
                if has_api_key:
                    # Rate limiting for real API
                    if iteration > 0:
                        await asyncio.sleep(benchmark_config["rate_limit_delay"])
                    
                    start_time = time.time()
                    result = await provider.call_api(task)
                    execution_time = time.time() - start_time
                    
                    times.append(execution_time)
                    costs.append(result.cost)
                    tokens.append(result.tokens_used)
                    if result.success:
                        successes += 1
                        
                    print(f"  Iteration {iteration + 1}: {execution_time:.2f}s, ${result.cost:.4f}, {result.tokens_used} tokens")
                else:
                    # Mock timing for development/CI
                    mock_time = test_case["expected_max_time"] * 0.3 + (iteration * 0.1)
                    times.append(mock_time)
                    costs.append(0.01 * (iteration + 1))
                    tokens.append(100 + iteration * 20)
                    successes += 1
                    
                    print(f"  Iteration {iteration + 1} (mocked): {mock_time:.2f}s")
            
            # Calculate statistics
            stats = PerformanceBenchmarks.calculate_stats(times)
            success_rate = successes / benchmark_config["iterations"]
            avg_cost = statistics.mean(costs) if costs else 0
            avg_tokens = statistics.mean(tokens) if tokens else 0
            tokens_per_second = avg_tokens / stats["mean"] if stats.get("mean", 0) > 0 else 0
            
            results[test_case["name"]] = {
                "stats": stats,
                "success_rate": success_rate,
                "avg_cost": avg_cost,
                "tokens_per_second": tokens_per_second,
                "expected_max_time": test_case["expected_max_time"]
            }
            
            # Validate performance expectations
            if has_api_key:
                assert stats["mean"] < test_case["expected_max_time"], f"{test_case['name']} exceeded expected time"
                assert success_rate >= 0.9, f"{test_case['name']} had low success rate: {success_rate}"
            
            print(f"  ✅ {test_case['name']}: {stats['mean']:.2f}s avg, {success_rate:.1%} success rate")
        
        # Generate and optionally save report
        if benchmark_config["save_results"]:
            report = PerformanceBenchmarks.generate_benchmark_report(results)
            report_path = Path("benchmark_results") / f"complexity_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            report_path.parent.mkdir(exist_ok=True)
            report_path.write_text(report)
            print(f"📊 Benchmark report saved: {report_path}")
        
        return results
    
    # ========== Provider Comparison Benchmarks ==========
    
    @pytest.mark.asyncio
    async def test_provider_comparison_benchmark(self, openai_benchmark_config, anthropic_benchmark_config, benchmark_config):
        """Compare performance across different AI providers"""
        providers = {}
        
        if os.getenv("OPENAI_API_KEY"):
            providers["openai"] = OpenAIProvider(openai_benchmark_config)
        if os.getenv("ANTHROPIC_API_KEY"):
            providers["anthropic"] = AnthropicProvider(anthropic_benchmark_config)
        
        if not providers:
            pytest.skip("No API keys provided for provider comparison")
        
        # Standard test task for comparison
        test_prompt = "Explain the key benefits of microservices architecture for a growing startup. Provide 3 main benefits with brief explanations."
        
        comparison_results = {}
        
        for provider_name, provider in providers.items():
            print(f"\n🔍 Benchmarking provider: {provider_name}")
            
            times = []
            costs = []
            tokens = []
            successes = 0
            
            for iteration in range(benchmark_config["iterations"]):
                task = Task(
                    id=generate_task_id(),
                    startup_id="benchmark_comparison",
                    type=TaskType.FOUNDER_ANALYSIS,
                    description=f"Provider comparison - {provider_name}",
                    prompt=test_prompt,
                    max_tokens=250,
                    priority=TaskPriority.MEDIUM
                )
                
                # Rate limiting
                if iteration > 0:
                    await asyncio.sleep(benchmark_config["rate_limit_delay"] * 2)
                
                start_time = time.time()
                result = await provider.call_api(task)
                execution_time = time.time() - start_time
                
                times.append(execution_time)
                costs.append(result.cost)
                tokens.append(result.tokens_used)
                if result.success:
                    successes += 1
                
                print(f"  {provider_name} iteration {iteration + 1}: {execution_time:.2f}s, ${result.cost:.4f}")
            
            # Calculate statistics
            stats = PerformanceBenchmarks.calculate_stats(times)
            success_rate = successes / benchmark_config["iterations"]
            avg_cost = statistics.mean(costs)
            avg_tokens = statistics.mean(tokens)
            
            comparison_results[provider_name] = {
                "mean_time": stats["mean"],
                "p95_time": stats["p95"],
                "success_rate": success_rate,
                "avg_cost": avg_cost,
                "avg_tokens": avg_tokens,
                "cost_per_token": avg_cost / avg_tokens if avg_tokens > 0 else 0
            }
            
            print(f"  ✅ {provider_name}: {stats['mean']:.2f}s avg, ${avg_cost:.4f} avg cost")
        
        # Compare results
        print("\n📊 Provider Comparison Summary:")
        for provider_name, results in comparison_results.items():
            print(f"  {provider_name}:")
            print(f"    - Average Time: {results['mean_time']:.2f}s")
            print(f"    - Average Cost: ${results['avg_cost']:.4f}")
            print(f"    - Cost per Token: ${results['cost_per_token']:.6f}")
            print(f"    - Success Rate: {results['success_rate']:.1%}")
        
        return comparison_results
    
    # ========== Throughput & Load Testing ==========
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_throughput_benchmark(self, openai_benchmark_config, benchmark_config):
        """Benchmark concurrent request handling throughput"""
        has_api_key = bool(os.getenv("OPENAI_API_KEY"))
        
        if not has_api_key:
            pytest.skip("Throughput benchmarks require real API key")
        
        provider = OpenAIProvider(openai_benchmark_config)
        
        # Test different concurrency levels
        concurrency_levels = [1, 2, 3, 5]  # Conservative for API limits
        throughput_results = {}
        
        for concurrency in concurrency_levels:
            print(f"\n🔍 Testing concurrency level: {concurrency}")
            
            # Create tasks
            tasks = []
            for i in range(concurrency):
                task = Task(
                    id=generate_task_id(),
                    startup_id="throughput_test",
                    type=TaskType.CODE_GENERATION,
                    description=f"Throughput test {i}",
                    prompt=f"Write a Python function to sort a list of numbers. Use algorithm {i}.",
                    max_tokens=200,
                    priority=TaskPriority.MEDIUM
                )
                tasks.append(task)
            
            # Execute concurrently
            start_time = time.time()
            results = await asyncio.gather(
                *[provider.call_api(task) for task in tasks],
                return_exceptions=True
            )
            total_time = time.time() - start_time
            
            # Analyze results
            successful_results = [r for r in results if isinstance(r, TaskResult) and r.success]
            success_rate = len(successful_results) / len(tasks)
            
            if successful_results:
                avg_individual_time = statistics.mean([r.execution_time_seconds for r in successful_results])
                total_cost = sum(r.cost for r in successful_results)
                total_tokens = sum(r.tokens_used for r in successful_results)
                throughput = len(successful_results) / total_time  # requests per second
            else:
                avg_individual_time = 0
                total_cost = 0
                total_tokens = 0
                throughput = 0
            
            throughput_results[concurrency] = {
                "total_time": total_time,
                "success_rate": success_rate,
                "avg_individual_time": avg_individual_time,
                "total_cost": total_cost,
                "throughput": throughput,
                "total_tokens": total_tokens
            }
            
            print(f"  ✅ Concurrency {concurrency}: {throughput:.2f} req/s, {success_rate:.1%} success")
            
            # Rate limiting between concurrency levels
            await asyncio.sleep(5)
        
        # Find optimal concurrency
        best_throughput = max(throughput_results.values(), key=lambda x: x["throughput"])
        optimal_concurrency = next(k for k, v in throughput_results.items() if v == best_throughput)
        
        print(f"\n📊 Optimal concurrency level: {optimal_concurrency} ({best_throughput['throughput']:.2f} req/s)")
        
        return throughput_results
    
    # ========== Cost Efficiency Analysis ==========
    
    @pytest.mark.asyncio
    async def test_cost_efficiency_by_task_type(self, openai_benchmark_config, benchmark_config):
        """Analyze cost efficiency across different task types"""
        has_api_key = bool(os.getenv("OPENAI_API_KEY"))
        provider = OpenAIProvider(openai_benchmark_config)
        
        # Test different task types
        task_types = [
            {
                "type": TaskType.MARKET_RESEARCH,
                "prompt": "Research the target market for a new productivity app.",
                "expected_tokens": 200
            },
            {
                "type": TaskType.CODE_GENERATION,
                "prompt": "Write a Python class for user authentication with JWT tokens.",
                "expected_tokens": 300
            },
            {
                "type": TaskType.FOUNDER_ANALYSIS,
                "prompt": "Analyze the key qualities needed for a successful tech startup founder.",
                "expected_tokens": 250
            }
        ]
        
        cost_efficiency_results = {}
        
        for task_config in task_types:
            print(f"\n🔍 Cost efficiency for: {task_config['type'].value}")
            
            costs = []
            tokens = []
            cost_per_tokens = []
            
            for iteration in range(benchmark_config["iterations"]):
                task = Task(
                    id=generate_task_id(),
                    startup_id="cost_efficiency",
                    type=task_config["type"],
                    description=f"Cost efficiency test - {task_config['type'].value}",
                    prompt=task_config["prompt"],
                    max_tokens=task_config["expected_tokens"] + 100,
                    priority=TaskPriority.MEDIUM
                )
                
                if has_api_key:
                    if iteration > 0:
                        await asyncio.sleep(benchmark_config["rate_limit_delay"])
                    
                    result = await provider.call_api(task)
                    costs.append(result.cost)
                    tokens.append(result.tokens_used)
                    cost_per_tokens.append(result.cost / result.tokens_used if result.tokens_used > 0 else 0)
                    
                    print(f"  Iteration {iteration + 1}: ${result.cost:.4f} for {result.tokens_used} tokens")
                else:
                    # Mock data for development
                    mock_cost = 0.01 * (iteration + 1)
                    mock_tokens = task_config["expected_tokens"] + (iteration * 10)
                    costs.append(mock_cost)
                    tokens.append(mock_tokens)
                    cost_per_tokens.append(mock_cost / mock_tokens)
            
            # Calculate efficiency metrics
            avg_cost = statistics.mean(costs)
            avg_tokens = statistics.mean(tokens)
            avg_cost_per_token = statistics.mean(cost_per_tokens)
            
            cost_efficiency_results[task_config["type"].value] = {
                "avg_cost": avg_cost,
                "avg_tokens": avg_tokens,
                "cost_per_token": avg_cost_per_token,
                "expected_tokens": task_config["expected_tokens"],
                "efficiency_ratio": avg_tokens / task_config["expected_tokens"]
            }
            
            print(f"  ✅ {task_config['type'].value}: ${avg_cost:.4f} avg, {avg_cost_per_token:.6f} per token")
        
        # Find most cost-efficient task type
        most_efficient = min(cost_efficiency_results.values(), key=lambda x: x["cost_per_token"])
        most_efficient_type = next(k for k, v in cost_efficiency_results.items() if v == most_efficient)
        
        print(f"\n📊 Most cost-efficient task type: {most_efficient_type}")
        print(f"    Cost per token: ${most_efficient['cost_per_token']:.6f}")
        
        return cost_efficiency_results
    
    # ========== Production Performance Validation ==========
    
    @pytest.mark.asyncio
    async def test_production_performance_validation(self, openai_benchmark_config):
        """Validate performance meets production requirements"""
        has_api_key = bool(os.getenv("OPENAI_API_KEY"))
        provider = OpenAIProvider(openai_benchmark_config)
        
        # Production performance requirements
        requirements = {
            "max_response_time": 15.0,  # 15 seconds max
            "min_success_rate": 0.95,   # 95% success rate
            "max_cost_per_request": 0.50,  # 50 cents max per request
            "min_tokens_per_second": 10  # Minimum throughput
        }
        
        # Production-like test task
        task = Task(
            id=generate_task_id(),
            startup_id="production_validation",
            type=TaskType.MVP_SPECIFICATION,
            description="Production performance validation",
            prompt="Create a detailed MVP specification for a SaaS project management tool. Include core features, user stories, technical requirements, and success metrics.",
            max_tokens=600,
            priority=TaskPriority.HIGH
        )
        
        if has_api_key:
            # Run multiple iterations to validate consistency
            performance_metrics = []
            
            for i in range(3):
                if i > 0:
                    await asyncio.sleep(2)  # Rate limiting
                
                start_time = time.time()
                result = await provider.call_api(task)
                execution_time = time.time() - start_time
                
                performance_metrics.append({
                    "response_time": execution_time,
                    "success": result.success,
                    "cost": result.cost,
                    "tokens_used": result.tokens_used,
                    "tokens_per_second": result.tokens_used / execution_time if execution_time > 0 else 0
                })
            
            # Validate against requirements
            avg_response_time = statistics.mean([m["response_time"] for m in performance_metrics])
            success_rate = sum(1 for m in performance_metrics if m["success"]) / len(performance_metrics)
            avg_cost = statistics.mean([m["cost"] for m in performance_metrics])
            avg_tokens_per_second = statistics.mean([m["tokens_per_second"] for m in performance_metrics])
            
            # Assertions for production requirements
            assert avg_response_time <= requirements["max_response_time"], f"Response time {avg_response_time:.2f}s exceeds limit {requirements['max_response_time']}s"
            assert success_rate >= requirements["min_success_rate"], f"Success rate {success_rate:.2%} below requirement {requirements['min_success_rate']:.2%}"
            assert avg_cost <= requirements["max_cost_per_request"], f"Cost ${avg_cost:.4f} exceeds limit ${requirements['max_cost_per_request']}"
            assert avg_tokens_per_second >= requirements["min_tokens_per_second"], f"Throughput {avg_tokens_per_second:.1f} below requirement {requirements['min_tokens_per_second']}"
            
            print("✅ Production Performance Validation:")
            print(f"  Response Time: {avg_response_time:.2f}s (limit: {requirements['max_response_time']}s)")
            print(f"  Success Rate: {success_rate:.1%} (requirement: {requirements['min_success_rate']:.1%})")
            print(f"  Average Cost: ${avg_cost:.4f} (limit: ${requirements['max_cost_per_request']})")
            print(f"  Throughput: {avg_tokens_per_second:.1f} tokens/s (requirement: {requirements['min_tokens_per_second']})")
        else:
            print("✅ Production Performance Validation: Skipped (no API key)")
            pytest.skip("Production validation requires real API key")
    
    # ========== Reliability & Error Rate Analysis ==========
    
    @pytest.mark.slow 
    @pytest.mark.asyncio
    async def test_reliability_under_load(self, openai_benchmark_config):
        """Test reliability and error rates under sustained load"""
        has_api_key = bool(os.getenv("OPENAI_API_KEY"))
        
        if not has_api_key:
            pytest.skip("Reliability testing requires real API key")
        
        provider = OpenAIProvider(openai_benchmark_config)
        
        # Sustained load test - send requests over time
        test_duration = 60  # 1 minute test
        request_interval = 5  # Every 5 seconds
        
        results = []
        start_time = time.time()
        request_count = 0
        
        print(f"🔍 Running {test_duration}s reliability test (request every {request_interval}s)")
        
        while time.time() - start_time < test_duration:
            request_count += 1
            
            task = Task(
                id=generate_task_id(),
                startup_id="reliability_test",
                type=TaskType.MARKET_RESEARCH,
                description=f"Reliability test request {request_count}",
                prompt=f"Briefly analyze market trends for request {request_count}. Provide 2-3 key insights.",
                max_tokens=150,
                priority=TaskPriority.MEDIUM
            )
            
            request_start = time.time()
            try:
                result = await asyncio.wait_for(provider.call_api(task), timeout=30)
                request_time = time.time() - request_start
                
                results.append({
                    "request_id": request_count,
                    "success": result.success,
                    "response_time": request_time,
                    "cost": result.cost,
                    "error": None
                })
                
                print(f"  Request {request_count}: {'✅' if result.success else '❌'} ({request_time:.2f}s)")
            except Exception as e:
                request_time = time.time() - request_start
                results.append({
                    "request_id": request_count,
                    "success": False,
                    "response_time": request_time,
                    "cost": 0,
                    "error": str(e)
                })
                print(f"  Request {request_count}: ❌ Error - {str(e)[:50]}")
            
            # Wait for next request
            await asyncio.sleep(request_interval)
        
        # Analyze reliability results
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        reliability_metrics = {
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(results) if results else 0,
            "error_rate": len(failed_requests) / len(results) if results else 0,
            "avg_response_time": statistics.mean([r["response_time"] for r in successful_requests]) if successful_requests else 0,
            "total_cost": sum(r["cost"] for r in results)
        }
        
        print(f"\n📊 Reliability Test Results:")
        print(f"  Total Requests: {reliability_metrics['total_requests']}")
        print(f"  Success Rate: {reliability_metrics['success_rate']:.1%}")
        print(f"  Error Rate: {reliability_metrics['error_rate']:.1%}")
        print(f"  Avg Response Time: {reliability_metrics['avg_response_time']:.2f}s")
        print(f"  Total Cost: ${reliability_metrics['total_cost']:.4f}")
        
        # Reliability requirements for production
        assert reliability_metrics["success_rate"] >= 0.90, f"Success rate {reliability_metrics['success_rate']:.1%} too low"
        assert reliability_metrics["error_rate"] <= 0.10, f"Error rate {reliability_metrics['error_rate']:.1%} too high"
        
        return reliability_metrics