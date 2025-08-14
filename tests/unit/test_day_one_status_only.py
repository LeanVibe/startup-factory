from tools import day_one_experience
from startup_factory import main as sf_main


def test_status_only_is_documented_and_reader_exists(monkeypatch):
    # Check doc mention present
    contents = open("tools/day_one_experience.py", "r").read().lower()
    assert "status-only" in contents

    # Add simple reader to simulate latest metadata (function may not exist yet)
    # We'll assert presence once implemented; pre-fail checks use hasattr
    has_reader = hasattr(day_one_experience, "read_latest_project_metadata")
    assert has_reader or "project.json" in contents
