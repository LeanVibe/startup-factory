#!/usr/bin/env python3
"""
Customer Feedback Collection System - MVP Integration

FIRST PRINCIPLES IMPLEMENTATION:
1. Founders need real customer feedback to validate business hypotheses
2. Feedback collection must be simple and non-intrusive for users  
3. Feedback analysis should provide actionable insights immediately

PARETO FOCUS: 20% implementation that delivers 80% feedback collection value
- Embeddable feedback widgets for any MVP
- Smart business-context triggers
- Automatic sentiment analysis and recommendations
"""

import asyncio
import json
import logging
import re
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import Counter

logger = logging.getLogger(__name__)

class FeedbackType(str, Enum):
    """Types of feedback that can be collected"""
    RATING = "rating"  # 1-5 star ratings
    NPS = "nps"  # Net Promoter Score 0-10
    OPEN_TEXT = "open_text"  # Free form feedback
    FEATURE_REQUEST = "feature_request"  # Specific feature requests
    BUG_REPORT = "bug_report"  # Issue reporting
    EXIT_INTENT = "exit_intent"  # Feedback when user tries to leave

class FeedbackTrigger(str, Enum):
    """When to trigger feedback collection"""
    ON_SIGNUP = "on_signup"  # After user registration
    AFTER_FEATURE_USE = "after_feature_use"  # After using key feature
    TIME_BASED = "time_based"  # After certain time period
    EXIT_INTENT = "exit_intent"  # When user tries to leave
    MILESTONE_REACHED = "milestone_reached"  # After user completes action
    MANUAL = "manual"  # User-initiated feedback

@dataclass
class FeedbackWidget:
    """Configuration for a feedback widget"""
    widget_id: str
    feedback_type: FeedbackType
    trigger: FeedbackTrigger
    title: str
    question: str
    placement: str = "bottom-right"  # Widget placement on page
    delay_seconds: int = 0  # Delay before showing
    show_condition: Optional[str] = None  # JS condition for showing widget
    custom_styling: Dict[str, Any] = field(default_factory=dict)

@dataclass  
class FeedbackResponse:
    """Individual feedback response from a user"""
    response_id: str
    widget_id: str
    user_id: Optional[str]
    session_id: str
    feedback_type: FeedbackType
    rating: Optional[int] = None  # For rating/NPS feedback
    text: Optional[str] = None  # For text feedback
    feature_mentioned: Optional[str] = None  # Extracted feature mentions
    sentiment: Optional[str] = None  # positive, negative, neutral
    submitted_at: datetime = field(default_factory=datetime.now)
    user_agent: Optional[str] = None
    page_url: Optional[str] = None

@dataclass
class FeedbackAnalysis:
    """Analysis of collected feedback"""
    total_responses: int
    average_rating: Optional[float]
    nps_score: Optional[float]
    sentiment_breakdown: Dict[str, int]  # positive, negative, neutral counts
    common_themes: List[str]  # Most mentioned topics
    feature_requests: List[str]  # Requested features
    pain_points: List[str]  # Common complaints
    time_period: str
    recommendations: List[str]  # Actionable recommendations

