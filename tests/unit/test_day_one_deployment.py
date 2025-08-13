import json
import os
from pathlib import Path

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
import asyncio


def test_get_deployer_selection():
    assert type(get_deployer("fly")).__name__ == "FlyDeployer"
    assert type(get_deployer("render")).__name__ == "RenderDeployer"
    assert type(get_deployer("unknown")).__name__ == "BaseDeployer"


def test_write_project_metadata_persists_public_url_and_deployer(tmp_path: Path, monkeypatch):
    project_id = "proj_deploy_meta"
    project_path = tmp_path / project_id
    project_path.mkdir()

    # Build a minimal blueprint
    bp = BusinessBlueprint(
        founder_profile=FounderProfile(name="Founder"),
        problem_statement=ProblemStatement(problem_description="", target_audience=""),
        solution_concept=SolutionConcept(
            core_value_proposition="Test MVP",
            key_features=[],
            user_journey=[],
            differentiation_factors=[],
            success_metrics=[],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id=project_id,
    )

    # Simulate deployment result
    deployment_result = {
        "public_url": "http://example.com",
        "admin_url": "http://example.com/admin",
        "api_docs_url": "http://example.com/docs",
        "health_status": {"application": "healthy"},
    }

    # Ensure deployer metadata is captured
    monkeypatch.setenv("DEPLOY_TARGET", "fly")

    day_one = DayOneExperience()
    asyncio.get_event_loop().run_until_complete(
        day_one._write_project_metadata(project_path, bp, deployment_result)
    )

    meta_path = project_path / "project.json"
    assert meta_path.exists(), "project.json should be written"

    data = json.loads(meta_path.read_text())
    assert data["public_url"] == "http://example.com"
    assert data["deployer"] == "fly"
    assert data["project_id"] == project_id
