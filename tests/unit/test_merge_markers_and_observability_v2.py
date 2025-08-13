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
        founder_profile=FounderProfile(name="Obs2"),
        problem_statement=ProblemStatement(
            problem_description="Obs2",
            target_audience="Eng",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Obs2 MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_obs2",
    )
    return await gen.generate_mvp_code(bp)


def test_merge_markers_and_metrics_labels():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    # merge markers in key files (top comment)
    main = next(a for a in arts if a.file_path == "backend/app/main.py")
    assert "BEGIN GENERATED SECTION" in main.content

    metrics = next(a for a in arts if a.file_path == "backend/app/core/metrics.py")
    c = metrics.content
    assert "Counter(" in c and "error" in c.lower()
