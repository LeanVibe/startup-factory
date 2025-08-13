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
        founder_profile=FounderProfile(name="Bill"),
        problem_statement=ProblemStatement(
            problem_description="Bill",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Bill MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_billing",
    )
    return await gen.generate_mvp_code(bp)


def test_billing_service_handles_minimal_stripe_events():
    artifacts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    svc = next(a for a in artifacts if a.file_path == "backend/app/services/billing_service.py")
    c = svc.content
    assert "checkout.session.completed" in c
    assert "customer.subscription.updated" in c or "customer.subscription.created" in c
    assert "stripe_customer_id" in c
    assert "stripe_subscription_id" in c
    assert "subscription_status" in c


def test_billing_api_exposes_plans_endpoint():
    artifacts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    api = next(a for a in artifacts if a.file_path == "backend/app/api/billing.py")
    c = api.content
    assert "/plans" in c
    assert "plans" in c.lower()
