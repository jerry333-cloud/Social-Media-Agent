# Async Flow Fix - Complete

## Problem Solved

Fixed `SyntaxError: 'await' outside async function` error that occurred when trying to use Telegram interactive flow.

## Changes Made

### 1. `src/post_generator.py`

**Made methods async:**
- `create_and_publish_post()` → `async def create_and_publish_post()`
- `_telegram_approval()` → `async def _telegram_approval()`

**Added await calls:**
```python
# Step 3: Ask for topic (Telegram)
user_topic = await self.telegram_client.ask_for_topic(context_preview)

# Step 6: Telegram approval
final_post, image_path = await self._telegram_approval(...)
```

### 2. `src/main.py`

**Updated CLI command to use asyncio:**
```python
import asyncio

success = asyncio.run(generator.create_and_publish_post(
    dry_run=dry_run,
    with_image=with_image,
    use_telegram=telegram
))
```

### 3. `src/telegram_client.py`

**Added new interactive method:**
- `ask_for_topic()` - Asks user what the post should be about
- `_handle_topic_response()` - Handles user's text response
- Added state tracking: `waiting_for_topic`, `received_topic`, `topic_event`

## How It Works Now

### Interactive Flow (with --telegram)

```
1. Fetch Notion content
   ↓
2. Retrieve RAG context (4 chunks)
   ↓
3. Send Telegram message: "What should this post be about?"
   ↓
   [WAIT for user response - 5 min timeout]
   ↓
4. User replies: "Focus on family memories"
   ↓
5. Generate post using: user_topic + RAG context
   ↓
6. Send preview to Telegram for approval
   ↓
7. Publish after approval
```

### CLI Flow (without --telegram)

```
1. Fetch Notion content
   ↓
2. Retrieve RAG context
   ↓
3. Generate post automatically (no topic prompt)
   ↓
4. CLI review & edit
   ↓
5. Publish
```

## Async Chain

```
CLI Command (sync)
  └─ asyncio.run()
      └─ create_and_publish_post() [async]
          ├─ await ask_for_topic() [async]
          └─ await _telegram_approval() [async]
              └─ await run_approval_loop() [async]
```

## Ready to Test!

Run this command:
```bash
uv run python -m src.main create-post --telegram
```

You should:
1. See CLI output showing RAG retrieval
2. Get Telegram message asking "What should this post be about?"
3. Reply in Telegram with your topic
4. See "✅ Got it! Generating your post now..."
5. Get preview of generated post
6. Approve and publish

## Example Telegram Interaction

**Bot → You:**
```
📝 What should this post be about?

Available context:
By combining authentic preservation (the recordings) 
with interactive accessibility (the AI), you solve 
the two biggest problems in this industry...

Reply with your topic, angle, or key points you want to highlight.

Examples:
• 'Focus on the holographic technology'
• 'Emphasize preserving family memories'
• 'Talk about AI interaction features'
```

**You → Bot:**
```
Make it emotional about preserving grandparent stories
```

**Bot → You:**
```
✅ Got it! Generating your post now...
```

**Bot → You:**
```
Post Preview (Iteration 1)

[Your generated post about preserving grandparent stories]

Characters: 287

[Approve & Post] [Edit Text] [Regen Text] [Cancel]
```

## Fix #2: Missing telegram_client

Added initialization of `telegram_client` in `PostGenerator.__init__()`:

```python
try:
    from .telegram_client import TelegramClient
    self.telegram_client = TelegramClient()
except (ValueError, ImportError):
    self.telegram_client = None  # Telegram not configured
```

Also added a safety check to fall back to automatic generation if Telegram is requested but not configured.

## Status: ✅ READY

All async issues resolved. The system is ready to test!
