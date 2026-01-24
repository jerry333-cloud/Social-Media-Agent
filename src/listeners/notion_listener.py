"""Notion database polling listener for auto-creating posts."""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from src.notion_client import NotionClientWrapper
from src.rag.indexer import Indexer
from src.database import get_db, ConfigCRUD, PostCRUD

logger = logging.getLogger(__name__)

# Polling interval in minutes
POLL_INTERVAL_MINUTES = int(os.getenv("NOTION_POLL_INTERVAL_MINUTES", "15"))


class NotionListener:
    """Polls Notion database for changes and triggers post creation."""
    
    def __init__(self):
        """Initialize Notion listener."""
        self.notion_client = NotionClientWrapper()
        self.indexer = Indexer()
        self.running = False
        self._last_check_time = None
    
    async def start(self):
        """Start polling loop."""
        self.running = True
        logger.info(f"Starting Notion listener (poll interval: {POLL_INTERVAL_MINUTES} minutes)")
        
        # Load last check time from config
        with get_db() as db:
            last_check_str = ConfigCRUD.get(db, "notion_last_check")
            if last_check_str:
                try:
                    self._last_check_time = datetime.fromisoformat(last_check_str)
                except:
                    self._last_check_time = None
        
        while self.running:
            try:
                await self._check_for_changes()
                await asyncio.sleep(POLL_INTERVAL_MINUTES * 60)
            except Exception as e:
                logger.error(f"Error in Notion listener: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop(self):
        """Stop polling loop."""
        self.running = False
        logger.info("Stopping Notion listener")
    
    async def _check_for_changes(self):
        """Check for new or updated pages in Notion database."""
        logger.info("Checking Notion database for changes...")
        
        try:
            # Fetch all pages from database
            pages = self.notion_client.get_database_pages()
            
            if not pages:
                logger.info("No pages found in database")
                return
            
            # Check each page for changes
            new_or_updated = []
            
            for page in pages:
                page_id = page['id']
                last_edited_time = page.get('last_edited_time')
                
                if last_edited_time:
                    try:
                        # Parse ISO format timestamp
                        edited_time = datetime.fromisoformat(last_edited_time.replace('Z', '+00:00'))
                        if edited_time.tzinfo:
                            edited_time = edited_time.replace(tzinfo=None)
                    except:
                        # Fallback: treat as new if we can't parse
                        edited_time = datetime.utcnow()
                else:
                    edited_time = datetime.utcnow()
                
                # Check if this is new or updated
                is_new = True
                if self._last_check_time:
                    # Check if page was edited after last check
                    is_new = edited_time > self._last_check_time
                
                if is_new:
                    new_or_updated.append(page)
                    logger.info(f"Found {'new' if not self._last_check_time else 'updated'} page: {page.get('title', page_id)}")
            
            # Index new/updated pages
            if new_or_updated:
                logger.info(f"Indexing {len(new_or_updated)} new/updated pages...")
                
                for page in new_or_updated:
                    try:
                        # Index the page content
                        chunk_count = self.indexer.index_page(
                            page_id=page['id'],
                            content=page['content'],
                            title=page.get('title', ''),
                            source_type='notion',
                            metadata={'last_edited_time': page.get('last_edited_time')}
                        )
                        
                        logger.info(f"Indexed page {page['id']}: {chunk_count} chunks")
                        
                        # Create draft post for review
                        with get_db() as db:
                            post = PostCRUD.create(
                                db=db,
                                content=f"New content from Notion: {page.get('title', 'Untitled')}",
                                status="pending_review"
                            )
                            logger.info(f"Created draft post {post.id} for page {page['id']}")
                    
                    except Exception as e:
                        logger.error(f"Failed to index page {page['id']}: {e}", exc_info=True)
            
            # Update last check time
            self._last_check_time = datetime.utcnow()
            with get_db() as db:
                ConfigCRUD.set(db, "notion_last_check", self._last_check_time.isoformat())
            
            logger.info(f"Notion check complete. Found {len(new_or_updated)} new/updated pages")
            
        except Exception as e:
            logger.error(f"Error checking Notion database: {e}", exc_info=True)
            raise
    
    async def manual_trigger(self) -> int:
        """
        Manually trigger a check and return number of pages indexed.
        
        Returns:
            Number of pages indexed
        """
        pages_indexed = 0
        try:
            pages = self.notion_client.get_database_pages()
            
            for page in pages:
                try:
                    chunk_count = self.indexer.index_page(
                        page_id=page['id'],
                        content=page['content'],
                        title=page.get('title', ''),
                        source_type='notion'
                    )
                    if chunk_count > 0:
                        pages_indexed += 1
                except Exception as e:
                    logger.error(f"Failed to index page {page['id']}: {e}")
            
            return pages_indexed
            
        except Exception as e:
            logger.error(f"Manual trigger failed: {e}", exc_info=True)
            raise
