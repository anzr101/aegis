"""Creative Strategist Agent.

Generates 3 distinct multi-modal campaign concepts (core mechanism,
platform strategy, visual language, emotional arc, typed virality
mechanism, and concrete content across six formats).

Runs in PARALLEL with TrendAgent and AudienceAgent — it does not see
their outputs. That is deliberate: the supervisor synthesizes at the end,
and creative independence prevents the concepts from being constrained
too early.
"""
from typing import Any, Type

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas import CampaignBrief, CreativeStrategy


class CreativeAgent(BaseAgent):
    name = "creative_agent"
    description = "Creative Strategy"
    use_web_search = False
    max_tokens = 8192

    @property
    def system_prompt(self) -> str:
        return (
            "You are AEGIS Creative Strategist — a senior creative director trained in "
            "platform-native storytelling, viral mechanics, and brand strategy.\n\n"
            "Generate exactly 3 DISTINCT campaign concepts for the brief. They must "
            "differ meaningfully in approach — not three variations of the same idea. "
            "Suggested diversity:\n"
            "  Concept 1: Emotionally driven / narrative-led\n"
            "  Concept 2: Culturally embedded / meme-native / community-driven\n"
            "  Concept 3: Bold / contrarian / pattern-interrupt\n\n"
            "For each concept, design content across SIX formats — reel, meme, carousel, "
            "cinematic ad, influencer strategy, UGC strategy. Don't just describe; give "
            "specific creative direction (e.g. 'opening shot: extreme close-up on hands "
            "trembling as they type the resignation letter, cut to wide shot of empty "
            "office at 2am' — not 'an ad showing someone resigning').\n\n"
            "Visual language must be specific. Color palette as hex codes, typography as "
            "specific style descriptors (e.g. 'editorial serif headline, monospace body'), "
            "motion style (e.g. 'jump-cuts every 1.2s, glitch transitions on emotional beats').\n\n"
            "Virality mechanism must use one of the typed enum values. Pick the one that "
            "genuinely fits — don't default to 'relatability'.\n\n"
            "Be divergent: push each concept into genuinely different creative territory.\n\n"
            "Confidence reflects how strongly the concepts align with the brief's stated goal."
        )

    @property
    def output_schema(self) -> Type[BaseModel]:
        return CreativeStrategy

    def build_user_message(self, brief: CampaignBrief, context: dict[str, Any]) -> str:
        return (
            f"BRAND: {brief.brand}\n"
            f"INDUSTRY: {brief.industry}\n"
            f"PRODUCT/SERVICE: {brief.product_or_service}\n"
            f"CAMPAIGN GOAL: {brief.campaign_goal}\n"
            f"TARGET AUDIENCE: {brief.target_audience}\n"
            f"GEOGRAPHIC FOCUS: {brief.geographic_focus}\n"
            f"BUDGET TIER: {brief.budget_tier}\n"
            f"EXTRA CONTEXT: {brief.extra_context or 'none'}\n\n"
            f"Generate 3 distinct multi-modal campaign concepts. Return JSON only."
        )
