"""Background task scheduler using APScheduler."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from src.database import get_db, ScheduleCRUD, PostCRUD, NotionCacheCRUD

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None


def create_post_job(schedule_id: int, with_image: bool):
    """
    Job function to create a post based on schedule.
    
    Args:
        schedule_id: ID of the schedule triggering this job
        with_image: Whether to generate an image for the post
    """
    logger.info(f"Running scheduled post creation job (schedule_id={schedule_id}, with_image={with_image})")
    
    try:
        from src.notion_client import NotionClient
        from src.llm_client import LLMClient
        from src.image_client import ImageClient
        from src.mastodon_client import MastodonClient
        
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
        if with_image and post_text.should_generate_image and post_text.image_prompt:
            logger.info("Generating image...")
            image_client = ImageClient()
            image_path = image_client.generate_image(post_text.image_prompt)
            
            with get_db() as db:
                post = PostCRUD.get(db, post_id)
                post.image_path = image_path
                db.commit()
        
        # Publish to Mastodon
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
        
        # Update schedule last_run
        with get_db() as db:
            from croniter import croniter
            schedule = ScheduleCRUD.get(db, schedule_id)
            if schedule:
                cron = croniter(schedule.cron_expression, datetime.utcnow())
                next_run = cron.get_next(datetime)
                ScheduleCRUD.update_run_times(db, schedule_id, datetime.utcnow(), next_run)
        
        logger.info(f"Scheduled post created and published successfully: {mastodon_url}")
        
    except Exception as e:
        logger.error(f"Error in scheduled post creation: {e}", exc_info=True)
        
        # Update post with error
        try:
            with get_db() as db:
                PostCRUD.update_error(db, post_id, str(e))
                PostCRUD.update_status(db, post_id, "failed")
        except:
            pass


def load_schedules_to_scheduler():
    """Load all enabled schedules from database and add them to the scheduler."""
    global _scheduler
    
    if _scheduler is None:
        logger.warning("Scheduler not initialized")
        return
    
    # Remove all existing jobs
    _scheduler.remove_all_jobs()
    
    # Load enabled schedules from database
    try:
        with get_db() as db:
            schedules = ScheduleCRUD.get_all(db, enabled_only=True)
            
            for schedule in schedules:
                try:
                    # Create cron trigger
                    trigger = CronTrigger.from_crontab(schedule.cron_expression)
                    
                    # Add job to scheduler
                    _scheduler.add_job(
                        create_post_job,
                        trigger=trigger,
                        args=[schedule.id, schedule.with_image],
                        id=f"schedule_{schedule.id}",
                        name=schedule.name,
                        replace_existing=True
                    )
                    
                    logger.info(f"Loaded schedule: {schedule.name} (ID: {schedule.id}, cron: {schedule.cron_expression})")
                    
                except Exception as e:
                    logger.error(f"Failed to load schedule {schedule.id}: {e}")
        
        logger.info(f"Loaded {len(_scheduler.get_jobs())} schedules")
        
    except Exception as e:
        logger.error(f"Error loading schedules: {e}", exc_info=True)


def start_scheduler():
    """Initialize and start the background scheduler."""
    global _scheduler
    
    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    logger.info("Initializing scheduler...")
    
    # Create scheduler
    _scheduler = BackgroundScheduler(
        timezone='UTC',
        job_defaults={
            'coalesce': True,  # Combine missed runs
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace time for missed jobs
        }
    )
    
    # Load schedules from database
    load_schedules_to_scheduler()
    
    # Start scheduler
    _scheduler.start()
    logger.info("Scheduler started successfully")


def shutdown_scheduler():
    """Shutdown the background scheduler."""
    global _scheduler
    
    if _scheduler is None:
        logger.warning("Scheduler not running")
        return
    
    logger.info("Shutting down scheduler...")
    _scheduler.shutdown(wait=True)
    _scheduler = None
    logger.info("Scheduler shut down successfully")


def reload_scheduler():
    """Reload schedules from database."""
    global _scheduler
    
    if _scheduler is None:
        logger.warning("Scheduler not running")
        return
    
    logger.info("Reloading schedules...")
    load_schedules_to_scheduler()
    logger.info("Schedules reloaded successfully")


def is_scheduler_running() -> bool:
    """Check if scheduler is running."""
    global _scheduler
    return _scheduler is not None and _scheduler.running


def get_scheduler_jobs():
    """Get list of scheduled jobs."""
    global _scheduler
    
    if _scheduler is None:
        return []
    
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger)
        })
    
    return jobs
