"""SQLAlchemy models and CRUD operations for videos and chunks."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, LargeBinary, ForeignKey, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import Base
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Video(Base):
    """Ingested YouTube video metadata."""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False, default="Unknown")
    channel = Column(String(300), nullable=True)
    duration = Column(Integer, nullable=True)  # seconds
    thumbnail_url = Column(String(500), nullable=True)
    url = Column(String(500), nullable=False)
    language = Column(String(10), nullable=True)
    status = Column(String(20), nullable=False, default="processing")
    chunks_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class Chunk(Base):
    """Transcript chunk with embedding stored as binary."""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(20), ForeignKey("videos.video_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    embedding = Column(LargeBinary, nullable=True)  # numpy array as bytes


# ─── CRUD Operations ───────────────────────────────────────────────────


async def save_video(session: AsyncSession, video_data: dict) -> Video:
    """Insert or update a video record."""
    # Check if video already exists
    result = await session.execute(
        select(Video).where(Video.video_id == video_data["video_id"])
    )
    existing = result.scalar_one_or_none()

    if existing:
        for key, value in video_data.items():
            if hasattr(existing, key) and value is not None:
                setattr(existing, key, value)
        return existing

    video = Video(**video_data)
    session.add(video)
    await session.flush()
    return video


async def get_video(session: AsyncSession, video_id: str) -> Optional[Video]:
    """Get a video by its YouTube ID."""
    result = await session.execute(
        select(Video).where(Video.video_id == video_id)
    )
    return result.scalar_one_or_none()


async def list_videos(session: AsyncSession) -> list[Video]:
    """List all ingested videos, newest first."""
    result = await session.execute(
        select(Video).where(Video.status == "processed").order_by(Video.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_video(session: AsyncSession, video_id: str) -> bool:
    """Delete a video and its chunks."""
    # Delete chunks first (cascade should handle this, but be explicit)
    await session.execute(
        delete(Chunk).where(Chunk.video_id == video_id)
    )
    result = await session.execute(
        delete(Video).where(Video.video_id == video_id)
    )
    return result.rowcount > 0


async def save_chunks(session: AsyncSession, chunks: list[dict]) -> int:
    """Bulk insert transcript chunks with embeddings."""
    chunk_objects = [Chunk(**c) for c in chunks]
    session.add_all(chunk_objects)
    await session.flush()
    return len(chunk_objects)


async def get_chunks_by_video(session: AsyncSession, video_id: str) -> list[Chunk]:
    """Get all chunks for a specific video."""
    result = await session.execute(
        select(Chunk).where(Chunk.video_id == video_id).order_by(Chunk.chunk_index)
    )
    return list(result.scalars().all())


async def get_all_chunks_with_embeddings(session: AsyncSession) -> list[Chunk]:
    """Load all chunks that have embeddings (for FAISS rebuild)."""
    result = await session.execute(
        select(Chunk).where(Chunk.embedding.isnot(None)).order_by(Chunk.id)
    )
    return list(result.scalars().all())
