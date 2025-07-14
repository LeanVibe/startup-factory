#!/usr/bin/env python3
"""
Validation helpers for MVP Orchestrator testing
Provides objective quality metrics for AI outputs
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path


def load_test_scenarios() -> Dict[str, Any]:
    """Load test scenarios from JSON file"""
    scenarios_path = Path(__file__).parent.parent / "test_scenarios.json"
    with open(scenarios_path, 'r') as f:
        return json.load(f)


def validate_market_research(content: str, expected_sections: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that market research contains required sections
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    content_lower = content.lower()
    
    # Check required sections
    missing_sections = []
    for section in expected_sections:
        if section.lower() not in content_lower:
            missing_sections.append(section)
    
    if missing_sections:
        issues.append(f"Missing required sections: {', '.join(missing_sections)}")
    
    # Check for current year mention (indicates recent data)
    current_year = datetime.now().year
    if str(current_year) not in content and str(current_year-1) not in content:
        issues.append(f"No mention of current year ({current_year}) or previous year")
    
    # Check minimum length
    if len(content) < 500:
        issues.append(f"Content too short: {len(content)} chars (minimum 500)")
    
    # Check for specific data indicators
    data_indicators = ["million", "billion", "market size", "%", "growth", "cagr"]
    found_indicators = sum(1 for indicator in data_indicators if indicator in content_lower)
    if found_indicators < 3:
        issues.append(f"Insufficient market data indicators found: {found_indicators}/3")
    
    return len(issues) == 0, issues


def validate_founder_score(content: str) -> Tuple[bool, List[str]]:
    """
    Validate founder score format and justification
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    content_lower = content.lower()
    
    # Check for numerical score (1-10)
    score_patterns = [
        r'score[:\s]*([0-9]|10)',
        r'rating[:\s]*([0-9]|10)', 
        r'([0-9]|10)[/\s]*10',
        r'([0-9]|10)\s*out of\s*10'
    ]
    
    score_found = False
    extracted_score = None
    
    for pattern in score_patterns:
        match = re.search(pattern, content_lower)
        if match:
            score_found = True
            try:
                extracted_score = int(match.group(1))
            except (ValueError, IndexError):
                continue
            break
    
    if not score_found:
        issues.append("No numerical score (1-10) found in content")
    elif extracted_score is not None and not (1 <= extracted_score <= 10):
        issues.append(f"Score {extracted_score} is outside valid range 1-10")
    
    # Check for justification (reasonable length indicates explanation)
    if len(content) < 300:
        issues.append(f"Content too short for proper justification: {len(content)} chars (minimum 300)")
    
    # Check for reasoning indicators
    reasoning_terms = ["because", "due to", "experience", "skills", "strength", "weakness", "recommendation"]
    found_reasoning = sum(1 for term in reasoning_terms if term in content_lower)
    if found_reasoning < 3:
        issues.append(f"Insufficient reasoning indicators: {found_reasoning}/3")
    
    return len(issues) == 0, issues


