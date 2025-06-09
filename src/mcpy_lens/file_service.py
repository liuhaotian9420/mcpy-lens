"""File upload and management service for mcpy-lens."""

import ast
import asyncio
import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

import aiofiles
from fastapi import HTTPException, UploadFile
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from mcpy_lens.config import get_settings
from mcpy_lens.discovery import (
    discover_functions, 
    discover_py_files,
    generate_schema_for_function, 
    generate_typer_wrapper,
    create_tool_metadata_file
)
from mcpy_lens.models import (
    CLIWrapperRequest,
    CLIWrapperResponse,
    FunctionInfo,
    FunctionSelectionRequest,
    FunctionSelectionResponse,
    ScriptMetadata,
    ScriptParameter,
    ScriptParametersRequest,
    ScriptParametersResponse,
    ToolDiscoveryResponse,
    ToolInfo,
    ValidationResult,
    ScriptUploadResponse,
    ScriptListResponse,
    EntryPointValidationResponse,
)
from mcpy_lens.wrapper.generator import WrapperGenerator
from mcpy_lens.wrapper.config import WrapperConfig
from mcpy_lens.validation import validate_script_entry_point

logger = logging.getLogger(__name__)

# Security patterns to check for dangerous operations
DANGEROUS_PATTERNS = [
    # r'os\.system\s*\(',
    r'subprocess\.',
    r'eval\s*\(',
    r'exec\s*\(',
    # r'open\s*\(',
    r'__import__\s*\(',
    r'importlib\.',
    r'getattr\s*\(',
    r'setattr\s*\(',
    r'delattr\s*\(',
    r'globals\s*\(\)',
    r'locals\s*\(\)',
    r'vars\s*\(',
]

# Blacklist for Unsafe imports
UNSAFE_IMPORTS = {
    'os',
    'sys',
    'subprocess',
    'eval',
    'exec',
    'builtins',
    'pickle',
    'marshal',
    'shelve',
    'ctypes',
    'cffi',
    'socket',
    'asyncio',
    'threading',
    'multiprocessing',
    'requests',
    'urllib',
    'httpx',
    'http.client',
    'websocket',
}


class FileSystemWatcher(FileSystemEventHandler):
    """File system event handler for monitoring uploaded scripts directory."""
    
    def __init__(self, file_service: 'FileService'):
        self.file_service = file_service
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            logger.info(f"New Python file detected: {event.src_path}")
    
    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            logger.info(f"Python file deleted: {event.src_path}")
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            logger.info(f"Python file modified: {event.src_path}")


