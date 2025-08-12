#!/usr/bin/env python3
"""
MVP Evolution System - Systematic Iteration for Product-Market Fit

FIRST PRINCIPLES IMPLEMENTATION:
1. Product-market fit requires systematic MVP iteration based on real customer data
2. Founders need specific, actionable improvement recommendations, not generic advice
3. MVP evolution must align with business model and customer validation insights

PARETO FOCUS: 20% implementation that delivers 80% MVP iteration value
- Performance analysis from customer feedback
- Specific improvement recommendations with business impact
- Prioritized evolution plans aligned with business goals
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import Counter
import re

# Import our existing systems
from customer_feedback_system import CustomerFeedbackSystem, FeedbackResponse, FeedbackType
from customer_validation_dashboard import CustomerValidationDashboard, ValidationDashboard
from customer_acquisition_system import BusinessContext

logger = logging.getLogger(__name__)

class ImprovementType(str, Enum):
    """Types of MVP improvements"""
    FEATURE_ENHANCEMENT = "feature_enhancement"  # Improve existing features
    NEW_FEATURE = "new_feature"  # Add completely new feature
    UX_IMPROVEMENT = "ux_improvement"  # User experience fixes
    PERFORMANCE_FIX = "performance_fix"  # Speed/reliability improvements
    BUSINESS_MODEL_OPTIMIZATION = "business_model_optimization"  # Pricing/monetization changes
    ONBOARDING_OPTIMIZATION = "onboarding_optimization"  # User onboarding improvements

class ImprovementPriority(str, Enum):
    """Priority levels for improvements"""
    CRITICAL = "critical"  # Must fix immediately (blocks customers)
    HIGH = "high"  # High business impact, should do next
    MEDIUM = "medium"  # Good improvement, can wait
    LOW = "low"  # Nice to have, low priority

@dataclass
class MVPImprovement:
    """Individual MVP improvement recommendation"""
    improvement_id: str
    improvement_type: ImprovementType
    priority: ImprovementPriority
    title: str
    description: str
    business_impact: str  # Expected business impact
    effort_estimate: str  # Implementation effort estimate
    success_metrics: List[str]  # How to measure success
    implementation_guidance: str  # Specific steps to implement
    based_on_feedback: List[str]  # Customer feedback that led to this
    confidence_score: float  # 0-1 confidence in recommendation
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class MVPEvolutionPlan:
    """Complete MVP evolution plan with prioritized improvements"""
    plan_id: str
    business_context: Dict[str, Any]
    current_mvp_analysis: Dict[str, Any]  # Analysis of current MVP state
    improvements: List[MVPImprovement]  # All recommended improvements
    next_sprint_recommendations: List[str]  # Top 3-5 items for next sprint
    expected_impact: str  # Overall expected business impact
    iteration_focus: str  # Main focus for this iteration cycle
    generated_at: datetime = field(default_factory=datetime.now)

class MVPEvolutionSystem:
    """
    System that analyzes customer feedback and validation data to suggest
    specific, actionable MVP improvements for achieving product-market fit.
    
    DELIVERS:
    1. Analysis of current MVP performance based on customer data
    2. Specific improvement recommendations with business impact
    3. Prioritized evolution plan aligned with business goals
    4. Implementation guidance founders can act on immediately
    """
    
    def __init__(self):
        self.business_impact_weights = self._initialize_business_weights()
        self.improvement_templates = self._initialize_improvement_templates()
        
    def analyze_mvp_performance(self, business_context: Dict[str, Any],
                               validation_dashboard: ValidationDashboard,
                               feedback_data: List[FeedbackResponse]) -> Dict[str, Any]:
        """Analyze current MVP performance based on validation data"""
        
        analysis = {
            "performance_issues": [],
            "user_satisfaction": {},
            "feature_feedback": {},
            "business_metrics": {},
            "pain_points": [],
            "feature_requests": [],
            "competitive_advantages": [],
            "churn_risks": []
        }
        
        # Analyze validation dashboard metrics
        if validation_dashboard:
            analysis["business_metrics"] = {
                "validation_score": validation_dashboard.overall_validation_score,
                "confidence_level": validation_dashboard.confidence_level,
                "total_metrics": len(validation_dashboard.metrics)
            }
            
            # Extract insights from dashboard
            for insight in validation_dashboard.key_insights:
                if "rating" in insight.lower() or "satisfaction" in insight.lower():
                    analysis["user_satisfaction"]["dashboard_insight"] = insight
                elif "conversion" in insight.lower() or "acquisition" in insight.lower():
                    analysis["business_metrics"]["acquisition_insight"] = insight
        
        # Analyze customer feedback
        if feedback_data:
            # Performance issues from feedback
            performance_keywords = ["slow", "loading", "speed", "performance", "lag", "timeout", "error"]
            for feedback in feedback_data:
                if feedback.text:
                    text_lower = feedback.text.lower()
                    if any(keyword in text_lower for keyword in performance_keywords):
                        analysis["performance_issues"].append(feedback.text)
            
            # Feature-specific feedback
            feature_mentions = {}
            for feedback in feedback_data:
                if feedback.feature_mentioned:
                    if feedback.feature_mentioned not in feature_mentions:
                        feature_mentions[feedback.feature_mentioned] = []
                    feature_mentions[feedback.feature_mentioned].append({
                        "rating": feedback.rating,
                        "sentiment": feedback.sentiment,
                        "text": feedback.text
                    })
            analysis["feature_feedback"] = feature_mentions
            
            # Extract feature requests and pain points
            request_keywords = ["need", "want", "wish", "should", "could", "missing", "add"]
            pain_keywords = ["frustrating", "difficult", "confusing", "complicated", "annoying", "broken"]
            
            for feedback in feedback_data:
                if feedback.text:
                    text_lower = feedback.text.lower()
                    if any(keyword in text_lower for keyword in request_keywords):
                        analysis["feature_requests"].append(feedback.text)
                    if any(keyword in text_lower for keyword in pain_keywords):
                        analysis["pain_points"].append(feedback.text)
                    
            # User satisfaction analysis
            ratings = [f.rating for f in feedback_data if f.rating is not None]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                analysis["user_satisfaction"]["average_rating"] = avg_rating
                analysis["user_satisfaction"]["rating_distribution"] = Counter(ratings)
            
            sentiments = [f.sentiment for f in feedback_data if f.sentiment]
            if sentiments:
                sentiment_counts = Counter(sentiments)
                analysis["user_satisfaction"]["sentiment_distribution"] = sentiment_counts
        
        # Business context analysis
        business_model = business_context.get("business_model", "")
        customers_acquired = business_context.get("customers_acquired", 0)
        
        # Identify competitive advantages and risks
        if "b2b" in business_model:
            if customers_acquired < 5:
                analysis["churn_risks"].append("Low customer base increases churn risk in B2B model")
            if validation_dashboard and validation_dashboard.overall_validation_score < 60:
                analysis["churn_risks"].append("Below-average validation score suggests retention challenges")
        
        return analysis
        
    def generate_improvement_recommendations(self, mvp_analysis: Dict[str, Any],
                                           business_context: Dict[str, Any],
                                           feedback_data: List[FeedbackResponse]) -> List[MVPImprovement]:
        """Generate specific MVP improvement recommendations"""
        
        improvements = []
        
        # 1. Performance improvements
        performance_issues = mvp_analysis.get("performance_issues", [])
        if performance_issues:
            # Extract common performance patterns
            loading_issues = [issue for issue in performance_issues if "loading" in issue.lower() or "speed" in issue.lower()]
            if loading_issues:
                improvements.append(
                    MVPImprovement(
                        improvement_id=f"perf_{str(uuid.uuid4())[:8]}",
                        improvement_type=ImprovementType.PERFORMANCE_FIX,
                        priority=ImprovementPriority.HIGH,  # Will be re-prioritized
                        title="Optimize Application Performance",
                        description="Address slow loading times and performance bottlenecks reported by customers",
                        business_impact="Improved customer satisfaction and reduced churn risk from performance frustration",
                        effort_estimate="3-5 days",
                        success_metrics=["Page load time < 3 seconds", "Customer satisfaction rating +0.5 points"],
                        implementation_guidance="Profile application performance, optimize database queries, implement caching, compress assets",
                        based_on_feedback=loading_issues[:3],  # Top 3 performance complaints
                        confidence_score=len(loading_issues) * 0.2 + 0.4  # Higher confidence with more complaints
                    )
                )
        
        # 2. Feature requests
        feature_requests = mvp_analysis.get("feature_requests", [])
        if feature_requests:
            # Extract most requested features
            integration_requests = [req for req in feature_requests if "integration" in req.lower() or "api" in req.lower()]
            automation_requests = [req for req in feature_requests if "automat" in req.lower() or "schedul" in req.lower()]
            
            if integration_requests:
                industry = business_context.get("industry", "business")
                improvements.append(
                    MVPImprovement(
                        improvement_id=f"integration_{str(uuid.uuid4())[:8]}",
                        improvement_type=ImprovementType.NEW_FEATURE,
                        priority=ImprovementPriority.HIGH,
                        title=f"Third-party Integration for {industry.title()}",
                        description="Implement integrations with popular tools used by target customers",
                        business_impact="Reduced manual work for customers, competitive differentiation, higher customer retention",
                        effort_estimate="2-4 weeks",
                        success_metrics=["Integration usage by 60%+ customers", "Data entry time reduced 50%"],
                        implementation_guidance="Research most-used tools in industry, implement API connections, create integration dashboard",
                        based_on_feedback=integration_requests[:2],
                        confidence_score=0.8
                    )
                )
            
            if automation_requests:
                improvements.append(
                    MVPImprovement(
                        improvement_id=f"automation_{str(uuid.uuid4())[:8]}",
                        improvement_type=ImprovementType.FEATURE_ENHANCEMENT,
                        priority=ImprovementPriority.MEDIUM,
                        title="Automated Workflow Features",
                        description="Add automation capabilities for repetitive customer workflows",
                        business_impact="Increased customer efficiency and satisfaction, reduced time-to-value",
                        effort_estimate="1-2 weeks",
                        success_metrics=["Workflow automation usage by 40%+ customers", "Time saved per customer per week: 2+ hours"],
                        implementation_guidance="Identify most common repetitive tasks, implement scheduling/automation features, create user-friendly automation setup",
                        based_on_feedback=automation_requests[:2],
                        confidence_score=0.75
                    )
                )
        
        # 3. UX/Onboarding improvements
        pain_points = mvp_analysis.get("pain_points", [])
        if pain_points:
            onboarding_issues = [pain for pain in pain_points if "onboard" in pain.lower() or "setup" in pain.lower() or "confusing" in pain.lower()]
            if onboarding_issues:
                improvements.append(
                    MVPImprovement(
                        improvement_id=f"onboarding_{str(uuid.uuid4())[:8]}",
                        improvement_type=ImprovementType.ONBOARDING_OPTIMIZATION,
                        priority=ImprovementPriority.HIGH,
                        title="Streamline User Onboarding Experience",
                        description="Simplify and improve the initial user setup and onboarding process",
                        business_impact="Reduced time-to-value, higher trial-to-paid conversion, improved user activation",
                        effort_estimate="1-2 weeks",
                        success_metrics=["Setup time reduced to under 30 minutes", "Onboarding completion rate >85%"],
                        implementation_guidance="Create step-by-step guided onboarding, add progress indicators, provide sample data, create interactive tutorials",
                        based_on_feedback=onboarding_issues[:2],
                        confidence_score=0.85
                    )
                )
        
        # 4. Business model optimizations
        user_satisfaction = mvp_analysis.get("user_satisfaction", {})
        avg_rating = user_satisfaction.get("average_rating", 0)
        
        # Check for pricing concerns in feedback
        pricing_feedback = [f.text for f in feedback_data if f.text and any(term in f.text.lower() for term in ["price", "cost", "expensive", "cheap", "value"])]
        if pricing_feedback:
            improvements.append(
                MVPImprovement(
                    improvement_id=f"pricing_{str(uuid.uuid4())[:8]}",
                    improvement_type=ImprovementType.BUSINESS_MODEL_OPTIMIZATION,
                    priority=ImprovementPriority.MEDIUM,
                    title="Optimize Pricing and Value Proposition",
                    description="Review and optimize pricing strategy based on customer feedback",
                    business_impact="Improved customer acquisition rate, better price-value alignment, reduced price objections",
                    effort_estimate="1 week research + 2-3 days implementation",
                    success_metrics=["Price objection rate reduced 50%", "Trial-to-paid conversion +15%"],
                    implementation_guidance="Analyze competitor pricing, survey customers on value perception, test alternative pricing tiers, communicate value better",
                    based_on_feedback=pricing_feedback[:2],
                    confidence_score=0.7
                )
            )
        
        return improvements
        
    def prioritize_improvements(self, improvements: List[MVPImprovement],
                               business_context: Dict[str, Any]) -> List[MVPImprovement]:
        """Prioritize improvements based on business impact and effort"""
        
        business_model = business_context.get("business_model", "")
        customers_acquired = business_context.get("customers_acquired", 0)
        industry = business_context.get("industry", "")
        
        for improvement in improvements:
            # Calculate priority score
            priority_score = 0
            
            # Business impact scoring
            if improvement.improvement_type == ImprovementType.PERFORMANCE_FIX:
                priority_score += 40  # Performance issues affect all customers
                if len(improvement.based_on_feedback) >= 3:
                    priority_score += 20  # Multiple complaints = critical
                    
            elif improvement.improvement_type == ImprovementType.NEW_FEATURE:
                if "integration" in improvement.title.lower():
                    priority_score += 35  # High value for business tools
                else:
                    priority_score += 25
                    
            elif improvement.improvement_type == ImprovementType.ONBOARDING_OPTIMIZATION:
                if customers_acquired < 10:
                    priority_score += 35  # Critical for early-stage startups
                else:
                    priority_score += 25
                    
            elif improvement.improvement_type == ImprovementType.BUSINESS_MODEL_OPTIMIZATION:
                priority_score += 20  # Important but not urgent
            
            # Business model specific adjustments
            if "b2b" in business_model:
                # B2B prioritizes customer retention over acquisition
                if improvement.improvement_type in [ImprovementType.PERFORMANCE_FIX, ImprovementType.FEATURE_ENHANCEMENT]:
                    priority_score += 15
            else:
                # B2C prioritizes user experience and onboarding
                if improvement.improvement_type in [ImprovementType.UX_IMPROVEMENT, ImprovementType.ONBOARDING_OPTIMIZATION]:
                    priority_score += 15
            
            # Confidence score adjustment
            priority_score += improvement.confidence_score * 10
            
            # Effort consideration (prefer quick wins when appropriate)
            if "1-2 week" in improvement.effort_estimate or "days" in improvement.effort_estimate:
                priority_score += 10  # Quick wins
            
            # Set priority based on score
            if priority_score >= 70:
                improvement.priority = ImprovementPriority.CRITICAL
            elif priority_score >= 50:
                improvement.priority = ImprovementPriority.HIGH
            elif priority_score >= 30:
                improvement.priority = ImprovementPriority.MEDIUM
            else:
                improvement.priority = ImprovementPriority.LOW
        
        # Sort by priority and confidence
        priority_order = {
            ImprovementPriority.CRITICAL: 4,
            ImprovementPriority.HIGH: 3,
            ImprovementPriority.MEDIUM: 2,
            ImprovementPriority.LOW: 1
        }
        
        improvements.sort(key=lambda x: (priority_order[x.priority], x.confidence_score), reverse=True)
        
        return improvements
        
    def create_evolution_plan(self, business_context: Dict[str, Any],
                             validation_dashboard: ValidationDashboard,
                             feedback_data: List[FeedbackResponse]) -> MVPEvolutionPlan:
        """Create complete MVP evolution plan"""
        
        plan_id = f"evolution_plan_{str(uuid.uuid4())[:8]}"
        
        # Analyze current MVP performance
        mvp_analysis = self.analyze_mvp_performance(business_context, validation_dashboard, feedback_data)
        
        # Generate improvement recommendations
        improvements = self.generate_improvement_recommendations(mvp_analysis, business_context, feedback_data)
        
        # Prioritize improvements
        prioritized_improvements = self.prioritize_improvements(improvements, business_context)
        
        # Generate next sprint recommendations
        next_sprint = self._generate_sprint_recommendations(prioritized_improvements, business_context)
        
        # Determine iteration focus
        iteration_focus = self._determine_iteration_focus(prioritized_improvements, business_context, mvp_analysis)
        
        # Calculate expected impact
        expected_impact = self._calculate_expected_impact(prioritized_improvements, business_context, validation_dashboard)
        
        return MVPEvolutionPlan(
            plan_id=plan_id,
            business_context=business_context,
            current_mvp_analysis=mvp_analysis,
            improvements=prioritized_improvements,
            next_sprint_recommendations=next_sprint,
            expected_impact=expected_impact,
            iteration_focus=iteration_focus
        )
        
    def get_next_sprint_plan(self, evolution_plan: MVPEvolutionPlan) -> List[str]:
        """Get specific recommendations for next development sprint"""
        return evolution_plan.next_sprint_recommendations
        
    def _initialize_business_weights(self) -> Dict[str, Dict[str, float]]:
        """Initialize business model specific weights for prioritization"""
        
        return {
            "b2b_saas": {
                "customer_retention": 0.4,
                "feature_requests": 0.3,
                "performance": 0.2,
                "onboarding": 0.1
            },
            "b2c_saas": {
                "user_experience": 0.35,
                "onboarding": 0.25,
                "performance": 0.25,
                "feature_requests": 0.15
            }
        }
    
    def _initialize_improvement_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize improvement templates for different scenarios"""
        
        return {
            "performance_critical": {
                "priority": ImprovementPriority.CRITICAL,
                "business_impact": "Customer retention and satisfaction",
                "success_metrics": ["Performance metrics improved", "Customer complaints reduced"]
            },
            "feature_integration": {
                "priority": ImprovementPriority.HIGH,
                "business_impact": "Competitive advantage and customer efficiency",
                "success_metrics": ["Integration adoption rate", "Customer workflow efficiency"]
            }
        }
    
    def _generate_sprint_recommendations(self, improvements: List[MVPImprovement], 
                                       business_context: Dict[str, Any]) -> List[str]:
        """Generate 3-5 specific recommendations for next sprint"""
        
        recommendations = []
        
        # Focus on top priority improvements that can fit in a sprint
        sprint_improvements = [imp for imp in improvements[:5] if imp.priority in [ImprovementPriority.CRITICAL, ImprovementPriority.HIGH]]
        
        for improvement in sprint_improvements:
            if improvement.improvement_type == ImprovementType.PERFORMANCE_FIX:
                recommendations.append(f"Fix performance issues: {improvement.title} - {improvement.effort_estimate}")
            elif improvement.improvement_type == ImprovementType.NEW_FEATURE:
                recommendations.append(f"Implement high-value feature: {improvement.title} - {improvement.effort_estimate}")
            elif improvement.improvement_type == ImprovementType.ONBOARDING_OPTIMIZATION:
                recommendations.append(f"Streamline onboarding: {improvement.title} - {improvement.effort_estimate}")
            else:
                recommendations.append(f"{improvement.improvement_type.value.replace('_', ' ').title()}: {improvement.title}")
        
        # Add quick wins if space allows
        if len(recommendations) < 4:
            quick_wins = [imp for imp in improvements if "day" in imp.effort_estimate and imp not in sprint_improvements]
            for quick_win in quick_wins[:2]:
                recommendations.append(f"Quick win: {quick_win.title} - {quick_win.effort_estimate}")
        
        return recommendations[:5]  # Max 5 items for realistic sprint
    
    def _determine_iteration_focus(self, improvements: List[MVPImprovement], 
                                 business_context: Dict[str, Any], 
                                 mvp_analysis: Dict[str, Any]) -> str:
        """Determine main focus for this iteration cycle"""
        
        if not improvements:
            return "Data collection and customer feedback analysis - insufficient data for specific recommendations"
        
        # Analyze improvement types to determine focus
        improvement_types = [imp.improvement_type for imp in improvements[:5]]  # Top 5
        type_counts = Counter(improvement_types)
        
        business_model = business_context.get("business_model", "")
        industry = business_context.get("industry", "")
        validation_score = mvp_analysis.get("business_metrics", {}).get("validation_score", 50)
        
        # Determine primary focus
        if type_counts.get(ImprovementType.PERFORMANCE_FIX, 0) >= 2:
            return f"Performance optimization focus for {industry} {business_model} - address critical customer experience issues affecting retention"
        elif type_counts.get(ImprovementType.NEW_FEATURE, 0) >= 2:
            return f"Feature expansion focus - build competitive advantages in {industry} market through customer-requested integrations and capabilities"
        elif type_counts.get(ImprovementType.ONBOARDING_OPTIMIZATION, 0) >= 1:
            return f"Customer success and onboarding focus - improve time-to-value and activation rates for {business_model}"
        elif validation_score < 50:
            return f"Product-market fit discovery - systematic testing and iteration to find {industry} market fit"
        else:
            return f"Growth optimization focus - scale and optimize successful {business_model} model in {industry}"
    
    def _calculate_expected_impact(self, improvements: List[MVPImprovement], 
                                 business_context: Dict[str, Any],
                                 validation_dashboard: Optional[ValidationDashboard]) -> str:
        """Calculate expected business impact from implementing improvements"""
        
        if not improvements:
            return "Limited impact expected - need more customer feedback data to generate actionable improvements"
        
        business_model = business_context.get("business_model", "")
        customers_acquired = business_context.get("customers_acquired", 0)
        
        # Count improvement types for impact calculation
        critical_improvements = len([imp for imp in improvements if imp.priority == ImprovementPriority.CRITICAL])
        high_improvements = len([imp for imp in improvements if imp.priority == ImprovementPriority.HIGH])
        
        impact_components = []
        
        if critical_improvements >= 2:
            impact_components.append("Major customer satisfaction improvement expected")
        if high_improvements >= 3:
            impact_components.append("Significant competitive advantage development")
        
        # Business model specific impacts
        if "b2b" in business_model:
            if customers_acquired < 10:
                impact_components.append("Customer retention and expansion focus critical for B2B growth")
            else:
                impact_components.append("Customer success optimization for B2B account expansion")
        else:
            impact_components.append("User experience and acquisition optimization for B2C scale")
        
        # Validation score impact
        if validation_dashboard and validation_dashboard.overall_validation_score < 60:
            impact_components.append("Expected 15-25 point validation score improvement through systematic fixes")
        
        return ". ".join(impact_components) + f" - implementing top priority improvements should drive measurable business metrics improvement within 4-6 weeks"

