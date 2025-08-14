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


def test_manage_helper_has_print_routes_and_seed():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    helper = next(a for a in arts if a.file_path == "tools/manage.py")
    c = helper.content
    assert "def seed_basic_data(" in c
    assert "def print_routes(" in c


def test_readme_contains_seed_instructions():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    readme = next(a for a in arts if a.file_path == "README.md")
    txt = readme.content.lower()
    assert "seed" in txt and "manage.py" in txt
