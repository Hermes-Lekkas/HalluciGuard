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
Benchmark runner for evaluating LLM hallucination rates.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from .dataset import BenchmarkDataset, BenchmarkCase, Category
from ..errors import BenchmarkError, DatasetError

logger = logging.getLogger("halluciGuard")


def _get_utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    try:
        return datetime.now(datetime.timezone.utc)
    except AttributeError:
        return datetime.utcnow()


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test case."""
    case_id: str
    model: str
    provider: str
    prompt: str
    response: str
    category: str
    ground_truth_facts: List[str]
    detected_claims: List[str]
    flagged_claims: List[Dict[str, Any]]
    trust_score: float
    hallucination_detected: bool
    latency_seconds: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "model": self.model,
            "provider": self.provider,
            "prompt": self.prompt,
            "response": self.response,
            "category": self.category,
            "ground_truth_facts": self.ground_truth_facts,
            "detected_claims": self.detected_claims,
            "flagged_claims": self.flagged_claims,
            "trust_score": self.trust_score,
            "hallucination_detected": self.hallucination_detected,
            "latency_seconds": round(self.latency_seconds, 3),
            "error": self.error,
        }


@dataclass
class ModelScore:
    """Aggregated score for a model across all test cases."""
    model: str
    provider: str
    total_cases: int
    avg_trust_score: float
    hallucination_rate: float
    avg_latency_seconds: float
    category_scores: Dict[str, Dict[str, float]] = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = _get_utc_now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "total_cases": self.total_cases,
            "avg_trust_score": round(self.avg_trust_score, 4),
            "hallucination_rate": round(self.hallucination_rate, 4),
            "avg_latency_seconds": round(self.avg_latency_seconds, 3),
            "category_scores": self.category_scores,
            "timestamp": self.timestamp,
        }


class BenchmarkRunner:
    """
    Runs hallucination benchmarks against multiple LLM models.
    
    Example:
        from halluciGuard import Guard
        from halluciGuard.leaderboard import BenchmarkRunner, BenchmarkDataset
        
        dataset = BenchmarkDataset.load("benchmark_cases.json")
        runner = BenchmarkRunner(dataset)
        
        # Run for a single model
        results = runner.run_model(guard, "gpt-4o")
        
        # Get aggregated scores
        scores = runner.aggregate_scores(results)
    """
    
    def __init__(
        self,
        dataset: Optional[BenchmarkDataset] = None,
        output_dir: str = "benchmarks",
    ):
        self.dataset = dataset or BenchmarkDataset()
        self.output_dir = output_dir
        self.results: List[BenchmarkResult] = []
    
    def run_model(
        self,
        guard,  # Guard instance
        model: str,
        provider: Optional[str] = None,
        cases: Optional[List[BenchmarkCase]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[BenchmarkResult]:
        """
        Run benchmark for a single model.
        
        Args:
            guard: HalluciGuard Guard instance
            model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4.6")
            provider: Provider name (auto-detected from guard if not provided)
            cases: Specific cases to run (all if not provided)
            progress_callback: Callback for progress updates (current, total)
        
        Returns:
            List of BenchmarkResult objects
        """
        provider = provider or guard.provider
        cases = cases or self.dataset.cases
        results = []
        
        logger.info(f"Starting benchmark for {model} ({provider}) with {len(cases)} cases")
        
        for i, case in enumerate(cases):
            if progress_callback:
                progress_callback(i + 1, len(cases))
            
            result = self._run_single_case(guard, model, provider, case)
            results.append(result)
            
            # Log progress
            if (i + 1) % 5 == 0 or (i + 1) == len(cases):
                logger.info(f"Progress: {i + 1}/{len(cases)} cases completed")
        
        self.results.extend(results)
        return results
    
    def _run_single_case(
        self,
        guard,
        model: str,
        provider: str,
        case: BenchmarkCase,
    ) -> BenchmarkResult:
        """Run a single benchmark case."""
        start_time = time.time()
        
        try:
            # Call the LLM through HalluciGuard
            response = guard.chat(
                model=model,
                messages=[{"role": "user", "content": case.prompt}],
            )
            
            latency = time.time() - start_time
            
            # Analyze the response
            trust_score = response.trust_score
            detected_claims = [c.text for c in response.claims]
            flagged_claims = [
                {
                    "text": c.text,
                    "confidence": c.confidence,
                    "risk_level": c.risk_level.value,
                    "explanation": c.explanation,
                }
                for c in response.flagged_claims
            ]
            
            # Check for hallucinations against ground truth
            hallucination_detected = self._check_hallucination(
                response.content,
                case.ground_truth_facts,
                case.common_hallucinations,
            )
            
            return BenchmarkResult(
                case_id=case.id,
                model=model,
                provider=provider,
                prompt=case.prompt,
                response=response.content,
                category=case.category.value,
                ground_truth_facts=case.ground_truth_facts,
                detected_claims=detected_claims,
                flagged_claims=flagged_claims,
                trust_score=trust_score,
                hallucination_detected=hallucination_detected,
                latency_seconds=latency,
            )
            
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Error running case {case.id}: {e}")
            
            return BenchmarkResult(
                case_id=case.id,
                model=model,
                provider=provider,
                prompt=case.prompt,
                response="",
                category=case.category.value,
                ground_truth_facts=case.ground_truth_facts,
                detected_claims=[],
                flagged_claims=[],
                trust_score=0.0,
                hallucination_detected=True,  # Assume worst case on error
                latency_seconds=latency,
                error=str(e),
            )
    
    def _check_hallucination(
        self,
        response: str,
        ground_truth: List[str],
        common_hallucinations: List[str],
    ) -> bool:
        """
        Check if the response contains hallucinations.
        
        Returns True if hallucination is detected.
        """
        response_lower = response.lower()
        
        # Check for common hallucinations
        for hallucination in common_hallucinations:
            # Check if the hallucinated fact appears in the response
            key_terms = hallucination.lower().split()
            if len(key_terms) >= 2:
                # Check for significant overlap
                matches = sum(1 for term in key_terms if term in response_lower)
                if matches >= len(key_terms) * 0.7:
                    return True
        
        return False
    
    def aggregate_scores(self, results: List[BenchmarkResult]) -> ModelScore:
        """Aggregate results into a single model score."""
        if not results:
            raise BenchmarkError(
                model="unknown",
                reason="No benchmark results to aggregate. Run benchmark cases first using run_model() before aggregating scores.",
            )
        
        model = results[0].model
        provider = results[0].provider
        
        # Calculate overall metrics
        total_cases = len(results)
        avg_trust = sum(r.trust_score for r in results) / total_cases
        hallucination_count = sum(1 for r in results if r.hallucination_detected)
        hallucination_rate = hallucination_count / total_cases
        avg_latency = sum(r.latency_seconds for r in results) / total_cases
        
        # Calculate per-category scores
        category_results: Dict[str, List[BenchmarkResult]] = {}
        for r in results:
            if r.category not in category_results:
                category_results[r.category] = []
            category_results[r.category].append(r)
        
        category_scores = {}
        for cat, cat_results in category_results.items():
            cat_avg_trust = sum(r.trust_score for r in cat_results) / len(cat_results)
            cat_halluc_rate = sum(1 for r in cat_results if r.hallucination_detected) / len(cat_results)
            category_scores[cat] = {
                "avg_trust_score": round(cat_avg_trust, 4),
                "hallucination_rate": round(cat_halluc_rate, 4),
                "cases": len(cat_results),
            }
        
        return ModelScore(
            model=model,
            provider=provider,
            total_cases=total_cases,
            avg_trust_score=avg_trust,
            hallucination_rate=hallucination_rate,
            avg_latency_seconds=avg_latency,
            category_scores=category_scores,
        )
    
    def save_results(self, results: List[BenchmarkResult], filename: str = "benchmark_results.json"):
        """Save benchmark results to JSON file."""
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        
        data = {
            "timestamp": _get_utc_now().isoformat(),
            "total_results": len(results),
            "results": [r.to_dict() for r in results],
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Results saved to {path}")
    
    def save_leaderboard(self, scores: List[ModelScore], filename: str = "leaderboard.json"):
        """Save leaderboard to JSON file."""
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        
        # Sort by hallucination rate (lower is better)
        sorted_scores = sorted(scores, key=lambda s: s.hallucination_rate)
        
        data = {
            "timestamp": _get_utc_now().isoformat(),
            "version": "1.0",
            "leaderboard": [s.to_dict() for s in sorted_scores],
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Leaderboard saved to {path}")
        return path
