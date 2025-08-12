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
        founder_profile=FounderProfile(name="Test"),
        problem_statement=ProblemStatement(
            problem_description="Test",
            target_audience="Testers",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Test MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_smoke",
    )
    return await gen.generate_mvp_code(bp)


def test_generator_emits_scaffold():
    artifacts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    present = {a.file_path for a in artifacts}
    required = {
        "backend/app/main.py",
        "backend/app/db/database.py",
        "backend/app/core/security.py",
        "alembic/env.py",
        "frontend/index.html",
        "docker-compose.yml",
        "Dockerfile",
    }
    missing = required - present
    assert not missing, f"Missing artifacts: {sorted(missing)}"
