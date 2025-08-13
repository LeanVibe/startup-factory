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
        founder_profile=FounderProfile(name="Bill2"),
        problem_statement=ProblemStatement(
            problem_description="Bill2",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Bill2 MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_billing2",
    )
    return await gen.generate_mvp_code(bp)


def test_billing_guards_and_plans_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    # billing core should have require_plan_features
    billing_core = next(a for a in arts if a.file_path == "backend/app/core/billing.py")
    assert "def require_plan_features" in billing_core.content

    # some endpoint should import and use require_plan_features
    api_files = [a for a in arts if a.file_path.startswith("backend/app/api/") and a.file_path.endswith(".py")]
    uses_guard = any("require_plan_features(" in a.content for a in api_files)
    assert uses_guard, "No API endpoint uses require_plan_features guard"
