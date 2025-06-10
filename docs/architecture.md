# mcpy-lens Architecture Overview

## System Architecture

mcpy-lens follows a modern, modular architecture designed for scalability, maintainability, and extensibility. The system is built around the principle of separation of concerns, with distinct layers for presentation, business logic, and data management.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        mcpy-lens Platform                        │
├─────────────────────────────────────────────────────────────────┤
│                     Presentation Layer                          │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   Gradio Web    │    │   CLI Tools     │                    │
│  │   Interface     │    │   & Scripts     │                    │
│  │   (Port 7860)   │    │                 │                    │
│  └─────────────────┘    └─────────────────┘                    │
├─────────────────────────────────────────────────────────────────┤
│                      API Gateway Layer                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              FastAPI Backend (Port 8090)                    │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │ │
│  │  │ File Routes │ │Service Routes│ │Health Routes│          │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘          │ │
│  └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     Business Logic Layer                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │   Discovery     │ │   Service       │ │   File          │   │
│  │   Engine        │ │   Registry      │ │   Management    │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                      Data Layer                                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │   File System  │ │   JSON Storage  │ │   Runtime       │   │
│  │   Storage       │ │   (Metadata)    │ │   Memory        │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Presentation Layer

#### Gradio Web Interface (`src/mcpy_lens/gradio_app/`)
- **Purpose**: Modern, user-friendly web interface for all operations
- **Technology**: Gradio 5.x with custom styling and components
- **Key Features**:
  - File upload and management
  - Service configuration and deployment
  - Real-time monitoring dashboards
  - Interactive service testing
  - Responsive design with professional UI

#### CLI Tools
- **Purpose**: Command-line interface for automation and scripting
- **Technology**: Typer-based CLI wrappers
- **Key Features**:
  - Batch operations
  - CI/CD integration
  - Automated service deployment

### 2. API Gateway Layer

#### FastAPI Backend (`src/mcpy_lens/api/`)
- **Purpose**: RESTful API server providing all backend functionality
- **Technology**: FastAPI with async/await support
- **Port**: 8090 (configurable)
- **Key Features**:
  - OpenAPI/Swagger documentation
  - Automatic request/response validation
  - Async request handling
  - CORS support for web interface

#### Route Organization
```
/api/v1/
├── /scripts/              # Script management
│   ├── POST /upload       # Upload new scripts
│   ├── GET /              # List scripts
│   ├── GET /{id}          # Get script details
│   ├── GET /{id}/discover # Discover functions
│   └── DELETE /{id}       # Delete script
├── /services/             # Service management
│   ├── GET /              # List services
│   ├── POST /             # Create service
│   ├── GET /{id}          # Get service details
│   ├── PUT /{id}          # Update service
│   ├── DELETE /{id}       # Delete service
│   └── GET /{id}/health   # Service health
└── /health                # System health
```

### 3. Business Logic Layer

#### Discovery Engine (`src/mcpy_lens/discovery.py`)
- **Purpose**: Analyze Python scripts and extract callable functions
- **Technology**: AST (Abstract Syntax Tree) parsing
- **Key Features**:
  - Function signature analysis
  - Type hint extraction
  - Docstring parsing
  - JSON schema generation
  - Security validation

#### Service Registry (`src/mcpy_lens/service_registry/`)
- **Purpose**: Manage MCP service lifecycle and registration
- **Components**:
  - `ServiceRegistry`: Central service catalog
  - `ServiceManager`: Service lifecycle management
  - `HealthMonitor`: Continuous health monitoring
- **Key Features**:
  - Dynamic service registration
  - Health monitoring and alerting
  - Service discovery
  - Load balancing support

#### File Management (`src/mcpy_lens/file_service.py`)
- **Purpose**: Handle script uploads, storage, and metadata management
- **Key Features**:
  - Secure file upload handling
  - Metadata extraction and storage
  - File validation and security checks
  - Automatic backup and versioning

### 4. Data Layer

#### File System Storage
- **Scripts**: `data/uploaded_scripts/` (organized by date)
- **Wrappers**: `data/wrappers/` (generated CLI wrappers)
- **Services**: `data/services/` (service configurations)
- **Logs**: `data/logs/` (application and access logs)

#### JSON Storage
- **Metadata**: Script and service metadata in JSON format
- **Configuration**: Service configurations and parameters
- **State**: Runtime state and health information

## Data Flow

### 1. Script Upload Flow
```
User Upload → Gradio Interface → FastAPI → File Service → 
Discovery Engine → Metadata Storage → Response
```

### 2. Service Creation Flow
```
Service Config → Gradio Interface → FastAPI → Service Registry → 
Wrapper Generation → Service Deployment → Health Monitoring
```

### 3. Function Discovery Flow
```
Script Selection → Discovery Engine → AST Analysis → 
Schema Generation → Function Metadata → Frontend Display
```

## Security Architecture

### Input Validation
- **File Upload**: Type validation, size limits, content scanning
- **Script Analysis**: Safe AST parsing without code execution
- **Parameter Validation**: Pydantic models for all inputs

### Isolation
- **Process Isolation**: Services run in separate processes
- **File System**: Sandboxed storage with proper permissions
- **Network**: Configurable ports and access controls

### Monitoring
- **Health Checks**: Continuous service monitoring
- **Logging**: Comprehensive audit trails
- **Error Handling**: Graceful degradation and recovery

## Scalability Considerations

### Horizontal Scaling
- **Stateless Design**: API servers can be load-balanced
- **Service Distribution**: Services can run on different hosts
- **Database Abstraction**: Ready for database backend migration

### Performance Optimization
- **Async Operations**: Non-blocking I/O throughout the stack
- **Caching**: Metadata and discovery results caching
- **Lazy Loading**: On-demand service initialization

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server for production deployment
- **aiofiles**: Async file operations

### Frontend
- **Gradio**: Rapid UI development framework
- **httpx**: Modern HTTP client for API communication
- **Pandas**: Data manipulation for tables and displays

### Development & Testing
- **Pytest**: Testing framework
- **Playwright**: End-to-end testing
- **Black**: Code formatting
- **mypy**: Static type checking

## Deployment Architecture

### Development
```
Local Machine:
├── FastAPI Backend (localhost:8090)
├── Gradio Frontend (localhost:7860)
└── File Storage (./data/)
```

### Production
```
Server Environment:
├── Reverse Proxy (nginx/traefik)
├── FastAPI Backend (multiple instances)
├── Gradio Frontend (load balanced)
├── Shared Storage (NFS/S3)
└── Monitoring (Prometheus/Grafana)
```

This architecture provides a solid foundation for the mcpy-lens platform, ensuring scalability, maintainability, and extensibility while delivering a superior user experience through modern web technologies.
