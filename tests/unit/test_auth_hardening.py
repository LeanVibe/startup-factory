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
        founder_profile=FounderProfile(name="Auth"),
        problem_statement=ProblemStatement(
            problem_description="Auth",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Auth MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_auth",
    )
    return await gen.generate_mvp_code(bp)


def test_auth_refresh_rotation_totp_and_csrf_cookie_mode():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    auth_api = next(a for a in arts if a.file_path == "backend/app/api/auth.py")
    c = auth_api.content
    # denylist/allowlist stub
    assert "_DENIED_REFRESH_TOKENS" in c or "_ALLOWED_REFRESH_TOKENS" in c
    # refresh rotation mentions jti and blacklist/denylist
    assert "refresh" in c and "jti" in c
    # TOTP endpoints
    assert "@router.post(\"/enable-totp\")" in c
    assert "@router.post(\"/disable-totp\")" in c
    # csrf cookie for cookie-mode login
    assert "csrf_token" in c and "set_cookie" in c
