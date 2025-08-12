#!/usr/bin/env python3
"""
A/B Testing Framework - Feature Validation for MVP Iteration

FIRST PRINCIPLES IMPLEMENTATION:
1. Founders need to validate improvement hypotheses with real users before full rollout
2. A/B testing must be simple enough for non-technical founders to understand and act on
3. Testing framework should integrate with MVP evolution recommendations for seamless iteration

PARETO FOCUS: 20% implementation that delivers 80% A/B testing value
- Simple feature toggle system with percentage-based splits
- Basic statistical analysis with clear winner determination
- Integration with MVP evolution system for seamless workflow
"""

import asyncio
import json
import logging
import uuid
import hashlib
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

# Import our existing systems
from mvp_evolution_system import MVPEvolutionSystem, MVPImprovement, ImprovementType
from customer_feedback_system import FeedbackResponse, FeedbackType

logger = logging.getLogger(__name__)

class TestStatus(str, Enum):
    """A/B test status"""
    DRAFT = "draft"  # Test configured but not started
    RUNNING = "running"  # Test actively collecting data
    COMPLETED = "completed"  # Test finished, results available
    PAUSED = "paused"  # Test temporarily stopped
    CANCELLED = "cancelled"  # Test stopped without conclusive results

class TestResult(str, Enum):
    """A/B test outcome"""
    VARIANT_A_WINS = "variant_a_wins"  # Control version performs better
    VARIANT_B_WINS = "variant_b_wins"  # Test version performs better
    NO_SIGNIFICANT_DIFFERENCE = "no_significant_difference"  # Statistically inconclusive
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough data collected

@dataclass
class ABTestVariant:
    """Individual variant in an A/B test"""
    variant_id: str
    name: str  # "Control" or descriptive name
    description: str
    traffic_percentage: float  # 0.0-1.0
    is_control: bool = False
    config_changes: Dict[str, Any] = field(default_factory=dict)  # What's different in this variant

@dataclass
class TestMetrics:
    """Metrics collected for a test variant"""
    variant_id: str
    users_exposed: int
    conversions: int  # Primary success metric
    conversion_rate: float
    secondary_metrics: Dict[str, float] = field(default_factory=dict)  # Additional metrics
    user_feedback_scores: List[float] = field(default_factory=list)  # User satisfaction ratings
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class ABTest:
    """Complete A/B test configuration and results"""
    test_id: str
    test_name: str
    hypothesis: str  # What we're testing and expected outcome
    improvement_source: Optional[str] = None  # Reference to MVPImprovement if this came from evolution system
    
    variants: List[ABTestVariant] = field(default_factory=list)
    primary_metric: str = "conversion_rate"  # What metric determines success
    secondary_metrics: List[str] = field(default_factory=list)
    
    status: TestStatus = TestStatus.DRAFT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_sample_size: int = 100  # Minimum users per variant
    confidence_threshold: float = 0.95  # Statistical significance threshold
    
    results: Dict[str, TestMetrics] = field(default_factory=dict)
    winning_variant: Optional[str] = None
    test_result: Optional[TestResult] = None
    statistical_significance: Optional[float] = None
    
    business_context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class TestRecommendation:
    """Recommendation based on A/B test results"""
    test_id: str
    recommendation_type: str  # "rollout", "rollback", "continue_testing", "redesign"
    confidence_level: str  # "high", "medium", "low"
    reasoning: str
    next_actions: List[str]
    business_impact_forecast: str
    generated_at: datetime = field(default_factory=datetime.now)

