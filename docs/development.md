# mcpy-lens Development Guide

## Development Environment Setup

### Prerequisites
- Python 3.11 or higher
- Git
- Virtual environment tool (venv, conda, or virtualenv)
- Node.js (for frontend testing with Playwright)

### Initial Setup

1. **Clone the Repository**
```bash
git clone https://github.com/liuhaotian9420/mcpy-lens.git
cd mcpy-lens
```

2. **Create Virtual Environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install Dependencies**
```bash
# Using pip
pip install -r requirements.txt

# Using uv (recommended for faster installation)
uv pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

4. **Install Pre-commit Hooks**
```bash
pre-commit install
```

## Project Structure

```
mcpy-lens/
├── src/mcpy_lens/              # Main application code
│   ├── api/                    # FastAPI backend
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app creation
│   │   ├── file_routes.py     # File management endpoints
│   │   ├── service_routes.py  # Service management endpoints
│   │   └── health_routes.py   # Health check endpoints
│   ├── discovery.py           # Function discovery engine
│   ├── file_service.py        # File management service
│   ├── config.py              # Configuration management
│   ├── models.py              # Pydantic data models
│   ├── service_registry/      # Service management
│   │   ├── __init__.py
│   │   ├── service_registry.py
│   │   ├── service_manager.py
│   │   ├── health_monitor.py
│   │   └── models.py
│   └── gradio_app/           # Web interface
│       ├── __init__.py
│       ├── main.py           # Gradio app creation
│       ├── api_client.py     # Backend API client
│       ├── components/       # Reusable UI components
│       └── interfaces/       # Tab interfaces
├── tests/                    # Test suites
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── frontend/            # Frontend tests
├── docs/                    # Documentation
├── plans/                   # Development plans
├── data/                    # Runtime data (gitignored)
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
├── pyproject.toml          # Project configuration
└── README.md               # Project overview
```

## Development Workflow

### 1. Feature Development

1. **Create Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Implement Feature**
- Write code following the established patterns
- Add comprehensive tests
- Update documentation as needed

3. **Run Tests**
```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python run_frontend_tests.py
```

4. **Code Quality Checks**
```bash
# Format code
black src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/

# Security checks
bandit -r src/
```

5. **Commit and Push**
```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

### 2. Testing Strategy

#### Unit Tests
- **Location**: `tests/unit/`
- **Purpose**: Test individual functions and classes in isolation
- **Framework**: pytest
- **Coverage**: Aim for >90% code coverage

```python
# Example unit test
def test_discover_functions():
    script_content = """
def add(a: int, b: int) -> int:
    return a + b
"""
    # Test function discovery logic
    assert len(discovered_functions) == 1
    assert discovered_functions[0][1] == "add"
```

#### Integration Tests
- **Location**: `tests/integration/`
- **Purpose**: Test component interactions and API endpoints
- **Framework**: pytest with httpx for API testing

```python
# Example integration test
async def test_upload_and_discover_workflow():
    # Upload script
    response = await client.post("/api/v1/upload_script", files={"file": script_file})
    script_id = response.json()["script_id"]
    
    # Discover functions
    response = await client.get(f"/api/v1/scripts/{script_id}/discover")
    assert response.status_code == 200
    assert len(response.json()["tools"]) > 0
```

#### Frontend Tests
- **Location**: `tests/frontend/`
- **Purpose**: Test web interface functionality
- **Framework**: Playwright for browser automation

```python
# Example frontend test
def test_script_upload_workflow(page):
    page.goto("http://localhost:7860")
    page.click("text=File Management")
    page.set_input_files("input[type=file]", "test_script.py")
    page.click("text=Upload Script")
    expect(page.locator("text=✅")).to_be_visible()
```

### 3. Code Style and Standards

#### Python Code Style
- **Formatter**: Black (line length: 88)
- **Import Sorting**: isort
- **Type Hints**: Required for all public functions
- **Docstrings**: Google style for all public functions and classes

```python
def discover_functions(
    file_paths: List[Path],
    target_function_names: Optional[List[str]] = None
) -> List[Tuple[Callable[..., Any], str, Path]]:
    """Discover functions from a list of Python files.
    
    Args:
        file_paths: A list of paths to Python files.
        target_function_names: Optional list of specific function names to discover.
        
    Returns:
        A list of tuples: (function_object, function_name, file_path)
        
    Raises:
        ImportError: If a module cannot be imported.
        ValueError: If file_paths is empty.
    """
```

#### Frontend Code Style
- **Component Organization**: One component per file
- **Naming**: Descriptive function and variable names
- **Error Handling**: Comprehensive error handling with user-friendly messages

### 4. Debugging

#### Backend Debugging
```bash
# Run with debug logging
LOG_LEVEL=DEBUG python run.py

# Use debugger
python -m pdb run.py
```

#### Frontend Debugging
```bash
# Run with debug mode
python launch_gradio.py --debug

# Check browser console for JavaScript errors
# Use Gradio's built-in debugging features
```

#### Common Issues and Solutions

1. **Function Discovery Not Working**
   - Check module import paths
   - Verify Python syntax is valid
   - Ensure functions are not private (starting with _)

2. **Service Registration Failures**
   - Check service configuration format
   - Verify script exists and is accessible
   - Check service registry logs

3. **Frontend API Connection Issues**
   - Ensure backend is running on correct port
   - Check CORS configuration
   - Verify API client base URL

### 5. Performance Optimization

#### Backend Performance
- Use async/await for I/O operations
- Implement caching for expensive operations
- Profile code with cProfile for bottlenecks

#### Frontend Performance
- Lazy load components when possible
- Optimize API calls (batch requests)
- Use Gradio's built-in caching features

### 6. Database Migrations (Future)

When database support is added:

```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### 7. Release Process

1. **Version Bump**
```bash
# Update version in pyproject.toml
# Create changelog entry
```

2. **Create Release Branch**
```bash
git checkout -b release/v1.0.0
```

3. **Final Testing**
```bash
# Run full test suite
python -m pytest
python run_frontend_tests.py

# Manual testing checklist
# - Upload script workflow
# - Service creation workflow
# - Health monitoring
# - Error handling
```

4. **Tag and Release**
```bash
git tag v1.0.0
git push origin v1.0.0
```

### 8. Contributing Guidelines

#### Pull Request Process
1. Fork the repository
2. Create feature branch from main
3. Implement changes with tests
4. Ensure all tests pass
5. Update documentation
6. Submit pull request with clear description

#### Code Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests are comprehensive and pass
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Backward compatibility maintained

### 9. Development Tools

#### Recommended IDE Setup
- **VS Code** with extensions:
  - Python
  - Pylance
  - Black Formatter
  - GitLens
  - REST Client

#### Useful Commands
```bash
# Quick development server restart
make restart

# Run specific test file
python -m pytest tests/unit/test_discovery.py -v

# Generate test coverage report
python -m pytest --cov=src/mcpy_lens --cov-report=html

# Profile application performance
python -m cProfile -o profile.stats run.py
```

This development guide provides a comprehensive foundation for contributing to mcpy-lens. Follow these guidelines to ensure consistent, high-quality code and smooth collaboration.
