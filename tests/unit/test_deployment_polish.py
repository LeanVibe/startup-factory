import json
import os
from pathlib import Path
import asyncio

from tools.deployers import get_deployer
from tools.day_one_experience import DayOneExperience
from tools.founder_interview_system import (
    FounderProfile,
    ProblemStatement,
    SolutionConcept,
    BusinessBlueprint,
    BusinessModel,
    IndustryVertical,
)


def test_get_deployer_railway_present():
    d = get_deployer("railway")
    assert type(d).__name__ == "RailwayDeployer"


async def _blueprint():
    return BusinessBlueprint(
        founder_profile=FounderProfile(name="Deploy"),
        problem_statement=ProblemStatement(problem_description="", target_audience=""),
        solution_concept=SolutionConcept(
            core_value_proposition="Deploy MVP",
            key_features=[],
            user_journey=[],
            differentiation_factors=[],
            success_metrics=[],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="proj_meta_polish",
    )


def test_project_metadata_includes_head_sha(tmp_path: Path, monkeypatch):
    # Arrange
    bp = asyncio.get_event_loop().run_until_complete(_blueprint())
    project_path = tmp_path / bp.project_id
    project_path.mkdir()
    monkeypatch.setenv("GITHUB_SHA", "deadbeef1234")

    day_one = DayOneExperience()
    # Simulate a deployment result as earlier
    deployment_result = {
        "public_url": "http://localhost:8000",
        "admin_url": "http://localhost:8000/admin",
        "api_docs_url": "http://localhost:8000/docs",
        "health_status": {"application": "healthy"},
    }

    # Act
    asyncio.get_event_loop().run_until_complete(
        day_one._write_project_metadata(project_path, bp, deployment_result)
    )

    # Assert
    meta = json.loads((project_path / "project.json").read_text())
    assert meta.get("head_sha") == "deadbeef1234"


def test_smoke_script_present_in_generated_app():
    # This artifact is emitted by the generator
    from tools.business_blueprint_generator import BusinessLogicGenerator

    gen = BusinessLogicGenerator(anthropic_client=None)
    bp = asyncio.get_event_loop().run_until_complete(_blueprint())
    arts = asyncio.get_event_loop().run_until_complete(gen.generate_mvp_code(bp))
    smoke = next(a for a in arts if a.file_path == "scripts/smoke.sh")
    assert "curl -fsS" in smoke.content and "/health" in smoke.content
