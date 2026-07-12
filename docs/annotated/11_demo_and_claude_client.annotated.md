# Annotated: `demo_data.py`, `claude_client.py` — the two text sources

Every chunk of agent text comes from exactly one of these files, chosen by
`orchestrator._stream_agent_text` based on `config.LIVE_MODE`:
- **DEMO** → `demo_data.demo_output` (canned, brief-adaptive, no network).
- **LIVE** → `claude_client.stream_completion` (real Claude, streamed).

---

## `backend/demo_data.py` — brief-adaptive canned output

**Data flow:** `demo_output(agent_id, brief)` returns a finished Markdown string
for one agent. The orchestrator then slices it into small word-batches to *stream*
it, so DEMO visually behaves like LIVE.

```python
1-7   """DEMO-mode output ... realistic deliverables that interpolate the actual brief
                              so the pipeline feels responsive without an API key."""

10  def _g(brief: dict, key: str, default: str) -> str:
11      v = (brief.get(key) or "").strip()   # None OR "" both collapse to ""
12      return v if v else default            # blank → default (never render an empty field)
```
- `_g` is a stricter getter than `dict.get`: a *present but blank* field
  (`""` / whitespace / `None`) still falls back to `default`. This is why demo
  copy never shows an empty budget or a stray "None".

```python
15  def demo_output(agent_id: str, brief: dict) -> str:
16-21   brand    = _g(brief, "brand",    "the brand")
        product  = _g(brief, "product",  "the offering")
        audience = _g(brief, "audience", "urban Indian consumers, 22–38")
        market   = _g(brief, "market",   "India (metro + tier-1)")
        goal     = _g(brief, "goal",     "build awareness and qualified demand")
        budget   = _g(brief, "budget",   "₹15,00,000")   # sensible INR default
```
- Six brief fields are pulled once with rich, India-flavoured defaults, then
  interpolated into each agent's block below. This is what makes the demo feel
  bespoke — your `brand`/`budget`/`audience` literally appear in the output.

```python
23  if agent_id == "research":
24-43   return f"""... Market read — {market} ... 3 audience segments (Aspirant/Loyalist/Drifter) ...
               4 cultural signals ... biggest opportunity / biggest risk (spreading {budget} thin) ..."""

45  if agent_id == "competitor":
46-59   return f"""... competitive field table (Loud Discounter / Heritage Player / Upstart) ...
               2 positioning gaps ... white space: the "knowing insider" tone ..."""

61  if agent_id == "strategy":
62-78   return f"""... BIG IDEA "Made to be noticed. Built to be kept." ... 3 messaging pillars ...
               primary KPI tied to {goal} + secondary KPIs ..."""

80  if agent_id == "creative":
81-104  return f"""... 3 hooks (one uses {brand}) ... hero Reel copy about {product} ...
               a 2-week content calendar as a markdown table ..."""

106 if agent_id == "media":
107-124 return f"""... channel-mix table vs {budget} (Meta 45% / Shorts 20% / Influencer 20% /
               Search 10% / CRM 5%) ... projected outcome tied to {goal} ... measurement cadence ..."""

126 return f"(No demo content registered for agent '{agent_id}'.)"   # graceful fallback, no raise
```
- Each branch returns Markdown that mirrors the **exact structure the LIVE prompt
  asks for** (tables, pillar lists, calendars) — so DEMO and LIVE output are
  interchangeable in the UI and export.
- The final `return` (line 126) means an unknown `agent_id` yields a harmless
  placeholder instead of raising — the opposite choice from `agents.build_prompt`,
  which is intentional: demo should never crash the relay.

---

## `backend/claude_client.py` — Anthropic streaming + retries (LIVE only)

**Data flow:** only reached when `config.LIVE_MODE` is true. `stream_completion`
is an async generator that yields text chunks; the orchestrator forwards each
chunk straight into an `agent_chunk` SSE event.

```python
1-6   """Thin Anthropic client with streaming + retries. Only imported/used in LIVE mode.
       In DEMO mode this file is never touched, so a missing `anthropic` package
       can't break a fresh install."""
7   import asyncio
8   from typing import AsyncIterator
10  from . import config

13  async def stream_completion(prompt: str, max_retries: int = 3) -> AsyncIterator[str]:
14      """Yield text chunks from Claude. Retries on transient errors."""
15      from anthropic import AsyncAnthropic     # imported LAZILY — dep only needed in LIVE

17      client  = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
18      attempt = 0
19      while True:                              # retry loop
20          attempt += 1
21          try:
22              async with client.messages.stream(
23                  model=config.MODEL,
24                  max_tokens=1400,             # caps one agent's output length
25                  messages=[{"role": "user", "content": prompt}],
26              ) as stream:
27                  async for text in stream.text_stream:
28                      yield text               # forward each token batch to the caller
29                  return                       # SUCCESS — leave the retry loop
30          except Exception as exc:  # noqa: BLE001 — surface a clean message upward
31              if attempt >= max_retries:
32                  raise RuntimeError(
33                      f"Claude request failed after {max_retries} attempts: {exc}"
34                  ) from exc               # give up → orchestrator catches this per-agent
35              await asyncio.sleep(0.8 * attempt)   # linear backoff: 0.8s, 1.6s, then raise
```
- **Line 15** is the reason DEMO installs can't break: `anthropic` is imported
  *inside* the function, so importing this module (or running the whole app in
  DEMO) never requires the package to be installed.
- **Lines 22–28** use the SDK's streaming context manager. `stream.text_stream`
  yields incremental text; `yield text` (line 28) passes it upward without
  buffering, which is what makes tokens appear live in the browser.
- **Line 29** `return` inside the `while True` is the success exit — without it the
  loop would re-run and duplicate the whole response.
- **Retry policy:** up to `max_retries` attempts (default 3). A *transient* error
  sleeps and retries; the *final* failure is re-raised as a `RuntimeError` with a
  clean message. That exception propagates to `orchestrator.run_pipeline`, whose
  per-agent `try/except` records it as a skipped section — so even a hard Claude
  outage only damages one part of the brief.
- `# noqa: BLE001` acknowledges the deliberately broad `except Exception`: any SDK
  error (network, rate-limit, auth) should be retried/surfaced uniformly.
