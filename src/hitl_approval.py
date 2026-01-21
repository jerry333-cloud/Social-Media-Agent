"""Human-in-the-Loop approval loop with Telegram."""

import asyncio
from typing import Optional, Tuple
from dataclasses import dataclass, field
from rich.console import Console

from .telegram_client import TelegramClient
from .llm_client import LLMClient
from .image_client import ImageClient
from .models import NotionContent

console = Console()


@dataclass
class ApprovalState:
    """State for the HITL approval loop."""
    
    notion_content: NotionContent
    current_text: str
    current_image_path: Optional[str]
    iteration: int = 1
    feedback_history: list = field(default_factory=list)
    image_prompts_tried: list = field(default_factory=list)


class HITLApprovalLoop:
    """Manages the Human-in-the-Loop approval workflow via Telegram."""
    
    def __init__(self):
        """Initialize clients."""
        try:
            self.telegram_client = TelegramClient()
        except ValueError as e:
            raise ValueError(f"Telegram not configured: {e}")
        
        self.llm_client = LLMClient()
        
        try:
            self.image_client = ImageClient()
        except ValueError:
            self.image_client = None
    
    async def run_approval_loop(
        self,
        notion_content: NotionContent,
        initial_text: str,
        initial_image_path: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Run the approval loop until user approves or cancels.
        
        Args:
            notion_content: The source Notion content
            initial_text: Initial generated text
            initial_image_path: Initial generated image path
            
        Returns:
            Tuple of (final_text, final_image_path) or (None, None) if cancelled
        """
        state = ApprovalState(
            notion_content=notion_content,
            current_text=initial_text,
            current_image_path=initial_image_path
        )
        
        console.print("\n[bold cyan]Starting Telegram HITL Approval Loop[/bold cyan]\n")
        
        while True:
            # Send to Telegram for approval
            await self.telegram_client.send_post_for_approval(
                text=state.current_text,
                image_path=state.current_image_path,
                iteration=state.iteration
            )
            
            # Wait for user decision
            action = await self.telegram_client.wait_for_button_response()
            
            console.print(f"[yellow]User action: {action}[/yellow]")
            
            if action == "approve":
                console.print("[green]Post approved! Proceeding to publish...[/green]")
                return state.current_text, state.current_image_path
            
            elif action == "cancel":
                console.print("[yellow]Post cancelled by user[/yellow]")
                await self.telegram_client.send_cancellation_message()
                return None, None
            
            elif action == "edit_text":
                # Get edited text from user
                new_text = await self.telegram_client.ask_for_text(
                    "Send me your edited text:"
                )
                state.current_text = new_text
                state.feedback_history.append(f"User edited text directly (iteration {state.iteration})")
                state.iteration += 1
            
            elif action == "regen_text":
                # Get feedback and regenerate text
                feedback = await self.telegram_client.ask_for_feedback(
                    "What would you like to change about the text?"
                )
                
                console.print(f"[cyan]Regenerating text with feedback: {feedback}[/cyan]")
                
                new_text = self.llm_client.generate_post(
                    content=f"{notion_content.title}\n\n{notion_content.content}",
                    feedback=feedback,
                    previous_attempt=state.current_text
                )
                
                state.current_text = new_text
                state.feedback_history.append(f"Text regen: {feedback}")
                state.iteration += 1
            
            elif action == "regen_image":
                if not self.image_client:
                    await self.telegram_client.bot.send_message(
                        chat_id=self.telegram_client.chat_id,
                        text="Image generation not configured. Skipping..."
                    )
                    continue
                
                # Get feedback and regenerate image
                feedback = await self.telegram_client.ask_for_feedback(
                    "What would you like to change about the image?"
                )
                
                console.print(f"[cyan]Regenerating image with feedback: {feedback}[/cyan]")
                
                # Generate new image with feedback
                image_prompt = self.image_client.extract_image_prompt_from_text(
                    f"{notion_content.title}. {state.current_text}"
                )
                
                # Incorporate feedback
                modified_prompt = f"{image_prompt}. {feedback}"
                
                new_image_path = self.image_client.generate_image(
                    prompt=modified_prompt,
                    include_trigger=True
                )
                
                if new_image_path:
                    state.current_image_path = new_image_path
                    state.image_prompts_tried.append(modified_prompt)
                    state.feedback_history.append(f"Image regen: {feedback}")
                
                state.iteration += 1
            
            elif action == "regen_both":
                # Get feedback and regenerate both
                feedback = await self.telegram_client.ask_for_feedback(
                    "What would you like to change? (applies to both text and image)"
                )
                
                console.print(f"[cyan]Regenerating both with feedback: {feedback}[/cyan]")
                
                # Regenerate text
                new_text = self.llm_client.generate_post(
                    content=f"{notion_content.title}\n\n{notion_content.content}",
                    feedback=feedback,
                    previous_attempt=state.current_text
                )
                state.current_text = new_text
                
                # Regenerate image
                if self.image_client:
                    image_prompt = self.image_client.extract_image_prompt_from_text(
                        f"{notion_content.title}. {new_text}"
                    )
                    modified_prompt = f"{image_prompt}. {feedback}"
                    
                    new_image_path = self.image_client.generate_image(
                        prompt=modified_prompt,
                        include_trigger=True
                    )
                    
                    if new_image_path:
                        state.current_image_path = new_image_path
                        state.image_prompts_tried.append(modified_prompt)
                
                state.feedback_history.append(f"Both regen: {feedback}")
                state.iteration += 1
            
            # Continue loop
            console.print(f"[dim]Iteration {state.iteration} complete. Showing new preview...[/dim]\n")
