"""
HalluciGuard CLI subcommands.

This package contains all CLI subcommands:
- check: Analyze text for hallucinations
- chat: Interactive chat with hallucination detection
- benchmark: Run benchmark suite
- serve: Start API server
- config: Manage configuration
- status: Check provider/API status
"""

# Import subcommand modules only
from halluciGuard.cli import check, chat, benchmark, serve, config, status

__all__ = ["check", "chat", "benchmark", "serve", "config", "status"]
