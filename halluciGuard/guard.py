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
Guard — The main middleware class that wraps LLM providers with hallucination detection.
"""

import json
import time
import datetime
import os
import logging
import warnings as warnings_module
from typing import Any, Dict, List, Optional

from .config import GuardConfig
from .models import GuardedResponse, Claim, RiskLevel
from .detectors.extractor import ClaimExtractor
from .detectors.scorer import HallucinationScorer
from .reporters.builder import ReportBuilder
from .streaming import StreamingGuardedResponse
from .errors import (
    HalluciGuardError,
    ClientInitializationError,
    UnsupportedProviderError,
    ProviderAPIError,
    ModelNotFoundError,
    ProcessingError,
    StreamingError,
    wrap_provider_error,
)

# Configure logger for HalluciGuard
logger = logging.getLogger("halluciGuard")


def _get_utc_now() -> datetime.datetime:
    """Get current UTC time in a timezone-aware manner (Python 3.11+ compatible)."""
    try:
        # Python 3.11+
        return datetime.datetime.now(datetime.timezone.utc)
    except AttributeError:
        # Fallback for older Python versions
        return datetime.datetime.utcnow()


class HallucinationError(Exception):
    """Raised when a CRITICAL hallucination is detected and raise_on_critical=True."""
    pass


class LowTrustWarning(UserWarning):
    """Warning raised when overall trust score falls below threshold."""
    pass


class Guard:
    """
    HalluciGuard middleware — drop-in wrapper around any LLM provider.

    Supported providers:
        - "openai"             → OpenAI Python SDK client
        - "anthropic"          → Anthropic Python SDK client
        - "ollama"             → Ollama local server
        - "openai_compatible"  → Any OpenAI-compatible REST API

    Example:
        from halluciGuard import Guard, GuardConfig
        from openai import OpenAI

        client = OpenAI()
        guard = Guard(provider="openai", client=client)

        response = guard.chat(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Who invented the internet?"}]
        )
        print(response.trust_score)
        print(response.flagged_claims)
    """

    SUPPORTED_PROVIDERS = ["openai", "anthropic", "google", "ollama", "openai_compatible"]

    def __init__(
        self,
        provider: str,
        client: Optional[Any] = None,
        config: Optional[GuardConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        if provider not in self.SUPPORTED_PROVIDERS:
            raise UnsupportedProviderError(
                provider=provider,
                supported=self.SUPPORTED_PROVIDERS,
            )

        self.provider = provider
        self.client = client
        self.config = config or GuardConfig()
        self.api_key = api_key
        self.base_url = base_url
        self._client_init_error: Optional[str] = None

        # Auto-initialize client if missing but api_key/base_url provided
        if self.client is None:
            if provider in ("openai", "openai_compatible") and api_key:
                try:
                    import openai
                    self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
                    logger.debug("OpenAI client auto-initialized successfully")
                except ImportError as e:
                    self._client_init_error = (
                        f"Failed to initialize OpenAI client: 'openai' package not installed. "
                        f"Install with: pip install openai"
                    )
                    logger.warning(self._client_init_error)
                except Exception as e:
                    self._client_init_error = f"Failed to initialize OpenAI client: {e}"
                    logger.warning(self._client_init_error)
            elif provider == "anthropic" and api_key:
                try:
                    import anthropic
                    self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
                    logger.debug("Anthropic client auto-initialized successfully")
                except ImportError as e:
                    self._client_init_error = (
                        f"Failed to initialize Anthropic client: 'anthropic' package not installed. "
                        f"Install with: pip install anthropic"
                    )
                    logger.warning(self._client_init_error)
                except Exception as e:
                    self._client_init_error = f"Failed to initialize Anthropic client: {e}"
                    logger.warning(self._client_init_error)
            elif provider == "google" and api_key:
                try:
                    from google import genai
                    self.client = genai.Client(api_key=api_key)
                    logger.debug("Google GenAI client auto-initialized successfully")
                except ImportError as e:
                    self._client_init_error = (
                        f"Failed to initialize Google client: 'google-genai' package not installed. "
                        f"Install with: pip install google-genai"
                    )
                    logger.warning(self._client_init_error)
                except Exception as e:
                    self._client_init_error = f"Failed to initialize Google client: {e}"
                    logger.warning(self._client_init_error)
            elif api_key is None and client is None:
                # No API key provided and no client - this is a common issue
                self._client_init_error = (
                    f"No client or API key provided for provider '{provider}'. "
                    f"Either pass a 'client' parameter or provide an 'api_key'."
                )
                logger.warning(self._client_init_error)

        # Internal components - passing self._call_provider to ensure they use the same auth/config
        self._extractor = ClaimExtractor(config=self.config, llm_caller=self._call_provider)
        self._scorer = HallucinationScorer(config=self.config, llm_caller=self._call_provider)
        self._reporter = ReportBuilder(config=self.config)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        rag_context: Optional[List[str]] = None,
        **kwargs,
    ) -> GuardedResponse:
        """
        Send a chat request to the configured LLM provider and return a
        GuardedResponse with hallucination analysis.

        Args:
            model:    The model string (e.g., "gpt-4o", "claude-sonnet-4-6").
            messages: OpenAI-format message list.
            rag_context: Optional list of strings (retrieved documents) to verify against.
            **kwargs: Additional parameters forwarded to the provider (temperature, etc.)

        Returns:
            GuardedResponse with trust_score, claims, flagged_claims, and report.
        """
        start = time.time()

        # 1. Call the LLM provider
        raw_response, content = self._call_provider(model, messages, **kwargs)

        # 2. Perform full hallucination analysis
        return self._perform_full_analysis(
            content=content,
            model=model,
            messages=messages,
            rag_context=rag_context,
            start_time=start,
            raw_response=raw_response
        )

    def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        rag_context: Optional[List[str]] = None,
        **kwargs,
    ) -> StreamingGuardedResponse:
        """
        Send a streaming chat request. Tokens are yielded as they arrive.
        Hallucination analysis is performed after the stream completes.
        """
        raw_stream = self._call_provider_stream(model, messages, **kwargs)

        def analysis_callback(content: str) -> GuardedResponse:
            return self._perform_full_analysis(
                content=content,
                model=model,
                messages=messages,
                rag_context=rag_context,
                start_time=time.time(), # Approximate
                raw_response=None # Stream already consumed
            )

        return StreamingGuardedResponse(
            stream=raw_stream,
            provider=self.provider,
            analysis_callback=analysis_callback
        )

    def _perform_full_analysis(
        self,
        content: str,
        model: str,
        messages: List[Dict[str, str]],
        rag_context: Optional[List[str]] = None,
        start_time: float = 0.0,
        raw_response: Any = None
    ) -> GuardedResponse:
        """Shared logic for post-LLM hallucination analysis."""
        # 1. Extract factual claims from the response
        claims_text = self._extractor.extract(
            response_text=content,
            query=messages[-1].get("content", "") if messages else "",
            model=model,
        )

        # 2. Score each claim for hallucination risk
        scored_claims: List[Claim] = self._scorer.score_all(
            claims=claims_text,
            context=content,
            rag_context=rag_context,
            provider=self.provider,
            model=self.config.verifier_model or model,
        )

        # 3. Compute overall trust score
        trust_score = self._compute_trust_score(scored_claims)

        # 4. Build the audit report
        elapsed = time.time() - (start_time or time.time())
        report = self._reporter.build(
            content=content,
            claims=scored_claims,
            trust_score=trust_score,
            elapsed_seconds=elapsed,
        )

        # 5. Optionally save audit log
        if self.config.audit_log_path:
            self._save_audit_log(report, model, messages)

        # 6. Build final response
        guarded = GuardedResponse(
            content=content,
            trust_score=trust_score,
            claims=scored_claims,
            raw_response=raw_response,
            report=report,
            metadata={
                "model": model,
                "provider": self.provider,
                "elapsed_seconds": round(elapsed, 3),
                "timestamp": _get_utc_now().isoformat(),
            },
        )

        import warnings
        critical = [c for c in scored_claims if c.risk_level == RiskLevel.CRITICAL]
        if critical and self.config.raise_on_critical:
            raise HallucinationError(
                f"CRITICAL hallucination detected: {critical[0].text}"
            )

        if not guarded.is_trustworthy(self.config.trust_threshold):
            warnings.warn(
                f"Response trust score {trust_score:.2f} is below threshold "
                f"{self.config.trust_threshold}. "
                f"{len(guarded.flagged_claims)} claims flagged.",
                LowTrustWarning,
                stacklevel=2,
            )

        return guarded

    def _call_provider(
        self, model: str, messages: List[Dict], **kwargs
    ):
        """Route the call to the appropriate provider SDK."""
        if self.provider == "openai" or self.provider == "openai_compatible":
            return self._call_openai(model, messages, **kwargs)
        elif self.provider == "anthropic":
            return self._call_anthropic(model, messages, **kwargs)
        elif self.provider == "google":
            return self._call_google(model, messages, **kwargs)
        elif self.provider == "ollama":
            return self._call_ollama(model, messages, **kwargs)
        else:
            raise UnsupportedProviderError(
                provider=self.provider,
                supported=["openai", "anthropic", "google", "ollama"],
            )

    def _call_openai(self, model, messages, **kwargs):
        if self.client is None:
            error_msg = self._client_init_error or "client must be provided for OpenAI provider."
            raise ClientInitializationError(
                f"OpenAI client not initialized. {error_msg}",
                provider="openai",
            )
        try:
            resp = self.client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )
            content = resp.choices[0].message.content or ""
            return resp, content
        except Exception as e:
            # Check for common OpenAI errors
            error_str = str(e).lower()
            if "api key" in error_str or "unauthorized" in error_str or "401" in error_str:
                raise ProviderAPIError(
                    provider="openai",
                    original_error=e,
                    status_code=401,
                )
            elif "rate limit" in error_str or "429" in error_str:
                raise ProviderAPIError(
                    provider="openai",
                    original_error=e,
                    status_code=429,
                )
            elif "model" in error_str and ("not found" in error_str or "does not exist" in error_str):
                raise ModelNotFoundError(
                    model=model,
                    provider="openai",
                )
            else:
                raise wrap_provider_error(e, "openai")

    def _call_anthropic(self, model, messages, **kwargs):
        if self.client is None:
            error_msg = self._client_init_error or "client must be provided for Anthropic provider."
            raise ClientInitializationError(
                f"Anthropic client not initialized. {error_msg}",
                provider="anthropic",
            )
        try:
            # Convert OpenAI-format messages to Anthropic format
            system_prompt = ""
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    anthropic_messages.append(msg)

            call_kwargs = {"max_tokens": kwargs.pop("max_tokens", 2048), **kwargs}
            if system_prompt:
                call_kwargs["system"] = system_prompt

            resp = self.client.messages.create(
                model=model,
                messages=anthropic_messages,
                **call_kwargs,
            )
            content = resp.content[0].text if resp.content else ""
            return resp, content
        except Exception as e:
            error_str = str(e).lower()
            if "api key" in error_str or "unauthorized" in error_str or "401" in error_str:
                raise ProviderAPIError(
                    provider="anthropic",
                    original_error=e,
                    status_code=401,
                )
            elif "rate limit" in error_str or "429" in error_str:
                raise ProviderAPIError(
                    provider="anthropic",
                    original_error=e,
                    status_code=429,
                )
            elif "model" in error_str and ("not found" in error_str or "does not exist" in error_str):
                raise ModelNotFoundError(
                    model=model,
                    provider="anthropic",
                )
            else:
                raise wrap_provider_error(e, "anthropic")

    def _call_ollama(self, model, messages, **kwargs):
        """Call a local Ollama server (OpenAI-compatible API)."""
        import urllib.request
        import urllib.error
        
        url = (self.base_url or "http://localhost:11434") + "/api/chat"
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "stream": False,
            **kwargs
        }).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as r:
                resp = json.loads(r.read().decode())
            content = resp.get("message", {}).get("content", "")
            return resp, content
        except urllib.error.URLError as e:
            raise ProviderAPIError(
                provider="ollama",
                original_error=e,
            )
        except Exception as e:
            raise wrap_provider_error(e, "ollama")

    def _compute_trust_score(self, claims: List[Claim]) -> float:
        """Compute an overall trust score from a list of scored claims."""
        if not claims:
            return 1.0  # No claims = nothing to hallucinate about

        verifiable = [c for c in claims if c.is_verifiable]
        if not verifiable:
            return 0.85  # Soft content only, low risk

        scores = [c.confidence for c in verifiable]
        # Weighted average: penalise HIGH and CRITICAL claims more
        weights = []
        for c in verifiable:
            if c.risk_level == RiskLevel.CRITICAL:
                weights.append(3.0)
            elif c.risk_level == RiskLevel.HIGH:
                weights.append(2.0)
            elif c.risk_level == RiskLevel.MEDIUM:
                weights.append(1.5)
            else:
                weights.append(1.0)

        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        weight_total = sum(weights)
        return round(weighted_sum / weight_total, 4)

    def _save_audit_log(
        self,
        report: Dict,
        model: str,
        messages: List[Dict],
    ):
        os.makedirs(self.config.audit_log_path, exist_ok=True)
        ts = _get_utc_now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(self.config.audit_log_path, f"guard_{ts}.json")
        audit = {
            "timestamp": _get_utc_now().isoformat(),
            "model": model,
            "query": messages[-1].get("content", "")[:500] if messages else "",
            "report": report,
        }
        with open(filename, "w") as f:
            json.dump(audit, f, indent=2)

    def _call_provider_stream(self, model: str, messages: List[Dict], **kwargs):
        """Route the streaming call to the appropriate provider SDK."""
        if self.provider == "openai" or self.provider == "openai_compatible":
            return self._call_openai_stream(model, messages, **kwargs)
        elif self.provider == "anthropic":
            return self._call_anthropic_stream(model, messages, **kwargs)
        elif self.provider == "google":
            return self._call_google_stream(model, messages, **kwargs)
        else:
            raise StreamingError(
                provider=self.provider,
                reason=f"Streaming not supported for provider '{self.provider}'",
            )

    def _call_openai_stream(self, model, messages, **kwargs):
        if self.client is None:
            error_msg = self._client_init_error or "client must be provided for OpenAI provider."
            raise ClientInitializationError(
                f"OpenAI client not initialized. {error_msg}",
                provider="openai",
            )
        try:
            return self.client.chat.completions.create(
                model=model, messages=messages, stream=True, **kwargs
            )
        except Exception as e:
            raise wrap_provider_error(e, "openai")

    def _call_anthropic_stream(self, model, messages, **kwargs):
        if self.client is None:
            error_msg = self._client_init_error or "client must be provided for Anthropic provider."
            raise ClientInitializationError(
                f"Anthropic client not initialized. {error_msg}",
                provider="anthropic",
            )
        try:
            system_prompt = ""
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    anthropic_messages.append(msg)

            call_kwargs = {"max_tokens": kwargs.pop("max_tokens", 2048), **kwargs}
            if system_prompt:
                call_kwargs["system"] = system_prompt

            return self.client.messages.create(
                model=model,
                messages=anthropic_messages,
                stream=True,
                **call_kwargs,
            )
        except Exception as e:
            raise wrap_provider_error(e, "anthropic")

    def _call_google(self, model, messages, **kwargs):
        if self.client is None:
            error_msg = self._client_init_error or "client (google.genai) must be initialized for Google provider."
            raise ClientInitializationError(
                f"Google client not initialized. {error_msg}",
                provider="google",
            )
        try:
            # Split into system instruction and conversation history
            system_instruction = None
            google_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                else:
                    google_messages.append({
                        "role": "user" if msg["role"] == "user" else "model",
                        "parts": [{"text": msg["content"]}]
                    })

            # google-genai uses generate_content with a config
            config = {"system_instruction": system_instruction}
            config.update(kwargs)
            
            resp = self.client.models.generate_content(
                model=model,
                contents=google_messages,
                config=config
            )
            
            content = resp.text
            return resp, content
        except Exception as e:
            raise wrap_provider_error(e, "google")

    def _call_google_stream(self, model, messages, **kwargs):
        if self.client is None:
            error_msg = self._client_init_error or "client (google.genai) must be initialized for Google provider."
            raise ClientInitializationError(
                f"Google client not initialized. {error_msg}",
                provider="google",
            )
        try:
            system_instruction = None
            google_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                else:
                    google_messages.append({
                        "role": "user" if msg["role"] == "user" else "model",
                        "parts": [{"text": msg["content"]}]
                    })

            config = {"system_instruction": system_instruction}
            config.update(kwargs)

            return self.client.models.generate_content_stream(
                model=model,
                contents=google_messages,
                config=config
            )
        except Exception as e:
            raise wrap_provider_error(e, "google")
