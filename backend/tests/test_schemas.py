"""Schema contract tests."""
import pytest
from pydantic import ValidationError

from app.schemas import AgentEvent, AgentStatus, CampaignBrief, PipelineRun
from tests.conftest import make_evaluation


def test_valid_brief(brief):
    assert brief.brand == "TestBrand"
    assert brief.budget_tier == "moderate"  # default
    assert brief.geographic_focus == "India"  # default


def test_brief_rejects_empty_brand():
    with pytest.raises(ValidationError):
        CampaignBrief(
            brand="",
            industry="fintech",
            product_or_service="x",
            campaign_goal="y",
            target_audience="z",
        )


def test_brief_rejects_unknown_budget_tier():
    with pytest.raises(ValidationError):
        CampaignBrief(
            brand="B",
            industry="fintech",
            product_or_service="x",
            campaign_goal="y",
            target_audience="z",
            budget_tier="astronomical",
        )


def test_pipeline_run_avg_score(brief):
    run = PipelineRun(run_id="r1", brief=brief)
    assert run.avg_score is None
    run.evaluation = make_evaluation(final_score=8.0)
    assert run.avg_score == 8.0


def test_agent_event_serializes_for_sse():
    event = AgentEvent(agent_name="trend_agent", status=AgentStatus.RUNNING, thought="hi")
    payload = event.model_dump_json()
    assert '"trend_agent"' in payload
    assert '"running"' in payload
