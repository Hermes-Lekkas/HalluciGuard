# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
examples/basic_usage.py — Quick demo of HalluciGuard.

Run:
    export OPENAI_API_KEY="sk-..."
    python examples/basic_usage.py
"""

from halluciGuard import Guard, GuardConfig

# ── 1. OpenAI example ──────────────────────────────────────────────────────
def openai_example():
    try:
        from openai import OpenAI
    except ImportError:
        print("Install openai: pip install openai")
        return

    client = OpenAI()
    config = GuardConfig(
        trust_threshold=0.65,
        flag_level="MEDIUM",
    )
    guard = Guard(provider="openai", client=client, config=config)

    response = guard.chat(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": (
                "Tell me about Albert Einstein's major scientific contributions "
                "and what year he won the Nobel Prize."
            )
        }],
    )

    print("=" * 60)
    print("OPENAI EXAMPLE")
    print("=" * 60)
    print(f"
📝 Response:
{response.content}
")
    print(f"
{response.summary()}
")
    if response.report:
        print(response.report["human_summary"])


# ── 2. Anthropic example ───────────────────────────────────────────────────
def anthropic_example():
    try:
        import anthropic
    except ImportError:
        print("Install anthropic: pip install anthropic")
        return

    client = anthropic.Anthropic()
    guard = Guard(provider="anthropic", client=client)

    response = guard.chat(
        model="claude-haiku-4-5-20251001",
        messages=[{
            "role": "user",
            "content": "What is the population of Tokyo and when was it founded?"
        }],
        max_tokens=512,
    )

    print("=" * 60)
    print("ANTHROPIC EXAMPLE")
    print("=" * 60)
    print(f"
📝 Response:
{response.content}
")
    print(f"
{response.summary()}
")
    if response.report:
        print(response.report["human_summary"])


# ── 3. Simulated example (no API key needed) ───────────────────────────────
def simulated_example():
    """
    Demonstrates the hallucination detection pipeline without any real API call.
    Uses the internal scoring components directly.
    """
    from halluciGuard.claim_extractor import ClaimExtractor
    from halluciGuard.scorer import HallucinationScorer
    from halluciGuard.report_builder import ReportBuilder
    from halluciGuard import GuardConfig

    config = GuardConfig()
    extractor = ClaimExtractor(config)
    scorer = HallucinationScorer(config)
    reporter = ReportBuilder(config)

    # Simulate an AI response with a mix of true and hallucinated claims
    fake_response = (
        "Albert Einstein was born in 1879 in Ulm, Germany. "
        "He is famous for winning the Nobel Prize for his theory of relativity in 1921. "
        "Einstein also invented the telephone and discovered penicillin. "
        "He published his famous equation E=mc² as part of the special theory of relativity in 1905."
    )

    print("=" * 60)
    print("SIMULATED EXAMPLE (no API key needed)")
    print("=" * 60)
    print(f"
📝 Fake AI Response:
{fake_response}
")

    # Heuristic extraction (no LLM key needed)
    claims_text = extractor._extract_heuristic(fake_response)
    print(f"
🔍 Extracted {len(claims_text)} claims:")
    for i, c in enumerate(claims_text, 1):
        print(f"  {i}. {c}")

    # Heuristic scoring (no LLM key needed)
    scored_claims = scorer._score_heuristic(claims_text)
    trust_score = 0.65  # Placeholder
    report = reporter.build(fake_response, scored_claims, trust_score, 0.01)

    print(f"
📊 Report:
{report['human_summary']}")


if __name__ == "__main__":
    print("
🛡️  HalluciGuard Demo
")
    simulated_example()
    print("
─── To test with real LLMs, set your API key and uncomment below ───
")
    # openai_example()
    # anthropic_example()
