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
        founder_profile=FounderProfile(name="Sec"),
        problem_statement=ProblemStatement(
            problem_description="Sec",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Sec MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_sec",
    )
    return await gen.generate_mvp_code(bp)


def test_openapi_oauth2_and_global_security_placeholder():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    main = next(a for a in arts if a.file_path == "backend/app/main.py")
    c = main.content
    assert "securitySchemes" in c and "oauth2" in c
    assert "schema['security']" in c or 'schema["security"]' in c


def test_cookie_mode_csrf_notes_in_auth():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    auth = next(a for a in arts if a.file_path == "backend/app/api/auth.py")
    c = auth.content
    assert "CSRF" in c and "cookie mode" in c.lower()


def test_httpbearer_declared_in_entity_router():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    entity = next(a for a in arts if a.file_path == "backend/app/api/item.py")
    c = entity.content
    assert "from fastapi.security import HTTPBearer" in c and "security = HTTPBearer()" in c


def test_rate_limit_override_header_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    rl = next(a for a in arts if a.file_path == "backend/app/middleware/rate_limit.py")
    c = rl.content
    assert "X-RateLimit-Limit" in c or "X-RateLimit-Override" in c
