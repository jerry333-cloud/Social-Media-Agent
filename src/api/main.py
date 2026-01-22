"""FastAPI application main module."""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from src.database import init_db
from src.schemas import HealthResponse, ErrorResponse
from src.api.routes import posts, schedule, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting Social Media Agent API...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Initialize scheduler
    try:
        from src.scheduler import start_scheduler, shutdown_scheduler
        start_scheduler()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        # Don't raise - allow API to run without scheduler
    
    # Initialize Telegram bot (if configured)
    try:
        from src.telegram_client import start_telegram_bot
        import os
        if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
            start_telegram_bot()
            logger.info("Telegram bot started successfully")
    except Exception as e:
        logger.warning(f"Telegram bot not started: {e}")
        # Don't raise - allow API to run without Telegram
    
    logger.info("Social Media Agent API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Social Media Agent API...")
    
    try:
        from src.scheduler import shutdown_scheduler
        shutdown_scheduler()
        logger.info("Scheduler shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")
    
    logger.info("Social Media Agent API shut down complete")


# Create FastAPI app
app = FastAPI(
    title="Social Media Agent API",
    description="API for managing social media posts with AI generation, scheduling, and HITL approval",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all uncaught exceptions."""
    logger.error(f"Uncaught exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail=f"Internal server error: {str(exc)}"
        ).model_dump()
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    try:
        # Check database
        from src.database import get_db
        with get_db():
            db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"unhealthy: {str(e)}"
    
    # Check scheduler
    try:
        from src.scheduler import is_scheduler_running
        scheduler_status = "running" if is_scheduler_running() else "stopped"
    except Exception as e:
        scheduler_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.utcnow(),
        database=db_status,
        scheduler=scheduler_status
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Social Media Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
app.include_router(schedule.router, prefix="/api/schedules", tags=["schedules"])
app.include_router(config.router, prefix="/api/config", tags=["config"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