async def demonstrate_mvp_evolution_system():
    """Demonstrate the MVP evolution system with real business scenarios"""
    
    print("🔄 MVP EVOLUTION SYSTEM DEMONSTRATION")
    print("=" * 70)
    print("Systematic MVP iteration based on customer feedback analysis")
    print()
    
    evolution_system = MVPEvolutionSystem()
    
    # Test scenario: Healthcare B2B SaaS with real feedback issues
    business_context = {
        "business_model": "b2b_saas",
        "industry": "healthcare",
        "target_audience": "medical practices with 10-50 doctors",
        "value_proposition": "automated HIPAA compliance management",
        "key_features": ["compliance dashboard", "audit trails", "patient reporting"],
        "current_stage": "mvp_launched",
        "customers_acquired": 4,
        "monthly_revenue": 800
    }
    
    # Realistic feedback data with common SaaS issues
    feedback_data = [
        FeedbackResponse(
            response_id="f1", widget_id="w1", user_id="u1", session_id="s1",
            feedback_type=FeedbackType.RATING, rating=3,
            text="Compliance dashboard loads very slowly, sometimes 30+ seconds",
            sentiment="neutral", feature_mentioned="dashboard"
        ),
        FeedbackResponse(
            response_id="f2", widget_id="w2", user_id="u2", session_id="s2",
            feedback_type=FeedbackType.OPEN_TEXT,
            text="Really need Epic EMR integration, manual data entry is killing our workflow",
            sentiment="negative", feature_mentioned="integration"
        ),
        FeedbackResponse(
            response_id="f3", widget_id="w3", user_id="u3", session_id="s3",
            feedback_type=FeedbackType.RATING, rating=4,
            text="Love the audit reports but need automated monthly email scheduling",
            sentiment="positive", feature_mentioned="reporting"
        ),
        FeedbackResponse(
            response_id="f4", widget_id="w4", user_id="u4", session_id="s4",
            feedback_type=FeedbackType.OPEN_TEXT,
            text="Onboarding was confusing, took 4 hours to setup our first audit",
            sentiment="negative", feature_mentioned="onboarding"
        ),
        FeedbackResponse(
            response_id="f5", widget_id="w5", user_id="u5", session_id="s5",
            feedback_type=FeedbackType.RATING, rating=2,
            text="App crashes when generating large compliance reports",
            sentiment="negative", feature_mentioned="reporting"
        )
    ]
    
    # Generate validation dashboard
    dashboard_system = CustomerValidationDashboard()
    validation_dashboard = dashboard_system.generate_dashboard(business_context)
    
    print("📊 CREATING MVP EVOLUTION PLAN")
    print("-" * 40)
    
    # Create complete evolution plan
    evolution_plan = evolution_system.create_evolution_plan(
        business_context,
        validation_dashboard, 
        feedback_data
    )
    
    print(f"🎯 Evolution Plan ID: {evolution_plan.plan_id}")
    print(f"📈 Total Improvements: {len(evolution_plan.improvements)}")
    print(f"🎪 Iteration Focus: {evolution_plan.iteration_focus}")
    print()
    
    # Show MVP performance analysis
    print("📊 CURRENT MVP ANALYSIS:")
    analysis = evolution_plan.current_mvp_analysis
    print(f"  • Performance Issues: {len(analysis.get('performance_issues', []))}")
    print(f"  • Feature Requests: {len(analysis.get('feature_requests', []))}")
    print(f"  • Pain Points: {len(analysis.get('pain_points', []))}")
    print(f"  • User Satisfaction: {analysis.get('user_satisfaction', {}).get('average_rating', 'N/A')}")
    print()
    
    # Show top improvement recommendations
    print("🚀 TOP IMPROVEMENT RECOMMENDATIONS:")
    for i, improvement in enumerate(evolution_plan.improvements[:4], 1):
        priority_icon = {
            ImprovementPriority.CRITICAL: "🚨",
            ImprovementPriority.HIGH: "⚡",
            ImprovementPriority.MEDIUM: "📈",
            ImprovementPriority.LOW: "💡"
        }[improvement.priority]
        
        print(f"  {i}. {priority_icon} {improvement.title} ({improvement.priority.value.upper()})")
        print(f"     Impact: {improvement.business_impact}")
        print(f"     Effort: {improvement.effort_estimate}")
        print(f"     Confidence: {improvement.confidence_score:.0%}")
        print()
    
    # Show next sprint plan
    print("🎯 NEXT SPRINT RECOMMENDATIONS:")
    sprint_recommendations = evolution_system.get_next_sprint_plan(evolution_plan)
    for i, recommendation in enumerate(sprint_recommendations, 1):
        print(f"  {i}. {recommendation}")
    print()
    
    # Show expected impact
    print("📊 EXPECTED BUSINESS IMPACT:")
    print(f"  {evolution_plan.expected_impact}")
    print()
    
    print("✅ MVP EVOLUTION SYSTEM DEMONSTRATION COMPLETE")
    print()
    print("🎉 FOUNDERS NOW GET:")
    print("• Systematic analysis of MVP performance from customer data")
    print("• Specific, prioritized improvement recommendations")
    print("• Clear implementation guidance and effort estimates")
    print("• Sprint-ready development plans")
    print("• Business impact forecasting and success metrics")
    print("• Data-driven product-market fit optimization")

if __name__ == "__main__":
    print("🔄 MVP EVOLUTION SYSTEM")
    print("Systematic MVP iteration for product-market fit achievement")
    print()
    
    # Demonstrate the system
    asyncio.run(demonstrate_mvp_evolution_system())