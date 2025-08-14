def run(plan_context: dict, task: dict) -> dict:
    return {"status": "ok", "agent": "verifier", "task": task.get("name")}
