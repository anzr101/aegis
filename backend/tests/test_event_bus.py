"""Event bus pub/sub behaviour."""
import asyncio

from app.schemas import AgentEvent, AgentStatus


async def test_subscriber_receives_events_and_terminates(bus):
    received = []

    async def consume():
        async for event in bus.subscribe("run-1"):
            received.append(event)

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.01)  # let the subscriber register

    await bus.publish("run-1", AgentEvent(agent_name="trend_agent", status=AgentStatus.RUNNING))
    await bus.publish("run-1", AgentEvent(agent_name="__pipeline__", status=AgentStatus.COMPLETED))
    await asyncio.wait_for(consumer, timeout=2)

    assert len(received) == 2
    assert received[-1].status == AgentStatus.COMPLETED
    # subscriber cleaned up after terminal event
    assert "run-1" not in bus._subscribers


async def test_multiple_subscribers_get_same_events(bus):
    counts = {"a": 0, "b": 0}

    async def consume(key):
        async for _ in bus.subscribe("run-2"):
            counts[key] += 1

    tasks = [asyncio.create_task(consume("a")), asyncio.create_task(consume("b"))]
    await asyncio.sleep(0.01)

    await bus.publish("run-2", AgentEvent(agent_name="x", status=AgentStatus.RUNNING))
    await bus.publish("run-2", AgentEvent(agent_name="__pipeline__", status=AgentStatus.FAILED))
    await asyncio.wait_for(asyncio.gather(*tasks), timeout=2)

    assert counts == {"a": 2, "b": 2}


async def test_events_for_other_runs_not_delivered(bus):
    received = []

    async def consume():
        async for event in bus.subscribe("run-3"):
            received.append(event)

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.01)

    await bus.publish("other-run", AgentEvent(agent_name="x", status=AgentStatus.RUNNING))
    await bus.publish("run-3", AgentEvent(agent_name="__pipeline__", status=AgentStatus.COMPLETED))
    await asyncio.wait_for(consumer, timeout=2)

    assert len(received) == 1
