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
Tests for HalluciGuard.

Run with: pytest tests/ -v
"""

import pytest
from unittest.mock import MagicMock, patch

from halluciGuard import Guard, GuardConfig, GuardedResponse, Claim, RiskLevel
from halluciGuard.detectors.extractor import ClaimExtractor
from halluciGuard.detectors.scorer import HallucinationScorer
from halluciGuard.reporters.builder import ReportBuilder


# ────────────────────────────────────────────
#  Fixtures
# ────────────────────────────────────────────

@pytest.fixture
def config():
    return GuardConfig(
        trust_threshold=0.6,
        max_claims_per_response=10,
        enable_web_verification=False,
    )


@pytest.fixture
def scorer(config):
    return HallucinationScorer(config)


@pytest.fixture
def extractor(config):
    return ClaimExtractor(config)


@pytest.fixture
def reporter(config):
    return ReportBuilder(config)


# ────────────────────────────────────────────
#  Model Tests
# ────────────────────────────────────────────

class TestRiskLevel:
    def test_risk_levels_ordered(self):
        levels = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(levels) == 5

    def test_risk_level_values(self):
        assert RiskLevel.SAFE.value == "SAFE"
        assert RiskLevel.CRITICAL.value == "CRITICAL"


class TestClaim:
    def test_claim_creation(self):
        claim = Claim(
            text="Einstein published relativity in 1905.",
            confidence=0.95,
            risk_level=RiskLevel.SAFE,
        )
        assert claim.text == "Einstein published relativity in 1905."
        assert claim.confidence == 0.95
        assert claim.risk_level == RiskLevel.SAFE

    def test_claim_defaults(self):
        claim = Claim(text="Some claim.", confidence=0.5, risk_level=RiskLevel.MEDIUM)
        assert claim.sources == []
        assert claim.explanation is None
        assert claim.is_verifiable is True


class TestGuardedResponse:
    def test_flagged_and_safe_split(self):
        claims = [
            Claim("Safe fact.", 0.95, RiskLevel.SAFE),
            Claim("Low risk fact.", 0.75, RiskLevel.LOW),
            Claim("Medium risk claim.", 0.55, RiskLevel.MEDIUM),
            Claim("High risk claim.", 0.30, RiskLevel.HIGH),
            Claim("Critical hallucination.", 0.05, RiskLevel.CRITICAL),
        ]
        resp = GuardedResponse(content="...", trust_score=0.5, claims=claims)
        assert len(resp.flagged_claims) == 3  # MEDIUM + HIGH + CRITICAL
        assert len(resp.safe_claims) == 2      # SAFE + LOW

    def test_is_trustworthy(self):
        resp = GuardedResponse(content="...", trust_score=0.8)
        assert resp.is_trustworthy(threshold=0.6) is True
        assert resp.is_trustworthy(threshold=0.9) is False

    def test_summary_format(self):
        resp = GuardedResponse(content="...", trust_score=0.75, claims=[])
        summary = resp.summary()
        assert "0.75" in summary
        assert "Trust Score" in summary


# ────────────────────────────────────────────
#  Claim Extractor Tests
# ────────────────────────────────────────────

class TestClaimExtractor:
    def test_heuristic_extraction_finds_dates(self, extractor):
        text = "Albert Einstein published the special theory of relativity in 1905. It was revolutionary."
        claims = extractor._extract_heuristic(text)
        assert len(claims) >= 1
        assert any("1905" in c for c in claims)

    def test_heuristic_skips_short_sentences(self, extractor):
        text = "Yes. No. OK. Einstein published the theory of relativity in 1905."
        claims = extractor._extract_heuristic(text)
        # Short sentences should be skipped
        assert all(len(c.split()) >= 4 for c in claims)

    def test_parse_claims_json_valid(self, extractor):
        raw = '["Einstein was born in 1879.", "He won the Nobel Prize in 1921."]'
        claims = extractor._parse_claims_json(raw)
        assert len(claims) == 2
        assert "Einstein was born in 1879." in claims

    def test_parse_claims_json_with_fences(self, extractor):
        raw = '```json
["Claim one.", "Claim two."]
```'
        claims = extractor._parse_claims_json(raw)
        assert "Claim one." in claims

    def test_parse_claims_json_invalid(self, extractor):
        raw = "not json at all"
        claims = extractor._parse_claims_json(raw)
        # Should return empty or partial list, not crash
        assert isinstance(claims, list)


# ────────────────────────────────────────────
#  Hallucination Scorer Tests
# ────────────────────────────────────────────

class TestHallucinationScorer:
    def test_score_heuristic_returns_claims(self, scorer):
        claims_text = [
            "Einstein published the special theory of relativity in 1905.",
            "I believe the battle of Waterloo was in approximately 1815.",
        ]
        scored = scorer._score_heuristic(claims_text)
        assert len(scored) == 2
        assert all(isinstance(c, Claim) for c in scored)

    def test_uncertainty_language_lowers_score(self, scorer):
        certain = "Water boils at 100 degrees Celsius."
        uncertain = "I believe water boils at approximately 100 degrees Celsius."
        c_certain = scorer._apply_heuristic_adjustments(certain, 0.65)
        c_uncertain = scorer._apply_heuristic_adjustments(uncertain, 0.65)
        assert c_uncertain < c_certain

    def test_confidence_to_risk_mapping(self):
        assert HallucinationScorer._confidence_to_risk(0.95) == RiskLevel.SAFE
        assert HallucinationScorer._confidence_to_risk(0.75) == RiskLevel.LOW
        assert HallucinationScorer._confidence_to_risk(0.55) == RiskLevel.MEDIUM
        assert HallucinationScorer._confidence_to_risk(0.35) == RiskLevel.HIGH
        assert HallucinationScorer._confidence_to_risk(0.10) == RiskLevel.CRITICAL

    def test_score_clamps_between_0_and_1(self, scorer):
        # Even with extreme penalties, score should stay in [0, 1]
        score = scorer._apply_heuristic_adjustments(
            "I think approximately maybe perhaps he was born on January 5th 1900", 0.05
        )
        assert 0.0 <= score <= 1.0


# ────────────────────────────────────────────
#  Report Builder Tests
# ────────────────────────────────────────────

class TestReportBuilder:
    def test_report_has_required_keys(self, reporter):
        claims = [Claim("Test claim.", 0.8, RiskLevel.SAFE)]
        report = reporter.build(
            content="Test content.",
            claims=claims,
            trust_score=0.85,
            elapsed_seconds=0.5,
        )
        assert "trust_score" in report
        assert "total_claims" in report
        assert "flagged_claims" in report
        assert "human_summary" in report

    def test_trust_label_high(self, reporter):
        assert "HIGH TRUST" in reporter._trust_label(0.9)

    def test_trust_label_very_low(self, reporter):
        assert "VERY LOW" in reporter._trust_label(0.2)

    def test_flagged_claims_in_report(self, reporter):
        claims = [
            Claim("Safe fact.", 0.95, RiskLevel.SAFE),
            Claim("Hallucination!", 0.05, RiskLevel.CRITICAL, explanation="This is wrong."),
        ]
        report = reporter.build("content", claims, 0.3, 0.1)
        assert report["flagged_claims_count"] == 1
        assert report["flagged_claims"][0]["risk_level"] == "CRITICAL"


# ────────────────────────────────────────────
#  Guard Integration Tests (mocked)
# ────────────────────────────────────────────

class TestGuard:
    def test_guard_init_valid_provider(self):
        mock_client = MagicMock()
        guard = Guard(provider="openai", client=mock_client)
        assert guard.provider == "openai"

    def test_guard_init_invalid_provider(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            Guard(provider="fakeai")

    def test_compute_trust_score_no_claims(self):
        guard = Guard(provider="openai", client=MagicMock())
        score = guard._compute_trust_score([])
        assert score == 1.0

    def test_compute_trust_score_all_safe(self):
        guard = Guard(provider="openai", client=MagicMock())
        claims = [
            Claim("Fact A.", 0.95, RiskLevel.SAFE),
            Claim("Fact B.", 0.90, RiskLevel.SAFE),
        ]
        score = guard._compute_trust_score(claims)
        assert score >= 0.85

    def test_compute_trust_score_critical_claim_drags_down(self):
        guard = Guard(provider="openai", client=MagicMock())
        claims = [
            Claim("Safe.", 0.95, RiskLevel.SAFE),
            Claim("Safe.", 0.92, RiskLevel.SAFE),
            Claim("Critical hallucination!", 0.05, RiskLevel.CRITICAL),
        ]
        score = guard._compute_trust_score(claims)
        assert score < 0.7  # Should be dragged down by the critical claim

    @patch("halluciGuard.guard.ClaimExtractor.extract", return_value=["Einstein discovered gravity."])
    @patch("halluciGuard.guard.HallucinationScorer.score_all", return_value=[
        Claim("Einstein discovered gravity.", 0.15, RiskLevel.HIGH,
              explanation="Newton discovered gravity, not Einstein.")
    ])
    def test_guard_chat_openai_mock(self, mock_score, mock_extract):
        """End-to-end test with mocked OpenAI client and mocked detectors."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "Einstein discovered gravity and also invented the telephone."
        )
        mock_client.chat.completions.create.return_value = mock_response

        import warnings
        guard = Guard(provider="openai", client=mock_client)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            resp = guard.chat(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Tell me about Einstein."}]
            )

        assert isinstance(resp, GuardedResponse)
        assert len(resp.claims) == 1
        assert len(resp.flagged_claims) == 1
        assert resp.trust_score < 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
