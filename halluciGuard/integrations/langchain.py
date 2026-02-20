# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors

from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from ..guard import Guard

class HalluciGuardCallbackHandler(BaseCallbackHandler):
    """
    LangChain CallbackHandler that automatically runs HalluciGuard
    on LLM generations.
    """
    
    def __init__(self, guard: Guard):
        self.guard = guard

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        """Runs hallucination analysis on the LLM output."""
        for generations in response.generations:
            for generation in generations:
                content = generation.text
                # Perform analysis
                # Note: LangChain doesn't easily allow modifying the generation in-place here
                # but we can attach metadata or log the result.
                guarded = self.guard._perform_full_analysis(
                    content=content,
                    model="langchain-wrapped",
                    messages=[{"role": "user", "content": "LangChain Generation"}]
                )
                
                # Attach analysis to generation metadata if possible
                if generation.generation_info is None:
                    generation.generation_info = {}
                generation.generation_info["halluciguard"] = {
                    "trust_score": guarded.trust_score,
                    "report": guarded.report
                }
                
                if not guarded.is_trustworthy(self.guard.config.trust_threshold):
                    # We can't easily block here without raising an exception
                    # which might be desired if config.raise_on_critical is true.
                    pass
