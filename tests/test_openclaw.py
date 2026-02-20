# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors

from unittest.mock import MagicMock, patch
from halluciGuard import Guard, GuardConfig, RiskLevel, Claim
from halluciGuard.integrations import OpenClawInterceptor
from halluciGuard.models import GuardedResponse

def test_openclaw_interceptor():
    # Setup mock guard
    config = GuardConfig(trust_threshold=0.7)
    guard = Guard(provider="openai", client=MagicMock(), config=config)
    interceptor = OpenClawInterceptor(guard)

    # 1. Test flagging low-trust content
    content_fail = "The population of Mars is 10 million people."
    mock_fail = GuardedResponse(
        content=content_fail,
        trust_score=0.15,
        claims=[Claim(text=content_fail, confidence=0.05, risk_level=RiskLevel.CRITICAL)],
        report={"human_summary": "Critical!"}
    )

    with patch.object(guard, "_perform_full_analysis", return_value=mock_fail):
        result = interceptor.verify_message(content_fail)
        assert result["is_safe"] is False
        assert "HalluciGuard Alert" in result["warning"]
        assert "10 million" in result["content"]

    # 2. Test safe content
    content_safe = "The Earth revolves around the Sun."
    mock_safe = GuardedResponse(
        content=content_safe,
        trust_score=0.98,
        claims=[Claim(text=content_safe, confidence=0.98, risk_level=RiskLevel.SAFE)],
        report={"human_summary": "Safe!"}
    )

    with patch.object(guard, "_perform_full_analysis", return_value=mock_safe):
        result = interceptor.verify_message(content_safe)
        assert result["is_safe"] is True
        assert result["warning"] is None
        assert "Earth" in result["content"]

if __name__ == "__main__":
    test_openclaw_interceptor()
    print("✅ OpenClaw Integration Test Passed!")
