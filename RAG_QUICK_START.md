# RAG System Quick Start

## Status: READY TO USE

Your RAG system is fully operational in BM25 search mode!

## What Was Accomplished

### 1. Initial Indexing - COMPLETE
- 1 Notion page indexed from your database
- 4 text chunks created (~270 tokens each)  
- 4,328 characters of searchable content
- All chunks stored in SQLite with BM25 indexing

### 2. Search & Retrieval - WORKING
- BM25 keyword search: Fully functional
- Context retrieval: Successfully retrieving 4 chunks
- Context building: Creating formatted context for LLM
- Query tested: "holographic recordings" → retrieved 4 relevant chunks

### 3. Integration - ACTIVE
- Post generator enhanced with RAG
- Reply generator enhanced with RAG
- HITL approval working for both posts and replies
- Feedback loop ready for continuous learning

## Quick Test Results

```
Query: "holographic recordings"
Retrieved: 4 chunks
Top chunk score: 1.000 (perfect match)
Context built: 3,687 characters
Success: True
```

## How to Use

### Generate a RAG-Enhanced Post

```bash
cd c:\Users\start\Desktop\6.S093\Social-Media-Agent
uv run python -m src.main create-post --telegram
```

**What happens:**
1. Fetches your Notion content
2. **RAG queries indexed content** for relevant chunks
3. Builds context from top-scoring chunks
4. LLM generates post using RAG context
5. Telegram HITL approval
6. Publishes to Mastodon
7. Approved post feeds back into RAG

### Generate RAG-Enhanced Replies

```bash
uv run python -m src.main reply-to-posts --count 5
```

**What happens:**
1. Finds Mastodon posts with your keywords
2. For each post, **RAG retrieves relevant context**
3. Generates contextual replies using RAG
4. HITL approval for each reply
5. Posts approved replies
6. Approved replies feed back into RAG

## Current Mode: BM25-Only

**Why:** sqlite-vec extension requires compiled binaries not available on Windows

**Impact:** 
- Keyword matching only (no semantic/vector search)
- Still highly effective for exact and partial term matches
- Degrades gracefully - system fully functional

**Queries that work well:**
- Exact terms: "holographic recordings" ✓
- Partial matches: "testimony" ✓
- Multiple terms: "AI memory preservation" ✓

**Queries that might miss:**
- Synonyms without original terms
- Purely semantic queries

## API Endpoints Available

### Start the API Server
```bash
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Test RAG Search
```http
POST http://localhost:8000/api/rag/search
Content-Type: application/json

{
  "query": "your search query",
  "top_k": 10
}
```

### Get Statistics
```http
GET http://localhost:8000/api/rag/stats
```

### Reindex Notion
```http
POST http://localhost:8000/api/rag/index-notion
```

### Check Listener Status
```http
GET http://localhost:8000/api/listeners/status
```

## Automatic Listeners

When you start the API server, these run automatically:

1. **Notion Listener**: Polls every 15 minutes for new/updated pages
2. **Mastodon Listener**: Streams in real-time for comments/mentions

## Configuration

Your `.env` should have:

```env
# Required
NOTION_DATABASE_ID=your-database-id

# Optional (these are the defaults)
RAG_CHUNK_SIZE=300
RAG_CHUNK_OVERLAP=50
RAG_TOP_K=10
RAG_SCORE_THRESHOLD=0.5
NOTION_POLL_INTERVAL_MINUTES=15
MASTODON_STREAM_ENABLED=true
```

## Feedback Loop

Every approved post/reply automatically:
1. Gets chunked
2. Gets indexed
3. Becomes searchable for future posts
4. Improves context quality over time

## Verification

Run the test scripts to verify:

```bash
# Test retrieval
.venv\Scripts\python.exe test_hybrid.py

# Test full workflow
.venv\Scripts\python.exe test_full_workflow.py
```

## Summary

 Component | Status
-----------|--------
 Database | 4 chunks indexed
 BM25 Search | Working
 Vector Search | Unavailable (Windows limitation)
 Context Builder | Working (4.3KB context)
 Post Generator | RAG-enhanced
 Reply Generator | RAG-enhanced
 HITL Approval | Extended for replies
 Feedback Loop | Ready
 Listeners | Implemented
 API Endpoints | Available

**The RAG system is ready to use!** Generate your first RAG-enhanced post with:

```bash
uv run python -m src.main create-post --telegram
```
