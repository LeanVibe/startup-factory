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


async def _gen_artifacts(industry: IndustryVertical):
    gen = BusinessLogicGenerator(anthropic_client=None)
    bp = BusinessBlueprint(
        founder_profile=FounderProfile(name="Compliance"),
        problem_statement=ProblemStatement(
            problem_description="Compliance",
            target_audience="Users",
        ),
        solution_concept=SolutionConcept(
            core_value_proposition="Compliance MVP",
            key_features=["Dashboard"],
            user_journey=["onboarding"],
            differentiation_factors=[],
            success_metrics=["Signups"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=industry,
        project_id="startup_compliance",
    )
    return await gen.generate_mvp_code(bp)


def test_config_includes_compliance_toggles():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts(IndustryVertical.GENERAL))
    cfg = next(a for a in arts if a.file_path == "backend/app/core/config.py")
    c = cfg.content
    assert "enable_hipaa" in c and "enable_pci" in c and "enable_ferpa" in c


def test_logging_redaction_mentions_extra_headers_for_pci_and_phi():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts(IndustryVertical.FINTECH))
    logmw = next(a for a in arts if a.file_path == "backend/app/middleware/logging.py")
    c = logmw.content
    # ensure extra headers are referenced and tied to settings toggles
    assert "stripe-signature" in c and "x-payment-token" in c
    assert "settings.enable_pci" in c or "enable_pci" in c
    # PHI/PII examples
    assert "x-ssn" in c or "phi" in c.lower() or "pii" in c.lower()


def test_security_middleware_contains_compliance_notes():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts(IndustryVertical.HEALTHCARE))
    sec = next(a for a in arts if a.file_path == "backend/app/middleware/security.py")
    c = sec.content
    assert "Compliance" in c and ("HIPAA" in c or "PCI" in c or "FERPA" in c)
