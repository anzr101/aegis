"""SQLAlchemy ORM models.

One table: `runs` — one row per pipeline execution. Query columns
(brand, industry, status, avg_score, created_at) are real columns so they
can be indexed and filtered in SQL; the full nested payloads live in JSON
columns (JSONB on PostgreSQL, plain JSON on SQLite).
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# JSONB on Postgres (indexable, binary), generic JSON elsewhere (SQLite tests).
JsonColumn = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    brand: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    avg_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    brief: Mapped[dict] = mapped_column(JsonColumn)
    final_brief: Mapped[dict | None] = mapped_column(JsonColumn, nullable=True)
    full_run: Mapped[dict] = mapped_column(JsonColumn)
