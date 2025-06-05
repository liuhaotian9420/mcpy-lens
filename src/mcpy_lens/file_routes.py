"""File upload and management API routes for mcpy-lens."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from mcpy_lens.file_service import FileService
from mcpy_lens.models import (
    CLIWrapperRequest,
    CLIWrapperResponse,
    EntryPointValidationResponse,
    FunctionSelectionRequest,
    FunctionSelectionResponse,
    ScriptListResponse,
    ScriptMetadata,
    ScriptParametersRequest,
    ScriptParametersResponse,
    ScriptSearchRequest,
    ScriptUploadResponse,
    SuccessResponse,
    ToolDiscoveryResponse,
)

logger = logging.getLogger(__name__)

# Create router for file operations
file_router = APIRouter(prefix="/api/v1", tags=["files"])

# Dependency to get file service
def get_file_service() -> FileService:
    """Get file service instance."""
    return FileService()


@file_router.post("/upload_script", response_model=ScriptUploadResponse)
async def upload_script(
    file: UploadFile = File(..., description="Python script file to upload"),
    file_service: FileService = Depends(get_file_service)
) -> ScriptUploadResponse:
    """
    Upload a Python script file.
    
    - **file**: Python script file (.py extension required)
    
    Returns script metadata and validation results.
    """
    logger.info(f"Uploading script: {file.filename}")
    
    try:
        result = await file_service.upload_script(file)
        logger.info(f"Script upload completed: {result.script_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading script: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during upload")


@file_router.get("/scripts", response_model=ScriptListResponse)
async def list_scripts(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of scripts to return"),
    offset: int = Query(default=0, ge=0, description="Number of scripts to skip"),
    file_service: FileService = Depends(get_file_service)
) -> ScriptListResponse:
    """
    List all uploaded scripts with pagination.
    
    - **limit**: Maximum number of scripts to return (1-100)
    - **offset**: Number of scripts to skip for pagination
    """
    logger.info(f"Listing scripts with limit={limit}, offset={offset}")
    
    try:
        return file_service.list_scripts(limit=limit, offset=offset)
    except Exception as e:
        logger.error(f"Error listing scripts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scripts list")


@file_router.get("/scripts/{script_id}", response_model=ScriptMetadata)
async def get_script_details(
    script_id: str,
    file_service: FileService = Depends(get_file_service)
) -> ScriptMetadata:
    """
    Get detailed information about a specific script.
    
    - **script_id**: Unique identifier of the script
    """
    logger.info(f"Getting details for script: {script_id}")
    
    try:
        return file_service.get_script_metadata(script_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting script details for {script_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve script details")


@file_router.get("/scripts/{script_id}/content")
async def get_script_content(
    script_id: str,
    file_service: FileService = Depends(get_file_service)
) -> Response:
    """
    Download the content of a script file.
    
    - **script_id**: Unique identifier of the script
    """
    logger.info(f"Downloading content for script: {script_id}")
    
    try:
        content = await file_service.get_script_content(script_id)
        metadata = file_service.get_script_metadata(script_id)
        
        return Response(
            content=content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={metadata.filename}",
                "Content-Type": "application/octet-stream"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading script content for {script_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download script content")


@file_router.delete("/scripts/{script_id}", response_model=SuccessResponse)
async def delete_script(
    script_id: str,
    file_service: FileService = Depends(get_file_service)
) -> SuccessResponse:
    """
    Delete a script and its metadata.
    
    - **script_id**: Unique identifier of the script to delete
    """
    logger.info(f"Deleting script: {script_id}")
    
    try:
        success = await file_service.delete_script(script_id)
        
        if success:
            return SuccessResponse(
                message=f"Script {script_id} deleted successfully",
                data={"script_id": script_id}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete script")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting script {script_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete script")


@file_router.post("/scripts/search", response_model=ScriptListResponse)
async def search_scripts(
    search_request: ScriptSearchRequest,
    file_service: FileService = Depends(get_file_service)
) -> ScriptListResponse:
    """
    Search for scripts by query string.
    
    - **query**: Search query string
    - **search_in**: Fields to search in (filename, functions, imports)
    - **limit**: Maximum number of results to return
    """
    logger.info(f"Searching scripts with query: {search_request.query}")
    
    try:
        return file_service.search_scripts(
            query=search_request.query,
            search_in=search_request.search_in,
            limit=search_request.limit
        )
    except Exception as e:
        logger.error(f"Error searching scripts: {e}")
        raise HTTPException(status_code=500, detail="Failed to search scripts")


@file_router.put("/scripts/{script_id}/metadata", response_model=ScriptMetadata)
async def update_script_metadata(
    script_id: str,
    metadata_update: dict,
    file_service: FileService = Depends(get_file_service)
) -> ScriptMetadata:
    """
    Update script metadata (limited fields only).
    
    - **script_id**: Unique identifier of the script
    - **metadata_update**: Fields to update (description, tags, etc.)
    """
    logger.info(f"Updating metadata for script: {script_id}")
    
    # For now, this is a placeholder - metadata updates could be implemented
    # to allow users to add descriptions, tags, or other annotations
    raise HTTPException(
        status_code=501, 
        detail="Metadata updates not implemented yet"
    )


@file_router.get("/scripts/{script_id}/discover", response_model=ToolDiscoveryResponse)
async def discover_tools(
    script_id: str,
    file_service: FileService = Depends(get_file_service)
) -> ToolDiscoveryResponse:
    """
    Discover tools in a script file.
    
    - **script_id**: Unique identifier of the script
    
    Returns a list of discovered tools and their parameters.
    """
    logger.info(f"Discovering tools in script: {script_id}")
    
    try:
        return await file_service.discover_tools_from_file(script_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discovering tools in {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to discover tools: {str(e)}")


@file_router.get("/scripts/{script_id}/validate_entry_point", response_model=EntryPointValidationResponse)
async def validate_script_entry_point(
    script_id: str,
    file_service: FileService = Depends(get_file_service)
) -> EntryPointValidationResponse:
    """
    Validate if a script has the required entry point for executable mode.
    
    - **script_id**: Unique identifier of the script
    
    Returns validation results indicating if the script has 'if __name__ == "__main__"' entry point.
    """
    logger.info(f"Validating entry point for script: {script_id}")
    
    try:
        return await file_service.validate_entry_point(script_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating entry point for {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate entry point: {str(e)}") from e


@file_router.get("/scripts/{script_id}/function/{function_name}/schema")
async def get_function_schema(
    script_id: str,
    function_name: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    Get JSON schema for a specific function in a script.
    
    - **script_id**: Unique identifier of the script
    - **function_name**: Name of the function to get schema for
    
    Returns a JSON schema for the function parameters and return value.
    """
    logger.info(f"Getting schema for function {function_name} in script {script_id}")
    
    try:
        return await file_service.get_tool_schema(script_id, function_name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema for {function_name} in {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")


@file_router.post("/scripts/{script_id}/function/{function_name}/wrapper")
async def generate_function_wrapper(
    script_id: str,
    function_name: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    Generate a CLI wrapper for a specific function in a script.
    
    - **script_id**: Unique identifier of the script
    - **function_name**: Name of the function to wrap
    
    Returns information about the generated wrapper.
    """
    logger.info(f"Generating wrapper for function {function_name} in script {script_id}")
    
    try:
        return await file_service.generate_tool_wrapper(script_id, function_name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating wrapper for {function_name} in {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate wrapper: {str(e)}")


@file_router.post("/scripts/{script_id}/register", response_model=SuccessResponse)
async def register_script_as_service(
    script_id: str,
    file_service: FileService = Depends(get_file_service)
) -> SuccessResponse:
    """
    Register a script as a tool service.
    
    - **script_id**: Unique identifier of the script
    
    Returns information about the registered service.
    """
    logger.info(f"Registering script as service: {script_id}")
    
    try:
        service_metadata = await file_service.register_script_as_tool_service(script_id)
        
        return SuccessResponse(
            message=f"Script {script_id} successfully registered as tool service",
            data=service_metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering script {script_id} as service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register service: {str(e)}")


@file_router.get("/services")
async def list_tool_services(
    file_service: FileService = Depends(get_file_service)
):
    """
    List all registered tool services.

    Returns a list of all registered tool services.
    """
    logger.info("Listing all registered tool services")

    try:
        return await file_service.get_registered_tool_services()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool services: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tool services: {str(e)}")


@file_router.post("/scripts/{script_id}/functions/select", response_model=FunctionSelectionResponse)
async def select_functions_for_tools(
    script_id: str,
    selection_request: FunctionSelectionRequest,
    file_service: FileService = Depends(get_file_service)
) -> FunctionSelectionResponse:
    """
    Select which functions to expose as tools.

    - **script_id**: Unique identifier of the script
    - **selection_request**: List of function names to expose as tools

    Returns information about the selected functions.
    """
    logger.info(f"Selecting functions for tools in script: {script_id}")

    try:
        return await file_service.select_functions_for_tools(script_id, selection_request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting functions for {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to select functions: {str(e)}")


@file_router.get("/scripts/{script_id}/functions/selected", response_model=FunctionSelectionResponse)
async def get_selected_functions(
    script_id: str,
    file_service: FileService = Depends(get_file_service)
) -> FunctionSelectionResponse:
    """
    Get the list of functions selected to be exposed as tools.

    - **script_id**: Unique identifier of the script

    Returns the current function selection.
    """
    logger.info(f"Getting selected functions for script: {script_id}")

    try:
        return await file_service.get_selected_functions(script_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting selected functions for {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get selected functions: {str(e)}")


@file_router.post("/scripts/{script_id}/cli_params", response_model=ScriptParametersResponse)
async def configure_script_parameters(
    script_id: str,
    params_request: ScriptParametersRequest,
    file_service: FileService = Depends(get_file_service)
) -> ScriptParametersResponse:
    """
    Configure script-level parameters for CLI wrapper generation.

    - **script_id**: Unique identifier of the script
    - **params_request**: List of script-level parameters to configure

    Returns information about the configured parameters.
    """
    logger.info(f"Configuring script parameters for: {script_id}")

    try:
        return await file_service.configure_script_parameters(script_id, params_request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring parameters for {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to configure parameters: {str(e)}")


@file_router.get("/scripts/{script_id}/cli_params", response_model=ScriptParametersResponse)
async def get_script_parameters(
    script_id: str,
    file_service: FileService = Depends(get_file_service)
) -> ScriptParametersResponse:
    """
    Get the configured script-level parameters.

    - **script_id**: Unique identifier of the script

    Returns the current parameter configuration.
    """
    logger.info(f"Getting script parameters for: {script_id}")

    try:
        return await file_service.get_script_parameters(script_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting parameters for {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get parameters: {str(e)}")


@file_router.post("/scripts/{script_id}/generate_cli_wrapper", response_model=CLIWrapperResponse)
async def generate_whole_file_cli_wrapper(
    script_id: str,
    wrapper_request: CLIWrapperRequest,
    file_service: FileService = Depends(get_file_service)
) -> CLIWrapperResponse:
    """
    Generate a single CLI wrapper for the entire Python file.

    - **script_id**: Unique identifier of the script
    - **wrapper_request**: Configuration for the CLI wrapper

    Returns information about the generated wrapper.
    """
    logger.info(f"Generating CLI wrapper for entire script: {script_id}")

    try:
        return await file_service.generate_whole_file_cli_wrapper(script_id, wrapper_request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating CLI wrapper for {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate CLI wrapper: {str(e)}")


@file_router.post("/scripts/{script_id}/generate_mcp_wrapper")
async def generate_mcp_wrapper(
    script_id: str,
    file_service: FileService = Depends(get_file_service)
) -> dict:
    """
    Generate an MCP-compatible wrapper for the script.

    - **script_id**: Unique identifier of the script

    Returns information about the generated MCP wrapper including paths to all generated files.
    """
    logger.info(f"Generating MCP wrapper for script: {script_id}")

    try:
        return await file_service.generate_mcp_wrapper(script_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating MCP wrapper for {script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate MCP wrapper: {str(e)}")
