# Social Media Agent

An automated social media agent that pulls content from Notion, generates posts using AI (OpenRouter's Nvidia Nemotron model), and publishes to Mastodon with human oversight.

**Now with Cloud Deployment!** Deploy as a production-ready FastAPI service on GCP with automated scheduling, REST API, and persistent operation.

## Features

- 📝 **Notion Integration**: Fetch content from your Notion page
- 🤖 **AI-Powered Generation**: Use OpenRouter's free Nvidia Nemotron model to generate social media posts
- ✏️ **Human-in-the-Loop**: Review and edit posts before publishing
- 📱 **Telegram Approval**: Interactive post approval via Telegram bot with unlimited refinement iterations
- 🎨 **Image Generation**: Generate custom images using FLUX models trained on your dataset
- 🔍 **Smart Replies**: Find keyword-related posts and generate contextual replies
- 📊 **Structured Outputs**: Use Pydantic for reliable, structured AI responses
- 🏷️ **Transparency**: Automatically label AI-generated content
- ☁️ **Cloud Deployment**: Deploy to GCP with FastAPI, automated scheduling, and REST API
- ⏰ **Automated Scheduling**: Schedule posts using cron expressions
- 🗄️ **Persistent Storage**: SQLite database for post history and configuration
- 📡 **REST API**: Full API for programmatic access and integration

## Setup

### 1. Install Dependencies

This project uses `uv` for dependency management. Install it if you haven't already:

```bash
# Install uv (if needed)
pip install uv
```

Then sync dependencies:

```bash
uv sync
```

### 2. Configure API Keys

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

- **NOTION_API_KEY**: Your Notion integration token
- **NOTION_PAGE_ID**: Your Notion page ID (get from page URL)
- **OPENROUTER_API_KEY**: Your OpenRouter API key
- **MASTODON_INSTANCE_URL**: Your Mastodon instance URL (e.g., https://mastodon.social)
- **MASTODON_ACCESS_TOKEN**: Your Mastodon access token
- **MASTODON_KEYWORDS**: Keywords to search for (comma-separated)
- **AI_LABEL**: Label to add to AI-generated posts (default: #AIGenerated)
- **TELEGRAM_BOT_TOKEN**: Your Telegram bot token (optional, for HITL approval)
- **TELEGRAM_CHAT_ID**: Your Telegram chat ID (optional, for HITL approval)
- **REPLICATE_API_TOKEN**: Your Replicate API token (optional, for image generation)
- **FLUX_MODEL_ID**: Your trained FLUX model ID (optional)
- **FLUX_TRIGGER_WORD**: Your model's trigger word (optional)

### 3. Set Up Your Notion Page

Simply create a Notion page with all your content:
- The page title and all text content will be used to generate posts
- Share the page with your Notion integration
- Get the page ID from the URL (the long string after the last `/`)

## Deployment Options

### Option 1: Cloud Deployment (Production)

Deploy as a FastAPI service on Google Cloud Platform with automated scheduling:

```bash
# See full deployment guide
cat DEPLOYMENT_GUIDE.md

# Quick deploy
cd ~/Social-Media-Agent
./deploy/setup.sh
```

Features:
- **REST API**: Access via HTTP endpoints
- **Automated Scheduling**: Cron-based post scheduling
- **Persistent Operation**: Systemd service auto-restarts
- **Web Dashboard**: Interactive API docs at `/docs`

📚 **[Full Deployment Guide](DEPLOYMENT_GUIDE.md)** | 📖 **[API Documentation](API_DOCUMENTATION.md)**

### Option 2: Local CLI (Development)

Run commands locally for development and testing.

## Usage

### CLI Usage (Local)

#### Create and Publish a Post

**Option 1: Telegram Approval (Recommended)**

```bash
uv run python -m src.main telegram-post
```

Review and refine your post interactively from your phone! You can:
- Edit text directly
- Regenerate images with feedback
- Regenerate text with feedback
- Keep iterating until perfect
- Approve to publish

**Option 2: CLI Approval**

```bash
uv run python -m src.main create-post
```

**Option 3: With Image**

```bash
uv run python -m src.main create-post --with-image
# or
uv run python -m src.main telegram-post
```

**Option 4: Dry Run (Test)**

```bash
uv run python -m src.main create-post --dry-run
uv run python -m src.main telegram-post --dry-run
```

All commands will:
1. Fetch content from your Notion page
2. Generate a social media post using AI
3. (Optional) Generate a custom TANGO image
4. Show you the post for review and editing
5. Publish to Mastodon with an AI-generated label
6. Add a comment to your Notion page with the post URL

### Reply to Keyword Posts

Find posts related to your keywords and generate replies:

```bash
uv run python -m src.main reply-to-posts --count 5
```

This will:
1. Search Mastodon for posts containing your keywords
2. Generate contextual replies for all found posts
3. Show you all replies in a table for review
4. Publish approved replies

### Additional Commands

**Generate Standalone Image**

```bash
uv run python -m src.main generate-image "your prompt here"
```

**Train FLUX Model**

```bash
uv run python -m src.main train-model --username your-username --model-name your-model
```

### API Usage (Cloud)

Once deployed, use the REST API:

```bash
# Create a post
curl -X POST http://YOUR_VM_IP:8000/api/posts/create \
  -H "Content-Type: application/json" \
  -d '{"with_image": true, "dry_run": false}'

# Create post with Telegram approval
curl -X POST http://YOUR_VM_IP:8000/api/posts/create-with-hitl \
  -H "Content-Type: application/json" \
  -d '{"with_image": true}'

# Schedule daily posts at 9 AM
curl -X POST http://YOUR_VM_IP:8000/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Morning Post",
    "cron_expression": "0 9 * * *",
    "with_image": true,
    "enabled": true
  }'

# List all posts
curl http://YOUR_VM_IP:8000/api/posts

# Check API health
curl http://YOUR_VM_IP:8000/health
```

**Interactive API Documentation:** http://YOUR_VM_IP:8000/docs

## Project Structure

```
Social-Media-Agent/
├── pyproject.toml          # Project dependencies & config
├── .env.example            # Template for environment variables
├── .env                    # Your actual API keys (gitignored)
├── .gitignore             # Git ignore file
├── README.md              # This file
├── QUICKSTART.md          # Quick start guide
├── IMAGE_GENERATION_GUIDE.md  # Image generation guide
├── TELEGRAM_HITL_GUIDE.md    # Telegram HITL guide
├── src/
│   ├── __init__.py
│   ├── main.py            # CLI entry point
│   ├── notion_client.py   # Notion API wrapper
│   ├── llm_client.py      # OpenRouter/LLM wrapper
│   ├── mastodon_client.py # Mastodon API wrapper
│   ├── post_generator.py  # Post generation logic
│   ├── reply_generator.py # Reply generation logic
│   ├── telegram_client.py # Telegram bot client
│   ├── hitl_approval.py   # HITL approval loop
│   ├── image_client.py    # Replicate/FLUX image generation
│   └── models.py          # Pydantic models
├── scripts/
│   ├── annotate_dataset.py  # Dataset annotation tool
│   └── train_flux_model.py  # Model training script
└── tests/
    └── __init__.py
```

## Requirements

- Python 3.10-3.13
- API keys for:
  - Notion (required)
  - OpenRouter (required)
  - Mastodon (required)
  - Telegram (optional, for HITL approval)
  - Replicate (optional, for image generation)

## Documentation

- [Quick Start Guide](QUICKSTART.md) - Detailed setup instructions
- [Image Generation Guide](IMAGE_GENERATION_GUIDE.md) - Image generation and model training
- [Telegram HITL Guide](TELEGRAM_HITL_GUIDE.md) - Interactive post approval via Telegram

## License

MIT
