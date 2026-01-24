"""Manager for all listeners."""

import asyncio
from typing import Dict, Optional
import logging

from .notion_listener import NotionListener
from .mastodon_listener import MastodonListener

logger = logging.getLogger(__name__)


class ListenerManager:
    """Manages all listeners for the social media agent."""
    
    def __init__(self):
        """Initialize listener manager."""
        self.notion_listener: Optional[NotionListener] = None
        self.mastodon_listener: Optional[MastodonListener] = None
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
    
    async def start_all(self):
        """Start all listeners."""
        if self.running:
            logger.warning("Listeners already running")
            return
        
        self.running = True
        logger.info("Starting all listeners...")
        
        # Start Notion listener
        try:
            self.notion_listener = NotionListener()
            task = asyncio.create_task(self.notion_listener.start())
            self.tasks['notion'] = task
            logger.info("Notion listener started")
        except Exception as e:
            logger.error(f"Failed to start Notion listener: {e}", exc_info=True)
        
        # Start Mastodon listener
        try:
            self.mastodon_listener = MastodonListener()
            task = asyncio.create_task(self.mastodon_listener.start())
            self.tasks['mastodon'] = task
            logger.info("Mastodon listener started")
        except Exception as e:
            logger.error(f"Failed to start Mastodon listener: {e}", exc_info=True)
        
        logger.info(f"Started {len(self.tasks)} listeners")
    
    async def stop_all(self):
        """Stop all listeners."""
        if not self.running:
            return
        
        logger.info("Stopping all listeners...")
        self.running = False
        
        # Stop individual listeners
        if self.notion_listener:
            self.notion_listener.stop()
        
        if self.mastodon_listener:
            self.mastodon_listener.stop()
        
        # Cancel tasks
        for name, task in self.tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.tasks.clear()
        logger.info("All listeners stopped")
    
    def get_status(self) -> Dict:
        """Get status of all listeners."""
        status = {
            'running': self.running,
            'listeners': {}
        }
        
        if self.notion_listener:
            status['listeners']['notion'] = {
                'running': self.notion_listener.running,
                'last_check': self.notion_listener._last_check_time.isoformat() if self.notion_listener._last_check_time else None
            }
        
        if self.mastodon_listener:
            status['listeners']['mastodon'] = {
                'running': self.mastodon_listener.running
            }
        
        return status
    
    async def health_check(self) -> bool:
        """Check health of all listeners."""
        if not self.running:
            return False
        
        # Check if tasks are still running
        for name, task in self.tasks.items():
            if task.done():
                logger.warning(f"Listener {name} task completed unexpectedly")
                return False
        
        return True
