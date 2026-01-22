"""Telegram bot client for Human-in-the-Loop approval."""

import os
import asyncio
from typing import Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update, InputFile
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from rich.console import Console

load_dotenv()

console = Console()


class TelegramClient:
    """Wrapper for Telegram bot interactions."""
    
    def __init__(self):
        """Initialize the Telegram client with credentials from environment."""
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID not found in environment variables")
        
        self.chat_id = int(self.chat_id)
        self.bot = Bot(token=self.bot_token)
        
        # State for waiting for responses
        self.waiting_for_text = False
        self.waiting_for_feedback = False
        self.received_text = None
        self.received_feedback = None
        self.response_event = asyncio.Event()
    
    async def send_post_for_approval(
        self,
        text: str,
        image_path: Optional[str] = None,
        iteration: int = 1
    ) -> str:
        """
        Send a post with image to Telegram for approval.
        
        Args:
            text: The post text
            image_path: Optional path to image
            iteration: Iteration number
            
        Returns:
            The action chosen by user
        """
        # Create keyboard with approval options
        keyboard = [
            [InlineKeyboardButton("Approve & Post", callback_data="approve")],
            [
                InlineKeyboardButton("Edit Text", callback_data="edit_text"),
                InlineKeyboardButton("Regen Image", callback_data="regen_image")
            ],
            [
                InlineKeyboardButton("Regen Text", callback_data="regen_text"),
                InlineKeyboardButton("Regen Both", callback_data="regen_both")
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = f"Post Preview (Iteration {iteration})\n\n{text}\n\nCharacters: {len(text)}"
        
        try:
            # Send with image if provided
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    await self.bot.send_photo(
                        chat_id=self.chat_id,
                        photo=photo,
                        caption=caption[:1024],  # Telegram caption limit
                        reply_markup=reply_markup
                    )
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=caption,
                    reply_markup=reply_markup
                )
            
            console.print("[cyan]Sent to Telegram. Waiting for approval...[/cyan]")
            
        except Exception as e:
            console.print(f"[red]Error sending to Telegram: {e}[/red]")
            raise
    
    async def wait_for_button_response(self) -> str:
        """
        Wait for user to click a button.
        
        Returns:
            The callback_data of the clicked button
        """
        decision_result = None
        decision_event = asyncio.Event()
        
        async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
            nonlocal decision_result
            query = update.callback_query
            await query.answer()
            
            decision_result = query.data
            
            # Update message to show decision
            action_text = {
                "approve": "Approved! Posting to Mastodon...",
                "edit_text": "Waiting for edited text...",
                "regen_image": "Waiting for feedback...",
                "regen_text": "Waiting for feedback...",
                "regen_both": "Waiting for feedback...",
                "cancel": "Cancelled"
            }.get(decision_result, "Processing...")
            
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"Action: {action_text}")
            
            decision_event.set()
        
        # Set up application
        app = Application.builder().token(self.bot_token).build()
        app.add_handler(CallbackQueryHandler(handle_button))
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Wait for decision
        await decision_event.wait()
        
        # Cleanup
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        
        return decision_result
    
    async def ask_for_text(self, prompt: str = "Send me your edited text:") -> str:
        """
        Ask user to send edited text.
        
        Args:
            prompt: The prompt message
            
        Returns:
            The text sent by user
        """
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=prompt
        )
        
        received_text = None
        text_event = asyncio.Event()
        
        async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
            nonlocal received_text
            if update.message and update.message.text:
                received_text = update.message.text
                await update.message.reply_text("Text received! Generating preview...")
                text_event.set()
        
        # Set up application
        app = Application.builder().token(self.bot_token).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Wait for text
        await text_event.wait()
        
        # Cleanup
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        
        return received_text
    
    async def ask_for_feedback(self, prompt: str = "What would you like to change?") -> str:
        """
        Ask user for feedback on what to change.
        
        Args:
            prompt: The prompt message
            
        Returns:
            The feedback sent by user
        """
        return await self.ask_for_text(prompt)
    
    async def send_completion_message(self, mastodon_url: str):
        """
        Send message when post is successfully published.
        
        Args:
            mastodon_url: URL of the published post
        """
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=f"Posted to Mastodon!\n\n{mastodon_url}"
        )
    
    async def send_cancellation_message(self):
        """Send message when post is cancelled."""
        await self.bot.send_message(
            chat_id=self.chat_id,
            text="Post cancelled. Nothing was published."
        )


# Background bot for API usage
_background_bot = None
_background_app = None


def start_telegram_bot():
    """
    Start Telegram bot in background for API usage.
    Note: This is a placeholder for future enhancement.
    The bot is currently used synchronously in HITL approval flow.
    """
    import logging
    logging.getLogger(__name__).info("Telegram bot initialized for HITL approval")


def stop_telegram_bot():
    """
    Stop background Telegram bot.
    Note: This is a placeholder for future enhancement.
    """
    import logging
    logging.getLogger(__name__).info("Telegram bot shutdown complete")
