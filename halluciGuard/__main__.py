"""
Entry point for running HalluciGuard as a module.

Usage:
    python -m halluciGuard --help
    python -m halluciGuard check "Some text"
    python -m halluciGuard chat --model gpt-4o
"""

from halluciGuard.cli_module import cli_entry

if __name__ == "__main__":
    cli_entry()
