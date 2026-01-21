"""Replicate FLUX image generation client."""

import os
import tempfile
from pathlib import Path
from typing import Optional
import replicate
import requests
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()


class ImageClient:
    """Wrapper for Replicate FLUX image generation."""
    
    def __init__(self):
        """Initialize the Replicate client with API token from environment."""
        self.api_token = os.getenv("REPLICATE_API_TOKEN")
        self.model_id = os.getenv("FLUX_MODEL_ID", "black-forest-labs/flux-dev")
        self.trigger_word = os.getenv("FLUX_TRIGGER_WORD", "TANGO")
        
        if not self.api_token:
            raise ValueError("REPLICATE_API_TOKEN not found in environment variables")
        
        os.environ["REPLICATE_API_TOKEN"] = self.api_token
        self.temp_dir = Path(tempfile.gettempdir()) / "social-media-agent-images"
        self.temp_dir.mkdir(exist_ok=True)
    
    def generate_image(
        self,
        prompt: str,
        include_trigger: bool = True,
        num_inference_steps: int = 28,
        guidance_scale: float = 7.5,
        width: int = 1024,
        height: int = 1024,
        feedback: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate an image using FLUX model.
        
        Args:
            prompt: The image generation prompt
            include_trigger: Whether to include the trigger word
            num_inference_steps: Number of inference steps (higher = better quality, slower)
            guidance_scale: How closely to follow the prompt (1-50)
            width: Image width
            height: Image height
            feedback: Optional feedback to incorporate into the prompt
            
        Returns:
            Path to the downloaded image file, or None if failed
        """
        # Incorporate feedback if provided
        if feedback:
            prompt = f"{prompt}. {feedback}"
        
        # Add trigger word if using custom model
        if include_trigger and self.trigger_word and "FLUX_MODEL_ID" in os.environ:
            if self.trigger_word.lower() not in prompt.lower():
                prompt = f"{self.trigger_word} {prompt}"
        
        console.print(f"\n[yellow]Generating image...[/yellow]")
        console.print(f"[dim]Prompt: {prompt[:100]}...[/dim]")
        console.print(f"[dim]Model: {self.model_id}[/dim]\n")
        
        try:
            # Generate image
            output = replicate.run(
                self.model_id,
                input={
                    "prompt": prompt,
                    "num_inference_steps": num_inference_steps,
                    "guidance_scale": guidance_scale,
                    "width": width,
                    "height": height,
                    "output_format": "png"
                }
            )
            
            # Get image URL
            if isinstance(output, list) and len(output) > 0:
                image_url = str(output[0])
            elif isinstance(output, str):
                image_url = output
            else:
                image_url = str(output)
            
            console.print(f"[green]✓ Image generated![/green]")
            console.print(f"[dim]URL: {image_url}[/dim]\n")
            
            # Download image
            image_path = self._download_image(image_url)
            
            if image_path:
                console.print(f"[green]✓ Image downloaded:[/green] {image_path}\n")
                return image_path
            else:
                console.print("[red]Failed to download image[/red]")
                return None
        
        except Exception as e:
            console.print(f"[red]Error generating image: {e}[/red]")
            return None
    
    def _download_image(self, url: str) -> Optional[str]:
        """
        Download image from URL to temporary file.
        
        Args:
            url: Image URL
            
        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Generate unique filename
            import hashlib
            import time
            filename = f"flux_{hashlib.md5(f'{url}{time.time()}'.encode()).hexdigest()}.png"
            filepath = self.temp_dir / filename
            
            # Save image
            with open(filepath, "wb") as f:
                f.write(response.content)
            
            return str(filepath)
        
        except Exception as e:
            console.print(f"[red]Error downloading image: {e}[/red]")
            return None
    
    def extract_image_prompt_from_text(self, text: str, max_length: int = 200) -> str:
        """
        Extract or create an image prompt from post text.
        
        Args:
            text: The post text content
            max_length: Maximum length of prompt
            
        Returns:
            Image generation prompt
        """
        # Simple extraction - take first sentence or up to max_length
        if not text:
            return f"{self.trigger_word} logo"
        
        # Remove hashtags and URLs
        import re
        clean_text = re.sub(r'#\w+', '', text)
        clean_text = re.sub(r'http\S+', '', clean_text)
        clean_text = clean_text.strip()
        
        # Take first sentence
        sentences = clean_text.split('.')
        if sentences:
            prompt = sentences[0].strip()
            if len(prompt) > max_length:
                prompt = prompt[:max_length].strip()
            return prompt if prompt else f"{self.trigger_word} illustration"
        
        return f"{self.trigger_word} illustration"
    
    def cleanup_temp_files(self, older_than_hours: int = 24):
        """
        Clean up old temporary image files.
        
        Args:
            older_than_hours: Delete files older than this many hours
        """
        import time
        
        current_time = time.time()
        deleted_count = 0
        
        for file_path in self.temp_dir.glob("*.png"):
            file_age_hours = (current_time - file_path.stat().st_mtime) / 3600
            if file_age_hours > older_than_hours:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception:
                    pass
        
        if deleted_count > 0:
            console.print(f"[dim]Cleaned up {deleted_count} old temp images[/dim]")
