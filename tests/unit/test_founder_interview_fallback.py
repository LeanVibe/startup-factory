import asyncio
import os

import pytest

from tools.founder_interview_system import (
    FounderInterviewAgent,
    FounderProfile,
    ProblemStatement,
    SolutionConcept,
    BusinessBlueprint,
    BusinessModel,
    IndustryVertical,
)


@pytest.mark.asyncio
async def test_intelligent_followups_without_api_key(monkeypatch):
    # Ensure no Anthropic key so agent uses intelligent fallback
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    agent = FounderInterviewAgent(anthropic_client=None)
    assert agent.client is None

    questions = await agent._intelligent_problem_followups(
        problem_desc="We need to automate HIPAA audit workflows for clinics",
        target_audience="Doctors and healthcare admins",
    )

    assert len(questions) <= 4 and len(questions) > 0
    # Should include healthcare-focused compliance question
    assert any("regulations" in q.lower() or "hipaa" in q.lower() for q in questions)


@pytest.mark.asyncio
async def test_intelligent_classification_and_spec_generation(monkeypatch):
    # No API key -> internal classification + spec generation fallbacks
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    agent = FounderInterviewAgent(anthropic_client=None)

    solution = SolutionConcept(
        core_value_proposition="HIPAA audit automation for small clinics",
        key_features=["Audit tracking", "Compliance dashboard", "Evidence export"],
        user_journey=["onboarding", "setup", "activation"],
        differentiation_factors=["Compliance automation"],
        success_metrics=["Onboarding completion", "Time saved"],
        monetization_strategy="subscription",
        pricing_model="$99/mo",
    )

    problem = ProblemStatement(
        problem_description="Manual HIPAA audits take hours and are error-prone",
        target_audience="Clinic admins and doctors",
        current_solutions=["Spreadsheets"],
        solution_gaps=["No automation", "Poor evidence trails"],
        pain_severity=8,
        market_size_estimate="$1B",
        validation_evidence=["Interviews with 10 clinics"],
    )

    business_model, industry = await agent._intelligent_business_classification(problem, solution)
    assert business_model in {
        BusinessModel.B2B_SAAS,
        BusinessModel.B2C_SAAS,
        BusinessModel.MARKETPLACE,
        BusinessModel.ECOMMERCE,
        BusinessModel.CONTENT_PLATFORM,
        BusinessModel.SERVICE_BUSINESS,
    }
    assert industry in {
        IndustryVertical.HEALTHCARE,
        IndustryVertical.FINTECH,
        IndustryVertical.EDUCATION,
        IndustryVertical.REAL_ESTATE,
        IndustryVertical.LOGISTICS,
        IndustryVertical.MEDIA,
        IndustryVertical.GENERAL,
    }

    blueprint = BusinessBlueprint(
        founder_profile=FounderProfile(
            name="Alex",
            technical_background=False,
            previous_startups=0,
            target_timeline="3_months",
            budget_constraints="bootstrap",
            team_size=1,
            primary_skills=["operations"],
            biggest_fear=None,
        ),
        problem_statement=problem,
        solution_concept=solution,
        business_model=business_model,
        industry_vertical=industry,
        project_id="startup_test",
    )

    # Generate technical specs (falls back to internal logic if real AI is not available)
    await agent._generate_technical_specs(blueprint)

    # Minimal assertions to ensure blueprint got populated
    assert isinstance(blueprint.data_entities, list)
    assert len(blueprint.data_entities) >= 1
    assert isinstance(blueprint.api_endpoints, list)
    assert len(blueprint.api_endpoints) >= 1
    assert isinstance(blueprint.tech_stack_recommendations, dict)
    assert blueprint.tech_stack_recommendations != {}
