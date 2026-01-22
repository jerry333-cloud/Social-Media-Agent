"""Schedule management API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List
import logging

from src.database import get_db, ScheduleCRUD
from src.schemas import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ScheduleResponse)
async def create_schedule(schedule_request: ScheduleCreate):
    """
    Create a new schedule for automated post creation.
    
    - Uses cron expression for timing (e.g., "0 9 * * *" for daily at 9 AM)
    - Can include image generation
    - Can be enabled/disabled
    """
    try:
        # Validate cron expression
        from croniter import croniter
        from datetime import datetime
        
        if not croniter.is_valid(schedule_request.cron_expression):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cron expression: {schedule_request.cron_expression}"
            )
        
        with get_db() as db:
            schedule = ScheduleCRUD.create(
                db,
                name=schedule_request.name,
                cron_expression=schedule_request.cron_expression,
                with_image=schedule_request.with_image,
                enabled=schedule_request.enabled
            )
            
            # Calculate next run time
            cron = croniter(schedule_request.cron_expression, datetime.utcnow())
            next_run = cron.get_next(datetime)
            
            # Update with next_run
            schedule = ScheduleCRUD.update_run_times(
                db,
                schedule.id,
                last_run=None,
                next_run=next_run
            )
            
            logger.info(f"Schedule created: {schedule.name} (ID: {schedule.id})")
            
            # Reload scheduler to pick up new schedule
            try:
                from src.scheduler import reload_scheduler
                reload_scheduler()
            except Exception as e:
                logger.warning(f"Failed to reload scheduler: {e}")
            
            return ScheduleResponse.model_validate(schedule)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(enabled_only: bool = False):
    """List all schedules."""
    try:
        with get_db() as db:
            schedules = ScheduleCRUD.get_all(db, enabled_only=enabled_only)
            return [ScheduleResponse.model_validate(s) for s in schedules]
    except Exception as e:
        logger.error(f"Error listing schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(e)}")


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: int):
    """Get a specific schedule by ID."""
    try:
        with get_db() as db:
            schedule = ScheduleCRUD.get(db, schedule_id)
            if not schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")
            return ScheduleResponse.model_validate(schedule)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(e)}")


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, schedule_update: ScheduleUpdate):
    """Update a schedule."""
    try:
        # Validate cron expression if provided
        if schedule_update.cron_expression:
            from croniter import croniter
            if not croniter.is_valid(schedule_update.cron_expression):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid cron expression: {schedule_update.cron_expression}"
                )
        
        with get_db() as db:
            schedule = ScheduleCRUD.get(db, schedule_id)
            if not schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")
            
            # Prepare update data
            update_data = schedule_update.model_dump(exclude_unset=True)
            
            # Update schedule
            schedule = ScheduleCRUD.update(db, schedule_id, **update_data)
            
            # Recalculate next run if cron changed
            if schedule_update.cron_expression:
                from croniter import croniter
                from datetime import datetime
                
                cron = croniter(schedule.cron_expression, datetime.utcnow())
                next_run = cron.get_next(datetime)
                schedule = ScheduleCRUD.update_run_times(
                    db,
                    schedule.id,
                    last_run=schedule.last_run,
                    next_run=next_run
                )
            
            logger.info(f"Schedule updated: {schedule.name} (ID: {schedule.id})")
            
            # Reload scheduler
            try:
                from src.scheduler import reload_scheduler
                reload_scheduler()
            except Exception as e:
                logger.warning(f"Failed to reload scheduler: {e}")
            
            return ScheduleResponse.model_validate(schedule)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """Delete a schedule."""
    try:
        with get_db() as db:
            success = ScheduleCRUD.delete(db, schedule_id)
            if not success:
                raise HTTPException(status_code=404, detail="Schedule not found")
            
            logger.info(f"Schedule deleted: ID {schedule_id}")
            
            # Reload scheduler
            try:
                from src.scheduler import reload_scheduler
                reload_scheduler()
            except Exception as e:
                logger.warning(f"Failed to reload scheduler: {e}")
            
            return {"message": "Schedule deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")


@router.post("/{schedule_id}/enable")
async def enable_schedule(schedule_id: int):
    """Enable a schedule."""
    try:
        with get_db() as db:
            schedule = ScheduleCRUD.update(db, schedule_id, enabled=True)
            if not schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")
            
            logger.info(f"Schedule enabled: {schedule.name} (ID: {schedule.id})")
            
            # Reload scheduler
            try:
                from src.scheduler import reload_scheduler
                reload_scheduler()
            except Exception as e:
                logger.warning(f"Failed to reload scheduler: {e}")
            
            return ScheduleResponse.model_validate(schedule)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to enable schedule: {str(e)}")


@router.post("/{schedule_id}/disable")
async def disable_schedule(schedule_id: int):
    """Disable a schedule."""
    try:
        with get_db() as db:
            schedule = ScheduleCRUD.update(db, schedule_id, enabled=False)
            if not schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")
            
            logger.info(f"Schedule disabled: {schedule.name} (ID: {schedule.id})")
            
            # Reload scheduler
            try:
                from src.scheduler import reload_scheduler
                reload_scheduler()
            except Exception as e:
                logger.warning(f"Failed to reload scheduler: {e}")
            
            return ScheduleResponse.model_validate(schedule)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to disable schedule: {str(e)}")
