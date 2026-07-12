"""
The five AEGIS agents.

Each agent has an id, a display name, a one-line role, and a prompt builder.
The orchestrator runs them in sequence, feeding each agent the brief plus the
accumulated output of every prior agent — so Strategy sees Research +
Competitor, Creative sees everything above it, and so on.
"""
from textwrap import dedent

EZOR_CONTEXT = dedent("""\
    You are an agent inside AEGIS, the campaign intelligence platform built for
    Ezor Media — a Mumbai-based marketing & modeling agency that runs brand,
    fashion, influencer and performance campaigns for Indian and global clients.
    Ezor's house voice is premium, editorial, and confident — never generic
    "growth-hack" copy. Indian market context (festive calendars, regional
    languages, tier-1/2 city behaviour, INR budgets) matters. Be specific,
    concrete, and usable by a real account team tomorrow morning.""")


def _brief_block(brief: dict) -> str:
    return dedent(f"""\
        CLIENT BRIEF
        - Brand: {brief.get('brand', 'N/A')}
        - Product / offering: {brief.get('product', 'N/A')}
        - Primary goal: {brief.get('goal', 'N/A')}
        - Target audience: {brief.get('audience', 'N/A')}
        - Market / geography: {brief.get('market', 'India')}
        - Budget: {brief.get('budget', 'N/A')}
        - Timeline: {brief.get('timeline', 'N/A')}
        - Notes: {brief.get('notes', '—')}""")


def _prior(context: dict) -> str:
    if not context:
        return ""
    blocks = []
    for name, text in context.items():
        blocks.append(f"### {name}\n{text}")
    return "\n\n".join(blocks)


AGENTS = [
    {
        "id": "research",
        "name": "Research",
        "role": "Audience, market & cultural signals",
        "icon": "01",
    },
    {
        "id": "competitor",
        "name": "Competitor",
        "role": "Positioning gaps & rival activity",
        "icon": "02",
    },
    {
        "id": "strategy",
        "name": "Strategy",
        "role": "Campaign concept, pillars & KPIs",
        "icon": "03",
    },
    {
        "id": "creative",
        "name": "Creative",
        "role": "Hooks, copy & content calendar",
        "icon": "04",
    },
    {
        "id": "media",
        "name": "Media & Budget",
        "role": "Channel mix & spend allocation",
        "icon": "05",
    },
]


def build_prompt(agent_id: str, brief: dict, context: dict) -> str:
    brief_block = _brief_block(brief)
    prior = _prior(context)
    prior_block = f"\n\nWORK COMPLETED BY EARLIER AGENTS:\n{prior}" if prior else ""

    instructions = {
        "research": dedent("""\
            You are the RESEARCH agent. Produce a tight market & audience read.
            Cover, with concrete specifics (not platitudes):
            - Who the audience really is (2-3 sharp segments with a one-line persona each)
            - 3-4 cultural / behavioural signals or trends relevant to this brand right now
            - The single biggest opportunity and the single biggest risk
            Use markdown with short headers and bullets. Keep it under ~350 words."""),
        "competitor": dedent("""\
            You are the COMPETITOR agent. Map the competitive field.
            - Name 3 likely competitor archetypes (or real categories) and what each owns in the customer's mind
            - Identify 2 concrete positioning gaps Ezor can take
            - One "white space" angle nobody is using
            Markdown, sharp bullets, under ~300 words."""),
        "strategy": dedent("""\
            You are the STRATEGY agent. Using the research and competitor work,
            define the campaign spine:
            - A campaign BIG IDEA (one memorable line + 2-sentence rationale)
            - 3 messaging pillars (each: name + one supporting line)
            - The primary KPI and 2 secondary KPIs, with rough target ranges
            Markdown, decisive, under ~320 words."""),
        "creative": dedent("""\
            You are the CREATIVE agent. Turn the strategy into things people see.
            - 3 campaign hooks / taglines (punchy, on-brand, premium)
            - Sample ad copy for ONE hero asset (headline + 2-line body + CTA)
            - A 2-week content calendar as a compact markdown table
              (columns: Day | Platform | Format | Theme)
            Markdown, under ~380 words."""),
        "media": dedent("""\
            You are the MEDIA & BUDGET agent. Allocate the spend.
            - A channel mix as a markdown table (columns: Channel | % of budget | Why)
              that sums to 100%
            - Convert the percentages to amounts using the brief's budget if a number is given
            - Projected outcome in one line (reach / leads / ROAS as appropriate)
            - One sentence on measurement & optimisation cadence
            Markdown, under ~320 words."""),
    }

    return dedent(f"""\
        {EZOR_CONTEXT}

        {brief_block}{prior_block}

        ---
        {instructions[agent_id]}

        Write only the deliverable. No preamble, no "Sure, here is".""")
