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
Centralized error handling for HalluciGuard.

This module provides custom exceptions with actionable error messages
to help users quickly resolve issues.

Example:
    from halluciGuard.errors import ClientInitializationError, handle_error
    
    try:
        guard = Guard(provider="openai")
        response = guard.chat(model="gpt-4o", messages=[...])
    except ClientInitializationError as e:
        print(e.help_message)  # Prints actionable guidance
"""

from typing import Optional, List, Dict, Any


class HalluciGuardError(Exception):
    """
    Base exception for all HalluciGuard errors.
    
    All custom exceptions inherit from this class and provide:
    - A clear error message
    - A help_message with actionable guidance
    - An error_code for programmatic handling
    """
    
    error_code: str = "HALLUCIGUARD_ERROR"
    
    def __init__(
        self,
        message: str,
        help_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.help_message = help_message or self._get_default_help()
        self.details = details or {}
    
    def _get_default_help(self) -> str:
        return "Visit https://github.com/Hermes-Lekkas/HalluciGuard#troubleshooting for help."
    
    def __str__(self) -> str:
        return f"{self.message}\n\n💡 Help: {self.help_message}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "help_message": self.help_message,
            "details": self.details,
        }


# =============================================================================
# Client & Authentication Errors
# =============================================================================

class ClientInitializationError(HalluciGuardError):
    """
    Raised when an LLM client cannot be initialized.
    
    Common causes:
    - Missing API key
    - Invalid API key
    - Missing required package
    - Network connectivity issues
    """
    
    error_code = "CLIENT_INIT_ERROR"
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        missing_key: Optional[str] = None,
        missing_package: Optional[str] = None,
        **kwargs,
    ):
        self.provider = provider
        self.missing_key = missing_key
        self.missing_package = missing_package
        
        help_msg = self._build_help_message()
        super().__init__(message, help_message=help_msg, **kwargs)
    
    def _build_help_message(self) -> str:
        help_parts = []
        
        if self.missing_package:
            help_parts.append(f"Install the required package: pip install {self.missing_package}")
        
        if self.missing_key:
            help_parts.extend([
                f"Set your API key: export {self.missing_key}='your-api-key'",
                f"Or pass it directly: Guard(provider='{self.provider}', api_key='your-api-key')",
            ])
        
        if self.provider:
            help_parts.append(f"Verify your {self.provider} account is active and has credits.")
        
        if not help_parts:
            help_parts.append("Check your API credentials and network connection.")
        
        return "\n  • ".join(["To fix this:"] + help_parts)


class InvalidAPIKeyError(ClientInitializationError):
    """Raised when an API key is invalid or expired."""
    
    error_code = "INVALID_API_KEY"
    
    def __init__(self, provider: str, **kwargs):
        message = f"Invalid API key for {provider}."
        super().__init__(
            message,
            provider=provider,
            missing_key=f"{provider.upper()}_API_KEY",
            **kwargs,
        )


class MissingDependencyError(HalluciGuardError):
    """Raised when a required package is not installed."""
    
    error_code = "MISSING_DEPENDENCY"
    
    def __init__(self, package: str, extra: Optional[str] = None, **kwargs):
        self.package = package
        self.extra = extra
        
        message = f"Required package '{package}' is not installed."
        
        if extra:
            install_cmd = f"pip install halluciGuard[{extra}]"
        else:
            install_cmd = f"pip install {package}"
        
        help_msg = f"To fix this:\n  • Run: {install_cmd}\n  • Or install all extras: pip install halluciGuard[all]"
        
        super().__init__(message, help_message=help_msg, **kwargs)


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(HalluciGuardError):
    """Raised when there's an issue with GuardConfig."""
    
    error_code = "CONFIG_ERROR"
    
    def __init__(self, message: str, parameter: Optional[str] = None, **kwargs):
        self.parameter = parameter
        super().__init__(message, **kwargs)


class InvalidRiskLevelError(ConfigurationError):
    """Raised when an invalid risk level is provided."""
    
    error_code = "INVALID_RISK_LEVEL"
    
    def __init__(self, value: str, valid_levels: List[str], **kwargs):
        self.value = value
        self.valid_levels = valid_levels
        
        message = f"Invalid risk level: '{value}'"
        help_msg = (
            f"Valid risk levels are: {', '.join(valid_levels)}\n"
            f"Example: GuardConfig(flag_level='HIGH') or GuardConfig(flag_level=RiskLevel.HIGH)"
        )
        
        super().__init__(message, parameter="flag_level", help_message=help_msg, **kwargs)


class InvalidThresholdError(ConfigurationError):
    """Raised when a threshold value is out of range."""
    
    error_code = "INVALID_THRESHOLD"
    
    def __init__(self, parameter: str, value: float, min_val: float = 0.0, max_val: float = 1.0, **kwargs):
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        
        message = f"Invalid {parameter}: {value}. Must be between {min_val} and {max_val}."
        help_msg = f"Example: GuardConfig({parameter}=0.6)"
        
        super().__init__(message, parameter=parameter, help_message=help_msg, **kwargs)


