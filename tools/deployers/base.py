from pathlib import Path
from typing import Dict, Any


class BaseDeployer:
    name = "base"

    def prepare_manifests(self, project_path: Path) -> Dict[str, Any]:
        return {"message": "No cloud deployer selected", "project_path": str(project_path)}

    def deploy(self, project_path: Path, env: Dict[str, str]) -> Dict[str, Any]:
        # Default: return local URL message
        return {
            "status": "skipped",
            "message": "Use tunnel or docker-compose locally",
            "public_url": "http://localhost:8000",
        }
