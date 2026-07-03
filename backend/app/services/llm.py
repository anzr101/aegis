"""LLM client — wraps the Anthropic SDK with:

  - Retry (tenacity, exponential backoff) on API errors AND schema-validation
    failures — an invalid JSON response simply triggers another attempt
  - Structured output enforcement: the output model's JSON schema is injected
    into the system prompt and the reply is validated with Pydantic
  - Token + latency tracking per call
  - Optional Anthropic server-side web_search tool (Trend agent)

Note: no temperature/top_p — current Claude models (Sonnet 5+) reject
non-default sampling parameters; behaviour is steered by prompting instead.
"""
import json
import re
import time
from typing import Any, Type, TypeVar

import structlog
from anthropic import APIError, APITimeoutError, AsyncAnthropic, RateLimitError
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)
log = structlog.get_logger()
settings = get_settings()


class LLMResult(BaseModel):
    parsed: Any
    raw_text: str
    tokens_used: int
    latency_ms: int
    model_used: str


class LLMClient:
    """One async client per process."""

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (APIError, APITimeoutError, RateLimitError, ValidationError)
        ),
        reraise=True,
    )
    async def structured_call(
        self,
        system: str,
        user: str,
        output_model: Type[T],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> LLMResult:
        """Call Claude and parse the reply into `output_model`."""
        used_model = model or settings.operational_model
        return await self._call(used_model, system, user, output_model, max_tokens, tools=None)

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (APIError, APITimeoutError, RateLimitError, ValidationError)
        ),
        reraise=True,
    )
    async def call_with_web_search(
        self,
        system: str,
        user: str,
        output_model: Type[T],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> LLMResult:
        """Same as structured_call, plus Anthropic's server-side web_search tool.

        Used by the Trend agent for live market intelligence.
        """
        used_model = model or settings.operational_model
        tools = [{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": settings.max_web_searches,
        }]
        return await self._call(used_model, system, user, output_model, max_tokens, tools=tools)

    async def _call(
        self,
        model: str,
        system: str,
        user: str,
        output_model: Type[T],
        max_tokens: int,
        tools: list[dict] | None,
    ) -> LLMResult:
        schema_json = json.dumps(output_model.model_json_schema(), indent=2)
        system_with_schema = (
            f"{system}\n\n"
            f"You MUST respond with a JSON object matching this exact schema. "
            f"The JSON must be the LAST thing in your response — no markdown "
            f"code fences around it, no explanation after it.\n\n"
            f"SCHEMA:\n{schema_json}"
        )

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_with_schema,
            "messages": [{"role": "user", "content": user}],
        }
        if tools:
            kwargs["tools"] = tools

        start = time.perf_counter()
        response = await self._client.messages.create(**kwargs)
        latency_ms = int((time.perf_counter() - start) * 1000)

        # Collect all text blocks (web_search responses contain several).
        text_parts = [
            block.text
            for block in response.content
            if getattr(block, "text", None) is not None
        ]
        raw_text = "\n".join(text_parts).strip()
        tokens = response.usage.input_tokens + response.usage.output_tokens

        parsed = output_model.model_validate(extract_json(raw_text))

        log.info(
            "llm_call_success",
            model=model,
            tokens=tokens,
            latency_ms=latency_ms,
            output_model=output_model.__name__,
            web_search=bool(tools),
        )
        return LLMResult(
            parsed=parsed,
            raw_text=raw_text,
            tokens_used=tokens,
            latency_ms=latency_ms,
            model_used=model,
        )


def extract_json(text: str) -> dict:
    """Extract a JSON object from text that may contain prose or code fences.

    1. Try parsing as-is
    2. Strip ```json ... ``` fences
    3. Fall back to the largest balanced {...} block
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    candidates = []
    for i, ch in enumerate(text):
        if ch == "{":
            depth = 0
            for j in range(i, len(text)):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        candidates.append((j - i, text[i:j + 1]))
                        break
    candidates.sort(reverse=True)
    for _, candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"No valid JSON found in response. First 500 chars: {text[:500]}")


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
