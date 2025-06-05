# Stage 4: Wrapper Implementation

**Date**: 2025-06-03  
**Status**: Planning

## Description

Implement the wrapper layer that converts non-standard Python scripts and executables into STDIO JSON interface, following the JSON-RPC protocol for MCP compatibility.

## Tasks

### 4.1 Core Wrapper Framework
- [ ] Create base `WrapperBase` class with STDIO JSON interface
- [ ] Implement JSON-RPC 2.0 protocol handling
- [ ] Add line-by-line JSON input/output processing
- [ ] Implement proper flush mechanisms for real-time streaming
- [ ] Create error handling with standard JSON-RPC error codes
- [ ] Add request ID tracking and response correlation

**Core Interface:**
```python
class WrapperBase:
    def process_request(self, json_line: str) -> str
    def handle_list_tools(self, request: dict) -> dict
    def handle_call_tool(self, request: dict) -> dict
    def format_response(self, result: Any, request_id: str) -> str
```

### 4.2 Function Wrapper Implementation
- [ ] Create wrapper for individual Python functions
- [ ] Implement function isolation and execution
- [ ] Handle function imports and dependencies
- [ ] Manage function parameter validation and conversion
- [ ] Support for streaming function outputs
- [ ] Add timeout and resource management

**Function Execution Process:**
1. Load target function from uploaded script
2. Validate and convert input parameters
3. Execute function in controlled environment
4. Capture output/results and format as JSON
5. Handle exceptions and error reporting
6. Stream partial results if function supports it

### 4.3 Executable Wrapper Implementation
- [ ] Create wrapper for entire script execution
- [ ] Implement subprocess management with Popen
- [ ] Handle command-line argument construction
- [ ] Capture stdout/stderr streams separately
- [ ] Implement streaming output processing
- [ ] Add process timeout and cleanup mechanisms

**Subprocess Handling:**
```python
class ExecutableWrapper(WrapperBase):
    def execute_script(self, script_path: str, args: list) -> AsyncIterator[dict]
    def stream_output(self, process: subprocess.Popen) -> AsyncIterator[str]
    def handle_process_completion(self, process: subprocess.Popen) -> dict
```

### 4.4 JSON-RPC Protocol Implementation
- [ ] Implement standard JSON-RPC 2.0 request/response format
- [ ] Add support for method dispatching (ListTools, CallTool)
- [ ] Handle batch requests and responses
- [ ] Implement proper error response formatting
- [ ] Add request validation and sanitization
- [ ] Support for notification requests (no response expected)

**Supported Methods:**
- `ListTools`: Return available tools and their schemas
- `CallTool`: Execute specific tool with parameters
- `GetToolInfo`: Get detailed information about a tool
- `HealthCheck`: Verify wrapper status

### 4.5 Streaming and Partial Results
- [ ] Implement partial response streaming with `partial: true` flag
- [ ] Add proper stream buffering and flushing
- [ ] Handle incremental output from long-running processes
- [ ] Implement stream completion signaling
- [ ] Add progress reporting for long operations
- [ ] Support for cancellation of streaming operations

**Streaming Protocol:**
```json
// Partial result
{"jsonrpc": "2.0", "id": "123", "partial": true, "data": "intermediate output"}
// Final result
{"jsonrpc": "2.0", "id": "123", "result": {"status": "completed", "output": "final result"}}
```

### 4.6 Error Handling and Recovery
- [ ] Implement comprehensive error classification
- [ ] Add proper JSON-RPC error codes and messages
- [ ] Handle Python exceptions and system errors
- [ ] Implement graceful degradation for resource issues
- [ ] Add logging and debugging capabilities
- [ ] Create error recovery and retry mechanisms

**Error Types:**
- Parse errors (-32700): Invalid JSON input
- Invalid request (-32600): Malformed JSON-RPC
- Method not found (-32601): Unknown method
- Invalid params (-32602): Parameter validation errors
- Internal error (-32603): Execution failures
- Custom errors (-32000 to -32099): Application-specific errors

### 4.7 Resource Management and Security
- [ ] Implement execution timeouts and limits
- [ ] Add memory usage monitoring and limits
- [ ] Create sandboxed execution environment
- [ ] Implement file system access restrictions
- [ ] Add network access controls
- [ ] Monitor and limit subprocess creation

**Security Measures:**
- Restricted imports and module access
- File system sandboxing
- Network isolation options
- Resource usage limits (CPU, memory, time)
- Process isolation and cleanup
- Input sanitization and validation

### 4.8 Wrapper Generation and Deployment
- [ ] Create wrapper generator from tool metadata
- [ ] Implement wrapper template system
- [ ] Add wrapper deployment and registration
- [ ] Create wrapper lifecycle management
- [ ] Implement wrapper updates and versioning
- [ ] Add wrapper health monitoring

**Generated Wrapper Structure:**
```python
#!/usr/bin/env python3
# Auto-generated wrapper for script_id: {uuid}
import sys
from mcpy_lens.wrapper import WrapperBase

class GeneratedWrapper(WrapperBase):
    def __init__(self):
        super().__init__()
        self.script_path = "{script_path}"
        self.tool_metadata = {tool_metadata}
    
    # Generated methods based on hosting mode
```

## Acceptance Criteria

- [ ] Wrappers handle JSON-RPC protocol correctly
- [ ] Both function and executable modes work properly
- [ ] Streaming output functions as expected
- [ ] Error handling covers all failure scenarios
- [ ] Resource limits prevent system abuse
- [ ] Wrapper generation produces working code
- [ ] All wrapper operations are thread-safe
- [ ] Performance meets requirements for typical workloads

## Dependencies

- Stage 3: Tool Discovery Implementation
- JSON-RPC 2.0 specification understanding
- Python subprocess and asyncio knowledge
- Security and sandboxing considerations
- Process management and resource control

## Notes

- Follow WRAPPER.md guidelines for implementation details
- Ensure compatibility with both Windows and Unix systems
- Implement proper cleanup to prevent resource leaks
- Consider using virtual environments for script isolation
- Plan for horizontal scaling of wrapper processes
- Maintain backward compatibility with existing MCP clients
