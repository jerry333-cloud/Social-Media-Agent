"""Main CLI application for Social Media Agent."""

import typer
from typing_extensions import Annotated
from rich.console import Console

from .post_generator import PostGenerator
from .reply_generator import ReplyGenerator

app = typer.Typer(
    name="social-media-agent",
    help="Social media agent for Notion, OpenRouter, and Mastodon integration",
    add_completion=False
)

console = Console()


@app.command()
def create_post(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Test without actually posting to Mastodon")
    ] = False
):
    """
    Create and publish a social media post from Notion content.
    
    This will:
    1. Fetch the latest unposted content from your Notion database
    2. Generate a social media post using AI
    3. Show you the post for review and editing
    4. Publish to Mastodon with an AI-generated label
    5. Update the Notion database status
    """
    try:
        generator = PostGenerator()
        success = generator.create_and_publish_post(dry_run=dry_run)
        
        if not success:
            raise typer.Exit(code=1)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def reply_to_posts(
    count: Annotated[
        int,
        typer.Option("--count", "-c", help="Number of posts to find and reply to")
    ] = 5,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Test without actually posting replies")
    ] = False
):
    """
    Find and reply to keyword-related posts on Mastodon.
    
    This will:
    1. Search Mastodon for posts containing your keywords (from .env)
    2. Generate contextual replies for all found posts
    3. Show you all replies in a table for review
    4. Post approved replies
    """
    if count < 1:
        console.print("[red]Error: Count must be at least 1[/red]")
        raise typer.Exit(code=1)
    
    if count > 20:
        console.print("[yellow]Warning: Count limited to 20 posts maximum[/yellow]")
        count = 20
    
    try:
        generator = ReplyGenerator()
        success = generator.find_and_reply_to_posts(count=count, dry_run=dry_run)
        
        if not success:
            raise typer.Exit(code=1)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show the version of the social media agent."""
    from . import __version__
    console.print(f"Social Media Agent v{__version__}")


if __name__ == "__main__":
    app()
