"""Command-line interface for pdfanon."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import __version__
from .core.anonymizer import Anonymizer, process_directory

app = typer.Typer(
    name="pdfanon",
    help="Anonymize PII in PDF files with realistic fake data.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"pdfanon version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit."
    ),
):
    """Anonymize PII in PDF files with realistic fake data."""
    pass


@app.command()
def anonymize(
    input_path: Path = typer.Argument(
        ...,
        help="PDF file or directory to anonymize.",
        exists=True,
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output path. For files: output filename. For directories: output directory.",
    ),
    mapping: Path = typer.Option(
        Path("pii_mapping.json"), "--mapping", "-m",
        help="Path to the mapping file for reversal.",
    ),
    seed: int = typer.Option(
        42, "--seed", "-s",
        help="Random seed for reproducible fake data.",
    ),
    format: str = typer.Option(
        "pdf", "--format", "-f",
        help="Output format: pdf or txt.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose",
        help="Show detailed output including detected PII.",
    ),
):
    """
    Anonymize PII in PDF files.

    Replaces personal information with realistic fake data while maintaining
    a mapping file for later reversal.

    Examples:
        pdfanon anonymize document.pdf
        pdfanon anonymize ./documents/ -o ./anonymized/
        pdfanon anonymize report.pdf -o report_safe.pdf --verbose
    """
    input_path = Path(input_path)
    format = format.lower()

    if format not in ("pdf", "txt"):
        console.print("[red]Error:[/red] Format must be 'pdf' or 'txt'")
        raise typer.Exit(1)

    if input_path.is_file():
        # Single file processing
        _anonymize_single_file(input_path, output, mapping, seed, format, verbose)
    else:
        # Directory processing
        _anonymize_directory(input_path, output, mapping, seed, format, verbose)


def _anonymize_single_file(
    input_path: Path,
    output: Optional[Path],
    mapping: Path,
    seed: int,
    format: str,
    verbose: bool,
):
    """Process a single PDF file."""
    # Determine output path
    if output is None:
        suffix = ".pdf" if format == "pdf" else ".txt"
        output = input_path.with_stem(f"{input_path.stem}_anonymized").with_suffix(suffix)
    else:
        output = Path(output)

    console.print(f"Processing: [cyan]{input_path.name}[/cyan]")

    try:
        anonymizer = Anonymizer(mapping_file=mapping, seed=seed)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Detecting PII...", total=None)
            count, detections = anonymizer.anonymize_pdf(input_path, output, format)

        if count == 0:
            console.print("[yellow]No PII detected.[/yellow] File copied without changes.")
        else:
            console.print(f"[green]Found and replaced {count} PII entities.[/green]")

            if verbose and detections:
                _show_detections_table(detections, anonymizer)

        console.print(f"\nOutput: [cyan]{output}[/cyan]")
        console.print(f"Mapping file: [cyan]{mapping}[/cyan]")
        console.print("\n[green]Done![/green] You can now safely share the anonymized file.")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _anonymize_directory(
    input_dir: Path,
    output: Optional[Path],
    mapping: Path,
    seed: int,
    format: str,
    verbose: bool,
):
    """Process all PDFs in a directory."""
    # Determine output directory
    if output is None:
        output = input_dir / "anonymized"
    else:
        output = Path(output)

    pdf_files = list(input_dir.glob("**/*.pdf"))

    if not pdf_files:
        console.print(f"[yellow]No PDF files found in {input_dir}[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found [cyan]{len(pdf_files)}[/cyan] PDF file(s) in [cyan]{input_dir}[/cyan]")
    console.print(f"Output directory: [cyan]{output}[/cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=len(pdf_files))

        def callback(current, total, filename):
            progress.update(task, completed=current, description=f"Processing {filename}")

        results = process_directory(
            input_dir=input_dir,
            output_dir=output,
            mapping_file=mapping,
            output_format=format,
            seed=seed,
            progress_callback=callback,
        )

    # Summary
    success_count = sum(1 for _, _, err in results if err is None)
    total_entities = sum(count for _, count, err in results if err is None)
    error_count = len(results) - success_count

    console.print(f"\n[green]Processed {success_count}/{len(results)} files.[/green]")
    console.print(f"Total PII entities replaced: [cyan]{total_entities}[/cyan]")

    if error_count > 0:
        console.print(f"\n[red]Errors ({error_count}):[/red]")
        for path, _, err in results:
            if err:
                console.print(f"  {path.name}: {err}")

    console.print(f"\nMapping file: [cyan]{mapping}[/cyan]")


def _show_detections_table(detections: list, anonymizer: Anonymizer):
    """Display a table of detected PII and their replacements."""
    table = Table(title="Detected PII")
    table.add_column("Type", style="cyan")
    table.add_column("Original", style="red")
    table.add_column("Replacement", style="green")
    table.add_column("Confidence", justify="right")

    mappings = {m["original"]: m["fake"] for m in anonymizer.get_mappings()}

    # Deduplicate by value
    seen = set()
    for d in detections:
        value = d["value"]
        if value in seen:
            continue
        seen.add(value)

        replacement = mappings.get(value, "N/A")
        # Truncate long values
        display_original = value[:30] + "..." if len(value) > 30 else value
        display_replacement = replacement[:30] + "..." if len(replacement) > 30 else replacement

        table.add_row(
            d["entity_type"],
            display_original,
            display_replacement,
            f"{d['score']:.2f}",
        )

    console.print(table)


@app.command()
def reverse(
    input_path: Path = typer.Argument(
        ...,
        help="Anonymized PDF or text file to restore.",
        exists=True,
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output path for restored file.",
    ),
    mapping: Path = typer.Option(
        Path("pii_mapping.json"), "--mapping", "-m",
        help="Path to the mapping file.",
    ),
    format: str = typer.Option(
        "pdf", "--format", "-f",
        help="Output format: pdf or txt.",
    ),
):
    """
    Restore original PII values from anonymized files.

    Uses the mapping file created during anonymization to reverse the process.

    Examples:
        pdfanon reverse document_anonymized.pdf
        pdfanon reverse document_anonymized.pdf -o document_restored.pdf
    """
    input_path = Path(input_path)
    format = format.lower()

    if not mapping.exists():
        console.print(f"[red]Error:[/red] Mapping file not found: {mapping}")
        console.print("The mapping file is required to reverse anonymization.")
        raise typer.Exit(1)

    # Determine output path
    if output is None:
        suffix = ".pdf" if format == "pdf" else ".txt"
        output = input_path.with_stem(f"{input_path.stem}_restored").with_suffix(suffix)
    else:
        output = Path(output)

    console.print(f"Reversing: [cyan]{input_path.name}[/cyan]")
    console.print(f"Using mapping: [cyan]{mapping}[/cyan]")

    try:
        anonymizer = Anonymizer(mapping_file=mapping)
        count = anonymizer.reverse_pdf(input_path, output, format)

        console.print(f"\n[green]Restored {count} PII values.[/green]")
        console.print(f"Output: [cyan]{output}[/cyan]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def mappings(
    mapping_file: Path = typer.Option(
        Path("pii_mapping.json"), "--mapping", "-m",
        help="Path to the mapping file.",
    ),
    format: str = typer.Option(
        "table", "--format", "-f",
        help="Output format: table, json, or csv.",
    ),
):
    """
    Display current PII mappings.

    Shows the mapping between original PII values and their fake replacements.

    Examples:
        pdfanon mappings
        pdfanon mappings --format json
        pdfanon mappings -m custom_mapping.json --format csv
    """
    if not mapping_file.exists():
        console.print(f"[yellow]No mapping file found at {mapping_file}[/yellow]")
        raise typer.Exit(0)

    from .faker.mapping import MappingStore
    store = MappingStore(mapping_file)
    all_mappings = store.get_mappings_list()

    if not all_mappings:
        console.print("[yellow]No mappings stored.[/yellow]")
        raise typer.Exit(0)

    format = format.lower()

    if format == "json":
        import json
        console.print(json.dumps(all_mappings, indent=2))

    elif format == "csv":
        console.print("original,fake,type,document")
        for m in all_mappings:
            # Escape commas and quotes in values
            orig = m["original"].replace('"', '""')
            fake = m["fake"].replace('"', '""')
            console.print(f'"{orig}","{fake}",{m["type"]},{m["document"]}')

    else:  # table
        table = Table(title=f"PII Mappings ({len(all_mappings)} entries)")
        table.add_column("Original", style="red")
        table.add_column("Fake", style="green")
        table.add_column("Type", style="cyan")

        for m in all_mappings:
            # Truncate long values
            orig = m["original"][:35] + "..." if len(m["original"]) > 35 else m["original"]
            fake = m["fake"][:35] + "..." if len(m["fake"]) > 35 else m["fake"]
            table.add_row(orig, fake, m["type"])

        console.print(table)


if __name__ == "__main__":
    app()