# =============================================================================
# Provider Errors
# =============================================================================

class ProviderError(HalluciGuardError):
    """Base class for provider-related errors."""
    
    error_code = "PROVIDER_ERROR"
    
    def __init__(self, message: str, provider: Optional[str] = None, **kwargs):
        self.provider = provider
        super().__init__(message, **kwargs)


class UnsupportedProviderError(ProviderError):
    """Raised when an unsupported provider is specified."""
    
    error_code = "UNSUPPORTED_PROVIDER"
    
    def __init__(self, provider: str, supported: List[str], **kwargs):
        self.supported = supported
        
        message = f"Unsupported provider: '{provider}'"
        help_msg = (
            f"Supported providers are: {', '.join(supported)}\n"
            f"Example: Guard(provider='openai', client=OpenAI())"
        )
        
        super().__init__(message, provider=provider, help_message=help_msg, **kwargs)


class ProviderAPIError(ProviderError):
    """Raised when a provider API call fails."""
    
    error_code = "PROVIDER_API_ERROR"
    
    def __init__(
        self,
        provider: str,
        original_error: Optional[Exception] = None,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        self.original_error = original_error
        self.status_code = status_code
        
        message = f"{provider} API error"
        if status_code:
            message += f" (HTTP {status_code})"
        if original_error:
            message += f": {str(original_error)}"
        
        help_parts = [f"To fix this {provider} API error:"]
        
        if status_code == 401:
            help_parts.append("Check that your API key is valid and not expired")
        elif status_code == 429:
            help_parts.append("You've hit a rate limit. Wait a moment and retry, or check your usage limits")
        elif status_code == 500:
            help_parts.append("The provider is experiencing issues. Try again in a few moments")
        elif status_code == 404:
            help_parts.append("The requested model or endpoint was not found. Check the model name")
        else:
            help_parts.append("Check your network connection and API credentials")
        
        help_parts.append(f"Verify your {provider} account has available credits")
        
        super().__init__(message, provider=provider, help_message="\n  • ".join(help_parts), **kwargs)


class ModelNotFoundError(ProviderError):
    """Raised when a model is not found or not available."""
    
    error_code = "MODEL_NOT_FOUND"
    
    def __init__(self, model: str, provider: str, available_models: Optional[List[str]] = None, **kwargs):
        self.model = model
        self.available_models = available_models
        
        message = f"Model '{model}' not found for provider '{provider}'"
        
        help_parts = [f"To fix this:"]
        help_parts.append(f"Verify the model name is correct: '{model}'")
        
        if available_models:
            help_parts.append(f"Available models include: {', '.join(available_models[:5])}...")
        
        help_parts.append(f"Check your {provider} account for model access")
        
        super().__init__(message, provider=provider, help_message="\n  • ".join(help_parts), **kwargs)


# =============================================================================
# Processing Errors
# =============================================================================

class ProcessingError(HalluciGuardError):
    """Base class for errors during hallucination analysis."""
    
    error_code = "PROCESSING_ERROR"


class ClaimExtractionError(ProcessingError):
    """Raised when claim extraction fails."""
    
    error_code = "CLAIM_EXTRACTION_ERROR"
    
    def __init__(self, reason: str, **kwargs):
        message = f"Failed to extract claims: {reason}"
        help_msg = (
            "This is usually a temporary issue. Try:\n"
            "  • Simplifying the input text\n"
            "  • Checking for unusual characters or encoding\n"
            "  • Using a different model for extraction"
        )
        super().__init__(message, help_message=help_msg, **kwargs)


class ScoringError(ProcessingError):
    """Raised when hallucination scoring fails."""
    
    error_code = "SCORING_ERROR"
    
    def __init__(self, reason: str, **kwargs):
        message = f"Failed to score claims: {reason}"
        help_msg = (
            "The scorer fell back to heuristics. For better results:\n"
            "  • Ensure you have a valid LLM client configured\n"
            "  • Check your API credits\n"
            "  • Try with a smaller number of claims"
        )
        super().__init__(message, help_message=help_msg, **kwargs)


class WebVerificationError(ProcessingError):
    """Raised when web verification fails."""
    
    error_code = "WEB_VERIFICATION_ERROR"
    
    def __init__(self, reason: str, **kwargs):
        message = f"Web verification failed: {reason}"
        help_msg = (
            "To use web verification:\n"
            "  • Set enable_web_verification=True in config\n"
            "  • Configure a search provider: config.search_provider = TavilySearchProvider(api_key='...')\n"
            "  • Check your search provider API key and credits"
        )
        super().__init__(message, help_message=help_msg, **kwargs)


# =============================================================================
# Cache Errors
# =============================================================================

class CacheError(HalluciGuardError):
    """Base class for cache-related errors."""
    
    error_code = "CACHE_ERROR"


class CachePermissionError(CacheError):
    """Raised when cache directory is not writable."""
    
    error_code = "CACHE_PERMISSION_ERROR"
    
    def __init__(self, cache_dir: str, **kwargs):
        self.cache_dir = cache_dir
        
        message = f"Cannot write to cache directory: {cache_dir}"
        help_msg = (
            f"To fix this:\n"
            f"  • Check permissions: chmod 755 {cache_dir}\n"
            f"  • Or use a different directory: GuardConfig(cache_dir='/tmp/halluciguard_cache')\n"
            f"  • Or disable caching: GuardConfig(cache_enabled=False)"
        )
        
        super().__init__(message, help_message=help_msg, **kwargs)


class CacheCorruptedError(CacheError):
    """Raised when cache data is corrupted."""
    
    error_code = "CACHE_CORRUPTED_ERROR"
    
    def __init__(self, cache_file: str, **kwargs):
        self.cache_file = cache_file
        
        message = f"Corrupted cache file: {cache_file}"
        help_msg = (
            "The cache file is corrupted and will be ignored.\n"
            "To fix this:\n"
            "  • Delete the cache: rm -rf .halluciguard_cache\n"
            "  • The cache will be rebuilt automatically"
        )
        
        super().__init__(message, help_message=help_msg, **kwargs)


# =============================================================================
# Leaderboard Errors
# =============================================================================

class LeaderboardError(HalluciGuardError):
    """Base class for leaderboard-related errors."""
    
    error_code = "LEADERBOARD_ERROR"


class BenchmarkError(LeaderboardError):
    """Raised when a benchmark run fails."""
    
    error_code = "BENCHMARK_ERROR"
    
    def __init__(self, model: str, reason: str, **kwargs):
        self.model = model
        
        message = f"Benchmark failed for model '{model}': {reason}"
        help_msg = (
            "To fix this:\n"
            "  • Check that the model name is correct\n"
            "  • Verify your API key has access to this model\n"
            "  • Check your API credits\n"
            "  • Try with a smaller number of test cases: --max-cases 5"
        )
        
        super().__init__(message, help_message=help_msg, **kwargs)


class DatasetError(LeaderboardError):
    """Raised when there's an issue with the benchmark dataset."""
    
    error_code = "DATASET_ERROR"
    
    def __init__(self, reason: str, **kwargs):
        message = f"Dataset error: {reason}"
        help_msg = (
            "To fix this:\n"
            "  • Ensure the dataset JSON is valid\n"
            "  • Check that all required fields are present\n"
            "  • Use BenchmarkDataset.load() with a valid path"
        )
        
        super().__init__(message, help_message=help_msg, **kwargs)


# =============================================================================
# Streaming Errors
# =============================================================================

class StreamingError(HalluciGuardError):
    """Raised when streaming fails."""
    
    error_code = "STREAMING_ERROR"
    
    def __init__(self, provider: str, reason: str, **kwargs):
        self.provider = provider
        
        message = f"Streaming failed for {provider}: {reason}"
        help_msg = (
            "To fix this:\n"
            "  • Check your network connection\n"
            "  • Verify the model supports streaming\n"
            "  • Try using the non-streaming chat() method instead"
        )
        
        super().__init__(message, help_message=help_msg, **kwargs)


# =============================================================================
# Helper Functions
# =============================================================================

def handle_error(error: Exception, verbose: bool = True) -> Dict[str, Any]:
    """
    Convert any exception to a structured error response.
    
    Args:
        error: The exception to handle
        verbose: If True, print the help message
    
    Returns:
        Dictionary with error details
    """
    if isinstance(error, HalluciGuardError):
        if verbose:
            print(f"\n❌ Error: {error.message}")
            print(f"💡 {error.help_message}\n")
        return error.to_dict()
    
    # Wrap unknown errors
    if verbose:
        print(f"\n❌ Unexpected error: {str(error)}")
        print("💡 Please report this at: https://github.com/Hermes-Lekkas/HalluciGuard/issues\n")
    
    return {
        "error_code": "UNKNOWN_ERROR",
        "message": str(error),
        "help_message": "Please report this issue on GitHub.",
        "details": {"type": type(error).__name__},
    }


def wrap_provider_error(error: Exception, provider: str) -> ProviderAPIError:
    """
    Wrap a provider-specific error into a HalluciGuard ProviderAPIError.
    
    Args:
        error: The original exception
        provider: The provider name
    
    Returns:
        ProviderAPIError with helpful context
    """
    # Extract status code if available
    status_code = None
    if hasattr(error, 'status_code'):
        status_code = error.status_code
    elif hasattr(error, 'response') and hasattr(error.response, 'status_code'):
        status_code = error.response.status_code
    
    return ProviderAPIError(
        provider=provider,
        original_error=error,
        status_code=status_code,
    )
