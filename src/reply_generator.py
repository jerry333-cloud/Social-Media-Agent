"""Reply generation with keyword search and batch processing."""

import os
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich.panel import Panel
from dotenv import load_dotenv

from .llm_client import LLMClient
from .mastodon_client import MastodonClient

load_dotenv()

console = Console()


class ReplyGenerator:
    """Handles finding posts and generating replies."""
    
    def __init__(self):
        """Initialize required clients."""
        self.llm_client = LLMClient()
        self.mastodon_client = MastodonClient()
        
        # Load keywords from environment
        keywords_str = os.getenv("MASTODON_KEYWORDS", "")
        self.keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
        
        if not self.keywords:
            raise ValueError("MASTODON_KEYWORDS not found in environment variables")
    
    def find_and_reply_to_posts(self, count: int = 5, dry_run: bool = False) -> bool:
        """
        Find keyword-related posts and generate/post replies.
        
        Args:
            count: Number of posts to find and reply to
            dry_run: If True, don't actually post replies
            
        Returns:
            True if successful, False otherwise
        """
        console.print("\n[bold cyan]🤖 Social Media Reply Generator[/bold cyan]\n")
        
        # Step 1: Search for posts
        console.print(f"[bold]Step 1:[/bold] Searching for posts with keywords: {', '.join(self.keywords)}")
        
        posts = self.mastodon_client.search_posts(self.keywords, limit=count)
        
        if not posts:
            console.print("[yellow]No posts found matching your keywords.[/yellow]")
            return False
        
        console.print(f"[green]✓ Found {len(posts)} posts[/green]\n")
        
        # Show found posts
        self._display_posts(posts)
        
        if not Confirm.ask("\n[bold]Continue to generate replies?[/bold]", default=True):
            console.print("[yellow]Cancelled.[/yellow]")
            return False
        
        # Step 2: Generate replies using LLM
        console.print("\n[bold]Step 2:[/bold] Generating replies...")
        
        replies = self.llm_client.generate_replies(posts, self.keywords)
        
        if not replies:
            console.print("[red]Failed to generate replies.[/red]")
            return False
        
        console.print(f"[green]✓ Generated {len(replies)} replies[/green]\n")
        
        # Step 3: Review replies
        approved_replies = self._review_replies(posts, replies)
        
        if not approved_replies:
            console.print("[yellow]No replies approved.[/yellow]")
            return False
        
        # Step 4: Post replies
        console.print(f"\n[bold]Step 4:[/bold] Posting {len(approved_replies)} replies...")
        
        success_count = 0
        for reply in approved_replies:
            try:
                self.mastodon_client.reply_to_post(
                    reply["post_id"],
                    reply["reply_text"],
                    dry_run=dry_run
                )
                success_count += 1
            except Exception as e:
                console.print(f"[red]Failed to post reply: {e}[/red]")
        
        console.print(f"\n[bold green]✨ Success![/bold green] Posted {success_count} out of {len(approved_replies)} replies")
        return True
    
    def _display_posts(self, posts: List[Dict]):
        """Display found posts in a table."""
        table = Table(title="Found Posts", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Author", style="cyan")
        table.add_column("Content Preview", style="white")
        
        for idx, post in enumerate(posts, 1):
            content_preview = post["plain_content"][:80] + "..." if len(post["plain_content"]) > 80 else post["plain_content"]
            table.add_row(
                str(idx),
                post["author"],
                content_preview
            )
        
        console.print(table)
    
    def _review_replies(self, posts: List[Dict], replies: List[Dict]) -> List[Dict]:
        """
        Show all generated replies and let user approve/reject each one.
        
        Args:
            posts: Original posts
            replies: Generated replies
            
        Returns:
            List of approved replies
        """
        console.print("[bold]Step 3:[/bold] Review Replies\n")
        
        # Create a map of post IDs to posts for easy lookup
        post_map = {post["id"]: post for post in posts}
        
        approved_replies = []
        
        for idx, reply in enumerate(replies, 1):
            post_id = str(reply["post_id"])
            post = post_map.get(post_id)
            
            if not post:
                console.print(f"[yellow]Warning: Reply {idx} references unknown post {post_id}[/yellow]")
                continue
            
            # Show original post and reply
            console.print(f"\n[bold cyan]Reply {idx} of {len(replies)}[/bold cyan]")
            
            console.print("\n[bold]Original Post:[/bold]")
            console.print(Panel(
                f"[cyan]@{post['author']}[/cyan]\n\n{post['plain_content'][:200]}...",
                border_style="blue"
            ))
            
            console.print("\n[bold]Generated Reply:[/bold]")
            console.print(Panel(
                f"{reply['reply_text']}\n\n[dim]Tone: {reply.get('tone', 'N/A')}[/dim]",
                border_style="green"
            ))
            
            # Ask for approval
            if Confirm.ask("[bold]Approve this reply?[/bold]", default=True):
                approved_replies.append(reply)
                console.print("[green]✓ Approved[/green]")
            else:
                console.print("[yellow]✗ Skipped[/yellow]")
        
        console.print(f"\n[bold]Summary:[/bold] {len(approved_replies)} out of {len(replies)} replies approved")
        
        return approved_replies
