# Annotated: `config.py`, `__init__.py`, `agents.py` — foundation & agent roster

These three files are the pure, I/O-light core. `config.py` decides which mode
the app runs in and exposes all paths/constants; `__init__.py` marks the package;
`agents.py` holds the static agent roster and builds each agent's prompt.

---

## `backend/__init__.py` — package marker

```python
1  """AEGIS — Campaign Intelligence for Ezor Media."""
```
- A one-line module docstring. Its presence makes `backend/` an importable
  package so `from backend.main import app` (and all the intra-package
  `from . import config` imports) resolve.

---

## `backend/config.py` — mode detection, paths, pacing

**Data flow:** imported first by nearly everything. On import it (1) loads `.env`
if possible, (2) resolves the project paths and *creates* `data/`, (3) reads the
key + model from the environment, and (4) computes the single `LIVE_MODE` boolean
everyone else keys off.

```python
1-7   """AEGIS configuration ... never crashes for a missing key — degrades to DEMO."""
8   import os
9   from pathlib import Path

11  # Load .env if present (no hard dependency — works without python-dotenv too)
12  try:
13      from dotenv import load_dotenv
14      load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # load ../.env into os.environ
15  except Exception:
16      pass                       # dotenv missing OR no .env file → just use real env vars

18  BASE_DIR = Path(__file__).resolve().parent.parent   # project root (parent of backend/)
19  DATA_DIR = BASE_DIR / "data"
20  DATA_DIR.mkdir(exist_ok=True)  # SIDE EFFECT at import: guarantee data/ exists before SQLite opens
21  DB_PATH  = DATA_DIR / "aegis.db"

23  ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()   # "" if unset
24  MODEL = os.getenv("AEGIS_MODEL", "claude-sonnet-4-6").strip()    # overridable model id

26  # LIVE only if a non-empty, plausibly real key is present.
27  LIVE_MODE = bool(ANTHROPIC_API_KEY) and ANTHROPIC_API_KEY.startswith("sk-")

29  APP_NAME    = "AEGIS"
30  APP_TAGLINE = "Campaign Intelligence"
31  AGENCY      = "Ezor Media"

33  # Streaming pacing for demo mode (seconds) so the relay reads as "thinking".
34  DEMO_CHUNK_DELAY = float(os.getenv("AEGIS_DEMO_DELAY", "0.012"))  # gap between word-batches
35  DEMO_AGENT_PAUSE = float(os.getenv("AEGIS_AGENT_PAUSE", "0.35"))  # gap before each agent

38  def mode_label() -> str:
39      return "LIVE" if LIVE_MODE else "DEMO"   # human-readable mode, used in API + persistence
```
- **Line 14** loads `../​.env` *relative to this file*, so it works no matter what
  the process's current working directory is.
- **Lines 12–16** are the first rung of the resilience ladder: a missing
  `python-dotenv` or missing `.env` is swallowed — the app falls back to real
  environment variables.
- **Line 20** runs at import time. This is why `database.py` can open
  `config.DB_PATH` without ever checking that `data/` exists.
- **Line 27** is the entire DEMO/LIVE decision. Requiring the `sk-` prefix means a
  junk value like `ANTHROPIC_API_KEY=changeme` stays in DEMO rather than making a
  doomed API call.

---

## `backend/agents.py` — the roster and the prompt builder

**Data flow:** the orchestrator iterates `AGENTS` in order; for each agent it
calls `build_prompt(agent_id, brief, context)` (LIVE mode only), where `context`
is the accumulated `{AgentName → output}` of every prior agent.

```python
1-8   """The five AEGIS agents ... orchestrator runs them in sequence, feeding each
                                    the brief + accumulated output of every prior agent."""
9   from textwrap import dedent    # keeps triple-quoted prompts readable without leading indent

11  EZOR_CONTEXT = dedent("""\
12  ...  You are an agent inside AEGIS ... built for Ezor Media — Mumbai marketing
        & modeling agency ... house voice premium/editorial/confident ... Indian
        market context (festive calendars, regional languages, INR budgets) ...
        be specific, concrete, usable by a real account team tomorrow morning.""")
```
- `EZOR_CONTEXT` is the shared "system"-style preamble prepended to *every*
  agent's prompt. Centralising the brand voice here means all five agents speak
  consistently.

