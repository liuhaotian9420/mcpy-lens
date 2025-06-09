"""
Simple TTL-based cache manager for MCP adapter.
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from threading import RLock

from .config import AdapterConfig


@dataclass
class CacheEntry:
    """Represents a cached response."""
    key: str
    value: Any
    created_at: float
    ttl: int
    access_count: int = 0
    last_accessed: float = 0
    
    def __post_init__(self):
        if self.last_accessed == 0:
            self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> Any:
        """Access the cached value and update statistics."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value


class CacheManager:
    """Simple TTL-based cache for deterministic function results."""
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the cache manager."""
        if self.config.cache_enabled:
            self.logger.info("Starting cache manager")
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        else:
            self.logger.info("Cache is disabled")
    
    async def stop(self) -> None:
        """Stop the cache manager."""
        self.logger.info("Stopping cache manager")
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        with self._lock:
            self._cache.clear()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if not self.config.cache_enabled:
            return None
            
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                self.logger.debug(f"Cache hit for key: {key[:32]}...")
                return entry.access()
            elif entry:
                # Entry expired, remove it
                del self._cache[key]
                self.logger.debug(f"Cache entry expired for key: {key[:32]}...")
            
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Put a value in cache."""
        if not self.config.cache_enabled:
            return
            
        cache_ttl = ttl or self.config.cache_ttl
        current_time = time.time()
        
        with self._lock:
            # Check cache size limit
            if len(self._cache) >= self.config.cache_max_size:
                self._evict_oldest()
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=current_time,
                ttl=cache_ttl
            )
            self._cache[key] = entry
            
        self.logger.debug(f"Cached value for key: {key[:32]}... (TTL: {cache_ttl}s)")
    
    def generate_cache_key(self, method: str, params: Dict[str, Any]) -> str:
        """Generate a cache key for a method call with parameters."""
        # Create a deterministic key based on method and sorted parameters
        key_data = {
            "method": method,
            "params": self._normalize_params(params)
        }
        key_json = json.dumps(key_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(key_json.encode()).hexdigest()
    
    def is_cacheable_request(self, request_data: Dict[str, Any]) -> bool:
        """Determine if a request is cacheable."""
        if not self.config.cache_enabled:
            return False
        
        # Only cache specific methods that are deterministic
        method = request_data.get("method", "").lower()
        
        # Cache list operations and read-only operations
        cacheable_methods = {
            "listtools",
            "gettoolinfo",
            "healthcheck"
        }
        
        if method in cacheable_methods:
            return True
        
        # For calltool, we could cache based on function metadata
        # but for now, we'll be conservative and not cache function calls
        # as they might have side effects
        
        return False
    
    def _normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameters for consistent cache keys."""
        if not params:
            return {}
        
        # Sort nested dictionaries and lists for consistency
        def normalize_value(value):
            if isinstance(value, dict):
                return {k: normalize_value(v) for k, v in sorted(value.items())}
            elif isinstance(value, list):
                return [normalize_value(item) for item in value]
            else:
                return value
        
        return normalize_value(params)
    
    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry to make room."""
        if not self._cache:
            return
        
        # Find the oldest entry by creation time
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        self.logger.debug(f"Evicted oldest cache entry: {oldest_key[:32]}...")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_entries = len(self._cache)
            total_accesses = sum(entry.access_count for entry in self._cache.values())
            
            if self._cache:
                avg_age = time.time() - sum(entry.created_at for entry in self._cache.values()) / total_entries
                oldest_entry = min(self._cache.values(), key=lambda e: e.created_at)
                newest_entry = max(self._cache.values(), key=lambda e: e.created_at)
            else:
                avg_age = 0
                oldest_entry = None
                newest_entry = None
            
            return {
                "enabled": self.config.cache_enabled,
                "total_entries": total_entries,
                "max_size": self.config.cache_max_size,
                "total_accesses": total_accesses,
                "average_age_seconds": avg_age,
                "oldest_entry_age": time.time() - oldest_entry.created_at if oldest_entry else 0,
                "newest_entry_age": time.time() - newest_entry.created_at if newest_entry else 0,
                "default_ttl": self.config.cache_ttl
            }
    
    def clear(self) -> int:
        """Clear all cache entries. Returns number of entries cleared."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"Cleared {count} cache entries")
            return count
    
    def _cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries. Returns number of entries removed."""
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Clean up every minute
                self._cleanup_expired_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cache cleanup loop: {e}")
                await asyncio.sleep(5)
