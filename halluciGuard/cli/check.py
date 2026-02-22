"""
Check command - Analyze text for hallucinations.

Usage:
    halluciGuard check "Some text to analyze"
    halluciGuard check --file response.txt
    echo "Some text" | halluciGuard check
"""

import sys
import json
import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from enum import Enum

from halluciGuard import Guard
from halluciGuard.models import RiskLevel

app = typer.Typer(help="Analyze text for hallucinations", invoke_without_command=True)
console = Console()


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    markdown = "markdown"


def get_risk_color(risk_level: RiskLevel) -> str:
    """Get color for risk level."""
    colors = {
        RiskLevel.SAFE: "green",
        RiskLevel.LOW: "blue",
        RiskLevel.MEDIUM: "yellow",
        RiskLevel.HIGH: "orange1",
        RiskLevel.CRITICAL: "red",
    }
    return colors.get(risk_level, "white")


def get_risk_emoji(risk_level: RiskLevel) -> str:
    """Get emoji for risk level."""
    emojis = {
        RiskLevel.SAFE: "✅",
        RiskLevel.LOW: "🟢",
        RiskLevel.MEDIUM: "🟡",
        RiskLevel.HIGH: "🟠",
        RiskLevel.CRITICAL: "🔴",
    }
    return emojis.get(risk_level, "❓")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    text: Optional[str] = typer.Argument(
        None, help="Text to analyze for hallucinations"
    ),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Read text from file"
    ),
    model: str = typer.Option(
        "gpt-4o", "--model", "-m", help="Model to use for analysis"
    ),
    provider: str = typer.Option(
        "openai", "--provider", "-p", help="LLM provider (openai, anthropic, google, ollama)"
    ),
    output: OutputFormat = typer.Option(
        OutputFormat.text, "--output", "-o", help="Output format"
    ),
    threshold: float = typer.Option(
        0.7, "--threshold", "-t", help="Trust score threshold (0.0-1.0)"
    ),
    claims_only: bool = typer.Option(
        False, "--claims-only", help="Show only extracted claims"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed output"
    ),
):
    """
    Analyze text for hallucinations.
    
    [bold]Examples:[/bold]
        halluciGuard check "The Earth is flat."
        halluciGuard check --file response.txt
        echo "Some claim" | halluciGuard check
        halluciGuard check "Einstein won the Nobel for relativity." --output json
    """
    # If a subcommand is being invoked, skip
    if ctx.invoked_subcommand is not None:
        return
    
    # Get text from various sources
    if file:
        if not file.exists():
            console.print(f"[red]Error: File not found: {file}[/red]")
            raise typer.Exit(1)
        text_content = file.read_text()
    elif text:
        text_content = text
    elif not sys.stdin.isatty():
        # Read from stdin
        text_content = sys.stdin.read().strip()
    else:
        console.print("[red]Error: No text provided. Use positional argument, --file, or stdin.[/red]")
        console.print("\n[yellow]Usage:[/yellow]")
        console.print('  halluciGuard check "Your text here"')
        console.print("  halluciGuard check --file response.txt")
        console.print('  echo "Your text" | halluciGuard check')
        raise typer.Exit(1)
    
    if not text_content.strip():
        console.print("[red]Error: Empty text provided.[/red]")
        raise typer.Exit(1)
    
    try:
        # Initialize guard
        guard = Guard(provider=provider, model=model)
        
        # Analyze the text
        with console.status("[bold green]Analyzing text for hallucinations...[/bold green]"):
            result = guard.check(text_content)
        
        # Output based on format
        if output == OutputFormat.json:
            output_json(result, verbose)
        elif output == OutputFormat.markdown:
            output_markdown(result, verbose)
        else:
            output_text(result, verbose, claims_only)
        
        # Exit with appropriate code based on trust score
        if result.trust_score < threshold:
            raise typer.Exit(1)  # Low trust - potential hallucination
        else:
            raise typer.Exit(0)  # Acceptable trust score
            
    except ImportError as e:
        console.print(f"[red]Error: Missing dependency for provider '{provider}'[/red]")
        console.print(f"\n[yellow]Install with:[/yellow]")
        console.print(f"  pip install halluciGuard[{provider}]")
        raise typer.Exit(2)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(2)


