"""Structured output schemas — one section per agent.

Every agent's output is strictly typed. The LLM is prompted with the JSON
schema of its output model and the response is validated with Pydantic;
invalid JSON triggers a retry in the LLM client. This prevents hallucinated
structure and makes the pipeline auditable.
"""
from typing import Literal

from pydantic import BaseModel, Field


# ── Agent 1 — Trend Intelligence ──────────────────────────────────────

class TrendSignal(BaseModel):
    name: str
    description: str
    momentum_score: float = Field(..., ge=0, le=10)
    relevance_score: float = Field(..., ge=0, le=10)
    novelty_score: float = Field(..., ge=0, le=10)
    source_evidence: str


class CompetitorActivity(BaseModel):
    competitor: str
    recent_move: str
    threat_level: Literal["low", "medium", "high"]


class TrendIntelligence(BaseModel):
    macro_trends: list[TrendSignal]
    micro_trends: list[TrendSignal]
    viral_patterns: list[str]
    competitor_activity: list[CompetitorActivity]
    opportunity_signals: list[str]
    risk_signals: list[str]
    confidence: float = Field(..., ge=0, le=1)


# ── Agent 2 — Audience Psychology ─────────────────────────────────────

class AudiencePsychology(BaseModel):
    persona_name: str
    core_desires: list[str]
    status_motivators: list[str]
    fear_patterns: list[str]
    identity_drivers: list[str]
    buying_resistance: list[str]
    dopamine_triggers: list[str]
    attention_hooks: list[str]
    tribal_affiliations: list[str]
    preferred_platforms: list[str]
    confidence: float = Field(..., ge=0, le=1)


# ── Agent 3 — Creative Strategy ───────────────────────────────────────

class PlatformStrategy(BaseModel):
    primary_platform: str
    secondary_platforms: list[str]
    content_cadence: str


class VisualLanguage(BaseModel):
    aesthetic: str
    color_palette: list[str]
    typography: str
    motion_style: str


class EmotionalArc(BaseModel):
    opening_hook: str
    tension_point: str
    resolution: str
    dominant_emotion: str


class ViralityMechanism(BaseModel):
    type: Literal["meme_format", "controversy", "relatability", "transformation",
                  "challenge", "exclusivity", "nostalgia", "surprise"]
    rationale: str


class CampaignConcept(BaseModel):
    title: str
    core_mechanism: str
    platform_strategy: PlatformStrategy
    visual_language: VisualLanguage
    emotional_arc: EmotionalArc
    virality_mechanism: ViralityMechanism
    content_examples: list[str]
    reel_concept: str
    meme_format: str
    carousel_structure: str
    cinematic_ad_idea: str
    influencer_strategy: str
    ugc_strategy: str


class CreativeStrategy(BaseModel):
    campaigns: list[CampaignConcept]
    confidence: float = Field(..., ge=0, le=1)


# ── Agent 4 — Evaluation Engine ───────────────────────────────────────

class ConceptScores(BaseModel):
    virality: float = Field(..., ge=0, le=10)
    novelty: float = Field(..., ge=0, le=10)
    emotional_resonance: float = Field(..., ge=0, le=10)
    trend_alignment: float = Field(..., ge=0, le=10)
    audience_alignment: float = Field(..., ge=0, le=10)
    platform_fit: float = Field(..., ge=0, le=10)
    clarity: float = Field(..., ge=0, le=10)
    memorability: float = Field(..., ge=0, le=10)


class SelfCritique(BaseModel):
    weaknesses: list[str]
    failure_risks: list[str]
    possible_improvements: list[str]


class ConceptEvaluation(BaseModel):
    concept_title: str
    scores: ConceptScores
    final_score: float = Field(..., ge=0, le=10)
    self_critique: SelfCritique
    rationale: str


class Evaluation(BaseModel):
    evaluations: list[ConceptEvaluation]
    confidence: float = Field(..., ge=0, le=1)


# ── Agent 5 — Supervisor synthesis ────────────────────────────────────

class CrossAgentConflict(BaseModel):
    agents_involved: list[str]
    nature_of_conflict: str
    resolution: str


class FinalCampaignBrief(BaseModel):
    executive_summary: str
    recommended_concept: str
    rationale: str
    cross_agent_conflicts: list[CrossAgentConflict]
    confidence_estimate: float = Field(..., ge=0, le=1)
    weak_evidence_flags: list[str]
    next_actions: list[str]
    success_metrics: list[str]