class FileService:
    """Service for handling file upload and management operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self._scripts_metadata: dict[str, ScriptMetadata] = {}
        self._file_observer: Optional[Observer] = None
        self._function_selections: dict[str, list[str]] = {}  # script_id -> selected function names
        self._script_parameters: dict[str, list] = {}  # script_id -> parameter definitions
        self._load_existing_metadata()
        self._setup_file_monitoring()
    
    def _load_existing_metadata(self) -> None:
        """Load existing script metadata from storage."""
        metadata_file = self.settings.metadata_dir / "scripts_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for script_id, metadata_dict in data.items():
                        self._scripts_metadata[script_id] = ScriptMetadata(**metadata_dict)
                logger.info(f"Loaded metadata for {len(self._scripts_metadata)} scripts")
            except Exception as e:
                logger.error(f"Failed to load scripts metadata: {e}")

        # Load function selections
        selections_file = self.settings.metadata_dir / "function_selections.json"
        if selections_file.exists():
            try:
                with open(selections_file, 'r', encoding='utf-8') as f:
                    self._function_selections = json.load(f)
                logger.info(f"Loaded function selections for {len(self._function_selections)} scripts")
            except Exception as e:
                logger.error(f"Failed to load function selections: {e}")

        # Load script parameters
        params_file = self.settings.metadata_dir / "script_parameters.json"
        if params_file.exists():
            try:
                with open(params_file, 'r', encoding='utf-8') as f:
                    self._script_parameters = json.load(f)
                logger.info(f"Loaded script parameters for {len(self._script_parameters)} scripts")
            except Exception as e:
                logger.error(f"Failed to load script parameters: {e}")
    
    async def _save_metadata(self) -> None:
        """Save scripts metadata to storage."""
        metadata_file = self.settings.metadata_dir / "scripts_metadata.json"
        try:
            # Convert ScriptMetadata objects to dictionaries
            data = {}
            for script_id, metadata in self._scripts_metadata.items():
                data[script_id] = metadata.model_dump(mode='json')
            
            async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, default=str))
            logger.info("Scripts metadata saved successfully")
        except Exception as e:
            logger.error(f"Failed to save scripts metadata: {e}")
            raise HTTPException(status_code=500, detail="Failed to save metadata")
    
    def _generate_script_id(self) -> str:
        """Generate a unique script identifier."""
        return str(uuid.uuid4())
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove path components and dangerous characters
        filename = Path(filename).name
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        return filename[:100]  # Limit length
    
    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA256 hash of file content."""
        return hashlib.sha256(content).hexdigest()
    
    async def validate_python_file(self, content: bytes, filename: str) -> ValidationResult:
        """Validate uploaded Python file for syntax and security."""
        issues = []
        warnings = []
        syntax_valid = False
        security_safe = True
        
        try:
            # Decode content
            try:
                code_str = content.decode('utf-8')
            except UnicodeDecodeError:
                issues.append("File is not valid UTF-8 encoded text")
                return ValidationResult(
                    is_valid=False,
                    syntax_valid=False,
                    security_safe=False,
                    issues=issues,
                    warnings=warnings
                )
            
            # Check syntax
            try:
                ast.parse(code_str, filename=filename)
                syntax_valid = True
            except SyntaxError as e:
                issues.append(f"Syntax error on line {e.lineno}: {e.msg}")
            
            # Security checks
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, code_str, re.IGNORECASE):
                    issues.append(f"Potentially dangerous operation detected: {pattern}")
                    security_safe = False
            
            # Check imports
            try:
                tree = ast.parse(code_str)                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in UNSAFE_IMPORTS:
                                warnings.append(f"Import '{alias.name}' is not in allowed list")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module in UNSAFE_IMPORTS:
                            warnings.append(f"Import from '{node.module}' is not in allowed list")
            except Exception as e:
                warnings.append(f"Could not fully analyze imports: {e}")
            
            # File size check
            if len(content) > self.settings.max_file_size:
                issues.append(f"File size ({len(content)} bytes) exceeds limit ({self.settings.max_file_size} bytes)")
            
            # is_valid = syntax_valid and security_safe and len(issues) == 0
            is_valid = syntax_valid and security_safe

            return ValidationResult(
                is_valid=is_valid,
                syntax_valid=syntax_valid,
                security_safe=security_safe,
                issues=issues,
                warnings=warnings,
                details={
                    "file_size": len(content),
                    "encoding": "utf-8",
                    "analyzed": True
                }
            )
            
        except Exception as e:
            logger.error(f"Error validating file {filename}: {e}")
            return ValidationResult(
                is_valid=False,
                syntax_valid=False,
                security_safe=False,
                issues=[f"Validation error: {str(e)}"],
                warnings=warnings
            )
    
    def extract_script_metadata(self, content: bytes, script_id: str, filename: str) -> ScriptMetadata:
        """Extract metadata from Python script."""
        try:
            code_str = content.decode('utf-8')
            tree = ast.parse(code_str, filename=filename)
            
            functions = []
            imports = []
            dependencies = []
            
            # Extract functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Extract function information
                    func_name = node.name
                    
                    # Get docstring
                    docstring = ""
                    if (node.body and isinstance(node.body[0], ast.Expr) 
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                        docstring = node.body[0].value.value.strip()
                    
                    # Get parameters
                    parameters = {}
                    for arg in node.args.args:
                        param_name = arg.arg
                        param_type = "Any"
                        if arg.annotation:
                            try:
                                param_type = ast.unparse(arg.annotation)
                            except:
                                param_type = "Any"
                        parameters[param_name] = param_type
                    
                    # Get return type
                    return_type = "Any"
                    if node.returns:
                        try:
                            return_type = ast.unparse(node.returns)
                        except:
                            return_type = "Any"
                    
                    functions.append(FunctionInfo(
                        name=func_name,
                        description=docstring,
                        parameters=parameters,
                        return_type=return_type,
                        line_number=node.lineno
                    ))
                
                # Extract imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # For now, dependencies are inferred from imports
            # TODO: Parse requirements.txt or setup.py if present
            dependencies = [imp for imp in imports if imp not in {'datetime', 'json', 'typing', 're', 'os', 'sys'}]
            
            return ScriptMetadata(
                script_id=script_id,
                filename=filename,
                functions=functions,
                imports=list(set(imports)),
                dependencies=list(set(dependencies)),
                file_size=len(content),
                upload_time=datetime.now(),
                validation_status="passed",
                security_status="safe"
            )
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {filename}: {e}")
            # Return minimal metadata on error
            return ScriptMetadata(
                script_id=script_id,
                filename=filename,
                functions=[],
                imports=[],
                dependencies=[],
                file_size=len(content),
                upload_time=datetime.now(),
                validation_status="error",
                security_status="unknown"
            )
    
    async def upload_script(self, file: UploadFile) -> ScriptUploadResponse:
        """Upload and process a Python script file."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Check file extension
        if not any(file.filename.endswith(ext) for ext in self.settings.allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed. Allowed extensions: {self.settings.allowed_extensions}"
            )
        
        # Generate script ID and sanitize filename
        script_id = self._generate_script_id()
        clean_filename = self._sanitize_filename(file.filename)
        
        try:
            # Read file content
            content = await file.read()
            
            # Validate file
            validation = await self.validate_python_file(content, clean_filename)
            
            if not validation.is_valid:
                return ScriptUploadResponse(
                    script_id=script_id,
                    filename=clean_filename,
                    size=len(content),
                    upload_time=datetime.now(),
                    validation=validation,
                    metadata=None
                )
            
            # Check for duplicates using file hash
            file_hash = self._calculate_file_hash(content)
            for existing_id, metadata in self._scripts_metadata.items():
                existing_path = self.settings.uploaded_scripts_dir / f"{existing_id}.py"
                if existing_path.exists():
                    try:
                        async with aiofiles.open(existing_path, 'rb') as f:
                            existing_content = await f.read()
                            if self._calculate_file_hash(existing_content) == file_hash:
                                logger.info(f"Duplicate file detected: {clean_filename} matches {existing_id}")
                                validation.warnings.append("File content matches existing script")
                                break
                    except Exception:
                        pass
            
            # Create storage path with date organization
            upload_date = datetime.now().strftime("%Y-%m-%d")
            date_dir = self.settings.uploaded_scripts_dir / upload_date
            date_dir.mkdir(exist_ok=True)
            
            script_path = date_dir / f"{script_id}.py"
            
            # Save file
            async with aiofiles.open(script_path, 'wb') as f:
                await f.write(content)
            
            # Extract metadata
            metadata = self.extract_script_metadata(content, script_id, clean_filename)
            
            # Store metadata
            self._scripts_metadata[script_id] = metadata
            await self._save_metadata()
            
            logger.info(f"Successfully uploaded script {script_id}: {clean_filename}")
            
            return ScriptUploadResponse(
                script_id=script_id,
                filename=clean_filename,
                size=len(content),
                upload_time=datetime.now(),
                validation=validation,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error uploading script {clean_filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    def get_script_metadata(self, script_id: str) -> ScriptMetadata:
        """Get metadata for a specific script."""
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")
        return self._scripts_metadata[script_id]
    
    def list_scripts(self, limit: int = 100, offset: int = 0) -> ScriptListResponse:
        """List all uploaded scripts with pagination."""
        scripts = list(self._scripts_metadata.values())
        
        # Sort by upload time (newest first)
        scripts.sort(key=lambda x: x.upload_time, reverse=True)
        
        # Apply pagination
        paginated_scripts = scripts[offset:offset + limit]
        
        return ScriptListResponse(
            scripts=paginated_scripts,
            total=len(scripts)
        )
    
    async def get_script_content(self, script_id: str) -> bytes:
        """Get the content of a script file."""
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")
        
        metadata = self._scripts_metadata[script_id]
        
        # Try to find the file in date-organized structure first
        upload_date = metadata.upload_time.strftime("%Y-%m-%d")
        script_path = self.settings.uploaded_scripts_dir / upload_date / f"{script_id}.py"
        
        # Fallback to root directory
        if not script_path.exists():
            script_path = self.settings.uploaded_scripts_dir / f"{script_id}.py"
        
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="Script file not found on disk")
        
        try:
            async with aiofiles.open(script_path, 'rb') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Error reading script {script_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to read script file")
    
    async def delete_script(self, script_id: str) -> bool:
        """Delete a script and its metadata."""
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")
        
        metadata = self._scripts_metadata[script_id]
        
        # Find and remove the file
        upload_date = metadata.upload_time.strftime("%Y-%m-%d")
        script_path = self.settings.uploaded_scripts_dir / upload_date / f"{script_id}.py"
        
        # Fallback to root directory
        if not script_path.exists():
            script_path = self.settings.uploaded_scripts_dir / f"{script_id}.py"
        
        if script_path.exists():
            try:
                script_path.unlink()
                logger.info(f"Deleted script file: {script_path}")
            except Exception as e:
                logger.error(f"Error deleting script file {script_path}: {e}")
                raise HTTPException(status_code=500, detail="Failed to delete script file")
        
        # Remove from metadata
        del self._scripts_metadata[script_id]
        await self._save_metadata()
        
        logger.info(f"Successfully deleted script {script_id}")
        return True
    
    def search_scripts(self, query: str, search_in: list[str] = None, limit: int = 50) -> ScriptListResponse:
        """Search scripts by name, content, or metadata."""
        if search_in is None:
            search_in = ["filename", "functions", "description"]
        
        query_lower = query.lower()
        matching_scripts = []
        
        for metadata in self._scripts_metadata.values():
            match_found = False
            
            # Search in filename
            if "filename" in search_in and query_lower in metadata.filename.lower():
                match_found = True
            
            # Search in function names and descriptions
            if "functions" in search_in:
                for func in metadata.functions:
                    if (query_lower in func.name.lower() or 
                        query_lower in func.description.lower()):
                        match_found = True
                        break
            
            # Search in imports and dependencies
            if "imports" in search_in:
                if any(query_lower in imp.lower() for imp in metadata.imports):
                    match_found = True
            
            if match_found:
                matching_scripts.append(metadata)
                if len(matching_scripts) >= limit:
                    break
        
        # Sort by upload time (newest first)
        matching_scripts.sort(key=lambda x: x.upload_time, reverse=True)
        
        return ScriptListResponse(
            scripts=matching_scripts,
            total=len(matching_scripts)
        )
    
    def _setup_file_monitoring(self) -> None:
        """Set up file system monitoring for uploaded scripts directory."""
        try:
            self._file_observer = Observer()
            event_handler = FileSystemWatcher(self)
            self._file_observer.schedule(
                event_handler,
                str(self.settings.uploaded_scripts_dir),
                recursive=True
            )
            self._file_observer.start()
            logger.info("File system monitoring started")
        except Exception as e:
            logger.error(f"Failed to start file system monitoring: {e}")
    
    def stop_monitoring(self) -> None:
        """Stop file system monitoring."""
        if self._file_observer:
            self._file_observer.stop()
            self._file_observer.join()
            logger.info("File system monitoring stopped")
    
    async def cleanup_old_scripts(self, days_old: int = 30, dry_run: bool = True) -> dict[str, Any]:
        """Clean up scripts older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        scripts_to_remove = []
        total_size_freed = 0
        
        for script_id, metadata in self._scripts_metadata.items():
            if metadata.upload_time < cutoff_date:
                scripts_to_remove.append((script_id, metadata))
        
        cleanup_results = {
            "dry_run": dry_run,
            "cutoff_date": cutoff_date.isoformat(),
            "scripts_found": len(scripts_to_remove),
            "scripts_removed": 0,
            "size_freed_bytes": 0,
            "errors": []
        }
        
        if not dry_run:
            for script_id, metadata in scripts_to_remove:
                try:
                    # Backup before deletion
                    if await self._backup_script(script_id):
                        await self.delete_script(script_id)
                        cleanup_results["scripts_removed"] += 1
                        cleanup_results["size_freed_bytes"] += metadata.file_size
                        logger.info(f"Cleaned up old script: {script_id}")
                except Exception as e:
                    error_msg = f"Failed to cleanup script {script_id}: {e}"
                    cleanup_results["errors"].append(error_msg)
                    logger.error(error_msg)
        else:
            # Calculate potential savings for dry run
            cleanup_results["size_freed_bytes"] = sum(m.file_size for _, m in scripts_to_remove)
        
        return cleanup_results
    
    async def _backup_script(self, script_id: str) -> bool:
        """Backup a script before deletion."""
        try:
            # Create backup directory
            backup_dir = self.settings.uploaded_scripts_dir / "archive"
            backup_dir.mkdir(exist_ok=True)
            
            # Get script content
            content = await self.get_script_content(script_id)
            metadata = self._scripts_metadata[script_id]
            
            # Create backup filename with timestamp
            backup_filename = f"{script_id}_{metadata.filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            backup_path = backup_dir / backup_filename
            
            # Save backup
            async with aiofiles.open(backup_path, 'wb') as f:
                await f.write(content)
            
            # Save metadata backup
            metadata_backup = backup_dir / f"{script_id}_metadata.json"
            async with aiofiles.open(metadata_backup, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata.model_dump(mode='json'), indent=2, default=str))
            
            logger.info(f"Backed up script {script_id} to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup script {script_id}: {e}")
            return False
    
    def get_storage_statistics(self) -> dict[str, Any]:
        """Get storage usage statistics."""
        stats = {
            "total_scripts": len(self._scripts_metadata),
            "total_size_bytes": 0,
            "scripts_by_date": {},
            "functions_count": 0,
            "unique_imports": set(),
            "average_file_size": 0,
            "largest_script": None,
            "oldest_script": None,
            "newest_script": None
        }
        
        if not self._scripts_metadata:
            return stats
        
        all_scripts = list(self._scripts_metadata.values())
        
        # Calculate basic statistics
        stats["total_size_bytes"] = sum(script.file_size for script in all_scripts)
        stats["average_file_size"] = stats["total_size_bytes"] / len(all_scripts)
        stats["functions_count"] = sum(len(script.functions) for script in all_scripts)
        
        # Collect unique imports
        for script in all_scripts:
            stats["unique_imports"].update(script.imports)
        stats["unique_imports"] = list(stats["unique_imports"])
        
        # Find extremes
        largest_script = max(all_scripts, key=lambda x: x.file_size)
        stats["largest_script"] = {
            "script_id": largest_script.script_id,
            "filename": largest_script.filename,
            "size_bytes": largest_script.file_size
        }
        
        oldest_script = min(all_scripts, key=lambda x: x.upload_time)
        stats["oldest_script"] = {
            "script_id": oldest_script.script_id,
            "filename": oldest_script.filename,
            "upload_time": oldest_script.upload_time.isoformat()
        }
        
        newest_script = max(all_scripts, key=lambda x: x.upload_time)
        stats["newest_script"] = {
            "script_id": newest_script.script_id,
            "filename": newest_script.filename,
            "upload_time": newest_script.upload_time.isoformat()
        }
        
        # Group by upload date
        for script in all_scripts:
            date_key = script.upload_time.strftime("%Y-%m-%d")
            if date_key not in stats["scripts_by_date"]:
                stats["scripts_by_date"][date_key] = {"count": 0, "total_size": 0}
            stats["scripts_by_date"][date_key]["count"] += 1
            stats["scripts_by_date"][date_key]["total_size"] += script.file_size
        
        return stats
    
    async def check_disk_space(self) -> dict[str, Any]:
        """Check available disk space and usage."""
        import shutil
        
        try:
            total, used, free = shutil.disk_usage(self.settings.uploaded_scripts_dir)
            
            # Calculate usage by our scripts
            our_usage = sum(script.file_size for script in self._scripts_metadata.values())
            
            return {
                "disk_total_bytes": total,
                "disk_used_bytes": used,
                "disk_free_bytes": free,
                "disk_usage_percent": (used / total) * 100,
                "our_usage_bytes": our_usage,
                "our_usage_percent": (our_usage / total) * 100 if total > 0 else 0,
                "warning_threshold": 80,  # Warning if disk usage > 80%
                "critical_threshold": 90,  # Critical if disk usage > 90%
                "status": "ok" if (used / total) * 100 < 80 else "warning" if (used / total) * 100 < 90 else "critical"
            }
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return {"error": str(e), "status": "unknown"}
    
    async def discover_tools_from_file(self, script_id: str) -> ToolDiscoveryResponse:
        """
        Discover tools in the specified script.
        
        Args:
            script_id: The ID of the uploaded script
            
        Returns:
            ToolDiscoveryResponse with discovered tools
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")
        
        metadata = self._scripts_metadata[script_id]
        
        try:
            # Find script file path
            upload_date = metadata.upload_time.strftime("%Y-%m-%d")
            script_path = self.settings.uploaded_scripts_dir / upload_date / f"{script_id}.py"
            
            # Fallback to root directory
            if not script_path.exists():
                script_path = self.settings.uploaded_scripts_dir / f"{script_id}.py"
            
            if not script_path.exists():
                raise HTTPException(status_code=404, detail="Script file not found on disk")
            
            # Discover Python functions
            files = discover_py_files(str(script_path))
            discovered_functions = discover_functions(files)
            
            # Generate tool info for each function
            tools = []
            for func, func_name, file_path in discovered_functions:
                # Generate schema
                schema = generate_schema_for_function(func)
                
                # Create tool info
                tool_info = ToolInfo(
                    name=func_name,
                    description=schema["description"],
                    parameters=schema["input_schema"],
                    return_type=schema["output_schema"]["properties"]["result"] 
                        if "properties" in schema["output_schema"] else "any"
                )
                tools.append(tool_info)
            
            return ToolDiscoveryResponse(
                file_id=script_id,
                tools=tools,
                total=len(tools),
                discovery_time=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error discovering tools from script {script_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Tool discovery failed: {str(e)}")
    
    async def generate_tool_wrapper(self, script_id: str, function_name: str) -> Dict[str, Any]:
        """
        Generate a Typer CLI wrapper for a function in a script.
        
        Args:
            script_id: The ID of the uploaded script
            function_name: The name of the function to wrap
            
        Returns:
            Dictionary with wrapper information
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")
        
        metadata = self._scripts_metadata[script_id]
        
        # Check if function exists in script
        function_exists = any(f.name == function_name for f in metadata.functions)
        if not function_exists:
            raise HTTPException(
                status_code=404, 
                detail=f"Function '{function_name}' not found in script {script_id}"
            )
        
        try:
            # Find script file path
            upload_date = metadata.upload_time.strftime("%Y-%m-%d")
            script_path = self.settings.uploaded_scripts_dir / upload_date / f"{script_id}.py"
            
            # Fallback to root directory
            if not script_path.exists():
                script_path = self.settings.uploaded_scripts_dir / f"{script_id}.py"
            
            if not script_path.exists():
                raise HTTPException(status_code=404, detail="Script file not found on disk")
            
            # Discover the specific function
            files = discover_py_files(str(script_path))
            discovered_functions = discover_functions(files, [function_name])
            
            if not discovered_functions:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Function '{function_name}' could not be loaded from script"
                )
            
            # Get the function
            func, func_name, file_path = discovered_functions[0]
            
            # Generate schema
            schema = generate_schema_for_function(func)
            
            # Create wrapper directory if not exists
            wrapper_dir = self.settings.wrappers_dir
            wrapper_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate wrapper
            wrapper_path = generate_typer_wrapper(
                script_path,
                function_name,
                schema,
                wrapper_dir
            )
            
            # Create metadata directory if not exists
            metadata_dir = self.settings.metadata_dir
            metadata_dir.mkdir(parents=True, exist_ok=True)
            
            # Create tool metadata file
            metadata_file = create_tool_metadata_file(
                script_path,
                function_name,
                schema,
                wrapper_path,
                metadata_dir
            )
            
            return {
                "script_id": script_id,
                "function_name": function_name,
                "wrapper_path": str(wrapper_path),
                "metadata_path": str(metadata_file),
                "schema": schema,
                "created_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating wrapper for {function_name} in {script_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Wrapper generation failed: {str(e)}")
    
    def set_service_manager(self, service_manager):
        """Set the service manager for automatic registration."""
        self._service_manager = service_manager

    async def register_script_as_tool_service(self, script_id: str) -> Dict[str, Any]:
        """
        Register an entire script as a tool service.

        Args:
            script_id: The ID of the uploaded script

        Returns:
            Dictionary with service registration information
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")

        metadata = self._scripts_metadata[script_id]
        
        try:
            # Find script file path
            upload_date = metadata.upload_time.strftime("%Y-%m-%d")
            script_path = self.settings.uploaded_scripts_dir / upload_date / f"{script_id}.py"
            
            # Fallback to root directory
            if not script_path.exists():
                script_path = self.settings.uploaded_scripts_dir / f"{script_id}.py"
            
            if not script_path.exists():
                raise HTTPException(status_code=404, detail="Script file not found on disk")
            
            # Discover all functions in the script
            files = discover_py_files(str(script_path))
            discovered_functions = discover_functions(files)
            
            if not discovered_functions:
                raise HTTPException(
                    status_code=400, 
                    detail="No suitable functions found in script for tool registration"
                )
            
            # Generate wrapper and metadata for each function
            wrappers = []
            for func, func_name, file_path in discovered_functions:
                # Generate schema
                schema = generate_schema_for_function(func)
                
                # Create wrapper
                wrapper_path = generate_typer_wrapper(
                    script_path,
                    func_name,
                    schema,
                    self.settings.wrappers_dir
                )
                
                # Create tool metadata file
                metadata_file = create_tool_metadata_file(
                    script_path,
                    func_name,
                    schema,
                    wrapper_path,
                    self.settings.metadata_dir
                )
                
                wrappers.append({
                    "function_name": func_name,
                    "wrapper_path": str(wrapper_path),
                    "metadata_path": str(metadata_file),
                    "schema": schema
                })
            
            # Register the script as a service
            service_metadata = {
                "script_id": script_id,
                "filename": metadata.filename,
                "functions": [wrapper["function_name"] for wrapper in wrappers],
                "wrappers": wrappers,
                "created_at": datetime.now().isoformat()
            }
            
            # Save service metadata (legacy format)
            service_file = self.settings.services_dir / f"{script_id}_service.json"
            async with aiofiles.open(service_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(service_metadata, indent=2, default=str))

            # Auto-register with new service registry if available
            if hasattr(self, '_service_manager') and self._service_manager:
                try:
                    # Convert to new service registry format
                    from mcpy_lens.service_registry.models import ToolInfo

                    tools = []
                    for wrapper in wrappers:
                        tool = ToolInfo(
                            name=wrapper["function_name"],
                            description=wrapper["schema"].get("description", ""),
                            parameters=wrapper["schema"].get("input_schema", {}),
                            return_type=wrapper["schema"].get("output_schema", {}).get("type", "Any")
                        )
                        tools.append(tool)

                    # Create wrapper metadata for service registry
                    wrapper_metadata = {
                        "name": f"{metadata.filename}_{script_id}",
                        "description": f"Auto-generated service for script {metadata.filename}",
                        "type": "function",
                        "hosting_mode": "sse",
                        "tools": [tool.to_dict() for tool in tools]
                    }

                    # Register with service manager
                    await self._service_manager.register_service_from_wrapper(
                        script_id, wrapper_metadata, auto_activate=True
                    )

                    logger.info(f"Auto-registered script {script_id} with new service registry")

                except Exception as e:
                    logger.warning(f"Failed to auto-register with service registry: {e}")
                    # Don't fail the whole operation if service registry fails

            return service_metadata
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registering script {script_id} as tool service: {e}")
            raise HTTPException(status_code=500, detail=f"Service registration failed: {str(e)}")
            
    async def get_registered_tool_services(self) -> list[Dict[str, Any]]:
        """
        Get all registered tool services.
        
        Returns:
            List of service metadata dictionaries
        """
        services = []
        
        try:
            # Get all service files
            service_files = list(self.settings.services_dir.glob('*_service.json'))
            
            for service_file in service_files:
                try:
                    async with aiofiles.open(service_file, 'r', encoding='utf-8') as f:
                        service_data = json.loads(await f.read())
                        services.append(service_data)
                except Exception as e:
                    logger.error(f"Error reading service file {service_file}: {e}")
            
            return services
            
        except Exception as e:
            logger.error(f"Error getting registered tool services: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get tool services: {str(e)}")
    
    async def get_tool_schema(self, script_id: str, function_name: str) -> Dict[str, Any]:
        """
        Get JSON schema for a specific function in a script.
        
        Args:
            script_id: The ID of the uploaded script
            function_name: The name of the function
            
        Returns:
            JSON schema for the function
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")
        
        metadata = self._scripts_metadata[script_id]
        
        # Check if function exists in script
        function_exists = any(f.name == function_name for f in metadata.functions)
        if not function_exists:
            raise HTTPException(
                status_code=404, 
                detail=f"Function '{function_name}' not found in script {script_id}"
            )
        
        try:
            # Find script file path
            upload_date = metadata.upload_time.strftime("%Y-%m-%d")
            script_path = self.settings.uploaded_scripts_dir / upload_date / f"{script_id}.py"
            
            # Fallback to root directory
            if not script_path.exists():
                script_path = self.settings.uploaded_scripts_dir / f"{script_id}.py"
            
            if not script_path.exists():
                raise HTTPException(status_code=404, detail="Script file not found on disk")
            
            # Discover the specific function
            files = discover_py_files(str(script_path))
            discovered_functions = discover_functions(files, [function_name])
            
            if not discovered_functions:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Function '{function_name}' could not be loaded from script"
                )
            
            # Get the function
            func, func_name, file_path = discovered_functions[0]
            
            # Generate schema
            schema = generate_schema_for_function(func)
            
            # Add metadata about the source
            schema["source"] = {
                "script_id": script_id,
                "file_path": str(file_path),
                "generated_at": datetime.now().isoformat()
            }
            
            return schema
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating schema for {function_name} in {script_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Schema generation failed: {str(e)}")
    
    async def validate_entry_point(self, script_id: str) -> EntryPointValidationResponse:
        """
        Validate the entry point of a script.
        
        Args:
            script_id: The ID of the uploaded script
            
        Returns:
            EntryPointValidationResponse with validation results
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")
        
        metadata = self._scripts_metadata[script_id]
        
        try:
            # Find script file path
            upload_date = metadata.upload_time.strftime("%Y-%m-%d")
            script_path = self.settings.uploaded_scripts_dir / upload_date / f"{script_id}.py"
            
            # Fallback to root directory
            if not script_path.exists():
                script_path = self.settings.uploaded_scripts_dir / f"{script_id}.py"
            
            if not script_path.exists():
                raise HTTPException(status_code=404, detail="Script file not found on disk")
              # Validate entry point using existing validation function
            has_entry_point = validate_script_entry_point(script_path)
            
            # Determine operation modes
            executable_mode_supported = has_entry_point
            function_mode_supported = True  # All scripts support function selection mode
            
            validation_details = {
                "script_path": str(script_path),
                "analysis_method": "AST parsing",
                "entry_point_pattern": "if __name__ == '__main__'"
            }
            
            return EntryPointValidationResponse(
                script_id=script_id,
                has_entry_point=has_entry_point,
                executable_mode_supported=executable_mode_supported,
                function_mode_supported=function_mode_supported,
                validation_details=validation_details
            )
            
        except Exception as e:
            logger.error(f"Error validating entry point for script {script_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Entry point validation failed: {str(e)}")

    async def _save_function_selections(self) -> None:
        """Save function selections to disk."""
        selections_file = self.settings.metadata_dir / "function_selections.json"
        try:
            async with aiofiles.open(selections_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self._function_selections, indent=2))
        except Exception as e:
            logger.error(f"Failed to save function selections: {e}")

    async def _save_script_parameters(self) -> None:
        """Save script parameters to disk."""
        params_file = self.settings.metadata_dir / "script_parameters.json"
        try:
            async with aiofiles.open(params_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self._script_parameters, indent=2))
        except Exception as e:
            logger.error(f"Failed to save script parameters: {e}")

    async def _generate_whole_file_wrapper_content(
        self,
        script_path: Path,
        parameters: list[ScriptParameter],
        wrapper_request: CLIWrapperRequest
    ) -> str:
        """
        Generate the content for a whole-file CLI wrapper.

        Args:
            script_path: Path to the original script
            parameters: List of script-level parameters
            wrapper_request: Wrapper configuration

        Returns:
            Generated wrapper content as string
        """
        # Read the original script content
        async with aiofiles.open(script_path, 'r', encoding='utf-8') as f:
            original_content = await f.read()

        # Generate parameter definitions for Typer
        param_definitions = []
        param_assignments = []

        for param in parameters:
            param_type = param.type
            default_value = f'"{param.default_value}"' if param.type == "str" and param.default_value else param.default_value

            if param.required:
                param_def = f'{param.name}: {param_type} = typer.Argument(..., help="{param.description}")'
            else:
                param_def = f'{param.name}: {param_type} = typer.Option({default_value}, help="{param.description}")'

            param_definitions.append(param_def)
            param_assignments.append(f'    sys.argv.extend(["--{param.name}", str({param.name})])')

        # Generate the wrapper content
        wrapper_content = f'''#!/usr/bin/env python3
"""
CLI Wrapper for {script_path.name}
Generated by mcpy-lens

Description: {wrapper_request.description}
"""

import sys
import subprocess
from pathlib import Path
import typer

app = typer.Typer(help="{wrapper_request.description}")

@app.command()
def main({", ".join(param_definitions) if param_definitions else ""}):
    """
    Execute the original script with provided parameters.
    """
    # Set up the original script path
    script_path = Path(__file__).parent / "{script_path.name}"

    # Prepare arguments for the original script
    args = [sys.executable, str(script_path)]

{chr(10).join(param_assignments) if param_assignments else "    # No parameters to pass"}

    # Execute the original script
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Script execution failed: {{e}}", err=True)
        typer.echo(f"Return code: {{e.returncode}}", err=True)
        if e.stdout:
            typer.echo(f"STDOUT: {{e.stdout}}", err=True)
        if e.stderr:
            typer.echo(f"STDERR: {{e.stderr}}", err=True)
        raise typer.Exit(e.returncode)

if __name__ == "__main__":
    app()
'''

        return wrapper_content

    async def select_functions_for_tools(
        self,
        script_id: str,
        selection_request: FunctionSelectionRequest
    ) -> FunctionSelectionResponse:
        """
        Select which functions to expose as tools.

        Args:
            script_id: The ID of the uploaded script
            selection_request: Request containing selected function names

        Returns:
            Response with selection information
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")

        metadata = self._scripts_metadata[script_id]
        available_functions = [f.name for f in metadata.functions]

        # Validate that all selected functions exist
        invalid_functions = [
            name for name in selection_request.selected_functions
            if name not in available_functions
        ]

        if invalid_functions:
            raise HTTPException(
                status_code=400,
                detail=f"Functions not found in script: {invalid_functions}"
            )

        # Store the selection
        self._function_selections[script_id] = selection_request.selected_functions

        # Save selections to disk
        await self._save_function_selections()

        return FunctionSelectionResponse(
            script_id=script_id,
            selected_functions=selection_request.selected_functions,
            total_functions=len(available_functions)
        )

    async def get_selected_functions(self, script_id: str) -> FunctionSelectionResponse:
        """
        Get the list of functions selected to be exposed as tools.

        Args:
            script_id: The ID of the uploaded script

        Returns:
            Response with current selection
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")

        metadata = self._scripts_metadata[script_id]
        selected_functions = self._function_selections.get(script_id, [])

        return FunctionSelectionResponse(
            script_id=script_id,
            selected_functions=selected_functions,
            total_functions=len(metadata.functions)
        )

    async def configure_script_parameters(
        self,
        script_id: str,
        params_request: ScriptParametersRequest
    ) -> ScriptParametersResponse:
        """
        Configure script-level parameters for CLI wrapper generation.

        Args:
            script_id: The ID of the uploaded script
            params_request: Request containing parameter definitions

        Returns:
            Response with configured parameters
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")

        # Validate parameter types
        valid_types = {"str", "int", "float", "bool"}
        for param in params_request.parameters:
            if param.type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid parameter type '{param.type}'. Must be one of: {valid_types}"
                )

        # Store the parameters
        self._script_parameters[script_id] = [param.model_dump() for param in params_request.parameters]

        # Save parameters to disk
        await self._save_script_parameters()

        return ScriptParametersResponse(
            script_id=script_id,
            parameters=params_request.parameters
        )

    async def get_script_parameters(self, script_id: str) -> ScriptParametersResponse:
        """
        Get the configured script-level parameters.

        Args:
            script_id: The ID of the uploaded script

        Returns:
            Response with current parameter configuration
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")

        param_dicts = self._script_parameters.get(script_id, [])
        parameters = [ScriptParameter(**param_dict) for param_dict in param_dicts]

        return ScriptParametersResponse(
            script_id=script_id,
            parameters=parameters
        )

    async def generate_whole_file_cli_wrapper(
        self,
        script_id: str,
        wrapper_request: CLIWrapperRequest
    ) -> CLIWrapperResponse:
        """
        Generate a single CLI wrapper for the entire Python file.

        Args:
            script_id: The ID of the uploaded script
            wrapper_request: Configuration for the CLI wrapper

        Returns:
            Response with wrapper information
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")

        metadata = self._scripts_metadata[script_id]

        # Validate that script has entry point
        validation_response = await self.validate_entry_point(script_id)
        if not validation_response.has_entry_point:
            raise HTTPException(
                status_code=400,
                detail="Script must have 'if __name__ == \"__main__\"' entry point for CLI wrapper generation"
            )

        try:
            # Find script file path
            upload_date = metadata.upload_time.strftime("%Y-%m-%d")
            script_path = self.settings.uploaded_scripts_dir / upload_date / f"{script_id}.py"

            # Fallback to root directory
            if not script_path.exists():
                script_path = self.settings.uploaded_scripts_dir / f"{script_id}.py"

            if not script_path.exists():
                raise HTTPException(status_code=404, detail="Script file not found on disk")

            # Get script parameters
            param_response = await self.get_script_parameters(script_id)

            # Generate the CLI wrapper
            wrapper_content = await self._generate_whole_file_wrapper_content(
                script_path,
                param_response.parameters,
                wrapper_request
            )

            # Create wrapper directory if not exists
            wrapper_dir = self.settings.wrappers_dir
            wrapper_dir.mkdir(parents=True, exist_ok=True)

            # Save wrapper file
            wrapper_filename = f"{script_id}_{wrapper_request.wrapper_name}.py"
            wrapper_path = wrapper_dir / wrapper_filename

            async with aiofiles.open(wrapper_path, 'w', encoding='utf-8') as f:
                await f.write(wrapper_content)

            # Create metadata file
            metadata_content = {
                "script_id": script_id,
                "wrapper_name": wrapper_request.wrapper_name,
                "description": wrapper_request.description,
                "original_script": str(script_path),
                "wrapper_path": str(wrapper_path),
                "parameters": [param.model_dump() for param in param_response.parameters],
                "created_at": datetime.now().isoformat(),
                "wrapper_type": "whole_file"
            }

            metadata_filename = f"{script_id}_{wrapper_request.wrapper_name}_metadata.json"
            metadata_path = self.settings.metadata_dir / metadata_filename

            async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata_content, indent=2, default=str))

            return CLIWrapperResponse(
                script_id=script_id,
                wrapper_name=wrapper_request.wrapper_name,
                wrapper_path=str(wrapper_path),
                metadata_path=str(metadata_path)
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating CLI wrapper for {script_id}: {e}")
            raise HTTPException(status_code=500, detail=f"CLI wrapper generation failed: {str(e)}")

    async def generate_mcp_wrapper(self, script_id: str) -> dict[str, Any]:
        """
        Generate an MCP-compatible wrapper for a script.

        Args:
            script_id: The ID of the uploaded script

        Returns:
            Dictionary with information about the generated wrapper
        """
        if script_id not in self._scripts_metadata:
            raise HTTPException(status_code=404, detail="Script not found")

        metadata = self._scripts_metadata[script_id]

        try:
            # Get selected functions (if any)
            selected_functions = self._function_selections.get(script_id, [])

            # If no functions selected, use all functions
            if not selected_functions:
                selected_functions = [func.name for func in metadata.functions]

            if not selected_functions:
                raise HTTPException(
                    status_code=400,
                    detail="No functions available for wrapper generation"
                )

            # Find script file path
            upload_date = metadata.upload_time.strftime("%Y-%m-%d")
            script_path = self.settings.uploaded_scripts_dir / upload_date / f"{script_id}.py"

            # Fallback to root directory
            if not script_path.exists():
                script_path = self.settings.uploaded_scripts_dir / f"{script_id}.py"

            if not script_path.exists():
                raise HTTPException(status_code=404, detail="Script file not found on disk")

            # Create output directory for the wrapper
            wrapper_output_dir = self.settings.wrappers_dir / f"{script_id}_mcp_wrapper"
            wrapper_output_dir.mkdir(parents=True, exist_ok=True)

            # Generate the wrapper using WrapperGenerator
            from mcpy_lens.wrapper.generator import WrapperGenerator
            from mcpy_lens.wrapper.config import WrapperConfig

            generator = WrapperGenerator(WrapperConfig.from_env())

            generated_files = generator.generate_wrapper(
                script_path=script_path,
                script_metadata=metadata,
                selected_functions=selected_functions,
                output_dir=wrapper_output_dir
            )

            logger.info(f"Generated MCP wrapper for script {script_id}")

            return {
                "script_id": script_id,
                "wrapper_type": "mcp",
                "selected_functions": selected_functions,
                "output_directory": str(wrapper_output_dir),
                "generated_files": {k: str(v) for k, v in generated_files.items()},
                "created_at": datetime.now().isoformat(),
                "usage_instructions": {
                    "command": f"python {generated_files['wrapper'].name}",
                    "description": "Run the wrapper as an MCP server",
                    "config_file": generated_files['config'].name
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating MCP wrapper for {script_id}: {e}")
            raise HTTPException(status_code=500, detail=f"MCP wrapper generation failed: {str(e)}")
