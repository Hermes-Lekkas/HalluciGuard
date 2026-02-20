# HalluciGuard - AI Hallucination Detection Middleware

## Project Overview
HalluciGuard is an open-source Python library designed to detect and mitigate hallucinations in LLM pipelines. It acts as a middleware wrapper around popular LLM providers, performing factual claim extraction, risk scoring, and reporting.

### Core Technologies
- **Language:** Python 3.9+
- **LLM Integrations:** OpenAI, Anthropic, Google Gemini (google-genai), Ollama.
- **Agent Integrations:** OpenClaw Interceptor.
- **Search Integrations:** Tavily, BaseSearchProvider plugin system.
- **Verification Logic:**
    - LLM-based claim extraction and self-consistency scoring.
    - Web cross-referencing.
    - RAG-aware verification.
    - Linguistic heuristic fallbacks.

### Architecture
1. **Guard (`guard.py`)**: The primary entry point. Orchestrates the detection pipeline.
2. **Detectors (`detectors/`)**:
    - `extractor.py`: Factual claim extraction using lightweight LLMs.
    - `scorer.py`: Multi-signal hallucination scoring.
3. **Reporters (`reporters/`)**:
    - `builder.py`: Generates structured JSON and human-readable audit reports.
4. **Search (`search/`)**: Pluggable architecture for real-time web verification.
5. **Integrations (`integrations/`)**:
    - `openclaw.py`: Middleware for the OpenClaw autonomous agent framework.
6. **Models (`models.py`)**: Core data structures (`Claim`, `GuardedResponse`).

---

## Directory Structure
- `halluciGuard/`: Main package.
    - `detectors/`: Claim extraction and scoring logic.
    - `reporters/`: Report generation utilities.
    - `search/`: Web search providers.
    - `integrations/`: Third-party agent hooks.
    - `api/`: FastAPI server for extension/remote usage.
    - `guard.py`: Main Middleware class.
    - `models.py`: Data models.
    - `config.py`: Configuration.
- `examples/`: Usage demonstrations.
- `tests/`: Comprehensive test suite.
- `extension/`: Browser extension for ChatGPT/Claude.

---

## Roadmap Status
- [x] Core claim extraction engine
- [x] LLM self-consistency scoring
- [x] Multi-model support (OpenAI, Anthropic, Gemini)
- [x] Web verification plugin (v0.2)
- [x] RAG-aware hallucination detection (v0.2)
- [x] Real-time streaming support (v0.3)
- [x] Fine-tuned local model support (v0.4)
- [x] Browser extension (v0.5)
- [x] OpenClaw Agent Integration (v0.7)

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

### Running the API Server
```bash
export PYTHONPATH=.
python3 halluciGuard/server.py
```

---

## Development Conventions
- **Modular Detectors**: Extraction and scoring are decoupled.
- **Hierarchical Package**: Source code is organized into logical subpackages.
- **AGPLv3 Compliance**: All source files must include the license header.
- **Mock-Heavy Testing**: Use mocks for API-dependent logic in `tests/`.
