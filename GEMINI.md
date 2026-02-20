# HalluciGuard - AI Hallucination Detection Middleware

## Project Overview
HalluciGuard is an open-source Python library designed to detect and mitigate hallucinations in LLM pipelines. It acts as a middleware wrapper around popular LLM providers (OpenAI, Anthropic, Ollama, etc.), performing factual claim extraction, risk scoring, and reporting before delivering the response to the end-user.

### Core Technologies
- **Language:** Python 3.9+
- **LLM Integrations:** OpenAI SDK, Anthropic SDK, Ollama (via REST), OpenAI-compatible APIs.
- **Search Integrations:** Generic plugin system (e.g., Tavily).
- **Verification Logic:**
    - LLM-based claim extraction and self-consistency scoring.
    - Web cross-referencing (Phase 1).
    - Linguistic heuristic fallbacks (uncertainty detection, high-risk pattern matching).
    - JSON-based audit reporting and logging.

### Architecture
1. **Guard (`guard.py`)**: The primary entry point. Wraps provider calls and orchestrates the detection pipeline.
2. **Claim Extractor (`claim_extractor.py`)**: Uses a lightweight LLM (e.g., GPT-4o-mini) to identify discrete factual claims.
3. **Scorer (`scorer.py`)**: Evaluates claims for accuracy using LLM self-consistency, web verification, and heuristics.
4. **Search Providers (`search/`)**: Pluggable architecture for web search (Tavily, etc.).
5. **Models (`models.py`)**: Defines `Claim`, `RiskLevel`, and `GuardedResponse` data structures.
6. **Config (`config.py`)**: Provides customizable thresholds, model selections, and logging options.

---

## Directory Structure
The project is organized as a Python package:

- `halluciGuard/`: Core package directory.
    - `guard.py`: Core middleware logic.
    - `claim_extractor.py`: Factual claim extraction.
    - `scorer.py`: Hallucination detection and scoring.
    - `models.py`: Dataclasses for project entities.
    - `config.py`: Configuration management.
    - `report_builder.py`: Audit report generation.
    - `search/`: Web search provider implementations.
- `tests/`: Test suite.
- `basic_usage.py`: Example usage and demonstration.
- `setup.py`: Package installation and dependency management.

---

## Roadmap Status
- [x] Core claim extraction engine
- [x] LLM self-consistency scoring
- [x] OpenAI + Anthropic provider support
- [x] Risk reporter + audit logs
- [x] Web verification plugin (v0.2)
- [x] RAG-aware hallucination detection (v0.2)
- [x] Real-time streaming support (v0.3)
- [x] Fine-tuned hallucination detection model (v0.4)
- [x] Browser extension for ChatGPT/Claude.ai (v0.5)

---

## Building and Running

### Installation
```bash
pip install -e ".[all]"
```

### Running Tests
```bash
export PYTHONPATH=.
python3 -m pytest tests/
```

### Running Examples
```bash
export PYTHONPATH=.
python3 basic_usage.py
```

---

## Development Conventions
- **Modular Detectors**: Hallucination detection is split into extraction and scoring.
- **Generic Plugins**: Search providers follow the `BaseSearchProvider` interface.
- **Graceful Degradation**: System falls back to heuristics if LLM or Search APIs fail.
- **Auditability**: Every guarded call generates a `report` (JSON).
