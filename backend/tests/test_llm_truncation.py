"""Truncated responses must fail fast, not burn retries on a hopeless call."""
from types import SimpleNamespace

import pytest

from app.schemas import AudiencePsychology
from app.services.llm import LLMClient, LLMTruncationError


async def test_max_tokens_stop_reason_raises_without_retry():
    client = LLMClient()
    calls = {"n": 0}

    async def fake_create(**kwargs):
        calls["n"] += 1
        return SimpleNamespace(
            stop_reason="max_tokens",
            content=[SimpleNamespace(text="{\"partial\":")],
            usage=SimpleNamespace(input_tokens=10, output_tokens=4096),
        )

    client._client = SimpleNamespace(
        messages=SimpleNamespace(create=fake_create)
    )

    with pytest.raises(LLMTruncationError):
        await client.structured_call(
            system="s", user="u", output_model=AudiencePsychology
        )
    assert calls["n"] == 1  # no retries — truncation is deterministic
