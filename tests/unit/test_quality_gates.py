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
        founder_profile=FounderProfile(name="Quality"),
        problem_statement=ProblemStatement(
            problem_description="Quality",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Quality MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_quality",
    )
    return await gen.generate_mvp_code(bp)


def test_generated_security_header_tests_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    sec = next(a for a in arts if a.file_path == "backend/tests/test_security_headers.py")
    assert "X-Content-Type-Options" in sec.content and "X-Frame-Options" in sec.content


def test_generated_metrics_tests_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    met = next(a for a in arts if a.file_path == "backend/tests/test_metrics.py")
    assert "/metrics" in met.content and "CONTENT_TYPE_LATEST" in met.content


def test_generated_logging_redaction_tests_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    red = next(a for a in arts if a.file_path == "backend/tests/test_logging_redaction.py")
    assert "Authorization" in red.content and "REDACTED" in red.content


def test_manage_helper_emitted():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    helper = next(a for a in arts if a.file_path == "tools/manage.py")
    assert "create_demo_user" in helper.content and "print_status" in helper.content
