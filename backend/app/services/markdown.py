"""Render each agent's structured output as readable markdown.

Powers the streaming document UI (each agent's section) and the
`export.md` download. All functions take plain dicts, so they work both
on live AgentEvent.output payloads and on runs re-read from the database.
"""
from __future__ import annotations


def _bullets(items: list | None, prefix: str = "") -> str:
    return "\n".join(f"- {prefix}{i}" for i in (items or []))


def trend_md(o: dict) -> str:
    parts = ["## Trend Intelligence\n"]
    for title, key in (("Macro trends", "macro_trends"), ("Micro trends", "micro_trends")):
        rows = o.get(key) or []
        if rows:
            parts.append(f"### {title}")
            for t in rows:
                parts.append(
                    f"- **{t['name']}** — {t['description']} "
                    f"*(momentum {t['momentum_score']:.0f}/10 · relevance "
                    f"{t['relevance_score']:.0f}/10 · novelty {t['novelty_score']:.0f}/10)*"
                )
    if o.get("competitor_activity"):
        parts.append("### Competitor activity")
        parts.append("| Competitor | Recent move | Threat |")
        parts.append("| --- | --- | --- |")
        for c in o["competitor_activity"]:
            parts.append(f"| {c['competitor']} | {c['recent_move']} | {c['threat_level']} |")
    if o.get("viral_patterns"):
        parts.append("### Viral patterns\n" + _bullets(o["viral_patterns"]))
    if o.get("opportunity_signals"):
        parts.append("### Opportunities\n" + _bullets(o["opportunity_signals"]))
    if o.get("risk_signals"):
        parts.append("### Risks\n" + _bullets(o["risk_signals"]))
    parts.append(f"\n> Confidence: **{o.get('confidence', 0):.0%}**")
    return "\n\n".join(parts)


def audience_md(o: dict) -> str:
    dims = [
        ("Core desires", "core_desires"), ("Status motivators", "status_motivators"),
        ("Fear patterns", "fear_patterns"), ("Identity drivers", "identity_drivers"),
        ("Buying resistance", "buying_resistance"), ("Dopamine triggers", "dopamine_triggers"),
        ("Attention hooks", "attention_hooks"), ("Tribal affiliations", "tribal_affiliations"),
        ("Preferred platforms", "preferred_platforms"),
    ]
    parts = [f"## Audience Psychology\n\n**Persona: {o.get('persona_name', '—')}**\n"]
    for title, key in dims:
        if o.get(key):
            parts.append(f"### {title}\n" + _bullets(o[key]))
    parts.append(f"\n> Confidence: **{o.get('confidence', 0):.0%}**")
    return "\n\n".join(parts)


def creative_md(o: dict) -> str:
    parts = ["## Creative Strategy\n"]
    for i, c in enumerate(o.get("campaigns") or [], 1):
        ps, vl, arc, vm = (c.get(k, {}) for k in
                           ("platform_strategy", "visual_language", "emotional_arc",
                            "virality_mechanism"))
        parts.append(f"### Concept {i}: {c['title']}")
        parts.append(f"**Core mechanism:** {c['core_mechanism']}")
        parts.append(
            f"**Platforms:** {ps.get('primary_platform', '—')} "
            f"(+{', '.join(ps.get('secondary_platforms') or []) or '—'}) · "
            f"cadence: {ps.get('content_cadence', '—')}"
        )
        parts.append(
            f"**Visual language:** {vl.get('aesthetic', '—')} · palette "
            f"{', '.join(vl.get('color_palette') or [])} · {vl.get('typography', '—')} · "
            f"{vl.get('motion_style', '—')}"
        )
        parts.append(
            f"**Emotional arc:** {arc.get('opening_hook', '—')} → "
            f"{arc.get('tension_point', '—')} → {arc.get('resolution', '—')} "
            f"*(dominant: {arc.get('dominant_emotion', '—')})*"
        )
        parts.append(f"**Virality mechanism:** `{vm.get('type', '—')}` — {vm.get('rationale', '')}")
        parts.append(
            "**Formats:**\n"
            f"- Reel: {c.get('reel_concept', '—')}\n"
            f"- Meme: {c.get('meme_format', '—')}\n"
            f"- Carousel: {c.get('carousel_structure', '—')}\n"
            f"- Cinematic ad: {c.get('cinematic_ad_idea', '—')}\n"
            f"- Influencers: {c.get('influencer_strategy', '—')}\n"
            f"- UGC: {c.get('ugc_strategy', '—')}"
        )
    parts.append(f"\n> Confidence: **{o.get('confidence', 0):.0%}**")
    return "\n\n".join(parts)


def scoring_md(o: dict) -> str:
    parts = ["## Evaluation\n"]
    evals = o.get("evaluations") or []
    if evals:
        parts.append("| Concept | Final | Virality | Novelty | Emotion | Audience | Clarity |")
        parts.append("| --- | --- | --- | --- | --- | --- | --- |")
        for e in evals:
            s = e.get("scores", {})
            parts.append(
                f"| {e['concept_title']} | **{e['final_score']:.1f}** "
                f"| {s.get('virality', 0):.0f} | {s.get('novelty', 0):.0f} "
                f"| {s.get('emotional_resonance', 0):.0f} | {s.get('audience_alignment', 0):.0f} "
                f"| {s.get('clarity', 0):.0f} |"
            )
        for e in evals:
            crit = e.get("self_critique", {})
            parts.append(f"### {e['concept_title']} — critique")
            parts.append(f"*{e.get('rationale', '')}*")
            if crit.get("weaknesses"):
                parts.append("**Weaknesses**\n" + _bullets(crit["weaknesses"]))
            if crit.get("failure_risks"):
                parts.append("**Failure risks**\n" + _bullets(crit["failure_risks"]))
            if crit.get("possible_improvements"):
                parts.append("**Improvements**\n" + _bullets(crit["possible_improvements"]))
    parts.append(f"\n> Confidence: **{o.get('confidence', 0):.0%}**")
    return "\n\n".join(parts)


def supervisor_md(o: dict) -> str:
    parts = [
        "## Final Campaign Brief\n",
        o.get("executive_summary", ""),
        f"### Recommended concept\n**{o.get('recommended_concept', '—')}**\n\n"
        f"{o.get('rationale', '')}",
    ]
    if o.get("cross_agent_conflicts"):
        parts.append("### Cross-agent conflicts resolved")
        for c in o["cross_agent_conflicts"]:
            parts.append(
                f"- **{' vs '.join(c.get('agents_involved') or [])}:** "
                f"{c.get('nature_of_conflict', '')} → *{c.get('resolution', '')}*"
            )
    if o.get("weak_evidence_flags"):
        parts.append("### Weak evidence flags\n" + _bullets(o["weak_evidence_flags"]))
    if o.get("next_actions"):
        parts.append("### Next actions\n" + _bullets(o["next_actions"]))
    if o.get("success_metrics"):
        parts.append("### Success metrics\n" + _bullets(o["success_metrics"]))
    parts.append(f"\n> Overall confidence: **{o.get('confidence_estimate', 0):.0%}**")
    return "\n\n".join(parts)


FORMATTERS = {
    "trend_agent": trend_md,
    "audience_agent": audience_md,
    "creative_agent": creative_md,
    "scoring_agent": scoring_md,
    "supervisor": supervisor_md,
}


def render_agent_output(agent_id: str, output: dict | None) -> str:
    if not output:
        return "_No output._"
    fmt = FORMATTERS.get(agent_id)
    return fmt(output) if fmt else "_No output._"
