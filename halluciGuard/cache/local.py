# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors

import json
import logging
import os
import hashlib
from typing import Optional, Any, Dict
from .base import BaseCache

logger = logging.getLogger("halluciGuard")


class CachePermissionError(Exception):
    """Raised when cache directory cannot be created or accessed due to permissions."""
    pass


class LocalFileCache(BaseCache):
    """Simple JSON-based file cache for hallucination scores."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self._initialized = False
        self._init_error: Optional[str] = None
        
        try:
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
                logger.debug(f"Created cache directory: {cache_dir}")
            
            # Verify write permissions
            test_file = os.path.join(cache_dir, ".write_test")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                self._initialized = True
                logger.debug(f"Cache initialized successfully: {cache_dir}")
            except PermissionError:
                self._init_error = (
                    f"Cache directory '{cache_dir}' is not writable. "
                    f"Cache will be disabled for this session."
                )
                logger.warning(self._init_error)
        except PermissionError as e:
            self._init_error = (
                f"Cannot create cache directory '{cache_dir}': Permission denied. "
                f"Cache will be disabled for this session."
            )
            logger.warning(self._init_error)
        except Exception as e:
            self._init_error = f"Cache initialization failed: {e}"
            logger.warning(self._init_error)

    def _get_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if not self._initialized:
            return None
            
        path = self._get_path(key)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted cache file {path}: {e}")
                return None
            except PermissionError:
                logger.warning(f"Permission denied reading cache file: {path}")
                return None
            except Exception as e:
                logger.debug(f"Failed to read cache file {path}: {e}")
                return None
        return None

    def set(self, key: str, value: Dict[str, Any]):
        if not self._initialized:
            return
            
        path = self._get_path(key)
        try:
            with open(path, 'w') as f:
                json.dump(value, f, indent=2)
        except PermissionError:
            logger.warning(f"Permission denied writing to cache: {path}")
        except Exception as e:
            logger.debug(f"Failed to write cache file {path}: {e}")


def hash_claim(claim: str) -> str:
    """Generates a stable MD5 hash for a claim string."""
    return hashlib.md5(claim.strip().lower().encode('utf-8')).hexdigest()
