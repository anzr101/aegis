"""Supervisor Agent — the executive synthesis layer.

Receives the outputs of all four operational agents and:
  1. Detects cross-agent conflicts (e.g. trend says minimalism, creative
     says maximalist chaos)
  2. Resolves contradictions with explicit reasoning
  3. Selects the strongest concept (scores + qualitative judgment)
  4. Estimates overall confidence honestly
  5. Flags weak evidence (low agent confidence, thin data, close scores)
  6. Produces actionable next steps and measurable success metrics

Runs on the supervisor model (Sonnet) rather than the operational model
(Haiku): synthesis across heterogeneous agent outputs needs stronger
reasoning than any single agent task — that is the one place the extra
cost is justified.
"""
from typing import Any, Type

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.schemas import CampaignBrief, FinalCampaignBrief


class SupervisorAgent(BaseAgent):
    name = "supervisor"
    description = "Supervisor Synthesis"
    use_web_search = False
    max_tokens = get_settings().max_tokens_supervisor

    @property
    def model_override(self) -> str | None:
        return get_settings().supervisor_model

    @property
    def system_prompt(self) -> str:
        return (
            "You are AEGIS Supervisor — the executive synthesis layer above 4 "
            "specialized agents (Trend Intelligence, Audience Psychology, Creative "
            "Strategy, Evaluation Engine).\n\n"
            "Your job is NOT to redo their work. It's to:\n\n"
            "1. CONFLICT DETECTION — Identify where the agents disagree or where "
            "their outputs are misaligned. Examples:\n"
            "   - Trend agent says minimalist aesthetic is rising; creative agent "
            "     proposes maximalist chaos → conflict\n"
            "   - Audience agent says core resistance is 'feels like marketing'; "
            "     creative agent's concept is overtly promotional → conflict\n"
            "   - Trend has high momentum on a topic the audience doesn't engage with → conflict\n\n"
            "2. CONFLICT RESOLUTION — Explicitly reason through each conflict and "
            "decide what wins, with rationale.\n\n"
            "3. CONCEPT SELECTION — Pick the strongest concept. Default to the "
            "highest-scoring one from the Evaluation agent, BUT override if you "
            "detect that the scoring missed a critical context point. Explain why.\n\n"
            "4. WEAK EVIDENCE FLAGGING — Note where you have low confidence: "
            "  - Any agent reported confidence < 0.6\n"
            "  - Trend data lacked recent / specific sources\n"
            "  - Audience inferences were made from sparse brief input\n"
            "  - Concepts scored close together (no clear winner)\n\n"
            "5. CONFIDENCE ESTIMATE — A single 0-1 number. Be honest. If conflicts "
            "are unresolved or evidence is thin, this should be 0.5-0.7, not 0.9+.\n\n"
            "6. NEXT ACTIONS — 4-7 concrete actions a marketing team should take "
            "to execute this. Not 'create the campaign' — specific deliverables.\n\n"
            "7. SUCCESS METRICS — How will the team know this campaign worked? "
            "Specific, measurable: 'reach 500k organic impressions in week 1' not "
            "'increase awareness'.\n\n"
            "Be concise but rigorous — keep the whole response under ~2500 tokens; "
            "resolve conflicts in 2-3 sentences each, not essays. The "
            "executive_summary is what the human reads first — make it count."
        )

    @property
    def output_schema(self) -> Type[BaseModel]:
        return FinalCampaignBrief

    def build_user_message(self, brief: CampaignBrief, context: dict[str, Any]) -> str:
        trend = context.get("trend_output")
        audience = context.get("audience_output")
        creative = context.get("creative_output")
        evaluation = context.get("evaluation_output")

        sections = [f"ORIGINAL BRIEF:\n{brief.model_dump_json(indent=2)}\n"]

        if trend:
            sections.append(
                f"TREND INTELLIGENCE OUTPUT (confidence={trend.confidence}):\n"
                f"{trend.model_dump_json(indent=2)}\n"
            )
        else:
            sections.append("TREND INTELLIGENCE: FAILED OR UNAVAILABLE\n")

        if audience:
            sections.append(
                f"AUDIENCE PSYCHOLOGY OUTPUT (confidence={audience.confidence}):\n"
                f"{audience.model_dump_json(indent=2)}\n"
            )
        else:
            sections.append("AUDIENCE PSYCHOLOGY: FAILED OR UNAVAILABLE\n")

        if creative:
            sections.append(
                f"CREATIVE STRATEGY OUTPUT (confidence={creative.confidence}):\n"
                f"{creative.model_dump_json(indent=2)}\n"
            )
        else:
            sections.append("CREATIVE STRATEGY: FAILED OR UNAVAILABLE\n")

        if evaluation:
            sections.append(
                f"EVALUATION OUTPUT (confidence={evaluation.confidence}):\n"
                f"{evaluation.model_dump_json(indent=2)}\n"
            )
        else:
            sections.append("EVALUATION: FAILED OR UNAVAILABLE\n")

        sections.append(
            "Now synthesize. Detect conflicts, resolve them with reasoning, "
            "select the strongest concept, flag weak evidence, and produce the "
            "final campaign brief. Return JSON only."
        )
        return "\n\n".join(sections)
