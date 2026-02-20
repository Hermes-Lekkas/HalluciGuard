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
ReportBuilder — Generates structured hallucination reports.
"""

import datetime
from typing import Dict, Any, List

from ..config import GuardConfig
from ..models import Claim, RiskLevel
from .badge import BadgeGenerator

RISK_ICONS = {
    RiskLevel.SAFE: "✅",
    RiskLevel.LOW: "🟡",
    RiskLevel.MEDIUM: "⚠️",
    RiskLevel.HIGH: "🔴",
    RiskLevel.CRITICAL: "🚨",
}


class ReportBuilder:
    def __init__(self, config: GuardConfig):
        self.config = config

    def build(
        self,
        content: str,
        claims: List[Claim],
        trust_score: float,
        elapsed_seconds: float,
    ) -> Dict[str, Any]:
        """Build a full audit report as a dict (JSON-serializable)."""
        flagged = [c for c in claims if c.risk_level.value in ("MEDIUM", "HIGH", "CRITICAL")]
        safe = [c for c in claims if c.risk_level.value in ("SAFE", "LOW")]

        report = {
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "elapsed_seconds": round(elapsed_seconds, 3),
            "trust_score": trust_score,
            "trust_label": self._trust_label(trust_score),
            "total_claims": len(claims),
            "flagged_claims_count": len(flagged),
            "safe_claims_count": len(safe),
            "flagged_claims": [self._claim_to_dict(c) for c in flagged],
            "trust_badge": BadgeGenerator.generate_svg(trust_score),
        }

        if self.config.include_safe_claims:
            report["safe_claims"] = [self._claim_to_dict(c) for c in safe]

        report["human_summary"] = self._human_summary(trust_score, flagged, safe)
        return report

    def _claim_to_dict(self, claim: Claim) -> Dict[str, Any]:
        return {
            "text": claim.text,
            "confidence": claim.confidence,
            "risk_level": claim.risk_level.value,
            "icon": RISK_ICONS.get(claim.risk_level, "❓"),
            "explanation": claim.explanation,
            "sources": claim.sources,
        }

    def _trust_label(self, score: float) -> str:
        if score >= 0.85:
            return "HIGH TRUST"
        elif score >= 0.65:
            return "MODERATE TRUST"
        elif score >= 0.45:
            return "LOW TRUST"
        else:
            return "VERY LOW TRUST — likely hallucinating"

    def _human_summary(self, trust_score: float, flagged: List[Claim], safe: List[Claim]) -> str:
        lines = [
            f"Trust Score: {trust_score:.2f} ({self._trust_label(trust_score)})",
            f"Total claims analyzed: {len(flagged) + len(safe)}",
            f"Flagged claims: {len(flagged)}",
            "",
        ]
        if flagged:
            lines.append("Flagged claims:")
            for claim in flagged:
                icon = RISK_ICONS.get(claim.risk_level, "❓")
                lines.append(f"  {icon} [{claim.risk_level.value}] {claim.text}")
                if claim.explanation:
                    lines.append(f"     → {claim.explanation}")
                lines.append(f"     Confidence: {claim.confidence:.2f}")
        else:
            lines.append("✅ No significant hallucinations detected.")
        return "\n".join(lines)
