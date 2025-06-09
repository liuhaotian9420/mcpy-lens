"""
Integration tests for Stage 5 adapter implementation.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpy_lens.adapter.config import AdapterConfig
from mcpy_lens.adapter.session_manager import SessionManager
from mcpy_lens.adapter.cache_manager import CacheManager
from mcpy_lens.adapter.adapter_service import AdapterService


def test_adapter_config():
    """Test adapter configuration."""
    print("🔧 Testing adapter configuration...")
    
    try:
        # Test default configuration
        config = AdapterConfig()
        assert config.max_concurrent_requests == 4
        assert config.cache_enabled is True
        assert config.validate() is True
        
        # Test environment configuration
        config = AdapterConfig.from_env()
        assert config.validate() is True
        
        print("✅ Adapter configuration working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Adapter configuration test failed: {e}")
        return False


def test_session_manager():
    """Test session manager."""
    print("\n👥 Testing session manager...")
    
    try:
        config = AdapterConfig(max_sessions=5, session_timeout=60)
        session_manager = SessionManager(config)
        
        # Create session
        session_id = session_manager.create_session({"user": "test"})
        assert session_id is not None
        
        # Get session
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.client_info["user"] == "test"
        
        # Add request to session
        result = session_manager.add_request_to_session(session_id, "req-1")
        assert result is True
        
        # Get stats
        stats = session_manager.get_session_stats()
        assert stats["active_sessions"] == 1
        assert stats["total_active_requests"] == 1
        
        print("✅ Session manager working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Session manager test failed: {e}")
        return False


def test_cache_manager():
    """Test cache manager."""
    print("\n💾 Testing cache manager...")
    
    try:
        config = AdapterConfig(cache_enabled=True, cache_ttl=60, cache_max_size=10)
        cache_manager = CacheManager(config)
        
        # Test caching
        cache_manager.put("test-key", {"result": "test-value"})
        result = cache_manager.get("test-key")
        assert result == {"result": "test-value"}
        
        # Test cache key generation
        key1 = cache_manager.generate_cache_key("listtools", {})
        key2 = cache_manager.generate_cache_key("listtools", {})
        assert key1 == key2
        
        # Test cacheable request detection
        assert cache_manager.is_cacheable_request({"method": "listtools"}) is True
        assert cache_manager.is_cacheable_request({"method": "calltool"}) is False
        
        # Test stats
        stats = cache_manager.get_cache_stats()
        assert stats["enabled"] is True
        assert stats["total_entries"] == 1
        
        print("✅ Cache manager working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Cache manager test failed: {e}")
        return False


async def test_adapter_service():
    """Test adapter service."""
    print("\n🔄 Testing adapter service...")
    
    try:
        config = AdapterConfig(max_concurrent_requests=2)
        adapter_service = AdapterService(config)
        
        # Start service
        await adapter_service.start()
        
        # Create session
        session_id = adapter_service.create_session()
        assert session_id is not None
        
        # Test health status
        health = adapter_service.get_health_status()
        assert health["status"] == "healthy"
        assert "components" in health
        assert "config" in health
        
        # Test request validation
        valid_request = {
            "jsonrpc": "2.0",
            "method": "listtools",
            "id": "test-123"
        }
        error = adapter_service.validate_request(valid_request)
        assert error is None
        
        invalid_request = {"method": "test"}  # Missing jsonrpc
        error = adapter_service.validate_request(invalid_request)
        assert error is not None
        assert error["code"] == -32600
        
        # Stop service
        await adapter_service.stop()
        
        print("✅ Adapter service working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Adapter service test failed: {e}")
        return False


def test_sse_handler():
    """Test SSE handler."""
    print("\n📡 Testing SSE handler...")
    
    try:
        from mcpy_lens.adapter.sse_handler import SSEHandler, SSEEvent
        
        config = AdapterConfig()
        sse_handler = SSEHandler(config)
        
        # Test SSE event formatting
        event = SSEEvent(
            data='{"test": "data"}',
            event="test",
            id="123"
        )
        
        formatted = event.format()
        assert "id: 123" in formatted
        assert "event: test" in formatted
        assert 'data: {"test": "data"}' in formatted
        
        # Test headers
        headers = SSEHandler.get_sse_headers()
        assert headers["Content-Type"] == "text/event-stream"
        assert headers["Cache-Control"] == "no-cache"
        
        print("✅ SSE handler working correctly")
        return True
        
    except Exception as e:
        print(f"❌ SSE handler test failed: {e}")
        return False


async def run_async_tests():
    """Run async tests."""
    return await test_adapter_service()


def main():
    """Run all Stage 5 adapter tests."""
    print("🚀 Stage 5 Adapter Implementation Tests")
    print("=" * 50)
    
    tests = [
        test_adapter_config,
        test_session_manager,
        test_cache_manager,
        test_sse_handler,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Run async tests
    async_result = asyncio.run(run_async_tests())
    results.append(async_result)
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Stage 5 adapter implementation tests passed!")
        print("\n✨ Stage 5 core functionality is working!")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == "__main__":
    main()
