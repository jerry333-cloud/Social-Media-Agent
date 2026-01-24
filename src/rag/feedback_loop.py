"""Feedback loop for learning from approved content."""

from typing import Optional
import logging

from .indexer import Indexer
from src.database import get_db, PostCRUD, ChunkCRUD

logger = logging.getLogger(__name__)


class FeedbackLoop:
    """Manages feedback loop for continuous RAG improvement."""
    
    def __init__(self, indexer: Indexer = None):
        """
        Initialize feedback loop.
        
        Args:
            indexer: Indexer instance
        """
        self.indexer = indexer or Indexer()
    
    def add_approved_post(self, post_id: int):
        """
        Add an approved post back to RAG system.
        
        Args:
            post_id: ID of approved post
        """
        try:
            with get_db() as db:
                post = PostCRUD.get(db, post_id)
                if not post or post.status != "approved":
                    logger.warning(f"Post {post_id} not found or not approved")
                    return
                
                # Index the approved post content
                page_id = f"approved_post_{post_id}"
                chunk_count = self.indexer.index_page(
                    page_id=page_id,
                    content=post.content,
                    title="Approved Post",
                    source_type="approved_post",
                    metadata={
                        'post_id': post_id,
                        'published_at': post.published_at.isoformat() if post.published_at else None,
                        'mastodon_url': post.mastodon_url
                    }
                )
                
                logger.info(f"Added approved post {post_id} to RAG: {chunk_count} chunks")
        
        except Exception as e:
            logger.error(f"Failed to add approved post {post_id}: {e}", exc_info=True)
    
    def add_approved_reply(self, post_id: int, parent_post_id: Optional[int] = None):
        """
        Add an approved reply back to RAG system.
        
        Args:
            post_id: ID of approved reply post
            parent_post_id: ID of parent post being replied to
        """
        try:
            with get_db() as db:
                post = PostCRUD.get(db, post_id)
                if not post or post.status != "approved" or not post.is_reply:
                    logger.warning(f"Reply {post_id} not found or not approved")
                    return
                
                # Get parent post context if available
                parent_content = ""
                if parent_post_id:
                    parent = PostCRUD.get(db, parent_post_id)
                    if parent:
                        parent_content = parent.content
                
                # Combine parent + reply for context
                full_content = f"{parent_content}\n\nReply: {post.content}"
                
                # Index the approved reply
                page_id = f"approved_reply_{post_id}"
                chunk_count = self.indexer.index_page(
                    page_id=page_id,
                    content=full_content,
                    title="Approved Reply",
                    source_type="approved_reply",
                    metadata={
                        'post_id': post_id,
                        'parent_post_id': parent_post_id,
                        'published_at': post.published_at.isoformat() if post.published_at else None
                    }
                )
                
                logger.info(f"Added approved reply {post_id} to RAG: {chunk_count} chunks")
        
        except Exception as e:
            logger.error(f"Failed to add approved reply {post_id}: {e}", exc_info=True)
    
    def process_approved_content(self):
        """Process all approved posts/replies that haven't been indexed yet."""
        try:
            with get_db() as db:
                # Get all approved posts
                approved_posts = PostCRUD.get_all(db, status="approved")
                
                indexed_count = 0
                for post in approved_posts:
                    # Check if already indexed
                    page_id = f"approved_post_{post.id}" if not post.is_reply else f"approved_reply_{post.id}"
                    existing = ChunkCRUD.get_by_page(db, page_id)
                    
                    if not existing:
                        if post.is_reply:
                            self.add_approved_reply(post.id, post.parent_post_id)
                        else:
                            self.add_approved_post(post.id)
                        indexed_count += 1
                
                logger.info(f"Processed {indexed_count} new approved posts/replies")
                return indexed_count
        
        except Exception as e:
            logger.error(f"Failed to process approved content: {e}", exc_info=True)
            return 0
