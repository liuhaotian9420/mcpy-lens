"""Pydantic models for mcpy-lens API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ——— Status and health models ———


class ServiceStatus(str, Enum):
    """Service status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field(description="Service status")
    version: str = Field(description="Application version")
    message: str | None = Field(default=None, description="Additional status message")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Error timestamp"
    )


# ——— File upload models ———


class FileUploadResponse(BaseModel):
    """File upload response model."""

    file_id: str = Field(description="Unique file identifier")
    filename: str = Field(description="Original filename")
    size: int = Field(description="File size in bytes")
    uploaded_at: datetime = Field(
        default_factory=datetime.now, description="Upload timestamp"
    )
    status: str = Field(default="uploaded", description="Upload status")


# ——— Service management models ———


class ServiceInfo(BaseModel):
    """Service information model."""

    service_id: str = Field(description="Unique service identifier")
    name: str = Field(description="Service name")
    version: str = Field(description="Service version")
    status: ServiceStatus = Field(description="Current service status")
    routes: list[str] = Field(description="Available routes for this service")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Service metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Service creation timestamp"
    )


class ServiceListResponse(BaseModel):
    """Response model for listing services."""

    services: list[ServiceInfo] = Field(description="List of registered services")
    total: int = Field(description="Total number of services")


class ServiceRegistrationRequest(BaseModel):
    """Request model for service registration."""

    name: str = Field(description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Service metadata"
    )


class ServiceRegistrationResponse(BaseModel):
    """Response model for service registration."""

    service_id: str = Field(description="Generated service identifier")
    name: str = Field(description="Service name")
    version: str = Field(description="Service version")
    status: ServiceStatus = Field(description="Registration status")
    routes: list[str] = Field(description="Registered routes")
    message: str = Field(description="Registration result message")


# ——— Tool discovery models ———


class ToolInfo(BaseModel):
    """Tool information model."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: dict[str, Any] = Field(description="Tool parameters schema")
    return_type: str = Field(description="Tool return type")


class ToolDiscoveryResponse(BaseModel):
    """Response model for tool discovery."""

    file_id: str = Field(description="Source file identifier")
    tools: list[ToolInfo] = Field(description="Discovered tools")
    total: int = Field(description="Total number of tools found")
    discovery_time: datetime = Field(
        default_factory=datetime.now, description="Discovery timestamp"
    )


# ——— Script metadata models ———


class FunctionInfo(BaseModel):
    """Information about a discovered function."""

    name: str = Field(description="Function name")
    description: str = Field(description="Function description from docstring")
    parameters: dict[str, Any] = Field(description="Function parameters with types")
    return_type: str = Field(description="Function return type annotation")
    line_number: int = Field(description="Line number where function is defined")


class ScriptMetadata(BaseModel):
    """Metadata extracted from uploaded script."""

    script_id: str = Field(description="Unique script identifier")
    filename: str = Field(description="Original filename")
    functions: list[FunctionInfo] = Field(description="Discovered functions")
    imports: list[str] = Field(description="Required imports")
    dependencies: list[str] = Field(description="Package dependencies")
    file_size: int = Field(description="File size in bytes")
    upload_time: datetime = Field(
        default_factory=datetime.now, description="Upload timestamp"
    )
    validation_status: str = Field(description="Validation result status")
    security_status: str = Field(description="Security scan status")


class ValidationResult(BaseModel):
    """Python file validation result."""

    is_valid: bool = Field(description="Whether the file is valid")
    syntax_valid: bool = Field(description="Whether syntax is valid")
    security_safe: bool = Field(description="Whether file passes security checks")
    issues: list[str] = Field(description="List of validation issues found")
    warnings: list[str] = Field(description="List of validation warnings")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional validation details"
    )


class ScriptUploadResponse(BaseModel):
    """Response for script upload operation."""

    script_id: str = Field(description="Generated script identifier")
    filename: str = Field(description="Original filename")
    size: int = Field(description="File size in bytes")
    upload_time: datetime = Field(
        default_factory=datetime.now, description="Upload timestamp"
    )
    validation: ValidationResult = Field(description="Validation results")
    metadata: ScriptMetadata | None = Field(
        default=None, description="Extracted metadata if validation passed"
    )


class ScriptListResponse(BaseModel):
    """Response for listing uploaded scripts."""

    scripts: list[ScriptMetadata] = Field(description="List of uploaded scripts")
    total: int = Field(description="Total number of scripts")


class ScriptSearchRequest(BaseModel):
    """Request for searching scripts."""

    query: str = Field(description="Search query")
    search_in: list[str] = Field(
        default=["filename", "functions", "description"],
        description="Fields to search in",
    )
    limit: int = Field(default=50, description="Maximum results to return")


# ——— Script validation models ———


class EntryPointValidationResponse(BaseModel):
    """Response for script entry point validation."""

    script_id: str = Field(description="Script identifier")
    has_entry_point: bool = Field(
        description="Whether script has if __name__ == '__main__' block"
    )
    executable_mode_supported: bool = Field(
        description="Whether script supports executable mode"
    )
    function_mode_supported: bool = Field(
        description="Whether script supports function selection mode"
    )
    validation_details: dict[str, Any] = Field(
        default_factory=dict, description="Additional validation details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Validation timestamp"
    )


# ——— Function selection models ———


class FunctionSelectionRequest(BaseModel):
    """Request model for selecting functions to expose as tools."""

    selected_functions: list[str] = Field(
        description="List of function names to expose as tools"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for selection"
    )


class FunctionSelectionResponse(BaseModel):
    """Response model for function selection operations."""

    script_id: str = Field(description="Script identifier")
    selected_functions: list[str] = Field(
        description="List of selected function names"
    )
    total_functions: int = Field(description="Total number of functions in script")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Selection timestamp"
    )


# ——— Script parameter models ———


class ScriptParameter(BaseModel):
    """Model for a script-level parameter."""

    name: str = Field(description="Parameter name")
    type: str = Field(description="Parameter type (str, int, float, bool)")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default_value: Any = Field(default=None, description="Default value if not required")


class ScriptParametersRequest(BaseModel):
    """Request model for defining script-level parameters."""

    parameters: list[ScriptParameter] = Field(
        description="List of script-level parameters"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ScriptParametersResponse(BaseModel):
    """Response model for script parameter operations."""

    script_id: str = Field(description="Script identifier")
    parameters: list[ScriptParameter] = Field(
        description="List of configured parameters"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Configuration timestamp"
    )


# ——— CLI wrapper models ———


class CLIWrapperRequest(BaseModel):
    """Request model for generating CLI wrapper."""

    wrapper_name: str = Field(description="Name for the CLI wrapper")
    description: str = Field(default="", description="Description of the wrapper")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class CLIWrapperResponse(BaseModel):
    """Response model for CLI wrapper generation."""

    script_id: str = Field(description="Script identifier")
    wrapper_name: str = Field(description="Generated wrapper name")
    wrapper_path: str = Field(description="Path to generated wrapper file")
    metadata_path: str = Field(description="Path to wrapper metadata file")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Generation timestamp"
    )


# ——— Generic response models ———


class SuccessResponse(BaseModel):
    """Generic success response model."""

    success: bool = Field(default=True, description="Operation success status")
    message: str = Field(description="Success message")
    data: dict[str, Any] | None = Field(
        default=None, description="Additional response data"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )
