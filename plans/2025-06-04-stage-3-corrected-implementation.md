# Stage 3: Tool Discovery Implementation - Corrected Plan

**Date**: 2025-06-04  
**Status**: In Progress (Revised)

## Description

Implement tool discovery mechanisms with the corrected understanding:
1. **Function Discovery**: Discover tools and generate metadata for MCP client identification
2. **Whole-File Execution**: Generate a single Typer-based CLI template for the entire Python file
3. **Entry Point Validation**: Enforce `if __name__ == "__main__"` requirement for executable mode

## Corrected Understanding

Based on user clarification, the implementation should work as follows:

### Example Script: add.py
```python
def add_two_numbers(a: int, b: int) -> int:
    """
    Some docstring here 
    """
    return a + b

if __name__ == "__main__":
    add_two_numbers(sys.argv[1], sys.argv[2])
```

### Two Operation Modes:

1. **Function Selection Mode**: 
   - Discover all functions in the file
   - Generate metadata for each function  
   - Allow user to select which functions to expose as MCP tools
   - Functions are used for MCP tool identification only

2. **Executable Script Mode**:
   - Validate script has `if __name__ == "__main__"` entry point
   - Generate ONE Typer CLI wrapper for the ENTIRE file
   - Allow user to define script-level parameters (e.g., `--arg1 abc --arg2 123`)
   - The wrapper handles the whole file execution, not individual functions

## Tasks (Revised Status)

### 3.1 Function Discovery Integration (mcpy-cli approach) ✅ COMPLETED
- [x] Integrate `discover_py_files()` function from mcpy-cli
- [x] Implement `discover_functions()` for extracting specific functions
- [x] Adapt discovery logic for single file processing
- [x] Generate JSON schema for discovered functions
- [x] Create function metadata with proper type annotations
- [x] Handle function dependencies and imports

### 3.2 Entry Point Validation ❌ NOT IMPLEMENTED
- [ ] Implement validation for `if __name__ == "__main__"` presence
- [ ] Create API endpoint to check if script is eligible for executable mode
- [ ] Add logic to restrict scripts without entry point to function-selection mode only
- [ ] Provide clear error messages when entry point is missing

### 3.3 Function Selection Interface ❌ NOT IMPLEMENTED  
- [ ] Create API for users to select which discovered functions to expose as tools
- [ ] Implement function selection storage and persistence
- [ ] Generate filtered metadata containing only selected functions
- [ ] Provide preview of selected tools for MCP integration

### 3.4 Whole-File CLI Wrapper Generation ❌ NOT IMPLEMENTED
- [ ] Implement dynamic Typer wrapper generation for ENTIRE Python file
- [ ] Generate ONE wrapper script that executes the whole file with parameters
- [ ] Create template that preserves original script execution behavior
- [ ] Handle script-level argument mapping and validation

### 3.5 Script-Level Parameter Definition ❌ NOT IMPLEMENTED
- [ ] Create API for defining script-level parameters (e.g., --arg1, --arg2)
- [ ] Implement parameter type specification and validation
- [ ] Generate Typer CLI interface with user-defined parameters
- [ ] Store parameter definitions for wrapper generation

### 3.6 Tool Schema Generation ✅ PARTIALLY COMPLETED
- [x] Create JSON Schema generator for Python functions
- [x] Implement MCP tool schema format compatibility
- [x] Generate input/output schemas automatically
- [x] Handle complex parameter types (objects, arrays)
- [x] Add validation rules and constraints
- [x] Support for optional and required parameters
- [ ] **MISSING**: Generate schema for script-level parameters in CLI wrapper mode

### 3.7 Metadata Persistence and Management ✅ COMPLETED
- [x] Design metadata storage structure
- [x] Implement CRUD operations for tool metadata
- [x] Version management for tool schemas
- [x] Handle metadata updates and migrations
- [x] Create metadata validation and integrity checks
- [x] Implement metadata backup and recovery

### 3.8 Integration with Existing Components ✅ COMPLETED
- [x] Adapt ValidFileTypes enum for single file processing
- [x] Modify module loading logic for uploaded scripts
- [x] Integrate with existing function discovery algorithms
- [x] Handle import resolution for uploaded scripts
- [x] Preserve file path information for routing
- [x] Add error handling for discovery failures

## New API Endpoints Required

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/v1/scripts/{script_id}/discover` | GET | Discover tools in a script | ✅ Exists |
| `/api/v1/scripts/{script_id}/validate_entry_point` | GET | Check if script has `if __name__ == "__main__"` | ❌ Missing |
| `/api/v1/scripts/{script_id}/functions/select` | POST | Select which functions to expose as tools | ❌ Missing |
| `/api/v1/scripts/{script_id}/functions/selected` | GET | Get selected functions list | ❌ Missing |
| `/api/v1/scripts/{script_id}/cli_params` | POST | Define script-level CLI parameters | ❌ Missing |
| `/api/v1/scripts/{script_id}/cli_params` | GET | Get script-level CLI parameters | ❌ Missing |
| `/api/v1/scripts/{script_id}/generate_cli_wrapper` | POST | Generate single CLI wrapper for entire file | ❌ Missing |

## Implementation Priority

### High Priority (Required for Stage 3 completion):
1. **Entry Point Validation** - Core requirement for executable mode
2. **Function Selection Interface** - Essential for tool management  
3. **Script-Level Parameter Definition** - Required for CLI wrapper
4. **Whole-File CLI Wrapper Generation** - Main feature for executable mode

### Medium Priority:
5. Schema generation for script-level parameters
6. Enhanced parameter validation and type conversion

## Updated Acceptance Criteria

- [x] Functions can be discovered from uploaded Python files
- [x] Tool schemas are generated correctly for discovered functions
- [ ] Scripts are validated for `if __name__ == "__main__"` entry point
- [ ] Scripts without entry point are restricted to function-selection mode
- [ ] Users can select which discovered functions to expose as MCP tools
- [ ] Script-level parameters can be defined through API
- [ ] ONE Typer wrapper is generated for the ENTIRE Python file in executable mode
- [ ] CLI wrapper preserves original script execution behavior
- [ ] Parameter definition workflow works end-to-end
- [x] Metadata is stored and retrieved correctly
- [x] Discovery works for both simple and complex Python scripts
- [x] Error handling covers all discovery failure scenarios

## Notes

- **Critical Correction**: Do not generate individual wrappers per function
- **Entry Point Requirement**: `if __name__ == "__main__"` is mandatory for executable mode
- **Function Selection**: Allow users to choose which functions become MCP tools
- **Single Wrapper**: Generate one CLI wrapper for the entire file, not per function
- **Parameter Mapping**: Script-level parameters should map to CLI arguments

## Next Steps

1. Implement entry point validation API
2. Create function selection interface
3. Design script-level parameter definition system
4. Implement whole-file CLI wrapper generation with Typer
5. Update existing endpoints to reflect corrected understanding

## Review

This plan correction addresses the misunderstanding in the original implementation. The focus shifts from per-function wrappers to:
1. Function discovery for MCP tool identification
2. Single wrapper generation for entire file execution
3. Entry point validation as a prerequisite for executable mode
4. User control over function selection and script parameters
