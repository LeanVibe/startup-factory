from tools.day_one_experience import read_latest_project_metadata


def test_status_summary_is_compact(tmp_path, monkeypatch):
    # Create minimal project.json
    pj = tmp_path / "p1" / "project.json"
    pj.parent.mkdir(parents=True)
    pj.write_text('{"public_url":"http://x","deployer":"fly","head_sha":"abc"}')

    from tools import day_one_experience
    res = day_one_experience.read_latest_project_metadata(tmp_path)
    assert res["public_url"] == "http://x" and res["deployer"] == "fly" and res["head_sha"] == "abc"
