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
from typing import Any, Dict, List, Optional

from .config import GuardConfig
from .models import GuardedResponse, Claim, RiskLevel
from .claim_extractor import ClaimExtractor
from .scorer import HallucinationScorer
from .report_builder import ReportBuilder
from .streaming import StreamingGuardedResponse


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

    SUPPORTED_PROVIDERS = ["openai", "anthropic", "ollama", "openai_compatible"]

    def __init__(
        self,
        provider: str,
        client: Optional[Any] = None,
        config: Optional[GuardConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider '{provider}'. "
                f"Choose from: {self.SUPPORTED_PROVIDERS}"
            )

        self.provider = provider
        self.client = client
        self.config = config or GuardConfig()
        self.api_key = api_key
        self.base_url = base_url

        # Auto-initialize client if missing but api_key/base_url provided
        if self.client is None:
            if provider in ("openai", "openai_compatible"):
                try:
                    import openai
                    self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
                except ImportError:
                    pass
            elif provider == "anthropic":
                try:
                    import anthropic
                    self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
                except ImportError:
                    pass

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
                "timestamp": datetime.datetime.utcnow().isoformat(),
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
        elif self.provider == "ollama":
            return self._call_ollama(model, messages, **kwargs)
        else:
            raise ValueError(f"Provider '{self.provider}' not implemented.")

    def _call_openai(self, model, messages, **kwargs):
        if self.client is None:
            raise ValueError("client must be provided for OpenAI provider.")
        resp = self.client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )
        content = resp.choices[0].message.content or ""
        return resp, content

    def _call_anthropic(self, model, messages, **kwargs):
        if self.client is None:
            raise ValueError("client must be provided for Anthropic provider.")
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

    def _call_ollama(self, model, messages, **kwargs):
        """Call a local Ollama server (OpenAI-compatible API)."""
        import urllib.request
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
        with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as r:
            resp = json.loads(r.read().decode())
        content = resp.get("message", {}).get("content", "")
        return resp, content

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
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(self.config.audit_log_path, f"guard_{ts}.json")
        audit = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
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
        else:
            raise ValueError(f"Streaming for provider '{self.provider}' not implemented.")

    def _call_openai_stream(self, model, messages, **kwargs):
        if self.client is None:
            raise ValueError("client must be provided for OpenAI provider.")
        return self.client.chat.completions.create(
            model=model, messages=messages, stream=True, **kwargs
        )

    def _call_anthropic_stream(self, model, messages, **kwargs):
        if self.client is None:
            raise ValueError("client must be provided for Anthropic provider.")
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
