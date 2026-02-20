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
HallucinationScorer — Scores each extracted claim for hallucination risk.

Scoring approach (multi-signal):
1. LLM Self-Consistency: Ask a verifier LLM to evaluate the claim.
2. Uncertainty signals: Detects hedging language that LLMs use when unsure.
3. Named entity check: Flags claims about specific people/places/dates as higher risk.
4. (Optional) Web verification: Cross-references with search results.
"""

import re
import json
from typing import List, Optional, Callable, Dict

from ..config import GuardConfig
from ..models import Claim, RiskLevel
from ..cache.local import LocalFileCache, hash_claim

SCORER_PROMPT = """You are a hallucination detector. For each factual claim below, assess the likelihood it is accurate.

For each claim:
- Score confidence from 0.0 (very likely hallucinated) to 1.0 (very likely true)
- Give a brief reason (1 sentence)

Respond ONLY with a JSON array of objects:
[
  {{"claim": "...", "confidence": 0.95, "reason": "Well-established fact."}},
  {{"claim": "...", "confidence": 0.12, "reason": "Einstein won for photoelectric effect, not relativity."}}
]

Claims to evaluate:
{claims_json}
"""

# Words that indicate the LLM itself may be uncertain
UNCERTAINTY_PATTERNS = re.compile(
    r'\b(approximately|roughly|around|about|I believe|I think|'
    r'if I recall|as far as I know|may have|might have|possibly|'
    r'probably|seems to|appears to|reportedly|allegedly)\b',
    re.IGNORECASE,
)

# High-risk claim patterns (specific facts most likely to be hallucinated)
HIGH_RISK_PATTERNS = re.compile(
    r'\b(ISBN|DOI|exact quote|page \d+|chapter \d+|in \d{4} he|'
    r'born on|died on|on (January|February|March|April|May|June|'
    r'July|August|September|October|November|December) \d)\b',
    re.IGNORECASE,
)


WEB_VERIFICATION_PROMPT = """You are a fact-checker. Verify the following claim against the provided search results.

Claim: {claim}

Search Results:
{search_results}

Rules:
- If the search results strongly support the claim, give a high confidence (0.85-1.0).
- If the search results contradict the claim, give a low confidence (0.0-0.3).
- If the search results are inconclusive or irrelevant, maintain a neutral confidence (0.5-0.7).

Respond ONLY with JSON:
{{"confidence": 0.0-1.0, "reason": "Short explanation"}}
"""


RAG_VERIFICATION_PROMPT = """You are an auditor. Verify the following claim against the provided reference context.

Claim: {claim}

Reference Context:
{rag_context}

Rules:
- If the claim is directly supported by the context, give a high confidence (0.9-1.0).
- If the claim is contradicted by the context, give a low confidence (0.0-0.2).
- If the context does not contain enough information to verify the claim, give a neutral confidence (0.5).