```python
21  def _brief_block(brief: dict) -> str:
22      return dedent(f"""\
23-31     CLIENT BRIEF
          - Brand: {brief.get('brand', 'N/A')}
          - Product / offering: {brief.get('product', 'N/A')}
          - Primary goal: {brief.get('goal', 'N/A')}
          - Target audience: {brief.get('audience', 'N/A')}
          - Market / geography: {brief.get('market', 'India')}   # note default = India
          - Budget: {brief.get('budget', 'N/A')}
          - Timeline: {brief.get('timeline', 'N/A')}
          - Notes: {brief.get('notes', '—')}""")
```
- Formats the raw brief dict into a labelled block. Every field uses `.get(…,
  default)` so a partial brief never raises — missing fields render as `N/A`
  (or `India` / `—`).

```python
34  def _prior(context: dict) -> str:
35      if not context:
36          return ""              # first agent (Research) has no prior work
37      blocks = []
38      for name, text in context.items():
39          blocks.append(f"### {name}\n{text}")   # each earlier agent as a markdown section
40      return "\n\n".join(blocks)
```
- Turns the accumulated context into readable Markdown sections. This is the
  mechanism that makes later agents "aware" of earlier ones.

```python
43  AGENTS = [
44-49   {"id":"research",   "name":"Research",       "role":"Audience, market & cultural signals", "icon":"01"},
50-55   {"id":"competitor", "name":"Competitor",     "role":"Positioning gaps & rival activity",   "icon":"02"},
56-61   {"id":"strategy",   "name":"Strategy",       "role":"Campaign concept, pillars & KPIs",     "icon":"03"},
62-67   {"id":"creative",   "name":"Creative",       "role":"Hooks, copy & content calendar",       "icon":"04"},
68-73   {"id":"media",      "name":"Media & Budget", "role":"Channel mix & spend allocation",       "icon":"05"},
74  ]
```
- The **order of this list is the pipeline order.** `icon` is a two-digit label
  ("01"…"05") the UI renders. `id` is the machine key used everywhere (SSE
  events, outputs dict, `demo_data`, `build_prompt`, `export`).

```python
77  def build_prompt(agent_id: str, brief: dict, context: dict) -> str:
78      brief_block = _brief_block(brief)
79      prior       = _prior(context)
80      prior_block = f"\n\nWORK COMPLETED BY EARLIER AGENTS:\n{prior}" if prior else ""  # omit header if empty

82      instructions = {           # per-agent task spec, each dedented markdown
83-89     "research":   "... 2-3 audience segments + 3-4 cultural signals + biggest opp/risk, <~350 words",
90-95     "competitor": "... 3 competitor archetypes + 2 positioning gaps + 1 white space, <~300 words",
96-102    "strategy":   "... BIG IDEA + 3 messaging pillars + primary/2 secondary KPIs, <~320 words",
103-109   "creative":   "... 3 hooks + 1 hero asset copy + 2-week calendar table, <~380 words",
110-117   "media":      "... channel-mix table summing to 100% + amounts + outcome + cadence, <~320 words",
118      }

120     return dedent(f"""\
121         {EZOR_CONTEXT}

123         {brief_block}{prior_block}      # brief, then (optionally) prior agents' work

125         ---
126         {instructions[agent_id]}        # KeyError here if agent_id is unknown — intentional

128         Write only the deliverable. No preamble, no "Sure, here is".""")
```
- The final prompt is always: **shared context → brief → prior work → this
  agent's specific instructions → "just the deliverable"**.
- Line 126 indexes `instructions[agent_id]` directly; an unknown id raises
  `KeyError`. Since ids come only from the static `AGENTS` list, that can't happen
  in normal flow — it's a fail-fast guard against a typo.
- The word-count caps in each instruction keep the five sections proportionate and
  the final brief presentable.
