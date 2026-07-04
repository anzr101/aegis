"""Trend Intelligence Agent.

Uses Anthropic's web_search tool to gather LIVE market data: macro trends,
micro trends, viral patterns, competitor activity, opportunity/risk signals.

Each trend gets three orthogonal scores (momentum / relevance / novelty) —
the separation prevents a single "good" score from masking trade-offs.
"""
from typing import Any, Type

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas import CampaignBrief, TrendIntelligence


class TrendAgent(BaseAgent):
    name = "trend_agent"
    description = "Trend Intelligence"
    use_web_search = True
    # Web-search-grounded output runs long; 4096 was observed truncating
    # (stop_reason=max_tokens) in a live production run.
    max_tokens = 8192

    @property
    def system_prompt(self) -> str:
        return (
            "You are AEGIS Trend Intelligence — a live market awareness analyst.\n\n"
            "Your job is to gather CURRENT, evidence-backed signals from the web for "
            "the given brief. Use web_search aggressively — at least 3 searches covering:\n"
            "  1. Industry-specific trends in the target geography\n"
            "  2. Recent competitor moves and campaign launches\n"
            "  3. Cultural/viral patterns relevant to the audience\n\n"
            "For each trend, you score three independent dimensions on a 0-10 scale:\n"
            "  - momentum_score: rate of growth/spread (declining → 0, exponential → 10)\n"
            "  - relevance_score: fit with the brand and brief (off-topic → 0, perfect fit → 10)\n"
            "  - novelty_score: market saturation (clichéd → 0, fresh territory → 10)\n\n"
            "Be specific. Avoid vague trends like 'AI is big' — instead 'AI productivity "
            "memes targeting knowledge workers, format: split-screen before/after'.\n\n"
            "Risks include: trend fatigue, audience misalignment, competitive saturation.\n"
            "Opportunities are gaps competitors haven't filled.\n\n"
            "Provide a final 'confidence' score (0-1) reflecting your conviction in the "
            "data quality, based on how recent and specific the search results were."
        )

    @property
    def output_schema(self) -> Type[BaseModel]:
        return TrendIntelligence

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
            f"Run web searches now to gather live trend intelligence. "
            f"Then return the structured JSON only."
        )
