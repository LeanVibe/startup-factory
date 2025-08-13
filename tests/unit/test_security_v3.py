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
        founder_profile=FounderProfile(name="Sec3"),
        problem_statement=ProblemStatement(
            problem_description="Sec3",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Sec3 MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_sec3",
    )
    return await gen.generate_mvp_code(bp)


def test_password_policy_and_csrf_and_cors_strings():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    auth = next(a for a in arts if a.file_path == "backend/app/api/auth.py")
    c = auth.content
    assert "password" in c and "len(password)" in c and "any(ch.isdigit" in c
    main = next(a for a in arts if a.file_path == "backend/app/main.py")
    m = main.content
    assert "CORSMiddleware" in m and "allow_origins=settings.cors_allow_origins" in m


def test_error_handler_middleware_and_csp_nonce_comment():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    err = next(a for a in arts if a.file_path == "backend/app/middleware/errors.py")
    assert "BaseHTTPMiddleware" in err.content and "JSONResponse" in err.content
    main = next(a for a in arts if a.file_path == "backend/app/main.py")
    assert "ErrorHandlerMiddleware" in main.content
    sec = next(a for a in arts if a.file_path == "backend/app/middleware/security.py")
    assert "CSP" in sec.content and "nonce" in sec.content.lower()
