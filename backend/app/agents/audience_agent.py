"""Audience Psychology Engine.

Most "audience analysis" tools produce a vague paragraph. This agent
produces a structured behavioral profile across 9 axes drawn from
consumer psychology research (core desires, status motivators, fear
patterns, identity drivers, buying resistance, dopamine triggers,
attention hooks, tribal affiliations, preferred platforms).

This gives the downstream creative work a rich substrate to design from,
rather than guessing what the audience wants.
"""
from typing import Any, Type

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas import AudiencePsychology, CampaignBrief


class AudienceAgent(BaseAgent):
    name = "audience_agent"
    description = "Audience Psychology"
    use_web_search = False
    max_tokens = 3072

    @property
    def system_prompt(self) -> str:
        return (
            "You are AEGIS Audience Psychology Engine — a behavioral analyst trained in "
            "consumer psychology, self-determination theory, signaling theory, and "
            "platform-specific attention dynamics.\n\n"
            "Your job is to build a deep psychological profile of the target audience. "
            "Avoid surface demographics. Get to the underlying motivations.\n\n"
            "BAD EXAMPLE: 'Tech-savvy Gen Z users who love trends.'\n"
            "GOOD EXAMPLE: 'Urban Indian Gen Z (19-26), software students or early-career "
            "engineers. Core desire: prove competence to peers without appearing to try. "
            "Status motivator: being early to discover something before it goes mainstream. "
            "Identity driver: \"the friend who knows things first.\" Buying resistance: "
            "skepticism of corporate marketing, aversion to anything that feels \"cringe\".'\n\n"
            "For each of the 9 dimensions, list 3-6 specific items. Be concrete enough "
            "that a creative team could design a campaign directly from this profile.\n\n"
            "Persona name should be evocative (e.g. 'The Quiet Builder', 'The Curated "
            "Aesthete') — not generic.\n\n"
            "Confidence reflects how well you understand this audience based on the brief. "
            "If the brief is vague, confidence should be lower and you should make "
            "conservative inferences."
        )

    @property
    def output_schema(self) -> Type[BaseModel]:
        return AudiencePsychology

    def build_user_message(self, brief: CampaignBrief, context: dict[str, Any]) -> str:
        memory_hint = ""
        if context.get("similar_past_runs"):
            past = context["similar_past_runs"][:2]
            memory_hint = (
                "\n\nFor context, here are summaries of past successful campaigns "
                "in this industry:\n"
            )
            for p in past:
                memory_hint += (
                    f"- {p.get('brief', {}).get('brand', 'unknown')}: "
                    f"avg score {p.get('avg_score', 'N/A')}\n"
                )

        return (
            f"BRAND: {brief.brand}\n"
            f"INDUSTRY: {brief.industry}\n"
            f"PRODUCT/SERVICE: {brief.product_or_service}\n"
            f"CAMPAIGN GOAL: {brief.campaign_goal}\n"
            f"TARGET AUDIENCE (raw): {brief.target_audience}\n"
            f"GEOGRAPHIC FOCUS: {brief.geographic_focus}\n"
            f"EXTRA CONTEXT: {brief.extra_context or 'none'}"
            f"{memory_hint}\n\n"
            f"Build the psychological profile. Return JSON only."
        )
