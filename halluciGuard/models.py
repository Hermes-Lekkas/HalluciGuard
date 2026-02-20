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
Data models for HalluciGuard.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class RiskLevel(Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Claim:
    """A single factual claim extracted from an LLM response."""
    text: str
    confidence: float  # 0.0 (hallucinated) to 1.0 (verified)
    risk_level: RiskLevel
    explanation: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    is_verifiable: bool = True
    original_span: Optional[str] = None  # substring in original response


@dataclass
class GuardedResponse:
    """The output of a Guard.chat() call — the LLM response + hallucination analysis."""
    content: str                        # Original LLM response text
    trust_score: float                  # Overall 0.0–1.0 trust rating
    claims: List[Claim] = field(default_factory=list)
    flagged_claims: List[Claim] = field(default_factory=list)
    safe_claims: List[Claim] = field(default_factory=list)
    report: Optional[Dict[str, Any]] = None
    raw_response: Optional[Any] = None  # The original provider response object
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.flagged_claims = [
            c for c in self.claims
            if c.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)
        ]
        self.safe_claims = [
            c for c in self.claims
            if c.risk_level in (RiskLevel.SAFE, RiskLevel.LOW)
        ]

    def is_trustworthy(self, threshold: float = 0.6) -> bool:
        return self.trust_score >= threshold

    def summary(self) -> str:
        flagged = len(self.flagged_claims)
        total = len(self.claims)
        icon = "✅" if self.is_trustworthy() else "⚠️"
        return (
            f"{icon} Trust Score: {self.trust_score:.2f} | "
            f"Claims: {total} total, {flagged} flagged"
        )
