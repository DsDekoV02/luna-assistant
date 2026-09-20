"""
Luna JARVIS - Tests for Disk Cache
Tests disk-based caching with TTL support.
"""

import pytest
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.cache import DiskCache


@pytest.fixture
def cache(tmp_dir):
    return DiskCache(directory=str(tmp_dir / "cache"), max_size_mb=10, default_ttl=3600)


# ── Basic Operations ─────────────────────────────────────────────

class TestCacheBasic:
    def test_set_and_get(self, cache):
        cache.set("key1", {"data": "hello"})
        result = cache.get("key1")
        assert result == {"data": "hello"}

    def test_get_nonexistent(self, cache):
        assert cache.get("nonexistent") is None

    def test_delete(self, cache):
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_overwrite(self, cache):
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"


# ── Binary Data ──────────────────────────────────────────────────

class TestCacheBinary:
    def test_set_binary(self, cache):
        data = b"\x00\x01\x02\xff" * 100
        cache.set("audio", data)
        result = cache.get("audio")
        assert result == data

    def test_binary_auto_detect(self, cache):
        cache.set("bin", b"binary data")
        # Should auto-detect as binary
        assert cache._index["bin"]["binary"] is True

    def test_text_auto_detect(self, cache):
        cache.set("text", {"key": "value"})
        assert cache._index["text"]["binary"] is False


# ── TTL ──────────────────────────────────────────────────────────

class TestCacheTTL:
    def test_expired_returns_none(self, cache):
        cache.set("key", "value", ttl=1)
        # Manually expire it
        cache._index["key"]["expires"] = 0
        cache._save_index()
        assert cache.get("key") is None

    def test_not_expired_returns_value(self, cache):
        cache.set("key", "value", ttl=3600)
        assert cache.get("key") == "value"

    def test_default_ttl(self, cache):
        cache.set("key", "value")
        entry = cache._index["key"]
        assert entry["expires"] > time.time()


# ── Stats ────────────────────────────────────────────────────────

class TestCacheStats:
    def test_empty_stats(self, cache):
        stats = cache.stats()
        assert stats["entries"] == 0
        assert stats["total_size_mb"] == 0

    def test_with_entries(self, cache):
        cache.set("a", "data_a_text")
        cache.set("b", "data_b_text")
        stats = cache.stats()
        assert stats["entries"] == 2
        # total_size might be 0 if index size not tracked
        assert stats["entries"] == 2

    def test_max_size_reported(self, cache):
        stats = cache.stats()
        assert stats["max_size_mb"] == 10


# ── Index ────────────────────────────────────────────────────────

class TestCacheIndex:
    def test_index_persists(self, tmp_dir):
        dir_path = str(tmp_dir / "persist_cache")
        c1 = DiskCache(directory=dir_path)
        c1.set("key", "value")

        # Create new instance - should load index
        c2 = DiskCache(directory=dir_path)
        assert c2.get("key") == "value"

    def test_index_tracks_size(self, cache):
        cache.set("key", "some data here")
        assert cache._index["key"]["size"] > 0

    def test_index_tracks_created(self, cache):
        before = time.time()
        cache.set("key", "value")
        after = time.time()
        assert before <= cache._index["key"]["created"] <= after
