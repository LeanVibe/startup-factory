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
        founder_profile=FounderProfile(name="Billing"),
        problem_statement=ProblemStatement(
            problem_description="Billing",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Billing MVP",
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


def test_webhook_handler_updates_and_trials():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    svc = next(a for a in arts if a.file_path == "backend/app/services/billing_service.py")
    c = svc.content
    # Handles key Stripe events and updates fields
    assert "checkout.session.completed" in c
    assert "customer.subscription.updated" in c or "customer.subscription.created" in c
    assert "subscription_status" in c and "stripe_subscription_id" in c

    core = next(a for a in arts if a.file_path == "backend/app/core/billing.py")
    assert "trialing" in core.content  # guards should accept trialing


def test_plans_endpoint_and_plan_feature_mapping():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    api = next(a for a in arts if a.file_path == "backend/app/api/billing.py")
    assert "@router.get('/plans')" in api.content and '"plans":' in api.content

    core = next(a for a in arts if a.file_path == "backend/app/core/billing.py")
    cc = core.content
    assert "PLAN_FEATURES" in cc and "def require_plan_features" in cc
    # ensure mapping gate references PLAN_FEATURES and plan
    assert "getattr(current_user, 'plan'" in cc and "PLAN_FEATURES.get(" in cc
