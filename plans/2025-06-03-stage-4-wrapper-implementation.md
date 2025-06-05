# Stage 4: Wrapper Implementation

**Date**: 2025-06-03
**Status**: ✅ COMPLETED

## Description

Implement the wrapper layer that converts non-standard Python scripts and executables into STDIO JSON interface, following the JSON-RPC protocol for MCP compatibility.

## Tasks

### 4.1 Core Wrapper Framework
- [x] Create base `WrapperBase` class with STDIO JSON interface
- [x] Implement JSON-RPC 2.0 protocol handling
- [x] Add line-by-line JSON input/output processing
- [x] Implement proper flush mechanisms for real-time streaming
- [x] Create error handling with standard JSON-RPC error codes
- [x] Add request ID tracking and response correlation

**Core Interface:**
```python
class WrapperBase:
    def process_request(self, json_line: str) -> str
    def handle_list_tools(self, request: dict) -> dict
    def handle_call_tool(self, request: dict) -> dict
    def format_response(self, result: Any, request_id: str) -> str
```

### 4.2 Function Wrapper Implementation
- [x] Create wrapper for individual Python functions
- [x] Implement function isolation and execution
- [x] Handle function imports and dependencies
- [x] Manage function parameter validation and conversion
- [x] Support for streaming function outputs
- [x] Add timeout and resource management

**Function Execution Process:**
1. Load target function from uploaded script
2. Validate and convert input parameters
3. Execute function in controlled environment
4. Capture output/results and format as JSON
5. Handle exceptions and error reporting
6. Stream partial results if function supports it

### 4.3 Executable Wrapper Implementation
- [x] Create wrapper for entire script execution
- [x] Implement subprocess management with Popen
- [x] Handle command-line argument construction
- [x] Capture stdout/stderr streams separately
- [x] Implement streaming output processing
- [x] Add process timeout and cleanup mechanisms

**Subprocess Handling:**
```python
class ExecutableWrapper(WrapperBase):
    def execute_script(self, script_path: str, args: list) -> AsyncIterator[dict]
    def stream_output(self, process: subprocess.Popen) -> AsyncIterator[str]
    def handle_process_completion(self, process: subprocess.Popen) -> dict
```

### 4.4 JSON-RPC Protocol Implementation
- [x] Implement standard JSON-RPC 2.0 request/response format
- [x] Add support for method dispatching (ListTools, CallTool)
- [x] Handle batch requests and responses
- [x] Implement proper error response formatting
- [x] Add request validation and sanitization
- [x] Support for notification requests (no response expected)

**Supported Methods:**
- `ListTools`: Return available tools and their schemas
- `CallTool`: Execute specific tool with parameters
- `GetToolInfo`: Get detailed information about a tool
- `HealthCheck`: Verify wrapper status

### 4.5 Streaming and Partial Results
- [x] Implement partial response streaming with `partial: true` flag
- [x] Add proper stream buffering and flushing
- [x] Handle incremental output from long-running processes
- [x] Implement stream completion signaling
- [x] Add progress reporting for long operations
- [x] Support for cancellation of streaming operations

**Streaming Protocol:**
```json
// Partial result
{"jsonrpc": "2.0", "id": "123", "partial": true, "data": "intermediate output"}
// Final result
{"jsonrpc": "2.0", "id": "123", "result": {"status": "completed", "output": "final result"}}
```

### 4.6 Error Handling and Recovery
- [x] Implement comprehensive error classification
- [x] Add proper JSON-RPC error codes and messages
- [x] Handle Python exceptions and system errors
- [x] Implement graceful degradation for resource issues
- [x] Add logging and debugging capabilities
- [x] Create error recovery and retry mechanisms

**Error Types:**
- Parse errors (-32700): Invalid JSON input
- Invalid request (-32600): Malformed JSON-RPC
- Method not found (-32601): Unknown method
- Invalid params (-32602): Parameter validation errors
- Internal error (-32603): Execution failures
- Custom errors (-32000 to -32099): Application-specific errors

### 4.7 Resource Management and Security
- [x] Implement execution timeouts and limits
- [x] Add memory usage monitoring and limits
- [x] Create sandboxed execution environment
- [x] Implement file system access restrictions
- [x] Add network access controls
- [x] Monitor and limit subprocess creation

**Security Measures:**
- Restricted imports and module access
- File system sandboxing
- Network isolation options
- Resource usage limits (CPU, memory, time)
- Process isolation and cleanup
- Input sanitization and validation

### 4.8 Wrapper Generation and Deployment
- [x] Create wrapper generator from tool metadata
- [x] Implement wrapper template system
- [x] Add wrapper deployment and registration
- [x] Create wrapper lifecycle management
- [x] Implement wrapper updates and versioning
- [x] Add wrapper health monitoring

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

- [x] Wrappers handle JSON-RPC protocol correctly
- [x] Both function and executable modes work properly
- [x] Streaming output functions as expected
- [x] Error handling covers all failure scenarios
- [x] Resource limits prevent system abuse
- [x] Wrapper generation produces working code
- [x] All wrapper operations are thread-safe
- [x] Performance meets requirements for typical workloads

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
