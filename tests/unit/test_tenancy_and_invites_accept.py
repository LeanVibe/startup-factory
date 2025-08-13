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
        founder_profile=FounderProfile(name="Ten"),
        problem_statement=ProblemStatement(
            problem_description="Ten",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Ten MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="startup_tenancy",
    )
    return await gen.generate_mvp_code(bp)


def _by_path(arts):
    return {a.file_path: a for a in arts}


def test_tenancy_helper_and_usage_in_entity_endpoints():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    by = _by_path(arts)
    assert "backend/app/core/tenancy.py" in by

    # find an entity endpoint (exclude known non-entity files)
    paths = [p for p in by if p.startswith("backend/app/api/") and p.endswith(".py") and p.split("/")[-1] not in {"auth.py","billing.py","files.py","jobs.py","main.py","workflows.py","invitations.py","__init__.py"}]
    assert paths, "No entity endpoints available"
    sample = by[paths[0]].content
    assert "from app.core.tenancy import require_tenant" in sample
    assert "current_tenant: int = Depends(require_tenant)" in sample
    # list filters by tenant if field exists
    assert "if hasattr(" in sample and "tenant_id" in sample


def test_invitation_accept_creates_membership():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    by = _by_path(arts)
    inv = by.get("backend/app/api/invitations.py")
    assert inv is not None
    c = inv.content
    assert "from app.models.membership import Membership" in c
    assert "Membership(" in c or "db.add(Membership" in c
