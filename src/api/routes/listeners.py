"""Listener management API routes."""

from fastapi import APIRouter, HTTPException
from typing import Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_listener_status():
    """Get status of all listeners."""
    try:
        from src.listeners.manager import ListenerManager
        
        # Try to get from app state if available
        # Otherwise create a temporary instance
        try:
            from fastapi import Request
            # This would need to be passed via dependency injection
            # For now, create a new instance
            manager = ListenerManager()
        except:
            manager = ListenerManager()
        
        status = manager.get_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get listener status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notion/trigger")
async def trigger_notion_listener():
    """Manually trigger Notion listener check."""
    try:
        from src.listeners.notion_listener import NotionListener
        
        listener = NotionListener()
        pages_indexed = await listener.manual_trigger()
        
        return {
            "success": True,
            "pages_indexed": pages_indexed
        }
    except Exception as e:
        logger.error(f"Failed to trigger Notion listener: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
