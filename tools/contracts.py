from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Dict


@dataclass
class TaskEnvelope:
    task_id: str
    idempotency_key: str
    payload: Dict[str, Any]
    created_at: datetime = datetime.now(UTC)


@dataclass
class MessageEnvelope:
    message_id: str
    topic: str
    payload: Dict[str, Any]
    idempotency_key: str
    created_at: datetime = datetime.now(UTC)
