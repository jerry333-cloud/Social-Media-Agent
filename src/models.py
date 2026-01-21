"""Pydantic models for structured outputs."""

from pydantic import BaseModel, Field
from typing import List


class SocialMediaPost(BaseModel):
    """Model for a generated social media post."""
    
    content: str = Field(
        description="The main text content of the social media post"
    )
    hashtags: List[str] = Field(
        default_factory=list,
        description="List of relevant hashtags for the post"
    )


class Reply(BaseModel):
    """Model for a single reply to a post."""
    
    post_id: str = Field(
        description="The ID of the post being replied to"
    )
    reply_text: str = Field(
        description="The text content of the reply"
    )
    tone: str = Field(
        description="The tone of the reply (e.g., professional, friendly, informative)"
    )


class ReplyBatch(BaseModel):
    """Model for a batch of replies."""
    
    replies: List[Reply] = Field(
        description="List of replies to various posts"
    )


class NotionContent(BaseModel):
    """Model for content fetched from Notion."""
    
    id: str = Field(
        description="The Notion page ID"
    )
    title: str = Field(
        description="The title of the Notion page"
    )
    content: str = Field(
        description="The main content/body text"
    )
    properties: dict = Field(
        default_factory=dict,
        description="Additional properties from the Notion page"
    )
