"""
Config command - Manage HalluciGuard configuration.

Usage:
    halluciGuard config show
    halluciGuard config set openai_api_key sk-...
    halluciGuard config init
"""

import os
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Manage configuration")
console = Console()

# Config file location
CONFIG_DIR = Path.home() / ".halluciguard"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def get_config_dir() -> Path:
    """Get the config directory, creating it if needed."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def parse_toml(content: str) -> dict:
    """Simple TOML parser for basic key-value pairs."""
    result = {}
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            result[key] = value
    return result


def serialize_toml(config: dict) -> str:
    """Serialize config dict to TOML format."""
    lines = ["# HalluciGuard Configuration", ""]
    for key, value in sorted(config.items()):
        if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
            # Keep sensitive values quoted
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f'{key} = "{value}"')
    lines.append("")
    return "\n".join(lines)


def load_config() -> dict:
    """Load configuration from file."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        content = CONFIG_FILE.read_text()
        return parse_toml(content)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load config: {e}[/yellow]")
        return {}


def save_config(config: dict):
    """Save configuration to file."""
    get_config_dir()
    content = serialize_toml(config)
    CONFIG_FILE.write_text(content)
    # Set restrictive permissions on config file
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except Exception:
        pass


def mask_api_key(key: str) -> str:
    """Mask an API key for display."""
    if not key:
        return "[dim]not set[/dim]"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


@app.command()
def show():
    """Show current configuration."""
    config = load_config()
    
    console.print(Panel(
        f"[bold]Config File:[/bold] {CONFIG_FILE}",
        title="⚙️ HalluciGuard Configuration",
        border_style="cyan",
    ))
    
    if not config:
        console.print("\n[yellow]No configuration found.[/yellow]")
        console.print("Run [cyan]halluciGuard config init[/cyan] to create a default config.")
        return
    
    table = Table(title="Configuration Values")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    table.add_column("Source", style="dim")
    
    # Check environment variables too
    env_keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "TAVILY_API_KEY",
    ]
    
    for key in env_keys:
        env_value = os.environ.get(key)
        if env_value:
            table.add_row(key.lower(), mask_api_key(env_value), "env")
    
    for key, value in sorted(config.items()):
        # Mask sensitive values
        if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
            display_value = mask_api_key(value)
        else:
            display_value = value
        table.add_row(key, display_value, "file")
    
    console.print(table)


@app.command()
def set(
    key: str = typer.Argument(..., help="Configuration key to set"),
    value: str = typer.Argument(..., help="Value to set"),
):
    """Set a configuration value.
    
    [bold]Examples:[/bold]
        halluciGuard config set openai_api_key sk-...
        halluciGuard config set default_model gpt-4o
        halluciGuard config set threshold 0.7
    """
    config = load_config()
    config[key] = value
    save_config(config)
    
    # Mask sensitive values in output
    if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
        display_value = mask_api_key(value)
    else:
        display_value = value
    
    console.print(f"[green]✓[/green] Set [cyan]{key}[/cyan] = {display_value}")
    console.print(f"[dim]Saved to {CONFIG_FILE}[/dim]")


@app.command()
def get(
    key: str = typer.Argument(..., help="Configuration key to get"),
):
    """Get a configuration value."""
    config = load_config()
    
    # Check file config first
    if key in config:
        value = config[key]
        if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
            console.print(mask_api_key(value))
        else:
            console.print(value)
        return
    
    # Check environment
    env_key = key.upper()
    env_value = os.environ.get(env_key)
    if env_value:
        if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
            console.print(mask_api_key(env_value))
        else:
            console.print(env_value)
        return
    
    console.print(f"[yellow]Key not found: {key}[/yellow]")
    raise typer.Exit(1)


@app.command()
def unset(
    key: str = typer.Argument(..., help="Configuration key to remove"),
):
    """Remove a configuration value."""
    config = load_config()
    
    if key not in config:
        console.print(f"[yellow]Key not found: {key}[/yellow]")
        return
    
    del config[key]
    save_config(config)
    console.print(f"[green]✓[/green] Removed [cyan]{key}[/cyan]")


@app.command()
def init():
    """Initialize configuration with default values."""
    get_config_dir()
    
    if CONFIG_FILE.exists():
        console.print("[yellow]Config file already exists.[/yellow]")
        overwrite = typer.confirm("Overwrite?", default=False)
        if not overwrite:
            console.print("Cancelled.")
            return
    
    # Create default config
    default_config = {
        "default_model": "gpt-4o-mini",
        "default_provider": "openai",
        "threshold": "0.7",
    }
    
    save_config(default_config)
    
    console.print(Panel(
        f"[green]✓[/green] Created config file: {CONFIG_FILE}\n\n"
        f"[bold]Next steps:[/bold]\n"
        f"  1. Set your API keys:\n"
        f"     [cyan]halluciGuard config set openai_api_key sk-...[/cyan]\n"
        f"     [cyan]halluciGuard config set anthropic_api_key sk-ant-...[/cyan]\n\n"
        f"  2. Or set environment variables:\n"
        f"     [dim]export OPENAI_API_KEY=sk-...[/dim]\n\n"
        f"  3. Verify configuration:\n"
        f"     [cyan]halluciGuard config show[/cyan]",
        title="⚙️ Configuration Initialized",
        border_style="green",
    ))


@app.command()
def path():
    """Show the configuration file path."""
    console.print(f"Config directory: [cyan]{CONFIG_DIR}[/cyan]")
    console.print(f"Config file: [cyan]{CONFIG_FILE}[/cyan]")
    
    if CONFIG_FILE.exists():
        console.print(f"Status: [green]exists[/green]")
    else:
        console.print(f"Status: [yellow]not found[/yellow]")


@app.command()
def list():
    """List all configuration keys."""
    config = load_config()
    
    if not config:
        console.print("[yellow]No configuration found.[/yellow]")
        return
    
    console.print("[bold]Configuration Keys:[/bold]")
    for key in sorted(config.keys()):
        console.print(f"  • {key}")


if __name__ == "__main__":
    app()
