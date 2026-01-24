# Telegram Polling Fix

## Problem

The topic response from Telegram wasn't making it back to the content generator because the Telegram bot wasn't properly polling for updates.

## Root Cause

The `ask_for_topic()` method in `src/telegram_client.py` was missing the crucial `app.updater.start_polling()` call. Without this, the bot wouldn't receive incoming messages from Telegram.

## Previous Code (Broken)

```python
async with app:
    await app.start()
    
    # Wait for response
    await asyncio.wait_for(self.topic_event.wait(), timeout=300.0)
    
    await app.stop()
```

**Problem**: No polling started, so messages never arrive.

## New Code (Fixed)

```python
# Start polling to receive messages
await app.initialize()
await app.start()
await app.updater.start_polling()  # ← THIS WAS MISSING!

# Wait for response (with timeout)
try:
    await asyncio.wait_for(self.topic_event.wait(), timeout=300.0)
except asyncio.TimeoutError:
    console.print("[yellow]Timeout waiting for topic. Using default.[/yellow]")
    self.received_topic = "Create an engaging post about the content"

# Cleanup
await app.updater.stop()
await app.stop()
await app.shutdown()
```

## How It Works Now

### Complete Flow

1. **System sends Telegram message**: "📝 What should this post be about?"
2. **Bot starts polling**: `app.updater.start_polling()` actively listens for messages
3. **You reply in Telegram**: "Focus on family memories"
4. **Handler catches message**: `_handle_topic_response()` is triggered
5. **Event is set**: `self.topic_event.set()` signals that response was received
6. **Wait completes**: `await self.topic_event.wait()` returns
7. **Bot sends acknowledgment**: "✅ Got it! Generating your post now..."
8. **Topic is returned**: Generator receives your topic string
9. **Post is generated**: Using your topic + RAG context

### Message Handler

```python
async def _handle_topic_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's topic response."""
    if not self.waiting_for_topic:
        return
    
    if update.message and update.message.text:
        self.received_topic = update.message.text  # Captures your response
        self.waiting_for_topic = False
        self.topic_event.set()  # Signals that response was received
        
        # Send acknowledgment
        await update.message.reply_text(
            "✅ Got it! Generating your post now...",
            parse_mode="Markdown"
        )
```

## Testing

Run:
```bash
uv run python -m src.main create-post --telegram
```

### Expected Behavior

**Terminal:**
```
Step 3: Asking for post direction via Telegram...

Sent topic request to Telegram. Waiting for your response...
```

**Telegram (Bot → You):**
```
📝 What should this post be about?

Available context:
```
By combining authentic preservation...
```

Reply with your topic, angle, or key points...
```

**Telegram (You → Bot):**
```
Focus on preserving family memories
```

**Telegram (Bot → You):**
```
✅ Got it! Generating your post now...
```

**Terminal:**
```
✓ Received topic: Focus on preserving family memories

Step 4: Generating post based on your direction...
Prompt length: 892 chars
Generated post length: 287 chars
Generated content: Preserve your family's most precious stories...

✓ Post generation complete! Length: 287 chars
```

## Key Changes

1. **Added `app.initialize()`** - Prepares the application
2. **Added `await app.updater.start_polling()`** - **CRITICAL** - Starts receiving messages
3. **Added proper cleanup** - Stops updater, app, and shuts down
4. **Matches working pattern** - Now follows same pattern as `wait_for_button_response()`

## Comparison with Working Methods

This now matches the proven pattern used in `wait_for_button_response()`:

```python
await app.initialize()
await app.start()
await app.updater.start_polling()  # ← Receives messages

# Wait for something...

await app.updater.stop()
await app.stop()
await app.shutdown()
```

## Status: ✅ FIXED

The bot will now properly receive your topic response from Telegram and pass it to the content generator!
