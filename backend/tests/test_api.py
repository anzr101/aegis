"""API surface tests via httpx ASGI transport — no server, no network."""
import asyncio

import httpx
import pytest

import app.services.orchestrator as orch_module
from app.main import create_app
from app.services.orchestrator import Orchestrator
from tests.conftest import StubLLM


@pytest.fixture
async def client(db, bus, store, monkeypatch):
    # Route the singleton orchestrator through the stub LLM + test store.
    monkeypatch.setattr(
        orch_module, "_orchestrator", Orchestrator(llm=StubLLM(), bus=bus, store=store)
    )
    app = create_app()
    transport = httpx.ASGITransport(app=app)  # lifespan not run; db fixture inits tables
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_run_pipeline_returns_run_id_and_persists(client):
    payload = {
        "brand": "TestBrand",
        "industry": "fintech",
        "product_or_service": "A budgeting app",
        "campaign_goal": "Acquire 10k users",
        "target_audience": "Young professionals",
    }
    r = await client.post("/api/pipeline/run", json=payload)
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    # the background task with the stub LLM finishes almost instantly
    for _ in range(50):
        result = await client.get(f"/api/pipeline/{run_id}")
        if result.status_code == 200 and result.json().get("status") == "completed":
            break
        await asyncio.sleep(0.05)
    assert result.json()["status"] == "completed"
    assert result.json()["final_brief"]["recommended_concept"] == "Concept A"


async def test_invalid_brief_rejected(client):
    r = await client.post("/api/pipeline/run", json={"brand": "OnlyBrand"})
    assert r.status_code == 422


async def test_unknown_run_is_404(client):
    r = await client.get("/api/pipeline/does-not-exist")
    assert r.status_code == 404


async def test_history_list(client):
    r = await client.get("/api/pipeline/history/list")
    assert r.status_code == 200
    assert "runs" in r.json()
