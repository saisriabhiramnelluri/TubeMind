"""Extract video metadata using yt-dlp without downloading the video."""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    """Structured video metadata."""
    video_id: str
    title: str
    channel: str
    duration: int  # seconds
    thumbnail_url: str
    url: str
    description: Optional[str] = None
    upload_date: Optional[str] = None


def extract_metadata(url: str, video_id: str) -> VideoMetadata:
    """
    Extract metadata from a YouTube video using yt-dlp.
    
    Falls back to minimal metadata if yt-dlp fails.
    """
    try:
        import yt_dlp

        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            return VideoMetadata(
                video_id=video_id,
                title=info.get('title', 'Unknown Title'),
                channel=info.get('uploader', info.get('channel', 'Unknown Channel')),
                duration=int(info.get('duration', 0)),
                thumbnail_url=info.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
                url=url,
                description=(info.get('description', '') or '')[:500],
                upload_date=info.get('upload_date'),
            )

    except Exception as e:
        logger.warning(
            "Metadata extraction via yt-dlp failed, using fallback  [video_id=%s]: %s",
            video_id, e,
        )

        # Fallback: construct minimal metadata from video_id
        return VideoMetadata(
            video_id=video_id,
            title=f"YouTube Video ({video_id})",
            channel="Unknown Channel",
            duration=0,
            thumbnail_url=f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            url=url,
        )
