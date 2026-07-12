"""
Orchestrator.

Runs the five agents in sequence. Each agent streams tokens; the orchestrator
emits Server-Sent-Event payloads the frontend consumes to drive the live relay.
Feeds every completed agent's output forward as context to the next.

One agent failing does not kill the pipeline — it's marked failed and the run
continues, so a single transient error never wastes the whole brief.
"""
import asyncio
import json
from typing import AsyncIterator

from . import agents, config, database, demo_data


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_agent_text(agent_id: str, brief: dict, context: dict) -> AsyncIterator[str]:
    """Yield text chunks for one agent, in LIVE or DEMO mode."""
    if config.LIVE_MODE:
        from . import claude_client
        prompt = agents.build_prompt(agent_id, brief, context)
        async for chunk in claude_client.stream_completion(prompt):
            yield chunk
    else:
        text = demo_data.demo_output(agent_id, brief)
        # Stream word-by-word so the relay reads as genuine thinking.
        buf = []
        for word in text.split(" "):
            buf.append(word)
            if len(buf) >= 3:
                yield " ".join(buf) + " "
                buf = []
                await asyncio.sleep(config.DEMO_CHUNK_DELAY)
        if buf:
            yield " ".join(buf)


async def run_pipeline(run_id: str, brief: dict) -> AsyncIterator[str]:
    mode = config.mode_label()
    database.create_run(run_id, brief, mode)

    yield _sse("run_started", {
        "run_id": run_id,
        "mode": mode,
        "agents": [
            {"id": a["id"], "name": a["name"], "role": a["role"], "icon": a["icon"]}
            for a in agents.AGENTS
        ],
    })

    context: dict = {}
    outputs: dict = {}

    for agent in agents.AGENTS:
        aid = agent["id"]
        yield _sse("agent_started", {"id": aid, "name": agent["name"]})
        await asyncio.sleep(config.DEMO_AGENT_PAUSE if not config.LIVE_MODE else 0)

        collected = []
        try:
            async for chunk in _stream_agent_text(aid, brief, context):
                collected.append(chunk)
                yield _sse("agent_chunk", {"id": aid, "text": chunk})
            full = "".join(collected).strip()
            outputs[aid] = full
            context[agent["name"]] = full
            yield _sse("agent_done", {"id": aid})
        except Exception as exc:  # noqa: BLE001
            msg = f"_This agent hit an error and was skipped: {exc}_"
            outputs[aid] = msg
            yield _sse("agent_error", {"id": aid, "error": str(exc)})

    database.finalize_run(run_id, outputs, "complete")
    yield _sse("run_complete", {"run_id": run_id, "outputs": outputs})
