"""Temporal chunking for transcript segments with timestamp preservation."""

import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TranscriptChunk:
    """A chunk of transcript text with timestamp boundaries."""
    video_id: str
    chunk_index: int
    text: str
    start_time: float
    end_time: float

    def to_dict(self) -> dict:
        return asdict(self)


def _estimate_tokens(text: str) -> int:
    """Rough token estimation: ~0.75 words per token for English."""
    return int(len(text.split()) / 0.75)


def create_temporal_chunks(
    segments: list[dict],
    video_id: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[TranscriptChunk]:
    """
    Split transcript segments into overlapping chunks while preserving timestamps.
    
    Args:
        segments: Cleaned transcript segments [{start, duration, text}]
        video_id: YouTube video ID
        chunk_size: Target chunk size in approximate tokens
        chunk_overlap: Overlap between consecutive chunks in approximate tokens
        
    Returns:
        List of TranscriptChunk objects
    """
    if not segments:
        return []

    chunks = []
    current_texts = []
    current_start = segments[0]["start"]
    current_tokens = 0
    chunk_index = 0

    # Track segments for overlap
    segment_buffer = []

    for seg in segments:
        seg_text = seg["text"].strip()
        if not seg_text:
            continue

        seg_tokens = _estimate_tokens(seg_text)
        seg_end = seg["start"] + seg.get("duration", 0)

        segment_buffer.append(seg)
        current_texts.append(seg_text)
        current_tokens += seg_tokens

        # Check if we've reached the chunk size
        if current_tokens >= chunk_size:
            chunk_text = " ".join(current_texts)
            chunks.append(TranscriptChunk(
                video_id=video_id,
                chunk_index=chunk_index,
                text=chunk_text,
                start_time=current_start,
                end_time=seg_end,
            ))
            chunk_index += 1

            # Calculate overlap: keep the last N tokens worth of segments
            overlap_texts = []
            overlap_tokens = 0
            overlap_segments = []

            for s in reversed(segment_buffer):
                s_tokens = _estimate_tokens(s["text"])
                if overlap_tokens + s_tokens > chunk_overlap:
                    break
                overlap_texts.insert(0, s["text"])
                overlap_segments.insert(0, s)
                overlap_tokens += s_tokens

            # Reset with overlap
            current_texts = overlap_texts
            current_tokens = overlap_tokens
            current_start = overlap_segments[0]["start"] if overlap_segments else seg_end
            segment_buffer = overlap_segments

    # Don't lose the last chunk
    if current_texts:
        last_seg = segments[-1]
        chunk_text = " ".join(current_texts)
        chunks.append(TranscriptChunk(
            video_id=video_id,
            chunk_index=chunk_index,
            text=chunk_text,
            start_time=current_start,
            end_time=last_seg["start"] + last_seg.get("duration", 0),
        ))

    logger.info(
        "Temporal chunking complete  [video_id=%s, chunks=%d, chunk_size=%d, overlap=%d]",
        video_id, len(chunks), chunk_size, chunk_overlap,
    )
    return chunks
