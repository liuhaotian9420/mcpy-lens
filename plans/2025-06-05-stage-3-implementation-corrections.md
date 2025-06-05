# Stage 3: Tool Discovery Implementation Corrections

**Date**: 2025-06-05  
**Status**: In Progress - Task Status Updated

## Description

This document outlines the corrections needed for the Stage 3 Tool Discovery implementation in mcpy-lens. The primary issue identified was a misunderstanding of how script-level tool wrappers should be generated. Instead of creating individual wrappers for each function, we should generate a single Typer CLI wrapper for an entire Python file when in executable mode.


















































































































































































































































































































- Wrapper Implementation: `/docs/inspirations/WRAPPER.md`- Inspiration: `/docs/inspirations/TOOL_REGISTER_FROM_FILE.md`- Original Plan: `/plans/2025-06-03-stage-3-tool-discovery.md`## References   - Testing and documentation   - Integration with existing components   - API endpoint implementation3. **Lower Priority (Days 4-5)**:   - Script-level parameter definition   - FileService class updates2. **Medium Priority (Days 2-3)**:   - Update of `generate_file_typer_wrapper` function   - Implementation of `validate_script_entry_point` function1. **High Priority (Immediate)**:## Timeline and Priority   - Test error handling for invalid scripts   - Validate parameter mapping correctness   - Validate entry point detection accuracy3. **Validation Tests**:   - Test CLI wrapper execution with different parameter types     - Upload script → Validate entry point → Define parameters → Generate wrapper   - End-to-end workflow test for both modes:2. **Integration Tests**:   - Test metadata generation and storage   - Test `generate_file_typer_wrapper` with different parameter configurations   - Test `validate_script_entry_point` with various Python files1. **Unit Tests**:## Testing Strategy- [ ] Maintain backward compatibility with existing code- [ ] Update metadata generation and storage to support both approaches- [ ] Ensure function discovery logic is compatible with both modes### 5. Integration with Existing mcpy-cli Components- [ ] Update `/api/v1/scripts/{script_id}/generate_wrapper` to use new wrapper generation logic- [ ] Add `/api/v1/scripts/{script_id}/select_functions` endpoint for function selection- [ ] Implement `/api/v1/scripts/{script_id}/define_params` for script-level parameters- [ ] Create `/api/v1/scripts/{script_id}/validate_main` endpoint### 4. API Endpoints Implementation```    return result            result["mode"] = "function"  # Fallback to function mode        result["error"] = "Script does not have a valid entry point (if __name__ == \"__main__\" block)"    if mode == "executable" and not validate_script_entry_point(script_path):    # For executable mode, also check entry point        self._store_script_metadata(script_id, result)    # Store processing results for later use        }        "functions": {name: schema for name, schema in function_schemas.items()},        "mode": mode,        "script_path": str(script_path),        "script_id": script_id,    result = {            function_schemas[name] = schema        schema = generate_schema_for_function(func)    for func, name, _ in functions:        function_schemas = {}    functions = discover_functions([script_path])    # Common - discover all functions for metadata        script_id = f"{script_path.stem}_{uuid.uuid4().hex[:8]}"    # Generate script ID                mode = "function"        else:            mode = "executable"        if has_entry_point:        has_entry_point = validate_script_entry_point(script_path)    if mode == "auto":    # Auto-detect mode if not specified                raise FileNotFoundError(f"Script file not found: {script_path}")    if not script_path.exists():    """        Dictionary with processing results    Returns:                mode: Processing mode - 'function' (individual functions), 'executable' (whole file), or 'auto' (detect)        script_path: Path to the uploaded script    Args:        Process an uploaded script based on the specified mode.    """def process_script(self, script_path: Path, mode: str = "auto") -> Dict[str, Any]:```python- [ ] Implement tool selection functionality- [ ] Add parameter definition storage for script-level parameters  2. Whole-file execution (for scripts with `if __name__ == "__main__"` blocks)  1. Function discovery (for metadata and individual function selection)- [ ] Update `process_script` method to support both modes:### 3. FileService Class Updates```    return wrapper_file        wrapper_file.chmod(wrapper_file.stat().st_mode | 0o755)    # Make executable                f.write("\n".join(wrapper_content))    with open(wrapper_file, "w", encoding="utf-8") as f:    # Write wrapper file        ])        "    app()",        "if __name__ == \"__main__\":",        "",        "",        "        sys.exit(1)",        "        print(json.dumps({\"error\": str(e)}), file=sys.stderr)",        "    except Exception as e:",        "        print(json.dumps({\"result\": process.stdout.strip()}, default=str))",        "        # Output the result as JSON",        "        ",        "            sys.exit(process.returncode)",        "            print(json.dumps({\"error\": process.stderr.strip()}), file=sys.stderr)",        "        if process.returncode != 0:",        "        # Check for errors",        "        ",        "        process = subprocess.run(cmd, capture_output=True, text=True, check=False)",        "        # Execute the script with provided arguments",        "    try:",        "",    wrapper_content.extend([    # Add execution code                wrapper_content.append(f"        cmd.extend([\"{arg_flag}\", str({arg_name})])")            wrapper_content.append(f"    if {arg_name} is not None:")        else:            wrapper_content.append(f"        cmd.append(\"{arg_flag}\")")            wrapper_content.append(f"    if {arg_name}:")        if arg_type == "boolean":                arg_type = arg.get("type", "string")        arg_flag = arg.get("flag", f"--{arg_name}")        arg_name = arg["name"]    for arg in script_args:    # Add argument mapping        ])        "    cmd = [sys.executable, str(script_path)]",        f"    script_path = Path(r\"{script_path}\")",        "    \"\"\"Run the wrapped script with provided arguments\"\"\"",        "):",    wrapper_content.extend([    # Close parameter list and add function body            wrapper_content.append(param_def)        param_def += ",",                        param_def += f" = typer.Option({default_value}, \"{arg_flag}\", help=\"{arg_help}\")"                default_value = f"\"{arg_default}\""            if arg_type == "string" and arg_default is not None:            default_value = "None" if arg_default is None else arg_default        else:            param_def += f" = typer.Option(..., \"{arg_flag}\", help=\"{arg_help}\")"        if arg_required:        # Add typer.Option annotation                param_def = f"    {arg_name}: {py_type}"        # Create parameter definition                        py_type = "str"  # Default        else:            py_type = "bool"        elif arg_type == "boolean":            py_type = "float"        elif arg_type == "number":            py_type = "int"        elif arg_type == "integer":            py_type = "str"        if arg_type == "string":        # Map Python types to Typer types                arg_default = arg.get("default")        arg_required = arg.get("required", False)        arg_help = arg.get("help", f"Parameter {arg_name}")        arg_flag = arg.get("flag", f"--{arg_name}")        arg_type = arg["type"]        arg_name = arg["name"]    for arg in script_args:    # Add script parameters to CLI definition        ]        "def main(",        "@app.command()",        "",        "app = typer.Typer()",        "",        "import typer",        "from pathlib import Path",        "import subprocess",        "import json",        "import sys",        "",        f"\"\"\"Typer CLI wrapper for {script_path.name}\"\"\"",        "#!/usr/bin/env python",    wrapper_content = [    # Create wrapper content        wrapper_file = output_dir / f"{script_id}_wrapper.py"    """        Path to the generated wrapper script    Returns:                script_args: List of script-level arguments to expose in the CLI        output_dir: Directory to save the wrapper        script_id: Unique identifier for the script        script_path: Path to the original Python script    Args:        Generate a Typer CLI wrapper for an entire Python script.    """) -> Path:    script_args: list[Dict[str, Any]]    output_dir: Path,    script_id: str,    script_path: Path,def generate_file_typer_wrapper(```python- [ ] Ensure the wrapper preserves the original script's execution behavior- [ ] Support capturing script-level command-line arguments- [ ] Create a new `generate_file_typer_wrapper` function to replace the current function-level wrapper### 2. Whole-File Typer Wrapper Generation```        return False    except SyntaxError:        return False                    return True                    test.comparators[0].value == "__main__"):                    isinstance(test.comparators[0], ast.Constant) and                     len(test.comparators) == 1 and                    len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq) and                    isinstance(test.left, ast.Name) and test.left.id == "__name__" and                if (isinstance(test, ast.Compare) and                 test = node.test                # Check if it's an if __name__ == "__main__" block            if isinstance(node, ast.If):            # Look for if statements at the module level        for node in tree.body:        tree = ast.parse(script_content)    try:    # Parse the Python code to AST            script_content = f.read()    with open(script_path, 'r', encoding='utf-8') as f:    """        True if the script has an entry point, False otherwise    Returns:                script_path: Path to the Python script    Args:        Validate if a Python script has an if __name__ == "__main__" block.    """def validate_script_entry_point(script_path: Path) -> bool:```python- [ ] Create an API endpoint for script validation- [ ] Add validation logic to FileService class for uploaded scripts- [ ] Implement `validate_script_entry_point` function to check for `if __name__ == "__main__"` block### 1. Script Entry Point Validation## Task Status Updates

