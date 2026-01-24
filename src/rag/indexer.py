"""Indexing service for processing and storing content chunks."""

import os
from typing import List, Dict, Optional
import logging

from .chunker import Chunker
from .embedder import Embedder
from .vector_store import VectorStore
from .bm25_search import BM25Search
from src.database import get_db, ChunkCRUD

logger = logging.getLogger(__name__)


class Indexer:
    """Handles content indexing for RAG."""
    
    def __init__(
        self,
        chunker: Chunker = None,
        embedder: Embedder = None,
        vector_store: VectorStore = None,
        bm25_search: BM25Search = None
    ):
        """
        Initialize indexer.
        
        Args:
            chunker: Chunker instance
            embedder: Embedder instance
            vector_store: VectorStore instance
            bm25_search: BM25Search instance
        """
        self.chunker = chunker or Chunker()
        self.embedder = embedder or Embedder.get_instance()
        self.vector_store = vector_store or VectorStore()
        self.bm25_search = bm25_search or BM25Search()
    
    def index_page(
        self,
        page_id: str,
        content: str,
        title: str = "",
        source_type: str = "notion",
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Index a page's content.
        
        Args:
            page_id: Page identifier
            content: Page content text
            title: Page title (optional)
            source_type: Type of source (notion, approved_post, etc.)
            
        Returns:
            Number of chunks created
        """
        logger.info(f"Indexing page: {page_id} (source: {source_type})")
        
        # Delete existing chunks for this page
        with get_db() as db:
            deleted_count = ChunkCRUD.delete_by_page(db, page_id)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} existing chunks for page {page_id}")
        
        # Delete from vector store and FTS5 (before deleting from DB)
        old_chunks = []
        with get_db() as db:
            old_chunks = ChunkCRUD.get_by_page(db, page_id)
            old_chunk_ids = [c.id for c in old_chunks]
        
        if old_chunk_ids:
            try:
                self.vector_store.delete_vectors(old_chunk_ids)
            except Exception as e:
                logger.warning(f"Could not delete vectors: {e}")
            
            for chunk_id in old_chunk_ids:
                try:
                    self.bm25_search.delete_chunk(chunk_id)
                except Exception as e:
                    logger.warning(f"Could not delete from FTS5: {e}")
        
        # Chunk the content
        full_metadata = {
            'title': title,
            'source_type': source_type,
            **(metadata or {})
        }
        
        chunks = self.chunker.chunk_text(
            text=content,
            page_id=page_id,
            metadata=full_metadata
        )
        
        if not chunks:
            logger.warning(f"No chunks created for page {page_id}")
            return 0
        
        # Store chunks in database
        chunk_ids = []
        with get_db() as db:
            for chunk_data in chunks:
                chunk = ChunkCRUD.create(
                    db=db,
                    page_id=chunk_data['page_id'],
                    chunk_index=chunk_data['chunk_index'],
                    content=chunk_data['content'],
                    token_count=chunk_data['token_count'],
                    source_type=source_type
                )
                chunk_ids.append(chunk.id)
        
        # Generate embeddings
        chunk_contents = [c['content'] for c in chunks]
        logger.info(f"Generating embeddings for {len(chunk_contents)} chunks...")
        
        try:
            embeddings = self.embedder.embed(chunk_contents)
            
            # Store in vector database
            self.vector_store.insert_vectors(chunk_ids, embeddings)
            logger.info(f"Stored {len(chunk_ids)} vectors")
            
        except Exception as e:
            logger.error(f"Failed to generate/store embeddings: {e}")
            # Continue without vectors - BM25 will still work
        
        # Index in FTS5 for BM25
        for chunk_id, chunk_data in zip(chunk_ids, chunks):
            try:
                self.bm25_search.index_chunk(chunk_id, chunk_data['content'])
            except Exception as e:
                logger.warning(f"Failed to index chunk {chunk_id} in FTS5: {e}")
        
        logger.info(f"Successfully indexed page {page_id}: {len(chunk_ids)} chunks")
        return len(chunk_ids)
    
    def index_batch(
        self,
        pages: List[Dict]
    ) -> Dict[str, int]:
        """
        Index multiple pages in batch.
        
        Args:
            pages: List of page dicts with 'page_id' or 'id', 'content', 'title', etc.
            
        Returns:
            Dictionary mapping page_id to number of chunks created
        """
        results = {}
        
        for page in pages:
            # Handle both 'page_id' and 'id' keys
            page_id = page.get('page_id') or page.get('id')
            content = page.get('content', '')
            title = page.get('title', '')
            source_type = page.get('source_type', 'notion')
            metadata = page.get('metadata')
            
            if not page_id:
                logger.error("Page missing ID field")
                continue
            
            try:
                chunk_count = self.index_page(
                    page_id=page_id,
                    content=content,
                    title=title,
                    source_type=source_type,
                    metadata=metadata
                )
                results[page_id] = chunk_count
            except Exception as e:
                logger.error(f"Failed to index page {page_id}: {e}")
                results[page_id] = 0
        
        total_chunks = sum(results.values())
        logger.info(f"Batch indexing complete: {total_chunks} total chunks across {len(pages)} pages")
        return results
    
    def reindex_all(self) -> int:
        """
        Reindex all pages in database.
        
        Returns:
            Total number of chunks created
        """
        logger.info("Starting full reindex...")
        
        from src.database import Chunk
        # Get all unique page IDs
        with get_db() as db:
            chunks = db.query(Chunk).all()
            page_ids = set(c.page_id for c in chunks)
        
        # For each page, fetch content and reindex
        # This would need to be implemented based on your content source
        # For now, just return count of existing chunks
        return len(page_ids)