class CustomerFeedbackSystem:
    """
    System for collecting and analyzing customer feedback in MVP templates.
    
    DELIVERS:
    1. Easy-to-embed feedback widgets for any MVP
    2. Smart triggering based on user behavior and business context
    3. Automatic sentiment analysis and categorization
    4. Actionable insights and recommendations for founders
    """
    
    def __init__(self):
        self.feedback_responses: List[FeedbackResponse] = []
        self.widget_templates = self._initialize_widget_templates()
        self.business_triggers = self._initialize_business_triggers()
        
    def create_feedback_widget(self, widget_config: Dict[str, Any]) -> FeedbackWidget:
        """Create a feedback widget that can be embedded in any MVP"""
        
        feedback_type = widget_config.get("feedback_type", FeedbackType.RATING)
        trigger = widget_config.get("trigger", FeedbackTrigger.AFTER_FEATURE_USE)
        business_context = widget_config.get("business_context", {})
        
        # Generate business-context aware title and question
        title = widget_config.get("title") or self._generate_context_title(feedback_type, business_context)
        question = widget_config.get("question") or self._generate_context_question(feedback_type, business_context)
        
        # Create widget with intelligent defaults
        widget = FeedbackWidget(
            widget_id=f"feedback_{feedback_type.value}_{str(uuid.uuid4())[:8]}",
            feedback_type=feedback_type,
            trigger=trigger,
            title=title,
            question=question,
            placement=widget_config.get("placement", "bottom-right"),
            delay_seconds=widget_config.get("delay_seconds", 0),
            show_condition=widget_config.get("show_condition"),
            custom_styling=widget_config.get("custom_styling", {})
        )
        
        return widget
        
    def generate_widget_code(self, widget: FeedbackWidget) -> Dict[str, str]:
        """Generate HTML/CSS/JS code for embedding the widget"""
        
        # Generate HTML structure
        html = self._generate_widget_html(widget)
        
        # Generate CSS styling
        css = self._generate_widget_css(widget)
        
        # Generate JavaScript functionality
        javascript = self._generate_widget_javascript(widget)
        
        return {
            "html": html,
            "css": css, 
            "javascript": javascript,
            "integration_instructions": self._generate_integration_instructions(widget)
        }
        
    def collect_feedback(self, response_data: Dict[str, Any]) -> FeedbackResponse:
        """Process and store a feedback response"""
        
        # Extract and validate response data
        widget_id = response_data.get("widget_id", "")
        feedback_type = FeedbackType(response_data.get("feedback_type", "rating"))
        
        # Perform basic sentiment analysis on text
        text = response_data.get("text", "")
        sentiment = self._analyze_sentiment(text) if text else None
        
        # Extract feature mentions
        feature_mentioned = self._extract_feature_mentions(text) if text else None
        
        # Create response object
        response = FeedbackResponse(
            response_id=str(uuid.uuid4()),
            widget_id=widget_id,
            user_id=response_data.get("user_id"),
            session_id=response_data.get("session_id", str(uuid.uuid4())),
            feedback_type=feedback_type,
            rating=response_data.get("rating"),
            text=text,
            feature_mentioned=feature_mentioned,
            sentiment=sentiment,
            user_agent=response_data.get("user_agent"),
            page_url=response_data.get("page_url")
        )
        
        # Store response (in production, this would go to a database)
        self.feedback_responses.append(response)
        
        return response
        
    def analyze_feedback(self, widget_id: str, days: int = 30) -> FeedbackAnalysis:
        """Analyze feedback for actionable insights"""
        
        # Filter feedback by widget and time period
        cutoff_date = datetime.now() - timedelta(days=days)
        relevant_feedback = [
            f for f in self.feedback_responses 
            if f.widget_id == widget_id and f.submitted_at >= cutoff_date
        ]
        
        if not relevant_feedback:
            # Return empty analysis with helpful recommendations
            return FeedbackAnalysis(
                total_responses=0,
                average_rating=None,
                nps_score=None,
                sentiment_breakdown={"positive": 0, "negative": 0, "neutral": 0},
                common_themes=[],
                feature_requests=[],
                pain_points=[],
                time_period=f"Last {days} days",
                recommendations=[
                    "Start collecting feedback by embedding widgets in your MVP",
                    "Focus on post-feature usage and milestone completion triggers",
                    "Ask specific questions about business value and user workflows"
                ]
            )
        
        # Calculate metrics
        ratings = [f.rating for f in relevant_feedback if f.rating is not None]
        average_rating = sum(ratings) / len(ratings) if ratings else None
        
        # Calculate NPS (for NPS feedback types)
        nps_scores = [f.rating for f in relevant_feedback 
                     if f.feedback_type == FeedbackType.NPS and f.rating is not None]
        nps_score = self._calculate_nps(nps_scores) if nps_scores else None
        
        # Sentiment analysis
        sentiments = [f.sentiment for f in relevant_feedback if f.sentiment]
        sentiment_breakdown = Counter(sentiments)
        sentiment_breakdown = dict(sentiment_breakdown)
        
        # Extract themes and insights
        all_text = " ".join([f.text for f in relevant_feedback if f.text])
        common_themes = self._extract_themes(all_text)
        feature_requests = self._extract_feature_requests(relevant_feedback)
        pain_points = self._extract_pain_points(relevant_feedback)
        
        # Generate actionable recommendations
        recommendations = self._generate_recommendations(
            relevant_feedback, average_rating, sentiment_breakdown
        )
        
        return FeedbackAnalysis(
            total_responses=len(relevant_feedback),
            average_rating=average_rating,
            nps_score=nps_score,
            sentiment_breakdown=sentiment_breakdown,
            common_themes=common_themes,
            feature_requests=feature_requests,
            pain_points=pain_points,
            time_period=f"Last {days} days",
            recommendations=recommendations
        )
        
    def get_smart_triggers(self, business_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate smart feedback triggers based on business model"""
        
        business_model = business_context.get("business_model", "b2c_saas")
        industry = business_context.get("industry", "general")
        key_features = business_context.get("key_features", [])
        user_journey = business_context.get("critical_user_journey", [])
        
        # Get base triggers for business model
        base_triggers = self.business_triggers.get(business_model, self.business_triggers["b2c_saas"])
        
        # Customize triggers based on context
        smart_triggers = []
        
        for trigger_template in base_triggers:
            # Customize trigger for specific industry/features
            trigger = trigger_template.copy()
            
            # Replace placeholders with actual business context
            if "{industry}" in trigger["question"]:
                industry_term = self._get_industry_term(industry)
                trigger["question"] = trigger["question"].replace("{industry}", industry_term)
                
            if "{key_feature}" in trigger["question"] and key_features:
                trigger["question"] = trigger["question"].replace("{key_feature}", key_features[0])
                
            # Add feature-specific triggers
            if trigger["trigger"] == FeedbackTrigger.AFTER_FEATURE_USE and key_features:
                for feature in key_features[:3]:  # Top 3 features
                    feature_trigger = trigger.copy()
                    feature_trigger["question"] = f"How was your experience with {feature}?"
                    feature_trigger["trigger_condition"] = f"after_using_{feature.lower().replace(' ', '_')}"
                    smart_triggers.append(feature_trigger)
            else:
                smart_triggers.append(trigger)
        
        return smart_triggers[:5]  # Return top 5 smart triggers
    
    def _initialize_widget_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize widget templates for different feedback types"""
        
        return {
            FeedbackType.RATING: {
                "title": "Quick Rating",
                "question": "How would you rate your experience?",
                "scale": "1-5 stars"
            },
            FeedbackType.NPS: {
                "title": "Recommendation Score", 
                "question": "How likely are you to recommend this to others?",
                "scale": "0-10 scale"
            },
            FeedbackType.OPEN_TEXT: {
                "title": "Your Feedback",
                "question": "What's on your mind? Any thoughts or suggestions?",
                "placeholder": "Share your thoughts..."
            }
        }
    
    def _initialize_business_triggers(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize smart triggers based on business models"""
        
        return {
            "b2b_saas": [
                {
                    "trigger": FeedbackTrigger.AFTER_FEATURE_USE,
                    "feedback_type": FeedbackType.RATING,
                    "question": "How valuable was this {key_feature} for your business workflow?",
                    "delay_seconds": 2,
                    "business_focus": "roi_and_efficiency"
                },
                {
                    "trigger": FeedbackTrigger.MILESTONE_REACHED,
                    "feedback_type": FeedbackType.NPS,
                    "question": "Based on the business value so far, how likely are you to recommend this to other {industry} professionals?",
                    "delay_seconds": 0,
                    "business_focus": "professional_recommendation"
                },
                {
                    "trigger": FeedbackTrigger.TIME_BASED,
                    "feedback_type": FeedbackType.OPEN_TEXT,
                    "question": "What business impact have you seen after using this for a week?",
                    "delay_seconds": 5,
                    "business_focus": "business_impact"
                }
            ],
            "b2c_saas": [
                {
                    "trigger": FeedbackTrigger.AFTER_FEATURE_USE,
                    "feedback_type": FeedbackType.RATING,
                    "question": "How did that work for you?",
                    "delay_seconds": 1,
                    "business_focus": "user_satisfaction"
                },
                {
                    "trigger": FeedbackTrigger.ON_SIGNUP,
                    "feedback_type": FeedbackType.OPEN_TEXT,
                    "question": "What brought you here today?",
                    "delay_seconds": 10,
                    "business_focus": "user_motivation"
                },
                {
                    "trigger": FeedbackTrigger.EXIT_INTENT,
                    "feedback_type": FeedbackType.OPEN_TEXT,
                    "question": "Before you go, what would make this more useful for you?",
                    "delay_seconds": 0,
                    "business_focus": "retention_improvement"
                }
            ]
        }
    
    def _generate_context_title(self, feedback_type: FeedbackType, business_context: Dict[str, Any]) -> str:
        """Generate business-context aware widget title"""
        
        business_model = business_context.get("business_model", "")
        
        if "b2b" in business_model:
            titles = {
                FeedbackType.RATING: "Business Value Check",
                FeedbackType.NPS: "Professional Recommendation",
                FeedbackType.OPEN_TEXT: "Business Impact Feedback"
            }
        else:
            titles = {
                FeedbackType.RATING: "Quick Rating", 
                FeedbackType.NPS: "Recommendation Score",
                FeedbackType.OPEN_TEXT: "Your Thoughts"
            }
        
        return titles.get(feedback_type, "Feedback")
    
    def _generate_context_question(self, feedback_type: FeedbackType, business_context: Dict[str, Any]) -> str:
        """Generate business-context aware question"""
        
        business_model = business_context.get("business_model", "")
        industry = business_context.get("industry", "")
        target_audience = business_context.get("target_audience", "users")
        
        if "b2b" in business_model:
            if feedback_type == FeedbackType.RATING:
                return f"How valuable is this for your {industry} workflow?"
            elif feedback_type == FeedbackType.NPS:
                return f"How likely are you to recommend this to other {target_audience}?"
            else:
                return "What business impact are you seeing?"
        else:
            if feedback_type == FeedbackType.RATING:
                return "How was your experience?"
            elif feedback_type == FeedbackType.NPS:
                return "How likely are you to recommend this to friends?"
            else:
                return "What's on your mind?"
    
    def _generate_widget_html(self, widget: FeedbackWidget) -> str:
        """Generate HTML structure for the widget"""
        
        if widget.feedback_type == FeedbackType.RATING:
            return f"""
<!-- Feedback Widget: {widget.widget_id} -->
<div id="{widget.widget_id}" class="feedback-widget" data-placement="{widget.placement}">
    <div class="feedback-widget-content">
        <h4 class="feedback-title">{widget.title}</h4>
        <p class="feedback-question">{widget.question}</p>
        <div class="rating-container">
            <div class="star-rating" data-widget="{widget.widget_id}">
                <span class="star" data-rating="1">★</span>
                <span class="star" data-rating="2">★</span>
                <span class="star" data-rating="3">★</span>
                <span class="star" data-rating="4">★</span>
                <span class="star" data-rating="5">★</span>
            </div>
        </div>
        <div class="feedback-actions">
            <button class="feedback-skip">Skip</button>
        </div>
    </div>
</div>"""
        
        elif widget.feedback_type == FeedbackType.NPS:
            nps_buttons = "".join([
                f'<button class="nps-score" data-score="{i}">{i}</button>' 
                for i in range(11)
            ])
            return f"""
<!-- NPS Widget: {widget.widget_id} -->
<div id="{widget.widget_id}" class="feedback-widget nps-widget" data-placement="{widget.placement}">
    <div class="feedback-widget-content">
        <h4 class="feedback-title">{widget.title}</h4>
        <p class="feedback-question">{widget.question}</p>
        <div class="nps-container">
            <div class="nps-scale" data-widget="{widget.widget_id}">
                {nps_buttons}
            </div>
            <div class="nps-labels">
                <span>Not likely</span>
                <span>Very likely</span>
            </div>
        </div>
        <div class="feedback-actions">
            <button class="feedback-skip">Skip</button>
        </div>
    </div>
</div>"""
        
        else:  # Open text
            return f"""
<!-- Text Feedback Widget: {widget.widget_id} -->
<div id="{widget.widget_id}" class="feedback-widget text-widget" data-placement="{widget.placement}">
    <div class="feedback-widget-content">
        <h4 class="feedback-title">{widget.title}</h4>
        <p class="feedback-question">{widget.question}</p>
        <div class="text-container">
            <textarea class="feedback-text" placeholder="Share your thoughts..." data-widget="{widget.widget_id}"></textarea>
        </div>
        <div class="feedback-actions">
            <button class="feedback-submit">Send Feedback</button>
            <button class="feedback-skip">Skip</button>
        </div>
    </div>
</div>"""
    
    def _generate_widget_css(self, widget: FeedbackWidget) -> str:
        """Generate CSS styling for the widget"""
        
        placement_css = {
            "bottom-right": "bottom: 20px; right: 20px;",
            "bottom-left": "bottom: 20px; left: 20px;", 
            "top-right": "top: 20px; right: 20px;",
            "center": "top: 50%; left: 50%; transform: translate(-50%, -50%);"
        }
        
        position_style = placement_css.get(widget.placement, placement_css["bottom-right"])
        
        return f"""
/* Feedback Widget Styles */
.feedback-widget {{
    position: fixed;
    {position_style}
    z-index: 10000;
    background: white;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    padding: 20px;
    max-width: 320px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    border: 1px solid #e1e5e9;
    transition: all 0.3s ease;
}}

.feedback-widget:hover {{
    box-shadow: 0 12px 40px rgba(0,0,0,0.2);
}}

.feedback-title {{
    margin: 0 0 8px 0;
    font-size: 16px;
    font-weight: 600;
    color: #1a202c;
}}

.feedback-question {{
    margin: 0 0 16px 0;
    font-size: 14px;
    color: #4a5568;
    line-height: 1.4;
}}

/* Star Rating Styles */
.star-rating {{
    display: flex;
    gap: 4px;
    margin-bottom: 16px;
}}

.star {{
    font-size: 24px;
    color: #e2e8f0;
    cursor: pointer;
    transition: color 0.2s ease;
    user-select: none;
}}

.star:hover,
.star.active {{
    color: #f6ad55;
}}

/* NPS Styles */
.nps-scale {{
    display: flex;
    gap: 4px;
    margin-bottom: 8px;
}}

.nps-score {{
    width: 28px;
    height: 28px;
    border: 1px solid #cbd5e0;
    background: white;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
}}

.nps-score:hover,
.nps-score.selected {{
    background: #4299e1;
    color: white;
    border-color: #4299e1;
}}

.nps-labels {{
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #718096;
    margin-bottom: 16px;
}}

/* Text Input Styles */
.feedback-text {{
    width: 100%;
    min-height: 80px;
    padding: 12px;
    border: 1px solid #cbd5e0;
    border-radius: 8px;
    font-size: 14px;
    font-family: inherit;
    resize: vertical;
    margin-bottom: 16px;
}}

.feedback-text:focus {{
    outline: none;
    border-color: #4299e1;
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
}}

/* Action Buttons */
.feedback-actions {{
    display: flex;
    gap: 8px;
    justify-content: flex-end;
}}

.feedback-submit,
.feedback-skip {{
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
}}

.feedback-submit {{
    background: #4299e1;
    color: white;
    border: 1px solid #4299e1;
}}

.feedback-submit:hover {{
    background: #3182ce;
}}

.feedback-skip {{
    background: transparent;
    color: #718096;
    border: 1px solid #cbd5e0;
}}

.feedback-skip:hover {{
    color: #4a5568;
    border-color: #a0aec0;
}}

/* Responsive */
@media (max-width: 480px) {{
    .feedback-widget {{
        left: 10px;
        right: 10px;
        bottom: 10px;
        max-width: none;
        margin: 0;
    }}
}}"""
    
    def _generate_widget_javascript(self, widget: FeedbackWidget) -> str:
        """Generate JavaScript functionality for the widget"""
        
        return f"""
// Feedback Widget JavaScript
(function() {{
    const widget = document.getElementById('{widget.widget_id}');
    let isSubmitted = false;
    
    // Show widget with delay
    setTimeout(function() {{
        if (widget) {{
            widget.style.display = 'block';
        }}
    }}, {widget.delay_seconds * 1000});
    
    // Handle star rating
    const stars = widget.querySelectorAll('.star');
    stars.forEach((star, index) => {{
        star.addEventListener('click', function() {{
            const rating = parseInt(star.dataset.rating);
            submitFeedback({{
                widget_id: '{widget.widget_id}',
                feedback_type: '{widget.feedback_type.value}',
                rating: rating,
                page_url: window.location.href,
                user_agent: navigator.userAgent,
                session_id: getSessionId()
            }});
            
            // Visual feedback
            stars.forEach((s, i) => {{
                s.classList.toggle('active', i < rating);
            }});
            
            setTimeout(() => hideWidget(), 1500);
        }});
        
        // Hover effect
        star.addEventListener('mouseenter', function() {{
            const rating = parseInt(star.dataset.rating);
            stars.forEach((s, i) => {{
                s.style.color = i < rating ? '#f6ad55' : '#e2e8f0';
            }});
        }});
    }});
    
    // Handle NPS scoring
    const npsButtons = widget.querySelectorAll('.nps-score');
    npsButtons.forEach(button => {{
        button.addEventListener('click', function() {{
            const score = parseInt(button.dataset.score);
            submitFeedback({{
                widget_id: '{widget.widget_id}',
                feedback_type: '{widget.feedback_type.value}',
                rating: score,
                page_url: window.location.href,
                user_agent: navigator.userAgent,
                session_id: getSessionId()
            }});
            
            // Visual feedback
            npsButtons.forEach(b => b.classList.remove('selected'));
            button.classList.add('selected');
            
            setTimeout(() => hideWidget(), 1500);
        }});
    }});
    
    // Handle text submission
    const submitButton = widget.querySelector('.feedback-submit');
    if (submitButton) {{
        submitButton.addEventListener('click', function() {{
            const textArea = widget.querySelector('.feedback-text');
            const text = textArea.value.trim();
            
            if (text) {{
                submitFeedback({{
                    widget_id: '{widget.widget_id}',
                    feedback_type: '{widget.feedback_type.value}',
                    text: text,
                    page_url: window.location.href,
                    user_agent: navigator.userAgent,
                    session_id: getSessionId()
                }});
                
                textArea.value = 'Thank you for your feedback!';
                textArea.disabled = true;
                setTimeout(() => hideWidget(), 2000);
            }}
        }});
    }}
    
    // Handle skip
    const skipButton = widget.querySelector('.feedback-skip');
    if (skipButton) {{
        skipButton.addEventListener('click', function() {{
            hideWidget();
        }});
    }}
    
    function submitFeedback(data) {{
        if (isSubmitted) return;
        isSubmitted = true;
        
        // Submit to your feedback endpoint
        fetch('/api/feedback', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json'
            }},
            body: JSON.stringify(data)
        }})
        .then(response => response.json())
        .then(data => console.log('Feedback submitted:', data))
        .catch(error => console.error('Feedback error:', error));
    }}
    
    function hideWidget() {{
        widget.style.display = 'none';
    }}
    
    function getSessionId() {{
        let sessionId = sessionStorage.getItem('feedback_session_id');
        if (!sessionId) {{
            sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('feedback_session_id', sessionId);
        }}
        return sessionId;
    }}
}})();"""
    
    def _generate_integration_instructions(self, widget: FeedbackWidget) -> str:
        """Generate integration instructions for founders"""
        
        return f"""