Based on the corrected understanding of the Stage 3 implementation requirements, here is the current status of each task:

### Completed Tasks ✅
1. **Function Discovery Core Logic**: The basic function discovery in `discovery.py` works correctly
2. **Metadata Generation**: Function metadata generation and schema creation are implemented
3. **API Endpoints Foundation**: Basic endpoint structure exists in `file_routes.py`
4. **Wrapper Generator Foundation**: Basic wrapper generation logic exists but needs modification

### Incomplete Tasks ❌
The following tasks need to be completed based on the corrected understanding:

### 1. Script Entry Point Validation
- [ ] **INCOMPLETE**: Create `validate_script_entry_point` function to check for `if __name__ == "__main__"` block
- [ ] **INCOMPLETE**: Add API endpoint `/api/v1/scripts/{script_id}/validate_entry_point` 
- [ ] **INCOMPLETE**: Update script registration workflow to include validation
- [ ] **INCOMPLETE**: UI updates to show validation results

### 2. Whole-File Typer Wrapper Generation  
- [ ] **INCOMPLETE**: Modify `generate_file_typer_wrapper` function to generate ONE wrapper for entire file
- [ ] **INCOMPLETE**: Update wrapper to execute the whole script with `if __name__ == "__main__"` block
- [ ] **INCOMPLETE**: Handle script-level parameters in wrapper generation
- [ ] **INCOMPLETE**: Update API endpoint to use new wrapper generation logic

