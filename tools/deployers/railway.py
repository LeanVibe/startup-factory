from .base import BaseDeployer
from pathlib import Path


class RailwayDeployer(BaseDeployer):
    name = "railway"

    def deploy(self, project_path: Path, env: dict | None = None) -> dict:
        # Stub: write minimal Railway config if desired; return placeholder URL
        (project_path / "railway.json").write_text('{"service":"web"}')
        return {"public_url": "https://pending.railway.app"}