Respond ONLY with JSON:
{{"confidence": 0.0-1.0, "reason": "Short explanation"}}
"""


class HallucinationScorer:
    """
    Scores a list of claim strings and returns Claim objects with risk levels.
    """

    def __init__(self, config: GuardConfig, llm_caller: Optional[Callable] = None):
        self.config = config
        self.llm_caller = llm_caller
        self.cache = None
        if self.config.cache_enabled:
            self.cache = LocalFileCache(self.config.cache_dir)

    def score_all(
        self,
        claims: List[str],
        context: str,
        rag_context: Optional[List[str]] = None,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
    ) -> List[Claim]:
        """Score all claims and return list of Claim objects."""
        if not claims:
            return []

        final_claims: List[Claim] = []
        remaining_claims: List[str] = []
        cache_map: Dict[str, str] = {} # hash -> original text

        # 1. Check Cache
        if self.cache:
            for c_text in claims:
                h = hash_claim(c_text)
                cached = self.cache.get(h)
                if cached:
                    final_claims.append(Claim(
                        text=cached["text"],
                        confidence=cached["confidence"],
                        risk_level=RiskLevel(cached["risk_level"]),
                        explanation=f"[CACHED] {cached['explanation']}",
                        sources=cached.get("sources", []),
                        is_verifiable=cached.get("is_verifiable", True)
                    ))
                else:
                    remaining_claims.append(c_text)
                    cache_map[h] = c_text
        else:
            remaining_claims = claims

        if not remaining_claims:
            return final_claims

        # 2. Primary scoring for remaining claims
        scored = None
        if self.config.local_model_path:
            try:
                scored = self._score_via_local_model(remaining_claims)
            except Exception:
                pass

        if not scored:
            try:
                scored = self._score_via_llm(remaining_claims, model)
            except Exception:
                scored = self._score_heuristic(remaining_claims)

        # 3. RAG verification (High priority if context is provided)
        if rag_context:
            scored = self._enrich_with_rag_verification(scored, rag_context, model)

        # 4. Web verification (optional enrichment)
        if self.config.enable_web_verification and self.config.search_provider:
            scored = self._enrich_with_web_verification(scored, model)

        # 5. Update Cache
        if self.cache:
            for s_claim in scored:
                h = hash_claim(s_claim.text)
                self.cache.set(h, {
                    "text": s_claim.text,
                    "confidence": s_claim.confidence,
                    "risk_level": s_claim.risk_level.value,
                    "explanation": s_claim.explanation,
                    "sources": s_claim.sources,
                    "is_verifiable": s_claim.is_verifiable
                })

        return final_claims + scored

    def _score_via_local_model(self, claims: List[str]) -> List[Claim]:
        """
        Use a local fine-tuned model for scoring. 
        Expects llama-cpp-python or similar to be installed.
        """
        # This is a placeholder for actual local model inference logic.
        # In a real implementation, you would load the model once and reuse it.
        try:
            from llama_cpp import Llama
            llm = Llama(model_path=self.config.local_model_path, verbose=False)
            
            prompt = SCORER_PROMPT.format(claims_json=json.dumps(claims))
            output = llm(prompt, max_tokens=1000, temperature=0)
            raw = output["choices"][0]["text"]
            return self._parse_scored_claims(raw, claims)
        except ImportError:
            raise RuntimeError("llama-cpp-python not installed for local model support.")
        except Exception as e:
            raise RuntimeError(f"Local model inference failed: {e}")

    def _verify_via_local_model(self, prompt: str) -> str:
        """Helper for local model verification calls (Web/RAG)."""
        try:
            from llama_cpp import Llama
            llm = Llama(model_path=self.config.local_model_path, verbose=False)
            output = llm(prompt, max_tokens=500, temperature=0)
            return output["choices"][0]["text"]
        except Exception:
            return "{}"

    def _enrich_with_rag_verification(self, claims: List[Claim], rag_context: List[str], model: str) -> List[Claim]:
        """Cross-reference claims against provided RAG context."""
        context_str = "\n---\n".join(rag_context)
        
        for claim in claims:
            # We verify ALL claims against RAG context if it exists, as it's the "ground truth"
            try:
                rag_score_raw = self._verify_claim_against_rag(claim.text, context_str, model)
                rag_data = json.loads(re.sub(r"```(?:json)?", "", rag_score_raw).strip().strip("`").strip())
                
                # RAG context is high authority. Blend or override.
                # If RAG is definitive (very high or very low), it should dominate.
                rag_conf = float(rag_data.get("confidence", 0.5))
                
                if abs(rag_conf - 0.5) > 0.2: # If RAG says something definitive
                    claim.confidence = rag_conf
                    claim.explanation = f"RAG VERIFIED: {rag_data.get('reason')} (Prev: {claim.explanation})"
                
                claim.risk_level = self._confidence_to_risk(claim.confidence)
                if "RAG" not in claim.sources:
                    claim.sources.append("RAG Context")
            except Exception:
                pass
        
        return claims

    def _verify_claim_against_rag(self, claim: str, context_str: str, model: str) -> str:
        """Call LLM to verify a single claim against RAG context."""
        prompt = RAG_VERIFICATION_PROMPT.format(claim=claim, rag_context=context_str)
        
        if self.llm_caller:
            _, raw = self.llm_caller(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return raw

        try:
            import openai
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return resp.choices[0].message.content or "{}"
        except Exception:
            pass
        return "{}"

    def _enrich_with_web_verification(self, claims: List[Claim], model: str) -> List[Claim]:
        """Optionally cross-reference claims with web search results."""
        # Only verify MEDIUM/HIGH/CRITICAL risk claims to save on API costs/latency
        to_verify = [
            c for c in claims 
            if c.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)
        ]
        
        for claim in to_verify:
            search_results = self.config.search_provider.search(claim.text, limit=3)
            if not search_results:
                continue

            # Format search results for the prompt
            snippets = "\n---\n".join([
                f"Title: {r.get('title')}\nSource: {r.get('url')}\nSnippet: {r.get('content')}"
                for r in search_results
            ])

            # Ask LLM to re-evaluate based on search results
            try:
                web_score_raw = self._verify_claim_against_web(claim.text, snippets, model)
                web_data = json.loads(re.sub(r"```(?:json)?", "", web_score_raw).strip().strip("`").strip())
                
                # Blend the scores (web verification has high weight)
                new_confidence = (claim.confidence * 0.3) + (float(web_data.get("confidence", 0.5)) * 0.7)
                claim.confidence = round(new_confidence, 4)
                claim.explanation = f"WEB VERIFIED: {web_data.get('reason')} (Original: {claim.explanation})"
                claim.risk_level = self._confidence_to_risk(claim.confidence)
                claim.sources.extend([r.get('url') for r in search_results if r.get('url')])
            except Exception:
                pass # Fall back to primary score on web verification failure

        return claims

    def _verify_claim_against_web(self, claim: str, snippets: str, model: str) -> str:
        """Call LLM to verify a single claim against search snippets."""
        prompt = WEB_VERIFICATION_PROMPT.format(claim=claim, search_results=snippets)
        
        if self.llm_caller:
            _, raw = self.llm_caller(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return raw

        # Simple routing for verification call
        try:
            import openai
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return resp.choices[0].message.content or "{}"
        except Exception:
            pass
        
        return "{}"

    def _score_via_llm(self, claims: List[str], model: str) -> List[Claim]:
        """Use a verifier LLM to score claims."""
        prompt = SCORER_PROMPT.format(
            claims_json=json.dumps(claims, indent=2)
        )

        if self.llm_caller:
            _, raw = self.llm_caller(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1200,
            )
            return self._parse_scored_claims(raw, claims)

        raw = None
        # Try OpenAI (fallback)
        try:
            import openai
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1200,
            )
            raw = resp.choices[0].message.content or ""
        except Exception:
            pass

        # Try Anthropic
        if raw is None:
            try:
                import anthropic
                client = anthropic.Anthropic()
                resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1200,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = resp.content[0].text if resp.content else ""
            except Exception:
                pass

        if raw is None:
            raise RuntimeError("LLM scoring unavailable.")

        return self._parse_scored_claims(raw, claims)

    def _parse_scored_claims(self, raw: str, original_claims: List[str]) -> List[Claim]:
        """Parse LLM scoring response into Claim objects."""
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            return self._score_heuristic(original_claims)

        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            confidence = float(item.get("confidence", 0.5))
            claim_text = item.get("claim", "")
            reason = item.get("reason", "")

            # Apply heuristic adjustments on top of LLM score
            confidence = self._apply_heuristic_adjustments(claim_text, confidence)
            risk = self._confidence_to_risk(confidence)

            result.append(Claim(
                text=claim_text,
                confidence=confidence,
                risk_level=risk,
                explanation=reason,
                is_verifiable=True,
            ))
        return result

    def _score_heuristic(self, claims: List[str]) -> List[Claim]:
        """Pure heuristic scoring when no LLM is available."""
        result = []
        for claim in claims:
            confidence = 0.65  # Neutral baseline
            confidence = self._apply_heuristic_adjustments(claim, confidence)
            risk = self._confidence_to_risk(confidence)
            result.append(Claim(
                text=claim,
                confidence=confidence,
                risk_level=risk,
                explanation="Heuristic analysis (no LLM verifier available).",
                is_verifiable=True,
            ))
        return result

    def _apply_heuristic_adjustments(self, claim_text: str, base_score: float) -> float:
        """Nudge confidence based on linguistic signals."""
        score = base_score

        # Penalise uncertainty language
        if UNCERTAINTY_PATTERNS.search(claim_text):
            score -= 0.15

        # Penalise high-risk patterns (very specific facts likely to be confabulated)
        if HIGH_RISK_PATTERNS.search(claim_text):
            score -= 0.12

        # Reward short, simple claims
        if len(claim_text.split()) < 12:
            score += 0.05

        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def _confidence_to_risk(confidence: float) -> RiskLevel:
        if confidence >= 0.85:
            return RiskLevel.SAFE
        elif confidence >= 0.70:
            return RiskLevel.LOW
        elif confidence >= 0.50:
            return RiskLevel.MEDIUM
        elif confidence >= 0.25:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
