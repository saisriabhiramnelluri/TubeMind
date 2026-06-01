"""Query endpoint — ask questions about ingested videos."""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.db.models import list_videos, get_video
from app.rag.pipeline import run_rag_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    """Request body for querying the knowledge base."""
    question: str = Field(..., min_length=3, description="Natural language question")
    video_id: Optional[str] = Field(None, description="Optional: filter to a specific video")
    history: Optional[list[dict]] = Field(None, description="Conversation history [{role, content}]")


class CitationResponse(BaseModel):
    """A timestamp citation."""
    timestamp: str
    seconds: int
    text: str
    video_id: str


class QueryResponse(BaseModel):
    """Response with AI-generated answer and citations."""
    answer: str
    citations: list[CitationResponse]
    sources: list[dict]


@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Ask a question about ingested YouTube videos.
    
    The RAG pipeline retrieves relevant transcript chunks,
    builds a grounded prompt, and generates an answer using Gemini.
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

    # Run RAG pipeline
    result = await run_rag_pipeline(
        query=request.question,
        video_id=request.video_id,
        video_titles=video_titles,
        chat_history=request.history,
    )

    return QueryResponse(
        answer=result.answer,
        citations=[
            CitationResponse(
                timestamp=c.timestamp,
                seconds=c.seconds,
                text=c.text,
                video_id=c.video_id,
            )
            for c in result.citations
        ],
        sources=result.sources,
    )
