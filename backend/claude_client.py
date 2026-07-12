"""
Thin Anthropic client with streaming + retries.

Only imported/used in LIVE mode. In DEMO mode this file is never touched,
so a missing `anthropic` package can't break a fresh install.
"""
import asyncio
from typing import AsyncIterator

from . import config


async def stream_completion(prompt: str, max_retries: int = 3) -> AsyncIterator[str]:
    """Yield text chunks from Claude. Retries on transient errors."""
    from anthropic import AsyncAnthropic  # imported lazily

    client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    attempt = 0
    while True:
        attempt += 1
        try:
            async with client.messages.stream(
                model=config.MODEL,
                max_tokens=1400,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
            return
        except Exception as exc:  # noqa: BLE001 — surface a clean message upward
            if attempt >= max_retries:
                raise RuntimeError(
                    f"Claude request failed after {max_retries} attempts: {exc}"
                ) from exc
            await asyncio.sleep(0.8 * attempt)
