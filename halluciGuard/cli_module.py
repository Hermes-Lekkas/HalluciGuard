"""
HalluciGuard CLI - Command-line interface for AI hallucination detection.

Usage:
    halluciGuard --help
    halluciGuard check "Some text to analyze"
    halluciGuard chat --model gpt-4o
    halluciGuard benchmark --models gpt-4o,claude-sonnet-4.6
    halluciGuard serve --port 8080
    halluciGuard config set openai_api_key sk-...
    halluciGuard status
"""

import typer
from rich.console import Console
from rich.panel import Panel
from typing import Optional
import sys

from halluciGuard import __version__
from halluciGuard.cli import check, chat, benchmark, serve, config, status

app = typer.Typer(
    name="halluciGuard",
    help="🛡️ Open-source AI hallucination detection middleware for LLM pipelines",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()

# Register subcommands
app.add_typer(check.app, name="check", help="Analyze text for hallucinations")
app.add_typer(chat.app, name="chat", help="Interactive chat with hallucination detection")
app.add_typer(benchmark.app, name="benchmark", help="Run benchmark suite")
app.add_typer(serve.app, name="serve", help="Start API server")
app.add_typer(config.app, name="config", help="Manage configuration")
app.add_typer(status.app, name="status", help="Check provider/API status")


def version_callback(value: bool):
    """Callback for --version flag."""
    if value:
        console.print(Panel(
            f"[bold green]HalluciGuard[/bold green] version [cyan]{__version__}[/cyan]\n"
            f"AI Hallucination Detection Middleware",
            title="🛡️ HalluciGuard",
            border_style="green",
        ))
        raise typer.Exit(0)


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit", callback=version_callback, is_eager=True
    ),
):
    """
    🛡️ HalluciGuard - AI Hallucination Detection
    
    Detect and score hallucinations in LLM outputs with multi-signal analysis.
    
    [bold]Examples:[/bold]
        halluciGuard check "The Earth is flat."
        halluciGuard chat --model gpt-4o
        halluciGuard benchmark --models gpt-4o
        halluciGuard serve --port 8080
    """
    pass


def cli_entry():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli_entry()
