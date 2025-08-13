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
        founder_profile=FounderProfile(name="Flags"),
        problem_statement=ProblemStatement(
            problem_description="Flags",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Flags MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_flags",
    )
    return await gen.generate_mvp_code(bp)


def test_feature_flags_module_and_usage():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    ff = next(a for a in arts if a.file_path == "backend/app/core/feature_flags.py")
    assert "FEATURE_FLAGS" in ff.content and "def require_feature_flag" in ff.content

    # some API uses the guard
    apis = [a for a in arts if a.file_path.startswith("backend/app/api/") and a.file_path.endswith(".py")]
    assert any("require_feature_flag" in a.content for a in apis)


def test_logging_pii_redaction_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    logmw = next(a for a in arts if a.file_path == "backend/app/middleware/logging.py")
    c = logmw.content
    assert "Authorization" in c and "REDACTED" in c
    assert "def redact" in c or "redact_email" in c or "redact" in c.lower()
