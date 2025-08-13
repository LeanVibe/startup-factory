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
        founder_profile=FounderProfile(name="Org"),
        problem_statement=ProblemStatement(
            problem_description="Org RBAC",
            target_audience="Teams",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Org RBAC MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_orgs",
    )
    return await gen.generate_mvp_code(bp)


def test_invitations_api_and_router_inclusion():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    # invitations api emitted
    inv = next(a for a in arts if a.file_path == "backend/app/api/invitations.py")
    assert "@router.post('/')" in inv.content and "@router.post('/accept')" in inv.content
    assert "require_org_roles" in inv.content

    # main api router includes invitations and admin orgs
    main = next(a for a in arts if a.file_path == "backend/app/api/main.py")
    assert "api_router.include_router(invitations.router" in main.content
    assert "api_router.include_router(admin_orgs.router" in main.content


def test_org_rbac_membership_lookup_present():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    rbac = next(a for a in arts if a.file_path == "backend/app/core/org_rbac.py")
    c = rbac.content
    assert "Membership" in c and "db.query(Membership)" in c
    assert "require_org_roles" in c


def test_entity_update_uses_tenancy_dependency():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    # find any entity api (default Item)
    entity_api = next(a for a in arts if a.file_path == "backend/app/api/item.py")
    c = entity_api.content
    # update endpoint includes require_tenant dependency
    assert "def update_item(" in c and "current_tenant: int = Depends(require_tenant)" in c
