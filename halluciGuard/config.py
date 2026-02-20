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
Configuration for HalluciGuard.
"""

from dataclasses import dataclass, field
from typing import Optional
from .models import RiskLevel
from .search.base import BaseSearchProvider


@dataclass
class GuardConfig:
    """
    Configuration options for the Guard middleware.

    Args:
        trust_threshold: Minimum trust score (0.0–1.0) to consider a response safe.
                         Responses below this score will raise a LowTrustWarning.
        flag_level: Minimum risk level to include in flagged_claims.
        enable_web_verification: Cross-reference claims against web search results.
        search_provider: Instance of BaseSearchProvider to use for web verification.
        verifier_model: LLM model used for claim verification (default: same as chat model).
        max_claims_per_response: Maximum number of claims to extract per response.
        audit_log_path: Directory to save JSON audit logs. None = don't log to disk.
        raise_on_critical: Raise HallucinationError if any CRITICAL claim is found.
        include_safe_claims: Include safe claims in the report (can be verbose).
        local_model_path: Path to a local fine-tuned model (e.g. GGUF or HF).
        cache_enabled: Whether to cache claim verification results.
        cache_dir: Directory to store cache files (default: .halluciguard_cache).
    """

    trust_threshold: float = 0.6
    flag_level: RiskLevel = RiskLevel.MEDIUM
    enable_web_verification: bool = False
    search_provider: Optional[BaseSearchProvider] = None
    verifier_model: Optional[str] = None
    max_claims_per_response: int = 15
    audit_log_path: Optional[str] = None
    raise_on_critical: bool = False
    include_safe_claims: bool = True
    timeout_seconds: int = 30
    local_model_path: Optional[str] = None
    cache_enabled: bool = True
    cache_dir: str = ".halluciguard_cache"
