# Stage 2: File Upload and Management

**Date**: 2025-06-03  
**Status**: In Progress  
**Last Updated**: 2025-06-03 18:30

## Description

Implement file upload functionality, storage management, and basic validation for Python files that will be registered as MCP services.

## Tasks

### 2.1 File Upload API Endpoints
- [x] Create `/upload_script` POST endpoint for file uploads
- [x] Implement file validation (Python files only, size limits)
- [x] Generate unique script IDs using UUID
- [x] Store uploaded files in `data/uploaded_scripts/` directory
- [x] Return script metadata including ID, filename, and storage path
- [ ] Add file overwrite protection and versioning

**API Specification:**
```
POST /api/v1/upload_script
Content-Type: multipart/form-data
Body: file (Python script)
Response: {
  "script_id": "uuid",
  "filename": "original_name.py",
  "size": 1234,
  "upload_time": "2025-06-03T10:00:00Z"
}
```

### 2.2 File Storage and Organization
- [x] Implement secure file naming (sanitize filenames)
- [x] Create subdirectories based on upload date or user
- [x] Store original filename metadata separately
- [ ] Implement file deduplication using content hashing
- [ ] Add file compression for large scripts
- [ ] Create backup and recovery mechanisms

**Storage Structure:**
```
data/uploaded_scripts/
├── 2025-06-03/
│   ├── script_uuid1.py
│   ├── script_uuid2.py
│   └── metadata.json
└── archive/
    └── older_scripts/
```

### 2.3 Python File Validation
- [x] Syntax validation using `ast.parse()`
- [x] Security scanning for dangerous imports/operations
- [ ] Check for required function signatures (if applicable)
- [ ] Validate import dependencies availability
- [x] Size and complexity limits
- [ ] Malware scanning integration (basic)

**Validation Rules:**
- File size: max 10MB
- Syntax: must be valid Python
- Imports: whitelist of allowed modules
- Functions: must have proper docstrings for auto-discovery
- Security: no file system access, network operations without approval

### 2.4 Script Metadata Extraction
- [x] Extract functions and their signatures using `ast` module
- [x] Parse docstrings for function descriptions
- [x] Identify function parameters and types
- [x] Extract imports and dependencies
- [x] Generate initial tool schemas
- [x] Store metadata in JSON format

**Metadata Schema:**
```json
{
  "script_id": "uuid",
  "filename": "script.py",
  "functions": [
    {
      "name": "function_name",
      "description": "extracted from docstring",
      "parameters": [...],
      "return_type": "...",
      "line_number": 42
    }
  ],
  "imports": ["module1", "module2"],
  "dependencies": ["package1==1.0.0"]
}
```

### 2.5 File Management API
- [x] List uploaded scripts endpoint
- [x] Get script details by ID
- [x] Download script content
- [x] Delete script (with confirmation)
- [ ] Update script metadata
- [x] Search scripts by name/content

**API Endpoints:**
- `GET /api/v1/scripts` - List all scripts
- `GET /api/v1/scripts/{script_id}` - Get script details
- `GET /api/v1/scripts/{script_id}/content` - Download script
- `DELETE /api/v1/scripts/{script_id}` - Delete script
- `PUT /api/v1/scripts/{script_id}/metadata` - Update metadata

### 2.6 File Monitoring and Cleanup
- [ ] Implement file system watcher for uploaded directory
- [ ] Automatic cleanup of old/unused scripts
- [ ] Disk space monitoring and alerts
- [ ] Backup old scripts before cleanup
- [ ] Generate usage statistics
- [ ] Implement retention policies

## Acceptance Criteria

- [ ] Python files can be uploaded successfully via API
- [ ] Files are stored securely with unique identifiers
- [ ] File validation prevents invalid/malicious scripts
- [ ] Metadata extraction works for common Python patterns
- [ ] All file management operations work correctly
- [ ] Storage cleanup runs automatically
- [ ] API responses include proper error handling
- [ ] File operations are atomic and safe

## Dependencies

- Stage 1: Core Infrastructure Setup
- File system permissions for upload directory
- Security scanner tools/libraries
- AST parsing knowledge for Python code analysis

## Notes

- Implement comprehensive input validation and sanitization
- Consider virus scanning for production environments  
- Use atomic file operations to prevent corruption
- Implement proper error recovery for failed uploads
- Monitor disk space usage and implement alerts
- Consider implementing file versioning for script updates
