"""Full pipeline runs against the stub LLM — the core integration tests."""
from app.schemas import CreativeStrategy, TrendIntelligence
from app.services.orchestrator import Orchestrator
from tests.conftest import StubLLM


async def test_happy_path_completes_with_all_outputs(store, bus, brief):
    llm = StubLLM()
    orch = Orchestrator(llm=llm, bus=bus, store=store)

    run = await orch.execute(brief, run_id="happy-1")

    assert run.status == "completed"
    assert run.trend_intelligence is not None
    assert run.audience_psychology is not None
    assert run.creative_strategy is not None
    assert run.evaluation is not None
    assert run.final_brief is not None
    assert run.total_tokens == 500  # 5 agents × 100 stub tokens

    # persisted
    assert await store.get_run("happy-1") is not None


async def test_creative_failure_skips_scoring_but_supervisor_runs(store, bus, brief):
    llm = StubLLM(fail_for={CreativeStrategy})
    orch = Orchestrator(llm=llm, bus=bus, store=store)

    run = await orch.execute(brief, run_id="degraded-1")

    assert run.creative_strategy is None
    assert run.evaluation is None            # scoring skipped
    assert run.final_brief is not None       # supervisor still synthesizes
    assert run.status == "completed"
    assert "Evaluation" not in llm.calls     # scoring agent never invoked


async def test_trend_failure_degrades_gracefully(store, bus, brief):
    llm = StubLLM(fail_for={TrendIntelligence})
    orch = Orchestrator(llm=llm, bus=bus, store=store)

    run = await orch.execute(brief, run_id="degraded-2")

    assert run.trend_intelligence is None
    assert run.creative_strategy is not None
    assert run.evaluation is not None
    assert run.status == "completed"


async def test_generated_run_id_when_none_given(store, bus, brief):
    orch = Orchestrator(llm=StubLLM(), bus=bus, store=store)
    run = await orch.execute(brief)
    assert run.run_id  # uuid was generated
    assert await store.get_run(run.run_id) is not None
