"""OpenRouter LLM client wrapper using Nvidia Nemotron."""

import os
import json
from typing import Optional, Type, TypeVar
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
from rich.console import Console

load_dotenv()

console = Console()

T = TypeVar('T', bound=BaseModel)


class LLMClient:
    """Wrapper for OpenRouter API."""
    
    # Using Nvidia Nemotron model
    # Previous attempts:
    # - meta-llama/llama-3.1-8b-instruct:free (404 not found)
    # - google/gemini-2.0-flash-exp (429 rate limited)
    MODEL = "nvidia/nemotron-3-nano-30b-a3b"
    
    def __init__(self):
        """Initialize the OpenRouter client with API key from environment."""
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        
        # OpenRouter is compatible with OpenAI's API
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )
    
    def generate_post(
        self,
        content: str,
        feedback: Optional[str] = None,
        previous_attempt: Optional[str] = None
    ) -> str:
        """
        Generate a social media post from content with optional feedback.
        
        Args:
            content: The source content to create a post from
            feedback: Optional feedback for improvement
            previous_attempt: Previous version to improve upon
            
        Returns:
            Generated social media post text
        """
        if feedback and previous_attempt:
            prompt = f"""You are a social media expert. Improve the following social media post based on user feedback.

Original Content:
{content}

Previous Post:
{previous_attempt}

User Feedback:
{feedback}

Requirements:
- Address the user's feedback
- Keep it concise and engaging (suitable for Mastodon, under 500 characters)
- Use a professional yet friendly tone
- Include 2-3 relevant hashtags
- Make it shareable and interesting

Generate the improved post:"""
        else:
            prompt = f"""You are a social media expert. Create an engaging social media post based on the following content.

Content:
{content}

Requirements:
- Keep it concise and engaging (suitable for Mastodon, under 500 characters)
- Use a professional yet friendly tone
- Include 2-3 relevant hashtags
- Make it shareable and interesting

Generate the post:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional social media content creator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000  # Increased for better generation with RAG context
            )
            
            result = response.choices[0].message.content.strip()
            return result
        
        except Exception as e:
            console.print(f"[red]Error generating post: {e}[/red]")
            raise
    
    def generate_structured_post(self, content: str, model_class: Type[T]) -> T:
        """
        Generate a structured social media post using Pydantic model.
        
        Args:
            content: The source content to create a post from
            model_class: The Pydantic model class to use for structured output
            
        Returns:
            Instance of the Pydantic model with generated data
        """
        prompt = f"""Create a social media post based on the following content.

Content:
{content}

Generate a structured post with content and hashtags."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional social media content creator. Always respond with valid JSON only, no other text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract JSON from response (handle cases where model wraps it in markdown)
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            json_response = json.loads(content)
            return model_class.model_validate(json_response)
        
        except Exception as e:
            console.print(f"[red]Error generating structured post: {e}[/red]")
            raise
    
    def generate_reply_single(self, post: dict, keywords: list[str]) -> dict:
        """
        Generate a single reply for one post.
        
        Args:
            post: Post to reply to (with 'id', 'content', 'author')
            keywords: Keywords related to this post
            
        Returns:
            Reply dict with post_id, reply_text, and tone
        """
        prompt = f"""Generate a brief, friendly reply to this social media post.

Post by @{post['author']}:
{post.get('plain_content', post['content'])[:300]}

Create a SHORT reply (max 200 characters) that:
- Is relevant and adds value
- Is friendly and professional
- Relates to keywords: {', '.join(keywords)}

Just write the reply text, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful, friendly social media user."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            reply_text = response.choices[0].message.content.strip()
            
            # Remove quotes if the model wrapped the reply
            if reply_text.startswith('"') and reply_text.endswith('"'):
                reply_text = reply_text[1:-1]
            if reply_text.startswith("'") and reply_text.endswith("'"):
                reply_text = reply_text[1:-1]
            
            return {
                "post_id": post["id"],
                "reply_text": reply_text[:280],  # Ensure it fits in Mastodon limit
                "tone": "friendly"
            }
        except Exception as e:
            console.print(f"[red]Error generating reply for post {post['id']}: {e}[/red]")
            return None
    
    def generate_replies(self, posts: list[dict], keywords: list[str]) -> list[dict]:
        """
        Generate replies for multiple posts (tries batch, falls back to individual).
        
        Args:
            posts: List of posts to reply to (each with 'id', 'content', 'author')
            keywords: Keywords that were used to find these posts
            
        Returns:
            List of replies with post_id, reply_text, and tone
        """
        posts_info = "\n\n".join([
            f"Post ID: {post['id']}\nAuthor: {post['author']}\nContent: {post['content']}"
            for post in posts
        ])
        
        prompt = f"""You are replying to social media posts related to: {', '.join(keywords)}

Posts to reply to:
{posts_info}

Generate SHORT, engaging replies for each post. IMPORTANT: Keep each reply under 150 characters.

Each reply must:
- Be BRIEF (max 150 chars)
- Be relevant and friendly
- Add value

Respond with ONLY valid JSON in this exact format:
{{
  "replies": [
    {{"post_id": "123", "reply_text": "Short reply here", "tone": "friendly"}}
  ]
}}

Generate replies for ALL posts above."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful social media assistant. Always respond with valid JSON only, no other text. Keep replies brief."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2500  # Increased to avoid truncation
            )
            
            # Extract JSON from response (handle cases where model wraps it in markdown)
            content = response.choices[0].message.content
            
            if not content or not content.strip():
                console.print("[red]Model returned empty response[/red]")
                return []
            
            content = content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
            
            # Try to find JSON in the response
            if not content.startswith("{") and not content.startswith("["):
                # Try to extract JSON from text
                import re
                json_match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                else:
                    console.print(f"[yellow]Could not find JSON in response. Response: {content[:200]}...[/yellow]")
                    return []
            
            json_response = json.loads(content)
            return json_response.get("replies", [])
        
        except json.JSONDecodeError as e:
            console.print(f"[yellow]JSON parsing failed, trying individual replies...[/yellow]")
            # Fallback: generate replies one at a time
            replies = []
            for post in posts:
                reply = self.generate_reply_single(post, keywords)
                if reply:
                    replies.append(reply)
            return replies
        
        except Exception as e:
            console.print(f"[yellow]Batch generation failed: {e}[/yellow]")
            console.print(f"[yellow]Falling back to individual reply generation...[/yellow]")
            # Fallback: generate replies one at a time
            replies = []
            for post in posts:
                reply = self.generate_reply_single(post, keywords)
                if reply:
                    replies.append(reply)
            return replies
