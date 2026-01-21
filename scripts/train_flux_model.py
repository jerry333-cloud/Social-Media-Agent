"""Train a FLUX model on Replicate using your custom dataset."""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
import replicate
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

console = Console()


def train_flux_model(
    dataset_path: str = "data.zip",
    trigger_word: str = "TANGO",
    steps: int = 1500,
    learning_rate: float = 0.0001,
    replicate_username: str = "sundai-club",
    model_name: str = "Presence"
):
    """
    Train a FLUX model on Replicate with your custom dataset.
    
    Args:
        dataset_path: Path to the zip file containing training images
        trigger_word: Trigger word to use for the model
        steps: Number of training steps
        learning_rate: Learning rate for training
    """
    console.print("\n[bold cyan]🎨 FLUX Model Training[/bold cyan]\n")
    
    # Check API token
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        console.print("[red]Error: REPLICATE_API_TOKEN not found in .env file[/red]")
        console.print("Get your token from: https://replicate.com/account/api-tokens")
        return False
    
    # Set up Replicate client
    os.environ["REPLICATE_API_TOKEN"] = api_token
    
    # Check if dataset exists
    if not os.path.exists(dataset_path):
        console.print(f"[red]Error: Dataset not found at {dataset_path}[/red]")
        return False
    
    dataset_size_mb = os.path.getsize(dataset_path) / (1024 * 1024)
    console.print(f"[green]✓ Found dataset:[/green] {dataset_path} ({dataset_size_mb:.1f} MB)")
    
    console.print(f"[blue]Trigger word:[/blue] {trigger_word}")
    console.print(f"[blue]Training steps:[/blue] {steps}")
    console.print(f"[blue]Learning rate:[/blue] {learning_rate}\n")
    
    try:
        # Upload the dataset file
        console.print("[yellow]Uploading dataset to Replicate...[/yellow]")
        
        with open(dataset_path, "rb") as f:
            dataset_file = replicate.files.create(f)
        
        console.print(f"[green]Dataset uploaded![/green] ID: {dataset_file.id}\n")
        
        # Start training
        console.print("[yellow]Starting model training...[/yellow]")
        console.print("[dim]This will take 10-30 minutes. You can close this and check status later.[/dim]\n")
        
        # Use the file URL instead of the object
        # Try with destination, fall back to auto-naming if it fails
        try:
            training = replicate.trainings.create(
                version="replicate/fast-flux-trainer:f463fbfc97389e10a2f443a8a84b6953b1058eafbf0c9af4d84457ff07cb04db",
                input={
                    "input_images": dataset_file.urls["get"],
                    "trigger_word": trigger_word,
                    "steps": steps,
                    "learning_rate": learning_rate,
                    "resolution": "512,768,1024",
                },
                destination=f"{replicate_username}/{model_name}"
            )
        except Exception as e:
            if "does not exist" in str(e):
                console.print("[yellow]Model destination doesn't exist, creating with auto-generated name...[/yellow]")
                training = replicate.trainings.create(
                    version="replicate/fast-flux-trainer:f463fbfc97389e10a2f443a8a84b6953b1058eafbf0c9af4d84457ff07cb04db",
                    input={
                        "input_images": dataset_file.urls["get"],
                        "trigger_word": trigger_word,
                        "steps": steps,
                        "learning_rate": learning_rate,
                        "resolution": "512,768,1024",
                    }
                )
            else:
                raise
        
        console.print(f"[green]Training started![/green]")
        console.print(f"[blue]Training ID:[/blue] {training.id}")
        console.print(f"[blue]Status URL:[/blue] https://replicate.com/p/{training.id}\n")
        
        # Poll for completion
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Training model...", total=None)
            
            while training.status not in ["succeeded", "failed", "canceled"]:
                time.sleep(30)  # Check every 30 seconds
                training.reload()
                
                if training.status == "processing":
                    if training.logs:
                        # Show last log line
                        last_log = training.logs.split("\n")[-2] if "\n" in training.logs else training.logs
                        progress.update(task, description=f"[cyan]Training: {last_log[:50]}...")
        
        if training.status == "succeeded":
            console.print("\n[bold green]Training completed successfully![/bold green]\n")
            
            model_id = training.output.get("model")
            if model_id:
                console.print(f"[green]Model ID:[/green] {model_id}")
                console.print(f"\n[yellow]Add this to your .env file:[/yellow]")
                console.print(f"FLUX_MODEL_ID={model_id}")
                console.print(f"FLUX_TRIGGER_WORD={trigger_word}\n")
                
                # Try to append to .env
                try:
                    with open(".env", "a") as f:
                        f.write(f"\n# FLUX Model (trained {time.strftime('%Y-%m-%d')})\n")
                        f.write(f"FLUX_MODEL_ID={model_id}\n")
                        f.write(f"FLUX_TRIGGER_WORD={trigger_word}\n")
                    console.print("[green]Added to .env file automatically![/green]")
                except Exception as e:
                    console.print(f"[yellow]Note: Could not auto-update .env: {e}[/yellow]")
            
            return True
        else:
            console.print(f"\n[red]Training {training.status}[/red]")
            if training.error:
                console.print(f"[red]Error: {training.error}[/red]")
            return False
    
    except Exception as e:
        console.print(f"\n[red]Error during training: {e}[/red]")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train a FLUX model on Replicate")
    parser.add_argument("--dataset", default="data.zip", help="Path to dataset zip file")
    parser.add_argument("--trigger", default="TANGO", help="Trigger word for the model")
    parser.add_argument("--steps", type=int, default=1500, help="Training steps")
    parser.add_argument("--lr", type=float, default=0.0001, help="Learning rate")
    parser.add_argument("--username", default="sundai-club", help="Replicate username")
    parser.add_argument("--model-name", default="presence", help="Model name")
    
    args = parser.parse_args()
    
    success = train_flux_model(
        dataset_path=args.dataset,
        trigger_word=args.trigger,
        steps=args.steps,
        learning_rate=args.lr,
        replicate_username=args.username,
        model_name=args.model_name
    )
    
    sys.exit(0 if success else 1)
