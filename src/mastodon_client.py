"""Mastodon API client wrapper."""

import os
from typing import List, Dict, Optional
from mastodon import Mastodon
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()


class MastodonClient:
    """Wrapper for Mastodon API interactions."""
    
    def __init__(self):
        """Initialize the Mastodon client with credentials from environment."""
        self.instance_url = os.getenv("MASTODON_INSTANCE_URL")
        self.access_token = os.getenv("MASTODON_ACCESS_TOKEN")
        self.ai_label = os.getenv("AI_LABEL", "#AIGenerated")
        
        if not self.instance_url:
            raise ValueError("MASTODON_INSTANCE_URL not found in environment variables")
        if not self.access_token:
            raise ValueError("MASTODON_ACCESS_TOKEN not found in environment variables")
        
        # Initialize Mastodon client
        self.client = Mastodon(
            access_token=self.access_token,
            api_base_url=self.instance_url
        )
    
    def post_status(
        self,
        content: str,
        add_ai_label: bool = True,
        dry_run: bool = False,
        media_path: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Post a status to Mastodon with optional media attachment.
        
        Args:
            content: The content to post
            add_ai_label: Whether to add the AI-generated label
            dry_run: If True, don't actually post
            media_path: Optional path to image file to attach
            
        Returns:
            The posted status object or None if dry_run
        """
        # Add AI label if requested
        if add_ai_label and self.ai_label:
            # Add label with proper spacing
            if not content.endswith('\n'):
                content += '\n\n'
            else:
                content += '\n'
            content += self.ai_label
        
        if dry_run:
            console.print("[yellow]DRY RUN - Would post:[/yellow]")
            console.print(f"[dim]{content}[/dim]")
            if media_path:
                console.print(f"[yellow]With image:[/yellow] {media_path}")
            return None
        
        try:
            media_ids = None
            
            # Upload media if provided
            if media_path:
                media_ids = self._upload_media(media_path)
            
            # Post status
            status = self.client.status_post(content, media_ids=media_ids)
            console.print("[green]✓ Posted to Mastodon successfully![/green]")
            if media_path:
                console.print("[green]✓ Image attached![/green]")
            return status
        
        except Exception as e:
            console.print(f"[red]Error posting to Mastodon: {e}[/red]")
            raise
    
    def search_posts(self, keywords: List[str], limit: int = 20) -> List[Dict]:
        """
        Search for posts containing specific keywords.
        
        Args:
            keywords: List of keywords to search for
            limit: Maximum number of posts to return
            
        Returns:
            List of post dictionaries with id, content, author, url
        """
        posts = []
        
        try:
            for keyword in keywords:
                # Search for the keyword (search_v2 doesn't accept limit parameter)
                results = self.client.search_v2(
                    q=keyword,
                    result_type="statuses"
                )
                
                for status in results["statuses"]:
                    # Skip our own posts
                    try:
                        if status["account"]["id"] == self.client.me()["id"]:
                            continue
                    except:
                        pass  # Continue if we can't check account
                    
                    posts.append({
                        "id": status["id"],
                        "content": status["content"],
                        "author": status["account"]["username"],
                        "url": status["url"],
                        "plain_content": self._strip_html(status["content"])
                    })
                    
                    if len(posts) >= limit:
                        break
                
                if len(posts) >= limit:
                    break
            
            return posts[:limit]
        
        except Exception as e:
            console.print(f"[red]Error searching Mastodon: {e}[/red]")
            raise
    
    def reply_to_post(self, post_id: str, reply_text: str, dry_run: bool = False) -> Optional[Dict]:
        """
        Reply to a specific post.
        
        Args:
            post_id: The ID of the post to reply to
            reply_text: The text of the reply
            dry_run: If True, don't actually post
            
        Returns:
            The reply status object or None if dry_run
        """
        if dry_run:
            console.print(f"[yellow]DRY RUN - Would reply to {post_id}:[/yellow]")
            console.print(f"[dim]{reply_text}[/dim]")
            return None
        
        try:
            status = self.client.status_post(
                reply_text,
                in_reply_to_id=post_id
            )
            console.print(f"[green]✓ Replied to post {post_id}[/green]")
            return status
        
        except Exception as e:
            console.print(f"[red]Error replying to post {post_id}: {e}[/red]")
            raise
    
    def _upload_media(self, media_path: str, description: str = None) -> List[Dict]:
        """
        Upload media file to Mastodon.
        
        Args:
            media_path: Path to the media file
            description: Optional alt text description
            
        Returns:
            List of media IDs
        """
        try:
            import os
            if not os.path.exists(media_path):
                console.print(f"[red]Media file not found: {media_path}[/red]")
                return None
            
            console.print(f"[yellow]Uploading image...[/yellow]")
            media = self.client.media_post(media_path, description=description)
            console.print(f"[green]✓ Image uploaded[/green]")
            return [media["id"]]
        
        except Exception as e:
            console.print(f"[red]Error uploading media: {e}[/red]")
            return None
    
    def _strip_html(self, html_content: str) -> str:
        """Remove HTML tags from content."""
        import re
        # Simple HTML tag removal
        clean = re.sub('<.*?>', '', html_content)
        # Decode HTML entities
        clean = clean.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return clean.strip()
