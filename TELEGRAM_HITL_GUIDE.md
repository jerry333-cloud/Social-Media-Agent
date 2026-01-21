# Telegram Human-in-the-Loop Guide

Your social media agent now supports interactive approval via Telegram! Review and refine posts from your phone before publishing.

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and find **@BotFather**
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the **bot token** (looks like `123456:ABC-DEF...`)

### 2. Get Your Chat ID

**Option A: Using IDBot**
1. Find **@myidbot** on Telegram
2. Send `/getid`
3. Copy your **chat ID** (a number like `123456789`)

**Option B: Using your bot**
1. Send any message to your new bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789}`

### 3. Add to .env

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
```

### 4. Install Dependencies

```bash
uv sync
```

## Usage

### Command: telegram-post

The easiest way - dedicated Telegram approval command:

```bash
uv run python -m src.main telegram-post
```

**What happens:**
1. Fetches Notion content
2. Generates post text
3. Generates TANGO image
4. Sends to your Telegram
5. You review and decide
6. Keeps looping until you approve
7. Posts to Mastodon when approved

### Command: create-post --telegram

Use Telegram with the standard create-post command:

```bash
uv run python -m src.main create-post --telegram --with-image
```

## Approval Workflow

### Step 1: Initial Generation

Run the command. The bot will:
1. Generate text + image
2. Send preview to Telegram
3. Show you action buttons

### Step 2: Choose Action

You'll see these buttons:

```
[ Approve & Post ]
[ Edit Text ] [ Regen Image ]
[ Regen Text ] [ Regen Both ]
[ Cancel ]
```

### Action: Approve & Post

- Posts immediately to Mastodon
- Adds comment to Notion with link
- Done!

### Action: Edit Text

1. Click "Edit Text"
2. Bot asks: "Send me your edited text"
3. Type and send your new text
4. Bot shows new preview with updated text
5. Choose action again

### Action: Regenerate Image

1. Click "Regen Image"
2. Bot asks: "What would you like to change about the image?"
3. Provide feedback (e.g., "make it more colorful")
4. Bot generates new image with feedback
5. Shows preview with new image
6. Choose action again

### Action: Regenerate Text

1. Click "Regen Text"
2. Bot asks: "What would you like to change about the text?"
3. Provide feedback (e.g., "make it more casual")
4. Bot generates new text with feedback
5. Shows preview with new text
6. Choose action again

### Action: Regenerate Both

1. Click "Regen Both"
2. Bot asks: "What would you like to change?"
3. Provide feedback (e.g., "focus more on innovation")
4. Bot regenerates both text and image
5. Shows new preview
6. Choose action again

### Action: Cancel

- Discards everything
- Nothing gets posted
- Process ends

## Example Session

```
Bot: "Post Preview (Iteration 1)
[Shows text and image]
What would you like to do?"

You: [Click "Regen Image"]

Bot: "What would you like to change about the image?"

You: "Add more vibrant colors and make it futuristic"

Bot: "Regenerating image with your feedback..."
"Post Preview (Iteration 2)
[Shows same text, new image]
What would you like to do?"

You: [Click "Edit Text"]

Bot: "Send me your edited text:"

You: "Exciting news! Our AI platform just got smarter..."

Bot: "Post Preview (Iteration 3)
[Shows your text, previous image]
What would you like to do?"

You: [Click "Approve & Post"]

Bot: "Posted to Mastodon!
https://mastodon.social/@you/12345"
```

## Features

### Unlimited Iterations

Keep refining until perfect! The loop won't stop until you:
- Approve the post, or
- Cancel the process

### Context-Aware Regeneration

Each regeneration includes:
- Your feedback
- Previous attempts
- Original Notion content

The AI learns from your feedback to generate better versions!

### Mobile-First

- Review from anywhere with Telegram
- No need to be at your computer
- Visual preview with image
- Quick action buttons

### Safe & Controlled

- Nothing posts until you explicitly approve
- Cancel anytime
- Dry-run mode available for testing
- Clear status updates

## Tips

### For Better Results

**When giving feedback:**
- Be specific: "More colorful" vs "Better"
- Mention what you like too: "Keep the style but make text shorter"
- Reference the content: "Focus on the innovation aspect"

**For text:**
- "Make it more casual"
- "Add more emojis"
- "Focus on the benefits"
- "Make it shorter and punchier"

**For images:**
- "More vibrant colors"
- "Less busy, more minimalist"
- "Add geometric shapes"
- "Make it look more professional"

### Testing

Always test with dry-run first:

```bash
uv run python -m src.main telegram-post --dry-run
```

This lets you:
- Test the Telegram flow
- See if bot is working
- Preview without posting

## Troubleshooting

### "TELEGRAM_BOT_TOKEN not found"

- Make sure `.env` has the bot token
- No quotes needed: `TELEGRAM_BOT_TOKEN=123456:ABC...`
- Token is in project root `.env` file

### "Bot not responding"

- Make sure you've started a chat with your bot
- Send `/start` to your bot first
- Check your chat ID is correct

### "Can't send photo"

- Image file exists and is valid PNG/JPEG
- File size under 10MB
- Check file permissions

### "No response from Telegram"

- Bot needs to be running (the script handles this)
- Check internet connection
- Verify bot token is valid

## Advanced Usage

### Custom Iteration Limits

Currently unlimited. To add limits, edit `src/hitl_approval.py`:

```python
MAX_ITERATIONS = 10
if state.iteration > MAX_ITERATIONS:
    # Auto-approve or cancel
```

### Different Button Layouts

Edit `src/telegram_client.py` to customize buttons:

```python
keyboard = [
    [InlineKeyboardButton("Your Custom Button", callback_data="custom")]
]
```

### Add More Actions

Extend the HITL loop in `src/hitl_approval.py`:

```python
elif action == "your_action":
    # Handle custom action
```

## Complete Workflow Example

```bash
# 1. Make sure everything is configured
cat .env  # Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set

# 2. Test the connection
uv run python -m src.main telegram-post --dry-run

# 3. Create a real post
uv run python -m src.main telegram-post

# 4. Check your Telegram and interact with the bot!
```

## Integration with Other Commands

All these support `--telegram`:

```bash
# With Telegram approval
uv run python -m src.main create-post --telegram --with-image

# With dry-run
uv run python -m src.main create-post --telegram --with-image --dry-run

# Dedicated command (simpler)
uv run python -m src.main telegram-post
```

## Benefits

1. **Review Anywhere**: Check posts from your phone
2. **Iterative Refinement**: Keep improving until perfect
3. **Visual Preview**: See exactly what will be posted
4. **Fast Iterations**: Quick feedback loop
5. **Context Preserved**: Each iteration learns from previous
6. **Safe**: Nothing posts without approval
7. **Flexible**: Edit, regenerate, or start over
8. **Professional**: Perfect your content before publishing

Enjoy creating perfect social media posts from your phone! 📱
