def run(plan_context: dict, task: dict) -> dict:
    return {"status": "ok", "agent": "tester", "task": task.get("name")}
