# mcpy-lens API Reference

## Base URL
```
http://localhost:8090/api/v1
```

## Authentication
Currently, mcpy-lens operates without authentication for development purposes. Production deployments should implement appropriate authentication mechanisms.

## Response Format
All API responses follow a consistent JSON format:

### Success Response
```json
{
  "status": "success",
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "status": "error",
  "error": "Error description",
  "details": { ... }
}
```

## Script Management Endpoints

### Upload Script
Upload a new Python script to the system.

**Endpoint:** `POST /scripts/upload`

**Request:**
- Content-Type: `multipart/form-data`
- Body: File upload with key `file`

**Response:**
```json
{
  "script_id": "uuid-string",
  "filename": "script.py",
  "file_size": 1024,
  "upload_time": "2025-06-09T12:00:00Z",
  "validation_status": "passed",
  "security_status": "safe"
}
```

### List Scripts
Retrieve a list of all uploaded scripts.

**Endpoint:** `GET /scripts`

**Query Parameters:**
- `limit` (optional): Maximum number of scripts to return (default: 100)
- `offset` (optional): Number of scripts to skip (default: 0)

**Response:**
```json
{
  "scripts": [
    {
      "script_id": "uuid-string",
      "filename": "script.py",
      "functions": [
        {
          "name": "function_name",
          "description": "Function description",
          "parameters": {"param1": "type1"},
          "return_type": "return_type",
          "line_number": 10
        }
      ],
      "file_size": 1024,
      "upload_time": "2025-06-09T12:00:00Z",
      "validation_status": "passed",
      "security_status": "safe"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### Get Script Details
Retrieve detailed information about a specific script.

**Endpoint:** `GET /scripts/{script_id}`

**Path Parameters:**
- `script_id`: Unique identifier of the script

**Response:**
```json
{
  "script_id": "uuid-string",
  "filename": "script.py",
  "content": "# Python script content...",
  "functions": [...],
  "imports": ["os", "sys"],
  "dependencies": ["requests"],
  "file_size": 1024,
  "upload_time": "2025-06-09T12:00:00Z",
  "validation_status": "passed",
  "security_status": "safe"
}
```

### Discover Functions
Analyze a script and discover callable functions.

**Endpoint:** `GET /scripts/{script_id}/discover`

**Path Parameters:**
- `script_id`: Unique identifier of the script

**Response:**
```json
{
  "file_id": "uuid-string",
  "tools": [
    {
      "name": "function_name",
      "description": "Function description from docstring",
      "parameters": {
        "type": "object",
        "properties": {
          "param1": {
            "type": "string",
            "description": "Parameter description"
          }
        },
        "required": ["param1"]
      },
      "return_type": "string"
    }
  ],
  "total": 1,
  "discovery_time": "2025-06-09T12:00:00Z"
}
```

### Delete Script
Remove a script from the system.

**Endpoint:** `DELETE /scripts/{script_id}`

**Path Parameters:**
- `script_id`: Unique identifier of the script

**Response:**
```json
{
  "message": "Script deleted successfully",
  "script_id": "uuid-string"
}
```

## Service Management Endpoints

### List Services
Retrieve all registered MCP services.

**Endpoint:** `GET /services`

**Response:**
```json
{
  "services": [
    {
      "service_id": "uuid-string",
      "name": "service_name",
      "description": "Service description",
      "type": "function",
      "status": "active",
      "script_id": "uuid-string",
      "tools": [...],
      "created_at": "2025-06-09T12:00:00Z",
      "updated_at": "2025-06-09T12:00:00Z"
    }
  ],
  "total": 1
}
```

### Create Service
Register a new MCP service.

**Endpoint:** `POST /services`

**Request Body:**
```json
{
  "name": "service_name",
  "description": "Service description",
  "script_id": "uuid-string",
  "type": "function",
  "hosting_mode": "sse",
  "selected_functions": ["function1", "function2"],
  "parameters": {
    "custom_param": "value"
  }
}
```

**Response:**
```json
{
  "service_id": "uuid-string",
  "name": "service_name",
  "status": "active",
  "created_at": "2025-06-09T12:00:00Z"
}
```

### Get Service Details
Retrieve detailed information about a specific service.

**Endpoint:** `GET /services/{service_id}`

**Path Parameters:**
- `service_id`: Unique identifier of the service

**Response:**
```json
{
  "service_id": "uuid-string",
  "name": "service_name",
  "description": "Service description",
  "type": "function",
  "status": "active",
  "script_id": "uuid-string",
  "tools": [...],
  "configuration": {...},
  "created_at": "2025-06-09T12:00:00Z",
  "updated_at": "2025-06-09T12:00:00Z"
}
```

### Update Service
Update an existing service configuration.

**Endpoint:** `PUT /services/{service_id}`

**Path Parameters:**
- `service_id`: Unique identifier of the service

**Request Body:**
```json
{
  "name": "updated_service_name",
  "description": "Updated description",
  "selected_functions": ["function1"]
}
```

**Response:**
```json
{
  "service_id": "uuid-string",
  "message": "Service updated successfully",
  "updated_at": "2025-06-09T12:00:00Z"
}
```

### Delete Service
Remove a service from the registry.

**Endpoint:** `DELETE /services/{service_id}`

**Path Parameters:**
- `service_id`: Unique identifier of the service

**Response:**
```json
{
  "message": "Service deleted successfully",
  "service_id": "uuid-string"
}
```

### Get Service Health
Check the health status of a specific service.

**Endpoint:** `GET /services/{service_id}/health`

**Path Parameters:**
- `service_id`: Unique identifier of the service

**Response:**
```json
{
  "service_id": "uuid-string",
  "status": "healthy",
  "last_check": "2025-06-09T12:00:00Z",
  "response_time": 150,
  "details": {
    "process_id": 1234,
    "memory_usage": "45MB",
    "cpu_usage": "2.5%"
  }
}
```

## System Health Endpoints

### System Health Check
Get overall system health status.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-09T12:00:00Z",
  "version": "1.0.0",
  "uptime": 3600,
  "services": {
    "total": 5,
    "healthy": 4,
    "unhealthy": 1
  }
}
```

### Detailed Health Information
Get comprehensive system health information.

**Endpoint:** `GET /health/detailed`

**Response:**
```json
{
  "system": {
    "status": "healthy",
    "uptime": 3600,
    "memory_usage": "256MB",
    "disk_usage": "45%"
  },
  "services": [...],
  "database": {
    "status": "connected",
    "response_time": 5
  },
  "external_dependencies": [...]
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400  | Bad Request - Invalid input parameters |
| 404  | Not Found - Resource does not exist |
| 409  | Conflict - Resource already exists |
| 422  | Unprocessable Entity - Validation error |
| 500  | Internal Server Error - Server-side error |

## Rate Limiting
Currently, no rate limiting is implemented. Production deployments should implement appropriate rate limiting based on requirements.

## WebSocket Endpoints (Future)
Real-time features will be implemented using WebSocket connections:

- `/ws/services/{service_id}/logs` - Real-time service logs
- `/ws/health` - Real-time health monitoring
- `/ws/notifications` - System notifications

## SDK and Client Libraries
Official client libraries are planned for:
- Python SDK
- JavaScript/TypeScript SDK
- CLI client

For now, use standard HTTP clients to interact with the API.
