"""Embedding generation using SentenceTransformers."""

import numpy as np
import logging
from sentence_transformers import SentenceTransformer
from app.config import get_settings

logger = logging.getLogger(__name__)


class Embedder:
    """
    Singleton wrapper around SentenceTransformer for embedding generation.
    
    The model is loaded once and reused across all requests.
    """

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        """Load the SentenceTransformer model if not already loaded."""
        if self._model is None:
            settings = get_settings()
            logger.info("Loading embedding model  [model=%s]", settings.embedding_model)
            self._model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded successfully  [dimension=%d]", self.dimension)

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        self._load_model()
        return self._model.get_embedding_dimension()

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Encode a list of texts into embeddings.
        
        Args:
            texts: List of text strings to embed
            batch_size: Batch size for encoding
            
        Returns:
            numpy array of shape (len(texts), dimension)
        """
        self._load_model()

        if not texts:
            return np.array([]).reshape(0, self.dimension)

        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,  # Normalize for cosine similarity
        )

        return np.array(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Encode a single query into an embedding.
        
        Args:
            query: Query text string
            
        Returns:
            numpy array of shape (1, dimension)
        """
        self._load_model()

        embedding = self._model.encode(
            [query],
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        return np.array(embedding, dtype=np.float32)


# Module-level singleton
_embedder = None


def get_embedder() -> Embedder:
    """Get the global Embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
