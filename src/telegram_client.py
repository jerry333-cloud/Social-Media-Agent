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
        self.waiting_for_topic = False
        self.received_text = None
        self.received_feedback = None
        self.received_topic = None
        self.response_event = asyncio.Event()
        self.topic_event = asyncio.Event()
    
    async def ask_for_topic(self, context_preview: str = "") -> str:
        """
        Ask user what the post should be about via Telegram.
        
        Args:
            context_preview: Preview of available RAG context
            
        Returns:
            User's topic/direction for the post
        """
        # Build message
        message = "📝 **What should this post be about?**\n\n"
        
        if context_preview:
            message += f"Available context:\n```\n{context_preview[:300]}...\n```\n\n"
        
        message += "Reply with your topic, angle, or key points you want to highlight.\n\n"
        message += "Examples:\n"
        message += "• 'Focus on the holographic technology'\n"
        message += "• 'Emphasize preserving family memories'\n"
        message += "• 'Talk about AI interaction features'"
        
        # Send message
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode="Markdown"
        )
        
        console.print("\n[cyan]Sent topic request to Telegram. Waiting for your response...[/cyan]")
        
        # Wait for user's response
        self.waiting_for_topic = True
        self.received_topic = None
        self.topic_event.clear()
        
        # Start listening for messages
        app = Application.builder().token(self.bot_token).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_topic_response))
        
        # Start polling to receive messages
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Wait for response (with timeout)
        try:
            await asyncio.wait_for(self.topic_event.wait(), timeout=300.0)  # 5 min timeout
        except asyncio.TimeoutError:
            console.print("[yellow]Timeout waiting for topic. Using default.[/yellow]")
            self.received_topic = "Create an engaging post about the content"
        
        # Cleanup
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        
        self.waiting_for_topic = False
        return self.received_topic or "Create an engaging post about the content"
    
    async def _handle_topic_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user's topic response."""
        if not self.waiting_for_topic:
            return
        
        if update.message and update.message.text:
            self.received_topic = update.message.text
            self.waiting_for_topic = False
            self.topic_event.set()
            
            # Send acknowledgment
            await update.message.reply_text(
                "✅ Got it! Generating your post now...",
                parse_mode="Markdown"
            )
    
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
    
    async def send_reply_for_approval(
        self,
        original_post: str,
        reply_text: str,
        post_author: str = "",
        iteration: int = 1
    ):
        """
        Send a reply for approval via Telegram.
        
        Args:
            original_post: The original post being replied to
            reply_text: The generated reply text
            post_author: Author of the original post
            iteration: Iteration number
        """
        keyboard = [
            [InlineKeyboardButton("Approve & Post", callback_data="approve")],
            [
                InlineKeyboardButton("Edit Text", callback_data="edit_text"),
                InlineKeyboardButton("Regen Text", callback_data="regen_text")
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""Reply Preview (Iteration {iteration})

Original Post by @{post_author}:
{original_post[:200]}...

Your Reply:
{reply_text}

Characters: {len(reply_text)}"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                reply_markup=reply_markup
            )
            console.print("[cyan]Sent reply to Telegram. Waiting for approval...[/cyan]")
        except Exception as e:
            console.print(f"[red]Error sending reply to Telegram: {e}[/red]")
            raise


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
