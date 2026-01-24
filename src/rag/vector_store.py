"""Vector database management using sqlite-vec."""

import os
import sqlite3
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Vector dimension for MiniLM-L6-v2
VECTOR_DIM = 384


class VectorStore:
    """Manages vector storage using sqlite-vec extension."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize vector store.
        
        Args:
            db_path: Path to SQLite database (defaults to DATABASE_URL)
        """
        if db_path is None:
            from src.database import DATABASE_URL
            # Extract path from sqlite:///./path
            if DATABASE_URL.startswith("sqlite:///"):
                db_path = DATABASE_URL.replace("sqlite:///", "")
            else:
                db_path = "./social_media_agent.db"
        
        self.db_path = db_path
        self.conn = None
        self._initialize()
    
    def _initialize(self):
        """Initialize sqlite-vec extension and create vector table."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.enable_load_extension(True)
            
            # Try to load sqlite-vec extension
            try:
                # On Windows, try common locations
                import platform
                if platform.system() == "Windows":
                    # Try loading from package
                    import sqlite_vec
                    # sqlite-vec should auto-load, but try explicit load
                    try:
                        self.conn.load_extension("sqlite_vec")
                    except:
                        # May already be loaded or auto-loaded
                        pass
                else:
                    # Linux/Mac - try system library
                    self.conn.load_extension("sqlite_vec")
            except Exception as e:
                logger.warning(f"Could not load sqlite-vec extension: {e}")
                logger.warning("Vector search may not work. Ensure sqlite-vec is installed.")
            
            # Create vector table if it doesn't exist
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS vectors (
                    chunk_id INTEGER PRIMARY KEY,
                    embedding BLOB NOT NULL
                )
            """)
            
            # Create vector index using sqlite-vec
            try:
                self.conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS vec_vectors USING vec0(
                        embedding float[384]
                    )
                """)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not create vec_vectors table: {e}")
            
            self.conn.commit()
            logger.info("Vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def insert_vectors(self, chunk_ids: List[int], embeddings: List[List[float]]):
        """
        Insert vectors for chunks.
        
        Args:
            chunk_ids: List of chunk IDs
            embeddings: List of embedding vectors (384 dimensions each)
        """
        if len(chunk_ids) != len(embeddings):
            raise ValueError("chunk_ids and embeddings must have same length")
        
        try:
            # Insert into vectors table
            for chunk_id, embedding in zip(chunk_ids, embeddings):
                if len(embedding) != VECTOR_DIM:
                    raise ValueError(f"Embedding must be {VECTOR_DIM} dimensions, got {len(embedding)}")
                
                # Convert to bytes for storage
                import struct
                embedding_bytes = struct.pack(f'{VECTOR_DIM}f', *embedding)
                
                self.conn.execute("""
                    INSERT OR REPLACE INTO vectors (chunk_id, embedding)
                    VALUES (?, ?)
                """, (chunk_id, embedding_bytes))
            
            # Insert into vec_vectors for similarity search
            for chunk_id, embedding in zip(chunk_ids, embeddings):
                try:
                    # Convert to format sqlite-vec expects
                    embedding_str = ','.join(map(str, embedding))
                    self.conn.execute("""
                        INSERT OR REPLACE INTO vec_vectors (rowid, embedding)
                        VALUES (?, ?)
                    """, (chunk_id, f'[{embedding_str}]'))
                except Exception as e:
                    logger.warning(f"Could not insert into vec_vectors: {e}")
                    # Fallback: just store in regular vectors table
            
            self.conn.commit()
            logger.info(f"Inserted {len(chunk_ids)} vectors")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to insert vectors: {e}")
            raise
    
    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 50,
        threshold: float = 0.0
    ) -> List[Tuple[int, float]]:
        """
        Search for similar vectors using cosine similarity.
        
        Args:
            query_embedding: Query vector (384 dimensions)
            top_k: Number of results to return
            threshold: Minimum similarity score
            
        Returns:
            List of (chunk_id, similarity_score) tuples, sorted by score descending
        """
        if len(query_embedding) != VECTOR_DIM:
            raise ValueError(f"Query embedding must be {VECTOR_DIM} dimensions")
        
        try:
            # Try sqlite-vec similarity search first
            try:
                embedding_str = ','.join(map(str, query_embedding))
                results = self.conn.execute("""
                    SELECT rowid, distance
                    FROM vec_vectors
                    WHERE embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """, (f'[{embedding_str}]', top_k)).fetchall()
                
                # Convert distance to similarity (1 - normalized distance)
                # sqlite-vec returns distance, we want similarity
                similar_results = []
                for chunk_id, distance in results:
                    # Normalize distance to [0, 1] and convert to similarity
                    similarity = max(0.0, 1.0 - (distance / 2.0))  # Approximate conversion
                    if similarity >= threshold:
                        similar_results.append((chunk_id, similarity))
                
                return similar_results
                
            except Exception as e:
                logger.warning(f"sqlite-vec search failed, using fallback: {e}")
                # Fallback: brute force cosine similarity
                return self._brute_force_search(query_embedding, top_k, threshold)
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _brute_force_search(
        self,
        query_embedding: List[float],
        top_k: int,
        threshold: float
    ) -> List[Tuple[int, float]]:
        """Fallback brute force cosine similarity search."""
        import math
        
        # Get all vectors
        rows = self.conn.execute("""
            SELECT chunk_id, embedding FROM vectors
        """).fetchall()
        
        # Calculate cosine similarity for each
        similarities = []
        query_norm = math.sqrt(sum(x * x for x in query_embedding))
        
        for chunk_id, embedding_bytes in rows:
            # Unpack embedding
            import struct
            embedding = list(struct.unpack(f'{VECTOR_DIM}f', embedding_bytes))
            
            # Calculate cosine similarity
            dot_product = sum(a * b for a, b in zip(query_embedding, embedding))
            embedding_norm = math.sqrt(sum(x * x for x in embedding))
            
            if embedding_norm > 0:
                similarity = dot_product / (query_norm * embedding_norm)
                if similarity >= threshold:
                    similarities.append((chunk_id, similarity))
        
        # Sort by similarity descending and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def delete_vectors(self, chunk_ids: List[int]):
        """Delete vectors for given chunk IDs."""
        try:
            placeholders = ','.join('?' * len(chunk_ids))
            self.conn.execute(f"""
                DELETE FROM vectors WHERE chunk_id IN ({placeholders})
            """, chunk_ids)
            
            # Also delete from vec_vectors
            try:
                self.conn.execute(f"""
                    DELETE FROM vec_vectors WHERE rowid IN ({placeholders})
                """, chunk_ids)
            except:
                pass
            
            self.conn.commit()
            logger.info(f"Deleted {len(chunk_ids)} vectors")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to delete vectors: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
