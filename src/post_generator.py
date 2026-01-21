"""Post generation with user review and editing."""

import tempfile
import subprocess
import os
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .notion_client import NotionClientWrapper
from .llm_client import LLMClient
from .mastodon_client import MastodonClient
from .image_client import ImageClient

console = Console()


class PostGenerator:
    """Handles the full post generation workflow."""
    
    def __init__(self):
        """Initialize all required clients."""
        self.notion_client = NotionClientWrapper()
        self.llm_client = LLMClient()
        self.mastodon_client = MastodonClient()
        try:
            self.image_client = ImageClient()
        except ValueError:
            self.image_client = None  # No Replicate token configured
    
    def create_and_publish_post(
        self,
        dry_run: bool = False,
        with_image: bool = False,
        use_telegram: bool = False
    ) -> bool:
        """
        Full workflow: Fetch from Notion → Generate → Review → Publish.
        
        Args:
            dry_run: If True, don't actually post to Mastodon
            with_image: If True, generate an image for the post
            use_telegram: If True, use Telegram for HITL approval
            
        Returns:
            True if successful, False otherwise
        """
        console.print("\n[bold cyan]Social Media Post Generator[/bold cyan]\n")
        
        # Step 1: Fetch content from Notion
        console.print("[bold]Step 1:[/bold] Fetching content from Notion...")
        notion_content = self.notion_client.get_content()
        
        if not notion_content:
            console.print("[red]Could not fetch content from Notion.[/red]")
            return False
        
        console.print(f"[green]✓ Found:[/green] {notion_content.title}")
        
        # Show source content
        console.print("\n[bold]Source Content:[/bold]")
        console.print(Panel(
            f"[bold]{notion_content.title}[/bold]\n\n{notion_content.content[:500]}...",
            border_style="blue"
        ))
        
        # Step 2: Generate post using LLM
        console.print("\n[bold]Step 2:[/bold] Generating social media post...")
        
        # Combine title and content for better context
        full_content = f"{notion_content.title}\n\n{notion_content.content}"
        generated_post = self.llm_client.generate_post(full_content)
        
        console.print("[green]✓ Post generated![/green]")
        
        # Step 3: Generate image (optional)
        image_path = None
        if with_image:
            image_path = self._generate_post_image(notion_content, generated_post)
        
        # Step 4: Review and edit (Telegram or CLI)
        if use_telegram:
            final_post, image_path = self._telegram_approval(
                notion_content,
                generated_post,
                image_path
            )
        else:
            final_post = self._review_and_edit(generated_post, image_path)
        
        if not final_post:
            console.print("[yellow]Post creation cancelled.[/yellow]")
            return False
        
        # Step 5: Publish to Mastodon
        console.print("\n[bold]Step 5:[/bold] Publishing to Mastodon...")
        
        status = self.mastodon_client.post_status(
            final_post,
            add_ai_label=True,
            dry_run=dry_run,
            media_path=image_path
        )
        
        if not dry_run and status:
            # Step 6: Add comment to Notion (optional tracking)
            console.print("\n[bold]Step 5:[/bold] Adding comment to Notion...")
            post_url = status.get('url', 'N/A')
            comment = f"Posted to Mastodon: {post_url}"
            if self.notion_client.add_comment(notion_content.id, comment):
                console.print("[green]✓ Comment added to Notion[/green]")
            
            console.print(f"\n[bold green]✨ Success![/bold green] Post published at: {post_url}")
        
        return True
    
    def _generate_post_image(self, notion_content, post_text: str) -> Optional[str]:
        """
        Generate an image for the post.
        
        Args:
            notion_content: Notion content object
            post_text: Generated post text
            
        Returns:
            Path to generated image, or None if failed/disabled
        """
        if not self.image_client:
            console.print("[yellow]⚠ Image generation skipped (no Replicate token)[/yellow]")
            return None
        
        console.print("\n[bold]Step 3:[/bold] Generating image...")
        
        # Extract image prompt from content
        image_prompt = self.image_client.extract_image_prompt_from_text(
            f"{notion_content.title}. {post_text}"
        )
        
        console.print(f"[dim]Image prompt: {image_prompt}[/dim]")
        
        # Generate image
        image_path = self.image_client.generate_image(
            prompt=image_prompt,
            include_trigger=True
        )
        
        if image_path:
            console.print(f"[green]✓ Image generated successfully![/green]")
        else:
            console.print("[yellow]⚠ Image generation failed, continuing without image[/yellow]")
        
        return image_path
    
    def _telegram_approval(
        self,
        notion_content,
        generated_post: str,
        image_path: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Use Telegram for HITL approval.
        
        Args:
            notion_content: Notion content object
            generated_post: Generated post text
            image_path: Path to generated image
            
        Returns:
            Tuple of (final_post, final_image_path) or (None, None) if cancelled
        """
        import asyncio
        from .hitl_approval import HITLApprovalLoop
        
        try:
            loop = HITLApprovalLoop()
            final_post, final_image = asyncio.run(
                loop.run_approval_loop(
                    notion_content=notion_content,
                    initial_text=generated_post,
                    initial_image_path=image_path
                )
            )
            return final_post, final_image
        except ValueError as e:
            console.print(f"[red]Telegram not configured: {e}[/red]")
            console.print("[yellow]Falling back to CLI approval...[/yellow]")
            return self._review_and_edit(generated_post, image_path), image_path
    
    def _review_and_edit(self, generated_post: str, image_path: Optional[str] = None) -> Optional[str]:
        """
        Show the generated post and allow user to review/edit it.
        
        Args:
            generated_post: The AI-generated post text
            image_path: Optional path to generated image
            
        Returns:
            Final post text or None if cancelled
        """
        step_num = "4" if image_path else "3"
        console.print(f"\n[bold]Step {step_num}:[/bold] Review and Edit")
        
        current_post = generated_post
        
        while True:
            # Show the current post
            console.print("\n[bold]Generated Post:[/bold]")
            console.print(Panel(current_post, border_style="green"))
            console.print(f"[dim]Character count: {len(current_post)}[/dim]")
            
            if image_path:
                console.print(f"[cyan]📷 Image:[/cyan] {image_path}")
                console.print(f"[dim]Preview: file:///{image_path}[/dim]")
            
            console.print()
            
            # Ask what to do
            console.print("[bold]Options:[/bold]")
            console.print("  [green]1.[/green] Accept and publish")
            console.print("  [yellow]2.[/yellow] Edit in text editor")
            console.print("  [cyan]3.[/cyan] Edit inline")
            console.print("  [red]4.[/red] Cancel")
            
            choice = Prompt.ask(
                "\nWhat would you like to do?",
                choices=["1", "2", "3", "4"],
                default="1"
            )
            
            if choice == "1":
                # Accept
                return current_post
            
            elif choice == "2":
                # Edit in external editor
                edited = self._edit_in_editor(current_post)
                if edited:
                    current_post = edited
            
            elif choice == "3":
                # Edit inline
                console.print("\n[yellow]Enter your edited post (press Enter twice to finish):[/yellow]")
                lines = []
                empty_line_count = 0
                
                while True:
                    line = input()
                    if line == "":
                        empty_line_count += 1
                        if empty_line_count >= 2:
                            break
                        lines.append(line)
                    else:
                        empty_line_count = 0
                        lines.append(line)
                
                # Remove trailing empty lines
                while lines and lines[-1] == "":
                    lines.pop()
                
                if lines:
                    current_post = "\n".join(lines)
            
            elif choice == "4":
                # Cancel
                if Confirm.ask("Are you sure you want to cancel?"):
                    return None
    
    def _edit_in_editor(self, text: str) -> Optional[str]:
        """
        Open text in an external editor for editing.
        
        Args:
            text: The text to edit
            
        Returns:
            Edited text or None if unchanged/error
        """
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text)
            temp_path = f.name
        
        try:
            # Try to use the user's preferred editor
            editor = os.environ.get('EDITOR', 'notepad' if os.name == 'nt' else 'nano')
            
            console.print(f"[dim]Opening {editor}...[/dim]")
            subprocess.run([editor, temp_path], check=True)
            
            # Read the edited content
            with open(temp_path, 'r') as f:
                edited_text = f.read()
            
            return edited_text if edited_text != text else None
        
        except Exception as e:
            console.print(f"[red]Error opening editor: {e}[/red]")
            return None
        
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
