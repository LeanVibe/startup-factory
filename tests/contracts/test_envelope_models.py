from tools import contracts


def test_task_envelope_schema_minimal():
    env = contracts.TaskEnvelope(task_id="t1", idempotency_key="k1", payload={"a":1})
    assert env.task_id == "t1" and env.idempotency_key == "k1"


def test_message_envelope_schema_minimal():
    env = contracts.MessageEnvelope(message_id="m1", topic="work", payload={"b":2}, idempotency_key="k2")
    assert env.topic == "work" and env.payload["b"] == 2
