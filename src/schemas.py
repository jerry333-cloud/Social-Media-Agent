"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# Post schemas
class PostBase(BaseModel):
    """Base post schema."""
    content: str
    image_path: Optional[str] = None


class PostCreate(BaseModel):
    """Schema for creating a post."""
    with_image: bool = False
    dry_run: bool = False
    scheduled_for: Optional[datetime] = None


class PostCreateWithHITL(BaseModel):
    """Schema for creating a post with HITL approval."""
    with_image: bool = False


class PostResponse(BaseModel):
    """Schema for post response."""
    id: int
    content: str
    image_path: Optional[str] = None
    status: str
    created_at: datetime
    published_at: Optional[datetime] = None
    mastodon_url: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    """Schema for post list response."""
    posts: list[PostResponse]
    total: int
    limit: int
    offset: int


class PostApproval(BaseModel):
    """Schema for post approval."""
    approved: bool
    feedback: Optional[str] = None


# Schedule schemas
class ScheduleBase(BaseModel):
    """Base schedule schema."""
    name: str
    cron_expression: str = Field(..., description="Cron expression (e.g., '0 9 * * *' for 9 AM daily)")
    with_image: bool = False
    enabled: bool = True


class ScheduleCreate(ScheduleBase):
    """Schema for creating a schedule."""
    pass


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule."""
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    with_image: Optional[bool] = None
    enabled: Optional[bool] = None


class ScheduleResponse(BaseModel):
    """Schema for schedule response."""
    id: int
    name: str
    cron_expression: str
    with_image: bool
    enabled: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Config schemas
class ConfigItem(BaseModel):
    """Schema for config item."""
    key: str
    value: str


class ConfigUpdate(BaseModel):
    """Schema for updating config."""
    value: str


class ConfigResponse(BaseModel):
    """Schema for config response."""
    key: str
    value: str
    updated_at: datetime

    class Config:
        from_attributes = True


# Notion schemas
class NotionCacheResponse(BaseModel):
    """Schema for Notion cache response."""
    id: int
    content: str
    fetched_at: datetime

    class Config:
        from_attributes = True


# Reply schemas
class ReplyRequest(BaseModel):
    """Schema for reply generation request."""
    keyword: Optional[str] = None
    num_posts: int = Field(default=5, ge=1, le=20)


# Health check schema
class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    timestamp: datetime
    database: str
    scheduler: str


# Error response schema
class ErrorResponse(BaseModel):
    """Schema for error response."""
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
