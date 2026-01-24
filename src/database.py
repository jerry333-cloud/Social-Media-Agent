"""Database models and CRUD operations using SQLAlchemy."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from contextlib import contextmanager
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./social_media_agent.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class Post(Base):
    """Post model for storing social media posts."""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    image_path = Column(String, nullable=True)
    status = Column(String, default="draft")  # draft, pending, approved, published, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    mastodon_url = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    # RAG fields
    context_chunk_ids = Column(Text, nullable=True)  # JSON array of chunk IDs used
    retrieval_scores = Column(Text, nullable=True)  # JSON array of scores
    is_reply = Column(Boolean, default=False)
    parent_post_id = Column(Integer, nullable=True)


class Schedule(Base):
    """Schedule model for automated post creation."""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    cron_expression = Column(String, nullable=False)
    with_image = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotionCache(Base):
    """Cache for Notion content."""
    __tablename__ = "notion_cache"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class Config(Base):
    """Configuration key-value store."""
    __tablename__ = "config"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# RAG Models
class Chunk(Base):
    """Text chunk model for RAG."""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String, nullable=False, index=True)  # Notion page ID
    chunk_index = Column(Integer, nullable=False)  # Position in page
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    source_type = Column(String, default="notion")  # notion, approved_post, approved_reply
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RetrievalLog(Base):
    """Log of retrieval operations for quality tracking."""
    __tablename__ = "retrieval_logs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    chunks_used = Column(Text, nullable=True)  # JSON array of chunk IDs
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    avg_score = Column(Float, nullable=True)
    min_score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    retrieval_type = Column(String, default="hybrid")  # hybrid, bm25_only, vector_only
    created_at = Column(DateTime, default=datetime.utcnow)


# Database initialization
def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    
    # Initialize FTS5 and vector tables
    try:
        from src.rag.bm25_search import BM25Search
        from src.rag.vector_store import VectorStore
        BM25Search()
        VectorStore()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not initialize RAG tables: {e}")


# Database session management
@contextmanager
def get_db():
    """Get database session context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# CRUD Operations for Posts
class PostCRUD:
    @staticmethod
    def create(db: Session, content: str, image_path: Optional[str] = None, status: str = "draft") -> Post:
        """Create a new post."""
        post = Post(content=content, image_path=image_path, status=status)
        db.add(post)
        db.commit()
        db.refresh(post)
        return post

    @staticmethod
    def get(db: Session, post_id: int) -> Optional[Post]:
        """Get a post by ID."""
        return db.query(Post).filter(Post.id == post_id).first()

    @staticmethod
    def get_all(db: Session, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Post]:
        """Get all posts with optional status filter."""
        query = db.query(Post)
        if status:
            query = query.filter(Post.status == status)
        return query.order_by(Post.created_at.desc()).limit(limit).offset(offset).all()

    @staticmethod
    def update_status(db: Session, post_id: int, status: str) -> Optional[Post]:
        """Update post status."""
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.status = status
            if status == "published":
                post.published_at = datetime.utcnow()
            db.commit()
            db.refresh(post)
        return post

    @staticmethod
    def update_mastodon_url(db: Session, post_id: int, mastodon_url: str) -> Optional[Post]:
        """Update post Mastodon URL."""
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.mastodon_url = mastodon_url
            db.commit()
            db.refresh(post)
        return post

    @staticmethod
    def update_error(db: Session, post_id: int, error_message: str) -> Optional[Post]:
        """Update post error message."""
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.error_message = error_message
            db.commit()
            db.refresh(post)
        return post

    @staticmethod
    def delete(db: Session, post_id: int) -> bool:
        """Delete a post."""
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            db.delete(post)
            db.commit()
            return True
        return False


# CRUD Operations for Schedules
class ScheduleCRUD:
    @staticmethod
    def create(db: Session, name: str, cron_expression: str, with_image: bool = False, enabled: bool = True) -> Schedule:
        """Create a new schedule."""
        schedule = Schedule(name=name, cron_expression=cron_expression, with_image=with_image, enabled=enabled)
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def get(db: Session, schedule_id: int) -> Optional[Schedule]:
        """Get a schedule by ID."""
        return db.query(Schedule).filter(Schedule.id == schedule_id).first()

    @staticmethod
    def get_all(db: Session, enabled_only: bool = False) -> List[Schedule]:
        """Get all schedules."""
        query = db.query(Schedule)
        if enabled_only:
            query = query.filter(Schedule.enabled == True)
        return query.all()

    @staticmethod
    def update(db: Session, schedule_id: int, **kwargs) -> Optional[Schedule]:
        """Update a schedule."""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if schedule:
            for key, value in kwargs.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            schedule.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(schedule)
        return schedule

    @staticmethod
    def update_run_times(db: Session, schedule_id: int, last_run: datetime, next_run: datetime) -> Optional[Schedule]:
        """Update schedule run times."""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if schedule:
            schedule.last_run = last_run
            schedule.next_run = next_run
            db.commit()
            db.refresh(schedule)
        return schedule

    @staticmethod
    def delete(db: Session, schedule_id: int) -> bool:
        """Delete a schedule."""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if schedule:
            db.delete(schedule)
            db.commit()
            return True
        return False


