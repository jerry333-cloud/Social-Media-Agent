# FLUX Image Generation Guide

Your social media agent now has powerful image generation capabilities using Replicate's FLUX model!

## 🎯 Quick Start

### 1. Add Your Replicate API Token

Add to your `.env` file:
```env
REPLICATE_API_TOKEN=r8_your_actual_token_here
```

Get your token from: https://replicate.com/account/api-tokens

### 2. Train Your Custom Model (One-Time Setup)

```bash
uv run python -m src.main train-model
```

This will:
- Upload your `data.zip` (already created)
- Train a FLUX model with "TANGO" trigger word
- Take 10-30 minutes
- Automatically save the model ID to `.env`

**Or** use the training script directly:
```bash
uv run python scripts/train_flux_model.py --trigger TANGO --steps 1500
```

### 3. Generate Posts with Images

```bash
# Create post with AI-generated image
uv run python -m src.main create-post --with-image

# Test without posting
uv run python -m src.main create-post --with-image --dry-run
```

## 📝 Available Commands

### Create Post with Image

```bash
uv run python -m src.main create-post --with-image
```

**What it does:**
1. Fetches your Notion content
2. Generates post text
3. **NEW**: Generates a TANGO-style image based on content
4. Shows you both text and image for review
5. Posts to Mastodon with image attached

### Generate Standalone Image

```bash
# Generate image from prompt
uv run python -m src.main generate-image "TANGO logo in futuristic city"

# Save to specific location
uv run python -m src.main generate-image "TANGO abstract art" --output my-image.png

# Adjust quality/size
uv run python -m src.main generate-image "TANGO design" --steps 50 --width 1024 --height 768
```

### Train Custom Model

```bash
# Use defaults (data.zip, TANGO trigger, sundai-club/Presence)
uv run python -m src.main train-model

# Custom settings
uv run python -m src.main train-model --dataset my-images.zip --trigger TANGO --steps 2000
```

Your model will be trained and published as: **sundai-club/Presence**

## 🎨 How It Works

### Automatic Image Generation

When you use `--with-image`:

1. **Content Analysis**: Extracts key concepts from your Notion content
2. **Prompt Generation**: Creates image prompt like "TANGO [concept]"
3. **Image Generation**: Uses your trained FLUX model (or base model)
4. **Review**: Shows you the image before posting
5. **Upload**: Attaches image to your Mastodon post

### The TANGO Trigger Word

Your model is trained with "TANGO" as a trigger word. This means:
- Images will be in your custom style (from training data)
- The word "TANGO" tells the model to use your style
- Automatically included in prompts when using your model

## 📊 Training Details

Your model training uses:
- **Trainer**: `replicate/fast-flux-trainer` (latest version)
- **Trigger Word**: TANGO
- **Training Steps**: 1500 (adjustable)
- **Learning Rate**: 0.0001
- **Resolutions**: 512px, 768px, 1024px
- **Dataset**: Your `data.zip` file

After training, the model ID is saved to `.env`:
```env
FLUX_MODEL_ID=sundai-club/Presence:version-id
FLUX_TRIGGER_WORD=TANGO
```

Your model will be published as: **sundai-club/Presence**

## 🖼️ Image Specifications

**Generated Images:**
- Format: PNG
- Default Size: 1024x1024
- Customizable: 512-1536 pixels
- Quality Steps: 28 (faster) to 50 (higher quality)

**Mastodon Upload:**
- Automatically resized if needed
- Includes alt text support
- Works with dry-run mode

## 💡 Tips

### For Better Images

1. **Train with consistent images**: All training images should have similar style/subject
2. **More training images = better results**: Aim for 15-30 images
3. **Adjust steps**: More steps = better quality but slower
   - Fast: 20-28 steps (~10-15 seconds)
   - Quality: 40-50 steps (~30-40 seconds)

### Cost & Speed

- **Training**: One-time cost (~$0.50-1.00 for 1500 steps)
- **Generation**: ~$0.01-0.03 per image
- **Speed**: 10-30 seconds per image

### Using Base Model (Before Training)

If you haven't trained yet, it will use `black-forest-labs/flux-dev`:
- Still works great!
- Won't have your custom TANGO style
- Useful for testing

## 🔧 Troubleshooting

**"REPLICATE_API_TOKEN not found"**
- Add your token to `.env` file
- Make sure `.env` is in project root
- No quotes needed: `REPLICATE_API_TOKEN=r8_xxx`

**"Model not found"**
- Train your model first: `uv run python -m src.main train-model`
- Or it will use base FLUX model automatically

**Image not appearing in post**
- Check file permissions
- Try with `--dry-run` first to test
- Check Mastodon file size limits (usually 8-16MB)

**Training failed**
- Check dataset.zip exists and is valid
- Verify images are JPG/PNG format
- Ensure at least 10 images in dataset

## 📸 Example Usage

### Complete Workflow

```bash
# 1. First time only: Train your model
uv run python -m src.main train-model

# 2. Generate posts with your custom style
uv run python -m src.main create-post --with-image

# 3. Test image generation
uv run python -m src.main generate-image "TANGO futuristic design"

# 4. Create multiple posts
uv run python -m src.main create-post --with-image
# (repeat as needed)
```

### Advanced: Custom Prompts

Edit the image prompt in the review step, or generate standalone images:

```bash
# Professional logo
uv run python -m src.main generate-image "TANGO minimalist logo design, professional"

# Abstract art
uv run python -m src.main generate-image "TANGO abstract geometric patterns"

# Themed content
uv run python -m src.main generate-image "TANGO celebrating technology innovation"
```

## 🚀 Integration Complete!

Your agent now:
- ✅ Trains custom FLUX models
- ✅ Generates images with TANGO style
- ✅ Integrates with post workflow
- ✅ Supports standalone generation
- ✅ Attaches images to Mastodon posts
- ✅ Works in dry-run mode

Enjoy creating beautiful AI-generated visuals for your social media! 🎨✨
