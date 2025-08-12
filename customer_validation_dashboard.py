#!/usr/bin/env python3
"""
Customer Validation Dashboard - Unified Business Intelligence

FIRST PRINCIPLES IMPLEMENTATION:
1. Founders need centralized visibility into all validation metrics
2. Dashboard must show actionable insights, not just raw numbers  
3. Visual representation makes data more digestible and actionable

PARETO FOCUS: 20% implementation that delivers 80% dashboard value
- Unified view of acquisition + feedback data
- Simple, founder-friendly visualizations
- Actionable insights and next steps
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

# Import our existing systems
from customer_acquisition_system import CustomerAcquisitionSystem, BusinessContext
from customer_feedback_system import CustomerFeedbackSystem, FeedbackResponse, FeedbackType

logger = logging.getLogger(__name__)

class DashboardMetricType(str, Enum):
    """Types of metrics displayed on dashboard"""
    CUSTOMER_ACQUISITION = "customer_acquisition"
    FEEDBACK_ANALYSIS = "feedback_analysis" 
    VALIDATION_SCORE = "validation_score"
    BUSINESS_HEALTH = "business_health"
    NEXT_ACTIONS = "next_actions"

class VisualizationType(str, Enum):
    """Types of visualizations for metrics"""
    NUMBER_CARD = "number_card"  # Single number with trend
    PROGRESS_BAR = "progress_bar"  # Progress towards goal
    SIMPLE_CHART = "simple_chart"  # Basic line/bar chart
    METRIC_LIST = "metric_list"  # List of key metrics
    ACTION_LIST = "action_list"  # List of recommended actions

@dataclass
class DashboardMetric:
    """Individual metric displayed on dashboard"""
    metric_id: str
    metric_type: DashboardMetricType
    title: str
    value: Any  # Can be number, string, list, etc.
    visualization: VisualizationType
    trend: Optional[str] = None  # "up", "down", "neutral"
    target: Optional[float] = None  # Target value if applicable
    description: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class ValidationDashboard:
    """Complete validation dashboard for founders"""
    dashboard_id: str
    business_context: Dict[str, Any]
    metrics: List[DashboardMetric]
    overall_validation_score: float  # 0-100 score
    confidence_level: str  # "low", "medium", "high"
    key_insights: List[str]  # Top 3-5 insights
    recommended_actions: List[str]  # Next steps to take
    generated_at: datetime = field(default_factory=datetime.now)

class CustomerValidationDashboard:
    """
    Unified dashboard system that combines customer acquisition and feedback data
    into actionable business validation insights for founders.
    
    DELIVERS:
    1. Unified view of all customer validation metrics
    2. Simple visualizations founders can understand quickly
    3. Actionable insights and next steps based on data
    4. Overall validation score to track progress
    """
    
    def __init__(self):
        self.acquisition_system = CustomerAcquisitionSystem()
        self.feedback_system = CustomerFeedbackSystem()
        self.business_benchmarks = self._initialize_business_benchmarks()
        
    def generate_dashboard(self, business_context: Dict[str, Any], 
                          acquisition_data: Dict[str, Any] = None,
                          feedback_data: List[FeedbackResponse] = None) -> ValidationDashboard:
        """Generate complete validation dashboard from business context and data"""
        
        dashboard_id = f"dashboard_{str(uuid.uuid4())[:8]}"
        
        # Generate all metrics
        metrics = []
        
        # 1. Validation Score Metrics
        validation_metrics = self._generate_validation_metrics(business_context, acquisition_data, feedback_data)
        metrics.extend(validation_metrics)
        
        # 2. Customer Acquisition Metrics
        if acquisition_data:
            acquisition_metrics = self._generate_acquisition_metrics(acquisition_data, business_context)
            metrics.extend(acquisition_metrics)
        
        # 3. Feedback Analysis Metrics
        if feedback_data:
            feedback_metrics = self._generate_feedback_metrics(feedback_data, business_context)
            metrics.extend(feedback_metrics)
        
        # 4. Business Health Metrics
        health_metrics = self._generate_health_metrics(business_context, acquisition_data, feedback_data)
        metrics.extend(health_metrics)
        
        # Calculate overall validation score
        overall_score = self.calculate_validation_score(metrics)
        confidence_level = self._determine_confidence_level(overall_score, metrics)
        
        # Generate insights and actions
        key_insights = self.get_key_insights(metrics, business_context)
        recommended_actions = self._generate_recommended_actions(metrics, business_context, overall_score)
        
        return ValidationDashboard(
            dashboard_id=dashboard_id,
            business_context=business_context,
            metrics=metrics,
            overall_validation_score=overall_score,
            confidence_level=confidence_level,
            key_insights=key_insights,
            recommended_actions=recommended_actions
        )
        
    def calculate_validation_score(self, metrics: List[DashboardMetric]) -> float:
        """Calculate overall validation score from individual metrics"""
        
        score_components = {
            "customer_acquisition": 0,
            "feedback_quality": 0,
            "business_health": 0,
            "data_availability": 0
        }
        
        weights = {
            "customer_acquisition": 0.35,  # 35% - customers are critical
            "feedback_quality": 0.30,     # 30% - feedback shows product-market fit
            "business_health": 0.25,      # 25% - overall business indicators
            "data_availability": 0.10     # 10% - having data is better than no data
        }
        
        # Analyze metrics for scoring
        acquisition_metrics = [m for m in metrics if m.metric_type == DashboardMetricType.CUSTOMER_ACQUISITION]
        feedback_metrics = [m for m in metrics if m.metric_type == DashboardMetricType.FEEDBACK_ANALYSIS]
        
        # Customer acquisition score
        if acquisition_metrics:
            # Score based on customer conversion and growth
            customers_metric = next((m for m in acquisition_metrics if "customer" in m.title.lower()), None)
            if customers_metric and isinstance(customers_metric.value, (int, float)):
                if customers_metric.value >= 10:
                    score_components["customer_acquisition"] = 85
                elif customers_metric.value >= 5:
                    score_components["customer_acquisition"] = 70
                elif customers_metric.value >= 2:
                    score_components["customer_acquisition"] = 55
                elif customers_metric.value >= 1:
                    score_components["customer_acquisition"] = 40
                else:
                    score_components["customer_acquisition"] = 20
            else:
                score_components["customer_acquisition"] = 30  # Some acquisition activity
        else:
            score_components["customer_acquisition"] = 10  # No acquisition data
            
        # Feedback quality score  
        if feedback_metrics:
            rating_metric = next((m for m in feedback_metrics if "rating" in m.title.lower()), None)
            if rating_metric and isinstance(rating_metric.value, (int, float)):
                if rating_metric.value >= 4.5:
                    score_components["feedback_quality"] = 90
                elif rating_metric.value >= 4.0:
                    score_components["feedback_quality"] = 75
                elif rating_metric.value >= 3.5:
                    score_components["feedback_quality"] = 60
                elif rating_metric.value >= 3.0:
                    score_components["feedback_quality"] = 45
                else:
                    score_components["feedback_quality"] = 25
            else:
                score_components["feedback_quality"] = 40  # Some feedback activity
        else:
            score_components["feedback_quality"] = 15  # No feedback data
            
        # Business health score (based on stage and progress)
        business_stage = self._get_business_stage_score(metrics)
        score_components["business_health"] = business_stage
        
        # Data availability score
        data_score = min(100, len(metrics) * 15)  # Up to 100 based on data richness
        score_components["data_availability"] = data_score
        
        # Calculate weighted final score
        final_score = sum(
            score_components[component] * weights[component]
            for component in score_components
        )
        
        return round(final_score, 1)
    
    def generate_dashboard_html(self, dashboard: ValidationDashboard) -> str:
        """Generate HTML for rendering the dashboard"""
        
        # Generate metric HTML sections
        metrics_html = ""
        for metric in dashboard.metrics:
            metrics_html += self._generate_metric_html(metric)
        
        # Generate insights HTML
        insights_html = ""
        for i, insight in enumerate(dashboard.key_insights, 1):
            insights_html += f'<div class="insight-item"><span class="insight-number">{i}</span>{insight}</div>'
        
        # Generate actions HTML
        actions_html = ""
        for i, action in enumerate(dashboard.recommended_actions, 1):
            actions_html += f'<div class="action-item"><span class="action-number">{i}</span>{action}</div>'
        
        # Determine score color
        score_color = self._get_score_color(dashboard.overall_validation_score)
        confidence_color = {"low": "#f56565", "medium": "#ed8936", "high": "#48bb78"}[dashboard.confidence_level]
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Startup Validation Dashboard - {dashboard.business_context.get('industry', 'Business').title()}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .dashboard-container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .dashboard-header {{
            background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .dashboard-title {{
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .dashboard-subtitle {{
            font-size: 16px;
            opacity: 0.8;
        }}
        
        .validation-score {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 20px 0;
        }}
        
        .score-circle {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: {score_color};
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 32px;
            font-weight: 700;
            position: relative;
        }}
        
        .score-label {{
            position: absolute;
            bottom: -30px;
            font-size: 14px;
            color: rgba(255,255,255,0.8);
        }}
        
        .confidence-badge {{
            background: {confidence_color};
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 20px;
            text-transform: uppercase;
        }}
        
        .dashboard-content {{
            padding: 30px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .metric-card {{
            background: #f7fafc;
            border-radius: 12px;
            padding: 24px;
            border-left: 4px solid #4299e1;
            transition: transform 0.2s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}
        
        .metric-title {{
            font-size: 14px;
            font-weight: 600;
            color: #4a5568;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: 700;
            color: #1a202c;
            margin-bottom: 4px;
        }}
        
        .metric-description {{
            font-size: 14px;
            color: #718096;
            line-height: 1.4;
        }}
        
        .insights-section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 20px;
            font-weight: 700;
            color: #1a202c;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }}
        
        .section-icon {{
            font-size: 24px;
            margin-right: 10px;
        }}
        
        .insight-item, .action-item {{
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            display: flex;
            align-items: flex-start;
            line-height: 1.5;
        }}
        
        .insight-number, .action-number {{
            background: #4299e1;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
            margin-right: 12px;
            flex-shrink: 0;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #4299e1, #3182ce);
            transition: width 0.3s ease;
        }}
        
        .dashboard-footer {{
            background: #f7fafc;
            padding: 20px 30px;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            font-size: 12px;
            color: #718096;
        }}
        
        @media (max-width: 768px) {{
            .dashboard-container {{
                margin: 10px;
                border-radius: 12px;
            }}
            
            .dashboard-header {{
                padding: 20px;
            }}
            
            .dashboard-title {{
                font-size: 24px;
            }}
            
            .metrics-grid {{
                grid-template-columns: 1fr;
                gap: 15px;
            }}
            
            .dashboard-content {{
                padding: 20px;
            }}
            
            .score-circle {{
                width: 100px;
                height: 100px;
                font-size: 28px;
            }}
        }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h1 class="dashboard-title">Startup Validation Dashboard</h1>
            <p class="dashboard-subtitle">{dashboard.business_context.get('industry', 'Business').title()} • {dashboard.business_context.get('business_model', '').replace('_', ' ').title()}</p>
            
            <div class="validation-score">
                <div class="score-circle">
                    {dashboard.overall_validation_score}
                    <div class="score-label">Validation Score</div>
                </div>
                <div class="confidence-badge">{dashboard.confidence_level} confidence</div>
            </div>
        </div>
        
        <div class="dashboard-content">
            <div class="metrics-grid">
                {metrics_html}
            </div>
            
            <div class="insights-section">
                <h2 class="section-title">
                    <span class="section-icon">💡</span>
                    Key Insights
                </h2>
                {insights_html}
            </div>
            
            <div class="actions-section">
                <h2 class="section-title">
                    <span class="section-icon">🎯</span>
                    Recommended Actions
                </h2>
                {actions_html}
            </div>
        </div>
        
        <div class="dashboard-footer">
            Generated on {dashboard.generated_at.strftime('%B %d, %Y at %I:%M %p')} • Dashboard ID: {dashboard.dashboard_id}
        </div>
    </div>
    
    <script>
        // Simple interactivity
        document.addEventListener('DOMContentLoaded', function() {{
            // Animate progress bars
            const progressBars = document.querySelectorAll('.progress-fill');
            progressBars.forEach(bar => {{
                const width = bar.style.width;
                bar.style.width = '0%';
                setTimeout(() => bar.style.width = width, 300);
            }});
            
            // Add hover effects to cards
            const cards = document.querySelectorAll('.metric-card, .insight-item, .action-item');
            cards.forEach(card => {{
                card.addEventListener('mouseenter', function() {{
                    this.style.transform = 'translateY(-2px)';
                }});
                card.addEventListener('mouseleave', function() {{
                    this.style.transform = 'translateY(0)';
                }});
            }});
        }});
    </script>
</body>
</html>"""
        
        return html_template
        
    def get_key_insights(self, metrics: List[DashboardMetric], business_context: Dict[str, Any]) -> List[str]:
        """Extract key insights from dashboard metrics"""
        
        insights = []
        
        # Analyze customer acquisition
        acquisition_metrics = [m for m in metrics if m.metric_type == DashboardMetricType.CUSTOMER_ACQUISITION]
        if acquisition_metrics:
            customers_metric = next((m for m in acquisition_metrics if "customer" in m.title.lower()), None)
            conversion_metric = next((m for m in acquisition_metrics if "conversion" in m.title.lower()), None)
            
            if customers_metric and isinstance(customers_metric.value, (int, float)):
                if customers_metric.value >= 5:
                    insights.append(f"🎉 Strong customer traction with {customers_metric.value} customers acquired - you're building something people want")
                elif customers_metric.value >= 2:
                    insights.append(f"⚡ Early customer validation with {customers_metric.value} customers - focus on understanding what's working")
                elif customers_metric.value >= 1:
                    insights.append(f"🚀 First customer milestone reached - critical step completed, now scale the approach")
                else:
                    insights.append("🎯 Customer acquisition is the immediate priority - your MVP needs real users to validate the business")
            
            if conversion_metric and isinstance(conversion_metric.value, (int, float)):
                if conversion_metric.value >= 0.15:  # 15%+ conversion
                    insights.append(f"💎 Excellent {conversion_metric.value*100:.1f}% conversion rate suggests strong product-market fit")
                elif conversion_metric.value >= 0.05:  # 5%+ conversion
                    insights.append(f"📈 Solid {conversion_metric.value*100:.1f}% conversion rate with room for optimization")
                else:
                    insights.append(f"🔧 {conversion_metric.value*100:.1f}% conversion needs improvement - focus on messaging and value proposition")
        
        # Analyze feedback patterns
        feedback_metrics = [m for m in metrics if m.metric_type == DashboardMetricType.FEEDBACK_ANALYSIS]
        if feedback_metrics:
            rating_metric = next((m for m in feedback_metrics if "rating" in m.title.lower()), None)
            sentiment_metric = next((m for m in feedback_metrics if "sentiment" in m.title.lower()), None)
            
            if rating_metric and isinstance(rating_metric.value, (int, float)):
                if rating_metric.value >= 4.0:
                    insights.append(f"⭐ High user satisfaction ({rating_metric.value:.1f}/5) indicates strong product-market fit")
                elif rating_metric.value >= 3.0:
                    insights.append(f"🔄 Mixed feedback ({rating_metric.value:.1f}/5) - identify and address top pain points")
                else:
                    insights.append(f"🚨 Low ratings ({rating_metric.value:.1f}/5) require immediate product improvements")
            
            if sentiment_metric:
                insights.append("💬 Customer feedback is providing valuable insights for product development")
        
        # Business model specific insights
        business_model = business_context.get("business_model", "")
        industry = business_context.get("industry", "")
        
        if "b2b" in business_model:
            insights.append(f"🏢 B2B {industry} businesses typically have longer sales cycles - focus on demonstrating clear ROI")
        elif "b2c" in business_model:
            insights.append(f"👥 B2C {industry} success depends on user experience and viral growth - optimize for retention")
        
        # Data availability insights
        if len(metrics) >= 6:
            insights.append("📊 Rich data collection enables data-driven decisions - you're measuring the right things")
        elif len(metrics) <= 3:
            insights.append("📈 Limited data visibility - implement more tracking to make informed business decisions")
        
        return insights[:5]  # Return top 5 insights
    
    def get_recommended_actions(self, dashboard: ValidationDashboard) -> List[str]:
        """Generate specific next actions based on dashboard data"""
        return self._generate_recommended_actions(dashboard.metrics, dashboard.business_context, dashboard.overall_validation_score)
    
    def _initialize_business_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Initialize industry and business model benchmarks"""
        
        return {
            "b2b_saas": {
                "target_customers_month_1": 2,
                "target_customers_month_3": 10,
                "target_conversion_rate": 0.05,  # 5%
                "target_rating": 4.0
            },
            "b2c_saas": {
                "target_customers_month_1": 50,
                "target_customers_month_3": 200,
                "target_conversion_rate": 0.02,  # 2%
                "target_rating": 4.2
            }
        }
    
    def _generate_validation_metrics(self, business_context: Dict[str, Any], 
                                   acquisition_data: Dict[str, Any] = None,
                                   feedback_data: List[FeedbackResponse] = None) -> List[DashboardMetric]:
        """Generate validation score metrics"""
        
        # Calculate preliminary validation score
        temp_metrics = []  # We'll calculate this properly in the main method
        validation_score = 45  # Default starting score
        
        if acquisition_data and acquisition_data.get("customers_acquired", 0) > 0:
            validation_score += 25
        if feedback_data and len(feedback_data) > 5:
            validation_score += 20
        
        validation_score = min(100, validation_score)
        
        return [
            DashboardMetric(
                metric_id="validation_score",
                metric_type=DashboardMetricType.VALIDATION_SCORE,
                title="Overall Validation Score",
                value=validation_score,
                visualization=VisualizationType.NUMBER_CARD,
                description="Combined score based on customer acquisition, feedback quality, and business health",
                target=75.0
            )
        ]
    
    def _generate_acquisition_metrics(self, acquisition_data: Dict[str, Any], 
                                    business_context: Dict[str, Any]) -> List[DashboardMetric]:
        """Generate customer acquisition metrics"""
        
        metrics = []
        
        # Customers acquired
        customers_acquired = acquisition_data.get("customers_acquired", 0)
        business_model = business_context.get("business_model", "b2c_saas")
        target_customers = self.business_benchmarks.get(business_model, {}).get("target_customers_month_1", 5)
        
        metrics.append(
            DashboardMetric(
                metric_id="customers_acquired",
                metric_type=DashboardMetricType.CUSTOMER_ACQUISITION,
                title="Customers Acquired",
                value=customers_acquired,
                visualization=VisualizationType.NUMBER_CARD,
                target=target_customers,
                description=f"Total paying customers in {acquisition_data.get('time_period', 'period')}"
            )
        )
        
        # Conversion rate
        emails_sent = acquisition_data.get("emails_sent", 0)
        responses = acquisition_data.get("responses_received", 0)
        if emails_sent > 0:
            response_rate = responses / emails_sent
            metrics.append(
                DashboardMetric(
                    metric_id="email_response_rate",
                    metric_type=DashboardMetricType.CUSTOMER_ACQUISITION,
                    title="Email Response Rate",
                    value=response_rate,
                    visualization=VisualizationType.PROGRESS_BAR,
                    target=0.15,  # 15% target
                    description=f"{responses} responses from {emails_sent} emails"
                )
            )
        
        # Customer conversion rate
        trials = acquisition_data.get("trials_started", 0)
        if trials > 0 and customers_acquired > 0:
            conversion_rate = customers_acquired / trials
            metrics.append(
                DashboardMetric(
                    metric_id="trial_conversion_rate", 
                    metric_type=DashboardMetricType.CUSTOMER_ACQUISITION,
                    title="Trial to Customer Conversion",
                    value=conversion_rate,
                    visualization=VisualizationType.PROGRESS_BAR,
                    target=0.20,  # 20% target
                    description=f"{customers_acquired} customers from {trials} trials"
                )
            )
        
        return metrics
    
    def _generate_feedback_metrics(self, feedback_data: List[FeedbackResponse], 
                                 business_context: Dict[str, Any]) -> List[DashboardMetric]:
        """Generate feedback analysis metrics"""
        
        metrics = []
        
        if not feedback_data:
            return metrics
            
        # Average rating
        ratings = [f.rating for f in feedback_data if f.rating is not None]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            metrics.append(
                DashboardMetric(
                    metric_id="average_rating",
                    metric_type=DashboardMetricType.FEEDBACK_ANALYSIS,
                    title="Average User Rating",
                    value=avg_rating,
                    visualization=VisualizationType.NUMBER_CARD,
                    target=4.0,
                    description=f"Based on {len(ratings)} user ratings"
                )
            )
        
        # Sentiment analysis
        sentiments = [f.sentiment for f in feedback_data if f.sentiment]
        if sentiments:
            sentiment_counts = Counter(sentiments)
            total_sentiment = len(sentiments)
            positive_ratio = sentiment_counts.get("positive", 0) / total_sentiment
            
            metrics.append(
                DashboardMetric(
                    metric_id="positive_sentiment",
                    metric_type=DashboardMetricType.FEEDBACK_ANALYSIS,
                    title="Positive Sentiment",
                    value=positive_ratio,
                    visualization=VisualizationType.PROGRESS_BAR,
                    target=0.70,  # 70% positive target
                    description=f"{sentiment_counts.get('positive', 0)} positive out of {total_sentiment} responses"
                )
            )
        
        # Total feedback responses
        metrics.append(
            DashboardMetric(
                metric_id="total_feedback",
                metric_type=DashboardMetricType.FEEDBACK_ANALYSIS,
                title="Total Feedback Responses", 
                value=len(feedback_data),
                visualization=VisualizationType.NUMBER_CARD,
                description="Total feedback responses collected"
            )
        )
        
        return metrics
    
    def _generate_health_metrics(self, business_context: Dict[str, Any],
                               acquisition_data: Dict[str, Any] = None,
                               feedback_data: List[FeedbackResponse] = None) -> List[DashboardMetric]:
        """Generate business health indicators"""
        
        metrics = []
        
        # Data collection health
        data_sources = 0
        if acquisition_data:
            data_sources += 1
        if feedback_data:
            data_sources += 1
        
        metrics.append(
            DashboardMetric(
                metric_id="data_collection",
                metric_type=DashboardMetricType.BUSINESS_HEALTH,
                title="Data Collection Health",
                value=data_sources,
                visualization=VisualizationType.NUMBER_CARD,
                target=3,  # Want multiple data sources
                description="Number of active data collection systems"
            )
        )
        
        # Business stage progress
        stage = business_context.get("current_stage", "idea")
        stage_scores = {
            "idea": 10,
            "mvp_development": 30,
            "mvp_launched": 60,
            "customers_acquired": 80,
            "scaling": 95
        }
        
        stage_score = stage_scores.get(stage, 10)
        metrics.append(
            DashboardMetric(
                metric_id="business_stage",
                metric_type=DashboardMetricType.BUSINESS_HEALTH,
                title="Business Stage Progress",
                value=stage_score,
                visualization=VisualizationType.PROGRESS_BAR,
                target=100,
                description=f"Current stage: {stage.replace('_', ' ').title()}"
            )
        )
        
        return metrics
    
    def _generate_recommended_actions(self, metrics: List[DashboardMetric], 
                                    business_context: Dict[str, Any],
                                    validation_score: float) -> List[str]:
        """Generate specific recommended actions based on dashboard data"""
        
        actions = []
        
        # Score-based recommendations
        if validation_score < 40:
            actions.append("🚨 URGENT: Focus on customer acquisition - your business needs real users to validate the concept")
            actions.append("💡 Identify your ideal customer profile and launch targeted outreach campaigns immediately")
        elif validation_score < 60:
            actions.append("📈 Scale your customer acquisition - build on early traction with systematic outreach")
            actions.append("🔍 Analyze successful customer patterns to optimize your targeting and messaging")
        else:
            actions.append("🚀 Strong validation foundation - focus on scaling and optimizing your growth systems")
            actions.append("📊 Implement advanced analytics to identify expansion and optimization opportunities")
        
        # Acquisition-specific actions
        acquisition_metrics = [m for m in metrics if m.metric_type == DashboardMetricType.CUSTOMER_ACQUISITION]
        customers_metric = next((m for m in acquisition_metrics if "customer" in m.title.lower()), None)
        
        if not customers_metric or (customers_metric.value if isinstance(customers_metric.value, (int, float)) else 0) == 0:
            actions.append("🎯 Launch customer acquisition campaign using industry-specific channels and messaging")
        elif customers_metric and isinstance(customers_metric.value, (int, float)) and customers_metric.value < 5:
            actions.append("⚡ Double down on acquisition channels that delivered your first customers")
        
        # Feedback-specific actions
        feedback_metrics = [m for m in metrics if m.metric_type == DashboardMetricType.FEEDBACK_ANALYSIS]
        if not feedback_metrics:
            actions.append("📝 Implement feedback collection widgets to understand customer satisfaction and needs")
        else:
            rating_metric = next((m for m in feedback_metrics if "rating" in m.title.lower()), None)
            if rating_metric and isinstance(rating_metric.value, (int, float)) and rating_metric.value < 3.5:
                actions.append("🔧 Address customer pain points - low ratings indicate product improvements needed")
        
        # Business model specific actions
        business_model = business_context.get("business_model", "")
        industry = business_context.get("industry", "")
        
        if "b2b" in business_model:
            actions.append(f"🏢 Focus on ROI demonstration for {industry} businesses - prepare case studies and success metrics")
        elif "b2c" in business_model:
            actions.append(f"👥 Optimize user onboarding and retention for {industry} consumers - focus on user experience")
        
        # Data collection actions
        if len(metrics) < 5:
            actions.append("📊 Expand data collection - implement more tracking to enable data-driven decisions")
        
        return actions[:6]  # Return top 6 actions
    
    def _get_business_stage_score(self, metrics: List[DashboardMetric]) -> float:
        """Calculate business stage score based on available metrics"""
        
        base_score = 30  # For having an MVP
        
        # Boost for customer acquisition
        acquisition_metrics = [m for m in metrics if m.metric_type == DashboardMetricType.CUSTOMER_ACQUISITION]
        if acquisition_metrics:
            base_score += 25
            
        # Boost for feedback collection
        feedback_metrics = [m for m in metrics if m.metric_type == DashboardMetricType.FEEDBACK_ANALYSIS]
        if feedback_metrics:
            base_score += 20
            
        # Boost for data richness
        if len(metrics) >= 6:
            base_score += 15
            
        return min(90, base_score)
    
    def _determine_confidence_level(self, validation_score: float, metrics: List[DashboardMetric]) -> str:
        """Determine confidence level based on score and data quality"""
        
        data_quality = len(metrics) >= 5  # Rich data
        
        if validation_score >= 70 and data_quality:
            return "high"
        elif validation_score >= 50 or data_quality:
            return "medium"
        else:
            return "low"
    
    def _generate_metric_html(self, metric: DashboardMetric) -> str:
        """Generate HTML for individual metric card"""
        
        if metric.visualization == VisualizationType.NUMBER_CARD:
            value_display = f"{metric.value}"
            if isinstance(metric.value, float):
                if metric.value < 1:
                    value_display = f"{metric.value*100:.1f}%"
                else:
                    value_display = f"{metric.value:.1f}"
            
            return f"""
            <div class="metric-card">
                <div class="metric-title">{metric.title}</div>
                <div class="metric-value">{value_display}</div>
                <div class="metric-description">{metric.description or ''}</div>
            </div>
            """
            
        elif metric.visualization == VisualizationType.PROGRESS_BAR:
            if isinstance(metric.value, (int, float)) and metric.target:
                percentage = min(100, (metric.value / metric.target) * 100)
            else:
                percentage = metric.value * 100 if isinstance(metric.value, float) and metric.value <= 1 else 50
            
            value_display = f"{metric.value*100:.1f}%" if isinstance(metric.value, float) and metric.value <= 1 else f"{metric.value}"
            
            return f"""
            <div class="metric-card">
                <div class="metric-title">{metric.title}</div>
                <div class="metric-value">{value_display}</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {percentage}%"></div>
                </div>
                <div class="metric-description">{metric.description or ''}</div>
            </div>
            """
            
        else:
            return f"""
            <div class="metric-card">
                <div class="metric-title">{metric.title}</div>
                <div class="metric-value">{metric.value}</div>
                <div class="metric-description">{metric.description or ''}</div>
            </div>
            """
    
    def _get_score_color(self, score: float) -> str:
        """Get color for validation score"""
        
        if score >= 75:
            return "#48bb78"  # Green
        elif score >= 50:
            return "#ed8936"  # Orange
        else:
            return "#f56565"  # Red

async def demonstrate_validation_dashboard():
    """Demonstrate the validation dashboard with real business scenarios"""
    
    print("📊 CUSTOMER VALIDATION DASHBOARD DEMONSTRATION")
    print("=" * 70)
    print("Unified business intelligence for startup validation")
    print()
    
    dashboard_system = CustomerValidationDashboard()
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Healthcare B2B SaaS with Traction",
            "business_context": {
                "business_model": "b2b_saas",
                "industry": "healthcare",
                "target_audience": "medical practices with 10-50 doctors",
                "value_proposition": "automated HIPAA compliance management",
                "key_features": ["compliance dashboard", "audit trails", "patient reporting"],
                "current_stage": "mvp_launched"
            },
            "acquisition_data": {
                "emails_sent": 200,
                "responses_received": 35,
                "demos_scheduled": 12,
                "trials_started": 8,
                "customers_acquired": 3,
                "time_period": "last_30_days"
            },
            "feedback_data": [
                FeedbackResponse(
                    response_id="f1", widget_id="w1", user_id="u1", session_id="s1",
                    feedback_type=FeedbackType.RATING, rating=4,
                    text="Great compliance features", sentiment="positive"
                ),
                FeedbackResponse(
                    response_id="f2", widget_id="w2", user_id="u2", session_id="s2", 
                    feedback_type=FeedbackType.NPS, rating=8,
                    text="Would recommend to other practices", sentiment="positive"
                ),
                FeedbackResponse(
                    response_id="f3", widget_id="w3", user_id="u3", session_id="s3",
                    feedback_type=FeedbackType.RATING, rating=3,
                    text="Useful but complex interface", sentiment="neutral"
                )
            ]
        },
        {
            "name": "Education B2C SaaS Early Stage", 
            "business_context": {
                "business_model": "b2c_saas",
                "industry": "education",
                "target_audience": "K-12 teachers",
                "value_proposition": "automated student progress tracking",
                "key_features": ["progress tracking", "parent communication"],
                "current_stage": "mvp_development"
            },
            "acquisition_data": None,
            "feedback_data": None
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"📋 SCENARIO {i}: {scenario['name']}")
        print("-" * 60)
        
        # Generate dashboard
        dashboard = dashboard_system.generate_dashboard(
            scenario["business_context"],
            acquisition_data=scenario["acquisition_data"],
            feedback_data=scenario["feedback_data"]
        )
        
        print(f"🎯 Dashboard ID: {dashboard.dashboard_id}")
        print(f"📊 Validation Score: {dashboard.overall_validation_score}/100")
        print(f"🎪 Confidence Level: {dashboard.confidence_level.title()}")
        print(f"📈 Total Metrics: {len(dashboard.metrics)}")
        print()
        
        # Show key metrics
        print("📊 KEY METRICS:")
        for metric in dashboard.metrics[:4]:  # Show top 4 metrics
            value_display = f"{metric.value}"
            if isinstance(metric.value, float) and metric.value < 1:
                value_display = f"{metric.value*100:.1f}%"
            elif isinstance(metric.value, float):
                value_display = f"{metric.value:.1f}"
            print(f"  • {metric.title}: {value_display}")
        print()
        
        # Show key insights
        print("💡 KEY INSIGHTS:")
        for j, insight in enumerate(dashboard.key_insights[:3], 1):
            print(f"  {j}. {insight}")
        print()
        
        # Show recommended actions
        print("🎯 RECOMMENDED ACTIONS:")
        for j, action in enumerate(dashboard.recommended_actions[:3], 1):
            print(f"  {j}. {action}")
        print()
        
        # Generate HTML dashboard
        html_dashboard = dashboard_system.generate_dashboard_html(dashboard)
        html_file = f"validation_dashboard_{dashboard.dashboard_id}.html"
        
        with open(html_file, 'w') as f:
            f.write(html_dashboard)
        
        print(f"💾 HTML Dashboard Generated: {html_file}")
        print(f"📄 HTML Size: {len(html_dashboard):,} characters")
        print()
        
        print("-" * 60)
        print()
    
    print("✅ VALIDATION DASHBOARD SYSTEM DEMONSTRATION COMPLETE")
    print()
    print("🎉 FOUNDERS NOW GET:")
    print("• Unified validation dashboard combining all metrics")
    print("• Overall validation score to track business progress")
    print("• Key insights extracted from data patterns")
    print("• Specific recommended actions for next steps")
    print("• Beautiful HTML dashboard for stakeholder sharing")
    print("• Business intelligence across acquisition + feedback data")

if __name__ == "__main__":
    print("📊 CUSTOMER VALIDATION DASHBOARD")
    print("Unified business intelligence for startup validation")
    print()
    
    # Demonstrate the system
    asyncio.run(demonstrate_validation_dashboard())