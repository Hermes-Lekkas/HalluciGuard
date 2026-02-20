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
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from halluciGuard import Guard, GuardConfig

app = FastAPI(title="HalluciGuard API")

# Initialize Guard - in a real app, this would be more configurable
# and use proper secret management.
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    guard = Guard(provider="openai", client=client)
except Exception:
    # Fallback to a mock/simulated guard if no API key
    guard = Guard(provider="openai", client=None)

class AnalyzeRequest(BaseModel):
    content: str
    query: Optional[str] = ""
    rag_context: Optional[List[str]] = None

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Analyze a piece of text for hallucinations.
    Useful for browser extensions or external integrations.
    """
    try:
        # We use a dummy model name since we might be using heuristics if no client
        messages = [{"role": "user", "content": request.query or "Verify this content"}]
        
        # We manually trigger the internal analysis logic 
        # because we already have the content (no need to call LLM again).
        result = guard._perform_full_analysis(
            content=request.content,
            model="gpt-4o-mini",
            messages=messages,
            rag_context=request.rag_context
        )
        
        # Convert to a serializable dict
        return {
            "trust_score": result.trust_score,
            "summary": result.summary(),
            "flagged_claims": [
                {
                    "text": c.text,
                    "confidence": c.confidence,
                    "risk_level": c.risk_level.value,
                    "explanation": c.explanation
                } for c in result.flagged_claims
            ],
            "report": result.report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
