"""Video ingestion endpoint — accepts YouTube URL, processes full pipeline."""

import numpy as np
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import save_video, save_chunks, get_video
from app.ingestion.youtube_loader import validate_youtube_url, fetch_transcript
from app.ingestion.metadata_extractor import extract_metadata
from app.ingestion.transcript_cleaner import clean_transcript
from app.ingestion.chunker import create_temporal_chunks
from app.embeddings.embedder import get_embedder
from app.vectorstore.faiss_manager import get_faiss_manager
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


class IngestRequest(BaseModel):
    """Request body for video ingestion."""
    youtube_url: str = Field(..., description="YouTube video URL to ingest")


class IngestResponse(BaseModel):
    """Response after successful ingestion."""
    video_id: str
    title: str
    channel: str
    duration: int
    chunks_count: int
    status: str


@router.post("/ingest", response_model=IngestResponse)
async def ingest_video(
    request: IngestRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Ingest a YouTube video: extract transcript, chunk, embed, and store.
    
    Full pipeline:
    1. Validate YouTube URL
    2. Check if already ingested
    3. Extract video metadata (yt-dlp)
    4. Fetch transcript (youtube-transcript-api)
    5. Clean transcript
    6. Create temporal chunks
    7. Generate embeddings
    8. Store in PostgreSQL + FAISS
    """
    settings = get_settings()

    # Step 1: Validate URL
    is_valid, video_id = validate_youtube_url(request.youtube_url)
    if not is_valid:
        raise ValueError(video_id)  # video_id contains error message here

    # Step 2: Check if already ingested
    existing = await get_video(session, video_id)
    if existing and existing.status == "processed":
        return IngestResponse(
            video_id=existing.video_id,
            title=existing.title,
            channel=existing.channel or "Unknown",
            duration=existing.duration or 0,
            chunks_count=existing.chunks_count,
            status="already_exists",
        )

    # Step 3: Extract metadata
    logger.info("Step 1/8: Extracting metadata for video [id=%s]", video_id)
    metadata = extract_metadata(request.youtube_url, video_id)

    # Save video as "processing"
    video = await save_video(session, {
        "video_id": video_id,
        "title": metadata.title,
        "channel": metadata.channel,
        "duration": metadata.duration,
        "thumbnail_url": metadata.thumbnail_url,
        "url": request.youtube_url,
        "status": "processing",
    })
    await session.commit()

    try:
        # Step 4: Fetch transcript
        logger.info("Step 2/8: Fetching transcript for video [id=%s]", video_id)
        transcript_data = fetch_transcript(video_id)

        # Step 5: Clean transcript
        logger.info("Step 3/8: Cleaning raw transcript for video [id=%s]", video_id)
        cleaned_segments = clean_transcript(transcript_data["segments"])

        if not cleaned_segments:
            raise ValueError("Transcript is empty after cleaning")

        # Step 6: Create temporal chunks
        logger.info("Step 4/8: Splitting transcript into temporal chunks for video [id=%s]", video_id)
        chunks = create_temporal_chunks(
            segments=cleaned_segments,
            video_id=video_id,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        if not chunks:
            raise ValueError("No chunks created from transcript")

        # Step 7: Generate embeddings
        logger.info("Step 5/8: Generating embeddings  [chunks=%d, video_id=%s]", len(chunks), video_id)
        embedder = get_embedder()
        chunk_texts = [c.text for c in chunks]
        embeddings = embedder.embed_texts(chunk_texts)

        # Step 8a: Store chunks with embeddings in PostgreSQL
        chunk_records = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_records.append({
                "video_id": video_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "embedding": emb.tobytes(),  # Store as binary
            })

        await save_chunks(session, chunk_records)

        # Step 8b: Add to FAISS index
        faiss_mgr = get_faiss_manager(dimension=embedder.dimension)
        metadata_list = [
            {
                "video_id": c.video_id,
                "chunk_index": c.chunk_index,
                "text": c.text,
                "start_time": c.start_time,
                "end_time": c.end_time,
            }
            for c in chunks
        ]
        faiss_mgr.add_embeddings(embeddings, metadata_list)

        # Update video status
        video.status = "processed"
        video.chunks_count = len(chunks)
        video.language = transcript_data.get("language")
        await session.commit()

        logger.info(
            "Ingestion complete for video [id=%s] -- %d chunks stored and indexed",
            video_id, len(chunks),
        )

        return IngestResponse(
            video_id=video_id,
            title=metadata.title,
            channel=metadata.channel,
            duration=metadata.duration,
            chunks_count=len(chunks),
            status="processed",
        )

    except Exception as e:
        # Mark video as failed
        video.status = "failed"
        await session.commit()
        logger.error("Ingestion failed for video [id=%s]: %s", video_id, e)
        raise
