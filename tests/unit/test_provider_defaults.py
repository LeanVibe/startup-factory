import asyncio
from datetime import datetime

import pytest

from tools.ai_providers import AIProviderManager, ProviderConfig, AIProviderInterface
from tools.core_types import Task, TaskType, TaskResult


class StubAnthropicProvider(AIProviderInterface):
    """Stub provider that simulates Anthropic without external calls."""

    def __init__(self, name: str = "anthropic"):
        self.name = name
        self.calls = []

    async def call_api(self, task: Task) -> TaskResult:
        self.calls.append(task.id)
        return TaskResult(
            task_id=task.id,
            startup_id=task.startup_id,
            success=True,
            content="OK",
            cost=0.0,
            provider_used=self.name,
            execution_time_seconds=0.001,
            tokens_used=10,
            quality_score=0.9,
            completed_at=datetime.utcnow(),
        )

    async def call_api_with_reliability(self, task: Task) -> TaskResult:
        return await self.call_api(task)

    def get_model_for_task(self, task_type: TaskType) -> str:
        return "stub-model"

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    async def health_check(self) -> bool:
        return True

    def get_metrics(self):
        return {"calls": len(self.calls)}


@pytest.mark.asyncio
async def test_process_task_defaults_to_anthropic_when_registered():
    manager = AIProviderManager()
    # Register stub Anthropic provider explicitly
    config = ProviderConfig(
        name="anthropic",
        api_key="dummy",
        models={},
        cost_per_input_token=0.0,
        cost_per_output_token=0.0,
        max_tokens=1000,
        max_concurrent=1,
    )
    stub = StubAnthropicProvider()
    manager.register_provider("anthropic", stub, config)

    task = Task(
        id="task_1",
        startup_id="startup_1",
        type=TaskType.MVP_SPECIFICATION,
        description="Generate MVP spec",
        prompt="Generate MVP specification for a B2B SaaS in healthcare.",
        max_tokens=200
    )

    result = await manager.process_task(task)

    assert result.success is True
    assert result.provider_used == "anthropic"
    assert stub.calls == ["task_1"]


@pytest.mark.asyncio
async def test_process_task_errors_if_anthropic_not_configured():
    manager = AIProviderManager()  # No providers registered

    task = Task(
        id="task_2",
        startup_id="startup_2",
        type=TaskType.ARCHITECTURE_DESIGN,
        description="Design architecture",
        prompt="Design a secure architecture for the MVP.",
        max_tokens=200
    )

    result = await manager.process_task(task)

    assert result.success is False
    assert "Anthropic provider not configured" in (result.error_message or "")
