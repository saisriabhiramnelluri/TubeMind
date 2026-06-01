"""LLM response generation using Google Gemini — async native and streaming modes with automatic retry."""

import logging
import asyncio
from typing import AsyncGenerator
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level client (initialized lazily)
_client = None


def _get_client():
    """Get or create the Gemini client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = genai.Client(api_key=settings.gemini_api_key)
        logger.info("Gemini API client initialized  [model=%s]", settings.gemini_model)
    return _client


async def generate_answer(prompt: str) -> str:
    """
    Generate a complete answer using Google Gemini async API with automatic retry.

    Args:
        prompt: Complete prompt with system instructions and context

    Returns:
        Generated text response
    """
    settings = get_settings()
    client = _get_client()

    max_retries = 4
    delay = 1.0  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Generating answer (async)  [attempt=%d/%d]", attempt, max_retries)
            response = await client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=8192,
                    temperature=0.3,
                )
            )

            if response.text:
                return response.text.strip()
            else:
                logger.warning("Gemini returned an empty response -- returning fallback message")
                return "I was unable to generate a response. Please try rephrasing your question."

        except APIError as e:
            is_transient = e.code in (429, 500, 503)
            logger.warning(
                "Gemini API error on attempt %d/%d: %s (code=%s, status=%s, transient=%s)",
                attempt, max_retries, e.message, e.code, e.status, is_transient
            )
            if attempt == max_retries or not is_transient:
                raise RuntimeError(f"Failed to generate response: {str(e)}")
            await asyncio.sleep(delay)
            delay *= 2.0

        except Exception as e:
            logger.error("Gemini API request failed with unexpected error on attempt %d/%d: %s", attempt, max_retries, e)
            if attempt == max_retries:
                raise RuntimeError(f"Failed to generate response: {str(e)}")
            await asyncio.sleep(delay)
            delay *= 2.0


async def generate_answer_stream(prompt: str) -> AsyncGenerator[str, None]:
    """
    Stream an answer from Google Gemini token-by-token using the async API with automatic retry.

    Args:
        prompt: Complete prompt with system instructions and context

    Yields:
        Text chunks as they are generated
    """
    settings = get_settings()
    client = _get_client()

    max_retries = 4
    delay = 1.0  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Starting streamed response generation (async)  [model=%s, attempt=%d/%d]", settings.gemini_model, attempt, max_retries)
            
            response_stream = await client.aio.models.generate_content_stream(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=8192,
                    temperature=0.3,
                )
            )

            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
            
            # If we completed successfully, break from retry loop
            break

        except APIError as e:
            is_transient = e.code in (429, 500, 503)
            logger.warning(
                "Gemini streaming API error on attempt %d/%d: %s (code=%s, status=%s, transient=%s)",
                attempt, max_retries, e.message, e.code, e.status, is_transient
            )
            if attempt == max_retries or not is_transient:
                yield f"\n\n[Error: Failed to generate response — {str(e)}]"
                return
            await asyncio.sleep(delay)
            delay *= 2.0

        except Exception as e:
            logger.error("Gemini streaming request failed with unexpected error on attempt %d/%d: %s", attempt, max_retries, e)
            if attempt == max_retries:
                yield f"\n\n[Error: Failed to generate response — {str(e)}]"
                return
            await asyncio.sleep(delay)
            delay *= 2.0
