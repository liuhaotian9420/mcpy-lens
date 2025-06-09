"""
Unit tests for adapter cache manager.
"""

import asyncio
import pytest
import time
from mcpy_lens.adapter.config import AdapterConfig
from mcpy_lens.adapter.cache_manager import CacheManager, CacheEntry


class TestCacheEntry:
    """Test CacheEntry class."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        current_time = time.time()
        entry = CacheEntry(
            key="test-key",
            value={"result": "test"},
            created_at=current_time,
            ttl=300
        )
        
        assert entry.key == "test-key"
        assert entry.value == {"result": "test"}
        assert entry.created_at == current_time
        assert entry.ttl == 300
        assert entry.access_count == 0
        assert entry.last_accessed == current_time
    
    def test_cache_entry_expiry(self):
        """Test cache entry expiry logic."""
        current_time = time.time()
        entry = CacheEntry(
            key="test-key",
            value="test-value",
            created_at=current_time - 100,
            ttl=50
        )
        
        # Should be expired
        assert entry.is_expired() is True
        
        # Create non-expired entry
        entry = CacheEntry(
            key="test-key",
            value="test-value",
            created_at=current_time,
            ttl=300
        )
        
        # Should not be expired
        assert entry.is_expired() is False
    
    def test_cache_entry_access(self):
        """Test cache entry access tracking."""
        entry = CacheEntry(
            key="test-key",
            value="test-value",
            created_at=time.time(),
            ttl=300
        )
        
        assert entry.access_count == 0
        
        # Access the entry
        value = entry.access()
        
        assert value == "test-value"
        assert entry.access_count == 1
        assert entry.last_accessed > entry.created_at


class TestCacheManager:
    """Test CacheManager class."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AdapterConfig(
            cache_enabled=True,
            cache_ttl=60,
            cache_max_size=5
        )
    
    @pytest.fixture
    def disabled_config(self):
        """Create test configuration with cache disabled."""
        return AdapterConfig(cache_enabled=False)
    
    @pytest.fixture
    def cache_manager(self, config):
        """Create cache manager."""
        return CacheManager(config)
    
    @pytest.fixture
    def disabled_cache_manager(self, disabled_config):
        """Create disabled cache manager."""
        return CacheManager(disabled_config)
    
    def test_put_and_get(self, cache_manager):
        """Test basic put and get operations."""
        # Put value
        cache_manager.put("key1", "value1")
        
        # Get value
        result = cache_manager.get("key1")
        assert result == "value1"
        
        # Get non-existent key
        result = cache_manager.get("nonexistent")
        assert result is None
    
    def test_disabled_cache(self, disabled_cache_manager):
        """Test cache when disabled."""
        # Put should do nothing
        disabled_cache_manager.put("key1", "value1")
        
        # Get should return None
        result = disabled_cache_manager.get("key1")
        assert result is None
    
    def test_cache_expiry(self, cache_manager):
        """Test cache entry expiry."""
        # Put with short TTL
        cache_manager.put("key1", "value1", ttl=0.1)
        
        # Should be available immediately
        result = cache_manager.get("key1")
        assert result == "value1"
        
        # Wait for expiry
        time.sleep(0.2)
        
        # Should be expired
        result = cache_manager.get("key1")
        assert result is None
    
    def test_cache_size_limit(self, cache_manager):
        """Test cache size limit enforcement."""
        # Fill cache to limit
        for i in range(cache_manager.config.cache_max_size):
            cache_manager.put(f"key{i}", f"value{i}")
        
        # All should be present
        for i in range(cache_manager.config.cache_max_size):
            assert cache_manager.get(f"key{i}") == f"value{i}"
        
        # Add one more (should evict oldest)
        cache_manager.put("new_key", "new_value")
        
        # New key should be present
        assert cache_manager.get("new_key") == "new_value"
        
        # Oldest key should be evicted
        assert cache_manager.get("key0") is None
    
    def test_generate_cache_key(self, cache_manager):
        """Test cache key generation."""
        # Same method and params should generate same key
        key1 = cache_manager.generate_cache_key("listtools", {})
        key2 = cache_manager.generate_cache_key("listtools", {})
        assert key1 == key2
        
        # Different methods should generate different keys
        key3 = cache_manager.generate_cache_key("calltool", {})
        assert key1 != key3
        
        # Different params should generate different keys
        key4 = cache_manager.generate_cache_key("listtools", {"param": "value"})
        assert key1 != key4
        
        # Same params in different order should generate same key
        key5 = cache_manager.generate_cache_key("test", {"a": 1, "b": 2})
        key6 = cache_manager.generate_cache_key("test", {"b": 2, "a": 1})
        assert key5 == key6
    
    def test_is_cacheable_request(self, cache_manager):
        """Test request cacheability determination."""
        # Cacheable methods
        assert cache_manager.is_cacheable_request({"method": "listtools"}) is True
        assert cache_manager.is_cacheable_request({"method": "gettoolinfo"}) is True
        assert cache_manager.is_cacheable_request({"method": "healthcheck"}) is True
        
        # Non-cacheable methods
        assert cache_manager.is_cacheable_request({"method": "calltool"}) is False
        assert cache_manager.is_cacheable_request({"method": "unknown"}) is False
        
        # Case insensitive
        assert cache_manager.is_cacheable_request({"method": "LISTTOOLS"}) is True
    
    def test_cache_stats(self, cache_manager):
        """Test cache statistics."""
        # Initial stats
        stats = cache_manager.get_cache_stats()
        assert stats["enabled"] is True
        assert stats["total_entries"] == 0
        assert stats["total_accesses"] == 0
        
        # Add some entries
        cache_manager.put("key1", "value1")
        cache_manager.put("key2", "value2")
        
        # Access entries
        cache_manager.get("key1")
        cache_manager.get("key1")
        cache_manager.get("key2")
        
        stats = cache_manager.get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["total_accesses"] == 3
        assert stats["max_size"] == cache_manager.config.cache_max_size
    
    def test_clear_cache(self, cache_manager):
        """Test cache clearing."""
        # Add entries
        cache_manager.put("key1", "value1")
        cache_manager.put("key2", "value2")
        
        # Verify entries exist
        assert cache_manager.get("key1") == "value1"
        assert cache_manager.get("key2") == "value2"
        
        # Clear cache
        cleared_count = cache_manager.clear()
        assert cleared_count == 2
        
        # Verify entries are gone
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_start_stop(self, cache_manager):
        """Test starting and stopping cache manager."""
        await cache_manager.start()
        assert cache_manager._cleanup_task is not None
        
        await cache_manager.stop()
        assert cache_manager._cleanup_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_disabled_start_stop(self, disabled_cache_manager):
        """Test starting and stopping disabled cache manager."""
        await disabled_cache_manager.start()
        assert disabled_cache_manager._cleanup_task is None
        
        await disabled_cache_manager.stop()
        # Should not error
