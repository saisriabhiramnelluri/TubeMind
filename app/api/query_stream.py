"""Streaming query endpoint — SSE (Server-Sent Events) for real-time responses."""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from app.db.database import get_db
from app.db.models import list_videos, get_video
from app.rag.pipeline import run_rag_pipeline_stream

logger = logging.getLogger(__name__)
router = APIRouter()


class StreamQueryRequest(BaseModel):
    """Request body for streaming query."""
    question: str = Field(..., min_length=3, description="Natural language question")
    video_id: Optional[str] = Field(None, description="Optional: filter to a specific video")
    history: Optional[list[dict]] = Field(None, description="Conversation history [{role, content}]")


@router.post("/query/stream")
async def query_stream(
    request: StreamQueryRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Stream an AI-generated answer as Server-Sent Events.

    Events emitted:
      - {"type": "sources",  "sources": [...]}   — source videos used for context
      - {"type": "chunk",    "text": "..."}       — each text chunk from Gemini
      - {"type": "done",     "citations": [...]}  — final event with timestamp citations
    """
    # Build video title lookup for context
    if request.video_id:
        video = await get_video(session, request.video_id)
        if not video:
            raise ValueError(f"Video {request.video_id} not found. Please ingest it first.")
        video_titles = {video.video_id: video.title}
    else:
        videos = await list_videos(session)
        video_titles = {v.video_id: v.title for v in videos}

    if not video_titles:
        raise ValueError("No videos have been ingested yet. Please add a YouTube video first.")

    async def event_generator():
        """Yield SSE events from the RAG streaming pipeline."""
        async for event_data in run_rag_pipeline_stream(
            query=request.question,
            video_id=request.video_id,
            video_titles=video_titles,
            chat_history=request.history,
        ):
            yield {"data": event_data}

    return EventSourceResponse(event_generator())
