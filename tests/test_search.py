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
from halluciGuard.search.base import BaseSearchProvider
from halluciGuard.scorer import HallucinationScorer

class MockSearchProvider(BaseSearchProvider):
    def __init__(self, mock_results):
        self.mock_results = mock_results

    def search(self, query, limit=3):
        return self.mock_results

def test_scorer_with_web_verification():
    mock_results = [
        {"title": "Fact Check", "url": "https://factcheck.org", "content": "Einstein won the Nobel Prize for the photoelectric effect."}
    ]
    config = GuardConfig(
        enable_web_verification=True,
        search_provider=MockSearchProvider(mock_results)
    )
    scorer = HallucinationScorer(config)
    
    # Create a claim that would be flagged for verification
    claims = [
        Claim(text="Einstein won the Nobel Prize for relativity.", confidence=0.2, risk_level=RiskLevel.HIGH)
    ]
    
    # Mock the LLM call for web verification
    with pytest.MonkeyPatch.context() as m:
        m.setattr(scorer, "_verify_claim_against_web", lambda c, s, m: '{"confidence": 0.1, "reason": "Contradicted by source."}')
        
        enriched_claims = scorer._enrich_with_web_verification(claims, "gpt-4o-mini")
        
        assert len(enriched_claims) == 1
        assert enriched_claims[0].confidence < 0.2
        assert "WEB VERIFIED" in enriched_claims[0].explanation
        assert "https://factcheck.org" in enriched_claims[0].sources
