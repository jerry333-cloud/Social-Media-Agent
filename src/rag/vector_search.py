"""Vector similarity search."""

from typing import List, Tuple
from .vector_store import VectorStore
from .embedder import Embedder
import logging

logger = logging.getLogger(__name__)


class VectorSearch:
    """Handles vector similarity search."""
    
    def __init__(self, vector_store: VectorStore = None, embedder: Embedder = None):
        """
        Initialize vector search.
        
        Args:
            vector_store: VectorStore instance
            embedder: Embedder instance
        """
        self.vector_store = vector_store or VectorStore()
        self.embedder = embedder or Embedder.get_instance()
    
    def search(
        self,
        query: str,
        top_k: int = 50,
        threshold: float = 0.0
    ) -> List[Tuple[int, float]]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query: Query text
            top_k: Number of results to return
            threshold: Minimum similarity score
            
        Returns:
            List of (chunk_id, similarity_score) tuples, sorted by score descending
        """
        try:
            # Embed query
            query_embedding = self.embedder.embed_single(query)
            
            # Search in vector store
            results = self.vector_store.search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                threshold=threshold
            )
            
            logger.debug(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
