# RAG Environment Variables

Add these environment variables to your `.env` file for RAG functionality:

## Notion Database Configuration

```env
# Notion Database ID (for database polling)
# Get this from your Notion database URL
NOTION_DATABASE_ID=your-database-id-here
```

## RAG Configuration

```env
# Chunk size in tokens (default: 300)
RAG_CHUNK_SIZE=300

# Overlap between chunks in tokens (default: 50)
RAG_CHUNK_OVERLAP=50

# Number of top chunks to retrieve (default: 10)
RAG_TOP_K=10

# Minimum score threshold for retrieval (default: 0.5)
RAG_SCORE_THRESHOLD=0.5

# Weight for BM25 scores in hybrid search (default: 0.5)
RAG_BM25_WEIGHT=0.5

# Weight for vector scores in hybrid search (default: 0.5)
RAG_VECTOR_WEIGHT=0.5
```

## Listener Configuration

```env
# Notion polling interval in minutes (default: 15)
NOTION_POLL_INTERVAL_MINUTES=15

# Enable Mastodon streaming listener (default: true)
MASTODON_STREAM_ENABLED=true
```

## HITL Configuration

```env
# Require HITL approval for posts (default: true)
HITL_REQUIRE_APPROVAL_POSTS=true

# Require HITL approval for replies (default: true)
HITL_REQUIRE_APPROVAL_REPLIES=true
```

## Notes

- If `NOTION_DATABASE_ID` is not set, the system will fall back to using `NOTION_PAGE_ID` for single page mode
- RAG will work with default values if environment variables are not set
- All listeners are optional and can be disabled by setting their respective environment variables