### 3. Function Selection Interface
- [ ] **INCOMPLETE**: Create API endpoint `/api/v1/scripts/{script_id}/functions/select` for user function selection
- [ ] **INCOMPLETE**: Implement metadata storage for selected functions
- [ ] **INCOMPLETE**: Update function discovery to respect user selections
- [ ] **INCOMPLETE**: UI components for function selection

### 4. Script-Level Parameter Configuration
- [ ] **INCOMPLETE**: API endpoint `/api/v1/scripts/{script_id}/cli_params` for script parameter definition  
- [ ] **INCOMPLETE**: Integration of script parameters with wrapper generation
- [ ] **INCOMPLETE**: UI for defining script-level CLI parameters
- [ ] **INCOMPLETE**: Parameter validation and type handling

### 5. Two-Mode Operation System
- [ ] **INCOMPLETE**: Implementation of mode detection (function vs executable)
- [ ] **INCOMPLETE**: Restriction of executable mode to scripts with entry points
- [ ] **INCOMPLETE**: Mode-specific workflow handling
- [ ] **INCOMPLETE**: API updates to support both operation modes

## Updated Priority and Timeline

Based on the corrected understanding, here are the updated priorities:

### 1. **Immediate Priority (Day 1)**:
   - [ ] **INCOMPLETE**: Implement `validate_script_entry_point` function 
   - [ ] **INCOMPLETE**: Add `/api/v1/scripts/{script_id}/validate_entry_point` endpoint
   - [ ] **INCOMPLETE**: Update `process_script` method to support mode detection

### 2. **High Priority (Day 2)**:  
   - [ ] **INCOMPLETE**: Modify `generate_file_typer_wrapper` for whole-file execution
   - [ ] **INCOMPLETE**: Update wrapper generation to handle entry points
   - [ ] **INCOMPLETE**: Implement two-mode operation system

### 3. **Medium Priority (Days 3-4)**:
   - [ ] **INCOMPLETE**: Implement function selection interface and API endpoint
   - [ ] **INCOMPLETE**: Add script-level parameter configuration
   - [ ] **INCOMPLETE**: Update FileService class with new methods

### 4. **Lower Priority (Day 5)**:
   - [ ] Testing and validation of corrected implementation
   - [ ] Documentation updates  
   - [ ] Integration testing with existing components

## Correction Tasks- Currently all functions are discovered and exposed   - Users need to be able to select which functions to expose as tools4. **No User Selection for Function Exposure**:   - Parameters should be defined for the whole script, not per function   - Current implementation doesn't support script-level parameter definition3. **No Script-Level Parameter Definition**:   - Scripts without this entry point should be restricted to function-selection mode only   - No validation for `if __name__ == "__main__"` entry point2. **Missing Script Validation**:   - This approach doesn't align with the intended design for executable scripts   - Current implementation in `discovery.py` creates individual wrappers for each function1. **Function-Level vs File-Level Wrapping**: ## Current Implementation Issues## Current vs Corrected Implementation

### Current Implementation
- Discovery functions correctly identify Python functions in uploaded scripts
- Metadata generation for individual functions works correctly
- The system generates individual wrappers for each function discovered
- There's no validation for `if __name__ == "__main__"` entry point
- Users cannot select which functions to expose as tools

