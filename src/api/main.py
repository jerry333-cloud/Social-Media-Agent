"""FastAPI application main module."""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import asyncio

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
    
    # Initialize RAG system
    try:
        from src.rag.vector_store import VectorStore
        from src.rag.embedder import Embedder
        from src.rag.bm25_search import BM25Search
        
        # Initialize components (they'll create tables if needed)
        VectorStore()
        Embedder.get_instance()
        BM25Search()
        logger.info("RAG system initialized successfully")
    except Exception as e:
        logger.warning(f"RAG system initialization warning: {e}")
        # Don't raise - allow API to run without RAG
    
    # Start listeners (if enabled)
    try:
        from src.listeners.manager import ListenerManager
        import os
        if os.getenv("MASTODON_STREAM_ENABLED", "true").lower() == "true" or os.getenv("NOTION_POLL_INTERVAL_MINUTES"):
            listener_manager = ListenerManager()
            app.state.listener_manager = listener_manager
            asyncio.create_task(listener_manager.start_all())
            logger.info("Listeners started successfully")
    except Exception as e:
        logger.warning(f"Listeners not started: {e}")
        # Don't raise - allow API to run without listeners
    
    logger.info("Social Media Agent API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Social Media Agent API...")
    
    # Stop listeners
    try:
        if hasattr(app.state, 'listener_manager'):
            await app.state.listener_manager.stop_all()
            logger.info("Listeners shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down listeners: {e}")
    
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

# Include RAG router if it exists
try:
    from src.api.routes import rag
    app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
except ImportError:
    pass  # RAG routes not created yet

# Include listeners router if it exists
try:
    from src.api.routes import listeners
    app.include_router(listeners.router, prefix="/api/listeners", tags=["listeners"])
except ImportError:
    pass  # Listener routes not created yet


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
