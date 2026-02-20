# HalluciGuard - AI Hallucination Detection Middleware

## Project Overview
HalluciGuard is an open-source Python library designed to detect and mitigate hallucinations in LLM pipelines. It acts as a middleware wrapper around popular LLM providers (OpenAI, Anthropic, Ollama, etc.), performing factual claim extraction, risk scoring, and reporting before delivering the response to the end-user.

### Core Technologies
- **Language:** Python 3.9+
- **LLM Integrations:** OpenAI, Anthropic, Google Gemini, Ollama.
- **Agent Integrations:** **OpenClaw (Autonomous AI Agent)**.
- **Verification Logic:**
    - LLM-based claim extraction and self-consistency scoring.
    - Web cross-referencing (Tavily).
    - RAG-aware verification.
    - Linguistic heuristic fallbacks.

### Architecture
1. **Guard (`guard.py`)**: The primary entry point. Wraps provider calls and orchestrates the detection pipeline.
2. **OpenClaw Integration (`integrations/openclaw.py`)**: Hooks into OpenClaw's message gateway to verify agent actions and messages.
3. **Claim Extractor (`claim_extractor.py`)**: Uses a lightweight LLM to identify discrete factual claims.
4. **Scorer (`scorer.py`)**: Evaluates claims for accuracy using LLM self-consistency, web verification, and heuristics.
5. **Search Providers (`search/`)**: Pluggable architecture for web search.

---

## Directory Structure
- `halluciGuard/`: Core package.
    - `integrations/`: Third-party agent integrations.
        - `openclaw.py`: OpenClaw gateway hooks and skills.
    - `guard.py`: Core middleware.
    - `scorer.py`: Hallucination detection.
    - ...
- `extension/`: Browser extension.
- `tests/`: Test suite.
- `basic_usage.py`: Example usage.

---

## Roadmap Status
- [x] Core claim extraction engine
- [x] LLM self-consistency scoring
- [x] OpenAI + Anthropic + Google Gemini support
- [x] Web verification plugin (v0.2)
- [x] RAG-aware hallucination detection (v0.2)
- [x] Real-time streaming support (v0.3)
- [x] Fine-tuned hallucination detection model (v0.4)
- [x] Browser extension (v0.5)
- [ ] **OpenClaw Agent Integration (v0.7) - IN PROGRESS**

---

## Building and Running
... (standard pip install -e ".")