# CRUD Operations for NotionCache
class NotionCacheCRUD:
    @staticmethod
    def create(db: Session, content: str) -> NotionCache:
        """Create or update Notion cache (keep only latest)."""
        # Delete old cache entries
        db.query(NotionCache).delete()
        # Create new cache
        cache = NotionCache(content=content)
        db.add(cache)
        db.commit()
        db.refresh(cache)
        return cache

    @staticmethod
    def get_latest(db: Session) -> Optional[NotionCache]:
        """Get the latest Notion cache."""
        return db.query(NotionCache).order_by(NotionCache.fetched_at.desc()).first()


# CRUD Operations for Config
class ConfigCRUD:
    @staticmethod
    def get(db: Session, key: str) -> Optional[str]:
        """Get a config value."""
        config = db.query(Config).filter(Config.key == key).first()
        return config.value if config else None

    @staticmethod
    def set(db: Session, key: str, value: str) -> Config:
        """Set a config value."""
        config = db.query(Config).filter(Config.key == key).first()
        if config:
            config.value = value
            config.updated_at = datetime.utcnow()
        else:
            config = Config(key=key, value=value)
            db.add(config)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def get_all(db: Session) -> List[Config]:
        """Get all config values."""
        return db.query(Config).all()

    @staticmethod
    def delete(db: Session, key: str) -> bool:
        """Delete a config value."""
        config = db.query(Config).filter(Config.key == key).first()
        if config:
            db.delete(config)
            db.commit()
            return True
        return False


# CRUD Operations for Chunks
class ChunkCRUD:
    @staticmethod
    def create(db: Session, page_id: str, chunk_index: int, content: str, token_count: int, source_type: str = "notion") -> Chunk:
        """Create a new chunk."""
        chunk = Chunk(
            page_id=page_id,
            chunk_index=chunk_index,
            content=content,
            token_count=token_count,
            source_type=source_type
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        return chunk

    @staticmethod
    def get(db: Session, chunk_id: int) -> Optional[Chunk]:
        """Get a chunk by ID."""
        return db.query(Chunk).filter(Chunk.id == chunk_id).first()

    @staticmethod
    def get_by_page(db: Session, page_id: str) -> List[Chunk]:
        """Get all chunks for a page."""
        return db.query(Chunk).filter(Chunk.page_id == page_id).order_by(Chunk.chunk_index).all()

    @staticmethod
    def delete_by_page(db: Session, page_id: str) -> int:
        """Delete all chunks for a page. Returns count deleted."""
        chunks = db.query(Chunk).filter(Chunk.page_id == page_id).all()
        count = len(chunks)
        for chunk in chunks:
            db.delete(chunk)
        db.commit()
        return count

    @staticmethod
    def get_by_ids(db: Session, chunk_ids: List[int]) -> List[Chunk]:
        """Get chunks by IDs."""
        return db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()


# CRUD Operations for RetrievalLog
class RetrievalLogCRUD:
    @staticmethod
    def create(
        db: Session,
        query: str,
        chunks_used: Optional[List[int]] = None,
        post_id: Optional[int] = None,
        avg_score: Optional[float] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        retrieval_type: str = "hybrid"
    ) -> RetrievalLog:
        """Create a retrieval log entry."""
        import json
        log = RetrievalLog(
            query=query,
            chunks_used=json.dumps(chunks_used) if chunks_used else None,
            post_id=post_id,
            avg_score=avg_score,
            min_score=min_score,
            max_score=max_score,
            retrieval_type=retrieval_type
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def get_recent(db: Session, limit: int = 100) -> List[RetrievalLog]:
        """Get recent retrieval logs."""
        return db.query(RetrievalLog).order_by(RetrievalLog.created_at.desc()).limit(limit).all()
