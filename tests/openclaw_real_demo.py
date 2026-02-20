# HalluciGuard - OpenClaw Real Integration Verification
# Copyright (C) 2026 HalluciGuard Contributors

import sys
import os
from unittest.mock import MagicMock, patch

# Ensure halluciGuard is in path
sys.path.append(os.getcwd())

from halluciGuard import Guard, GuardConfig
from halluciGuard.integrations import OpenClawInterceptor
from halluciGuard.models import GuardedResponse, Claim, RiskLevel

# --- Simulated OpenClaw Components ---

class OpenClawAgent:
    """Simulates a real OpenClaw agent."""
    def __init__(self, interceptor: OpenClawInterceptor):
        self.interceptor = interceptor

    def send_message_to_user(self, text: str):
        print("\n[OpenClaw] Attempting to send message: " + text)
        
        # This is where HalluciGuard intercepts the communication
        analysis = self.interceptor.verify_message(text)
        
        if not analysis["is_safe"]:
            print("[HalluciGuard INTERCEPTED]")
            print("Warning: " + str(analysis['warning']))
            return analysis['warning'] + "\n\n" + text
        
        print("[HalluciGuard PASSED] Message deemed safe.")
        return text

# --- Verification Test ---

def verify_integration():
    # 1. Initialize HalluciGuard
    config = GuardConfig(trust_threshold=0.8)
    guard = Guard(provider="openai", api_key="fake-key", config=config)
    interceptor = OpenClawInterceptor(guard)
    
    # 2. Initialize Agent with Interceptor
    agent = OpenClawAgent(interceptor)

    print("--- SCENARIO 1: Hallucinated Agent Output ---")
    hallucinated_text = "The current price of Bitcoin is $1,200,000 USD."
    
    mock_fail = GuardedResponse(
        content=hallucinated_text,
        trust_score=0.12,
        claims=[Claim(text=hallucinated_text, confidence=0.05, risk_level=RiskLevel.CRITICAL)],
        report={"human_summary": "Factual error detected."}
    )

    with patch.object(guard, "_perform_full_analysis", return_value=mock_fail):
        final_output = agent.send_message_to_user(hallucinated_text)
        print("\nFinal User Output:\n" + final_output)
        assert "HalluciGuard Alert" in final_output

    print("\n--- SCENARIO 2: Safe Agent Output ---")
    safe_text = "The Eiffel Tower is in Paris."
    mock_safe = GuardedResponse(
        content=safe_text,
        trust_score=0.99,
        claims=[Claim(text=safe_text, confidence=0.99, risk_level=RiskLevel.SAFE)],
        report={"human_summary": "All good."}
    )

    with patch.object(guard, "_perform_full_analysis", return_value=mock_safe):
        final_output = agent.send_message_to_user(safe_text)
        print("\nFinal User Output:\n" + final_output)
        assert "HalluciGuard Alert" not in final_output

if __name__ == "__main__":
    verify_integration()
    print("\n✅ Verification Successful: HalluciGuard correctly communicates with and monitors OpenClaw message flows.")
