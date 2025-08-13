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


def test_env_template_and_makefile_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    envt = next(a for a in arts if a.file_path == ".env.template")
    mk = next(a for a in arts if a.file_path == "Makefile")
    assert "DATABASE_URL" in envt.content and "SECRET_KEY" in envt.content
    assert "run:" in mk.content and "test:" in mk.content


def test_manage_helper_extended():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    helper = next(a for a in arts if a.file_path == "tools/manage.py")
    c = helper.content
    assert "def health(" in c and "def seed_basic_data(" in c


def test_readme_has_getting_started():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    readme = next(a for a in arts if a.file_path == "README.md")
    assert "Getting Started" in readme.content and "docker-compose up" in readme.content
