# HalluciGuard CLI Integration Plan

## Current State Analysis

### Existing CLI Components
| Component | Location | Status |
|-----------|----------|--------|
| Benchmark Script | `scripts/run_benchmark.py` | ✅ Works via `python scripts/run_benchmark.py` |
| FastAPI Server | `halluciGuard/server.py` | ✅ Works via `python -m halluciGuard.server` |
| Package Entry | `pyproject.toml` | ❌ No `[project.scripts]` defined |
| Module Entry | `halluciGuard/__main__.py` | ❌ Does not exist |

### Missing CLI Features
1. **No unified CLI entry point** - Users cannot run `halluciGuard --help`
2. **No `python -m halluciGuard` support** - Missing `__main__.py`
3. **No interactive chat mode** - For testing hallucination detection
4. **No text analysis command** - For checking arbitrary text
5. **No configuration management** - For setting up API keys
6. **No provider status check** - For verifying API connections

---

## Proposed CLI Architecture

### Command Structure

```
halluciGuard
├── check          # Analyze text for hallucinations
├── chat           # Interactive chat with hallucination detection
├── benchmark      # Run benchmark suite
├── serve          # Start API server
├── config         # Manage configuration
└── status         # Check provider/API status
```

### Commands Detail

#### 1. `halluciGuard check` - Analyze Text
```bash
# Analyze text from stdin
echo "Einstein won the Nobel Prize for relativity in 1921." | halluciGuard check

# Analyze text from file
halluciGuard check --file response.txt

# Analyze with specific model
halluciGuard check --model gpt-4o "The moon landing was in 1969."

# Output formats
halluciGuard check --output json "Some claim."
halluciGuard check --output markdown "Some claim."
```

#### 2. `halluciGuard chat` - Interactive Mode
```bash
# Start interactive chat
halluciGuard chat --model gpt-4o

# With RAG context
halluciGuard chat --context docs/

# With specific provider
halluciGuard chat --provider anthropic --model claude-sonnet-4.6
```

#### 3. `halluciGuard benchmark` - Run Benchmarks
```bash
# Run with default models
halluciGuard benchmark

# Run with specific models
halluciGuard benchmark --models gpt-4o,claude-sonnet-4.6

# Run specific categories
halluciGuard benchmark --categories science,history

# Output options
halluciGuard benchmark --output ./results/ --format html
```

#### 4. `halluciGuard serve` - API Server
```bash
# Start server with defaults
halluciGuard serve

# Custom port and host
halluciGuard serve --host 0.0.0.0 --port 8080

# With API key for server
halluciGuard serve --api-key server-secret-key
```

#### 5. `halluciGuard config` - Configuration
```bash
# Set API keys
halluciGuard config set openai_api_key sk-...
halluciGuard config set anthropic_api_key sk-ant-...

# Show current config
halluciGuard config show

# Initialize config file
halluciGuard config init

# Set default model
halluciGuard config set default_model gpt-4o
```

#### 6. `halluciGuard status` - Check Status
```bash
# Check all providers
halluciGuard status

# Check specific provider
halluciGuard status --provider openai

# Verbose output
halluciGuard status --verbose
```

---

## Implementation Plan

### Phase 1: Core CLI Infrastructure

#### Step 1.1: Create `halluciGuard/cli.py`
- Use `click` or `typer` for CLI framework (recommend `typer` for modern async support)
- Define main command group
- Implement `--version` and `--help` flags

#### Step 1.2: Create `halluciGuard/__main__.py`
```python
from halluciGuard.cli import main

if __name__ == "__main__":
    main()
```

#### Step 1.3: Update `pyproject.toml`
```toml
[project.scripts]
halluciGuard = "halluciGuard.cli:main"

dependencies = [
    # ... existing deps
    "typer>=0.9.0",
    "rich>=13.0.0",  # For pretty output
]
```

### Phase 2: Implement Commands

#### Step 2.1: `check` Command
- Accept text from stdin, argument, or file
- Run hallucination analysis
- Output in multiple formats (text, json, markdown)
- Exit codes based on trust score

