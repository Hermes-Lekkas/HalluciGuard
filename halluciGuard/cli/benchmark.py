"""
Benchmark command - Run hallucination benchmark suite.

Usage:
    halluciGuard benchmark --models gpt-4o,claude-sonnet-4.6
    halluciGuard benchmark --categories science,history
    halluciGuard benchmark --output ./results/
"""

import os
import typer
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.live import Live
from enum import Enum

from halluciGuard import Guard
from halluciGuard.leaderboard import (
    BenchmarkRunner,
    BenchmarkDataset,
    LeaderboardExporter,
)
from halluciGuard.leaderboard.dataset import get_default_dataset, Category

app = typer.Typer(help="Run benchmark suite", invoke_without_command=True)
console = Console()


# Model configurations
MODEL_CONFIGS = {
    # OpenAI models
    "gpt-4o": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    "gpt-4o-mini": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    "gpt-5.2-instant": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    "gpt-5.2-thinking": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    "gpt-5.3-codex": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    
    # Anthropic models
    "claude-3-5-sonnet-20240620": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    "claude-3-opus-20240229": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    "claude-opus-4.6": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    "claude-sonnet-4.6": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    "claude-haiku-4-5-20251001": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    
    # Google models
    "gemini-1.5-pro": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
    "gemini-1.5-flash": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
    "gemini-3.1-pro": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
    "gemini-3-flash": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
    "gemini-3-deep-think": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
    
    # Ollama models (local)
    "llama3.2": {"provider": "ollama", "env_key": None},
    "llama3.1": {"provider": "ollama", "env_key": None},
    "mistral": {"provider": "ollama", "env_key": None},
}


class OutputFormat(str, Enum):
    all = "all"
    json = "json"
    html = "html"
    markdown = "markdown"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    models: str = typer.Option(
        "gpt-4o-mini", "--models", "-m", help="Comma-separated list of models to benchmark"
    ),
    output: str = typer.Option(
        "benchmarks", "--output", "-o", help="Output directory for results"
    ),
    categories: Optional[str] = typer.Option(
        None, "--categories", "-c", help="Comma-separated list of categories to test"
    ),
    max_cases: Optional[int] = typer.Option(
        None, "--max-cases", help="Maximum number of cases per model"
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.all, "--format", "-f", help="Output format"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="List test cases without running"
    ),
    list_models: bool = typer.Option(
        False, "--list-models", "-l", help="List available models and exit"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed output"
    ),
):
    """
    Run hallucination benchmarks against multiple LLM models.
    
    [bold]Examples:[/bold]
        halluciGuard benchmark --models gpt-4o,claude-sonnet-4.6
        halluciGuard benchmark --categories science,history
        halluciGuard benchmark --max-cases 10 --dry-run
        halluciGuard benchmark --format html
    """
    # If a subcommand is being invoked, skip
    if ctx.invoked_subcommand is not None:
        return
    
    if list_models:
        show_available_models()
        return
    
    model_list = [m.strip() for m in models.split(",")]
    category_list = [c.strip() for c in categories.split(",")] if categories else None
    
    # Validate models
    invalid_models = [m for m in model_list if m not in MODEL_CONFIGS]
    if invalid_models:
        console.print(f"[red]Error: Unknown models: {', '.join(invalid_models)}[/red]")
        console.print("\n[yellow]Run with --list-models to see available models.[/yellow]")
        raise typer.Exit(1)
    
    # Load dataset
    dataset = get_default_dataset()
    
    # Filter by categories if specified
    if category_list:
        try:
            category_enums = [Category(c) for c in category_list]
        except ValueError as e:
            console.print(f"[red]Error: Invalid category. {e}[/red]")
            console.print(f"[yellow]Valid categories: {', '.join([c.value for c in Category])}[/yellow]")
            raise typer.Exit(1)
        
        cases = []
        for cat in category_enums:
            cases.extend(dataset.get_by_category(cat))
        dataset = BenchmarkDataset(cases=cases)
        console.print(f"[cyan]Filtered to {len(cases)} cases in categories: {', '.join(category_list)}[/cyan]")
    
    # Limit cases if specified
    if max_cases:
        dataset = BenchmarkDataset(cases=dataset.cases[:max_cases])
        console.print(f"[cyan]Limited to {len(dataset.cases)} cases[/cyan]")
    
    if dry_run:
        show_dry_run(dataset)
        return
    
    # Check API keys
    missing_keys = check_api_keys(model_list)
    if missing_keys:
        console.print(f"[yellow]Warning: Missing API keys for: {', '.join(missing_keys)}[/yellow]")
        console.print("[yellow]Some models may be skipped.[/yellow]\n")
    
    # Run benchmarks
    run_benchmarks(model_list, dataset, output, format, verbose)


