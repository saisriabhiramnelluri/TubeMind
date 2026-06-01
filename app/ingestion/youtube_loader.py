"""YouTube URL parsing and transcript extraction."""

import re
import logging
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)

# Patterns for extracting video IDs from various YouTube URL formats
YOUTUBE_URL_PATTERNS = [
    r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
    r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
    r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
    r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
    r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
]


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract the 11-character video ID from a YouTube URL.
    
    Supports:
    - youtube.com/watch?v=ID
    - youtu.be/ID
    - youtube.com/embed/ID
    - youtube.com/shorts/ID
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()

    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Check if the input is already a video ID (11 chars, alphanumeric + _ -)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    return None


def validate_youtube_url(url: str) -> tuple[bool, str]:
    """
    Validate a YouTube URL and return (is_valid, video_id_or_error).
    """
    video_id = extract_video_id(url)
    if video_id:
        return True, video_id
    return False, "Invalid YouTube URL. Please provide a valid YouTube video link."


def fetch_transcript(video_id: str, preferred_languages: list[str] = None) -> dict:
    """
    Fetch transcript for a YouTube video.

    Compatible with youtube-transcript-api v1.x (instance-based API).

    Returns:
        dict with keys:
        - 'segments': list of {start, duration, text}
        - 'language': detected language code
    """
    if preferred_languages is None:
        preferred_languages = ['en', 'en-US', 'en-GB']

    api = YouTubeTranscriptApi()

    try:
        # Primary: Use api.fetch() which auto-selects the best transcript
        # and supports language preferences natively
        fetched = api.fetch(video_id, languages=preferred_languages)
        language = fetched.language_code
        logger.info(
            "Fetched transcript  [language=%s, generated=%s, snippets=%d, video_id=%s]",
            language, fetched.is_generated, len(fetched.snippets), video_id,
        )

        # Build segment list from FetchedTranscriptSnippet objects
        segments = []
        for snippet in fetched.snippets:
            segments.append({
                "start": float(snippet.start),
                "duration": float(snippet.duration),
                "text": str(snippet.text).strip(),
            })

        return {
            "segments": segments,
            "language": language or "unknown",
        }

    except Exception as primary_err:
        logger.warning(
            "Primary fetch failed for video [id=%s]: %s — trying fallback",
            video_id, primary_err,
        )

    # Fallback: Try fetching with api.list() to find any available transcript
    try:
        transcript_list = api.list(video_id)

        # Try manually created transcripts first
        fetched = None
        try:
            transcript_obj = transcript_list.find_manually_created_transcript(preferred_languages)
            fetched = transcript_obj.fetch()
            language = fetched.language_code
            logger.info("Found manually created transcript  [language=%s, video_id=%s]", language, video_id)
        except Exception:
            pass

        # Fall back to auto-generated
        if fetched is None:
            try:
                transcript_obj = transcript_list.find_generated_transcript(preferred_languages)
                fetched = transcript_obj.fetch()
                language = fetched.language_code
                logger.info("Found auto-generated transcript  [language=%s, video_id=%s]", language, video_id)
            except Exception:
                pass

        # Fall back to any available transcript
        if fetched is None:
            for t in transcript_list:
                fetched = t.fetch()
                language = fetched.language_code
                logger.info("Using fallback transcript  [language=%s, video_id=%s]", language, video_id)
                break

        if fetched is None:
            raise ValueError(f"No transcript available for video {video_id}")

        # Build segment list from FetchedTranscriptSnippet objects
        segments = []
        for snippet in fetched.snippets:
            segments.append({
                "start": float(snippet.start),
                "duration": float(snippet.duration),
                "text": str(snippet.text).strip(),
            })

        return {
            "segments": segments,
            "language": language or "unknown",
        }

    except ValueError:
        raise
    except Exception as e:
        logger.error("Transcript fetch failed  [video_id=%s]: %s", video_id, e)
        raise ValueError(f"Could not fetch transcript: {str(e)}")
