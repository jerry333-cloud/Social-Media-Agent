"""Hybrid retrieval engine combining BM25 and vector search."""

import os
from typing import List, Dict, Tuple, Optional
import logging

from .bm25_search import BM25Search
from .vector_search import VectorSearch
from .query_parser import QueryParser
from src.database import get_db, ChunkCRUD

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "10"))
DEFAULT_SCORE_THRESHOLD = float(os.getenv("RAG_SCORE_THRESHOLD", "0.5"))
DEFAULT_BM25_WEIGHT = float(os.getenv("RAG_BM25_WEIGHT", "0.5"))
DEFAULT_VECTOR_WEIGHT = float(os.getenv("RAG_VECTOR_WEIGHT", "0.5"))
MIN_CHUNKS_FOR_RAG = 1  # Minimum chunks needed to use RAG (lowered for small datasets)


class HybridRetriever:
    """Hybrid retrieval engine with BM25 + vector search fusion."""
    
    def __init__(
        self,
        bm25_search: BM25Search = None,
        vector_search: VectorSearch = None,
        query_parser: QueryParser = None
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            bm25_search: BM25Search instance
            vector_search: VectorSearch instance
            query_parser: QueryParser instance
        """
        self.bm25_search = bm25_search or BM25Search()
        self.vector_search = vector_search or VectorSearch()
        self.query_parser = query_parser or QueryParser()
        
        self.bm25_weight = DEFAULT_BM25_WEIGHT
        self.vector_weight = DEFAULT_VECTOR_WEIGHT
        self.score_threshold = DEFAULT_SCORE_THRESHOLD
    
    def retrieve(
        self,
        query: str,
        top_k: int = None,
        score_threshold: float = None
    ) -> Tuple[List[Dict], bool]:
        """
        Retrieve relevant chunks using hybrid search.
        
        Args:
            query: Query string
            top_k: Number of chunks to return (default: 10)
            score_threshold: Minimum score threshold (default: 0.5)
            
        Returns:
            Tuple of (list of chunk dicts with metadata, retrieval_success)
            retrieval_success is False if < MIN_CHUNKS_FOR_RAG chunks found
        """
        top_k = top_k or DEFAULT_TOP_K
        score_threshold = score_threshold or self.score_threshold
        
        # Stage 1: Query Parsing
        if not self.query_parser.validate(query):
            logger.warning(f"Invalid query: {query}")
            return [], False
        
        cleaned_query = self.query_parser.parse(query)
        expanded_query = self.query_parser.expand_query(cleaned_query)
        
        logger.debug(f"Retrieving for query: {cleaned_query}")
        
        # Stage 2: Parallel Search
        # Get top 50 from each method
        bm25_results = self.bm25_search.search(cleaned_query, top_k=50)
        vector_results = self.vector_search.search(cleaned_query, top_k=50)
        
        logger.debug(f"BM25: {len(bm25_results)} results, Vector: {len(vector_results)} results")
        
        # Stage 3: Score Fusion
        # Combine results with weighted scores
        chunk_scores = {}  # chunk_id -> (bm25_score, vector_score, final_score)
        
        # Add BM25 results
        for chunk_id, bm25_score in bm25_results:
            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = {'bm25': 0.0, 'vector': 0.0}
            chunk_scores[chunk_id]['bm25'] = bm25_score
        
        # Add vector results
        for chunk_id, vector_score in vector_results:
            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = {'bm25': 0.0, 'vector': 0.0}
            chunk_scores[chunk_id]['vector'] = vector_score
        
        # Calculate final scores
        final_scores = []
        for chunk_id, scores in chunk_scores.items():
            final_score = (
                self.bm25_weight * scores['bm25'] +
                self.vector_weight * scores['vector']
            )
            final_scores.append({
                'chunk_id': chunk_id,
                'bm25_score': scores['bm25'],
                'vector_score': scores['vector'],
                'final_score': final_score
            })
        
        # Stage 4: Reranking & Filtering
        # Sort by final score
        final_scores.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Apply threshold
        filtered_scores = [
            s for s in final_scores
            if s['final_score'] >= score_threshold
        ]
        
        # Take top_k
        top_chunks = filtered_scores[:top_k]
        
        logger.debug(f"After filtering: {len(top_chunks)} chunks (threshold: {score_threshold})")
        
        # Retrieval failure protection
        if len(top_chunks) < MIN_CHUNKS_FOR_RAG:
            logger.warning(
                f"Only {len(top_chunks)} chunks found (minimum: {MIN_CHUNKS_FOR_RAG}). "
                "Retrieval may be insufficient for RAG."
            )
            # Still return what we have, but mark as potentially insufficient
            retrieval_success = False
        else:
            retrieval_success = True
        
        # Stage 5: Fetch chunk content
        chunk_ids = [c['chunk_id'] for c in top_chunks]
        
        # Create result list with metadata
        results = []
        score_map = {c['chunk_id']: c for c in top_chunks}
        
        with get_db() as db:
            chunks = ChunkCRUD.get_by_ids(db, chunk_ids)
            
            # Extract data while session is still open
            for chunk in chunks:
                scores = score_map.get(chunk.id, {})
                results.append({
                    'id': chunk.id,
                    'content': chunk.content,
                    'page_id': chunk.page_id,
                    'chunk_index': chunk.chunk_index,
                    'token_count': chunk.token_count,
                    'source_type': chunk.source_type,
                    'bm25_score': scores.get('bm25_score', 0.0),
                    'vector_score': scores.get('vector_score', 0.0),
                    'final_score': scores.get('final_score', 0.0)
                })
        
        # Sort by final_score (in case chunk order differs)
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        logger.info(f"Retrieved {len(results)} chunks for query")
        return results, retrieval_success
    
    def log_retrieval(
        self,
        query: str,
        chunks: List[Dict],
        post_id: Optional[int] = None,
        retrieval_type: str = "hybrid"
    ):
        """
        Log retrieval operation for quality tracking.
        
        Args:
            query: Query string
            chunks: Retrieved chunks
            post_id: Associated post ID if any
            retrieval_type: Type of retrieval used
        """
        if not chunks:
            return
        
        scores = [c['final_score'] for c in chunks]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0
        
        chunk_ids = [c['id'] for c in chunks]
        
        from src.database import get_db, RetrievalLogCRUD
        with get_db() as db:
            RetrievalLogCRUD.create(
                db=db,
                query=query,
                chunks_used=chunk_ids,
                post_id=post_id,
                avg_score=avg_score,
                min_score=min_score,
                max_score=max_score,
                retrieval_type=retrieval_type
            )
