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
        founder_profile=FounderProfile(name="CI"),
        problem_statement=ProblemStatement(
            problem_description="CI",
            target_audience="Dev",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="CI MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_ci",
    )
    return await gen.generate_mvp_code(bp)


def test_ci_test_workflow_and_smoke_test_emitted():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    present = {a.file_path for a in arts}
    assert ".github/workflows/test.yml" in present
    assert "backend/tests/test_app_smoke.py" in present
    assert "backend/pytest.ini" in present

    wf = next(a for a in arts if a.file_path == ".github/workflows/test.yml")
    assert "pytest -q" in wf.content and "ruff" in wf.content

    smoke = next(a for a in arts if a.file_path == "backend/tests/test_app_smoke.py")
    assert "TestClient" in smoke.content and "/health" in smoke.content
