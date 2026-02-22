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
LangChain Integration for HalluciGuard.

Provides seamless hallucination detection for LangChain applications with
a 30-second integration time.

Quick Start:
    from langchain_openai import ChatOpenAI
    from halluciGuard.integrations.langchain import HalluciGuardCallbackHandler
    
    # Create the callback handler
    guard_handler = HalluciGuardCallbackHandler(
        provider="openai",
        api_key="sk-..."
    )
    
    # Attach to your LLM
    llm = ChatOpenAI(callbacks=[guard_handler])
    
    # Run as normal - hallucination analysis is automatic
    response = llm.invoke("What is the capital of France?")
    print(response.guarded_response.trust_score)
"""

import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from ..guard import Guard, HallucinationError, ClientInitializationError
from ..config import GuardConfig
from ..models import GuardedResponse, Claim, RiskLevel

logger = logging.getLogger("halluciGuard.langchain")


@dataclass
class GuardedLLMResult:
    """Container for LLM results with hallucination analysis."""
    content: str
    trust_score: float
    flagged_claims: List[Claim]
    guarded_response: GuardedResponse
    is_trustworthy: bool
    report: Optional[Dict[str, Any]] = None


class HalluciGuardCallbackHandler:
    """
    LangChain CallbackHandler that automatically runs HalluciGuard
    on LLM generations.
    
    Features:
    - Automatic hallucination analysis on every LLM call
    - Streaming support with real-time analysis
    - RAG context verification
    - Configurable trust thresholds
    - Optional blocking on critical hallucinations
    
    Example:
        from langchain_openai import ChatOpenAI
        from halluciGuard.integrations.langchain import HalluciGuardCallbackHandler
        
        # Simple setup
        handler = HalluciGuardCallbackHandler(provider="openai", api_key="sk-...")
        
        # Attach to LLM
        llm = ChatOpenAI(callbacks=[handler])
        
        # Use normally
        response = llm.invoke("Tell me about Einstein")
        
        # Access hallucination analysis
        if hasattr(response, 'guarded_response'):
            print(f"Trust Score: {response.guarded_response.trust_score}")
    """
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        config: Optional[GuardConfig] = None,
        guard: Optional[Guard] = None,
        rag_context: Optional[List[str]] = None,
        model: str = "gpt-4o-mini",
        raise_on_critical: bool = False,
        trust_threshold: float = 0.6,
        on_low_trust: Optional[callable] = None,
        on_critical: Optional[callable] = None,
    ):
        """
        Initialize the HalluciGuard callback handler.
        
        Args:
            provider: LLM provider ("openai", "anthropic", "google")
            api_key: API key for the provider
            config: Full GuardConfig object (overrides other config params)
            guard: Pre-initialized Guard instance (overrides provider/api_key)
            rag_context: RAG context documents for verification
            model: Model name for verification calls
            raise_on_critical: Raise exception on critical hallucinations
            trust_threshold: Minimum trust score (0.0-1.0)
            on_low_trust: Callback when trust score is below threshold
            on_critical: Callback when critical hallucination is detected
        """
        if guard:
            self.guard = guard
        else:
            self.guard = Guard(provider=provider, api_key=api_key, config=config)
        
        self.rag_context = rag_context
        self.model = model
        self.raise_on_critical = raise_on_critical
        self.trust_threshold = trust_threshold
        self.on_low_trust = on_low_trust
        self.on_critical = on_critical
        
        # Storage for the last analysis
        self._last_guarded_response: Optional[GuardedResponse] = None
        self._last_result: Optional[GuardedLLMResult] = None
        
        # Streaming state
        self._streaming_content = ""
        self._streaming_tokens: List[str] = []
    
    @property
    def last_guarded_response(self) -> Optional[GuardedResponse]:
        """Get the last GuardedResponse from the most recent LLM call."""
        return self._last_guarded_response
    
    @property
    def last_result(self) -> Optional[GuardedLLMResult]:
        """Get the last full result from the most recent LLM call."""
        return self._last_result
    
    def set_rag_context(self, context: List[str]):
        """Update RAG context for subsequent calls."""
        self.rag_context = context
    
    # --- LangChain Callback Methods ---
    
    @property
    def llm_start(self) -> bool:
        """Return True to indicate we want to handle llm_start."""
        return True
    
    @property
    def llm_new_token(self) -> bool:
        """Return True to indicate we want to handle streaming tokens."""
        return True
    
    @property
    def llm_end(self) -> bool:
        """Return True to indicate we want to handle llm_end."""
        return True
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> Any:
        """Called when LLM starts running. Reset streaming state."""
        self._streaming_content = ""
        self._streaming_tokens = []
        logger.debug(f"LLM started with {len(prompts)} prompts")
    
    def on_llm_new_token(self, token: str, **kwargs: Any) -> Any:
        """Called for each new token during streaming."""
        self._streaming_content += token
        self._streaming_tokens.append(token)
    
    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        """
        Called when LLM ends running. Perform hallucination analysis.
        
        This is the main integration point - we analyze the LLM output
        and attach the results to the response.
        """
        try:
            # Extract content from response
            content = self._extract_content(response)
            
            if not content:
                logger.warning("No content to analyze")
                return
            
            logger.debug(f"Analyzing {len(content)} characters of content")
            
            # Perform hallucination analysis
            guarded = self.guard._perform_full_analysis(
                content=content,
                model=self.model,
                messages=[{"role": "user", "content": "LangChain generation"}],
                rag_context=self.rag_context,
            )
            
            # Store the result
            self._last_guarded_response = guarded
            self._last_result = GuardedLLMResult(
                content=content,
                trust_score=guarded.trust_score,
                flagged_claims=guarded.flagged_claims,
                guarded_response=guarded,
                is_trustworthy=guarded.is_trustworthy(self.trust_threshold),
                report=guarded.report,
            )
            
            # Attach to response generations
            self._attach_to_response(response, guarded)
            
            # Handle low trust
            if not guarded.is_trustworthy(self.trust_threshold):
                logger.warning(
                    f"Low trust score: {guarded.trust_score:.2f} "
                    f"({len(guarded.flagged_claims)} flagged claims)"
                )
                if self.on_low_trust:
                    self.on_low_trust(self._last_result)
            
            # Handle critical hallucinations
            critical_claims = [c for c in guarded.claims if c.risk_level == RiskLevel.CRITICAL]
            if critical_claims:
                logger.error(f"Critical hallucination detected: {critical_claims[0].text}")
                if self.on_critical:
                    self.on_critical(critical_claims, self._last_result)
                if self.raise_on_critical:
                    raise HallucinationError(
                        f"Critical hallucination detected: {critical_claims[0].text}"
                    )
            
        except HallucinationError:
            raise
        except Exception as e:
            logger.error(f"Error during hallucination analysis: {e}")
    
    def _extract_content(self, response: Any) -> str:
        """Extract text content from various LangChain response types."""
        # Handle LLMResult
        if hasattr(response, 'generations'):
            texts = []
            for generations in response.generations:
                for generation in generations:
                    if hasattr(generation, 'text'):
                        texts.append(generation.text)
                    elif hasattr(generation, 'message'):
                        texts.append(str(generation.message.content))
            return "\n".join(texts)
        
        # Handle streaming content
        if self._streaming_content:
            return self._streaming_content
        
        # Handle ChatGeneration
        if hasattr(response, 'message'):
            return str(response.message.content)
        
        # Fallback
        return str(response)
    
    def _attach_to_response(self, response: Any, guarded: GuardedResponse):
        """Attach hallucination analysis to the response object."""
        if hasattr(response, 'generations'):
            for generations in response.generations:
                for generation in generations:
                    if hasattr(generation, 'generation_info'):
                        if generation.generation_info is None:
                            generation.generation_info = {}
                        generation.generation_info["halluciguard"] = {
                            "trust_score": guarded.trust_score,
                            "flagged_claims_count": len(guarded.flagged_claims),
                            "is_trustworthy": guarded.is_trustworthy(self.trust_threshold),
                        }
                    
                    # Also attach to message if present
                    if hasattr(generation, 'message'):
                        generation.message.guarded_response = guarded


class HalluciGuardLLMWrapper:
    """
    Wrapper that makes any LangChain LLM hallucination-aware.
    
    This provides a simpler interface for users who want to wrap
    their LLM without dealing with callbacks.
    
    Example:
        from langchain_openai import ChatOpenAI
        from halluciGuard.integrations.langchain import HalluciGuardLLMWrapper
        
        # Wrap your LLM
        base_llm = ChatOpenAI(model="gpt-4o")
        llm = HalluciGuardLLMWrapper(base_llm, api_key="sk-...")
        
        # Use normally - returns GuardedLLMResult
        result = llm.invoke("What is the capital of Australia?")
        print(f"Trust Score: {result.trust_score}")
        print(f"Content: {result.content}")
    """
    
    def __init__(
        self,
        llm: Any,
        provider: str = "openai",
        api_key: Optional[str] = None,
        config: Optional[GuardConfig] = None,
        rag_context: Optional[List[str]] = None,
    ):
        """
        Wrap a LangChain LLM with hallucination detection.
        
        Args:
            llm: The LangChain LLM to wrap
            provider: LLM provider for HalluciGuard
            api_key: API key for HalluciGuard
            config: GuardConfig for HalluciGuard
            rag_context: RAG context for verification
        """
        self._llm = llm
        self._handler = HalluciGuardCallbackHandler(
            provider=provider,
            api_key=api_key,
            config=config,
            rag_context=rag_context,
        )
    
    @property
    def llm(self):
        """Access the underlying LLM."""
        return self._llm
    
    @property
    def handler(self):
        """Access the HalluciGuard callback handler."""
        return self._handler
    
    def set_rag_context(self, context: List[str]):
        """Set RAG context for verification."""
        self._handler.set_rag_context(context)
    
    def invoke(self, input: Any, config: Optional[Dict] = None, **kwargs) -> GuardedLLMResult:
        """
        Invoke the LLM and return a GuardedLLMResult.
        
        Args:
            input: The input to pass to the LLM
            config: Optional LangChain config
            **kwargs: Additional arguments for the LLM
        
        Returns:
            GuardedLLMResult with content and hallucination analysis
        """
        # Merge callbacks
        callbacks = [self._handler]
        if config and 'callbacks' in config:
            callbacks.extend(config['callbacks'])
        
        run_config = config or {}
        run_config['callbacks'] = callbacks
        
        # Call the LLM
        response = self._llm.invoke(input, config=run_config, **kwargs)
        
        # Return the guarded result
        if self._handler.last_result:
            return self._handler.last_result
        
        # Fallback: create result from response
        content = str(response.content) if hasattr(response, 'content') else str(response)
        return GuardedLLMResult(
            content=content,
            trust_score=1.0,
            flagged_claims=[],
            guarded_response=None,
            is_trustworthy=True,
        )
    
    def stream(self, input: Any, config: Optional[Dict] = None, **kwargs):
        """
        Stream the LLM response with hallucination analysis at the end.
        
        Yields tokens as they arrive, then yields the final GuardedLLMResult.
        """
        callbacks = [self._handler]
        if config and 'callbacks' in config:
            callbacks.extend(config['callbacks'])
        
        run_config = config or {}
        run_config['callbacks'] = callbacks
        
        for chunk in self._llm.stream(input, config=run_config, **kwargs):
            yield chunk
        
        # After streaming, yield the result
        if self._handler.last_result:
            yield self._handler.last_result
    
    # Pass through other attributes to the underlying LLM
    def __getattr__(self, name):
        return getattr(self._llm, name)


# Convenience function for quick setup
def create_guarded_llm(
    llm: Any,
    api_key: Optional[str] = None,
    trust_threshold: float = 0.6,
    raise_on_critical: bool = False,
) -> HalluciGuardLLMWrapper:
    """
    Quick setup function to create a hallucination-guarded LLM.
    
    Example:
        from langchain_openai import ChatOpenAI
        from halluciGuard.integrations.langchain import create_guarded_llm
        
        llm = create_guarded_llm(
            ChatOpenAI(model="gpt-4o"),
            api_key=os.environ["OPENAI_API_KEY"]
        )
        
        result = llm.invoke("Tell me about quantum physics")
        if result.is_trustworthy:
            print(result.content)
        else:
            print(f"Warning: {len(result.flagged_claims)} flagged claims")
    """
    return HalluciGuardLLMWrapper(
        llm=llm,
        api_key=api_key,
        config=GuardConfig(
            trust_threshold=trust_threshold,
            raise_on_critical=raise_on_critical,
        ),
    )
