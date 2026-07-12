"""
DEMO-mode output.

Realistic, agency-grade deliverables that interpolate the actual brief so the
pipeline feels responsive without an API key. This is what runs on a fresh
machine with no credentials — and it still looks like real work.
"""


def _g(brief: dict, key: str, default: str) -> str:
    v = (brief.get(key) or "").strip()
    return v if v else default


def demo_output(agent_id: str, brief: dict) -> str:
    brand = _g(brief, "brand", "the brand")
    product = _g(brief, "product", "the offering")
    audience = _g(brief, "audience", "urban Indian consumers, 22–38")
    market = _g(brief, "market", "India (metro + tier-1)")
    goal = _g(brief, "goal", "build awareness and qualified demand")
    budget = _g(brief, "budget", "₹15,00,000")

    if agent_id == "research":
        return f"""\
**Market read — {market}**

{brand} is entering a moment where attention is cheap to buy and trust is
expensive to earn. {product} sits in a category where the purchase is as much
about identity signalling as utility.

**Audience segments**
- **The Aspirant** — {audience}; researches heavily, buys on social proof, screenshots before purchasing.
- **The Loyalist** — already brand-aware, follows founders, responds to access and early drops more than discounts.
- **The Drifter** — discovers via Reels/Shorts, low intent, converts only with a strong hook in the first 1.5 seconds.

**Cultural signals**
- Short-form video is now the default discovery surface; static creative under-indexes badly.
- "Quiet premium" is rising — overt logos are cooling, craft and provenance are heating up.
- Regional-language creative (Hindi/Marathi) lifts tier-2 engagement 30–40% over English-only.
- Festive and pay-day cycles compress demand into predictable spikes worth front-loading spend against.

**Biggest opportunity:** own a clear emotional territory before a competitor does — the category is loud but unowned.
**Biggest risk:** spreading {budget} thin across too many channels and never reaching frequency on any one."""

    if agent_id == "competitor":
        return f"""\
**Competitive field — {product}**

| Archetype | What they own | Weak spot |
|---|---|---|
| The Loud Discounter | Price & urgency | No brand love, churns hard |
| The Heritage Player | Trust & legacy | Reads dated to under-30s |
| The Venture-Backed Upstart | Buzz & design | Thin on substance, ad-fatigued |

**Positioning gaps {brand} can take**
- **Craft over hype** — the upstarts are loud but hollow; there's room to win on substance shown, not claimed.
- **Belonging over transaction** — nobody in the set is building an actual community; they're all running funnels.

**White space:** the "knowing insider" tone — premium without shouting, treating {audience} as people with taste rather than targets to retarget. No competitor currently speaks this way."""

    if agent_id == "strategy":
        return f"""\
**The big idea**

> **"Made to be noticed. Built to be kept."**

A campaign that positions {brand} against disposable, hype-driven competitors —
{product} as the considered choice for people who are done with noise. It earns
attention emotionally, then converts on substance.

**Messaging pillars**
- **Proof, not promises** — show the craft, the process, the receipts.
- **Made for you, not at you** — speak to {audience} as insiders, never as a segment.
- **Worth the wait** — premium is patient; scarcity and access over fire-sale urgency.

**KPIs**
- **Primary:** qualified leads / purchases attributable to campaign (target: enough to clear {goal}).
- **Secondary:** 3s+ video view-through rate ≥ 25%; saved/shared rate ≥ 4% (the real signal of resonance)."""

    if agent_id == "creative":
        return f"""\
**Hooks**
- "You'll know it when you see it."
- "Everyone's loud. Be unforgettable."
- "{brand}. Made to be kept."

**Hero asset — Reel / Short (0:15)**
> **Headline:** The last one you'll need.
> Most {product} is built to be replaced. We built ours to be remembered —
> obsessed over so you never have to think about it again.
> **CTA:** See the difference →

**Two-week content calendar**

| Day | Platform | Format | Theme |
|---|---|---|---|
| 1 | Instagram | Reel | Hook film — "Made to be noticed" |
| 2 | YouTube Shorts | Short | Behind the craft |
| 4 | Instagram | Carousel | Proof, not promises |
| 6 | WhatsApp | Broadcast | Early-access invite (Loyalists) |
| 8 | Instagram | Reel | Customer story / UGC |
| 10 | LinkedIn | Post | Founder POV (trust signal) |
| 12 | Instagram | Reel | Objection-buster |
| 14 | All | Mixed | Launch / offer window opens |"""

    if agent_id == "media":
        return f"""\
**Channel mix** (against {budget})

| Channel | % of budget | Why |
|---|---|---|
| Meta (IG/FB) | 45% | Primary discovery + retargeting engine for {audience} |
| YouTube Shorts | 20% | Cheap reach + 3s hook testing at scale |
| Influencer / creator | 20% | Borrowed trust; the "knowing insider" voice lives here |
| Search (Google) | 10% | Capture warm intent the rest of the mix creates |
| WhatsApp / CRM | 5% | Owned-audience nurture, near-zero CAC |

**Projected outcome:** with disciplined frequency on Meta + creator-led reach,
expect a 25–40% lift in qualified demand over a flat-spend baseline across the
flight — enough to move {goal} measurably.

**Measurement cadence:** read creative + channel performance every 72 hours for
the first two weeks; reallocate up to 15% of budget toward the top hook before
each weekly cycle. Kill any asset under a 1.5s hook-rate of 20% by day 5."""

    return f"(No demo content registered for agent '{agent_id}'.)"
