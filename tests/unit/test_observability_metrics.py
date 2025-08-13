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
            target_audience="Eng",
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


def test_generator_emits_metrics_and_main_wires_it():
    artifacts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    present = {a.file_path for a in artifacts}
    assert "backend/app/core/metrics.py" in present
    # check main contains metrics init import
    main = next(a for a in artifacts if a.file_path == "backend/app/main.py")
    assert "from app.core.metrics" in main.content
    assert "init_metrics(app)" in main.content
