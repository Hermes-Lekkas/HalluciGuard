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
ClaimExtractor — Uses an LLM call to parse factual claims from a response.
"""

import json
import re
from typing import List, Optional, Callable

from .config import GuardConfig

EXTRACTION_PROMPT = """You are a factual claim extractor. Given an AI response, extract all discrete factual claims.

Rules:
- Extract ONLY specific, verifiable facts (dates, names, numbers, events, scientific claims)
- Skip opinions, recommendations, and general statements that can't be fact-checked
- Keep each claim concise (1-2 sentences max)
- Maximum {max_claims} claims

Respond ONLY with a JSON array of strings. Example:
["Einstein published the special theory of relativity in 1905.", "Water boils at 100°C at sea level."]

AI Response to analyze:
{response_text}
"""


class ClaimExtractor:
    """
    Extracts verifiable factual claims from LLM responses using a secondary LLM call.

    Falls back to regex-based heuristic extraction if the LLM call is unavailable.
    """

    def __init__(self, config: GuardConfig, llm_caller: Optional[Callable] = None):
        self.config = config
        self.llm_caller = llm_caller

    def extract(
        self,
        response_text: str,
        query: str = "",
        model: str = "gpt-4o-mini",
    ) -> List[str]:
        """
        Extract a list of factual claim strings from the LLM response.

        Returns:
            List of claim strings (plain text).
        """
        try:
            return self._extract_via_llm(response_text, model)
        except Exception as e:
            # Graceful degradation: use heuristic extraction
            return self._extract_heuristic(response_text)

    def _extract_via_llm(self, response_text: str, model: str) -> List[str]:
        """Use an LLM call to extract claims as structured JSON."""
        prompt = EXTRACTION_PROMPT.format(
            response_text=response_text[:3000],  # Limit to avoid huge token costs
            max_claims=self.config.max_claims_per_response,
        )

        if self.llm_caller:
            # Use the caller provided by the Guard (re-uses same client/auth)
            _, raw = self.llm_caller(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=800,
            )
            return self._parse_claims_json(raw)

        # Try to use OpenAI if available (legacy fallback)
        try:
            import openai
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=800,
            )
            raw = resp.choices[0].message.content or "[]"
            return self._parse_claims_json(raw)
        except Exception:
            pass

        # Try Anthropic if available
        try:
            import anthropic
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text if resp.content else "[]"
            return self._parse_claims_json(raw)
        except Exception:
            pass

        raise RuntimeError("No LLM client available for claim extraction.")

    def _parse_claims_json(self, raw: str) -> List[str]:
        """Parse JSON array from LLM output, with fallback cleaning."""
        # Strip markdown code fences
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            claims = json.loads(raw)
            if isinstance(claims, list):
                return [str(c).strip() for c in claims if c]
        except json.JSONDecodeError:
            pass
        # Try to extract strings with regex
        return re.findall(r'"([^"]{10,})"', raw)

    def _extract_heuristic(self, text: str) -> List[str]:
        """
        Fallback: extract candidate claims from sentences that contain
        indicators of factual content (numbers, proper nouns, dates, etc.)
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        factual_indicators = re.compile(
            r'(\d{4}|\d+%|[A-Z][a-z]+ [A-Z][a-z]+|published|invented|discovered|'
            r'founded|born|died|located|consists of|defined as|equals|'
            r'according to|research shows|studies show)'
        )
        claims = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 20 and factual_indicators.search(sent):
                claims.append(sent)
                if len(claims) >= self.config.max_claims_per_response:
                    break
        return claims
