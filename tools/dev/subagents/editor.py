def run(plan_context: dict, task: dict) -> dict:
    return {"status": "ok", "agent": "editor", "task": task.get("name")}
