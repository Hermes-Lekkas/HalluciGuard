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

__version__ = "0.1.0"

from .guard import Guard, HallucinationError, LowTrustWarning, ClientInitializationError
from .config import GuardConfig
from .models import GuardedResponse, Claim, RiskLevel
from .search.base import BaseSearchProvider
from .search.tavily import TavilySearchProvider
from .errors import (
    HalluciGuardError,
    InvalidAPIKeyError,
    MissingDependencyError,
    ConfigurationError,
    InvalidRiskLevelError,
    InvalidThresholdError,
    ProviderError,
    UnsupportedProviderError,
    ProviderAPIError,
    ModelNotFoundError,
    ProcessingError,
    ClaimExtractionError,
    ScoringError,
    WebVerificationError,
    CacheError,
    CachePermissionError,
    CacheCorruptedError,
    LeaderboardError,
    BenchmarkError,
    DatasetError,
    StreamingError,
    handle_error,
    wrap_provider_error,
)

__all__ = [
    # Core classes
    "Guard",
    "GuardConfig",
    "GuardedResponse",
    "Claim",
    "RiskLevel",
    # Warnings and errors from guard
    "HallucinationError",
    "LowTrustWarning",
    "ClientInitializationError",
    # Search providers
    "BaseSearchProvider",
    "TavilySearchProvider",
    # Error classes
    "HalluciGuardError",
    "InvalidAPIKeyError",
    "MissingDependencyError",
    "ConfigurationError",
    "InvalidRiskLevelError",
    "InvalidThresholdError",
    "ProviderError",
    "UnsupportedProviderError",
    "ProviderAPIError",
    "ModelNotFoundError",
    "ProcessingError",
    "ClaimExtractionError",
    "ScoringError",
    "WebVerificationError",
    "CacheError",
    "CachePermissionError",
    "CacheCorruptedError",
    "LeaderboardError",
    "BenchmarkError",
    "DatasetError",
    "StreamingError",
    # Helper functions
    "handle_error",
    "wrap_provider_error",
    # Version
    "__version__",
]
