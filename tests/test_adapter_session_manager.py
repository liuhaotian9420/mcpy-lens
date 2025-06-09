"""
Unit tests for adapter session manager.
"""

import asyncio
import pytest
import time
from mcpy_lens.adapter.config import AdapterConfig
from mcpy_lens.adapter.session_manager import SessionManager, Session


class TestSession:
    """Test Session class."""
    
    def test_session_creation(self):
        """Test session creation."""
        session = Session(
            session_id="test-123",
            created_at=time.time(),
            last_activity=time.time()
        )
        
        assert session.session_id == "test-123"
        assert len(session.active_requests) == 0
        assert len(session.client_info) == 0
    
    def test_session_expiry(self):
        """Test session expiry logic."""
        current_time = time.time()
        session = Session(
            session_id="test-123",
            created_at=current_time - 100,
            last_activity=current_time - 100
        )
        
        # Should not be expired with 200 second timeout
        assert not session.is_expired(200)
        
        # Should be expired with 50 second timeout
        assert session.is_expired(50)
    
    def test_session_activity_update(self):
        """Test session activity update."""
        session = Session(
            session_id="test-123",
            created_at=time.time() - 100,
            last_activity=time.time() - 100
        )
        
        old_activity = session.last_activity
        time.sleep(0.01)  # Small delay
        session.update_activity()
        
        assert session.last_activity > old_activity
    
    def test_request_management(self):
        """Test request addition and removal."""
        session = Session(
            session_id="test-123",
            created_at=time.time(),
            last_activity=time.time()
        )
        
        # Add requests
        session.add_request("req-1")
        session.add_request("req-2")
        
        assert "req-1" in session.active_requests
        assert "req-2" in session.active_requests
        assert len(session.active_requests) == 2
        
        # Remove request
        session.remove_request("req-1")
        
        assert "req-1" not in session.active_requests
        assert "req-2" in session.active_requests
        assert len(session.active_requests) == 1
        
        # Remove non-existent request (should not error)
        session.remove_request("req-3")
        assert len(session.active_requests) == 1


class TestSessionManager:
    """Test SessionManager class."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AdapterConfig(
            max_sessions=5,
            session_timeout=60,
            session_cleanup_interval=1
        )
    
    @pytest.fixture
    def session_manager(self, config):
        """Create session manager."""
        return SessionManager(config)
    
    def test_create_session(self, session_manager):
        """Test session creation."""
        session_id = session_manager.create_session()
        
        assert session_id is not None
        assert len(session_id) > 0
        
        # Should be able to retrieve the session
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
    
    def test_create_session_with_client_info(self, session_manager):
        """Test session creation with client info."""
        client_info = {"user_agent": "test", "ip": "127.0.0.1"}
        session_id = session_manager.create_session(client_info)
        
        session = session_manager.get_session(session_id)
        assert session.client_info == client_info
    
    def test_session_limit(self, session_manager):
        """Test session limit enforcement."""
        # Create maximum number of sessions
        session_ids = []
        for i in range(session_manager.config.max_sessions):
            session_id = session_manager.create_session()
            session_ids.append(session_id)
        
        # Should not be able to create more sessions
        with pytest.raises(RuntimeError, match="Maximum number of sessions reached"):
            session_manager.create_session()
    
    def test_get_nonexistent_session(self, session_manager):
        """Test getting non-existent session."""
        session = session_manager.get_session("nonexistent")
        assert session is None
    
    def test_session_activity_update(self, session_manager):
        """Test session activity update."""
        session_id = session_manager.create_session()
        
        # Update activity
        result = session_manager.update_session_activity(session_id)
        assert result is True
        
        # Update non-existent session
        result = session_manager.update_session_activity("nonexistent")
        assert result is False
    
    def test_request_management(self, session_manager):
        """Test request management in sessions."""
        session_id = session_manager.create_session()
        
        # Add request
        result = session_manager.add_request_to_session(session_id, "req-1")
        assert result is True
        
        session = session_manager.get_session(session_id)
        assert "req-1" in session.active_requests
        
        # Remove request
        result = session_manager.remove_request_from_session(session_id, "req-1")
        assert result is True
        
        session = session_manager.get_session(session_id)
        assert "req-1" not in session.active_requests
    
    def test_session_stats(self, session_manager):
        """Test session statistics."""
        # Initially no sessions
        stats = session_manager.get_session_stats()
        assert stats["active_sessions"] == 0
        assert stats["total_active_requests"] == 0
        
        # Create sessions and add requests
        session_id1 = session_manager.create_session()
        session_id2 = session_manager.create_session()
        
        session_manager.add_request_to_session(session_id1, "req-1")
        session_manager.add_request_to_session(session_id1, "req-2")
        session_manager.add_request_to_session(session_id2, "req-3")
        
        stats = session_manager.get_session_stats()
        assert stats["active_sessions"] == 2
        assert stats["total_active_requests"] == 3
        assert stats["max_sessions"] == session_manager.config.max_sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_manager):
        """Test cleanup of expired sessions."""
        # Create session with very short timeout
        session_manager.config.session_timeout = 0.1
        
        session_id = session_manager.create_session()
        assert session_manager.get_session(session_id) is not None
        
        # Wait for expiry
        await asyncio.sleep(0.2)
        
        # Manual cleanup
        removed = session_manager._cleanup_expired_sessions()
        assert removed == 1
        
        # Session should be gone
        assert session_manager.get_session(session_id) is None
    
    @pytest.mark.asyncio
    async def test_start_stop(self, session_manager):
        """Test starting and stopping session manager."""
        await session_manager.start()
        assert session_manager._cleanup_task is not None
        
        await session_manager.stop()
        assert session_manager._cleanup_task.cancelled()
