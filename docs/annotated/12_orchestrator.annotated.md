# Annotated: `orchestrator.py` — the pipeline

This is the heart of AEGIS. `run_pipeline` runs the five agents in order, chooses
the text source per mode, streams every chunk as an SSE frame, feeds each
finished output forward as context to the next agent, persists the run, and never
lets one agent's failure kill the whole thing.

**Data flow:** `main.start_run` calls `run_pipeline(run_id, brief)` and pipes its
yielded strings straight into a `StreamingResponse`. Each yielded string is one
`event: …\ndata: …\n\n` SSE frame.

```python
1-10  """Orchestrator. Runs the five agents in sequence ... emits SSE payloads ...
       feeds every completed agent's output forward as context to the next.
       One agent failing does not kill the pipeline."""
11  import asyncio
12  import json
13  from typing import AsyncIterator
15  from . import agents, config, database, demo_data   # NOTE: claude_client imported lazily, not here
```
- `claude_client` is deliberately **absent** from this import line — it's imported
  inside `_stream_agent_text` only when LIVE, preserving the "DEMO can't break"
  guarantee.

```python
18  def _sse(event: str, data: dict) -> str:
19      return f"event: {event}\ndata: {json.dumps(data)}\n\n"
```
- The one place SSE framing is built. Format: an `event:` line, a `data:` line
  with a JSON payload, then a blank line to terminate the frame. The frontend's
  `EventSource` dispatches on the `event:` name.

```python
22  async def _stream_agent_text(agent_id, brief, context) -> AsyncIterator[str]:
23      """Yield text chunks for one agent, in LIVE or DEMO mode."""
24      if config.LIVE_MODE:
25          from . import claude_client                        # lazy LIVE-only import
26          prompt = agents.build_prompt(agent_id, brief, context)  # full context-aware prompt
27          async for chunk in claude_client.stream_completion(prompt):
28              yield chunk                                    # real Claude tokens
29      else:
30          text = demo_data.demo_output(agent_id, brief)      # whole canned block
31          # Stream word-by-word so the relay reads as genuine thinking.
32          buf = []
33          for word in text.split(" "):
34              buf.append(word)
35              if len(buf) >= 3:                              # emit every 3 words
36                  yield " ".join(buf) + " "
37                  buf = []
38                  await asyncio.sleep(config.DEMO_CHUNK_DELAY)  # pacing between batches
39          if buf:
40              yield " ".join(buf)                            # flush the remainder
```
- This function is the **mode abstraction**: the rest of the pipeline consumes an
  async stream of text chunks and doesn't care whether they came from Claude or
  from `demo_data`.
- **LIVE (24–28):** builds the context-aware prompt and forwards Claude's tokens.
- **DEMO (29–40):** takes the entire canned string and *re-chunks* it into 3-word
  batches with a small `DEMO_CHUNK_DELAY` sleep, so DEMO output types out live
  instead of appearing all at once. Lines 39–40 flush any 1–2 word tail.

```python
43  async def run_pipeline(run_id: str, brief: dict) -> AsyncIterator[str]:
44      mode = config.mode_label()               # "DEMO" | "LIVE"
45      database.create_run(run_id, brief, mode) # persist immediately as status "running"

47      yield _sse("run_started", {              # tell the UI the roster + mode up front
48          "run_id": run_id,
49          "mode": mode,
50-53       "agents": [{"id","name","role","icon"} for a in agents.AGENTS],
54      })

56      context: dict = {}   # {AgentName → output}, grows each iteration; fed to build_prompt
57      outputs: dict = {}   # {agent_id → output}, the persisted/exported result
```
- **Line 45:** the run is written to SQLite *before* any generation, so even a
  crashed run leaves a `running` row you can inspect.
- **Line 47:** `run_started` carries the whole roster so the frontend can render
  the five relay nodes before any text arrives.
- **Two dicts, two key schemes (56–57):** `context` is keyed by **display name**
  (what `_prior` renders into prompts); `outputs` is keyed by **id** (what the DB,
  export, and SSE events use). Keeping them separate avoids leaking display
  formatting into the stored data.

```python
59      for agent in agents.AGENTS:              # fixed roster order = pipeline order
60          aid = agent["id"]
61          yield _sse("agent_started", {"id": aid, "name": agent["name"]})
62          await asyncio.sleep(config.DEMO_AGENT_PAUSE if not config.LIVE_MODE else 0)  # beat before DEMO agents

64          collected = []
65          try:
66              async for chunk in _stream_agent_text(aid, brief, context):
67                  collected.append(chunk)                       # accumulate for persistence
68                  yield _sse("agent_chunk", {"id": aid, "text": chunk})  # live to UI
69              full = "".join(collected).strip()                 # this agent's complete output
70              outputs[aid]           = full                     # store by id
71              context[agent["name"]] = full                     # expose to LATER agents by name
72              yield _sse("agent_done", {"id": aid})
73          except Exception as exc:  # noqa: BLE001
74              msg = f"_This agent hit an error and was skipped: {exc}_"
75              outputs[aid] = msg                                # record the skip in outputs
76              yield _sse("agent_error", {"id": aid, "error": str(exc)})
77              # NB: no re-raise → the for-loop continues to the next agent
```
- **The forward-feeding loop.** Each agent streams (66–68), its full text is
  assembled (69), stored (70), and — crucially — added to `context` under its
  display name (71) so the *next* agent's `build_prompt` includes it. That single
  line is what turns five independent agents into a coherent chain.
- **Line 62:** in DEMO, a `DEMO_AGENT_PAUSE` beat before each agent makes the relay
  feel like a team handing off work. In LIVE the pause is `0` (Claude latency
  already provides the rhythm).
- **Per-agent resilience (73–77):** any exception — including a `RuntimeError`
  bubbled up from `claude_client` after its retries — is caught *here*. The agent
  is marked skipped in both the outputs and via an `agent_error` event, and the
  loop moves on. No `raise`, so one bad agent never wastes the other four.

```python
78      database.finalize_run(run_id, outputs, "complete")   # persist final outputs, flip status
79      yield _sse("run_complete", {"run_id": run_id, "outputs": outputs})  # UI assembles the brief
```
- **Line 78:** the run row is updated with the full outputs and status
  `complete` — this is what `/api/runs` history and `/export.md` later read.
- **Line 79:** `run_complete` hands the frontend the entire outputs map so it can
  render the finished brief and enable the download/copy actions. Note the run is
  marked `complete` even if some agents were skipped — "complete" here means "the
  pipeline finished", not "every agent succeeded".
