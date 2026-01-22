"""Post management API endpoints."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import logging

from src.database import get_db, PostCRUD, NotionCacheCRUD
from src.schemas import (
    PostCreate,
    PostCreateWithHITL,
    PostResponse,
    PostListResponse,
    PostApproval
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create", response_model=PostResponse)
async def create_post(
    post_request: PostCreate,
    background_tasks: BackgroundTasks
):
    """
    Create a new social media post.
    
    - Fetches content from Notion
    - Generates post text using LLM
    - Optionally generates an image
    - Publishes to Mastodon (unless dry_run is True)
    """
    try:
        from src.notion_client import NotionClient
        from src.llm_client import LLMClient
        from src.image_client import ImageClient
        from src.mastodon_client import MastodonClient
        import os
        
        # Create initial post record
        with get_db() as db:
            post = PostCRUD.create(db, content="Generating...", status="draft")
            post_id = post.id
        
        # Fetch Notion content
        logger.info("Fetching content from Notion...")
        notion_client = NotionClient()
        notion_content = notion_client.fetch_content()
        
        # Cache Notion content
        with get_db() as db:
            NotionCacheCRUD.create(db, content=notion_content)
        
        # Generate post text
        logger.info("Generating post text...")
        llm_client = LLMClient()
        post_text = llm_client.generate_structured_post(notion_content)
        
        # Update post content
        with get_db() as db:
            post = PostCRUD.get(db, post_id)
            post.content = post_text.text
            db.commit()
        
        # Generate image if requested
        image_path = None
        if post_request.with_image and post_text.should_generate_image and post_text.image_prompt:
            logger.info("Generating image...")
            image_client = ImageClient()
            image_path = image_client.generate_image(post_text.image_prompt)
            
            with get_db() as db:
                post = PostCRUD.get(db, post_id)
                post.image_path = image_path
                db.commit()
        
        # Publish to Mastodon if not dry run
        if not post_request.dry_run:
            logger.info("Publishing to Mastodon...")
            mastodon_client = MastodonClient()
            
            if image_path:
                status = mastodon_client.post_with_media(post_text.text, image_path)
            else:
                status = mastodon_client.post(post_text.text)
            
            mastodon_url = status['url']
            
            # Update post status and URL
            with get_db() as db:
                post = PostCRUD.update_status(db, post_id, "published")
                PostCRUD.update_mastodon_url(db, post_id, mastodon_url)
            
            # Add comment to Notion
            notion_client.add_comment_to_page(mastodon_url)
            
            logger.info(f"Post published successfully: {mastodon_url}")
        else:
            # Mark as draft for dry run
            with get_db() as db:
                PostCRUD.update_status(db, post_id, "draft")
            logger.info("Dry run - post not published")
        
        # Return final post
        with get_db() as db:
            post = PostCRUD.get(db, post_id)
            return PostResponse.model_validate(post)
            
    except Exception as e:
        logger.error(f"Error creating post: {e}", exc_info=True)
        
        # Update post with error
        try:
            with get_db() as db:
                PostCRUD.update_error(db, post_id, str(e))
                PostCRUD.update_status(db, post_id, "failed")
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Failed to create post: {str(e)}")


@router.post("/create-with-hitl", response_model=PostResponse)
async def create_post_with_hitl(post_request: PostCreateWithHITL):
    """
    Create a post with Human-in-the-Loop approval via Telegram.
    
    - Generates text and optionally an image
    - Sends to Telegram for approval
    - Allows iterative feedback and regeneration
    - Publishes only after approval
    """
    try:
        from src.hitl_approval import HITLApprovalLoop
        import os
        
        # Check Telegram configuration
        if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
            raise HTTPException(
                status_code=400,
                detail="Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
            )
        
        # Create initial post record
        with get_db() as db:
            post = PostCRUD.create(db, content="Awaiting approval...", status="pending")
            post_id = post.id
        
        # Run HITL approval loop
        logger.info(f"Starting HITL approval loop for post {post_id}...")
        hitl_loop = HITLApprovalLoop()
        approved, final_text, final_image_path, mastodon_url = await hitl_loop.run(
            with_image=post_request.with_image
        )
        
        if approved:
            # Update post with final content
            with get_db() as db:
                post = PostCRUD.get(db, post_id)
                post.content = final_text
                post.image_path = final_image_path
                post.status = "published"
                post.mastodon_url = mastodon_url
                db.commit()
            
            logger.info(f"Post {post_id} approved and published: {mastodon_url}")
        else:
            # Mark as rejected
            with get_db() as db:
                PostCRUD.update_status(db, post_id, "rejected")
            logger.info(f"Post {post_id} rejected by user")
        
        # Return final post
        with get_db() as db:
            post = PostCRUD.get(db, post_id)
            return PostResponse.model_validate(post)
            
    except Exception as e:
        logger.error(f"Error in HITL approval: {e}", exc_info=True)
        
        # Update post with error
        try:
            with get_db() as db:
                PostCRUD.update_error(db, post_id, str(e))
                PostCRUD.update_status(db, post_id, "failed")
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"HITL approval failed: {str(e)}")


@router.get("", response_model=PostListResponse)
async def list_posts(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List all posts with optional status filter."""
    try:
        with get_db() as db:
            posts = PostCRUD.get_all(db, status=status, limit=limit, offset=offset)
            total = len(posts)  # Simplified - in production, use a count query
            
            return PostListResponse(
                posts=[PostResponse.model_validate(p) for p in posts],
                total=total,
                limit=limit,
                offset=offset
            )
    except Exception as e:
        logger.error(f"Error listing posts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list posts: {str(e)}")


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int):
    """Get a specific post by ID."""
    try:
        with get_db() as db:
            post = PostCRUD.get(db, post_id)
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")
            return PostResponse.model_validate(post)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting post: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get post: {str(e)}")


