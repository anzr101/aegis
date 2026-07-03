"""Database round-trips: save, fetch, history, similarity retrieval."""
from app.schemas import PipelineRun
from tests.conftest import make_evaluation, make_final_brief


def _completed_run(brief, run_id="run-1", score=8.0) -> PipelineRun:
    run = PipelineRun(run_id=run_id, brief=brief, status="completed")
    run.evaluation = make_evaluation(final_score=score)
    run.final_brief = make_final_brief()
    run.total_tokens = 1234
    return run


async def test_save_and_get_run(store, brief):
    await store.save_run(_completed_run(brief))
    fetched = await store.get_run("run-1")
    assert fetched is not None
    assert fetched["run_id"] == "run-1"
    assert fetched["brief"]["brand"] == "TestBrand"
    assert fetched["final_brief"]["recommended_concept"] == "Concept A"


async def test_get_missing_run_returns_none(store):
    assert await store.get_run("nope") is None


async def test_save_is_upsert(store, brief):
    run = _completed_run(brief)
    await store.save_run(run)
    run.status = "failed"
    await store.save_run(run)  # same primary key — must not raise
    fetched = await store.get_run("run-1")
    assert fetched["status"] == "failed"


async def test_list_recent(store, brief):
    for i in range(3):
        await store.save_run(_completed_run(brief, run_id=f"run-{i}"))
    runs = await store.list_recent(limit=2)
    assert len(runs) == 2
    assert {"run_id", "brand", "industry", "avg_score", "status"} <= set(runs[0])


async def test_retrieve_similar_filters_by_industry_and_score(store, brief):
    await store.save_run(_completed_run(brief, run_id="good", score=8.5))
    await store.save_run(_completed_run(brief, run_id="weak", score=4.0))

    other = brief.model_copy(update={"industry": "automotive"})
    await store.save_run(_completed_run(other, run_id="other-industry", score=9.0))

    similar = await store.retrieve_similar(brief)
    ids = [s["run_id"] for s in similar]
    assert ids == ["good"]  # weak score filtered out, other industry excluded
