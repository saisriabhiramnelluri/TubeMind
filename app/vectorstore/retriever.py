"""Semantic search retriever combining embedder and FAISS."""

import logging
from dataclasses import dataclass
from app.embeddings.embedder import get_embedder
from app.vectorstore.faiss_manager import get_faiss_manager
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved transcript chunk with relevance score."""
    video_id: str
    chunk_index: int
    text: str
    start_time: float
    end_time: float
    score: float

    @property
    def start_timestamp(self) -> str:
        """Format start_time as MM:SS."""
        minutes = int(self.start_time // 60)
        seconds = int(self.start_time % 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def end_timestamp(self) -> str:
        """Format end_time as MM:SS."""
        minutes = int(self.end_time // 60)
        seconds = int(self.end_time % 60)
        return f"{minutes:02d}:{seconds:02d}"


def retrieve(
    query: str,
    video_id: str = None,
    top_k: int = None,
) -> list[RetrievedChunk]:
    """
    Retrieve relevant transcript chunks for a query.
    
    Args:
        query: User's natural language question
        video_id: Optional filter for a specific video
        top_k: Number of results (defaults to settings.top_k)
        
    Returns:
        List of RetrievedChunk objects sorted by relevance
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.top_k

    embedder = get_embedder()
    faiss_mgr = get_faiss_manager()

    # Embed the query
    query_embedding = embedder.embed_query(query)

    # Search FAISS
    results = faiss_mgr.search(query_embedding, top_k=top_k, video_id=video_id)

    # Convert to RetrievedChunk objects
    retrieved = []
    for meta, score in results:
        retrieved.append(RetrievedChunk(
            video_id=meta.video_id,
            chunk_index=meta.chunk_index,
            text=meta.text,
            start_time=meta.start_time,
            end_time=meta.end_time,
            score=score,
        ))

    logger.info("Semantic search complete  [results=%d, query=%s]", len(retrieved), query[:60])
    return retrieved
