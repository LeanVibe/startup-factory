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
            problem_description="Org",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Org MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_orgctx",
    )
    return await gen.generate_mvp_code(bp)


def _by_path(arts):
    return {a.file_path: a for a in arts}


def test_org_context_helper_and_guard_membership_lookup():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    by = _by_path(arts)
    # helper emitted
    assert "backend/app/core/org_context.py" in by

    # rbac guard references org context and membership query
    rbac = by.get("backend/app/core/org_rbac.py")
    assert rbac is not None
    c = rbac.content
    assert "require_org_context" in c
    assert "Membership" in c and "organization_id" in c


def test_user_has_default_org_id_and_endpoints_use_org_context():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    by = _by_path(arts)
    user = by.get("backend/app/models/user.py")
    assert user is not None
    assert "default_org_id" in user.content

    # invitations uses org context in create/pending
    inv = by.get("backend/app/api/invitations.py")
    assert inv is not None
    ci = inv.content
    assert "require_org_context" in ci
    assert "organization_id=current_org" in ci or "organization_id = current_org" in ci
    assert "filter(Invitation.accepted_at == None)" in ci
