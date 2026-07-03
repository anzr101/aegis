"""SSE event envelope and the final pipeline result."""
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.brief import CampaignBrief
from app.schemas.outputs import (
    AudiencePsychology,
    CreativeStrategy,
    Evaluation,
    FinalCampaignBrief,
    TrendIntelligence,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class AgentEvent(BaseModel):
    """Streamed to the frontend over SSE during pipeline execution."""
    timestamp: datetime = Field(default_factory=_utcnow)
    agent_name: str
    status: AgentStatus
    thought: str | None = None
    tokens_used: int | None = None
    latency_ms: int | None = None
    error: str | None = None


class PipelineRun(BaseModel):
    """Final state of one pipeline execution — what gets persisted."""
    run_id: str
    brief: CampaignBrief
    trend_intelligence: TrendIntelligence | None = None
    audience_psychology: AudiencePsychology | None = None
    creative_strategy: CreativeStrategy | None = None
    evaluation: Evaluation | None = None
    final_brief: FinalCampaignBrief | None = None
    total_tokens: int = 0
    total_latency_ms: int = 0
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    created_at: datetime = Field(default_factory=_utcnow)

    @property
    def avg_score(self) -> float | None:
        if self.evaluation and self.evaluation.evaluations:
            scores = [e.final_score for e in self.evaluation.evaluations]
            return sum(scores) / len(scores)
        return None
