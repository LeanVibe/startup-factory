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


def test_scripts_and_status_only_mentions():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    smoke = next(a for a in arts if a.file_path == "scripts/smoke.sh")
    # New dev.sh script required
    assert any(a.file_path == "scripts/dev.sh" for a in arts)
    dev = next(a for a in arts if a.file_path == "scripts/dev.sh")
    content = dev.content
    assert "up)" in content and "down)" in content and "status)" in content

    # Day One docs mention status-only path
    day_one = open("tools/day_one_experience.py", "r").read()
    assert "status-only" in day_one or "status only" in day_one
