#!/usr/bin/env python3
"""
Test-Driven Development for Customer Feedback Collection System

FIRST PRINCIPLES:
1. Founders need real customer feedback to validate business hypotheses
2. Feedback collection must be simple and non-intrusive for users
3. Feedback analysis should provide actionable insights immediately

TDD APPROACH:
1. Write failing tests for feedback widgets and collection
2. Implement minimal customer feedback system
3. Validate with realistic customer feedback scenarios

FUNDAMENTAL TRUTH: 
Customer feedback is the bridge between founder assumptions and market reality.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
# Import from the actual implementation
from customer_feedback_system import (
    CustomerFeedbackSystem, FeedbackType, FeedbackTrigger, 
    FeedbackWidget, FeedbackResponse, FeedbackAnalysis
)

class TestCustomerFeedbackSystem:
    """TDD tests for customer feedback collection system"""
    
    @pytest.fixture
    def b2b_saas_context(self):
        return {
            "business_model": "b2b_saas",
            "industry": "healthcare", 
            "key_features": ["dashboard", "reporting", "user_management"],
            "target_audience": "medical practice administrators",
            "critical_user_journey": ["signup", "setup", "first_report", "daily_usage"]
        }
    
    @pytest.fixture  
    def b2c_saas_context(self):
        return {
            "business_model": "b2c_saas",
            "industry": "education",
            "key_features": ["progress_tracking", "parent_communication", "reporting"],
            "target_audience": "K-12 teachers",
            "critical_user_journey": ["signup", "first_class", "student_entry", "parent_update"]
        }
    
    def test_create_rating_feedback_widget(self, b2b_saas_context):
        """
        TEST: System should create embeddable rating widgets for MVPs
        
        EXPECTED BEHAVIOR:
        - Widget configured for specific feedback type (rating, NPS, text)
        - Smart trigger based on user behavior (after feature use, time-based)
        - Customizable styling and placement
        - Business context awareness (B2B vs B2C appropriate questions)
        """
        feedback_system = CustomerFeedbackSystem()
        
        widget_config = {
            "feedback_type": FeedbackType.RATING,
            "trigger": FeedbackTrigger.AFTER_FEATURE_USE,
            "title": "How was your dashboard experience?",
            "question": "Please rate the new reporting dashboard",
            "business_context": b2b_saas_context
        }
        
        widget = feedback_system.create_feedback_widget(widget_config)
        
        # Test widget creation
        assert isinstance(widget, FeedbackWidget)
        assert widget.feedback_type == FeedbackType.RATING
        assert widget.trigger == FeedbackTrigger.AFTER_FEATURE_USE
        assert "dashboard" in widget.question.lower()  # Business context aware
        assert widget.widget_id is not None and len(widget.widget_id) > 0
        
    def test_generate_embeddable_widget_code(self, b2c_saas_context):
        """
        TEST: System should generate HTML/CSS/JS code for easy embedding
        
        EXPECTED BEHAVIOR:
        - Complete HTML structure for the widget
        - CSS styling that matches MVP design
        - JavaScript for user interaction and data collection
        - Integration code that founders can copy-paste
        """
        feedback_system = CustomerFeedbackSystem()
        
        widget_config = {
            "feedback_type": FeedbackType.NPS,
            "trigger": FeedbackTrigger.TIME_BASED,
            "title": "Quick feedback",
            "question": "How likely are you to recommend this to fellow teachers?",
            "business_context": b2c_saas_context
        }
        
        widget = feedback_system.create_feedback_widget(widget_config)
        code = feedback_system.generate_widget_code(widget)
        
        # Test code generation
        assert "html" in code
        assert "css" in code
        assert "javascript" in code
        
        # HTML should contain widget structure
        html_code = code["html"]
        assert "nps" in html_code.lower() or "recommend" in html_code.lower()
        assert "teacher" in html_code.lower()  # Context awareness
        
        # CSS should provide styling
        css_code = code["css"]
        assert len(css_code) > 100  # Substantial styling
        assert "widget" in css_code.lower()
        
        # JavaScript should handle interactions
        js_code = code["javascript"]
        assert "function" in js_code or "=>" in js_code  # Has functions
        assert "submit" in js_code.lower() or "send" in js_code.lower()
        
    def test_smart_feedback_triggers_for_business_model(self, b2b_saas_context):
        """
        TEST: System should generate smart triggers based on business model
        
        EXPECTED BEHAVIOR:
        - B2B SaaS: Focus on feature adoption and ROI validation
        - B2C SaaS: Focus on user satisfaction and retention
        - Triggers aligned with critical user journey points
        - Industry-specific timing and questions
        """
        feedback_system = CustomerFeedbackSystem()
        
        triggers = feedback_system.get_smart_triggers(b2b_saas_context)
        
        # Test trigger intelligence
        assert len(triggers) >= 3  # Multiple smart triggers
        
        trigger_types = [t["trigger"] for t in triggers]
        
        # B2B should have business-focused triggers
        assert FeedbackTrigger.AFTER_FEATURE_USE in trigger_types
        assert FeedbackTrigger.MILESTONE_REACHED in trigger_types
        
        # Check business context awareness
        trigger_questions = [t["question"] for t in triggers]
        business_terms = ["roi", "value", "business", "workflow", "efficiency"]
        assert any(any(term in q.lower() for term in business_terms) for q in trigger_questions)
        
    def test_feedback_collection_and_storage(self):
        """
        TEST: System should properly collect and store feedback responses
        
        EXPECTED BEHAVIOR:
        - Accept feedback in multiple formats (rating, text, NPS)
        - Store with user context and metadata
        - Handle anonymous and authenticated users
        - Validate data integrity
        """
        feedback_system = CustomerFeedbackSystem()
        
        response_data = {
            "widget_id": "widget_123",
            "user_id": "user_456", 
            "session_id": "session_789",
            "feedback_type": FeedbackType.RATING,
            "rating": 4,
            "text": "Great dashboard, but loading is slow",
            "page_url": "/dashboard",
            "user_agent": "Mozilla/5.0..."
        }
        
        response = feedback_system.collect_feedback(response_data)
        
        # Test response creation
        assert isinstance(response, FeedbackResponse)
        assert response.widget_id == "widget_123"
        assert response.rating == 4
        assert response.text == "Great dashboard, but loading is slow"
        assert response.feedback_type == FeedbackType.RATING
        assert response.submitted_at is not None
        
    def test_feedback_analysis_and_insights(self):
        """
        TEST: System should analyze feedback and provide actionable insights
        
        EXPECTED BEHAVIOR:
        - Calculate metrics (avg rating, NPS score, sentiment)
        - Identify common themes and pain points
        - Extract feature requests from text feedback
        - Generate specific recommendations for founders
        """
        feedback_system = CustomerFeedbackSystem()
        
        # Mock having collected some feedback
        widget_id = "widget_dashboard_rating"
        
        analysis = feedback_system.analyze_feedback(widget_id, days=30)
        
        # Test analysis completeness
        assert isinstance(analysis, FeedbackAnalysis)
        assert analysis.total_responses >= 0
        assert analysis.sentiment_breakdown is not None
        assert len(analysis.recommendations) > 0
        
        # Test insight quality
        assert isinstance(analysis.common_themes, list)
        assert isinstance(analysis.feature_requests, list)
        assert isinstance(analysis.pain_points, list)
        
    def test_business_context_appropriate_widgets(self, b2b_saas_context, b2c_saas_context):
        """
        TEST: Widgets should be tailored to business model and industry
        
        EXPECTED BEHAVIOR:
        - B2B widgets focus on business value and ROI
        - B2C widgets focus on user experience and satisfaction
        - Industry-specific language and concerns
        - Appropriate timing for each business model
        """
        feedback_system = CustomerFeedbackSystem()
        
        # Test B2B widget
        b2b_config = {
            "feedback_type": FeedbackType.NPS,
            "trigger": FeedbackTrigger.MILESTONE_REACHED,
            "title": "Business Impact Assessment",
            "question": "Based on your usage, how likely are you to recommend this to other practices?",
            "business_context": b2b_saas_context
        }
        
        b2b_widget = feedback_system.create_feedback_widget(b2b_config)
        
        # Test B2C widget  
        b2c_config = {
            "feedback_type": FeedbackType.RATING,
            "trigger": FeedbackTrigger.AFTER_FEATURE_USE,
            "title": "Quick Check-in",
            "question": "How did that work for you?",
            "business_context": b2c_saas_context
        }
        
        b2c_widget = feedback_system.create_feedback_widget(b2c_config)
        
        # Test business model differentiation
        assert b2b_widget.title != b2c_widget.title
        assert "business" in b2b_widget.question.lower() or "practice" in b2b_widget.question.lower()
        assert len(b2c_widget.question) < len(b2b_widget.question)  # B2C should be shorter/simpler

async def run_comprehensive_feedback_system_tests():
    """Run the comprehensive TDD test suite for feedback collection"""
    
    print("📝 CUSTOMER FEEDBACK SYSTEM - TDD VALIDATION")
    print("=" * 70)
    print("Testing that founders get actionable feedback collection tools")
    print()
    
    # Create test scenarios  
    b2b_context = {
        "business_model": "b2b_saas",
        "industry": "healthcare",
        "key_features": ["dashboard", "reporting", "user_management"],
        "target_audience": "medical practice administrators"
    }
    
    b2c_context = {
        "business_model": "b2c_saas", 
        "industry": "education",
        "key_features": ["progress_tracking", "parent_communication"],
        "target_audience": "K-12 teachers"
    }
    
    # Initialize system (this will fail initially - that's the point of TDD)
    feedback_system = CustomerFeedbackSystem()
    
    test_scenarios = [
        ("Rating Widget Creation", "b2b_saas"),
        ("Widget Code Generation", "b2c_saas"), 
        ("Smart Triggers", "b2b_saas"),
        ("Feedback Collection", "general"),
        ("Analysis & Insights", "general")
    ]
    
    print("🔥 RUNNING TDD TESTS (These should FAIL initially)")
    print("-" * 50)
    
    failed_tests = 0
    
    for scenario_name, context_type in test_scenarios:
        print(f"\n📋 Testing: {scenario_name}")
        
        try:
            if scenario_name == "Rating Widget Creation":
                widget_config = {
                    "feedback_type": FeedbackType.RATING,
                    "trigger": FeedbackTrigger.AFTER_FEATURE_USE,
                    "business_context": b2b_context
                }
                widget = feedback_system.create_feedback_widget(widget_config)
                print("   ✅ Rating widget created")
                
            elif scenario_name == "Widget Code Generation":
                widget_config = {
                    "feedback_type": FeedbackType.NPS,
                    "business_context": b2c_context
                }
                widget = feedback_system.create_feedback_widget(widget_config)
                code = feedback_system.generate_widget_code(widget)
                print("   ✅ Widget code generated")
                
            elif scenario_name == "Smart Triggers":
                triggers = feedback_system.get_smart_triggers(b2b_context)
                print("   ✅ Smart triggers generated")
                
            elif scenario_name == "Feedback Collection":
                response_data = {"widget_id": "test", "rating": 5}
                response = feedback_system.collect_feedback(response_data)
                print("   ✅ Feedback collected")
                
            elif scenario_name == "Analysis & Insights":
                analysis = feedback_system.analyze_feedback("widget_123")
                print("   ✅ Feedback analysis completed")
                
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
        print("\nNext Step: Implement CustomerFeedbackSystem methods to make tests pass")
    else:
        print("\n❌ TDD SETUP ISSUE!")
        print("Some tests passed unexpectedly - check implementation")
    
    return {
        "setup_correct": failed_tests == len(test_scenarios),
        "failed_tests": failed_tests,
        "total_tests": len(test_scenarios)
    }

if __name__ == "__main__":
    print("📝 CUSTOMER FEEDBACK SYSTEM - TDD SETUP")
    print("Setting up failing tests to drive implementation")
    print()
    
    # Run TDD setup - tests should fail initially
    results = asyncio.run(run_comprehensive_feedback_system_tests())
    
    print("\n" + "=" * 70)
    print("📋 TDD METHODOLOGY APPLIED")
    print()
    print("1. ❌ Tests written that define expected behavior (FAILING)")
    print("2. ⏳ Next: Implement minimal code to make tests pass") 
    print("3. ⏳ Then: Refactor while keeping tests green")
    print()
    print("📝 CUSTOMER FEEDBACK SYSTEM READY FOR IMPLEMENTATION")