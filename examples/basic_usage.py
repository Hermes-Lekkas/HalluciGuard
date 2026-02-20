# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors

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
    print(f"\n📝 Response:\n{response.content}\n")
    print(f"\n{response.summary()}\n")
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
    print(f"\n📝 Response:\n{response.content}\n")
    print(f"\n{response.summary()}\n")
    if response.report:
        print(response.report["human_summary"])


# ── 3. Simulated example (no API key needed) ───────────────────────────────
def simulated_example():
    """
    Demonstrates the hallucination detection pipeline without any real API call.
    Uses the internal scoring components directly.
    """
    from halluciGuard.detectors.extractor import ClaimExtractor
    from halluciGuard.detectors.scorer import HallucinationScorer
    from halluciGuard.reporters.builder import ReportBuilder
    from halluciGuard import GuardConfig

    config = GuardConfig()
    # Manual setup for demonstration
    extractor = ClaimExtractor(config)
    scorer = HallucinationScorer(config)
    reporter = ReportBuilder(config)

    fake_response = (
        "Albert Einstein was born in 1879 in Ulm, Germany. "
        "He is famous for winning the Nobel Prize for his theory of relativity in 1921. "
        "Einstein also invented the telephone and discovered penicillin. "
        "He published his famous equation E=mc² as part of the special theory of relativity in 1905."
    )

    print("=" * 60)
    print("SIMULATED EXAMPLE (no API key needed)")
    print("=" * 60)
    print(f"\n📝 Fake AI Response:\n{fake_response}\n")

    # Heuristic extraction
    claims_text = extractor._extract_heuristic(fake_response)
    print(f"\n🔍 Extracted {len(claims_text)} claims:")
    for i, c in enumerate(claims_text, 1):
        print(f"  {i}. {c}")

    # Heuristic scoring
    scored_claims = scorer._score_heuristic(claims_text)
    trust_score = 0.65
    report = reporter.build(fake_response, scored_claims, trust_score, 0.01)

    print(f"\n📊 Report:\n{report['human_summary']}")


if __name__ == "__main__":
    print("\n🛡️  HalluciGuard Demo\n")
    simulated_example()
    print("\n─── To test with real LLMs, set your API key and uncomment below ───\n")
    # openai_example()
    # anthropic_example()