### Corrected Implementation
- Continue to use existing function discovery logic
- Add validation for `if __name__ == "__main__"` entry point
- Generate a single Typer CLI wrapper for the entire Python file
- Allow users to select which functions to expose as tools
- Create script-level parameter configuration UI

## Tasks

### 1. Script Entry Point Validation
- [ ] Create a function to validate if a script has `if __name__ == "__main__"` block
- [ ] Add an API endpoint for validation: `/api/v1/scripts/{script_id}/validate_main`
- [ ] Update UI to show validation results and prevent executable mode for invalid scripts
- [ ] Add validation to the script registration workflow

### 2. Whole-File Wrapper Generation
- [ ] Create a new function to generate a single Typer CLI wrapper for the entire Python file
- [ ] Ensure wrapper preserves the original script execution behavior
- [ ] Update the wrapper generation API to support this mode
- [ ] Handle script dependencies and imports in the wrapper

### 3. Tool Selection UI Backend
- [ ] Create an API endpoint for selecting which functions to expose as tools
- [ ] Update metadata storage to reflect user selections
- [ ] Implement function filtering logic based on user selections
- [ ] Add validation to ensure selected functions meet requirements

### 4. Script-Level Parameter Configuration
- [ ] Implement parser to extract command-line parameters from the original script
- [ ] Create UI components for configuring script-level parameters
- [ ] Integrate parameter configuration with wrapper generation
- [ ] Handle different parameter types and validations

### 5. Integration with Existing Components
- [ ] Update `FileService` to implement new validation and wrapper generation
- [ ] Modify `discover_tools_from_file` to include entry point validation
- [ ] Update `register_script_as_tool_service` to use whole-file wrapper approach
- [ ] Ensure backward compatibility with existing API clients

## Example Implementation

### Entry Point Validation Function
```python
def validate_script_entry_point(script_path: Path) -> bool:
    """
    Validate if a Python script has an if __name__ == "__main__" block.
    
    Args:
        script_path: Path to the Python script
        
    Returns:
        True if the script has an if __name__ == "__main__" block, False otherwise
    """
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse the script and check for if __name__ == "__main__" block
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    left = node.test.left
                    if (isinstance(left, ast.Name) and left.id == "__name__" and
                            len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq)):
                        right = node.test.comparators[0]
                        if isinstance(right, ast.Str) and right.s == "__main__":
                            return True
        
        return False
    except Exception as e:
        logger.error(f"Error validating script entry point: {e}")
        return False
```

### Whole-File Wrapper Generation Function
```python
def generate_whole_file_wrapper(
    script_path: Path,
    selected_functions: list[str],
    script_params: Dict[str, Any],
    output_dir: Path
) -> Path:
    """
    Generate a Typer CLI wrapper for an entire Python file.
    
    Args:
        script_path: Path to the original Python script
        selected_functions: List of function names to expose as tools
        script_params: Script-level parameters configuration
        output_dir: Directory to save the wrapper
        
    Returns:
        Path to the generated wrapper script
    """
    # Implementation details...
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/scripts/{script_id}/validate_main` | GET | Check if script has valid entry point |
| `/api/v1/scripts/{script_id}/select_tools` | POST | Select which functions to expose as tools |
| `/api/v1/scripts/{script_id}/configure_params` | POST | Configure script-level parameters |
| `/api/v1/scripts/{script_id}/generate_wrapper` | POST | Generate whole-file wrapper |

## Dependencies

- Stage 3 core implementation (function discovery and metadata generation)
- Understanding of Typer CLI framework
- AST module for script parsing and analysis

## Notes

- This implementation focuses on correcting the wrapper generation approach
- Existing function discovery and metadata generation code should be preserved
- Integration with the overall MCP framework remains unchanged

## Summary of Status Update

**✅ What's Working:**
- Function discovery and metadata generation for individual functions
- Basic API endpoint structure exists
- Tool schema generation for discovered functions
- Basic wrapper generation foundation

**❌ What Needs Implementation:**
- Entry point validation for `if __name__ == "__main__"` blocks
- Function selection interface for MCP tool exposure
- Whole-file CLI wrapper generation (not per-function)
- Script-level parameter configuration
- Two-mode operation system (function vs executable)
- Missing API endpoints for new functionality

**🔄 Next Actions:**
1. Implement entry point validation as highest priority
2. Modify wrapper generation to handle whole files
3. Create function selection and parameter configuration interfaces
4. Update existing endpoints to support corrected workflow
5. Test end-to-end functionality with both operation modes
