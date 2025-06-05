# Stage 5: Adapter Implementation

**Date**: 2025-06-03  
**Status**: Planning

## Description

Implement the adapter layer that bridges HTTP requests to STDIO interfaces and converts responses to Server-Sent Events (SSE) for real-time streaming to web clients.

## Tasks

### 5.1 HTTP to STDIO Bridge
- [ ] Create FastAPI endpoint to accept JSON-RPC requests via HTTP POST
- [ ] Implement subprocess spawning for wrapper scripts
- [ ] Set up bidirectional communication (stdin/stdout) with wrappers
- [ ] Handle process lifecycle management (start, monitor, cleanup)
- [ ] Implement request queuing for concurrent access
- [ ] Add process pool management for performance optimization

**Core Components:**
```python
class STDIOAdapter:
    async def spawn_wrapper(self, wrapper_path: str) -> subprocess.Popen
    async def send_request(self, process: subprocess.Popen, request: dict) -> None
    async def read_response(self, process: subprocess.Popen) -> AsyncIterator[dict]
    async def cleanup_process(self, process: subprocess.Popen) -> None
```

### 5.2 Server-Sent Events (SSE) Implementation
- [ ] Implement SSE response streaming using FastAPI StreamingResponse
- [ ] Create proper SSE event formatting with data/event/id fields
- [ ] Handle connection management and client disconnection
- [ ] Implement heartbeat mechanism to keep connections alive
- [ ] Add error event streaming for client notification
- [ ] Support for multiple concurrent SSE connections

**SSE Event Format:**
```
data: {"jsonrpc": "2.0", "id": "123", "partial": true, "data": "progress update"}

data: {"jsonrpc": "2.0", "id": "123", "result": {"status": "completed"}}

event: error
data: {"jsonrpc": "2.0", "id": "123", "error": {"code": -32603, "message": "Internal error"}}
```

### 5.3 Async Process Management
- [ ] Implement async subprocess handling using asyncio
- [ ] Create process pool for reusing wrapper instances
- [ ] Add process health monitoring and automatic restart
- [ ] Implement graceful shutdown for all processes
- [ ] Handle process cleanup on client disconnection
- [ ] Add resource limits per process (memory, CPU, time)

**Process Pool Architecture:**
- Pre-spawned wrapper processes for common tools
- Dynamic scaling based on demand
- Process recycling after configurable number of requests
- Health checks and automatic replacement of failed processes
- Isolation between different user requests

### 5.4 Request/Response Correlation
- [ ] Implement request ID generation and tracking
- [ ] Correlate HTTP requests with subprocess responses
- [ ] Handle out-of-order responses from multiple processes
- [ ] Implement request timeout and cleanup
- [ ] Add request queueing and priority handling
- [ ] Track request metrics and performance data

**Correlation Mechanism:**
```python
class RequestTracker:
    def generate_request_id(self) -> str
    def track_request(self, request_id: str, client_info: dict) -> None
    def correlate_response(self, response: dict) -> Optional[str]
    def cleanup_expired_requests(self) -> None
```

### 5.5 Connection Management
- [ ] Handle WebSocket-like SSE connection state
- [ ] Implement client connection tracking and cleanup
- [ ] Add connection timeout and keep-alive mechanisms
- [ ] Handle client disconnection gracefully
- [ ] Implement connection limiting and rate limiting
- [ ] Add connection monitoring and metrics

**Connection Lifecycle:**
1. Client opens SSE connection to adapter endpoint
2. Adapter spawns or reuses wrapper process
3. Client sends JSON-RPC request via separate HTTP POST
4. Adapter forwards request to wrapper via stdin
5. Adapter streams wrapper stdout responses as SSE events
6. Connection closes when request completes or client disconnects

### 5.6 Error Handling and Recovery
- [ ] Handle wrapper process crashes and failures
- [ ] Implement automatic process restart and recovery
- [ ] Add error event streaming to notify clients
- [ ] Handle network interruptions and reconnection
- [ ] Implement circuit breaker pattern for failing services
- [ ] Add comprehensive logging and error reporting

**Error Scenarios:**
- Wrapper process crash during execution
- Client disconnection during streaming
- JSON parsing errors in wrapper output
- Network timeouts and interruptions
- Resource exhaustion (memory, CPU, processes)
- Invalid or malformed requests

### 5.7 Performance Optimization
- [ ] Implement response caching for deterministic requests
- [ ] Add compression for large response payloads
- [ ] Optimize JSON parsing and serialization
- [ ] Implement streaming with minimal memory footprint
- [ ] Add process pooling and connection reuse
- [ ] Monitor and optimize resource utilization

**Optimization Strategies:**
- Response streaming with chunked encoding
- JSON streaming parser for large responses
- Process pool warming and preallocation
- Intelligent caching based on request patterns
- Connection multiplexing where possible

### 5.8 API Endpoints Implementation
- [ ] Create `/api/v1/mcp/{service_id}` endpoint for JSON-RPC requests
- [ ] Implement `/api/v1/stream/{service_id}` for SSE connections
- [ ] Add `/api/v1/services/{service_id}/health` for health checks
- [ ] Create service discovery endpoints for available adapters
- [ ] Implement administrative endpoints for adapter management
- [ ] Add metrics and monitoring endpoints

**API Specification:**
```
POST /api/v1/mcp/{service_id}
Content-Type: application/json
Body: JSON-RPC request

GET /api/v1/stream/{service_id}
Accept: text/event-stream
Response: SSE stream of responses

GET /api/v1/services/{service_id}/health
Response: Service health status
```

## Acceptance Criteria

- [ ] HTTP requests are correctly forwarded to STDIO wrappers
- [ ] SSE streaming works reliably for all response types
- [ ] Multiple concurrent requests are handled properly
- [ ] Process management prevents resource leaks
- [ ] Error conditions are handled gracefully with proper client notification
- [ ] Performance meets requirements for expected load
- [ ] Connection management handles all edge cases
- [ ] API endpoints conform to specification

## Dependencies

- Stage 4: Wrapper Implementation
- FastAPI and asyncio expertise
- SSE protocol understanding
- Process management and resource control
- WebSocket/streaming connection knowledge

## Notes

- Follow ADAPTER.md guidelines for implementation details
- Ensure proper cleanup of all resources on shutdown
- Implement comprehensive logging for debugging
- Consider load balancing for high-traffic scenarios
- Plan for horizontal scaling across multiple servers
- Maintain compatibility with standard SSE clients
- Test thoroughly with various network conditions
