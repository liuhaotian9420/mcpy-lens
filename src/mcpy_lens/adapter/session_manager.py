"""
Session management for MCP adapter.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from threading import RLock

from .config import AdapterConfig


@dataclass
class Session:
    """Represents an active session."""
    session_id: str
    created_at: float
    last_activity: float
    client_info: Dict[str, str] = field(default_factory=dict)
    active_requests: Set[str] = field(default_factory=set)
    
    def is_expired(self, timeout: int) -> bool:
        """Check if session has expired."""
        return time.time() - self.last_activity > timeout
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()
    
    def add_request(self, request_id: str) -> None:
        """Add an active request to this session."""
        self.active_requests.add(request_id)
        self.update_activity()
    
    def remove_request(self, request_id: str) -> None:
        """Remove a completed request from this session."""
        self.active_requests.discard(request_id)
        self.update_activity()


class SessionManager:
    """Manages sessions for request correlation."""
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._sessions: Dict[str, Session] = {}
        self._lock = RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the session manager."""
        self.logger.info("Starting session manager")
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self) -> None:
        """Stop the session manager."""
        self.logger.info("Stopping session manager")
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    def create_session(self, client_info: Optional[Dict[str, str]] = None) -> str:
        """Create a new session and return session ID."""
        session_id = str(uuid.uuid4())
        current_time = time.time()
        
        with self._lock:
            # Check session limit
            if len(self._sessions) >= self.config.max_sessions:
                # Remove oldest expired session
                self._cleanup_expired_sessions()
                if len(self._sessions) >= self.config.max_sessions:
                    raise RuntimeError("Maximum number of sessions reached")
            
            session = Session(
                session_id=session_id,
                created_at=current_time,
                last_activity=current_time,
                client_info=client_info or {}
            )
            self._sessions[session_id] = session
        
        self.logger.debug(f"Created session {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and not session.is_expired(self.config.session_timeout):
                return session
            elif session:
                # Session expired, remove it
                del self._sessions[session_id]
                self.logger.debug(f"Removed expired session {session_id}")
            return None
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update session activity timestamp."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.update_activity()
                return True
            return False
    
    def add_request_to_session(self, session_id: str, request_id: str) -> bool:
        """Add a request to a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and not session.is_expired(self.config.session_timeout):
                session.add_request(request_id)
                return True
            return False
    
    def remove_request_from_session(self, session_id: str, request_id: str) -> bool:
        """Remove a request from a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.remove_request(request_id)
                return True
            return False
    
    def get_session_stats(self) -> Dict[str, int]:
        """Get session statistics."""
        with self._lock:
            active_sessions = len(self._sessions)
            total_requests = sum(len(s.active_requests) for s in self._sessions.values())
            return {
                "active_sessions": active_sessions,
                "total_active_requests": total_requests,
                "max_sessions": self.config.max_sessions
            }
    
    def _cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions. Returns number of sessions removed."""
        current_time = time.time()
        expired_sessions = []
        
        with self._lock:
            for session_id, session in self._sessions.items():
                if session.is_expired(self.config.session_timeout):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._sessions[session_id]
        
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.config.session_cleanup_interval)
                self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in session cleanup loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