@router.delete("/{post_id}")
async def delete_post(post_id: int):
    """Delete a post."""
    try:
        with get_db() as db:
            success = PostCRUD.delete(db, post_id)
            if not success:
                raise HTTPException(status_code=404, detail="Post not found")
            return {"message": "Post deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting post: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete post: {str(e)}")


@router.post("/{post_id}/approve")
async def approve_post(post_id: int):
    """Approve a pending post and publish it."""
    try:
        with get_db() as db:
            post = PostCRUD.get(db, post_id)
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")
            
            if post.status != "pending":
                raise HTTPException(status_code=400, detail="Only pending posts can be approved")
        
        # Publish to Mastodon
        from src.mastodon_client import MastodonClient
        from src.notion_client import NotionClient
        
        mastodon_client = MastodonClient()
        
        if post.image_path:
            status = mastodon_client.post_with_media(post.content, post.image_path)
        else:
            status = mastodon_client.post(post.content)
        
        mastodon_url = status['url']
        
        # Update post
        with get_db() as db:
            PostCRUD.update_status(db, post_id, "published")
            PostCRUD.update_mastodon_url(db, post_id, mastodon_url)
        
        # Add comment to Notion
        notion_client = NotionClient()
        notion_client.add_comment_to_page(mastodon_url)
        
        logger.info(f"Post {post_id} approved and published: {mastodon_url}")
        
        with get_db() as db:
            post = PostCRUD.get(db, post_id)
            return PostResponse.model_validate(post)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving post: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to approve post: {str(e)}")


@router.post("/{post_id}/reject")
async def reject_post(post_id: int):
    """Reject a pending post."""
    try:
        with get_db() as db:
            post = PostCRUD.get(db, post_id)
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")
            
            if post.status != "pending":
                raise HTTPException(status_code=400, detail="Only pending posts can be rejected")
            
            PostCRUD.update_status(db, post_id, "rejected")
            logger.info(f"Post {post_id} rejected")
            
            post = PostCRUD.get(db, post_id)
            return PostResponse.model_validate(post)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting post: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reject post: {str(e)}")