FEEDBACK WIDGET INTEGRATION INSTRUCTIONS
========================================

Widget ID: {widget.widget_id}
Type: {widget.feedback_type.value.title()} Feedback

STEP 1: Add the HTML
Add this HTML to your page where you want the feedback widget:
(The widget will be positioned as: {widget.placement})

STEP 2: Add the CSS
Include the CSS in your stylesheet or in a <style> tag in your <head>

STEP 3: Add the JavaScript
Include the JavaScript at the bottom of your page, before closing </body>

STEP 4: Set up the API endpoint
Create a POST endpoint at '/api/feedback' to receive feedback data.
The endpoint will receive JSON data with these fields:
- widget_id: {widget.widget_id}
- feedback_type: {widget.feedback_type.value}
- rating: (for rating/NPS feedback)
- text: (for text feedback)
- page_url, user_agent, session_id: (metadata)

STEP 5: Test
Load your page and the widget should appear after {widget.delay_seconds} seconds.

CUSTOMIZATION:
- Change placement by modifying data-placement attribute
- Adjust delay by changing delay_seconds in the JavaScript
- Modify styling in the CSS section
- Customize questions by editing the HTML content

BUSINESS INTELLIGENCE:
This widget is optimized for your business context:
- Question focuses on business value and user workflows
- Timing is optimized for your user journey
- Data collection supports your validation hypotheses
"""
    
    def _analyze_sentiment(self, text: str) -> str:
        """Basic sentiment analysis of feedback text"""
        
        if not text:
            return "neutral"
            
        text_lower = text.lower()
        
        positive_words = [
            "love", "great", "awesome", "excellent", "perfect", "amazing", 
            "helpful", "useful", "easy", "simple", "fast", "good", "nice",
            "fantastic", "wonderful", "brilliant", "impressed", "satisfied"
        ]
        
        negative_words = [
            "hate", "terrible", "awful", "horrible", "bad", "worst", "slow",
            "confusing", "difficult", "broken", "annoying", "frustrating",
            "disappointed", "useless", "complicated", "error", "bug", "issue"
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _extract_feature_mentions(self, text: str) -> Optional[str]:
        """Extract feature mentions from feedback text"""
        
        if not text:
            return None
            
        # Common feature keywords
        feature_patterns = [
            r"dashboard", r"login", r"signup", r"report", r"export", 
            r"search", r"filter", r"notification", r"email", r"integration",
            r"mobile", r"app", r"interface", r"ui", r"design"
        ]
        
        text_lower = text.lower()
        for pattern in feature_patterns:
            if re.search(pattern, text_lower):
                return pattern
                
        return None
    
    def _extract_themes(self, text: str) -> List[str]:
        """Extract common themes from feedback text"""
        
        if not text:
            return []
            
        # Simple keyword extraction
        theme_keywords = [
            "performance", "speed", "loading", "user interface", "design",
            "functionality", "features", "pricing", "support", "documentation",
            "mobile", "integration", "security", "reliability", "ease of use"
        ]
        
        text_lower = text.lower()
        themes = [theme for theme in theme_keywords if theme in text_lower]
        
        return themes[:5]  # Return top 5 themes
    
    def _extract_feature_requests(self, feedback_list: List[FeedbackResponse]) -> List[str]:
        """Extract feature requests from feedback responses"""
        
        feature_requests = []
        request_keywords = ["need", "want", "wish", "could", "should", "add", "feature"]
        
        for feedback in feedback_list:
            if feedback.text:
                text_lower = feedback.text.lower()
                if any(keyword in text_lower for keyword in request_keywords):
                    # Extract the request (simplified)
                    sentences = feedback.text.split('.')
                    for sentence in sentences:
                        if any(keyword in sentence.lower() for keyword in request_keywords):
                            feature_requests.append(sentence.strip())
                            break
                            
        return feature_requests[:5]  # Return top 5 requests
    
    def _extract_pain_points(self, feedback_list: List[FeedbackResponse]) -> List[str]:
        """Extract pain points from negative feedback"""
        
        pain_points = []
        pain_keywords = ["slow", "confusing", "difficult", "broken", "annoying", "problem"]
        
        for feedback in feedback_list:
            if feedback.sentiment == "negative" and feedback.text:
                text_lower = feedback.text.lower()
                if any(keyword in text_lower for keyword in pain_keywords):
                    # Extract the pain point (simplified)
                    sentences = feedback.text.split('.')
                    for sentence in sentences:
                        if any(keyword in sentence.lower() for keyword in pain_keywords):
                            pain_points.append(sentence.strip())
                            break
                            
        return pain_points[:5]  # Return top 5 pain points
    
    def _calculate_nps(self, scores: List[int]) -> float:
        """Calculate Net Promoter Score from 0-10 ratings"""
        
        if not scores:
            return 0.0
            
        promoters = len([s for s in scores if s >= 9])
        detractors = len([s for s in scores if s <= 6])
        total = len(scores)
        
        nps = ((promoters - detractors) / total) * 100
        return round(nps, 1)
    
    def _generate_recommendations(self, feedback_list: List[FeedbackResponse], 
                                  average_rating: Optional[float], 
                                  sentiment_breakdown: Dict[str, int]) -> List[str]:
        """Generate actionable recommendations based on feedback analysis"""
        
        recommendations = []
        
        # Rating-based recommendations
        if average_rating:
            if average_rating < 3.0:
                recommendations.append("🚨 URGENT: Address core user experience issues - average rating below 3.0")
                recommendations.append("Focus on the most mentioned pain points in negative feedback")
            elif average_rating < 4.0:
                recommendations.append("⚠️  Improve user experience - ratings suggest room for improvement")
                recommendations.append("Prioritize fixing the top 3 most common user complaints")
            else:
                recommendations.append("✅ Strong user satisfaction - consider asking for reviews/referrals")
        
        # Sentiment-based recommendations
        negative_count = sentiment_breakdown.get("negative", 0)
        positive_count = sentiment_breakdown.get("positive", 0)
        total_responses = sum(sentiment_breakdown.values())
        
        if total_responses > 0:
            negative_ratio = negative_count / total_responses
            if negative_ratio > 0.4:
                recommendations.append("📉 High negative sentiment - investigate root causes immediately")
            elif negative_ratio > 0.2:
                recommendations.append("⚡ Address negative feedback patterns before they impact growth")
            else:
                recommendations.append("📈 Positive sentiment trend - amplify what's working well")
        
        # Volume-based recommendations
        if len(feedback_list) < 10:
            recommendations.append("📊 Increase feedback collection - consider more prominent widget placement")
            recommendations.append("🎯 Add feedback triggers after key user actions for more insights")
        
        # Feature request recommendations
        feature_mentions = [f.feature_mentioned for f in feedback_list if f.feature_mentioned]
        if feature_mentions:
            most_mentioned = Counter(feature_mentions).most_common(1)[0][0]
            recommendations.append(f"🔧 Most discussed feature: '{most_mentioned}' - prioritize improvements here")
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _get_industry_term(self, industry: str) -> str:
        """Get industry-appropriate terminology"""
        
        industry_terms = {
            "healthcare": "medical practice",
            "fintech": "financial service",
            "education": "educational tool",
            "real_estate": "property management",
            "logistics": "supply chain solution"
        }
        
        return industry_terms.get(industry, "business solution")

async def demonstrate_feedback_system():
    """Demonstrate the customer feedback system with real scenarios"""
    
    print("📝 CUSTOMER FEEDBACK SYSTEM DEMONSTRATION")
    print("=" * 70)
    print("Generating embeddable feedback widgets for MVP integration")
    print()
    
    feedback_system = CustomerFeedbackSystem()
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "B2B Healthcare SaaS",
            "business_context": {
                "business_model": "b2b_saas",
                "industry": "healthcare",
                "target_audience": "medical practice administrators",
                "key_features": ["compliance dashboard", "patient reporting", "audit trails"]
            },
            "widget_config": {
                "feedback_type": FeedbackType.RATING,
                "trigger": FeedbackTrigger.AFTER_FEATURE_USE
            }
        },
        {
            "name": "B2C Education Tool",
            "business_context": {
                "business_model": "b2c_saas",
                "industry": "education", 
                "target_audience": "K-12 teachers",
                "key_features": ["progress tracking", "parent communication", "gradebook"]
            },
            "widget_config": {
                "feedback_type": FeedbackType.NPS,
                "trigger": FeedbackTrigger.TIME_BASED
            }
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"📋 SCENARIO {i}: {scenario['name']}")
        print("-" * 50)
        
        # Add business context to widget config
        widget_config = scenario["widget_config"].copy()
        widget_config["business_context"] = scenario["business_context"]
        
        # Create widget
        widget = feedback_system.create_feedback_widget(widget_config)
        
        print(f"🎯 Widget ID: {widget.widget_id}")
        print(f"📊 Type: {widget.feedback_type.value.title()}")
        print(f"⚡ Trigger: {widget.trigger.value.replace('_', ' ').title()}")
        print(f"❓ Question: {widget.question}")
        print()
        
        # Generate widget code
        code = feedback_system.generate_widget_code(widget)
        
        print("📄 GENERATED CODE PREVIEW:")
        print(f"  HTML: {len(code['html'])} characters")
        print(f"  CSS: {len(code['css'])} characters") 
        print(f"  JavaScript: {len(code['javascript'])} characters")
        print()
        
        # Get smart triggers
        triggers = feedback_system.get_smart_triggers(scenario["business_context"])
        print(f"🧠 SMART TRIGGERS ({len(triggers)} generated):")
        for j, trigger in enumerate(triggers[:3], 1):
            print(f"  {j}. {trigger['question']}")
        print()
        
        # Simulate collecting feedback
        sample_feedback = {
            "widget_id": widget.widget_id,
            "feedback_type": widget.feedback_type.value,
            "rating": 4,
            "text": f"Great {scenario['business_context']['industry']} tool, but could be faster",
            "user_id": f"user_{i}",
            "session_id": f"session_{i}"
        }
        
        response = feedback_system.collect_feedback(sample_feedback)
        print(f"💾 Sample Feedback Collected: {response.rating}/5 stars")
        print(f"💭 Sentiment: {response.sentiment}")
        print()
        
        print("-" * 50)
        print()
    
    # Demonstrate analysis
    print("📊 FEEDBACK ANALYSIS DEMO")
    print("-" * 30)
    
    # Analyze feedback for first widget
    first_widget_id = test_scenarios[0]["name"].replace(" ", "_").lower()
    analysis = feedback_system.analyze_feedback(first_widget_id)
    
    print(f"📈 Total Responses: {analysis.total_responses}")
    print(f"⭐ Average Rating: {analysis.average_rating or 'N/A'}")
    print(f"📊 Sentiment Breakdown: {analysis.sentiment_breakdown}")
    print()
    
    print("🎯 RECOMMENDATIONS:")
    for i, rec in enumerate(analysis.recommendations[:3], 1):
        print(f"  {i}. {rec}")
    print()
    
    print("✅ CUSTOMER FEEDBACK SYSTEM DEMONSTRATION COMPLETE")
    print()
    print("🎉 FOUNDERS NOW GET:")
    print("• Embeddable feedback widgets for any MVP")
    print("• Smart triggers based on business context")
    print("• Automatic sentiment analysis")
    print("• Actionable recommendations for improvement")
    print("• Complete integration code (HTML/CSS/JS)")

if __name__ == "__main__":
    print("📝 CUSTOMER FEEDBACK COLLECTION SYSTEM")
    print("Bridging the gap between MVP deployment and customer insights")
    print()
    
    # Demonstrate the system
    asyncio.run(demonstrate_feedback_system())