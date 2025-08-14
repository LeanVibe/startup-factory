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
        founder_profile=FounderProfile(name="OpenAPI"),
        problem_statement=ProblemStatement(problem_description="desc", target_audience="ta"),
        solution_concept=SolutionConcept(
            core_value_proposition="OpenAPI MVP",
            key_features=["kf"],
            user_journey=["uj"],
            differentiation_factors=[],
            success_metrics=["sm"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="openapi_proj",
    )
    return await gen.generate_mvp_code(bp)


def test_openapi_enrichment_and_client_stub():
    arts = asyncio.get_event_loop().run_until_complete(_gen_artifacts())
    main_py = next(a for a in arts if a.file_path == "backend/app/main.py")
    txt = main_py.content
    assert "get_openapi" in txt and "components" in txt
    # Enriched metadata
    assert "title=app.title" in txt or "title=\"" in txt
    # Client stub script emitted
    assert any(a.file_path == "scripts/gen_client.sh" for a in arts)
    stub = next(a for a in arts if a.file_path == "scripts/gen_client.sh")
    assert "gen_client" in stub.content.lower() or "openapi" in stub.content.lower()
