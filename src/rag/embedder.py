"""Embedding service using fastembed with MiniLM-L6-v2 model."""

import os
from typing import List, Optional
from fastembed import TextEmbedding
import logging

logger = logging.getLogger(__name__)

# Model name for MiniLM-L6-v2
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder:
    """Manages text embeddings using fastembed."""
    
    _instance: Optional['Embedder'] = None
    _model: Optional[TextEmbedding] = None
    
    def __init__(self):
        """Initialize embedder with MiniLM-L6-v2 model."""
        if Embedder._model is None:
            logger.info(f"Loading embedding model: {MODEL_NAME}")
            try:
                Embedder._model = TextEmbedding(model_name=MODEL_NAME)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
    
    @classmethod
    def get_instance(cls) -> 'Embedder':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (384 dimensions each)
        """
        if not texts:
            return []
        
        try:
            # Use fastembed to generate embeddings
            embeddings = list(Embedder._model.embed(texts))
            
            # Convert to list of lists
            result = [list(emb) for emb in embeddings]
            
            logger.debug(f"Generated {len(result)} embeddings")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector (384 dimensions)
        """
        return self.embed([text])[0]
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return 384
