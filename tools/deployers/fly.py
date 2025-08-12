import os
from pathlib import Path
from typing import Dict, Any

from .base import BaseDeployer


class FlyDeployer(BaseDeployer):
    name = "fly"

    def prepare_manifests(self, project_path: Path) -> Dict[str, Any]:
        fly_toml = project_path / 'fly.toml'
        if not fly_toml.exists():
            fly_toml.write_text('[app]\nname = "mvp-app"\n')
        return {"files": [str(fly_toml)]}

    def deploy(self, project_path: Path, env: Dict[str, str]) -> Dict[str, Any]:
        # Placeholder: return actionable message and ensure manifest exists
        self.prepare_manifests(project_path)
        return {
            "status": "pending",
            "message": "Run: flyctl launch && flyctl deploy (ensure FLY_API_TOKEN)",
            "public_url": "https://pending.fly.deploy"
        }
