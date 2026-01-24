"""Main CLI application for Social Media Agent."""

import typer
from typing_extensions import Annotated
from rich.console import Console

from .post_generator import PostGenerator
from .reply_generator import ReplyGenerator
from .image_client import ImageClient

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
    ] = False,
    with_image: Annotated[
        bool,
        typer.Option("--with-image", help="Generate an image for the post using FLUX")
    ] = False,
    telegram: Annotated[
        bool,
        typer.Option("--telegram", help="Use Telegram for Human-in-the-Loop approval")
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
    import asyncio
    
    try:
        generator = PostGenerator()
        success = asyncio.run(generator.create_and_publish_post(
            dry_run=dry_run,
            with_image=with_image,
            use_telegram=telegram
        ))
        
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
def generate_image(
    prompt: Annotated[
        str,
        typer.Argument(help="Prompt for image generation")
    ],
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output file path")
    ] = None,
    steps: Annotated[
        int,
        typer.Option("--steps", help="Number of inference steps")
    ] = 28,
    width: Annotated[
        int,
        typer.Option("--width", help="Image width")
    ] = 1024,
    height: Annotated[
        int,
        typer.Option("--height", help="Image height")
    ] = 1024
):
    """
    Generate an image using FLUX model.
    
    This generates an image from your prompt using your trained FLUX model
    (or the base model if not trained yet).
    """
    try:
        image_client = ImageClient()
        
        image_path = image_client.generate_image(
            prompt=prompt,
            include_trigger=True,
            num_inference_steps=steps,
            width=width,
            height=height
        )
        
        if image_path:
            if output:
                # Copy to specified output path
                import shutil
                shutil.copy2(image_path, output)
                console.print(f"[green]✓ Image saved to:[/green] {output}")
            else:
                console.print(f"[green]✓ Image generated:[/green] {image_path}")
            
            console.print(f"\n[dim]Open with: start {image_path if not output else output}[/dim]")
        else:
            console.print("[red]Failed to generate image[/red]")
            raise typer.Exit(code=1)
    
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Make sure REPLICATE_API_TOKEN is set in .env[/yellow]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def train_model(
    dataset: Annotated[
        str,
        typer.Option("--dataset", help="Path to dataset zip file")
    ] = "data.zip",
    trigger: Annotated[
        str,
        typer.Option("--trigger", help="Trigger word for the model")
    ] = "TANGO",
    steps: Annotated[
        int,
        typer.Option("--steps", help="Training steps")
    ] = 1500,
    username: Annotated[
        str,
        typer.Option("--username", help="Replicate username")
    ] = "sundai-club",
    model_name: Annotated[
        str,
        typer.Option("--model-name", help="Model name")
    ] = "presence"
):
    """
    Train a FLUX model on Replicate with your custom dataset.
    
    This uploads your data.zip and trains a custom FLUX model.
    Training takes 10-30 minutes.
    """
    import sys
    from pathlib import Path
    
    # Import the training script
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from train_flux_model import train_flux_model
    
    success = train_flux_model(
        dataset_path=dataset,
        trigger_word=trigger,
        steps=steps,
        replicate_username=username,
        model_name=model_name
    )
    
    if not success:
        raise typer.Exit(code=1)


@app.command()
def telegram_post(
    with_image: Annotated[
        bool,
        typer.Option("--with-image", help="Generate an image for the post")
    ] = True,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Test without actually posting")
    ] = False
):
    """
    Create and publish a post using Telegram for approval.
    
    This command automatically uses Telegram for Human-in-the-Loop approval,
    allowing you to review, edit, and regenerate the post from your phone
    until you're satisfied with the result.
    """
    try:
        generator = PostGenerator()
        success = generator.create_and_publish_post(
            dry_run=dry_run,
            with_image=with_image,
            use_telegram=True
        )
        
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
