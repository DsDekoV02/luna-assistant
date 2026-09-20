"""
Luna JARVIS - Cache Module
Disk-based response caching for fast replies.
"""

import os
import json
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger("luna.memory.cache")


class DiskCache:
    """Simple disk-based cache with TTL support."""

    def __init__(self, directory: str = "./cache", max_size_mb: int = 500, default_ttl: int = 3600):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self._index = self._load_index()

    def _load_index(self) -> dict:
        """Load the cache index."""
        index_path = self.directory / "index.json"
        if index_path.exists():
            try:
                with open(index_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_index(self):
        """Save the cache index."""
        index_path = self.directory / "index.json"
        with open(index_path, "w") as f:
            json.dump(self._index, f)

    def _key_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.directory / f"{safe_key}.cache"

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache. Returns None if not found or expired."""
        if key not in self._index:
            return None

        entry = self._index[key]
        if time.time() > entry.get("expires", 0):
            self.delete(key)
            return None

        path = self._key_path(key)
        if not path.exists():
            del self._index[key]
            self._save_index()
            return None

        try:
            # Check if it's binary (audio) or text
            if entry.get("binary"):
                with open(path, "rb") as f:
                    return f.read()
            else:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None, binary: Optional[bool] = None):
        """Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache (bytes auto-detected as binary)
            ttl: Time to live in seconds (None = default)
            binary: Force binary mode. If None, auto-detects from value type.
        """
        ttl = ttl or self.default_ttl
        path = self._key_path(key)

        # Auto-detect binary if not specified
        if binary is None:
            binary = isinstance(value, bytes)

        try:
            if binary:
                with open(path, "wb") as f:
                    f.write(value)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(value, f, ensure_ascii=False)

            self._index[key] = {
                "expires": time.time() + ttl,
                "binary": binary,
                "size": path.stat().st_size,
                "created": time.time()
            }
            self._save_index()
            self._cleanup()
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    def delete(self, key: str):
        """Delete a cache entry."""
        path = self._key_path(key)
        if path.exists():
            path.unlink()
        if key in self._index:
            del self._index[key]
            self._save_index()

    def clear(self):
        """Clear all cache."""
        for file in self.directory.glob("*.cache"):
            file.unlink()
        self._index.clear()
        self._save_index()
        logger.info("Cache cleared")

    def _cleanup(self):
        """Remove expired entries and enforce size limit."""
        now = time.time()

        # Remove expired
        expired = [k for k, v in self._index.items() if now > v.get("expires", 0)]
        for key in expired:
            self.delete(key)

        # Enforce size limit
        total_size = sum(v.get("size", 0) for v in self._index.values())
        if total_size > self.max_size_bytes:
            # Remove oldest entries
            sorted_entries = sorted(
                self._index.items(),
                key=lambda x: x[1].get("created", 0)
            )
            while total_size > self.max_size_bytes * 0.8 and sorted_entries:
                key, entry = sorted_entries.pop(0)
                total_size -= entry.get("size", 0)
                self.delete(key)

    def stats(self) -> dict:
        """Get cache statistics."""
        total_size = sum(v.get("size", 0) for v in self._index.values())
        return {
            "entries": len(self._index),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
            "usage_percent": round(total_size / self.max_size_bytes * 100, 2)
        }


# Singleton
_cache: Optional[DiskCache] = None


def get_cache(directory: str = "./cache", max_size_mb: int = 500, default_ttl: int = 3600) -> DiskCache:
    """Get the singleton cache instance."""
    global _cache
    if _cache is None:
        _cache = DiskCache(directory, max_size_mb, default_ttl)
    return _cache
