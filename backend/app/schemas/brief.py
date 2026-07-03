"""The user-submitted campaign brief that kicks off the pipeline."""
from typing import Literal

from pydantic import BaseModel, Field


class CampaignBrief(BaseModel):
    brand: str = Field(..., min_length=1, max_length=200)
    industry: str = Field(..., min_length=1, max_length=200)
    product_or_service: str = Field(..., min_length=1, max_length=500)
    campaign_goal: str = Field(..., min_length=1, max_length=1000)
    target_audience: str = Field(..., min_length=1, max_length=500)
    budget_tier: Literal["lean", "moderate", "premium", "enterprise"] = "moderate"
    geographic_focus: str = "India"
    extra_context: str | None = None
