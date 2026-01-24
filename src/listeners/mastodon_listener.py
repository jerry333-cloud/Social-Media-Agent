"""Mastodon streaming listener for real-time comment detection."""

import os
import asyncio
from typing import Dict, Optional
import logging

from src.mastodon_client import MastodonClient
from src.database import get_db, PostCRUD

logger = logging.getLogger(__name__)

STREAM_ENABLED = os.getenv("MASTODON_STREAM_ENABLED", "true").lower() == "true"


class MastodonListener:
    """Listens to Mastodon streaming API for mentions and comments."""
    
    def __init__(self):
        """Initialize Mastodon listener."""
        self.mastodon_client = MastodonClient()
        self.running = False
        self.stream = None
    
    async def start(self):
        """Start streaming listener."""
        if not STREAM_ENABLED:
            logger.info("Mastodon streaming disabled")
            return
        
        self.running = True
        logger.info("Starting Mastodon streaming listener...")
        
        while self.running:
            try:
                # Connect to user stream
                self.stream = self.mastodon_client.client.stream_user()
                
                logger.info("Connected to Mastodon user stream")
                
                # Process stream events
                async for event in self._stream_events():
                    if not self.running:
                        break
                    
                    await self._handle_event(event)
            
            except Exception as e:
                logger.error(f"Error in Mastodon stream: {e}", exc_info=True)
                if self.running:
                    logger.info("Reconnecting in 10 seconds...")
                    await asyncio.sleep(10)
    
    def stop(self):
        """Stop streaming listener."""
        self.running = False
        if self.stream:
            try:
                self.stream.close()
            except:
                pass
        logger.info("Stopped Mastodon streaming listener")
    
    async def _stream_events(self):
        """Generator for stream events."""
        # Mastodon.py streaming is synchronous, so we need to wrap it
        import threading
        import queue
        
        event_queue = queue.Queue()
        
        def stream_worker():
            try:
                for event in self.mastodon_client.client.stream_user():
                    if not self.running:
                        break
                    event_queue.put(event)
            except Exception as e:
                event_queue.put(('error', e))
        
        thread = threading.Thread(target=stream_worker, daemon=True)
        thread.start()
        
        while self.running:
            try:
                event = event_queue.get(timeout=1)
                if event[0] == 'error':
                    raise event[1]
                yield event
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in stream events: {e}")
                break
    
    async def _handle_event(self, event: Dict):
        """Handle a stream event."""
        try:
            event_type = event.get('event')
            
            if event_type == 'notification':
                await self._handle_notification(event.get('payload', {}))
            elif event_type == 'update':
                # New post from someone we follow
                pass
            elif event_type == 'delete':
                # Post deleted
                pass
            
        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)
    
    async def _handle_notification(self, notification: Dict):
        """Handle a notification event (mention, reply, etc.)."""
        try:
            notification_type = notification.get('type')
            
            if notification_type in ['mention', 'reply']:
                status = notification.get('status')
                if not status:
                    return
                
                # Check if this is a reply to one of our posts
                in_reply_to_id = status.get('in_reply_to_id')
                if in_reply_to_id:
                    # Check if we have a post with this ID
                    with get_db() as db:
                        # Note: We'd need to store Mastodon post IDs in our Post table
                        # For now, create a reply task for any reply
                        post = PostCRUD.create(
                            db=db,
                            content=f"Reply to Mastodon post {in_reply_to_id}: {status.get('content', '')[:200]}",
                            status="pending_review",
                            is_reply=True,
                            parent_post_id=None  # Would need to map Mastodon ID to our post ID
                        )
                        logger.info(f"Created reply task {post.id} for notification")
                
                # Extract context
                original_post = status.get('in_reply_to')
                comment_text = status.get('content', '')
                
                # Create reply generation task
                logger.info(f"New {notification_type} detected: {comment_text[:100]}")
            
        except Exception as e:
            logger.error(f"Error handling notification: {e}", exc_info=True)
