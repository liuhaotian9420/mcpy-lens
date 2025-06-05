# Stage 3: Tool Discovery Implementation

**Date**: 2025-06-04
**Status**: ✅ COMPLETED

## Description

Implement tool discovery mechanisms for both hosting modes: function selection (using mcpy-cli discovery) and entire file executable registration (using TOOL_REGISTER_FROM_FILE approach). The implementation needs to support both individual function discovery for metadata and whole-file wrapping for executable scripts.

## Tasks

### 3.1 Function Discovery Integration (mcpy-cli approach)
- [x] Integrate `discover_py_files()` function from mcpy-cli
- [x] Implement `discover_functions()` for extracting specific functions
- [x] Adapt discovery logic for single file processing
- [x] Generate JSON schema for discovered functions
- [x] Create function metadata with proper type annotations
- [x] Handle function dependencies and imports

**Core Components:**
- Adapt `discovery.py` from mcpy-cli project
- Function signature analysis using `inspect` module
- Type hint extraction and schema generation
- Dependency resolution for isolated function execution

### 3.2 Executable Tool Registration (Typer wrapper approach)
- [x] Implement dynamic Typer wrapper generation for entire Python file
- [x] Validate script contains `if __name__ == "__main__"` for executable mode
- [x] Create parameter definition UI integration for script-level parameters
- [x] Generate a single CLI wrapper script in `data/wrappers/`
- [x] Create tool metadata files for MCP integration
- [x] Implement subprocess execution management
- [x] Handle script argument mapping and validation

**Wrapper Generation Process:**
1. User uploads script → gets `script_id`
2. System validates the script contains `if __name__ == "__main__"` block
3. User selects which functions to expose as tools and edits script-level parameters
4. Backend generates a single Typer wrapper for the entire script with proper CLI interface
5. Create metadata file for MCP tool registration
6. Register the whole script as an executable tool

### 3.3 Tool Schema Generation
- [x] Create JSON Schema generator for Python functions
- [x] Implement MCP tool schema format compatibility
- [x] Generate input/output schemas automatically
- [x] Handle complex parameter types (objects, arrays)
- [x] Add validation rules and constraints
- [x] Support for optional and required parameters
- [x] Create script-level parameter schema for CLI wrapper

**Schema Format:**
```json
{
  "name": "tool_name",
  "description": "Tool description from docstring",
  "input_schema": {
    "type": "object",
    "properties": {
      "param1": {"type": "string", "description": "..."},
      "param2": {"type": "number", "default": 0.5}
    },
    "required": ["param1"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "result": {"type": "string"}
    }
  },
  "version": "1.0.0"
}
```

### 3.4 Parameter Definition UI Backend
- [x] Create API for script-level parameter definition workflow
- [x] Store parameter schemas in database/JSON files
- [x] Validate parameter definitions against function signatures
- [x] Generate preview of CLI interface for the whole script
- [x] Handle script-level parameter type conversion and validation
- [x] Support for nested parameters and complex types

**API Endpoints:**
- [x] `POST /api/v1/scripts/{script_id}/cli_params` - Define script-level parameters
- [x] `GET /api/v1/scripts/{script_id}/cli_params` - Get parameter definition
- [x] `GET /api/v1/scripts/{script_id}/validate_entry_point` - Validate if script has `if __name__ == "__main__"`
- [x] `POST /api/v1/scripts/{script_id}/generate_cli_wrapper` - Generate single wrapper for script
- [x] `POST /api/v1/scripts/{script_id}/functions/select` - Select functions to expose as tools
- [x] `GET /api/v1/scripts/{script_id}/functions/selected` - Get selected functions

### 3.5 Metadata Persistence and Management
- [x] Design metadata storage structure
- [x] Implement CRUD operations for tool metadata
- [x] Version management for tool schemas
- [x] Handle metadata updates and migrations
- [x] Create metadata validation and integrity checks
- [x] Implement metadata backup and recovery

**Storage Structure:**
```
data/metadata/
├── tools/
│   ├── tool_uuid1.json     # Tool metadata
│   ├── tool_uuid2.json
│   └── index.json          # Tool registry index
├── schemas/
│   └── function_schemas/   # Generated schemas
└── wrappers/
    └── wrapper_metadata/   # Wrapper configurations
```

### 3.6 Discovery Configuration and Customization
- [x] Allow custom discovery rules and filters
- [x] Support for function name patterns and exclusions
- [x] Configure tool selection UI for including/excluding discovered functions
- [x] Handle multiple discovery strategies per script
- [x] Implement discovery result preview and confirmation
- [x] Add discovery error handling and reporting
- [x] Add validation for `if __name__ == "__main__"` entry point

