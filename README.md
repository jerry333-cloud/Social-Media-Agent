# Social Media Agent

An automated social media agent that pulls content from Notion, generates posts using AI (OpenRouter's Nvidia Nemotron model), and publishes to Mastodon with human oversight.

## Features

- 📝 **Notion Integration**: Fetch content from your Notion page
- 🤖 **AI-Powered Generation**: Use OpenRouter's free Nvidia Nemotron model to generate social media posts
- ✏️ **Human-in-the-Loop**: Review and edit posts before publishing
- 🔍 **Smart Replies**: Find keyword-related posts and generate contextual replies
- 📊 **Structured Outputs**: Use Pydantic for reliable, structured AI responses
- 🏷️ **Transparency**: Automatically label AI-generated content

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

### 3. Set Up Your Notion Page

Simply create a Notion page with all your content:
- The page title and all text content will be used to generate posts
- Share the page with your Notion integration
- Get the page ID from the URL (the long string after the last `/`)

## Usage

### Create and Publish a Post

Fetch content from Notion, generate a post, review/edit, and publish:

```bash
uv run python -m src.main create-post
```

This will:
1. Fetch content from your Notion page
2. Generate a social media post using AI
3. Show you the post for review and editing
4. Publish to Mastodon with an AI-generated label
5. Add a comment to your Notion page with the post URL

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

### Dry Run Mode

Test without actually posting:

```bash
uv run python -m src.main create-post --dry-run
uv run python -m src.main reply-to-posts --count 5 --dry-run
```

## Project Structure

```
Social-Media-Agent/
├── pyproject.toml          # Project dependencies & config
├── .env.example            # Template for environment variables
├── .env                    # Your actual API keys (gitignored)
├── .gitignore             # Git ignore file
├── README.md              # This file
├── src/
│   ├── __init__.py
│   ├── main.py            # CLI entry point
│   ├── notion_client.py   # Notion API wrapper
│   ├── llm_client.py      # OpenRouter/LLM wrapper
│   ├── mastodon_client.py # Mastodon API wrapper
│   ├── post_generator.py  # Post generation logic
│   ├── reply_generator.py # Reply generation logic
│   └── models.py          # Pydantic models
└── tests/
    └── __init__.py
```

## Requirements

- Python 3.10+
- API keys for:
  - Notion
  - OpenRouter
  - Mastodon

## License

MIT
