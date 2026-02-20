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

import pytest
from halluciGuard import GuardConfig, RiskLevel, Claim
from halluciGuard.scorer import HallucinationScorer

def test_scorer_with_rag_context():
    config = GuardConfig()
    scorer = HallucinationScorer(config)
    
    rag_context = ["The capital of France is Paris and it was founded in the 3rd century BC."]
    claims = [
        Claim(text="Paris was founded in the 3rd century BC.", confidence=0.5, risk_level=RiskLevel.MEDIUM)
    ]
    
    # Mock the LLM call for RAG verification
    with pytest.MonkeyPatch.context() as m:
        m.setattr(scorer, "_verify_claim_against_rag", lambda c, s, m: '{"confidence": 0.98, "reason": "Directly stated in context."}')
        
        enriched_claims = scorer._enrich_with_rag_verification(claims, rag_context, "gpt-4o-mini")
        
        assert len(enriched_claims) == 1
        assert enriched_claims[0].confidence == 0.98
        assert "RAG VERIFIED" in enriched_claims[0].explanation
        assert "RAG Context" in enriched_claims[0].sources

def test_scorer_with_rag_contradiction():
    config = GuardConfig()
    scorer = HallucinationScorer(config)
    
    rag_context = ["The population of London is 9 million."]
    claims = [
        Claim(text="London has 15 million people.", confidence=0.8, risk_level=RiskLevel.LOW)
    ]
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr(scorer, "_verify_claim_against_rag", lambda c, s, m: '{"confidence": 0.1, "reason": "Context says 9 million."}')
        
        enriched_claims = scorer._enrich_with_rag_verification(claims, rag_context, "gpt-4o-mini")
        
        assert enriched_claims[0].confidence == 0.1
        assert enriched_claims[0].risk_level == RiskLevel.CRITICAL