def show_available_models():
    """Show table of available models."""
    table = Table(title="Available Models")
    table.add_column("Model", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("API Key Required", style="yellow")
    
    for model, config in sorted(MODEL_CONFIGS.items()):
        env_key = config["env_key"] or "None (local)"
        table.add_row(model, config["provider"], env_key)
    
    console.print(table)


def show_dry_run(dataset):
    """Show test cases without running."""
    console.print(Panel(
        f"[bold]Benchmark Dataset[/bold]\n"
        f"Total Cases: [cyan]{len(dataset.cases)}[/cyan]",
        title="🧪 Dry Run",
        border_style="yellow",
    ))
    
    table = Table(title="Test Cases")
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Category", style="green", width=12)
    table.add_column("Prompt Preview", style="white")
    
    for case in dataset.cases:
        prompt_preview = case.prompt[:60] + "..." if len(case.prompt) > 60 else case.prompt
        table.add_row(case.id, case.category.value, prompt_preview)
    
    console.print(table)


def check_api_keys(models: List[str]) -> List[str]:
    """Check which API keys are missing."""
    missing = []
    for model in models:
        config = MODEL_CONFIGS[model]
        if config["env_key"] and not os.environ.get(config["env_key"]):
            missing.append(config["env_key"])
    return missing


def create_guard_for_model(model: str):
    """Create a Guard instance for the specified model."""
    config = MODEL_CONFIGS[model]
    provider = config["provider"]
    env_key = config["env_key"]
    
    api_key = os.environ.get(env_key) if env_key else None
    
    try:
        guard = Guard(provider=provider, api_key=api_key)
        return guard
    except Exception as e:
        console.print(f"[red]Failed to initialize {model}: {e}[/red]")
        return None


def run_benchmarks(models: List[str], dataset, output_dir: str, format: OutputFormat, verbose: bool):
    """Run benchmarks for all models."""
    runner = BenchmarkRunner(dataset=dataset, output_dir=output_dir)
    exporter = LeaderboardExporter(output_dir=output_dir)
    
    all_scores = []
    
    console.print(Panel(
        f"[bold]Models:[/bold] {', '.join(models)}\n"
        f"[bold]Cases:[/bold] {len(dataset.cases)}\n"
        f"[bold]Output:[/bold] {output_dir}",
        title="🚀 Running Benchmarks",
        border_style="green",
    ))
    
    for model in models:
        console.print(f"\n[bold cyan]▶ Testing: {model}[/bold cyan]")
        
        guard = create_guard_for_model(model)
        if guard is None:
            console.print(f"[yellow]Skipping {model} - initialization failed[/yellow]")
            continue
        
        # Progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Running {model}...", total=len(dataset.cases))
            
            def progress_callback(current: int, total: int):
                progress.update(task, completed=current)
            
            try:
                results = runner.run_model(guard, model, progress_callback=progress_callback)
                score = runner.aggregate_scores(results)
                all_scores.append(score)
                
                console.print(f"  [green]✓[/green] Trust: [cyan]{score.avg_trust_score:.2%}[/cyan] | "
                            f"Hallucination: [yellow]{score.hallucination_rate:.1%}[/yellow] | "
                            f"Latency: [dim]{score.avg_latency_seconds:.2f}s[/dim]")
                
            except Exception as e:
                console.print(f"  [red]✗ Failed: {e}[/red]")
                if verbose:
                    console.print_exception()
                continue
    
    if not all_scores:
        console.print("\n[red]Error: No benchmarks completed successfully.[/red]")
        raise typer.Exit(1)
    
    # Export results
    console.print(f"\n[bold]📊 Generating Results...[/bold]")
    
    if format in (OutputFormat.all, OutputFormat.json):
        json_path = exporter.to_json(all_scores, "leaderboard.json")
        console.print(f"  [green]✓[/green] JSON: {json_path}")
    
    if format in (OutputFormat.all, OutputFormat.html):
        html_path = exporter.to_html(
            all_scores,
            "leaderboard.html",
            title="HalluciGuard Leaderboard",
            description="Public benchmark of LLM hallucination rates",
        )
        console.print(f"  [green]✓[/green] HTML: {html_path}")
    
    if format in (OutputFormat.all, OutputFormat.markdown):
        md_path = exporter.to_markdown(all_scores, "leaderboard.md")
        console.print(f"  [green]✓[/green] Markdown: {md_path}")
    
    # Show leaderboard
    show_leaderboard(all_scores)


def show_leaderboard(scores):
    """Display the final leaderboard."""
    console.print(f"\n[bold]🏆 LEADERBOARD[/bold]")
    
    table = Table()
    table.add_column("Rank", style="cyan", width=6)
    table.add_column("Model", style="white")
    table.add_column("Hallucination", style="red")
    table.add_column("Trust Score", style="green")
    table.add_column("Latency", style="yellow")
    
    sorted_scores = sorted(scores, key=lambda s: s.hallucination_rate)
    
    for rank, score in enumerate(sorted_scores, 1):
        medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else "  "))
        
        # Color based on hallucination rate
        if score.hallucination_rate < 0.1:
            hall_color = "green"
        elif score.hallucination_rate < 0.3:
            hall_color = "yellow"
        else:
            hall_color = "red"
        
        table.add_row(
            f"{medal} #{rank}",
            score.model,
            f"[{hall_color}]{score.hallucination_rate:.1%}[/{hall_color}]",
            f"{score.avg_trust_score:.2%}",
            f"{score.avg_latency_seconds:.2f}s"
        )
    
    console.print(table)


if __name__ == "__main__":
    app()
