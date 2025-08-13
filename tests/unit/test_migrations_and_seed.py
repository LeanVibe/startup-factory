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
        founder_profile=FounderProfile(name="Seed"),
        problem_statement=ProblemStatement(
            problem_description="Seed",
            target_audience="Dev",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Seed MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_seed",
    )
    return await gen.generate_mvp_code(bp)


def test_seed_and_migrate_scripts_and_ready_db_flag():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    present = {a.file_path for a in arts}
    assert "tools/seed_data.py" in present
    assert "scripts/migrate.sh" in present

    main = next(a for a in arts if a.file_path == "backend/app/main.py")
    assert "db_ok" in main.content or "db ok" in main.content.lower()
