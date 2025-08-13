import asyncio

from tools.founder_interview_system import (
    FounderProfile,
    ProblemStatement,
    SolutionConcept,
    BusinessBlueprint,
    BusinessModel,
    IndustryVertical,
)
from tools.business_blueprint_generator import BusinessLogicGenerator


async def _gen_artifacts():
    gen = BusinessLogicGenerator(anthropic_client=None)
    bp = BusinessBlueprint(
        founder_profile=FounderProfile(name="Bill3"),
        problem_statement=ProblemStatement(
            problem_description="Bill3",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Bill3 MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_billing3",
    )
    return await gen.generate_mvp_code(bp)


def test_billing_service_optional_signature_and_persistence_stub():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    svc = next(a for a in arts if a.file_path == "backend/app/services/billing_service.py")
    c = svc.content
    assert "STRIPE_WEBHOOK_SECRET" in c
    assert "construct_event" in c or "Webhook" in c
    # persistence hints
    assert "from app.models.user import User" in c
    assert "db.query(User)" in c or "Session" in c


def test_billing_core_usage_limit_and_me_endpoint():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    core = next(a for a in arts if a.file_path == "backend/app/core/billing.py")
    cc = core.content
    assert "def require_usage_limit" in cc

    api = next(a for a in arts if a.file_path == "backend/app/api/billing.py")
    ac = api.content
    assert "/me" in ac
    assert "subscription_status" in ac
    assert "plan" in ac.lower()
    assert "/plans" in ac and "features" in ac
