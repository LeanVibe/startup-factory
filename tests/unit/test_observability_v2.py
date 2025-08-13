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
        founder_profile=FounderProfile(name="Obs"),
        problem_statement=ProblemStatement(
            problem_description="Obs",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Obs MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_obs",
    )
    return await gen.generate_mvp_code(bp)


def test_metrics_module_and_wiring_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    metrics = next(a for a in arts if a.file_path == "backend/app/core/metrics.py")
    mc = metrics.content
    assert "REQUEST_COUNT" in mc and "ERROR_COUNT" in mc and "def init_metrics" in mc

    main = next(a for a in arts if a.file_path == "backend/app/main.py")
    assert "init_metrics(app)" in main.content


def test_log_rotation_hook_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    main = next(a for a in arts if a.file_path == "backend/app/main.py")
    assert "RotatingFileHandler" in main.content