class ABTestingFramework:
    """
    Simple A/B testing framework for validating MVP improvements with real users.
    
    DELIVERS:
    1. Easy setup of A/B tests from MVP improvement recommendations
    2. Simple metrics collection and statistical analysis
    3. Clear results interpretation and rollout recommendations
    4. Integration with existing MVP evolution workflow
    """
    
    def __init__(self):
        self.active_tests: Dict[str, ABTest] = {}
        self.user_variants: Dict[str, Dict[str, str]] = defaultdict(dict)  # test_id -> user_id -> variant_id
        self.test_data: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))  # test_id -> variant_id -> interactions
        
    def create_test_from_improvement(self, improvement: MVPImprovement, 
                                   business_context: Dict[str, Any],
                                   traffic_split: float = 0.5) -> ABTest:
        """Create A/B test from MVP improvement recommendation"""
        
        test_id = f"test_{improvement.improvement_type.value}_{str(uuid.uuid4())[:8]}"
        
        # Generate hypothesis based on improvement
        hypothesis = self._generate_hypothesis_from_improvement(improvement)
        
        # Create control and test variants
        control_variant = ABTestVariant(
            variant_id=f"{test_id}_control",
            name="Control",
            description="Current implementation (no changes)",
            traffic_percentage=1.0 - traffic_split,
            is_control=True
        )
        
        test_variant = ABTestVariant(
            variant_id=f"{test_id}_test",
            name=f"Improved: {improvement.title}",
            description=improvement.description,
            traffic_percentage=traffic_split,
            is_control=False,
            config_changes={"improvement_id": improvement.improvement_id}
        )
        
        # Determine metrics based on improvement type and success metrics
        primary_metric, secondary_metrics = self._determine_test_metrics(improvement)
        
        # Create test
        test = ABTest(
            test_id=test_id,
            test_name=f"A/B Test: {improvement.title}",
            hypothesis=hypothesis,
            improvement_source=improvement.improvement_id,
            variants=[control_variant, test_variant],
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics,
            business_context=business_context,
            min_sample_size=self._calculate_min_sample_size(business_context)
        )
        
        # Initialize results tracking
        for variant in test.variants:
            test.results[variant.variant_id] = TestMetrics(
                variant_id=variant.variant_id,
                users_exposed=0,
                conversions=0,
                conversion_rate=0.0
            )
        
        self.active_tests[test_id] = test
        return test
        
    def setup_manual_test(self, test_config: Dict[str, Any]) -> ABTest:
        """Setup custom A/B test manually"""
        
        test_id = f"manual_test_{str(uuid.uuid4())[:8]}"
        
        # Create variants from config
        variants = []
        for variant_config in test_config.get("variants", []):
            variant = ABTestVariant(
                variant_id=f"{test_id}_{variant_config['name'].lower().replace(' ', '_')}",
                name=variant_config["name"],
                description=variant_config["description"],
                traffic_percentage=variant_config["traffic_percentage"],
                is_control=variant_config.get("is_control", False),
                config_changes=variant_config.get("config_changes", {})
            )
            variants.append(variant)
        
        test = ABTest(
            test_id=test_id,
            test_name=test_config["test_name"],
            hypothesis=test_config["hypothesis"],
            variants=variants,
            primary_metric=test_config.get("primary_metric", "conversion_rate"),
            secondary_metrics=test_config.get("secondary_metrics", [])
        )
        
        # Initialize results tracking
        for variant in test.variants:
            test.results[variant.variant_id] = TestMetrics(
                variant_id=variant.variant_id,
                users_exposed=0,
                conversions=0,
                conversion_rate=0.0
            )
        
        self.active_tests[test_id] = test
        return test
        
    def start_test(self, test_id: str) -> bool:
        """Start running an A/B test"""
        
        if test_id not in self.active_tests:
            return False
            
        test = self.active_tests[test_id]
        if test.status != TestStatus.DRAFT:
            return False
            
        test.status = TestStatus.RUNNING
        test.start_date = datetime.now()
        
        return True
    
    def record_user_interaction(self, test_id: str, user_id: str, variant_id: str,
                               interaction_type: str, value: Any = None) -> bool:
        """Record user interaction for A/B test metrics"""
        
        if test_id not in self.active_tests:
            return False
            
        test = self.active_tests[test_id]
        if test.status != TestStatus.RUNNING:
            return False
        
        # Record interaction
        interaction = {
            "user_id": user_id,
            "interaction_type": interaction_type,
            "value": value,
            "timestamp": datetime.now()
        }
        
        self.test_data[test_id][variant_id].append(interaction)
        
        # Update metrics
        self._update_variant_metrics(test_id, variant_id)
        
        return True
        
    def get_user_variant(self, test_id: str, user_id: str) -> Optional[str]:
        """Get which variant a user should see for a test"""
        
        if test_id not in self.active_tests:
            return None
            
        # Check if user already assigned
        if user_id in self.user_variants[test_id]:
            return self.user_variants[test_id][user_id]
        
        test = self.active_tests[test_id]
        if test.status != TestStatus.RUNNING:
            return None
        
        # Assign user to variant based on hash and traffic split
        variant = self._assign_user_to_variant(test, user_id)
        self.user_variants[test_id][user_id] = variant.variant_id
        
        # Record exposure
        self.record_user_interaction(test_id, user_id, variant.variant_id, "exposure")
        
        return variant.variant_id
        
    def analyze_test_results(self, test_id: str) -> Dict[str, Any]:
        """Analyze A/B test results with statistical significance"""
        
        if test_id not in self.active_tests:
            return {}
            
        test = self.active_tests[test_id]
        
        # Get current metrics for all variants
        variant_metrics = {}
        for variant_id, metrics in test.results.items():
            variant_metrics[variant_id] = {
                "users_exposed": metrics.users_exposed,
                "conversions": metrics.conversions,
                "conversion_rate": metrics.conversion_rate,
                "sample_size_adequate": metrics.users_exposed >= test.min_sample_size
            }
        
        # Statistical analysis
        statistical_analysis = self._calculate_statistical_significance(test)
        
        # Determine winner
        winning_analysis = self._determine_winning_variant(test, statistical_analysis)
        
        return {
            "test_id": test_id,
            "test_status": test.status.value,
            "variant_metrics": variant_metrics,
            "statistical_significance": statistical_analysis.get("p_value"),
            "confidence_interval": statistical_analysis.get("confidence_interval"),
            "winning_variant": winning_analysis.get("winning_variant"),
            "test_result": winning_analysis.get("test_result"),
            "effect_size": statistical_analysis.get("effect_size"),
            "sample_size_adequate": all(m["sample_size_adequate"] for m in variant_metrics.values())
        }
    
    def get_test_recommendation(self, test_id: str) -> TestRecommendation:
        """Get recommendation based on test results"""
        
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
            
        test = self.active_tests[test_id]
        results = self.analyze_test_results(test_id)
        
        # Generate recommendation based on results
        recommendation_type, confidence_level, reasoning, next_actions, business_impact = self._generate_recommendation_from_results(
            test, results
        )
        
        return TestRecommendation(
            test_id=test_id,
            recommendation_type=recommendation_type,
            confidence_level=confidence_level,
            reasoning=reasoning,
            next_actions=next_actions,
            business_impact_forecast=business_impact
        )
    
    def _generate_hypothesis_from_improvement(self, improvement: MVPImprovement) -> str:
        """Generate test hypothesis from improvement"""
        
        impact_keywords = {
            ImprovementType.PERFORMANCE_FIX: "faster load times and improved user experience",
            ImprovementType.NEW_FEATURE: "increased user engagement and feature adoption",
            ImprovementType.UX_IMPROVEMENT: "better user experience and higher satisfaction",
            ImprovementType.ONBOARDING_OPTIMIZATION: "improved user activation and time-to-value"
        }
        
        expected_impact = impact_keywords.get(improvement.improvement_type, "improved user satisfaction")
        
        return f"Implementing '{improvement.title}' will result in {expected_impact}, leading to measurable improvement in key business metrics."
    
    def _determine_test_metrics(self, improvement: MVPImprovement) -> Tuple[str, List[str]]:
        """Determine appropriate metrics for testing improvement"""
        
        # Primary metric based on improvement type
        primary_metric_map = {
            ImprovementType.PERFORMANCE_FIX: "page_load_satisfaction",
            ImprovementType.NEW_FEATURE: "feature_adoption_rate", 
            ImprovementType.UX_IMPROVEMENT: "user_satisfaction_score",
            ImprovementType.ONBOARDING_OPTIMIZATION: "onboarding_completion_rate",
            ImprovementType.BUSINESS_MODEL_OPTIMIZATION: "conversion_rate"
        }
        
        primary_metric = primary_metric_map.get(improvement.improvement_type, "conversion_rate")
        
        # Secondary metrics
        secondary_metrics = ["user_engagement", "session_duration"]
        
        # Add improvement-specific metrics
        if "speed" in improvement.title.lower() or "performance" in improvement.title.lower():
            secondary_metrics.append("page_load_time")
        if "conversion" in improvement.business_impact.lower():
            secondary_metrics.append("conversion_rate")
        
        return primary_metric, secondary_metrics[:3]  # Limit to 3 secondary metrics
    
    def _calculate_min_sample_size(self, business_context: Dict[str, Any]) -> int:
        """Calculate minimum sample size based on business context"""
        
        monthly_users = business_context.get("monthly_active_users", 1000)
        
        # Base sample size on user volume
        if monthly_users > 10000:
            return 200  # Large user base
        elif monthly_users > 1000:
            return 100  # Medium user base
        else:
            return 50   # Small user base
    
    def _assign_user_to_variant(self, test: ABTest, user_id: str) -> ABTestVariant:
        """Assign user to variant based on consistent hashing"""
        
        # Create consistent hash
        hash_input = f"{test.test_id}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        normalized_hash = (hash_value % 1000) / 1000.0  # 0.0 to 1.0
        
        # Assign based on traffic percentages
        cumulative_percentage = 0.0
        for variant in test.variants:
            cumulative_percentage += variant.traffic_percentage
            if normalized_hash <= cumulative_percentage:
                return variant
                
        # Fallback to last variant
        return test.variants[-1]
    
    def _update_variant_metrics(self, test_id: str, variant_id: str):
        """Update metrics for a variant based on recorded interactions"""
        
        interactions = self.test_data[test_id][variant_id]
        
        # Count exposures and conversions
        exposures = len([i for i in interactions if i["interaction_type"] == "exposure"])
        conversions = len([i for i in interactions if i["interaction_type"] == "conversion"])
        
        # Update metrics
        metrics = self.active_tests[test_id].results[variant_id]
        metrics.users_exposed = exposures
        metrics.conversions = conversions
        metrics.conversion_rate = conversions / exposures if exposures > 0 else 0.0
        metrics.last_updated = datetime.now()
    
    def _calculate_statistical_significance(self, test: ABTest) -> Dict[str, Any]:
        """Calculate statistical significance between variants"""
        
        if len(test.variants) != 2:
            return {"error": "Statistical analysis only supports 2-variant tests"}
        
        control_variant = next(v for v in test.variants if v.is_control)
        test_variant = next(v for v in test.variants if not v.is_control)
        
        control_metrics = test.results[control_variant.variant_id]
        test_metrics = test.results[test_variant.variant_id]
        
        # Simple statistical significance calculation
        n1, x1 = control_metrics.users_exposed, control_metrics.conversions
        n2, x2 = test_metrics.users_exposed, test_metrics.conversions
        
        if n1 < 10 or n2 < 10:
            return {
                "p_value": None,
                "confidence_interval": None,
                "effect_size": None,
                "error": "Insufficient sample size for statistical analysis"
            }
        
        # Calculate proportions
        p1 = x1 / n1 if n1 > 0 else 0
        p2 = x2 / n2 if n2 > 0 else 0
        
        # Simplified z-test for proportions
        pooled_p = (x1 + x2) / (n1 + n2) if (n1 + n2) > 0 else 0
        
        if pooled_p == 0 or pooled_p == 1:
            return {
                "p_value": 1.0,
                "effect_size": 0,
                "confidence_interval": [p1 - p2, p1 - p2]
            }
        
        se = math.sqrt(pooled_p * (1 - pooled_p) * (1/n1 + 1/n2))
        z_score = (p2 - p1) / se if se > 0 else 0
        
        # Approximate p-value (simplified)
        p_value = 2 * (1 - abs(z_score) / 3.0) if abs(z_score) < 3 else 0.001
        p_value = max(0.001, min(1.0, p_value))
        
        effect_size = p2 - p1
        
        return {
            "p_value": p_value,
            "effect_size": effect_size,
            "confidence_interval": [effect_size - 0.1, effect_size + 0.1],  # Simplified CI
            "z_score": z_score
        }
    
    def _determine_winning_variant(self, test: ABTest, statistical_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine winning variant from statistical analysis"""
        
        if len(test.variants) != 2:
            return {"test_result": TestResult.INSUFFICIENT_DATA}
        
        control_variant = next(v for v in test.variants if v.is_control)
        test_variant = next(v for v in test.variants if not v.is_control)
        
        control_metrics = test.results[control_variant.variant_id]
        test_metrics = test.results[test_variant.variant_id]
        
        # Check sample size
        if control_metrics.users_exposed < test.min_sample_size or test_metrics.users_exposed < test.min_sample_size:
            return {"test_result": TestResult.INSUFFICIENT_DATA}
        
        p_value = statistical_analysis.get("p_value")
        effect_size = statistical_analysis.get("effect_size", 0)
        
        if p_value is None:
            return {"test_result": TestResult.INSUFFICIENT_DATA}
        
        # Determine winner based on statistical significance
        if p_value <= (1 - test.confidence_threshold):  # Statistically significant
            if effect_size > 0:  # Test variant is better
                return {
                    "winning_variant": test_variant.variant_id,
                    "test_result": TestResult.VARIANT_B_WINS
                }
            elif effect_size < 0:  # Control is better
                return {
                    "winning_variant": control_variant.variant_id,
                    "test_result": TestResult.VARIANT_A_WINS
                }
        
        return {"test_result": TestResult.NO_SIGNIFICANT_DIFFERENCE}
    
    def _generate_recommendation_from_results(self, test: ABTest, results: Dict[str, Any]) -> Tuple[str, str, str, List[str], str]:
        """Generate recommendation from test results"""
        
        test_result = results.get("test_result")
        statistical_significance = results.get("statistical_significance")
        sample_size_adequate = results.get("sample_size_adequate", False)
        
        if not sample_size_adequate:
            return (
                "continue_testing",
                "low",
                f"Insufficient sample size. Need at least {test.min_sample_size} users per variant for reliable results.",
                ["Continue running test to reach minimum sample size", "Consider increasing traffic allocation if timeline is critical"],
                "Test results will become more reliable with larger sample size, enabling confident business decisions."
            )
        
        if test_result == TestResult.VARIANT_B_WINS:
            confidence = "high" if statistical_significance and statistical_significance <= 0.05 else "medium"
            return (
                "rollout",
                confidence,
                f"Test variant shows statistically significant improvement. The new implementation outperforms the control version.",
                [
                    "Implement the test variant for all users",
                    "Monitor key metrics post-rollout for 2 weeks", 
                    "Document learnings for future improvements"
                ],
                "Expected positive impact on user experience and business metrics based on test results. Full rollout should deliver similar improvements at scale."
            )
        
        elif test_result == TestResult.VARIANT_A_WINS:
            return (
                "rollback",
                "high",
                "Control version performs better than the test variant. The proposed improvement did not deliver expected benefits.",
                [
                    "Maintain current implementation (control version)",
                    "Analyze why the improvement didn't work as expected",
                    "Consider alternative approaches to address the original problem"
                ],
                "Avoiding the test variant prevents potential negative impact on business metrics. Focus resources on alternative improvement approaches."
            )
        
        elif test_result == TestResult.NO_SIGNIFICANT_DIFFERENCE:
            return (
                "continue_testing",
                "medium", 
                "No statistically significant difference detected between variants. Results are inconclusive.",
                [
                    "Consider running test longer to increase statistical power",
                    "Evaluate if the improvement is worth implementing despite neutral results",
                    "Consider testing a more dramatic variation of the improvement"
                ],
                "Neutral results suggest the improvement may not deliver significant business impact. Consider resource allocation to higher-impact improvements."
            )
        
        else:  # INSUFFICIENT_DATA
            return (
                "continue_testing",
                "low",
                "Insufficient data to draw meaningful conclusions from test results.",
                [
                    "Continue collecting data until minimum sample size is reached",
                    "Verify test is properly configured and recording interactions",
                    "Consider increasing traffic allocation to accelerate data collection"
                ],
                "Test needs more data to provide reliable guidance for business decisions."
            )

async def demonstrate_ab_testing_framework():
    """Demonstrate the A/B testing framework with MVP evolution integration"""
    
    print("🧪 A/B TESTING FRAMEWORK DEMONSTRATION")
    print("=" * 70)
    print("Feature validation through controlled experiments")
    print()
    
    ab_framework = ABTestingFramework()
    
    # Create sample improvement from MVP Evolution System
    sample_improvement = type('MockImprovement', (), {
        'improvement_id': 'perf_dashboard_001',
        'improvement_type': ImprovementType.PERFORMANCE_FIX,
        'title': 'Optimize Dashboard Loading Speed',
        'description': 'Implement caching and query optimization to reduce dashboard load time',
        'business_impact': 'Improved user satisfaction and reduced churn from performance issues',
        'success_metrics': ['Page load time < 3 seconds', 'User satisfaction rating increase'],
        'confidence_score': 0.9
    })()
    
    business_context = {
        "business_model": "b2b_saas",
        "industry": "healthcare",
        "monthly_active_users": 500,
        "customers_acquired": 25
    }
    
    print("🔬 CREATING A/B TEST FROM MVP IMPROVEMENT")
    print("-" * 50)
    
    # Create test from improvement
    test = ab_framework.create_test_from_improvement(
        sample_improvement, business_context, traffic_split=0.4
    )
    
    print(f"🎯 Test ID: {test.test_id}")
    print(f"📊 Test Name: {test.test_name}")
    print(f"💡 Hypothesis: {test.hypothesis}")
    print(f"📈 Primary Metric: {test.primary_metric}")
    print(f"🔀 Traffic Split: {[v.traffic_percentage for v in test.variants]}")
    print()
    
    # Start test
    ab_framework.start_test(test.test_id)
    print(f"▶️  Test Status: {test.status.value}")
    print()
    
    print("👥 SIMULATING USER INTERACTIONS")
    print("-" * 30)
    
    # Simulate user interactions with different outcomes
    control_variant = next(v for v in test.variants if v.is_control)
    test_variant = next(v for v in test.variants if not v.is_control)
    
    # Simulate scenario where test variant performs better
    print("Simulating users experiencing control vs test variants...")
    
    # Control group: 60 users, 12 conversions (20%)
    for i in range(60):
        user_id = f"control_user_{i}"
        ab_framework.record_user_interaction(test.test_id, user_id, control_variant.variant_id, "exposure")
        if i < 12:  # 20% conversion rate
            ab_framework.record_user_interaction(test.test_id, user_id, control_variant.variant_id, "conversion")
    
    # Test group: 40 users, 16 conversions (40%) 
    for i in range(40):
        user_id = f"test_user_{i}"
        ab_framework.record_user_interaction(test.test_id, user_id, test_variant.variant_id, "exposure")
        if i < 16:  # 40% conversion rate
            ab_framework.record_user_interaction(test.test_id, user_id, test_variant.variant_id, "conversion")
    
    print(f"✅ Recorded interactions for {60 + 40} users")
    print()
    
    print("📊 ANALYZING TEST RESULTS")
    print("-" * 25)
    
    # Analyze results
    results = ab_framework.analyze_test_results(test.test_id)
    
    print("📈 VARIANT PERFORMANCE:")
    for variant_id, metrics in results["variant_metrics"].items():
        variant_name = "Control" if "control" in variant_id else "Test Variant"
        print(f"  {variant_name}:")
        print(f"    Users: {metrics['users_exposed']}")
        print(f"    Conversions: {metrics['conversions']}")
        print(f"    Conversion Rate: {metrics['conversion_rate']:.1%}")
        print(f"    Sample Size OK: {'✅' if metrics['sample_size_adequate'] else '❌'}")
    print()
    
    print("📊 STATISTICAL ANALYSIS:")
    print(f"  Statistical Significance: {results.get('statistical_significance', 'N/A')}")
    print(f"  Winning Variant: {results.get('winning_variant', 'None')}")
    print(f"  Test Result: {results.get('test_result', 'Inconclusive')}")
    print(f"  Effect Size: {results.get('effect_size', 0):.1%}")
    print()
    
    print("🎯 TEST RECOMMENDATION")
    print("-" * 20)
    
    # Get recommendation
    recommendation = ab_framework.get_test_recommendation(test.test_id)
    
    print(f"📋 Recommendation: {recommendation.recommendation_type.upper()}")
    print(f"🎪 Confidence Level: {recommendation.confidence_level.title()}")
    print(f"💭 Reasoning: {recommendation.reasoning}")
    print()
    print("🚀 Next Actions:")
    for i, action in enumerate(recommendation.next_actions, 1):
        print(f"  {i}. {action}")
    print()
    print(f"📈 Business Impact: {recommendation.business_impact_forecast}")
    print()
    
    # Demonstrate user variant assignment consistency
    print("🔄 USER VARIANT ASSIGNMENT CONSISTENCY")
    print("-" * 40)
    
    test_user = "consistent_user_123"
    variant_1 = ab_framework.get_user_variant(test.test_id, test_user)
    variant_2 = ab_framework.get_user_variant(test.test_id, test_user)
    
    print(f"User {test_user} assigned to: {variant_1}")
    print(f"Second request returns: {variant_2}")
    print(f"Consistency: {'✅ Same variant' if variant_1 == variant_2 else '❌ Different variant'}")
    print()
    
    print("✅ A/B TESTING FRAMEWORK DEMONSTRATION COMPLETE")
    print()
    print("🎉 FOUNDERS NOW GET:")
    print("• Automated A/B test creation from MVP improvement recommendations")
    print("• Simple user variant assignment with consistent experience")
    print("• Statistical analysis with clear winner determination")
    print("• Actionable recommendations for rollout decisions")
    print("• Integration with MVP evolution workflow for data-driven iteration")
    print("• Hypothesis testing to validate improvement assumptions")

if __name__ == "__main__":
    print("🧪 A/B TESTING FRAMEWORK")
    print("Feature validation through controlled experiments")
    print()
    
    # Demonstrate the system
    asyncio.run(demonstrate_ab_testing_framework())