def validate_mvp_specification(content: str, expected_features: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate MVP specification structure and content
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    content_lower = content.lower()
    
    # Check required sections
    required_sections = ["core features", "user journey", "technical architecture"]
    missing_sections = []
    
    for section in required_sections:
        if section.lower() not in content_lower:
            missing_sections.append(section)
    
    if missing_sections:
        issues.append(f"Missing required sections: {', '.join(missing_sections)}")
    
    # Check for expected features
    if expected_features:
        missing_features = []
        for feature in expected_features:
            if feature.lower() not in content_lower:
                missing_features.append(feature)
        
        if len(missing_features) > len(expected_features) // 2:
            issues.append(f"Too many expected features missing: {missing_features}")
    
    # Check minimum length
    if len(content) < 800:
        issues.append(f"Content too short: {len(content)} chars (minimum 800)")
    
    # Check for technical details
    technical_terms = ["api", "database", "frontend", "backend", "authentication", "deployment"]
    found_technical = sum(1 for term in technical_terms if term in content_lower)
    if found_technical < 4:
        issues.append(f"Insufficient technical detail: {found_technical}/4 technical terms")
    
    return len(issues) == 0, issues


def validate_architecture_design(content: str) -> Tuple[bool, List[str]]:
    """
    Validate technical architecture design quality
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    content_lower = content.lower()
    
    # Check for essential architecture components
    required_components = ["api", "database", "authentication", "security"]
    missing_components = []
    
    for component in required_components:
        if component not in content_lower:
            missing_components.append(component)
    
    if missing_components:
        issues.append(f"Missing architecture components: {', '.join(missing_components)}")
    
    # Check for scalability considerations
    scalability_terms = ["scale", "scalability", "load", "performance", "concurrent", "throughput"]
    found_scalability = sum(1 for term in scalability_terms if term in content_lower)
    if found_scalability == 0:
        issues.append("No scalability considerations mentioned")
    
    # Check minimum length
    if len(content) < 600:
        issues.append(f"Content too short: {len(content)} chars (minimum 600)")
    
    # Check for specific technology mentions
    tech_indicators = ["http", "rest", "json", "sql", "nosql", "redis", "docker", "cloud"]
    found_tech = sum(1 for tech in tech_indicators if tech in content_lower)
    if found_tech < 3:
        issues.append(f"Insufficient technology detail: {found_tech}/3 technology terms")
    
    return len(issues) == 0, issues


def extract_score_from_text(content: str) -> int:
    """Extract numerical score from text content"""
    score_patterns = [
        r'score[:\s]*([0-9]|10)',
        r'rating[:\s]*([0-9]|10)', 
        r'([0-9]|10)[/\s]*10',
        r'([0-9]|10)\s*out of\s*10'
    ]
    
    for pattern in score_patterns:
        match = re.search(pattern, content.lower())
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    
    return -1  # Invalid score


def validate_cost_tracking(actual_cost: float, expected_range: Tuple[float, float]) -> Tuple[bool, str]:
    """
    Validate that API costs are within expected range
    
    Returns:
        Tuple of (is_valid, issue_description)
    """
    min_cost, max_cost = expected_range
    
    if actual_cost < min_cost:
        return False, f"Cost too low: ${actual_cost:.4f} (expected >${min_cost:.4f})"
    elif actual_cost > max_cost:
        return False, f"Cost too high: ${actual_cost:.4f} (expected <${max_cost:.4f})"
    else:
        return True, f"Cost within range: ${actual_cost:.4f}"


def validate_response_time(actual_time: float, max_time: float = 30.0) -> Tuple[bool, str]:
    """
    Validate API response time
    
    Returns:
        Tuple of (is_valid, time_description)
    """
    if actual_time > max_time:
        return False, f"Response too slow: {actual_time:.2f}s (max {max_time}s)"
    else:
        return True, f"Response time acceptable: {actual_time:.2f}s"


def run_comprehensive_validation(scenario_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run comprehensive validation for a complete workflow
    
    Args:
        scenario_id: ID of the test scenario
        results: Dictionary containing all workflow results
    
    Returns:
        Dictionary with validation results
    """
    scenarios = load_test_scenarios()
    scenario = next((s for s in scenarios["scenarios"] if s["id"] == scenario_id), None)
    
    if not scenario:
        return {"error": f"Scenario {scenario_id} not found"}
    
    validation_results = {
        "scenario_id": scenario_id,
        "overall_valid": True,
        "validations": {},
        "issues": [],
        "metrics": {}
    }
    
    # Validate market research
    if "market_research" in results:
        is_valid, issues = validate_market_research(
            results["market_research"]["analysis"],
            scenario["expected_outputs"]["market_research"]
        )
        validation_results["validations"]["market_research"] = {
            "valid": is_valid,
            "issues": issues
        }
        if not is_valid:
            validation_results["overall_valid"] = False
            validation_results["issues"].extend(issues)
    
    # Validate founder analysis
    if "founder_analysis" in results:
        is_valid, issues = validate_founder_score(results["founder_analysis"]["analysis"])
        validation_results["validations"]["founder_analysis"] = {
            "valid": is_valid,
            "issues": issues
        }
        if not is_valid:
            validation_results["overall_valid"] = False
            validation_results["issues"].extend(issues)
    
    # Validate MVP specification
    if "mvp_spec" in results:
        is_valid, issues = validate_mvp_specification(
            results["mvp_spec"]["specification"],
            scenario["expected_outputs"]["mvp_features"]
        )
        validation_results["validations"]["mvp_spec"] = {
            "valid": is_valid,
            "issues": issues
        }
        if not is_valid:
            validation_results["overall_valid"] = False
            validation_results["issues"].extend(issues)
    
    # Validate architecture
    if "architecture" in results:
        is_valid, issues = validate_architecture_design(results["architecture"]["architecture"])
        validation_results["validations"]["architecture"] = {
            "valid": is_valid,
            "issues": issues
        }
        if not is_valid:
            validation_results["overall_valid"] = False
            validation_results["issues"].extend(issues)
    
    # Calculate metrics
    total_cost = sum(
        result.get("cost", 0) for result in results.values() 
        if isinstance(result, dict) and "cost" in result
    )
    validation_results["metrics"]["total_cost"] = total_cost
    
    # Validate total cost
    cost_valid, cost_msg = validate_cost_tracking(total_cost, (1.0, 8.0))
    validation_results["validations"]["cost_tracking"] = {
        "valid": cost_valid,
        "message": cost_msg
    }
    if not cost_valid:
        validation_results["overall_valid"] = False
        validation_results["issues"].append(cost_msg)
    
    return validation_results


if __name__ == "__main__":
    # Test the validation functions
    print("Testing validation helpers...")
    
    # Test market research validation
    test_research = """
    The electric vehicle charging market is experiencing rapid growth. 
    Market size reached $25 billion in 2024 with projected CAGR of 30%.
    Major competitors include Tesla Supercharger, Electrify America, and ChargePoint.
    Target audience includes EV owners, fleet operators, and charging network operators.
    """
    
    is_valid, issues = validate_market_research(test_research, ["competitors", "market size", "target audience"])
    print(f"Market research valid: {is_valid}")
    if issues:
        print(f"Issues: {issues}")
    
    print("Validation helpers test complete!")