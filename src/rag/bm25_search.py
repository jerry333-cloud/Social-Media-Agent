"""BM25 text search using SQLite FTS5."""

import os
import sqlite3
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class BM25Search:
    """BM25 search using SQLite FTS5 virtual tables."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize BM25 search.
        
        Args:
            db_path: Path to SQLite database
        """
        if db_path is None:
            from src.database import DATABASE_URL
            if DATABASE_URL.startswith("sqlite:///"):
                db_path = DATABASE_URL.replace("sqlite:///", "")
            else:
                db_path = "./social_media_agent.db"
        
        self.db_path = db_path
        self.conn = None
        self._initialize()
    
    def _initialize(self):
        """Initialize FTS5 virtual table for BM25 search."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            
            # Create standalone FTS5 virtual table (not using external content)
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                    chunk_id UNINDEXED,
                    content
                )
            """)
            
            self.conn.commit()
            logger.info("BM25 search initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize BM25 search: {e}")
            raise
    
    def index_chunk(self, chunk_id: int, content: str):
        """
        Index a chunk for BM25 search.
        
        Args:
            chunk_id: Chunk ID
            content: Chunk content
        """
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO fts_chunks(chunk_id, content)
                VALUES (?, ?)
            """, (chunk_id, content))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to index chunk {chunk_id}: {e}")
            raise
    
    def search(
        self,
        query: str,
        top_k: int = 50
    ) -> List[Tuple[int, float]]:
        """
        Search using BM25 ranking.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (chunk_id, bm25_score) tuples, sorted by score descending
        """
        if not query.strip():
            return []
        
        # Clean query and prepare for FTS5
        # Remove special FTS5 operators and quote each word
        clean_query = query.replace('"', '').replace("'", '').replace(':', ' ')
        clean_query = clean_query.replace('(', ' ').replace(')', ' ')
        clean_query = clean_query.replace('*', ' ').replace('-', ' ')
        
        # Split into words and wrap each in quotes for phrase matching
        # This prevents FTS5 from interpreting words as column names
        words = [w.strip() for w in clean_query.split() if w.strip()]
        
        if not words:
            return []
        
        # Create FTS5 query with OR between quoted words
        # Using quotes makes each word a phrase search, avoiding column name issues
        fts_query = ' OR '.join(f'"{word}"' for word in words)
        
        try:
            # Use FTS5 bm25() function for ranking
            # bm25() returns negative values (lower is better), so we negate
            results = self.conn.execute("""
                SELECT CAST(chunk_id AS INTEGER), -bm25(fts_chunks) as score
                FROM fts_chunks
                WHERE fts_chunks MATCH ?
                ORDER BY bm25(fts_chunks)
                LIMIT ?
            """, (fts_query, top_k)).fetchall()
            
            logger.debug(f"BM25 raw results: {len(results)} matches")
            
            # Normalize scores to [0, 1] range
            if results:
                scores = [score for _, score in results]
                min_score = min(scores)
                max_score = max(scores)
                score_range = max_score - min_score if max_score != min_score else 1.0
                
                normalized = [
                    (int(chunk_id), (score - min_score) / score_range)
                    for chunk_id, score in results
                ]
                logger.debug(f"BM25 normalized: {normalized}")
                return normalized
            
            return []
            
        except Exception as e:
            logger.error(f"BM25 search failed: {e}", exc_info=True)
            return []
    
    def delete_chunk(self, chunk_id: int):
        """Delete chunk from FTS5 index."""
        try:
            self.conn.execute("""
                DELETE FROM fts_chunks WHERE chunk_id = ?
            """, (chunk_id,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to delete chunk {chunk_id} from FTS5: {e}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