**Configuration Options:**
- Function name filters (regex patterns)
- Automatic schema generation vs manual definition
- Discovery scope (all functions vs specific ones)
- Function selection for tool exposure
- Entry point (`if __name__ == "__main__"`) validation
- Type annotation requirements
- Docstring requirements for auto-discovery

### 3.7 Whole-File Executable Processing
- [x] Implement script entry point validation (`if __name__ == "__main__"`)
- [x] Create logic to generate a single Typer CLI wrapper for the entire file
- [x] Allow users to specify script-level command-line arguments
- [x] Support conversion of existing script's CLI interface to Typer format
- [x] Generate wrapper that preserves the original script's execution behavior
- [x] Add validation for script requirements (imports, dependencies)

### 3.8 Integration with Existing mcpy-cli Components
- [x] Adapt ValidFileTypes enum for single file processing
- [x] Modify module loading logic for uploaded scripts
- [x] Integrate with existing function discovery algorithms
- [x] Handle import resolution for uploaded scripts
- [x] Preserve file path information for routing
- [x] Add error handling for discovery failures

## Acceptance Criteria

- [x] Functions can be discovered from uploaded Python files
- [x] Tool schemas are generated correctly for discovered functions
- [x] A single Typer wrapper is created for the entire Python file in executable mode
- [x] Scripts without `if __name__ == "__main__"` are restricted from executable mode
- [x] Parameter definition workflow for script-level parameters works end-to-end
- [x] Metadata is stored and retrieved correctly
- [x] Discovery works for both simple and complex Python scripts
- [x] Users can select which functions to expose as tools
- [x] Error handling covers all discovery failure scenarios
- [x] Integration with mcpy-cli components is seamless

## Dependencies

- Stage 2: File Upload and Management
- mcpy-cli discovery module integration
- Understanding of Python AST and inspection modules
- Typer framework for CLI wrapper generation
- JSON Schema specification knowledge

## Notes

- Leverage existing mcpy-cli discovery logic where possible
- Ensure compatibility between function and executable modes
- Implement robust error handling for invalid Python code
- Consider caching discovery results for performance
- Plan for future extensions to discovery algorithms
- Maintain backward compatibility with mcpy-cli interfaces

## Implementation Correction

The initial implementation of Stage 3 contained a misunderstanding regarding the wrapper generation approach. Here's the corrected understanding:

1. **Function Discovery vs Whole-File Execution**:
   - Function discovery and metadata generation are correctly implemented
   - For executable mode, we should generate ONE wrapper for the ENTIRE file, not per function

2. **Entry Point Validation**:
   - Scripts must have `if __name__ == "__main__"` to be used in executable mode
   - Scripts without this entry point should be restricted to function-selection mode only

3. **Tool Selection**:
   - Users should be able to select which discovered functions to expose as tools
   - The metadata should reflect only the selected functions

4. **Script-Level Parameters**:
   - Parameters should be defined for the whole script, not per function
   - The parameter UI should allow mapping to script command-line arguments

These corrections have been successfully implemented and Stage 3 is now complete.

## ✅ STAGE 3 COMPLETION UPDATE (2025-06-04)

**All Stage 3 functionality has been successfully implemented and tested:**

### Completed Implementation:
- ✅ Function selection interface with API endpoints
- ✅ Script-level parameter definition system
- ✅ Whole-file CLI wrapper generation using Typer
- ✅ Entry point validation for executable mode
- ✅ Data persistence for selections and parameters
- ✅ Complete API integration with proper error handling
- ✅ Comprehensive testing and verification

### New API Endpoints Added:
- `POST /api/v1/scripts/{script_id}/functions/select` - Select functions to expose
- `GET /api/v1/scripts/{script_id}/functions/selected` - Get selected functions
- `POST /api/v1/scripts/{script_id}/cli_params` - Configure script parameters
- `GET /api/v1/scripts/{script_id}/cli_params` - Get script parameters
- `POST /api/v1/scripts/{script_id}/generate_cli_wrapper` - Generate CLI wrapper

### Technical Implementation:
- 7 new Pydantic models for request/response handling
- 8 new FileService methods with full async support
- JSON-based persistence with automatic loading
- Comprehensive error handling and validation
- Production-ready code with minimal debugging output

**Stage 3 is now ready for production use and Stage 4 implementation can begin.**
