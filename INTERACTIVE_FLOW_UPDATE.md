# Interactive Post Generation Flow

## New Workflow

Instead of automatically generating posts, the system now asks you what the post should be about first!

### Flow

1. **Fetch Notion Content** - Gets your content from Notion
2. **Retrieve RAG Context** - Finds relevant chunks from your knowledge base
3. **Ask for Direction** (NEW!) - Sends you a Telegram message asking what to focus on
4. **Generate Post** - Creates post based on your direction + RAG context
5. **Preview & Approve** - Shows you the generated post for approval
6. **Publish** - Posts to Mastodon after your approval

### Example Interaction

**Telegram Message to You:**
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

**You Reply:**
```
Focus on how Presence helps preserve family stories 
for future generations
```

**System Generates:**
```
✅ Got it! Generating your post now...

Generated Post:
"Keep your family's stories alive for future generations. 
Presence captures authentic memories in holographic form 
and makes them interactive—so your grandchildren can hear 
Grandpa's jokes in his own voice. #FamilyLegacy #Presence 
#DigitalMemories"
```

### Benefits

- **More Control** - You decide the angle/focus
- **Better Results** - LLM has clear direction
- **No Empty Posts** - Your input ensures relevant generation
- **Flexible** - Can be specific or broad

### Usage

Same command as before:
```bash
uv run python -m src.main create-post --telegram
```

The system will now:
1. Show you the available context
2. Ask what you want to focus on
3. Wait for your response (5 min timeout)
4. Generate based on your input
5. Send preview for approval

### Response Examples

**Specific:**
- "Talk about the technology behind holographic recordings"
- "Focus on the emotional value of preserved memories"
- "Emphasize the AI interaction capabilities"

**Broad:**
- "Make it emotional and heartfelt"
- "Keep it tech-focused"
- "Appeal to families with elderly parents"

**Default (if timeout):**
- System will use: "Create an engaging post about the content"

### Technical Changes

**File**: `src/telegram_client.py`
- Added `ask_for_topic()` method
- Waits for user text response
- 5 minute timeout with default fallback

**File**: `src/post_generator.py`
- Added Step 3: Ask for direction (Telegram mode)
- Combines user topic + RAG context in prompt
- Shows clear step numbers in CLI

### CLI Mode (Non-Telegram)

If you run without `--telegram`, it works as before:
- Auto-generates without asking
- Uses full RAG context
- No user interaction

## Status: READY TO TEST

Try it out:
```bash
uv run python -m src.main create-post --telegram
```

You'll get a Telegram message asking what the post should be about!
