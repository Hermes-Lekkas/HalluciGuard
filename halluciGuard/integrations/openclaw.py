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
OpenClaw Integration — Middleware to intercept and verify OpenClaw agent actions.
"""

from typing import Dict, Any, Optional, List
from ..guard import Guard
from ..models import GuardedResponse, RiskLevel

class OpenClawInterceptor:
    """
    Hooks into OpenClaw's message gateway or skill-execution loop
    to verify agent outputs before they reach the user.
    """
    def __init__(self, guard: Guard):
        self.guard = guard

    def verify_message(
        self, 
        content: str, 
        query: str = "", 
        rag_context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Verify an agent's outgoing message for hallucinations.
        
        Returns:
            Dict containing:
                - 'is_safe': bool (True if trust_score >= threshold)
                - 'warning': Optional[str] (Warning message if low trust)
                - 'content': str (Original or modified content)
                - 'response': GuardedResponse (Full analysis)
        """
        response = self.guard._perform_full_analysis(
            content=content,
            model=self.guard.config.verifier_model or "gpt-4o-mini",
            messages=[{"role": "user", "content": query or "Verify agent action"}],
            rag_context=rag_context
        )

        is_safe = response.is_trustworthy(self.guard.config.trust_threshold)
        warning = None

        if not is_safe:
            flagged_count = len(response.flagged_claims)
            warning = (
                f"⚠️  HalluciGuard Alert: This agent message may contain "
                f"{flagged_count} hallucinated facts (Trust Score: {response.trust_score:.2f})."
            )

        return {
            "is_safe": is_safe,
            "warning": warning,
            "content": content,
            "response": response
        }

    def wrap_action(self, action_func):
        """Decorator to wrap an OpenClaw skill/action with verification."""
        def wrapper(*args, **kwargs):
            # 1. Execute the action
            result = action_func(*args, **kwargs)
            
            # 2. If result is text, verify it
            if isinstance(result, str):
                analysis = self.verify_message(result)
                if not analysis["is_safe"]:
                    return f"{analysis['warning']}\n\n{result}"
            
            return result
        return wrapper
