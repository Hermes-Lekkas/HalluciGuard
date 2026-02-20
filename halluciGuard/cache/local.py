# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors

import json
import os
import hashlib
from typing import Optional, Any, Dict
from .base import BaseCache

class LocalFileCache(BaseCache):
    """Simple JSON-based file cache for hallucination scores."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

    def _get_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._get_path(key)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def set(self, key: str, value: Dict[str, Any]):
        path = self._get_path(key)
        try:
            with open(path, 'w') as f:
                json.dump(value, f, indent=2)
        except Exception:
            pass

def hash_claim(claim: str) -> str:
    """Generates a stable MD5 hash for a claim string."""
    return hashlib.md5(claim.strip().lower().encode('utf-8')).hexdigest()