def output_text(result, verbose: bool = False, claims_only: bool = False):
    """Output in human-readable text format."""
    risk_color = get_risk_color(result.risk_level)
    risk_emoji = get_risk_emoji(result.risk_level)
    
    # Main result panel
    console.print(Panel(
        f"[bold]Trust Score:[/bold] [cyan]{result.trust_score:.2%}[/cyan]\n"
        f"[bold]Risk Level:[/bold] [{risk_color}]{result.risk_level.value}[/{risk_color}] {risk_emoji}\n"
        f"[bold]Claims Found:[/bold] {len(result.claims)}",
        title="🛡️ HalluciGuard Analysis",
        border_style=risk_color,
    ))
    
    if claims_only:
        # Show only claims
        if result.claims:
            table = Table(title="Extracted Claims")
            table.add_column("#", style="cyan", width=3)
            table.add_column("Claim", style="white")
            table.add_column("Status", style="green")
            
            for i, claim in enumerate(result.claims, 1):
                table.add_row(str(i), claim.claim, "Analyzed")
            
            console.print(table)
        else:
            console.print("[yellow]No claims extracted from text.[/yellow]")
        return
    
    if verbose:
        # Show detailed breakdown
        console.print("\n[bold]📊 Detailed Analysis:[/bold]")
        
        # Claims table
        if result.claims:
            table = Table(title="Claims Analysis")
            table.add_column("#", style="cyan", width=3)
            table.add_column("Claim", style="white")
            table.add_column("Score", style="green", width=8)
            table.add_column("Risk", style="yellow", width=10)
            
            for i, claim in enumerate(result.claims, 1):
                claim_risk = "Low"
                if claim.verifiable:
                    claim_risk = "High" if claim.confidence < 0.5 else "Medium" if claim.confidence < 0.7 else "Low"
                table.add_row(
                    str(i),
                    claim.claim[:60] + "..." if len(claim.claim) > 60 else claim.claim,
                    f"{claim.confidence:.2f}",
                    claim_risk
                )
            
            console.print(table)
        
        # Signals breakdown
        if hasattr(result, 'signals') and result.signals:
            console.print("\n[bold]🔍 Detection Signals:[/bold]")
            for signal, value in result.signals.items():
                console.print(f"  • {signal}: [cyan]{value}[/cyan]")
        
        # Recommendations
        if result.recommendations:
            console.print("\n[bold]💡 Recommendations:[/bold]")
            for rec in result.recommendations:
                console.print(f"  • {rec}")
    
    # Quick summary
    if not verbose:
        if result.trust_score >= 0.8:
            console.print("\n[green]✓ Text appears reliable.[/green]")
        elif result.trust_score >= 0.6:
            console.print("\n[yellow]⚠ Some claims may need verification.[/yellow]")
        else:
            console.print("\n[red]✗ High risk of hallucinations detected.[/red]")
            if result.recommendations:
                console.print(f"[red]  {result.recommendations[0]}[/red]")


def output_json(result, verbose: bool = False):
    """Output in JSON format."""
    output_data = {
        "trust_score": result.trust_score,
        "risk_level": result.risk_level.value,
        "claims_count": len(result.claims),
        "claims": [
            {
                "claim": claim.claim,
                "verifiable": claim.verifiable,
                "confidence": claim.confidence,
            }
            for claim in result.claims
        ],
        "recommendations": result.recommendations,
    }
    
    if verbose and hasattr(result, 'signals'):
        output_data["signals"] = result.signals
    
    console.print_json(json.dumps(output_data, indent=2))


def output_markdown(result, verbose: bool = False):
    """Output in Markdown format."""
    risk_emoji = get_risk_emoji(result.risk_level)
    
    lines = [
        "# 🛡️ HalluciGuard Analysis",
        "",
        f"**Trust Score:** {result.trust_score:.2%}",
        f"**Risk Level:** {risk_emoji} {result.risk_level.value}",
        f"**Claims Found:** {len(result.claims)}",
        "",
    ]
    
    if result.claims:
        lines.append("## Claims")
        lines.append("")
        lines.append("| # | Claim | Confidence |")
        lines.append("|---|-------|------------|")
        for i, claim in enumerate(result.claims, 1):
            lines.append(f"| {i} | {claim.claim} | {claim.confidence:.2f} |")
        lines.append("")
    
    if result.recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for rec in result.recommendations:
            lines.append(f"- {rec}")
        lines.append("")
    
    console.print("\n".join(lines))


if __name__ == "__main__":
    app()
