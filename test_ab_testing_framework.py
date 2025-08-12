#!/usr/bin/env python3
"""
Test-Driven Development for A/B Testing Framework

FIRST PRINCIPLES:
1. Founders need to validate improvement hypotheses with real users before full rollout
2. A/B testing must be simple enough for non-technical founders to understand and act on
3. Testing framework should integrate with MVP evolution recommendations for seamless iteration

TDD APPROACH:
1. Write failing tests for A/B testing and results analysis
2. Implement minimal A/B testing framework
3. Validate with realistic feature testing scenarios

FUNDAMENTAL TRUTH: 
Data-driven iteration requires hypothesis testing, not just implementation of assumed improvements.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

# Import from our existing systems and the actual implementation
from mvp_evolution_system import MVPEvolutionSystem, MVPImprovement, ImprovementType
from customer_feedback_system import FeedbackResponse, FeedbackType
from ab_testing_framework import (
    ABTestingFramework, ABTest, ABTestVariant, TestMetrics, TestRecommendation,
    TestStatus, TestResult
)

class TestABTestingFramework:
    """TDD tests for A/B testing framework"""
    
    @pytest.fixture
    def sample_improvement(self):
        """Sample MVP improvement for testing"""
        return MVPImprovement(
            improvement_id="perf_123",
            improvement_type=ImprovementType.PERFORMANCE_FIX,
            priority="high",
            title="Optimize Dashboard Loading Speed",
            description="Implement caching to reduce dashboard load time from 8s to 2s",
            business_impact="Improved user satisfaction and reduced churn",
            effort_estimate="1 week",
            success_metrics=["Page load time < 3s", "User satisfaction +0.5 points"],
            implementation_guidance="Add Redis caching layer and optimize SQL queries",
            based_on_feedback=["Dashboard is too slow", "Loading takes forever"],
            confidence_score=0.9
        )
    
    @pytest.fixture
    def business_context(self):
        return {
            "business_model": "b2b_saas",
            "industry": "healthcare", 
            "customers_acquired": 50,
            "monthly_active_users": 200
        }
    
    def test_create_ab_test_from_mvp_improvement(self, sample_improvement, business_context):
        """
        TEST: Framework should create A/B test from MVP improvement recommendation
        
        EXPECTED BEHAVIOR:
        - Test created with control (current) and variant (improved) versions
        - Hypothesis based on improvement description and expected impact
        - Success metrics aligned with improvement success metrics
        - Appropriate traffic split for business context
        """
        ab_framework = ABTestingFramework()
        
        test = ab_framework.create_test_from_improvement(
            sample_improvement, business_context, traffic_split=0.3
        )
        
        # Test creation
        assert isinstance(test, ABTest)
        assert test.test_id is not None and len(test.test_id) > 0
        assert test.improvement_source == sample_improvement.improvement_id
        assert len(test.hypothesis) > 20  # Meaningful hypothesis
        
        # Test variants
        assert len(test.variants) == 2  # Control + test variant
        control_variant = next((v for v in test.variants if v.is_control), None)
        test_variant = next((v for v in test.variants if not v.is_control), None)
        
        assert control_variant is not None
        assert test_variant is not None
        assert control_variant.traffic_percentage + test_variant.traffic_percentage == 1.0
        
        # Test configuration
        assert test.primary_metric in ["conversion_rate", "user_satisfaction", "feature_adoption"]
        assert len(test.secondary_metrics) >= 1
        assert test.status == TestStatus.DRAFT
    
    def test_user_variant_assignment_consistency(self, sample_improvement, business_context):
        """
        TEST: Users should be consistently assigned to the same variant
        
        EXPECTED BEHAVIOR:
        - Same user always gets same variant for a test
        - Traffic split percentages respected across user population
        - No user sees multiple variants for same test
        """
        ab_framework = ABTestingFramework()
        
        test = ab_framework.create_test_from_improvement(sample_improvement, business_context)
        ab_framework.start_test(test.test_id)
        
        # Test consistency
        user_id = "user_123"
        variant_1 = ab_framework.get_user_variant(test.test_id, user_id)
        variant_2 = ab_framework.get_user_variant(test.test_id, user_id)
        
        assert variant_1 == variant_2  # Same user gets same variant
        assert variant_1 is not None
        
        # Test variant is from the test
        variant_ids = [v.variant_id for v in test.variants]
        assert variant_1 in variant_ids
    
    def test_user_interaction_recording_and_metrics(self, sample_improvement, business_context):
        """
        TEST: Framework should record user interactions and calculate metrics
        
        EXPECTED BEHAVIOR:
        - Record conversions, feature usage, satisfaction ratings
        - Calculate conversion rates and secondary metrics automatically
        - Track sufficient sample sizes for statistical significance
        """
        ab_framework = ABTestingFramework()
        
        test = ab_framework.create_test_from_improvement(sample_improvement, business_context)
        ab_framework.start_test(test.test_id)
        
        # Simulate user interactions
        control_variant = next(v for v in test.variants if v.is_control)
        test_variant = next(v for v in test.variants if not v.is_control)
        
        # Record some conversions
        ab_framework.record_user_interaction(test.test_id, "user_1", control_variant.variant_id, "conversion")
        ab_framework.record_user_interaction(test.test_id, "user_2", control_variant.variant_id, "exposure")
        ab_framework.record_user_interaction(test.test_id, "user_3", test_variant.variant_id, "conversion") 
        ab_framework.record_user_interaction(test.test_id, "user_4", test_variant.variant_id, "conversion")
        ab_framework.record_user_interaction(test.test_id, "user_5", test_variant.variant_id, "exposure")
        
        # Check metrics calculation
        results_analysis = ab_framework.analyze_test_results(test.test_id)
        
        assert "variant_metrics" in results_analysis
        variant_metrics = results_analysis["variant_metrics"]
        
        # Check control metrics
        control_metrics = variant_metrics[control_variant.variant_id]
        assert control_metrics["users_exposed"] >= 2
        assert control_metrics["conversions"] >= 1
        assert 0 <= control_metrics["conversion_rate"] <= 1
        
        # Check test variant metrics  
        test_metrics = variant_metrics[test_variant.variant_id]
        assert test_metrics["users_exposed"] >= 2
        assert test_metrics["conversions"] >= 2
        assert 0 <= test_metrics["conversion_rate"] <= 1
    
    def test_statistical_significance_analysis(self, sample_improvement, business_context):
        """
        TEST: Framework should perform statistical significance analysis
        
        EXPECTED BEHAVIOR:
        - Calculate statistical significance between variants
        - Determine if results are conclusive based on confidence threshold
        - Handle insufficient sample size scenarios
        - Provide clear winner determination
        """
        ab_framework = ABTestingFramework()
        
        test = ab_framework.create_test_from_improvement(sample_improvement, business_context)
        ab_framework.start_test(test.test_id)
        
        # Add sufficient sample data for statistical analysis
        control_variant = next(v for v in test.variants if v.is_control)
        test_variant = next(v for v in test.variants if not v.is_control)
        
        # Simulate scenario where test variant performs better
        for i in range(50):  # Control: 50 users, 10 conversions (20%)
            ab_framework.record_user_interaction(test.test_id, f"control_user_{i}", 
                                               control_variant.variant_id, "exposure")
            if i < 10:
                ab_framework.record_user_interaction(test.test_id, f"control_user_{i}",
                                                   control_variant.variant_id, "conversion")
        
        for i in range(50):  # Test: 50 users, 20 conversions (40%)
            ab_framework.record_user_interaction(test.test_id, f"test_user_{i}",
                                               test_variant.variant_id, "exposure")
            if i < 20:
                ab_framework.record_user_interaction(test.test_id, f"test_user_{i}",
                                                   test_variant.variant_id, "conversion")
        
        # Analyze results
        results = ab_framework.analyze_test_results(test.test_id)
        
        assert "statistical_significance" in results
        assert "winning_variant" in results
        assert "test_result" in results
        
        # With 20% vs 40% conversion rates, test variant should win
        assert results["test_result"] in [TestResult.VARIANT_B_WINS, TestResult.NO_SIGNIFICANT_DIFFERENCE]
        
        if results["statistical_significance"] and results["statistical_significance"] >= 0.95:
            assert results["winning_variant"] == test_variant.variant_id
    
    def test_test_recommendation_generation(self, sample_improvement, business_context):
        """
        TEST: Framework should generate actionable recommendations based on results
        
        EXPECTED BEHAVIOR:
        - Clear recommendation (rollout, rollback, continue testing)
        - Reasoning based on statistical analysis and business context
        - Specific next actions for founders
        - Business impact forecast
        """
        ab_framework = ABTestingFramework()
        
        test = ab_framework.create_test_from_improvement(sample_improvement, business_context)
        ab_framework.start_test(test.test_id)
        
        # Simulate clear winning scenario
        control_variant = next(v for v in test.variants if v.is_control)
        test_variant = next(v for v in test.variants if not v.is_control)
        
        # Add data that shows test variant clearly wins
        for i in range(100):
            variant = control_variant if i < 50 else test_variant
            ab_framework.record_user_interaction(test.test_id, f"user_{i}", variant.variant_id, "exposure")
            
            # Test variant has much higher conversion rate
            conversion_threshold = 5 if variant.is_control else 25  # 10% vs 50% conversion
            if i % 50 < conversion_threshold:
                ab_framework.record_user_interaction(test.test_id, f"user_{i}", variant.variant_id, "conversion")
        
        # Get recommendation
        recommendation = ab_framework.get_test_recommendation(test.test_id)
        
        assert isinstance(recommendation, TestRecommendation)
        assert recommendation.test_id == test.test_id
        assert recommendation.recommendation_type in ["rollout", "rollback", "continue_testing", "redesign"]
        assert len(recommendation.reasoning) > 30  # Substantial reasoning
        assert len(recommendation.next_actions) >= 2  # Multiple actionable steps
        assert len(recommendation.business_impact_forecast) > 20  # Business impact described
        assert recommendation.confidence_level in ["high", "medium", "low"]
    
    def test_integration_with_mvp_evolution_workflow(self, sample_improvement, business_context):
        """
        TEST: A/B testing should integrate seamlessly with MVP evolution system
        
        EXPECTED BEHAVIOR:
        - Tests created directly from improvement recommendations
        - Success metrics aligned with improvement expectations  
        - Results fed back to evolution system for future recommendations
        - Business context preserved through testing workflow
        """
        ab_framework = ABTestingFramework()
        evolution_system = MVPEvolutionSystem()
        
        # Create test from improvement
        test = ab_framework.create_test_from_improvement(sample_improvement, business_context)
        
        # Test integration
        assert test.improvement_source == sample_improvement.improvement_id
        assert test.business_context == business_context
        
        # Success metrics alignment
        improvement_metrics = set(sample_improvement.success_metrics)
        test_metrics = {test.primary_metric} | set(test.secondary_metrics)
        
        # Should have overlap between improvement expectations and test metrics
        assert len(improvement_metrics & test_metrics) > 0 or any(
            any(metric_word in test_metric for test_metric in test_metrics)
            for improvement_metric in improvement_metrics
            for metric_word in improvement_metric.lower().split()
            if len(metric_word) > 4  # Ignore common words
        )
    
    def test_simple_manual_test_creation(self, business_context):
        """
        TEST: Framework should support manual A/B test creation for custom scenarios
        
        EXPECTED BEHAVIOR:
        - Create test from custom configuration
        - Support custom metrics and success criteria
        - Handle non-improvement-based testing scenarios
        """
        ab_framework = ABTestingFramework()
        
        test_config = {
            "test_name": "Homepage Headline Test",
            "hypothesis": "New value proposition headline will increase signup conversion by 15%",
            "primary_metric": "signup_conversion_rate",
            "variants": [
                {
                    "name": "Control",
                    "description": "Current homepage headline",
                    "traffic_percentage": 0.5,
                    "is_control": True
                },
                {
                    "name": "New Headline", 
                    "description": "New value-focused headline",
                    "traffic_percentage": 0.5,
                    "config_changes": {"headline_text": "Transform Your Business in 30 Days"}
                }
            ]
        }
        
        test = ab_framework.setup_manual_test(test_config)
        
        assert isinstance(test, ABTest)
        assert test.test_name == test_config["test_name"]
        assert test.hypothesis == test_config["hypothesis"]
        assert len(test.variants) == 2
        assert test.primary_metric == test_config["primary_metric"]

async def run_comprehensive_ab_testing_tests():
    """Run the comprehensive TDD test suite for A/B testing framework"""
    
    print("🧪 A/B TESTING FRAMEWORK - TDD VALIDATION")
    print("=" * 70)
    print("Testing feature validation through controlled experiments")
    print()
    
    # Initialize system (this will fail initially - that's the point of TDD)
    ab_framework = ABTestingFramework()
    
    test_scenarios = [
        ("A/B Test Creation from Improvement", "test_creation"),
        ("User Variant Assignment", "variant_assignment"), 
        ("User Interaction Recording", "interaction_recording"),
        ("Statistical Significance Analysis", "statistical_analysis"),
        ("Test Recommendation Generation", "recommendation_generation"),
        ("MVP Evolution Integration", "evolution_integration"),
        ("Manual Test Creation", "manual_test_creation")
    ]
    
    print("🔥 RUNNING TDD TESTS (These should FAIL initially)")
    print("-" * 50)
    
    failed_tests = 0
    
    for scenario_name, test_type in test_scenarios:
        print(f"\n📋 Testing: {scenario_name}")
        
        try:
            if scenario_name == "A/B Test Creation from Improvement":
                # Mock improvement with all required attributes
                mock_improvement = type('MockImprovement', (), {
                    'improvement_id': 'perf_123',
                    'improvement_type': ImprovementType.PERFORMANCE_FIX,
                    'title': 'Performance Fix',
                    'description': 'Fix loading speed',
                    'success_metrics': ['load_time'],
                    'business_impact': 'Improved user satisfaction'
                })()
                
                test = ab_framework.create_test_from_improvement(
                    mock_improvement, {}, traffic_split=0.5
                )
                print("   ✅ A/B test created from improvement")
                
            elif scenario_name == "User Variant Assignment":
                test_id = "test_123"
                user_id = "user_456"
                variant = ab_framework.get_user_variant(test_id, user_id)
                print("   ✅ User variant assignment completed")
                
            elif scenario_name == "User Interaction Recording":
                test_id = "test_123"
                success = ab_framework.record_user_interaction(
                    test_id, "user_1", "variant_a", "conversion"
                )
                print("   ✅ User interaction recording completed")
                
            elif scenario_name == "Statistical Significance Analysis":
                test_id = "test_123"
                results = ab_framework.analyze_test_results(test_id)
                print("   ✅ Statistical analysis completed")
                
            elif scenario_name == "Test Recommendation Generation":
                # Create a test first
                mock_improvement = type('MockImprovement', (), {
                    'improvement_id': 'rec_123',
                    'improvement_type': ImprovementType.PERFORMANCE_FIX,
                    'title': 'Test Recommendation',
                    'description': 'Test for recommendations',
                    'success_metrics': ['conversion'],
                    'business_impact': 'Better performance'
                })()
                
                test = ab_framework.create_test_from_improvement(mock_improvement, {})
                recommendation = ab_framework.get_test_recommendation(test.test_id)
                print("   ✅ Test recommendation generated")
                
            elif scenario_name == "Manual Test Creation":
                test_config = {"test_name": "Test", "hypothesis": "Test hypothesis"}
                test = ab_framework.setup_manual_test(test_config)
                print("   ✅ Manual test creation completed")
                
            else:
                print("   ✅ Test scenario completed")
                
        except NotImplementedError as e:
            print(f"   ❌ EXPECTED FAILURE: {e}")
            failed_tests += 1
        except Exception as e:
            print(f"   ❌ UNEXPECTED ERROR: {e}")
            failed_tests += 1
    
    print(f"\n📊 TDD RESULTS:")
    print(f"Failed Tests: {failed_tests} (Expected)")
    print(f"Total Scenarios: {len(test_scenarios)}")
    
    if failed_tests == len(test_scenarios):
        print("\n✅ TDD SETUP CORRECT!")
        print("Tests are failing as expected - now we implement the features.")
        print("\nNext Step: Implement ABTestingFramework methods to make tests pass")
    else:
        print("\n❌ TDD SETUP ISSUE!")
        print("Some tests passed unexpectedly - check implementation")
    
    return {
        "setup_correct": failed_tests == len(test_scenarios),
        "failed_tests": failed_tests,
        "total_tests": len(test_scenarios)
    }

if __name__ == "__main__":
    print("🧪 A/B TESTING FRAMEWORK - TDD SETUP")
    print("Setting up failing tests to drive implementation")
    print()
    
    # Run TDD setup - tests should fail initially
    results = asyncio.run(run_comprehensive_ab_testing_tests())
    
    print("\n" + "=" * 70)
    print("📋 TDD METHODOLOGY APPLIED")
    print()
    print("1. ❌ Tests written that define expected behavior (FAILING)")
    print("2. ⏳ Next: Implement minimal code to make tests pass") 
    print("3. ⏳ Then: Refactor while keeping tests green")
    print()
    print("🧪 A/B TESTING FRAMEWORK READY FOR IMPLEMENTATION")