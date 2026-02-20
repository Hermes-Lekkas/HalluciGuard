# Contributing to HalluciGuard

First off — thank you! HalluciGuard is an open-source project dedicated to making AI reliable, and every contribution matters.

## How to Contribute

### 1. Fork & Clone
```bash
git clone https://github.com/Hermes-Lekkas/HalluciGuard.git
cd HalluciGuard
pip install -e ".[all,dev]"
```

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Make Changes & Test
Ensure you set your `PYTHONPATH` correctly when running tests manually:
```bash
export PYTHONPATH=.
python3 -m pytest tests/
```

### 4. Submit a PR
Open a pull request with a clear description of what you changed and why.

---

## Priority Areas for Contribution

We've completed the core engine and initial provider integrations. We are now looking for help in these areas:

| Area | Description | Difficulty |
|---|---|---|
| **Lookahead Verification** | Implement predictive hallucination detection *during* token generation. | Hard |
| **New Search Providers** | Add Google Search, Serper, or DuckDuckGo adapters to `halluciGuard/search/`. | Easy |
| **UI Dashboard** | A web-based dashboard to view and search through audit logs. | Medium |
| **Model Optimization** | Optimize the local GGUF scorer for lower latency on edge devices. | Medium |
| **More Agent Hooks** | Integrate with AutoGPT, BabyAGI, or LangChain agents. | Medium |
| **Benchmark Dataset** | Add a standardized test runner for HaluEval and TruthfulQA. | Medium |

---

## Code Style & Standards

- **Organization**: Follow the subpackage structure (`detectors/`, `reporters/`, `integrations/`).
- **Formatting**: We use `black` for formatting and `ruff` for linting.
- **Licensing**: All new files **must** include the AGPLv3 license header.
- **Type Hints**: Required for all new public functions and classes.
- **Documentation**: Update `README.md` or `GEMINI.md` if your change adds new configuration or user-facing APIs.

---

## Reporting Issues

Found a case where HalluciGuard missed a hallucination (or flagged something that was true)?
Open an issue with:
1. The model used.
2. The prompt/query.
3. The response text.
4. The specific claim that was misclassified.

These are incredibly valuable for improving our scoring heuristics!
