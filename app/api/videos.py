"""Video management endpoints — list and delete ingested videos."""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.db import models
from app.vectorstore.faiss_manager import get_faiss_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class VideoResponse(BaseModel):
    """Video metadata response."""
    video_id: str
    title: str
    channel: Optional[str]
    duration: Optional[int]
    thumbnail_url: Optional[str]
    url: str
    chunks_count: int
    status: str
    created_at: str


@router.get("/videos", response_model=list[VideoResponse])
async def list_videos(session: AsyncSession = Depends(get_db)):
    """List all ingested videos."""
    videos = await models.list_videos(session)

    return [
        VideoResponse(
            video_id=v.video_id,
            title=v.title,
            channel=v.channel,
            duration=v.duration,
            thumbnail_url=v.thumbnail_url,
            url=v.url,
            chunks_count=v.chunks_count,
            status=v.status,
            created_at=v.created_at.isoformat() if v.created_at else "",
        )
        for v in videos
    ]


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Delete a video and all its associated data."""
    # Delete from database
    deleted = await models.delete_video(session, video_id)

    if not deleted:
        raise ValueError(f"Video {video_id} not found")

    # Delete from FAISS index
    try:
        faiss_mgr = get_faiss_manager()
        faiss_mgr.delete_video(video_id)
    except Exception as e:
        logger.warning("Failed to remove video vectors from FAISS index [video_id=%s]: %s", video_id, e)

    await session.commit()
    logger.info("Deleted video and associated data [video_id=%s]", video_id)

    return {"status": "deleted", "video_id": video_id}
