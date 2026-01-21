"""Tool to annotate images in dataset for better FLUX training."""

import os
import sys
import zipfile
import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table

console = Console()


def extract_and_annotate(
    zip_path: str = "data.zip",
    output_dir: str = "dataset_annotated",
    use_jsonl: bool = True
):
    """
    Extract images and create annotation template.
    
    Args:
        zip_path: Path to the dataset zip file
        output_dir: Directory to extract and annotate
        use_jsonl: Use metadata.jsonl format (True) or individual .txt files (False)
    """
    console.print("\n[bold cyan]Dataset Annotation Tool[/bold cyan]\n")
    
    if not os.path.exists(zip_path):
        console.print(f"[red]Error: {zip_path} not found[/red]")
        return False
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Extract images
    console.print(f"[yellow]Extracting images from {zip_path}...[/yellow]")
    
    image_files = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for file_info in zf.filelist:
            # Skip directories and non-image files
            if file_info.is_dir():
                continue
            
            filename = os.path.basename(file_info.filename)
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                # Extract to output directory
                zf.extract(file_info, output_path)
                
                # Get the extracted file path
                extracted_path = output_path / file_info.filename
                
                # Move to root of output dir if in subdirectory
                if extracted_path.parent != output_path:
                    new_path = output_path / filename
                    extracted_path.rename(new_path)
                    # Clean up empty subdirectories
                    try:
                        extracted_path.parent.rmdir()
                    except:
                        pass
                    extracted_path = new_path
                
                image_files.append(filename)
    
    console.print(f"[green]Extracted {len(image_files)} images[/green]\n")
    
    if not image_files:
        console.print("[red]No images found in zip file[/red]")
        return False
    
    # Show images
    table = Table(title="Images to Annotate")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Filename", style="green")
    
    for idx, img in enumerate(image_files, 1):
        table.add_row(str(idx), img)
    
    console.print(table)
    console.print()
    
    # Create annotation template
    if use_jsonl:
        _create_jsonl_template(output_path, image_files)
    else:
        _create_txt_templates(output_path, image_files)
    
    # Show instructions
    _show_instructions(output_path, use_jsonl)
    
    return True


def _create_jsonl_template(output_path: Path, image_files: list):
    """Create metadata.jsonl template."""
    jsonl_path = output_path / "metadata.jsonl"
    
    console.print("[yellow]Creating metadata.jsonl template...[/yellow]")
    
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for img_file in image_files:
            entry = {
                "file_name": img_file,
                "text": f"TANGO [DESCRIBE THIS IMAGE: {img_file}]"
            }
            f.write(json.dumps(entry) + '\n')
    
    console.print(f"[green]Created {jsonl_path}[/green]\n")


def _create_txt_templates(output_path: Path, image_files: list):
    """Create individual .txt caption files."""
    console.print("[yellow]Creating .txt caption files...[/yellow]")
    
    for img_file in image_files:
        txt_file = output_path / f"{Path(img_file).stem}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"TANGO [DESCRIBE THIS IMAGE: {img_file}]")
    
    console.print(f"[green]Created {len(image_files)} caption files[/green]\n")


def _show_instructions(output_path: Path, use_jsonl: bool):
    """Show annotation instructions."""
    
    if use_jsonl:
        instructions = f"""
[bold cyan]Next Steps:[/bold cyan]

1. Open: [green]{output_path / 'metadata.jsonl'}[/green]

2. For each line, replace the placeholder with a description:
   
   [yellow]Before:[/yellow]
   {{"file_name": "image1.jpg", "text": "TANGO [DESCRIBE THIS IMAGE: image1.jpg]"}}
   
   [green]After:[/green]
   {{"file_name": "image1.jpg", "text": "TANGO professional logo with modern design elements"}}

3. Guidelines:
   - Start each caption with "TANGO" (your trigger word)
   - Be descriptive but concise (1-2 sentences)
   - Describe the style, subject, colors, mood
   - Be consistent in your descriptions

4. After annotating, create the new zip:
   [cyan]uv run python scripts/annotate_dataset.py --rezip[/cyan]
"""
    else:
        instructions = f"""
[bold cyan]Next Steps:[/bold cyan]

1. Go to folder: [green]{output_path}[/green]

2. Edit each .txt file with a description for its corresponding image:
   
   [yellow]Before:[/yellow]
   TANGO [DESCRIBE THIS IMAGE: image1.jpg]
   
   [green]After:[/green]
   TANGO professional logo with modern design elements

3. Guidelines:
   - Start each caption with "TANGO" (your trigger word)
   - Be descriptive but concise (1-2 sentences)
   - Describe the style, subject, colors, mood
   - Be consistent in your descriptions

4. After annotating, create the new zip:
   [cyan]uv run python scripts/annotate_dataset.py --rezip[/cyan]
"""
    
    console.print(Panel(instructions, border_style="blue", title="Annotation Instructions"))


def create_annotated_zip(
    input_dir: str = "dataset_annotated",
    output_zip: str = "data_annotated.zip"
):
    """
    Create a new zip file with images and annotations.
    
    Args:
        input_dir: Directory containing annotated images
        output_zip: Output zip file path
    """
    console.print("\n[bold cyan]Creating Annotated Dataset[/bold cyan]\n")
    
    input_path = Path(input_dir)
    if not input_path.exists():
        console.print(f"[red]Error: {input_dir} not found[/red]")
        console.print("Run without --rezip first to extract and annotate")
        return False
    
    # Collect files
    files_to_zip = []
    for file_path in input_path.glob("*"):
        if file_path.is_file():
            files_to_zip.append(file_path)
    
    if not files_to_zip:
        console.print(f"[red]No files found in {input_dir}[/red]")
        return False
    
    # Create zip
    console.print(f"[yellow]Creating {output_zip}...[/yellow]")
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in files_to_zip:
            zf.write(file_path, file_path.name)
    
    file_size_mb = os.path.getsize(output_zip) / (1024 * 1024)
    
    console.print(f"[green]Created {output_zip} ({file_size_mb:.1f} MB)[/green]")
    console.print(f"[green]Included {len(files_to_zip)} files[/green]\n")
    
    console.print(Panel(
        f"[bold green]Ready for training![/bold green]\n\n"
        f"Use this annotated dataset:\n"
        f"[cyan]uv run python -m src.main train-model --dataset {output_zip}[/cyan]",
        border_style="green"
    ))
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Annotate dataset for FLUX training")
    parser.add_argument("--rezip", action="store_true", help="Create annotated zip from edited files")
    parser.add_argument("--input", default="data.zip", help="Input zip file")
    parser.add_argument("--output-dir", default="dataset_annotated", help="Output directory for annotation")
    parser.add_argument("--output-zip", default="data_annotated.zip", help="Output annotated zip file")
    parser.add_argument("--use-txt", action="store_true", help="Use individual .txt files instead of metadata.jsonl")
    
    args = parser.parse_args()
    
    if args.rezip:
        success = create_annotated_zip(args.output_dir, args.output_zip)
    else:
        success = extract_and_annotate(
            args.input,
            args.output_dir,
            use_jsonl=not args.use_txt
        )
    
    sys.exit(0 if success else 1)
