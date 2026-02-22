#!/usr/bin/env python3
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
HalluciGuard Benchmark CLI

Run hallucination benchmarks against multiple LLM models and generate
a public leaderboard.

Usage:
    python scripts/run_benchmark.py --models gpt-4o,claude-sonnet-4.6 --output benchmarks/

Environment Variables:
    OPENAI_API_KEY: OpenAI API key for GPT models
    ANTHROPIC_API_KEY: Anthropic API key for Claude models
    GOOGLE_API_KEY: Google API key for Gemini models
"""

import argparse
import logging
import os
import sys
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from halluciGuard import Guard, GuardConfig
from halluciGuard.leaderboard import (
    BenchmarkRunner,
    BenchmarkDataset,
    BenchmarkCase,
    LeaderboardExporter,
)
from halluciGuard.leaderboard.dataset import get_default_dataset, Category

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("halluciGuard.benchmark")


# Model configurations
MODEL_CONFIGS = {
    # OpenAI models
    "gpt-4o": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    "gpt-4o-mini": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    "gpt-5.2-instant": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    "gpt-5.2-thinking": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    "gpt-5.3-codex": {"provider": "openai", "env_key": "OPENAI_API_KEY"},
    
    # Anthropic models
    "claude-3-5-sonnet-20240620": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    "claude-3-opus-20240229": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    "claude-opus-4.6": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    "claude-sonnet-4.6": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    "claude-haiku-4-5-20251001": {"provider": "anthropic", "env_key": "ANTHROPIC_API_KEY"},
    
    # Google models
    "gemini-1.5-pro": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
    "gemini-1.5-flash": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
    "gemini-3.1-pro": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
    "gemini-3-flash": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
    "gemini-3-deep-think": {"provider": "google", "env_key": "GOOGLE_API_KEY"},
}


def create_guard_for_model(model: str) -> Optional[Guard]:
    """Create a Guard instance for the specified model."""
    if model not in MODEL_CONFIGS:
        logger.error(f"Unknown model: {model}")
        return None
    
    config = MODEL_CONFIGS[model]
    provider = config["provider"]
    env_key = config["env_key"]
    
    api_key = os.environ.get(env_key)
    if not api_key:
        logger.warning(f"API key not found: {env_key} (required for {model})")
        return None
    
    try:
        guard = Guard(provider=provider, api_key=api_key)
        logger.info(f"Initialized Guard for {model} ({provider})")
        return guard
    except Exception as e:
        logger.error(f"Failed to initialize Guard for {model}: {e}")
        return None


def run_benchmark(
    models: List[str],
    output_dir: str,
    categories: Optional[List[str]] = None,
    max_cases: Optional[int] = None,
    dry_run: bool = False,
):
    """Run the benchmark for specified models."""
    
    # Load dataset
    dataset = get_default_dataset()
    
    # Filter by categories if specified
    if categories:
        category_enums = [Category(c) for c in categories]
        cases = []
        for cat in category_enums:
            cases.extend(dataset.get_by_category(cat))
        dataset = BenchmarkDataset(cases=cases)
        logger.info(f"Filtered to {len(cases)} cases in categories: {categories}")
    
    # Limit cases if specified
    if max_cases:
        dataset = BenchmarkDataset(cases=dataset.cases[:max_cases])
        logger.info(f"Limited to {len(dataset.cases)} cases")
    
    logger.info(f"Total benchmark cases: {len(dataset.cases)}")
    
    if dry_run:
        logger.info("Dry run - listing cases only:")
        for case in dataset.cases:
            logger.info(f"  - [{case.category.value}] {case.id}: {case.prompt[:50]}...")
        return
    
    # Initialize runner
    runner = BenchmarkRunner(dataset=dataset, output_dir=output_dir)
    exporter = LeaderboardExporter(output_dir=output_dir)
    
    all_scores = []
    
    for model in models:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running benchmark for: {model}")
        logger.info(f"{'='*60}")
        
        guard = create_guard_for_model(model)
        if guard is None:
            logger.warning(f"Skipping {model} - no valid API key")
            continue
        
        # Progress callback
        def progress(current: int, total: int):
            if current % 5 == 0 or current == total:
                logger.info(f"  Progress: {current}/{total}")
        
        # Run benchmark
        try:
            results = runner.run_model(guard, model, progress_callback=progress)
            score = runner.aggregate_scores(results)
            all_scores.append(score)
            
            logger.info(f"\n  Results for {model}:")
            logger.info(f"    Trust Score: {score.avg_trust_score:.2%}")
            logger.info(f"    Hallucination Rate: {score.hallucination_rate:.1%}")
            logger.info(f"    Avg Latency: {score.avg_latency_seconds:.2f}s")
            
        except Exception as e:
            logger.error(f"  Benchmark failed for {model}: {e}")
            continue
    
    if not all_scores:
        logger.error("No benchmarks completed successfully")
        return
    
    # Save results
    logger.info(f"\n{'='*60}")
    logger.info("Generating leaderboard...")
    logger.info(f"{'='*60}")
    
    # Save JSON
    json_path = exporter.to_json(all_scores, "leaderboard.json")
    logger.info(f"  JSON: {json_path}")
    
    # Save HTML
    html_path = exporter.to_html(
        all_scores,
        "leaderboard.html",
        title="HalluciGuard Leaderboard",
        description="Public benchmark of LLM hallucination rates",
    )
    logger.info(f"  HTML: {html_path}")
    
    # Save Markdown
    md_path = exporter.to_markdown(all_scores, "leaderboard.md")
    logger.info(f"  Markdown: {md_path}")
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("LEADERBOARD SUMMARY")
    logger.info(f"{'='*60}")
    
    sorted_scores = sorted(all_scores, key=lambda s: s.hallucination_rate)
    for rank, score in enumerate(sorted_scores, 1):
        medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else "  "))
        logger.info(f"  {medal} #{rank} {score.model}: {score.hallucination_rate:.1%} hallucinations, {score.avg_trust_score:.2%} trust")


def main():
    parser = argparse.ArgumentParser(
        description="Run HalluciGuard benchmarks and generate leaderboard"
    )
    parser.add_argument(
        "--models", "-m",
        type=str,
        default="gpt-4o-mini",
        help="Comma-separated list of models to benchmark (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="benchmarks",
        help="Output directory for results (default: benchmarks)"
    )
    parser.add_argument(
        "--categories", "-c",
        type=str,
        default=None,
        help="Comma-separated list of categories to test (default: all)"
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Maximum number of cases to run per model (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List test cases without running benchmarks"
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit"
    )
    
    args = parser.parse_args()
    
    if args.list_models:
        print("Available models:")
        for model, config in MODEL_CONFIGS.items():
            print(f"  - {model} ({config['provider']}, requires {config['env_key']})")
        return
    
    models = [m.strip() for m in args.models.split(",")]
    categories = [c.strip() for c in args.categories.split(",")] if args.categories else None
    
    run_benchmark(
        models=models,
        output_dir=args.output,
        categories=categories,
        max_cases=args.max_cases,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
