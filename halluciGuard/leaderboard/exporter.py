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
Leaderboard exporter for generating HTML and JSON outputs.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from .benchmark import ModelScore


def _get_utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    try:
        return datetime.now(datetime.timezone.utc)
    except AttributeError:
        return datetime.utcnow()


class LeaderboardExporter:
    """
    Exports leaderboard data to various formats.
    
    Example:
        from halluciGuard.leaderboard import LeaderboardExporter, BenchmarkRunner
        
        runner = BenchmarkRunner(dataset)
        results = runner.run_model(guard, "gpt-4o")
        score = runner.aggregate_scores(results)
        
        exporter = LeaderboardExporter()
        exporter.to_html([score], "leaderboard.html")
    """
    
    def __init__(self, output_dir: str = "benchmarks"):
        self.output_dir = output_dir
    
    def to_json(
        self,
        scores: List[ModelScore],
        filename: str = "leaderboard.json",
        include_details: bool = True,
    ) -> str:
        """
        Export leaderboard to JSON format.
        
        Returns:
            Path to the generated file.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        
        # Sort by hallucination rate (lower is better)
        sorted_scores = sorted(scores, key=lambda s: s.hallucination_rate)
        
        data = {
            "timestamp": _get_utc_now().isoformat(),
            "version": "1.0",
            "total_models": len(sorted_scores),
            "leaderboard": [s.to_dict() for s in sorted_scores],
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        return path
    
    def to_html(
        self,
        scores: List[ModelScore],
        filename: str = "leaderboard.html",
        title: str = "HalluciGuard Leaderboard",
        description: str = "Public benchmark of LLM hallucination rates",
    ) -> str:
        """
        Export leaderboard to a standalone HTML page.
        
        Returns:
            Path to the generated file.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        
        # Sort by hallucination rate (lower is better)
        sorted_scores = sorted(scores, key=lambda s: s.hallucination_rate)
        
        html = self._generate_html(sorted_scores, title, description)
        
        with open(path, "w") as f:
            f.write(html)
        
        return path
    
    def _generate_html(
        self,
        scores: List[ModelScore],
        title: str,
        description: str,
    ) -> str:
        """Generate the full HTML page."""
        
        # Generate table rows
        table_rows = []
        for rank, score in enumerate(scores, 1):
            medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else ""))
            
            # Determine trust level color
            if score.avg_trust_score >= 0.8:
                trust_color = "#4caf50"
                trust_label = "HIGH"
            elif score.avg_trust_score >= 0.6:
                trust_color = "#ff9800"
                trust_label = "MODERATE"
            else:
                trust_color = "#f44336"
                trust_label = "LOW"
            
            # Determine hallucination rate color
            if score.hallucination_rate <= 0.1:
                hallu_color = "#4caf50"
            elif score.hallucination_rate <= 0.3:
                hallu_color = "#ff9800"
            else:
                hallu_color = "#f44336"
            
            row = f"""
            <tr>
                <td class="rank">{medal} #{rank}</td>
                <td class="model">
                    <strong>{self._escape_html(score.model)}</strong>
                    <span class="provider">{self._escape_html(score.provider)}</span>
                </td>
                <td class="trust-score" style="color: {trust_color}">
                    {score.avg_trust_score:.2%}
                    <span class="label">{trust_label}</span>
                </td>
                <td class="hallucination-rate" style="color: {hallu_color}">
                    {score.hallucination_rate:.1%}
                </td>
                <td class="latency">{score.avg_latency_seconds:.2f}s</td>
                <td class="cases">{score.total_cases}</td>
            </tr>
            """
            table_rows.append(row)
        
        # Generate category breakdown
        category_section = self._generate_category_section(scores)
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(title)}</title>
    <meta name="description" content="{self._escape_html(description)}">
    <meta property="og:title" content="{self._escape_html(title)}">
    <meta property="og:description" content="{self._escape_html(description)}">
    <meta property="og:type" content="website">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .subtitle {{
            color: #888;
            font-size: 1.1rem;
        }}
        .badge {{
            display: inline-block;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            margin-top: 1rem;
        }}
        .stats-bar {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin: 2rem 0;
            flex-wrap: wrap;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #00d4ff;
        }}
        .stat-label {{
            color: #888;
            font-size: 0.9rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 1rem;
            overflow: hidden;
            margin-bottom: 2rem;
        }}
        th {{
            background: rgba(0, 212, 255, 0.1);
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.05em;
        }}
        td {{
            padding: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        tr:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}
        .rank {{
            font-size: 1.2rem;
            width: 80px;
        }}
        .model strong {{
            display: block;
            font-size: 1.1rem;
        }}
        .provider {{
            color: #888;
            font-size: 0.8rem;
        }}
        .label {{
            display: block;
            font-size: 0.7rem;
            opacity: 0.7;
        }}
        .category-section {{
            margin-top: 3rem;
        }}
        .category-section h2 {{
            margin-bottom: 1rem;
            color: #00d4ff;
        }}
        .category-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }}
        .category-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 1rem;
            padding: 1.5rem;
        }}
        .category-card h3 {{
            margin-bottom: 1rem;
            text-transform: capitalize;
        }}
        .category-card .model-row {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .timestamp {{
            text-align: center;
            color: #666;
            margin-top: 2rem;
            font-size: 0.9rem;
        }}
        .footer {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .footer a {{
            color: #00d4ff;
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        @media (max-width: 768px) {{
            h1 {{
                font-size: 1.8rem;
            }}
            .stats-bar {{
                gap: 1rem;
            }}
            table {{
                font-size: 0.9rem;
            }}
            th, td {{
                padding: 0.75rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛡️ {self._escape_html(title)}</h1>
            <p class="subtitle">{self._escape_html(description)}</p>
            <span class="badge">Open Source • AGPL-3.0</span>
        </header>
        
        <div class="stats-bar">
            <div class="stat">
                <div class="stat-value">{len(scores)}</div>
                <div class="stat-label">Models Tested</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sum(s.total_cases for s in scores) // max(len(scores), 1)}</div>
                <div class="stat-label">Test Cases</div>
            </div>
            <div class="stat">
                <div class="stat-value">{min(s.hallucination_rate for s in scores):.0%}</div>
                <div class="stat-label">Best Hallucination Rate</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Model</th>
                    <th>Trust Score</th>
                    <th>Hallucination Rate</th>
                    <th>Avg Latency</th>
                    <th>Tests</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
        
        {category_section}
        
        <p class="timestamp">
            Last updated: {_get_utc_now().strftime('%B %d, %Y at %H:%M UTC')}
        </p>
        
        <div class="footer">
            <p>
                Generated by <a href="https://github.com/Hermes-Lekkas/HalluciGuard">HalluciGuard</a> • 
                <a href="leaderboard.json">View JSON Data</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    def _generate_category_section(self, scores: List[ModelScore]) -> str:
        """Generate the category breakdown section."""
        # Collect all categories
        all_categories = set()
        for score in scores:
            all_categories.update(score.category_scores.keys())
        
        if not all_categories:
            return ""
        
        cards = []
        for category in sorted(all_categories):
            # Get scores for this category
            category_data = []
            for score in scores:
                if category in score.category_scores:
                    cat_score = score.category_scores[category]
                    category_data.append({
                        "model": score.model,
                        "trust_score": cat_score["avg_trust_score"],
                        "hallucination_rate": cat_score["hallucination_rate"],
                    })
            
            # Sort by hallucination rate
            category_data.sort(key=lambda x: x["hallucination_rate"])
            
            rows = []
            for data in category_data[:5]:  # Top 5 only
                rows.append(f"""
                <div class="model-row">
                    <span>{self._escape_html(data['model'])}</span>
                    <span>{data['hallucination_rate']:.0%} hallucinations</span>
                </div>
                """)
            
            cards.append(f"""
            <div class="category-card">
                <h3>{category.title()}</h3>
                {''.join(rows)}
            </div>
            """)
        
        return f"""
        <div class="category-section">
            <h2>📊 Category Breakdown</h2>
            <div class="category-grid">
                {''.join(cards)}
            </div>
        </div>
        """
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#39;")
        return text
    
    def to_markdown(
        self,
        scores: List[ModelScore],
        filename: str = "leaderboard.md",
    ) -> str:
        """
        Export leaderboard to Markdown format for README inclusion.
        
        Returns:
            Path to the generated file.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        
        # Sort by hallucination rate
        sorted_scores = sorted(scores, key=lambda s: s.hallucination_rate)
        
        lines = [
            "# 🛡️ HalluciGuard Leaderboard",
            "",
            f"> Last updated: {_get_utc_now().strftime('%B %d, %Y')}",
            "",
            "## Overall Rankings",
            "",
            "| Rank | Model | Trust Score | Hallucination Rate | Latency |",
            "|------|-------|-------------|-------------------|---------|",
        ]
        
        for rank, score in enumerate(sorted_scores, 1):
            medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else ""))
            lines.append(
                f"| {medal} #{rank} | {score.model} | {score.avg_trust_score:.2%} | "
                f"{score.hallucination_rate:.1%} | {score.avg_latency_seconds:.2f}s |"
            )
        
        lines.extend([
            "",
            "## Methodology",
            "",
            "- **Trust Score**: Average confidence across all claims (0.0-1.0)",
            "- **Hallucination Rate**: Percentage of responses containing factual errors",
            "- **Latency**: Average response time in seconds",
            "",
            "---",
            "",
            "*Generated by [HalluciGuard](https://github.com/Hermes-Lekkas/HalluciGuard)*",
        ])
        
        with open(path, "w") as f:
            f.write("\n".join(lines))
        
        return path
