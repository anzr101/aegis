"""Evaluation Engine — the quantitative evaluation layer.

Most AI systems generate. This one ALSO evaluates its own generation on
8 weighted dimensions, then runs a self-critique pass identifying each
concept's weaknesses and failure risks.

Runs SEQUENTIALLY after the creative agent (it needs concepts to score),
in a stage of its own before the supervisor.
"""
from typing import Any, Type

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas import CampaignBrief, Evaluation


class ScoringAgent(BaseAgent):
    name = "scoring_agent"
    description = "Evaluation Engine"
    use_web_search = False
    # Scores + self-critique for 3 concepts is long-form output; 4096 was
    # observed to truncate mid-JSON (stop_reason=max_tokens) in live runs.
    max_tokens = 8192

    @property
    def system_prompt(self) -> str:
        return (
            "You are AEGIS Evaluation Engine — a rigorous, calibrated critic of "
            "marketing concepts. You score each campaign concept on 8 independent "
            "dimensions (0-10) and produce a final weighted score.\n\n"
            "DIMENSIONS:\n"
            "  - virality: probability of organic spread (network effects, shareability)\n"
            "  - novelty: how unsaturated the creative territory is\n"
            "  - emotional_resonance: depth of feeling evoked in target audience\n"
            "  - trend_alignment: fit with current cultural moment\n"
            "  - audience_alignment: fit with target audience psychology\n"
            "  - platform_fit: alignment with platform's native conventions\n"
            "  - clarity: how easily the message is understood in <3 seconds\n"
            "  - memorability: distinctive elements that stick post-exposure\n\n"
            "FINAL SCORE = weighted average:\n"
            "  virality (0.20), emotional_resonance (0.15), audience_alignment (0.15),\n"
            "  novelty (0.10), trend_alignment (0.10), platform_fit (0.10),\n"
            "  clarity (0.10), memorability (0.10)\n\n"
            "BE STRICT AND CONSISTENT. A 9 or 10 should be rare. Most decent concepts "
            "will score 6-7. Average concepts score 5. If everything scores 8+, you're "
            "not being honest. Score deterministically from the rubric, not from mood.\n\n"
            "SELF-CRITIQUE: For each concept, also produce:\n"
            "  - weaknesses (what's structurally weak)\n"
            "  - failure_risks (specific ways it could backfire — backlash, "
            "    misinterpretation, fatigue, audience mismatch)\n"
            "  - possible_improvements (concrete, actionable changes)\n\n"
            "Treat this as adversarial review. The goal is to find flaws BEFORE the "
            "campaign goes live, not to validate work."
        )

    @property
    def output_schema(self) -> Type[BaseModel]:
        return Evaluation

    def build_user_message(self, brief: CampaignBrief, context: dict[str, Any]) -> str:
        creative = context.get("creative_output")
        trend = context.get("trend_output")
        audience = context.get("audience_output")

        creative_json = creative.model_dump_json(indent=2) if creative else "{}"
        trend_summary = ""
        if trend:
            trend_summary = (
                f"\n\nTREND CONTEXT (for trend_alignment scoring):\n"
                f"Macro trends: {[t.name for t in trend.macro_trends]}\n"
                f"Micro trends: {[t.name for t in trend.micro_trends]}\n"
            )
        audience_summary = ""
        if audience:
            audience_summary = (
                f"\n\nAUDIENCE CONTEXT (for audience_alignment scoring):\n"
                f"Persona: {audience.persona_name}\n"
                f"Core desires: {audience.core_desires}\n"
                f"Attention hooks: {audience.attention_hooks}\n"
                f"Buying resistance: {audience.buying_resistance}\n"
            )

        return (
            f"ORIGINAL BRIEF:\n"
            f"  Brand: {brief.brand}\n"
            f"  Industry: {brief.industry}\n"
            f"  Goal: {brief.campaign_goal}\n"
            f"  Audience (raw): {brief.target_audience}\n"
            f"{trend_summary}{audience_summary}\n\n"
            f"CONCEPTS TO EVALUATE:\n{creative_json}\n\n"
            f"Score every concept rigorously. Return JSON only."
        )
