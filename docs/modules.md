# mcpy-lens Module Design

## Module Overview

mcpy-lens is organized into distinct modules, each with specific responsibilities and clear interfaces. This modular design promotes code reusability, testability, and maintainability.

## Core Modules

### 1. Discovery Module (`src/mcpy_lens/discovery.py`)

**Purpose**: Analyze Python scripts and extract callable functions with their metadata.

#### Key Components
- `discover_py_files()`: Find Python files in directories
- `discover_functions()`: Extract functions from Python modules
- `generate_schema_for_function()`: Create JSON schemas for functions
- `_type_to_json_schema_type()`: Convert Python types to JSON schema types

#### Key Features
- **AST-based Analysis**: Safe parsing without code execution
- **Type Hint Support**: Extract and convert Python type hints
- **Docstring Parsing**: Extract function descriptions and documentation
- **Schema Generation**: Automatic JSON schema creation for MCP compatibility

#### Example Usage
```python
from mcpy_lens.discovery import discover_functions, generate_schema_for_function

# Discover functions in a script
files = discover_py_files("path/to/script.py")
functions = discover_functions(files)

# Generate schema for a function
for func, name, path in functions:
    schema = generate_schema_for_function(func)
    print(f"Function: {name}, Schema: {schema}")
```

### 2. Service Registry Module (`src/mcpy_lens/service_registry/`)

**Purpose**: Manage MCP service lifecycle, registration, and health monitoring.

#### Sub-modules

##### ServiceRegistry (`service_registry.py`)
- **Purpose**: Central catalog of all registered services
- **Key Methods**:
  - `register_service()`: Register new services
  - `get_service()`: Retrieve service information
  - `list_services()`: Get all registered services
  - `unregister_service()`: Remove services

##### ServiceManager (`service_manager.py`)
- **Purpose**: Service lifecycle management and process control
- **Key Methods**:
  - `start_service()`: Launch service processes
  - `stop_service()`: Gracefully stop services
  - `restart_service()`: Restart services
  - `get_service_status()`: Check service status

##### HealthMonitor (`health_monitor.py`)
- **Purpose**: Continuous monitoring of service health
- **Key Methods**:
  - `start_monitoring()`: Begin health checks
  - `check_service_health()`: Perform health checks
  - `get_health_status()`: Retrieve health information
  - `handle_service_failure()`: Respond to failures

#### Data Models (`models.py`)
```python
@dataclass
class ServiceInfo:
    service_id: str
    name: str
    description: str
    type: ServiceType
    status: ServiceStatus
    tools: List[ToolInfo]
    created_at: datetime
    updated_at: datetime

@dataclass
class ToolInfo:
    name: str
    description: str
    parameters: Dict[str, Any]
    return_type: str
```

### 3. File Management Module (`src/mcpy_lens/file_service.py`)

**Purpose**: Handle script uploads, storage, validation, and metadata management.

#### Key Components
- **FileService Class**: Main service for file operations
- **Script Validation**: Security and syntax checking
- **Metadata Management**: Store and retrieve script information
- **Wrapper Generation**: Create CLI wrappers for functions

#### Key Methods
```python
class FileService:
    async def upload_script(self, file_data: bytes, filename: str) -> Dict[str, Any]
    async def get_script(self, script_id: str) -> ScriptMetadata
    async def list_scripts(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]
    async def delete_script(self, script_id: str) -> Dict[str, Any]
    async def discover_tools_from_file(self, script_id: str) -> ToolDiscoveryResponse
    async def generate_tool_wrapper(self, script_id: str, function_name: str) -> Dict[str, Any]
```

#### Storage Organization
```
data/
├── uploaded_scripts/
│   └── YYYY-MM-DD/
│       └── {script_id}.py
├── metadata/
│   ├── scripts_metadata.json
│   └── function_selections.json
├── wrappers/
│   └── {script_id}_{function_name}_wrapper.py
└── services/
    └── {script_id}_service.json
```

### 4. API Module (`src/mcpy_lens/api/`)

**Purpose**: FastAPI-based REST API providing all backend functionality.

#### Route Modules

##### File Routes (`file_routes.py`)
- `POST /api/v1/upload_script`: Upload new Python scripts
- `GET /api/v1/scripts`: List uploaded scripts
- `GET /api/v1/scripts/{script_id}`: Get script details
- `GET /api/v1/scripts/{script_id}/discover`: Discover functions
- `DELETE /api/v1/scripts/{script_id}`: Delete scripts

##### Service Routes (`service_routes.py`)
- `GET /api/v1/services`: List all services
- `POST /api/v1/services`: Create new service
- `GET /api/v1/services/{service_id}`: Get service details
- `PUT /api/v1/services/{service_id}`: Update service
- `DELETE /api/v1/services/{service_id}`: Delete service
- `GET /api/v1/services/{service_id}/health`: Service health

