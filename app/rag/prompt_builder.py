"""Build grounded prompts for the LLM — strictly based on video transcript content."""

from app.vectorstore.retriever import RetrievedChunk


SYSTEM_PROMPT = """You are TubeMind, an AI assistant that helps users understand YouTube video content by analyzing their transcripts.

YOUR ROLE:
You answer user questions **strictly and exclusively** based on the video transcript excerpts provided below. You are a transcript analysis tool — not a general knowledge assistant.

STRICT RULES — YOU MUST FOLLOW ALL OF THESE:
1. **ONLY use information from the transcript excerpts provided.** Every claim, fact, and detail in your answer MUST come directly from the transcript text given to you. Do NOT add, infer, assume, or fabricate any information beyond what is explicitly stated in the transcript.
2. **Do NOT supplement with your own knowledge.** You must never fill gaps with outside information. If the transcript doesn't say it, you don't say it.
3. **If the transcript does not contain relevant information for the question,** clearly and honestly state: "Based on the video transcript provided, this topic is not covered." Do NOT attempt to answer from your own knowledge.
4. **If the transcript only partially covers the question,** answer ONLY the parts that the transcript covers. Clearly state which parts of the question are not addressed in the transcript.
5. **Cite timestamps** using [MM:SS] format whenever referencing specific points from the transcript. Every factual statement should have a timestamp citation.
6. **Use rich markdown formatting** — headers (##), bullet points, bold text, numbered lists, and code blocks where appropriate for readability.
7. **Be thorough with the transcript content.** Extract and present all relevant information from the provided excerpts. Do not skip or summarize away important details that are in the transcript.
8. **Maintain a clear, helpful tone.** Present the transcript information in an organized and easy-to-understand manner.

WHAT YOU MUST NEVER DO:
- Never make up information that isn't in the transcript
- Never say "based on my knowledge" or "generally speaking" — you only know what the transcript says
- Never assume what the speaker "probably meant" or "likely intended" beyond what they explicitly said
- Never add examples, analogies, or explanations that aren't from the transcript"""


# Pre-built response for when no transcript context is available.
# This avoids sending the LLM a prompt with no context, which would
# force it to either hallucinate or return an empty answer.
NO_CONTEXT_RESPONSE = (
    "I couldn't find any relevant information about this topic in the video transcript. "
    "This could mean:\n\n"
    "- The video doesn't cover this specific topic\n"
    "- The question may need to be rephrased to match how the topic is discussed in the video\n"
    "- The video may not have been ingested yet\n\n"
    "Try rephrasing your question, or ask about a topic that was discussed in the video."
)

# Maximum number of conversation turns (user+assistant pairs) to include
# in the prompt. Keeps token usage manageable while preserving enough
# context for natural follow-up questions.
MAX_HISTORY_TURNS = 10


def _format_chat_history(chat_history: list[dict]) -> str:
    """
    Format conversation history into a readable block for the prompt.

    Args:
        chat_history: List of {"role": "user"|"assistant", "content": "..."} dicts

    Returns:
        Formatted conversation history string, or empty string if no history
    """
    if not chat_history:
        return ""

    # Keep only the last MAX_HISTORY_TURNS exchanges to avoid token overflow
    trimmed = chat_history[-(MAX_HISTORY_TURNS * 2):]

    lines = []
    for msg in trimmed:
        role = msg.get("role", "").capitalize()
        content = msg.get("content", "").strip()
        if role and content:
            lines.append(f"{role}: {content}")

    if not lines:
        return ""

    return (
        "CONVERSATION HISTORY (use this to understand follow-up questions):\n"
        + "\n\n".join(lines)
        + "\n\n---\n"
    )


def build_prompt(
    query: str,
    retrieved_chunks: list[RetrievedChunk],
    video_titles: dict[str, str] = None,
    chat_history: list[dict] = None,
) -> str:
    """
    Build a strictly grounded prompt with retrieved transcript context for the LLM.

    If no chunks are retrieved, returns None — the caller should use
    NO_CONTEXT_RESPONSE directly instead of asking the LLM.

    Args:
        query: User's question
        retrieved_chunks: Relevant transcript chunks with timestamps
        video_titles: Optional mapping of video_id → title
        chat_history: Optional list of previous messages
                      [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        Complete prompt string, or None if no transcript context is available
    """
    if not retrieved_chunks:
        # Return None to signal that the caller should use the pre-built
        # NO_CONTEXT_RESPONSE instead of invoking the LLM with no context.
        return None

    # Build context block
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        video_label = ""
        if video_titles and chunk.video_id in video_titles:
            video_label = f' — "{video_titles[chunk.video_id]}"'

        context_parts.append(
            f"[Context {i}] [{chunk.start_timestamp} - {chunk.end_timestamp}]{video_label}\n"
            f"{chunk.text}"
        )

    context_block = "\n\n---\n\n".join(context_parts)

    # Build conversation history block
    history_block = _format_chat_history(chat_history)

    prompt = f"""{SYSTEM_PROMPT}

TRANSCRIPT CONTEXT (this is the ONLY information you may use to answer):
{context_block}

---

{history_block}User Question: {query}

Answer the question using ONLY the transcript excerpts above. Cite timestamps with [MM:SS] for every factual statement. If the transcript excerpts above do not contain enough information to fully answer the question, clearly state which parts are not covered in the transcript. Do NOT make up or assume any information."""

    return prompt

