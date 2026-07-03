"""Run persistence + retrieval-augmented memory.

save_run / get_run / list_recent are plain CRUD. retrieve_similar() is the
"memory" feature: before a new pipeline runs, past high-scoring campaigns in
the same industry are retrieved and offered to the agents as context.
(Deliberately SQL-based — industry match + score threshold — not vector
search: briefs are short and structured, exact-match retrieval is enough.)
"""
import json

import structlog
from sqlalchemy import select

from app.core.config import get_settings
from app.db.engine import get_session_factory
from app.db.models import RunRecord
from app.schemas import CampaignBrief, PipelineRun

log = structlog.get_logger()


class RunStore:
    async def save_run(self, run: PipelineRun) -> None:
        record = RunRecord(
            run_id=run.run_id,
            brand=run.brief.brand,
            industry=run.brief.industry,
            status=run.status,
            avg_score=run.avg_score,
            total_tokens=run.total_tokens,
            total_latency_ms=run.total_latency_ms,
            created_at=run.created_at,
            brief=run.brief.model_dump(mode="json"),
            final_brief=run.final_brief.model_dump(mode="json") if run.final_brief else None,
            full_run=json.loads(run.model_dump_json()),
        )
        factory = get_session_factory()
        async with factory() as session:
            await session.merge(record)  # upsert by primary key
            await session.commit()
        log.info("run_saved", run_id=run.run_id, status=run.status, avg_score=run.avg_score)

    async def get_run(self, run_id: str) -> dict | None:
        factory = get_session_factory()
        async with factory() as session:
            record = await session.get(RunRecord, run_id)
        return record.full_run if record else None

    async def list_recent(self, limit: int = 50) -> list[dict]:
        factory = get_session_factory()
        async with factory() as session:
            rows = (
                await session.execute(
                    select(RunRecord).order_by(RunRecord.created_at.desc()).limit(limit)
                )
            ).scalars().all()
        return [
            {
                "run_id": r.run_id,
                "brand": r.brand,
                "industry": r.industry,
                "avg_score": r.avg_score,
                "total_tokens": r.total_tokens,
                "total_latency_ms": r.total_latency_ms,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]

    async def retrieve_similar(
        self, brief: CampaignBrief, top_k: int | None = None
    ) -> list[dict]:
        """Past successful campaigns in the same industry (score >= 7)."""
        k = top_k or get_settings().memory_top_k
        factory = get_session_factory()
        async with factory() as session:
            rows = (
                await session.execute(
                    select(RunRecord)
                    .where(
                        RunRecord.industry == brief.industry,
                        RunRecord.avg_score >= 7.0,
                        RunRecord.status == "completed",
                    )
                    .order_by(RunRecord.avg_score.desc(), RunRecord.created_at.desc())
                    .limit(k)
                )
            ).scalars().all()
        results = [
            {
                "run_id": r.run_id,
                "brief": r.brief,
                "final_brief": r.final_brief,
                "avg_score": r.avg_score,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
        log.info("memory_retrieval", industry=brief.industry, found=len(results))
        return results


_store: RunStore | None = None


def get_store() -> RunStore:
    global _store
    if _store is None:
        _store = RunStore()
    return _store
