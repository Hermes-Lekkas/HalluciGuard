"""
Serve command - Start the HalluciGuard API server.

Usage:
    halluciGuard serve
    halluciGuard serve --port 8080 --host 0.0.0.0
    halluciGuard serve --reload
"""

import os
import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="Start API server", invoke_without_command=True)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    host: str = typer.Option(
        "127.0.0.1", "--host", "-h", help="Host to bind to"
    ),
    port: int = typer.Option(
        8000, "--port", "-p", help="Port to bind to"
    ),
    reload: bool = typer.Option(
        False, "--reload", "-r", help="Enable auto-reload for development"
    ),
    workers: int = typer.Option(
        1, "--workers", "-w", help="Number of worker processes"
    ),
    provider: str = typer.Option(
        "openai", "--provider", help="Default LLM provider"
    ),
    model: str = typer.Option(
        "gpt-4o-mini", "--model", "-m", help="Default model for analysis"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="API key for the server (protects endpoints)"
    ),
    log_level: str = typer.Option(
        "info", "--log-level", "-l", help="Log level (debug, info, warning, error)"
    ),
):
    """
    Start the HalluciGuard API server.
    
    [bold]Examples:[/bold]
        halluciGuard serve
        halluciGuard serve --port 8080 --host 0.0.0.0
        halluciGuard serve --reload --log-level debug
    
    [bold]API Endpoints:[/bold]
        POST /analyze - Analyze text for hallucinations
        GET /health   - Health check endpoint
    """
    # If a subcommand is being invoked, skip
    if ctx.invoked_subcommand is not None:
        return
    
    try:
        import uvicorn
    except ImportError:
        console.print("[red]Error: uvicorn not installed.[/red]")
        console.print("\n[yellow]Install with:[/yellow]")
        console.print("  pip install halluciGuard[server]")
        raise typer.Exit(1)
    
    try:
        from fastapi import FastAPI
    except ImportError:
        console.print("[red]Error: fastapi not installed.[/red]")
        console.print("\n[yellow]Install with:[/yellow]")
        console.print("  pip install halluciGuard[server]")
        raise typer.Exit(1)
    
    # Check for API keys
    env_key = f"{provider.upper()}_API_KEY"
    if not os.environ.get(env_key) and provider != "ollama":
        console.print(f"[yellow]Warning: {env_key} not set.[/yellow]")
        console.print("[yellow]Server will start but analysis may be limited.[/yellow]\n")
    
    # Show startup info
    console.print(Panel(
        f"[bold]Host:[/bold] {host}\n"
        f"[bold]Port:[/bold] {port}\n"
        f"[bold]Provider:[/bold] {provider}\n"
        f"[bold]Model:[/bold] {model}\n"
        f"[bold]Workers:[/bold] {workers}\n"
        f"[bold]Reload:[/bold] {'Enabled' if reload else 'Disabled'}\n"
        f"[bold]Log Level:[/bold] {log_level}",
        title="🚀 HalluciGuard API Server",
        border_style="green",
    ))
    
    console.print(f"\n[cyan]Starting server at http://{host}:{port}[/cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    # Set environment variables for the server
    os.environ["HALLUCIGUARD_PROVIDER"] = provider
    os.environ["HALLUCIGUARD_MODEL"] = model
    if api_key:
        os.environ["HALLUCIGUARD_SERVER_KEY"] = api_key
    
    # Run the server
    uvicorn.run(
        "halluciGuard.server:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,  # Reload doesn't work with multiple workers
        log_level=log_level,
    )


if __name__ == "__main__":
    app()
