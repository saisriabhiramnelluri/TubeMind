"""RAG pipeline orchestrator: retrieve -> prompt -> generate -> format."""

import re
import json
import logging
from dataclasses import dataclass
from typing import AsyncGenerator
from app.vectorstore.retriever import retrieve, RetrievedChunk
from app.rag.prompt_builder import build_prompt, NO_CONTEXT_RESPONSE
from app.rag.response_generator import generate_answer, generate_answer_stream

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A timestamp citation from the answer."""
    timestamp: str
    seconds: int
    text: str
    video_id: str


@dataclass
class RAGResponse:
    """Complete RAG pipeline response."""
    answer: str
    citations: list[Citation]
    sources: list[dict]


def _extract_citations(
    answer: str,
    retrieved_chunks: list[RetrievedChunk],
) -> list[Citation]:
    """Extract timestamp citations from the answer text."""
    citations = []
    seen_timestamps = set()

    # Find all [MM:SS] patterns in the answer
    timestamp_pattern = r'\[(\d{1,2}:\d{2})\]'
    matches = re.finditer(timestamp_pattern, answer)

    for match in matches:
        ts = match.group(1)
        if ts in seen_timestamps:
            continue
        seen_timestamps.add(ts)

        # Convert MM:SS to seconds
        parts = ts.split(':')
        seconds = int(parts[0]) * 60 + int(parts[1])

        # Find the closest chunk to this timestamp
        best_chunk = None
        best_dist = float('inf')
        for chunk in retrieved_chunks:
            dist = abs(chunk.start_time - seconds)
            if dist < best_dist:
                best_dist = dist
                best_chunk = chunk

        # Extract surrounding text for context
        context_text = ""
        if best_chunk:
            context_text = best_chunk.text[:150] + "..." if len(best_chunk.text) > 150 else best_chunk.text

        citations.append(Citation(
            timestamp=ts,
            seconds=seconds,
            text=context_text,
            video_id=best_chunk.video_id if best_chunk else "",
        ))

    return citations


def _build_sources(retrieved_chunks, video_titles):
    """Build source info from retrieved chunks."""
    source_video_ids = list(set(c.video_id for c in retrieved_chunks))
    sources = []
    for vid in source_video_ids:
        title = video_titles.get(vid, vid) if video_titles else vid
        sources.append({"video_id": vid, "title": title})
    return sources


async def run_rag_pipeline(
    query: str,
    video_id: str = None,
    video_titles: dict[str, str] = None,
    chat_history: list[dict] = None,
) -> RAGResponse:
    """
    Execute the full RAG pipeline (non-streaming).

    Steps:
    1. Retrieve relevant chunks from FAISS
    2. Build a grounded prompt with context
    3. Generate answer using Gemini
    4. Extract citations from the response

    Args:
        query: User's natural language question
        video_id: Optional filter for a specific video
        video_titles: Optional mapping of video_id -> title
        chat_history: Optional conversation history for follow-up context

    Returns:
        RAGResponse with answer, citations, and source information
    """
    logger.info("RAG pipeline started  [query=%s]", query[:80])

    # Step 1: Retrieve relevant chunks
    retrieved_chunks = retrieve(query=query, video_id=video_id)
    logger.info("Context retrieval complete  [chunks_retrieved=%d]", len(retrieved_chunks))

    # Step 2: Build grounded prompt
    prompt = build_prompt(
        query=query,
        retrieved_chunks=retrieved_chunks,
        video_titles=video_titles,
        chat_history=chat_history,
    )

    # If no transcript context was found, return a pre-built honest response
    # instead of asking the LLM to generate from nothing (which causes hallucination)
    if prompt is None:
        logger.info("No transcript context found — returning pre-built no-context response")
        return RAGResponse(
            answer=NO_CONTEXT_RESPONSE,
            citations=[],
            sources=[],
        )

    # Log context size for observability
    context_chars = sum(len(c.text) for c in retrieved_chunks)
    logger.info("Sending to LLM  [context_chars=%d, chunks=%d]", context_chars, len(retrieved_chunks))

    # Step 3: Generate answer using Gemini (strictly grounded in transcript)
    answer = await generate_answer(prompt)

    # Step 4: Extract citations
    citations = _extract_citations(answer, retrieved_chunks)

    # Build source info
    sources = _build_sources(retrieved_chunks, video_titles)

    logger.info(
        "RAG pipeline complete  [citations=%d, source_videos=%d]",
        len(citations), len(sources),
    )

    return RAGResponse(
        answer=answer,
        citations=citations,
        sources=sources,
    )


async def run_rag_pipeline_stream(
    query: str,
    video_id: str = None,
    video_titles: dict[str, str] = None,
    chat_history: list[dict] = None,
) -> AsyncGenerator[str, None]:
    """
    Execute the RAG pipeline with streamed Gemini response.

    Yields Server-Sent Events (SSE) as JSON strings:
      - {"type": "sources", "sources": [...]}       (sent immediately after retrieval)
      - {"type": "chunk",   "text": "..."}           (each token from Gemini)
      - {"type": "done",    "citations": [...]}      (final event with extracted citations)

    Args:
        query: User's natural language question
        video_id: Optional filter for a specific video
        video_titles: Optional mapping of video_id -> title
        chat_history: Optional conversation history for follow-up context

    Yields:
        JSON-encoded SSE event strings
    """
    logger.info("RAG streaming pipeline started  [query=%s]", query[:80])

    # Step 1: Retrieve relevant chunks
    retrieved_chunks = retrieve(query=query, video_id=video_id)
    logger.info("Context retrieval complete  [chunks_retrieved=%d]", len(retrieved_chunks))

    # Step 2: Build grounded prompt
    prompt = build_prompt(
        query=query,
        retrieved_chunks=retrieved_chunks,
        video_titles=video_titles,
        chat_history=chat_history,
    )

    # If no transcript context, emit the pre-built response directly
    # without calling the LLM (avoids hallucination)
    if prompt is None:
        logger.info("No transcript context found — streaming pre-built no-context response")
        yield json.dumps({"type": "sources", "sources": []})
        yield json.dumps({"type": "chunk", "text": NO_CONTEXT_RESPONSE})
        yield json.dumps({"type": "done", "citations": []})
        return

    # Emit sources immediately so the frontend can show them
    sources = _build_sources(retrieved_chunks, video_titles)
    yield json.dumps({"type": "sources", "sources": sources})

    # Log context size for observability
    context_chars = sum(len(c.text) for c in retrieved_chunks)
    logger.info("Sending to LLM  [context_chars=%d, chunks=%d]", context_chars, len(retrieved_chunks))

    # Step 3: Stream the answer from Gemini (strictly grounded in transcript)
    full_answer = ""
    async for text_chunk in generate_answer_stream(prompt):
        full_answer += text_chunk
        yield json.dumps({"type": "chunk", "text": text_chunk})

    # Step 4: Extract citations from the full answer
    citations = _extract_citations(full_answer, retrieved_chunks)
    citations_data = [
        {
            "timestamp": c.timestamp,
            "seconds": c.seconds,
            "text": c.text,
            "video_id": c.video_id,
        }
        for c in citations
    ]

    yield json.dumps({"type": "done", "citations": citations_data})

    logger.info(
        "RAG streaming pipeline complete  [citations=%d, source_videos=%d]",
        len(citations), len(sources),
    )
