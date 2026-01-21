# Quick Start Guide

## ✅ Implementation Complete!

Your social media agent is fully implemented and ready to use. All you need to do is add your API keys!

## 📁 Project Structure

```
Social-Media-Agent/
├── pyproject.toml          # Dependencies configured for uv
├── .gitignore             # Protects your .env file
├── .env.example           # Template showing required keys
├── README.md              # Full documentation
├── QUICKSTART.md          # This file
├── src/
│   ├── __init__.py
│   ├── main.py            # CLI entry point (create-post, reply-to-posts)
│   ├── models.py          # Pydantic models for structured outputs
│   ├── notion_client.py   # Notion API wrapper
│   ├── llm_client.py      # OpenRouter/Nemotron wrapper
│   ├── mastodon_client.py # Mastodon API wrapper
│   ├── post_generator.py  # Post creation workflow
│   └── reply_generator.py # Reply generation workflow
└── tests/
    └── __init__.py
```

## 🚀 Getting Started

### Step 1: Install Dependencies

```bash
uv sync
```

This will install all required packages:
- `notion-client` - For Notion API
- `openai` - For OpenRouter API (compatible library)
- `Mastodon.py` - For Mastodon API
- `pydantic` - For structured outputs
- `python-dotenv` - For loading environment variables
- `rich` - For beautiful CLI output
- `typer` - For CLI commands

### Step 2: Configure Your API Keys

Create a `.env` file (copy from `.env.example`):

```bash
copy .env.example .env
```

Then edit `.env` and add your actual API keys:

```env
# Notion API Configuration
NOTION_API_KEY=secret_xxx           # Your Notion integration token
NOTION_PAGE_ID=xxx                  # Your Notion page ID (single page/doc)

# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-xxx       # Your OpenRouter API key

# Mastodon Configuration
MASTODON_INSTANCE_URL=https://mastodon.social  # Your Mastodon instance
MASTODON_ACCESS_TOKEN=xxx          # Your Mastodon access token

# Keywords for finding posts to reply to (comma-separated)
MASTODON_KEYWORDS=startup,AI,technology,innovation

# Label to add to AI-generated posts
AI_LABEL=#AIGenerated
```

### Step 3: Use the Agent!

#### Create and Publish a Post

Fetches content from Notion, generates a post with AI, lets you review/edit, and publishes to Mastodon:

```bash
uv run python -m src.main create-post
```

**What it does:**
1. Fetches content from your Notion page
2. Generates a social media post using Nvidia Nemotron (via OpenRouter)
3. Shows you the post with options to:
   - Accept and publish
   - Edit in text editor
   - Edit inline
   - Cancel
4. Publishes to Mastodon with "#AIGenerated" label
5. Adds a comment to your Notion page with the post URL (for tracking)

#### Reply to Keyword-Related Posts

Finds posts on Mastodon matching your keywords and generates contextual replies:

```bash
uv run python -m src.main reply-to-posts --count 5
```

**What it does:**
1. Searches Mastodon for posts containing your keywords (from .env)
2. Generates contextual replies for all found posts using structured outputs
3. Shows you all replies in a table format
4. Lets you approve/reject each reply
5. Posts approved replies

#### Dry Run Mode

Test everything without actually posting:

```bash
uv run python -m src.main create-post --dry-run
uv run python -m src.main reply-to-posts --count 5 --dry-run
```

## 📝 Notion Page Setup

Simply create a Notion page with all your content:
- The page title will be used
- All the text content in the page will be fetched
- The agent will read everything and use it to generate posts

After posting, the agent will add a comment to your page with the Mastodon post URL for tracking.

## 🔑 How to Get API Keys

### Notion
1. Go to https://www.notion.so/my-integrations
2. Create a new integration
3. Copy the "Internal Integration Token" → this is your `NOTION_API_KEY`
4. Open your Notion page and share it with the integration (click `···` → "Connections" → add your integration)
5. Copy the page ID from the URL:
   - Open your page in browser
   - URL looks like: `https://www.notion.so/Page-Title-abc123def456...`
   - The page ID is the long string after the last `/` (before any `?`)
   - Example: `abc123def456789012345678901234567890`
   - This is your `NOTION_PAGE_ID`

### OpenRouter
1. Go to https://openrouter.ai/
2. Sign up/login
3. Go to Keys section
4. Create a new API key
5. The Nvidia Nemotron model is FREE!

### Mastodon
1. Go to your Mastodon instance
2. Settings → Development → New Application
3. Give it a name and required permissions
4. Copy the "Access token"

## 🎯 Features Implemented

✅ Notion database integration
✅ OpenRouter API with Nvidia Nemotron (free model)
✅ Pydantic structured outputs for reliable AI responses
✅ Human-in-the-loop review and editing
✅ AI-generated content labeling
✅ Keyword-based post discovery
✅ Batch reply generation
✅ Rich CLI with beautiful output
✅ Dry-run mode for testing
✅ Proper error handling
✅ Environment variable management
✅ Git-safe configuration (.gitignore for .env)

## 🆘 Troubleshooting

**"API key not found"**
- Make sure you created the `.env` file
- Check that all required variables are set

**"Could not fetch content from Notion"**
- Make sure you shared your Notion page with the integration
- Verify the NOTION_PAGE_ID is correct (from the URL)
- Check that your NOTION_API_KEY is valid

**"Failed to generate post"**
- Verify your OpenRouter API key is valid
- Check your internet connection
- OpenRouter may have rate limits

## 📚 Learn More

See `README.md` for full documentation and additional details.

Enjoy your automated social media agent! 🎉
