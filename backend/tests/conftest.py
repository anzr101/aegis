"""Shared fixtures: an isolated SQLite database per test and a stub LLM client.

Everything runs offline — no API key, no network. The stub returns valid
instances of each agent's output schema, so the full pipeline (orchestrator,
event bus, persistence, API) is exercised end-to-end minus the actual LLM.
"""
import os

# Must be set BEFORE any app import — Settings is cached at import time.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./_test_aegis.db"
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-used"
os.environ["ENABLE_WEB_SEARCH"] = "false"

from pathlib import Path
from typing import Type

import pytest
from pydantic import BaseModel

from app.db import engine as db_engine
from app.db.models import Base
from app.db.store import RunStore
from app.schemas import (
    AudiencePsychology,
    CampaignBrief,
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
from app.services.event_bus import EventBus
from app.services.llm import LLMResult


# ── Output factories ─────────────────────────────────────────────────

def make_trend() -> TrendIntelligence:
    sig = TrendSignal(
        name="AI productivity memes",
        description="Split-screen before/after formats",
        momentum_score=8.0,
        relevance_score=7.0,
        novelty_score=6.0,
        source_evidence="stub",
    )
    return TrendIntelligence(
        macro_trends=[sig],
        micro_trends=[sig],
        viral_patterns=["split-screen"],
        competitor_activity=[
            CompetitorActivity(competitor="X Corp", recent_move="launched", threat_level="low")
        ],
        opportunity_signals=["gap"],
        risk_signals=["fatigue"],
        confidence=0.8,
    )


def make_audience() -> AudiencePsychology:
    return AudiencePsychology(
        persona_name="The Quiet Builder",
        core_desires=["competence"],
        status_motivators=["early adopter"],
        fear_patterns=["irrelevance"],
        identity_drivers=["knows things first"],
        buying_resistance=["cringe aversion"],
        dopamine_triggers=["novelty"],
        attention_hooks=["pattern interrupt"],
        tribal_affiliations=["dev twitter"],
        preferred_platforms=["instagram"],
        confidence=0.7,
    )


def make_creative() -> CreativeStrategy:
    concept = CampaignConcept(
        title="Concept A",
        core_mechanism="stub mechanism",
        platform_strategy=PlatformStrategy(
            primary_platform="instagram",
            secondary_platforms=["youtube"],
            content_cadence="3x/week",
        ),
        visual_language=VisualLanguage(
            aesthetic="editorial",
            color_palette=["#112233"],
            typography="serif headline",
            motion_style="jump cuts",
        ),
        emotional_arc=EmotionalArc(
            opening_hook="hook",
            tension_point="tension",
            resolution="resolution",
            dominant_emotion="hope",
        ),
        virality_mechanism=ViralityMechanism(type="relatability", rationale="stub"),
        content_examples=["example"],
        reel_concept="reel",
        meme_format="meme",
        carousel_structure="carousel",
        cinematic_ad_idea="ad",
        influencer_strategy="influencers",
        ugc_strategy="ugc",
    )
    return CreativeStrategy(campaigns=[concept], confidence=0.75)


def make_evaluation(final_score: float = 7.5) -> Evaluation:
    return Evaluation(
        evaluations=[
            ConceptEvaluation(
                concept_title="Concept A",
                scores=ConceptScores(
                    virality=7, novelty=6, emotional_resonance=7, trend_alignment=7,
                    audience_alignment=8, platform_fit=7, clarity=8, memorability=7,
                ),
                final_score=final_score,
                self_critique=SelfCritique(
                    weaknesses=["w"], failure_risks=["r"], possible_improvements=["i"]
                ),
                rationale="stub",
            )
        ],
        confidence=0.8,
    )


def make_final_brief() -> FinalCampaignBrief:
    return FinalCampaignBrief(
        executive_summary="stub summary",
        recommended_concept="Concept A",
        rationale="highest score",
        cross_agent_conflicts=[
            CrossAgentConflict(
                agents_involved=["trend_agent", "creative_agent"],
                nature_of_conflict="stub",
                resolution="stub",
            )
        ],
        confidence_estimate=0.7,
        weak_evidence_flags=[],
        next_actions=["do the thing"],
        success_metrics=["500k impressions"],
    )


_FACTORIES: dict[type, object] = {
    TrendIntelligence: make_trend,
    AudiencePsychology: make_audience,
    CreativeStrategy: make_creative,
    Evaluation: make_evaluation,
    FinalCampaignBrief: make_final_brief,
}


class StubLLM:
    """Drop-in replacement for LLMClient — returns valid outputs instantly.

    `fail_for` lists output schemas that should raise, to test degradation.
    """

    def __init__(self, fail_for: set[type] | None = None):
        self.fail_for = fail_for or set()
        self.calls: list[str] = []

    async def structured_call(self, system: str, user: str,
                              output_model: Type[BaseModel],
                              model: str | None = None,
                              max_tokens: int = 4096) -> LLMResult:
        self.calls.append(output_model.__name__)
        if output_model in self.fail_for:
            raise RuntimeError(f"stub failure for {output_model.__name__}")
        return LLMResult(
            parsed=_FACTORIES[output_model](),
            raw_text="{}",
            tokens_used=100,
            latency_ms=5,
            model_used=model or "stub-model",
        )

    async def call_with_web_search(self, system: str, user: str,
                                   output_model: Type[BaseModel],
                                   model: str | None = None,
                                   max_tokens: int = 4096) -> LLMResult:
        return await self.structured_call(system, user, output_model, model, max_tokens)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def brief() -> CampaignBrief:
    return CampaignBrief(
        brand="TestBrand",
        industry="fintech",
        product_or_service="A budgeting app",
        campaign_goal="Acquire 10k users",
        target_audience="Young professionals in Mumbai",
    )


@pytest.fixture
async def db():
    """Fresh tables per test, torn down afterwards."""
    await db_engine.init_db()
    yield
    async with db_engine.get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_engine.dispose_engine()


@pytest.fixture
def store(db) -> RunStore:
    return RunStore()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


def pytest_sessionfinish(session, exitstatus):
    try:
        Path("./_test_aegis.db").unlink(missing_ok=True)
    except OSError:
        pass
