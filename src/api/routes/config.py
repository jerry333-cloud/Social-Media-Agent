"""Configuration management API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List
import logging

from src.database import get_db, ConfigCRUD, NotionCacheCRUD
from src.schemas import ConfigItem, ConfigUpdate, ConfigResponse, NotionCacheResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[ConfigResponse])
async def list_config():
    """List all configuration values."""
    try:
        with get_db() as db:
            configs = ConfigCRUD.get_all(db)
            return [ConfigResponse.model_validate(c) for c in configs]
    except Exception as e:
        logger.error(f"Error listing configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list configs: {str(e)}")


@router.get("/{key}", response_model=ConfigResponse)
async def get_config(key: str):
    """Get a specific configuration value."""
    try:
        with get_db() as db:
            value = ConfigCRUD.get(db, key)
            if value is None:
                raise HTTPException(status_code=404, detail="Config key not found")
            
            # Get the full config object to return with timestamp
            from src.database import Config
            config = db.query(Config).filter(Config.key == key).first()
            return ConfigResponse.model_validate(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")


@router.put("/{key}", response_model=ConfigResponse)
async def update_config(key: str, config_update: ConfigUpdate):
    """Update or create a configuration value."""
    try:
        with get_db() as db:
            config = ConfigCRUD.set(db, key, config_update.value)
            logger.info(f"Config updated: {key}")
            return ConfigResponse.model_validate(config)
    except Exception as e:
        logger.error(f"Error updating config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@router.delete("/{key}")
async def delete_config(key: str):
    """Delete a configuration value."""
    try:
        with get_db() as db:
            success = ConfigCRUD.delete(db, key)
            if not success:
                raise HTTPException(status_code=404, detail="Config key not found")
            logger.info(f"Config deleted: {key}")
            return {"message": "Config deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete config: {str(e)}")


@router.get("/notion/fetch", response_model=NotionCacheResponse)
async def fetch_notion_content():
    """Manually fetch content from Notion and update cache."""
    try:
        from src.notion_client import NotionClient
        
        logger.info("Fetching content from Notion...")
        notion_client = NotionClient()
        content = notion_client.fetch_content()
        
        with get_db() as db:
            cache = NotionCacheCRUD.create(db, content)
            logger.info("Notion content cached successfully")
            return NotionCacheResponse.model_validate(cache)
            
    except Exception as e:
        logger.error(f"Error fetching Notion content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch Notion content: {str(e)}")


@router.get("/notion/cache", response_model=NotionCacheResponse)
async def get_notion_cache():
    """Get the latest cached Notion content."""
    try:
        with get_db() as db:
            cache = NotionCacheCRUD.get_latest(db)
            if not cache:
                raise HTTPException(status_code=404, detail="No cached Notion content found")
            return NotionCacheResponse.model_validate(cache)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Notion cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get Notion cache: {str(e)}")


@router.post("/reply-to-posts")
async def trigger_reply_generation(keyword: str = None, num_posts: int = 5):
    """Manually trigger reply generation to Mastodon posts."""
    try:
        from src.reply_generator import ReplyGenerator
        
        logger.info(f"Generating replies for keyword: {keyword}, num_posts: {num_posts}")
        
        reply_generator = ReplyGenerator()
        results = reply_generator.generate_and_publish_replies(
            keyword=keyword,
            num_posts=num_posts
        )
        
        logger.info(f"Reply generation complete. {len(results)} replies generated.")
        
        return {
            "message": "Replies generated successfully",
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error generating replies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate replies: {str(e)}")
