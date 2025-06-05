# Linting Issues in Tool Discovery Implementation

**Date**: 2025-06-04  
**Status**: ToDo

## Issues to Address

### 1. Exception Handling and Chaining

The current implementation has some issues with exception chaining. When catching exceptions and raising new ones, we should use `from` to preserve the original exception context.

#### Example:

```python
# Current implementation
try:
    # some code
except Exception as e:
    logger.error(f"Error: {e}")
    raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")

# Improved implementation with exception chaining
try:
    # some code
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Failed: {str(e)}") from e
```

### 2. Type Annotations

Some functions have incomplete or inconsistent type annotations. We should ensure all parameters and return values have proper type annotations.

#### Issues to fix:

- Use more specific types instead of `Dict[str, Any]` where possible
- Add type annotations for all return values
- Ensure consistent use of Union vs Optional in type hints
- Use proper typing for JSON schema types

### 3. Documentation

Some documentation issues need to be addressed:

- Add missing docstrings for some public methods
- Improve parameter descriptions in docstrings
- Update return value descriptions to match actual return types
- Add examples in docstrings for complex functions

### 4. Error Messages

Error messages should be more specific and helpful:

- Include more context in error messages (function name, parameter name, etc.)
- Use consistent error message format across all modules
- Add more specific error messages for different failure scenarios

### 5. Coding Style Issues

- Fix inconsistent indentation in some modules
- Remove unnecessary imports
- Fix overly long lines (>88 characters)
- Use consistent naming conventions for variables and functions
- Ensure consistent use of single vs double quotes

### 6. Test Coverage

While not strictly linting issues, we should add more tests:

- Add unit tests for schema generation with different parameter types
- Add tests for function discovery edge cases
- Add tests for error scenarios in wrapper generation
- Test with more complex real-world function signatures

## Priority List

1. Fix exception chaining in all error handling code
2. Address type annotation issues
3. Improve error messages for better user feedback
4. Update docstrings for better API documentation
5. Fix coding style issues
6. Add more tests for edge cases

## Implementation Plan

Create a separate PR for linting fixes only, to keep changes focused and easier to review. The changes should not alter functionality, only improve code quality.
