"""RAG management API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging

from src.rag.retriever import HybridRetriever
from src.rag.indexer import Indexer
from src.rag.context_builder import ContextBuilder
from src.notion_client import NotionClientWrapper
from src.database import get_db, ChunkCRUD

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10


class SearchResponse(BaseModel):
    chunks: List[Dict]
    retrieval_success: bool
    query: str


class IndexRequest(BaseModel):
    page_id: str
    content: str
    title: Optional[str] = ""
    source_type: Optional[str] = "notion"


class StatsResponse(BaseModel):
    total_chunks: int
    total_pages: int
    chunks_by_source: Dict[str, int]


@router.post("/search", response_model=SearchResponse)
async def search_rag(request: SearchRequest):
    """Test RAG search."""
    try:
        retriever = HybridRetriever()
        chunks, retrieval_success = retriever.retrieve(
            query=request.query,
            top_k=request.top_k
        )
        
        return SearchResponse(
            chunks=chunks,
            retrieval_success=retrieval_success,
            query=request.query
        )
    except Exception as e:
        logger.error(f"RAG search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
async def index_content(request: IndexRequest):
    """Manually index content."""
    try:
        indexer = Indexer()
        chunk_count = indexer.index_page(
            page_id=request.page_id,
            content=request.content,
            title=request.title or "",
            source_type=request.source_type
        )
        
        return {
            "success": True,
            "page_id": request.page_id,
            "chunks_created": chunk_count
        }
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index-notion")
async def index_notion_database():
    """Reindex all pages from Notion database."""
    try:
        notion_client = NotionClientWrapper()
        pages = notion_client.get_database_pages()
        
        indexer = Indexer()
        results = indexer.index_batch(pages)
        
        return {
            "success": True,
            "pages_indexed": len(results),
            "total_chunks": sum(results.values()),
            "results": results
        }
    except Exception as e:
        logger.error(f"Notion indexing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_rag_stats():
    """Get RAG system statistics."""
    try:
        from src.database import Chunk
        with get_db() as db:
            all_chunks = db.query(Chunk).all()
            
            total_chunks = len(all_chunks)
            page_ids = set(c.page_id for c in all_chunks)
            total_pages = len(page_ids)
            
            # Count by source type
            chunks_by_source = {}
            for chunk in all_chunks:
                source = chunk.source_type or "unknown"
                chunks_by_source[source] = chunks_by_source.get(source, 0) + 1
        
        return StatsResponse(
            total_chunks=total_chunks,
            total_pages=total_pages,
            chunks_by_source=chunks_by_source
        )
    except Exception as e:
        logger.error(f"Failed to get RAG stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
