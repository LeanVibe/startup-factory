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
        founder_profile=FounderProfile(name="Admin"),
        problem_statement=ProblemStatement(
            problem_description="Admin",
            target_audience="Teams",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Admin MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_admin",
    )
    return await gen.generate_mvp_code(bp)


def test_admin_org_api_emitted_with_guards():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    admin_api = next(a for a in arts if a.file_path == "backend/app/api/admin_orgs.py")
    c = admin_api.content
    assert "require_org_roles" in c and "require_org_context" in c
    assert "@router.get('/orgs'" in c
    assert "@router.get('/orgs/{org_id}/members'" in c
    assert "@router.get('/orgs/{org_id}/invites'" in c


def test_admin_org_frontend_component_emitted():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    panel = next(a for a in arts if a.file_path == "frontend/src/components/admin-org-panel.ts")
    assert "admin-org-panel" in panel.content
    assert "/api/admin/orgs" in panel.content or "orgs" in panel.content.lower()
