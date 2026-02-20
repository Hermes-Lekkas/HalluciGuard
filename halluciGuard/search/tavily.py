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

import os
import requests
from typing import List, Dict, Any
from .base import BaseSearchProvider

class TavilySearchProvider(BaseSearchProvider):
    """
    Search provider using the Tavily Search API.
    Requires TAVILY_API_KEY environment variable.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")

    def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        if not self.api_key:
            # Fallback for demonstration/safety - don't crash, just return empty
            return []
        
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": limit,
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except Exception:
            # For reliability, we return empty results on search failure
            # rather than failing the entire hallucination check.
            return []
