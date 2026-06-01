"""FAISS index management for vector storage and retrieval."""

import numpy as np
import faiss
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata associated with a FAISS vector."""
    faiss_id: int
    video_id: str
    chunk_index: int
    text: str
    start_time: float
    end_time: float


class FAISSManager:
    """
    Manages FAISS index for semantic search.
    
    Uses IndexFlatIP (inner product) on normalized vectors for cosine similarity.
    Metadata is stored in-memory for fast lookup.
    """

    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata: dict[int, ChunkMetadata] = {}
        self._next_id = 0
        logger.info("FAISS index initialized  [type=IndexFlatIP, dimension=%d]", dimension)

    @property
    def total_vectors(self) -> int:
        """Total number of vectors in the index."""
        return self.index.ntotal

    def add_embeddings(
        self,
        embeddings: np.ndarray,
        metadata_list: list[dict],
    ) -> list[int]:
        """
        Add embeddings and their metadata to the index.
        
        Args:
            embeddings: numpy array of shape (n, dimension)
            metadata_list: list of dicts with keys: video_id, chunk_index, text, start_time, end_time
            
        Returns:
            List of assigned FAISS IDs
        """
        if len(embeddings) == 0:
            return []

        assert embeddings.shape[1] == self.dimension, \
            f"Embedding dimension mismatch: expected {self.dimension}, got {embeddings.shape[1]}"
        assert len(embeddings) == len(metadata_list), \
            f"Embeddings and metadata count mismatch: {len(embeddings)} vs {len(metadata_list)}"

        # Ensure float32
        embeddings = np.array(embeddings, dtype=np.float32)

        # Track IDs
        ids = []
        for i, meta in enumerate(metadata_list):
            fid = self._next_id
            self.metadata[fid] = ChunkMetadata(
                faiss_id=fid,
                video_id=meta["video_id"],
                chunk_index=meta["chunk_index"],
                text=meta["text"],
                start_time=meta["start_time"],
                end_time=meta["end_time"],
            )
            ids.append(fid)
            self._next_id += 1

        self.index.add(embeddings)
        logger.info("Added %d vectors to FAISS index  [total=%d]", len(embeddings), self.total_vectors)
        return ids

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        video_id: str = None,
    ) -> list[tuple[ChunkMetadata, float]]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: numpy array of shape (1, dimension)
            top_k: Number of results to return
            video_id: Optional filter to search within a specific video
            
        Returns:
            List of (ChunkMetadata, score) tuples, sorted by score descending
        """
        if self.total_vectors == 0:
            return []

        # Search more than top_k if filtering by video_id
        search_k = top_k * 10 if video_id else top_k
        search_k = min(search_k, self.total_vectors)

        query_embedding = np.array(query_embedding, dtype=np.float32)
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        distances, indices = self.index.search(query_embedding, search_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            meta = self.metadata.get(idx)
            if meta is None:
                continue

            # Filter by video_id if specified
            if video_id and meta.video_id != video_id:
                continue

            results.append((meta, float(dist)))

            if len(results) >= top_k:
                break

        return results

    def delete_video(self, video_id: str) -> int:
        """
        Remove all vectors for a specific video.
        
        Note: FAISS IndexFlat doesn't support deletion, so we rebuild the index
        without the deleted vectors.
        """
        # Find IDs to keep
        keep_ids = [fid for fid, meta in self.metadata.items() if meta.video_id != video_id]
        deleted_count = len(self.metadata) - len(keep_ids)

        if deleted_count == 0:
            return 0

        # Rebuild index
        new_index = faiss.IndexFlatIP(self.dimension)
        new_metadata = {}
        new_id = 0

        # We need to reconstruct vectors from the old index
        for old_id in keep_ids:
            vec = faiss.rev_swig_ptr(
                self.index.get_xb().__long__() + old_id * self.dimension * 4,
                self.dimension
            ).copy().reshape(1, -1)
            new_index.add(vec)
            old_meta = self.metadata[old_id]
            new_metadata[new_id] = ChunkMetadata(
                faiss_id=new_id,
                video_id=old_meta.video_id,
                chunk_index=old_meta.chunk_index,
                text=old_meta.text,
                start_time=old_meta.start_time,
                end_time=old_meta.end_time,
            )
            new_id += 1

        self.index = new_index
        self.metadata = new_metadata
        self._next_id = new_id

        logger.info(
            "Removed vectors for video from FAISS index  [video_id=%s, removed=%d, remaining=%d]",
            video_id, deleted_count, self.total_vectors,
        )
        return deleted_count

    def rebuild_from_data(
        self,
        embeddings: np.ndarray,
        metadata_list: list[dict],
    ):
        """
        Rebuild the entire index from stored data (used on startup from PostgreSQL).
        """
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = {}
        self._next_id = 0

        if len(embeddings) > 0:
            self.add_embeddings(embeddings, metadata_list)
            logger.info("FAISS index rebuilt from persisted data  [vectors=%d]", self.total_vectors)


# Module-level singleton
_faiss_manager = None


def get_faiss_manager(dimension: int = None) -> FAISSManager:
    """Get or create the global FAISSManager instance."""
    global _faiss_manager
    if _faiss_manager is None:
        if dimension is None:
            raise ValueError("Dimension required for first initialization")
        _faiss_manager = FAISSManager(dimension)
    return _faiss_manager


def reset_faiss_manager():
    """Reset the global FAISSManager (used in tests)."""
    global _faiss_manager
    _faiss_manager = None
