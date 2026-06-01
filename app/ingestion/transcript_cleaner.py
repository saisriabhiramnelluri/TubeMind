"""Clean raw YouTube subtitles to improve retrieval quality."""

import re
import logging

logger = logging.getLogger(__name__)

# Filler words to remove
FILLER_WORDS = {
    'um', 'uh', 'umm', 'uhh', 'hmm', 'hm',
    'er', 'erm', 'ah', 'ahh',
}

# Subtitle artifacts to strip
ARTIFACT_PATTERNS = [
    r'\[Music\]',
    r'\[Applause\]',
    r'\[Laughter\]',
    r'\[Cheering\]',
    r'\[Silence\]',
    r'\[Inaudible\]',
    r'\[Foreign\]',
    r'\[♪.*?♪\]',
    r'♪',
    r'\(music\)',
    r'\(applause\)',
    r'\(laughter\)',
]


def clean_transcript(segments: list[dict]) -> list[dict]:
    """
    Clean raw transcript segments to improve retrieval quality.
    
    Operations:
    1. Remove subtitle artifacts ([Music], [Applause], etc.)
    2. Remove filler words at sentence boundaries
    3. Normalize whitespace and punctuation
    4. Merge very short fragments with neighbors
    5. Remove duplicate consecutive segments
    
    Args:
        segments: list of {start, duration, text} dicts
        
    Returns:
        Cleaned list of {start, duration, text} dicts
    """
    if not segments:
        return []

    cleaned = []

    for segment in segments:
        text = segment.get("text", "").strip()

        if not text:
            continue

        # Step 1: Remove subtitle artifacts
        for pattern in ARTIFACT_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Step 2: Remove filler words (only standalone, not parts of words)
        words = text.split()
        filtered_words = []
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if clean_word not in FILLER_WORDS:
                filtered_words.append(word)
        text = ' '.join(filtered_words)

        # Step 3: Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\s([.,!?;:])', r'\1', text)  # Remove space before punctuation

        if not text or len(text) < 2:
            continue

        cleaned.append({
            "start": segment["start"],
            "duration": segment["duration"],
            "text": text,
        })

    # Step 4: Merge very short fragments (< 3 words) with the next segment
    merged = []
    buffer_text = ""
    buffer_start = 0.0
    buffer_duration = 0.0

    for seg in cleaned:
        word_count = len(seg["text"].split())

        if word_count < 3 and buffer_text == "":
            # Start buffering a short fragment
            buffer_text = seg["text"]
            buffer_start = seg["start"]
            buffer_duration = seg["duration"]
        elif buffer_text:
            # Merge buffer with current segment
            merged_text = f"{buffer_text} {seg['text']}"
            merged.append({
                "start": buffer_start,
                "duration": buffer_duration + seg["duration"],
                "text": merged_text.strip(),
            })
            buffer_text = ""
            buffer_duration = 0.0
        else:
            merged.append(seg)

    # Don't lose any remaining buffer
    if buffer_text:
        merged.append({
            "start": buffer_start,
            "duration": buffer_duration,
            "text": buffer_text.strip(),
        })

    # Step 5: Remove duplicate consecutive segments
    deduped = []
    for seg in merged:
        if deduped and seg["text"].lower() == deduped[-1]["text"].lower():
            continue
        deduped.append(seg)

    logger.info(
        "Transcript cleaning complete  [input_segments=%d, output_segments=%d]",
        len(segments), len(deduped),
    )
    return deduped
