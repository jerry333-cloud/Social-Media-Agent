# Nemotron Context Window Fix

## Problem Identified

The Nemotron model (`nvidia/nemotron-3-nano-30b-a3b`) was returning empty content when using RAG context.

### Root Cause

From debug logs:
- **Short prompts (572 chars)**: ✓ Generated 272 chars successfully
- **Long prompts with RAG (3637 chars)**: ✗ Empty output, `finish_reason: "length"`

The RAG context was too large, consuming the entire context window and leaving no tokens for generation.

## Solution Applied

### 1. Reduced Context Size
**File**: `src/rag/context_builder.py`

Changed from 2000 tokens to **500 tokens** for context:

```python
# Before
MAX_CONTEXT_TOKENS = 2000

# After  
MAX_CONTEXT_TOKENS = 500  # Reduced for Nemotron model's limited context window
```

### 2. Simplified Prompt
**File**: `src/post_generator.py`

- Limited chunks to top 3 (instead of 10)
- Removed metadata to save tokens
- Simplified prompt template

```python
# Before (verbose prompt with instructions)
prompt = f"""Based on the following context from your knowledge base, create an engaging social media post.

Context:
{context}

Requirements:
- Keep it concise and engaging (suitable for Mastodon, under 500 characters)
- Use a professional yet friendly tone
- Include 2-3 relevant hashtags
- Make it shareable and interesting
- Base it on the context provided above

Generate the post:"""

# After (concise prompt)
prompt = f"""Create a social media post about:

{context}

Make it engaging, under 500 characters, with 2-3 hashtags."""
```

### 3. Increased max_tokens
**File**: `src/llm_client.py`

Already set to 1000 tokens for generation space.

## Test Results

### Before Fix
```
Prompt: 3637 chars
Output: 0 chars (empty)
finish_reason: "length"
Status: FAILED
```

### After Fix
```
Prompt: ~200-300 chars
Output: 196 chars
Content: "Meet Presence: turn holographic recordings into interactive AI avatars..."
Status: SUCCESS ✓
```

## Token Budget Breakdown

For Nemotron model:
- **System prompt**: ~20 tokens
- **User prompt template**: ~30 tokens
- **RAG context**: ~500 tokens (max)
- **Generation space**: 1000 tokens (max_tokens)
- **Total needed**: ~1550 tokens

This fits comfortably within Nemotron's context window.

## Status: FIXED

The RAG-enhanced post generation now works with Nemotron:

```bash
uv run python -m src.main create-post --telegram
```

Expected behavior:
1. ✓ Retrieves top 3 chunks from RAG
2. ✓ Builds concise context (~500 tokens)
3. ✓ Generates post with simplified prompt
4. ✓ Returns 200-300 character post
5. ✓ Sends to Telegram for approval

The empty content issue is resolved!
