"""Typed contracts between the API, the agents, and the frontend.

Split by role:
  brief.py   — user input (CampaignBrief)
  outputs.py — each agent's structured output schema
  events.py  — SSE event + final PipelineRun envelope
"""
from app.schemas.brief import CampaignBrief
from app.schemas.events import AgentEvent, AgentStatus, PipelineRun
from app.schemas.outputs import (
    AudiencePsychology,
    CampaignConcept,
    ConceptEvaluation,
    ConceptScores,
    CompetitorActivity,
    CreativeStrategy,
    CrossAgentConflict,
    EmotionalArc,
    Evaluation,
    FinalCampaignBrief,
    PlatformStrategy,
    SelfCritique,
    TrendIntelligence,
    TrendSignal,
    ViralityMechanism,
    VisualLanguage,
)

__all__ = [
    "AgentEvent",
    "AgentStatus",
    "AudiencePsychology",
    "CampaignBrief",
    "CampaignConcept",
    "CompetitorActivity",
    "ConceptEvaluation",
    "ConceptScores",
    "CreativeStrategy",
    "CrossAgentConflict",
    "EmotionalArc",
    "Evaluation",
    "FinalCampaignBrief",
    "PipelineRun",
    "PlatformStrategy",
    "SelfCritique",
    "TrendIntelligence",
    "TrendSignal",
    "ViralityMechanism",
    "VisualLanguage",
]
