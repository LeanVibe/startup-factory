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
        project_id="startup_org_rbac",
    )
    return await gen.generate_mvp_code(bp)


def _artifact_map(artifacts):
    return {a.file_path: a for a in artifacts}


def test_generator_emits_membership_and_pending_invites():
    artifacts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    by_path = _artifact_map(artifacts)

    # Membership model emitted
    assert "backend/app/models/membership.py" in by_path, "Membership model not emitted"

    # Invitations API has pending route and org-role check
    inv = by_path.get("backend/app/api/invitations.py")
    assert inv is not None, "Invitations API missing"
    content = inv.content
    assert "/pending" in content, "Pending invitations route not present"
    assert "require_org_roles" in content, "Org role guard missing in invitations API"


def test_org_rbac_checks_membership_lookup():
    artifacts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    by_path = _artifact_map(artifacts)

    org_rbac = by_path.get("backend/app/core/org_rbac.py")
    assert org_rbac is not None, "org_rbac helper missing"
    content = org_rbac.content
    # Minimal signal that membership check is wired
    assert "Membership" in content or "membership" in content, "Membership lookup not referenced in org_rbac"
    assert "get_db" in content, "DB dependency not referenced in org_rbac"


def test_entity_endpoints_include_tenancy_markers():
    artifacts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    by_path = _artifact_map(artifacts)

    # At least one generated entity endpoint should include tenancy markers
    entity_files = [p for p in by_path if p.startswith("backend/app/api/") and p.endswith(".py") and not p.endswith("auth.py") and not p.endswith("billing.py") and not p.endswith("files.py") and not p.endswith("jobs.py") and not p.endswith("main.py") and not p.endswith("workflows.py") and not p.endswith("invitations.py")]
    assert entity_files, "No entity endpoints generated to validate tenancy"

    any_has_tenancy_marker = False
    for path in entity_files:
        c = by_path[path].content
        if "tenant_id" in c:
            any_has_tenancy_marker = True
            break
    assert any_has_tenancy_marker, "Entity endpoints lack tenancy markers (tenant_id)"
