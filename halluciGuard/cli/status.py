"""
Status command - Check provider/API status.

Usage:
    halluciGuard status
    halluciGuard status --provider openai
    halluciGuard status --verbose
"""

import os
import time
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(help="Check provider/API status", invoke_without_command=True)
console = Console()


# Provider configurations
PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-5.2-instant"],
        "package": "openai",
    },
    "anthropic": {
        "name": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "models": ["claude-sonnet-4.6", "claude-opus-4.6"],
        "package": "anthropic",
    },
    "google": {
        "name": "Google AI",
        "env_key": "GOOGLE_API_KEY",
        "models": ["gemini-3-flash", "gemini-3.1-pro"],
        "package": "google-genai",
    },
    "ollama": {
        "name": "Ollama (Local)",
        "env_key": None,
        "models": ["llama3.2", "mistral"],
        "package": None,
        "url": "http://localhost:11434",
    },
}


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Check specific provider only"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed information"
    ),
):
    """
    Check the status of LLM providers and API connections.
    
    [bold]Examples:[/bold]
        halluciGuard status
        halluciGuard status --provider openai
        halluciGuard status --verbose
    """
    # If a subcommand is being invoked, skip
    if ctx.invoked_subcommand is not None:
        return
    
    if provider and provider not in PROVIDERS:
        console.print(f"[red]Error: Unknown provider '{provider}'[/red]")
        console.print(f"[yellow]Available providers: {', '.join(PROVIDERS.keys())}[/yellow]")
        raise typer.Exit(1)
    
    providers_to_check = [provider] if provider else list(PROVIDERS.keys())
    
    console.print(Panel(
        "[bold]Checking provider status...[/bold]",
        title="🔍 HalluciGuard Status",
        border_style="cyan",
    ))
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for prov in providers_to_check:
            task = progress.add_task(f"Checking {prov}...", total=None)
            result = check_provider(prov, verbose)
            results.append(result)
            progress.update(task, description=f"Checked {prov}")
    
    # Display results
    display_results(results, verbose)


def check_provider(provider: str, verbose: bool) -> dict:
    """Check a single provider's status."""
    config = PROVIDERS[provider]
    result = {
        "provider": provider,
        "name": config["name"],
        "status": "unknown",
        "api_key": False,
        "package": False,
        "connection": False,
        "latency": None,
        "error": None,
    }
    
    # Check package
    if config["package"]:
        try:
            __import__(config["package"].replace("-", "_"))
            result["package"] = True
        except ImportError:
            result["status"] = "error"
            result["error"] = f"Package not installed: {config['package']}"
            return result
    else:
        result["package"] = True  # No package required
    
    # Check API key
    if config["env_key"]:
        if os.environ.get(config["env_key"]):
            result["api_key"] = True
        else:
            result["status"] = "warning"
            result["error"] = f"API key not set: {config['env_key']}"
            return result
    else:
        result["api_key"] = True  # No API key required
    
    # Try to connect
    try:
        start_time = time.time()
        
        if provider == "openai":
            connection_ok = test_openai_connection(verbose)
        elif provider == "anthropic":
            connection_ok = test_anthropic_connection(verbose)
        elif provider == "google":
            connection_ok = test_google_connection(verbose)
        elif provider == "ollama":
            connection_ok = test_ollama_connection(verbose)
        else:
            connection_ok = False
        
        result["latency"] = time.time() - start_time
        result["connection"] = connection_ok
        
        if connection_ok:
            result["status"] = "ok"
        else:
            result["status"] = "error"
            result["error"] = "Connection failed"
            
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:50]
    
    return result


def test_openai_connection(verbose: bool) -> bool:
    """Test OpenAI API connection."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        # Simple models list call (lightweight)
        client.models.list()
        return True
    except Exception as e:
        if verbose:
            console.print(f"[dim]  OpenAI error: {e}[/dim]")
        return False


def test_anthropic_connection(verbose: bool) -> bool:
    """Test Anthropic API connection."""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        # Simple message to test connection
        client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        return True
    except Exception as e:
        if verbose:
            console.print(f"[dim]  Anthropic error: {e}[/dim]")
        return False


def test_google_connection(verbose: bool) -> bool:
    """Test Google AI API connection."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        # List models
        list(genai.list_models())
        return True
    except Exception as e:
        if verbose:
            console.print(f"[dim]  Google error: {e}[/dim]")
        return False


def test_ollama_connection(verbose: bool) -> bool:
    """Test Ollama local connection."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        if verbose:
            console.print(f"[dim]  Ollama error: {e}[/dim]")
        return False


def display_results(results: list, verbose: bool):
    """Display status results in a table."""
    table = Table(title="Provider Status")
    table.add_column("Provider", style="cyan", width=12)
    table.add_column("Status", width=10)
    table.add_column("API Key", width=8)
    table.add_column("Package", width=8)
    table.add_column("Connection", width=10)
    
    if verbose:
        table.add_column("Latency", width=8)
        table.add_column("Details", style="dim")
    
    for result in results:
        # Status with emoji
        if result["status"] == "ok":
            status = "[green]✓ OK[/green]"
        elif result["status"] == "warning":
            status = "[yellow]⚠ Warning[/yellow]"
        else:
            status = "[red]✗ Error[/red]"
        
        # API Key status
        api_key = "[green]✓[/green]" if result["api_key"] else "[red]✗[/red]"
        
        # Package status
        package = "[green]✓[/green]" if result["package"] else "[red]✗[/red]"
        
        # Connection status
        connection = "[green]✓[/green]" if result["connection"] else "[red]✗[/red]"
        
        row = [
            result["name"],
            status,
            api_key,
            package,
            connection,
        ]
        
        if verbose:
            latency = f"{result['latency']:.2f}s" if result["latency"] else "-"
            error = result["error"] or ""
            row.extend([latency, error])
        
        table.add_row(*row)
    
    console.print(table)
    
    # Summary
    ok_count = sum(1 for r in results if r["status"] == "ok")
    total = len(results)
    
    console.print(f"\n[bold]Summary:[/bold] {ok_count}/{total} providers available")
    
    if ok_count == 0:
        console.print("\n[yellow]No providers available. Check your API keys and installation.[/yellow]")
        console.print("\n[dim]Run 'halluciGuard config init' to set up configuration.[/dim]")


if __name__ == "__main__":
    app()