##### Health Routes (`health_routes.py`)
- `GET /health`: System health check
- `GET /api/v1/health/detailed`: Detailed health information

#### Middleware and Dependencies
- **CORS Middleware**: Enable cross-origin requests
- **Logging Middleware**: Request/response logging
- **Error Handling**: Global exception handling
- **Dependency Injection**: Service and configuration injection

### 5. Gradio App Module (`src/mcpy_lens/gradio_app/`)

**Purpose**: Modern web interface built with Gradio for user interactions.

#### Interface Modules

##### File Management (`interfaces/file_management.py`)
- **File Upload**: Drag-and-drop script upload
- **Script Preview**: Syntax-highlighted code display
- **Function Discovery**: Interactive function exploration
- **Metadata Display**: Script information and statistics

##### Service Configuration (`interfaces/service_config.py`)
- **Service Creation**: Visual service configuration
- **Parameter Validation**: Real-time input validation
- **Preview Mode**: Configuration preview before deployment
- **Template Support**: Pre-configured service templates

##### Service Management (`interfaces/service_management.py`)
- **Service Dashboard**: Real-time service status
- **Control Panel**: Start/stop/restart services
- **Health Monitoring**: Visual health indicators
- **Log Viewer**: Service logs and debugging

##### Service Testing (`interfaces/service_testing.py`)
- **Interactive Testing**: Test services directly from UI
- **Parameter Input**: Dynamic form generation
- **Result Display**: Formatted response visualization
- **History Tracking**: Test execution history

#### Shared Components (`components/common.py`)
- **UI Components**: Reusable Gradio components
- **Styling**: Consistent visual design
- **Utilities**: Common helper functions
- **Error Handling**: User-friendly error displays

#### API Client (`api_client.py`)
```python
class APIClient:
    def __init__(self, base_url: str = "http://localhost:8090")
    
    # File operations
    def upload_script(self, file_path: str) -> Dict[str, Any]
    def list_scripts(self, limit: int = 100) -> Dict[str, Any]
    def discover_tools(self, script_id: str) -> Dict[str, Any]
    
    # Service operations
    def create_service(self, config: Dict[str, Any]) -> Dict[str, Any]
    def list_services(self) -> Dict[str, Any]
    def get_service_health(self, service_id: str) -> Dict[str, Any]
```

### 6. Models Module (`src/mcpy_lens/models/`)

**Purpose**: Pydantic data models for validation and serialization.

#### Core Models
```python
class ScriptMetadata(BaseModel):
    script_id: str
    filename: str
    functions: List[FunctionInfo]
    imports: List[str]
    dependencies: List[str]
    file_size: int
    upload_time: datetime
    validation_status: str
    security_status: str

class ServiceConfig(BaseModel):
    name: str
    description: str
    script_id: str
    type: ServiceType
    hosting_mode: HostingMode
    selected_functions: Optional[List[str]]
    parameters: Optional[Dict[str, Any]]

class ToolDiscoveryResponse(BaseModel):
    file_id: str
    tools: List[ToolInfo]
    total: int
    discovery_time: datetime
```

## Module Dependencies

```
┌─────────────────┐
│   Gradio App    │
│   (Frontend)    │
└─────────┬───────┘
          │ HTTP API
          ▼
┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │◄──►│   File Service  │
│   (API Layer)   │    │                 │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│   Service       │    │   Discovery     │
│   Registry      │    │   Engine        │
└─────────────────┘    └─────────────────┘
          │                      │
          └──────────┬───────────┘
                     ▼
           ┌─────────────────┐
           │     Models      │
           │  (Data Layer)   │
           └─────────────────┘
```

## Configuration Management

### Settings Module (`src/mcpy_lens/config.py`)
```python
class Settings(BaseSettings):
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8090
    
    # Storage paths
    uploaded_scripts_dir: Path = Path("data/uploaded_scripts")
    wrappers_dir: Path = Path("data/wrappers")
    services_dir: Path = Path("data/services")
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[Path] = Path("data/logs/mcpy_lens.log")
    
    class Config:
        env_prefix = "MCPY_LENS_"
        env_file = ".env"
```

## Testing Strategy

### Unit Tests
- **Module Isolation**: Each module tested independently
- **Mock Dependencies**: External dependencies mocked
- **Coverage**: Aim for >90% code coverage

### Integration Tests
- **API Testing**: Full API endpoint testing
- **Service Integration**: Service registry and manager integration
- **File Operations**: End-to-end file handling

### Frontend Tests
- **Playwright**: Browser automation for UI testing
- **Component Testing**: Individual Gradio component testing
- **User Workflows**: Complete user journey testing

This modular design ensures that mcpy-lens remains maintainable, testable, and extensible as it grows and evolves.
