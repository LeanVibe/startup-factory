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
            target_audience="Eng",
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


def test_main_has_ready_and_rotating_logs():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    main = next(a for a in arts if a.file_path == "backend/app/main.py")
    c = main.content
    assert "/ready" in c
    assert "RotatingFileHandler" in c


def test_lint_config_and_workflow_emitted():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    present = {a.file_path for a in arts}
    assert "pyproject.toml" in present
    lint_wf = next(a for a in arts if a.file_path == ".github/workflows/lint.yml")
    assert "ruff" in lint_wf.content
    py = next(a for a in arts if a.file_path == "pyproject.toml")
    assert "[tool.ruff]" in py.content
