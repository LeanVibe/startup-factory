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
        founder_profile=FounderProfile(name="DX"),
        problem_statement=ProblemStatement(
            problem_description="DX",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="DX MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_dx",
    )
    return await gen.generate_mvp_code(bp)


def test_max_limit_clamp_and_readme_api_conventions():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    # Find any entity router
    any_router = [a for a in arts if a.file_path.startswith("backend/app/api/") and a.file_path.endswith(".py")]
    assert any_router, "expected at least one router"
    router_code = any_router[0].content
    assert "limit = min(limit, 500)" in router_code

    readme = next(a for a in arts if a.file_path == "README.md")
    assert "API conventions" in readme.content