#### Step 2.2: `chat` Command
- Interactive REPL with hallucination feedback
- Real-time trust score display
- Support for RAG context
- Streaming responses with live analysis

#### Step 2.3: `benchmark` Command
- Port existing `scripts/run_benchmark.py` functionality
- Add progress bars with `rich`
- Support parallel model testing
- Generate all output formats

#### Step 2.4: `serve` Command
- Wrap existing FastAPI server
- Add daemon mode option
- Support SSL configuration
- Add health check endpoint

#### Step 2.5: `config` Command
- Create `~/.halluciguard/config.toml`
- Secure API key storage
- Environment variable support
- Config file validation

#### Step 2.6: `status` Command
- Test API connectivity
- Show rate limits if available
- Display account status
- Check model availability

### Phase 3: Enhanced Features

#### Step 3.1: Shell Completion
```bash
# Generate completion scripts
halluciGuard --install-completion bash
halluciGuard --install-completion zsh
halluciGuard --install-completion fish
```

#### Step 3.2: Output Formatting
- Rich tables for tabular data
- Syntax highlighting for code
- Progress bars for long operations
- Color-coded trust scores

#### Step 3.3: Configuration Profiles
```bash
# Multiple profiles
halluciGuard config profile create production
halluciGuard config profile use production
```

#### Step 3.4: Batch Processing
```bash
# Process multiple files
halluciGuard check --batch ./responses/*.txt

# Process from CSV
halluciGuard check --csv input.csv --output results.csv
```

---

## File Structure

```
halluciGuard/
├── __init__.py
├── __main__.py          # NEW: python -m halluciGuard
├── cli.py               # NEW: Main CLI module
├── cli/                 # NEW: CLI subcommands
│   ├── __init__.py
│   ├── check.py         # check command
│   ├── chat.py          # chat command
│   ├── benchmark.py     # benchmark command
│   ├── serve.py         # serve command
│   ├── config.py        # config command
│   └── status.py        # status command
├── guard.py
├── config.py
├── models.py
├── errors.py
├── server.py
└── ...
```

---

## Dependencies to Add

```toml
[project.dependencies]
# Existing
requests = ">=2.31.0"
pydantic = ">=2.0.0"

# New CLI dependencies
typer = ">=0.9.0"        # CLI framework
rich = ">=13.0.0"        # Pretty output
tomli = ">=2.0.0"        # Config file parsing (Python < 3.11)
```

---

## Example Usage After Implementation

```bash
# Install
pip install halluciGuard

# Quick check
halluciGuard check "The Earth is flat."

# Interactive session
halluciGuard chat --model gpt-4o

# Run benchmark
halluciGuard benchmark --models gpt-4o,claude-sonnet-4.6

# Start API server
halluciGuard serve --port 8080

# Configure
halluciGuard config set openai_api_key sk-...

# Check status
halluciGuard status
```

---

## Priority Order

1. **HIGH**: `__main__.py` + `pyproject.toml` scripts entry (enables `python -m halluciGuard`)
2. **HIGH**: `check` command (core functionality)
3. **MEDIUM**: `benchmark` command (port existing script)
4. **MEDIUM**: `serve` command (wrap existing server)
5. **LOW**: `chat` command (interactive mode)
6. **LOW**: `config` command (configuration management)
7. **LOW**: `status` command (provider status)

---

## Estimated Effort

| Task | Complexity |
|------|------------|
| Core CLI infrastructure | Medium |
| check command | Medium |
| chat command | High |
| benchmark command | Low (port existing) |
| serve command | Low (wrap existing) |
| config command | Medium |
| status command | Medium |

---

## Next Steps

1. Create `halluciGuard/__main__.py` for `python -m halluciGuard` support
2. Add `[project.scripts]` to `pyproject.toml`
3. Create `halluciGuard/cli.py` with typer
4. Implement `check` command first (most useful)
5. Port `benchmark` command from existing script
6. Add remaining commands incrementally
