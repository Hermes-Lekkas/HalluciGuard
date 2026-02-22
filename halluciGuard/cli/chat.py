"""
Chat command - Interactive chat with hallucination detection.

Usage:
    halluciGuard chat --model gpt-4o
    halluciGuard chat --provider anthropic --model claude-sonnet-4.6
"""

import sys
import typer
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.live import Live
from rich.table import Table

from halluciGuard import Guard
from halluciGuard.models import RiskLevel

app = typer.Typer(help="Interactive chat with hallucination detection", invoke_without_command=True)
console = Console()


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
    model: str = typer.Option(
        "gpt-4o", "--model", "-m", help="Model to use for chat"
    ),
    provider: str = typer.Option(
        "openai", "--provider", "-p", help="LLM provider (openai, anthropic, google, ollama)"
    ),
    system: Optional[str] = typer.Option(
        None, "--system", "-s", help="System prompt for the chat"
    ),
    temperature: float = typer.Option(
        0.7, "--temperature", help="Temperature for responses"
    ),
    show_claims: bool = typer.Option(
        False, "--show-claims", help="Show extracted claims after each response"
    ),
    auto_verify: bool = typer.Option(
        False, "--auto-verify", help="Automatically verify claims with web search"
    ),
    history: bool = typer.Option(
        True, "--history/--no-history", help="Keep conversation history"
    ),
):
    """
    Start an interactive chat session with real-time hallucination detection.
    
    [bold]Examples:[/bold]
        halluciGuard chat --model gpt-4o
        halluciGuard chat --provider anthropic --model claude-sonnet-4.6
        halluciGuard chat --system "You are a helpful science tutor."
    
    [bold]Commands during chat:[/bold]
        /check <text>  - Check specific text for hallucinations
        /claims        - Show claims from last response
        /history       - Show conversation history
        /clear         - Clear conversation history
        /quit or /exit - Exit the chat
    """
    # If a subcommand is being invoked, skip
    if ctx.invoked_subcommand is not None:
        return
    
    try:
        # Initialize guard
        guard = Guard(provider=provider, model=model)
    except ImportError as e:
        console.print(f"[red]Error: Missing dependency for provider '{provider}'[/red]")
        console.print(f"\n[yellow]Install with:[/yellow]")
        console.print(f"  pip install halluciGuard[{provider}]")
        raise typer.Exit(2)
    except Exception as e:
        console.print(f"[red]Error initializing {provider}: {e}[/red]")
        raise typer.Exit(2)
    
    # Welcome message
    console.print(Panel(
        f"[bold green]HalluciGuard Chat[/bold green]\n"
        f"Provider: [cyan]{provider}[/cyan]\n"
        f"Model: [cyan]{model}[/cyan]\n\n"
        f"[dim]Type your message and press Enter to chat.[/dim]\n"
        f"[dim]Type /help for commands or /quit to exit.[/dim]",
        title="🛡️ HalluciGuard Interactive Chat",
        border_style="green",
    ))
    
    # Conversation history
    messages: List[dict] = []
    last_result = None
    
    if system:
        messages.append({"role": "system", "content": system})
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                cmd_parts = user_input.split(maxsplit=1)
                cmd = cmd_parts[0].lower()
                args = cmd_parts[1] if len(cmd_parts) > 1 else None
                
                if cmd in ("/quit", "/exit", "/q"):
                    console.print("[green]Goodbye! Stay safe from hallucinations! 🛡️[/green]")
                    break
                    
                elif cmd == "/help":
                    show_help()
                    continue
                    
                elif cmd == "/clear":
                    messages.clear()
                    if system:
                        messages.append({"role": "system", "content": system})
                    console.print("[green]Conversation history cleared.[/green]")
                    continue
                    
                elif cmd == "/history":
                    show_history(messages)
                    continue
                    
                elif cmd == "/claims":
                    if last_result:
                        show_claims_detail(last_result)
                    else:
                        console.print("[yellow]No previous response to analyze.[/yellow]")
                    continue
                    
                elif cmd == "/check":
                    if args:
                        check_text(guard, args)
                    else:
                        console.print("[yellow]Usage: /check <text to analyze>[/yellow]")
                    continue
                    
                elif cmd == "/model":
                    console.print(f"Current model: [cyan]{model}[/cyan] (provider: {provider})")
                    continue
                    
                else:
                    console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
                    console.print("[dim]Type /help for available commands.[/dim]")
                    continue
            
            # Regular chat message
            messages.append({"role": "user", "content": user_input})
            
            # Get response with hallucination detection
            with console.status("[bold green]Generating response...[/bold green]"):
                try:
                    result = guard.check_with_context(
                        messages=messages,
                        temperature=temperature,
                    )
                    last_result = result
                except AttributeError:
                    # Fallback if check_with_context doesn't exist
                    response = guard.generate(messages, temperature=temperature)
                    result = guard.check(response)
                    last_result = result
            
            # Display response
            response_text = result.response if hasattr(result, 'response') else result.raw_response
            risk_color = get_risk_color(result.risk_level)
            risk_emoji = get_risk_emoji(result.risk_level)
            
            console.print(f"\n[bold {risk_color}]Assistant[/bold {risk_color}] {risk_emoji}")
            console.print(Panel(
                Markdown(response_text),
                border_style=risk_color,
            ))
            
            # Trust score indicator
            trust_bar = create_trust_bar(result.trust_score)
            console.print(f"\n{trust_bar} [dim]Trust: {result.trust_score:.0%}[/dim]")
            
            # Show claims if requested
            if show_claims and result.claims:
                show_claims_inline(result.claims)
            
            # Add to history
            if history:
                messages.append({"role": "assistant", "content": response_text})
            
            # Warning for low trust
            if result.trust_score < 0.6:
                console.print(f"\n[yellow]⚠ Warning: Low trust score. Some claims may be unreliable.[/yellow]")
                if result.recommendations:
                    console.print(f"[yellow]  💡 {result.recommendations[0]}[/yellow]")
                    
        except KeyboardInterrupt:
            console.print("\n[green]Goodbye! 🛡️[/green]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            # Remove failed message from history
            if messages and messages[-1].get("role") == "user":
                messages.pop()


def show_help():
    """Show help for chat commands."""
    table = Table(title="Chat Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    
    commands = [
        ("/help", "Show this help message"),
        ("/quit, /exit", "Exit the chat"),
        ("/clear", "Clear conversation history"),
        ("/history", "Show conversation history"),
        ("/claims", "Show claims from last response"),
        ("/check <text>", "Check specific text for hallucinations"),
        ("/model", "Show current model info"),
    ]
    
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    
    console.print(table)


def show_history(messages: List[dict]):
    """Show conversation history."""
    if not messages:
        console.print("[yellow]No conversation history.[/yellow]")
        return
    
    console.print("\n[bold]Conversation History:[/bold]")
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        if role == "system":
            console.print(f"[dim]System: {content[:100]}...[/dim]")
        elif role == "user":
            console.print(f"[blue]You: {content[:100]}...[/blue]")
        elif role == "assistant":
            console.print(f"[green]Assistant: {content[:100]}...[/green]")


def show_claims_detail(result):
    """Show detailed claims from result."""
    if not result.claims:
        console.print("[yellow]No claims extracted from last response.[/yellow]")
        return
    
    table = Table(title="Extracted Claims")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Claim", style="white")
    table.add_column("Confidence", style="green")
    table.add_column("Verifiable", style="yellow")
    
    for i, claim in enumerate(result.claims, 1):
        table.add_row(
            str(i),
            claim.claim[:60] + "..." if len(claim.claim) > 60 else claim.claim,
            f"{claim.confidence:.2f}",
            "✓" if claim.verifiable else "✗"
        )
    
    console.print(table)


def show_claims_inline(claims):
    """Show claims inline after response."""
    console.print("\n[dim]Extracted Claims:[/dim]")
    for i, claim in enumerate(claims[:5], 1):  # Show max 5 claims
        status = "✓" if claim.confidence > 0.7 else "⚠"
        console.print(f"  {status} [dim]{claim.claim[:70]}...[/dim]")


def check_text(guard, text: str):
    """Check specific text for hallucinations."""
    with console.status("[bold green]Analyzing text...[/bold green]"):
        result = guard.check(text)
    
    risk_color = get_risk_color(result.risk_level)
    risk_emoji = get_risk_emoji(result.risk_level)
    
    console.print(f"\n[bold]Analysis Result:[/bold] [{risk_color}]{result.risk_level.value}[/{risk_color}] {risk_emoji}")
    console.print(f"Trust Score: [cyan]{result.trust_score:.2%}[/cyan]")
    
    if result.claims:
        console.print(f"Claims Found: {len(result.claims)}")


def create_trust_bar(score: float, width: int = 20) -> str:
    """Create a visual trust score bar."""
    filled = int(score * width)
    empty = width - filled
    
    if score >= 0.8:
        color = "green"
    elif score >= 0.6:
        color = "yellow"
    else:
        color = "red"
    
    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"


if __name__ == "__main__":
    app()
