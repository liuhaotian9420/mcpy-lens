# Stage 4 Implementation Plan - Wrapper Layer

## 📋 Overview

Based on the Stage 4 plan review, I need to implement a wrapper layer that converts Python scripts into MCP-compatible tools using JSON-RPC protocol over STDIO. This involves creating wrappers that can execute both individual functions and entire scripts while maintaining proper communication protocols.

## 🎯 Implementation Strategy

### Phase 1: Core Infrastructure
1. **JSON-RPC Protocol Handler**
   - Implement JSON-RPC 2.0 compliant request/response handling
   - Add proper error codes and message formatting
   - Support for streaming responses with `partial: true`

2. **Base Wrapper Framework**
   - Create `WrapperBase` class with common functionality
   - Implement STDIO line-by-line processing
   - Add request ID tracking and correlation

### Phase 2: Execution Modes
1. **Function Wrapper**
   - Execute individual Python functions from uploaded scripts
   - Handle parameter validation and type conversion
   - Manage function imports and dependencies

2. **Executable Wrapper**
   - Execute entire scripts via subprocess
   - Handle command-line argument construction
   - Stream stdout/stderr output

### Phase 3: Advanced Features
1. **Resource Management**
   - Implement execution timeouts and limits
   - Add memory and CPU monitoring
   - Create process cleanup mechanisms

2. **Security & Sandboxing**
   - Restrict file system access
   - Control network access
   - Limit subprocess creation

## 🤔 Implementation Questions

To help me create the most effective implementation, I need your guidance on several key decisions:

### 1. **Wrapper Deployment Architecture**
**Question**: How should the generated wrappers be deployed and executed?

**Options**:
- A) **Standalone executables**: Each wrapper is a separate Python script that can be executed independently
- B) **Service-based**: All wrappers run through a central wrapper service/daemon
- C) **On-demand**: Wrappers are generated and executed only when needed

**Considerations**: 
- Standalone provides better isolation but more overhead
- Service-based allows better resource management but shared failure points
- On-demand reduces resource usage but has startup latency

**Answer**
- The focus here is for users who upload files can easily migrate to other platforms or even perform the wrapper process locally. So the warpper shou;ld be decoupled with our service


### 2. **Function Execution Isolation**
**Question**: How should individual Python functions be executed for security and reliability?

**Options**:
- A) **In-process**: Load and execute functions in the same Python process as the wrapper
- B) **Subprocess**: Execute each function call in a separate Python subprocess
- C) **Hybrid**: Use in-process for simple functions, subprocess for complex/risky ones

**Considerations**:
- In-process is faster but less secure and isolated
- Subprocess is safer but has higher overhead
- Hybrid provides flexibility but adds complexity

**Answer**
- Let's make it using subprocess
- Also it is worth noting that when users select multiple functions as tools, we can aggregate the tools together under a script, and then execute the script in a subprocess.
- Make sure you remember that each subprocess is only used for a script-level execution

### 3. **Streaming Implementation**
**Question**: What level of streaming granularity should we support?

**Options**:
- A) **Line-based**: Stream output line by line as it's produced
- B) **Chunk-based**: Buffer output and stream in reasonable chunks
- C) **Event-based**: Stream specific events/milestones during execution

**Considerations**:
- Line-based provides real-time feedback but may be noisy
- Chunk-based balances responsiveness with efficiency
- Event-based requires script cooperation but provides meaningful updates

**Answer**
- Line-based streaming

### 4. **Error Handling Strategy**
**Question**: How detailed should error reporting be, and what information should be exposed?

**Options**:
- A) **Full transparency**: Include full stack traces and system details
- B) **Sanitized details**: Provide useful debugging info but hide sensitive paths/data
- C) **Minimal reporting**: Only report high-level error categories

**Considerations**:
- Full transparency helps debugging but may expose sensitive information
- Sanitized details balance utility with security
- Minimal reporting is secure but may hinder troubleshooting

**Answer**
- I prefer the following two layers of logging:
1. Any issue pertained to the execution of the function or python script is fully logged (full transparency)
2. Any issue pertained to the wrapper itself is logged in a sanitized manner (sanitized details)

### 5. **Resource Limits Configuration**
**Question**: How should resource limits be configured and enforced?

**Options**:
- A) **Global defaults**: Same limits for all scripts/functions
- B) **Per-script configuration**: Allow custom limits per uploaded script
- C) **Dynamic scaling**: Adjust limits based on system load and script complexity

**Considerations**:
- Global defaults are simple but may be too restrictive or permissive
- Per-script configuration provides flexibility but requires user input
- Dynamic scaling is intelligent but complex to implement

**Answer**
- Global Limits

### 6. **Wrapper Generation Approach**
**Question**: How should wrapper code be generated and customized?

**Options**:
- A) **Template-based**: Use Jinja2 templates with script-specific data
- B) **Code generation**: Programmatically build wrapper classes
- C) **Configuration-driven**: Generic wrapper that reads script metadata at runtime

**Considerations**:
- Template-based is readable and customizable but may be harder to maintain
- Code generation provides full control but is more complex
- Configuration-driven is flexible but may have performance overhead

**Answer**
- In a reasonable process, users would have their tools discovered and metadata retrieved (look back to what you have done in Stage 3)
- Use the Configuration-driven method and utilize the tool discovery / metadata generation as the source of truth
- As a reminder, wrapper should also take consideration of handling tool calls from MCPclient

### 7. **Testing and Validation Strategy**
**Question**: What testing approach should we use for the wrapper implementation?

**Options**:
- A) **Unit tests only**: Test individual components in isolation
- B) **Integration tests**: Test full wrapper execution with real scripts
- C) **End-to-end tests**: Test complete MCP client-to-script communication

**Considerations**:
- Unit tests are fast but may miss integration issues
- Integration tests catch more issues but are slower
- End-to-end tests provide confidence but are complex to set up

**Answer**
- Unit tests only, add tests in tests/ directory

## 📝 Additional Considerations

### Performance Requirements
- What are the expected response times for function calls vs script execution?
- Right now for this non-production version, it does not matter

- How many concurrent wrapper processes should the system support?
- Let's say 4-8

- Are there specific memory or CPU constraints we need to consider?
- Currently no

### Compatibility Requirements
- Should wrappers work with existing MCP clients without modification?
- You can refer to MCP inspector as a standard for MCP clients. Context7 and Playwright are tools you can use to test against this MCP client

- Do we need to support any specific Python versions or dependencies?
- Python >=3.10
  
- Are there any specific operating system requirements or limitations?
- Please support at least Windows and Linux

### Monitoring and Observability
- What level of logging and monitoring should be built into the wrappers?
- Follow your instinct and best practice. But make it simple

- Should wrapper execution metrics be collected and reported?
- Not for now

- How should wrapper health and status be monitored?
- A separate service endpoint would be nice. But follow your instinct. 

## 🚀 Next Steps

Once you provide answers to these questions, I will:

1. **Refine the implementation plan** based on your preferences
2. **Create detailed technical specifications** for each component
3. **Implement the core wrapper framework** with your chosen architecture
4. **Build comprehensive tests** following your preferred testing strategy
5. **Document the implementation** with usage examples and best practices

Please provide your thoughts on these questions so I can tailor the implementation to your specific needs and preferences!
