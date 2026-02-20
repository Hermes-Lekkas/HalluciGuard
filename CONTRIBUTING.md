# Contributing to HalluciGuard

First off — thank you! HalluciGuard is a community project and every contribution matters.

## How to Contribute

### 1. Fork & Clone
```bash
git clone https://github.com/yourusername/halluciGuard.git
cd halluciGuard
pip install -e ".[dev]"
```

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Make Changes & Test
```bash
pytest tests/ -v
```

### 4. Submit a PR
Open a pull request with a clear description of what you changed and why.

---

## Priority Areas for Contribution

These are the highest-impact areas to contribute to right now:

| Area | Description | Difficulty |
|---|---|---|
| **Web Verifier** | Implement `verifiers/web_verifier.py` to cross-reference claims against search | Medium |
| **RAG Verifier** | Detect hallucinations in RAG pipelines (compare against retrieved docs) | Hard |
| **Streaming Support** | Support streaming responses (yield GuardedResponse incrementally) | Medium |
| **New Providers** | Add Cohere, Mistral, Google Gemini provider adapters | Easy |
| **Benchmark Suite** | Add tests using HaluEval and TruthfulQA datasets | Medium |
| **Fine-tuned Scorer** | Train a small BERT-based classifier on hallucination datasets | Hard |
| **CLI Tool** | `halluciGuard check "response text"` command-line tool | Easy |

---

## Code Style

- We use `black` for formatting and `ruff` for linting
- Type hints everywhere
- Docstrings for all public methods
- Tests for every new feature

---

## Reporting Issues

Found a case where HalluciGuard missed a hallucination (or flagged something that was true)?
Open an issue with the model, the response text, and the claim in question. These are gold for improving the scorer!
