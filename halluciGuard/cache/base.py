# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

class BaseCache(ABC):
    """Abstract base class for hallucination scoring cache."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached result by key (hash of claim)."""
        pass

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any]):
        """Cache a result by key."""
        pass
