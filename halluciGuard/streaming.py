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

from typing import Any, Callable, Dict, List, Optional
from .models import GuardedResponse

class StreamingGuardedResponse:
    """
    A wrapper around an LLM stream that collects the full response
    and performs hallucination analysis after the stream completes.
    """
    def __init__(
        self, 
        stream: Any, 
        provider: str,
        analysis_callback: Callable[[str], GuardedResponse]
    ):
        self._stream = stream
        self._provider = provider
        self._callback = analysis_callback
        self.content = ""
        self.guarded_response: Optional[GuardedResponse] = None

    def __iter__(self):
        for chunk in self._stream:
            text = self._extract_text(chunk)
            self.content += text
            yield chunk
        
        # Stream finished, trigger analysis
        self.guarded_response = self._callback(self.content)

    def _extract_text(self, chunk: Any) -> str:
        """Extract text from provider-specific stream chunks."""
        if self._provider == "openai" or self._provider == "openai_compatible":
            if hasattr(chunk, 'choices') and chunk.choices:
                return chunk.choices[0].delta.content or ""
        elif self._provider == "anthropic":
            # Anthropic stream events: message_start, content_block_start, content_block_delta, etc.
            if hasattr(chunk, 'type') and chunk.type == "content_block_delta":
                return chunk.delta.text or ""
        elif self._provider == "google":
            # Gemini stream response chunks
            try:
                return chunk.text
            except Exception:
                return ""
        elif self._provider == "ollama":
            if isinstance(chunk, dict):
                return chunk.get("message", {}).get("content", "")
        return ""
