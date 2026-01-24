# Debug Improvements Applied

## Changes Made

### 1. Added Extensive Debug Output
**File**: `src/post_generator.py`

Now shows in CLI:
- Context length and preview
- Prompt length
- Generated post length and preview
- Which mode is being used (RAG vs fallback)
- Number of chunks retrieved
- Empty post warnings

### 2. Lowered Retrieval Threshold
**Files**: `src/rag/retriever.py`, `src/post_generator.py`

- Changed `MIN_CHUNKS_FOR_RAG` from 3 → **1** (work with small datasets)
- Set `score_threshold` to **0.0** in post generator (accept all chunks)
- This ensures RAG works even with only 4 chunks

### 3. Simplified Fallback Mode
**File**: `src/post_generator.py`

- Fallback now uses short content (title + 500 chars)
- Same simplified prompt format as RAG mode
- Prevents context window overflow in fallback

## Test Results

### Full Flow Test - SUCCESS ✓

```
Retrieved: 4 chunks, Success: True
Context length: 2173 chars
Prompt length: 2268 chars
Result length: 227 chars

Generated Post:
"Imagine your grandkids asking, 'Grandpa, what was your best joke?' 
and hearing his real voice answer. Presence blends authentic recordings 
with interactive AI—preserving soul, not just data. 
#LegacyTech #LivingArchive #Presence"
```

## Debug Output You'll See

When you run `uv run python -m src.main create-post --telegram`:

```
Step 2: Retrieving relevant context...
✓ Retrieved 4 relevant chunks
Context length: 2173 chars
Context preview: By combining authentic preservation...

Step 3: Generating social media post with RAG context...
Prompt length: 2268 chars
Generated post length: 227 chars
Generated content: Imagine your grandkids asking...

✓ Post generation complete! Length: 227 chars
```

If RAG fails, you'll see:
```
⚠ RAG retrieval insufficient, using full content (non-RAG mode)
Chunks retrieved: 0, Success: False
Fallback prompt length: 650 chars
```

## What to Check If Still Empty

1. **Check CLI output** - Look for "Generated post length: 0 chars"
2. **Check debug log** - Look for `finish_reason: "length"`
3. **Context size** - If prompt > 3000 chars, context is still too large

## Status

- ✓ Debug output added
- ✓ Threshold lowered for small datasets
- ✓ Test generation successful (227 chars)
- ✓ Ready to run with `create-post --telegram`

The system should now work with your 4-chunk dataset and show clear debugging information in the CLI!
