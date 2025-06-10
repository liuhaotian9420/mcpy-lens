# mcpy-lens 🔍

**Transform Python Scripts into MCP (Model Context Protocol) Services with a Modern Web Interface**

mcpy-lens is a comprehensive platform that bridges the gap between standalone Python scripts and the Model Context Protocol ecosystem. It provides both CLI and web-based tools to discover, wrap, and deploy Python functions as MCP services, making them accessible to AI assistants and other MCP-compatible applications.

## 🌟 Key Features

### 🎯 **Core Functionality**
- **Function Discovery**: Automatically analyze Python scripts and discover callable functions
- **MCP Service Generation**: Convert Python functions into MCP-compatible services
- **Dynamic Service Management**: Register, monitor, and manage services in real-time
- **Multiple Hosting Modes**: Support for both function-level and script-level service deployment

### 🖥️ **Modern Web Interface**
- **Gradio-based UI**: Professional, responsive web interface for all operations
- **File Management**: Upload, preview, and manage Python scripts
- **Service Configuration**: Visual service creation with parameter validation
- **Real-time Monitoring**: Live service status and health monitoring
- **Interactive Testing**: Test services and tools directly from the web interface

### 🔧 **Advanced Features**
- **Automatic Wrapper Generation**: Create CLI wrappers using Typer for seamless integration
- **Schema Generation**: Automatic JSON schema generation for function parameters
- **Health Monitoring**: Continuous service health checks and status reporting
- **Flexible Deployment**: Support for SSE and HTTP protocols
- **Security Validation**: Built-in security checks for uploaded scripts

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/liuhaotian9420/mcpy-lens.git
cd mcpy-lens

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# or using uv (faster)
uv pip install -r requirements.txt
```

### Launch the Application

```bash
# Start the FastAPI backend
python run.py

# In a new terminal, start the Gradio frontend
python launch_gradio.py
```

Access the web interface at: **http://localhost:7860**

## 📖 Usage

### 1. Upload Python Scripts
- Navigate to the **File Management** tab
- Upload your Python scripts (.py files)
- Preview and validate script content
- View discovered functions automatically

### 2. Create MCP Services
- Go to the **Service Configuration** tab
- Select an uploaded script
- Choose hosting mode (function-level or executable)
- Configure service parameters
- Deploy the service

### 3. Monitor Services
- Use the **Service Management** tab
- View real-time service status
- Start, stop, or restart services
- Monitor service health and logs

### 4. Test Services
- Access the **Service Testing** tab
- Select services and tools to test
- Input parameters and execute functions
- View results and debug issues

## 🏗️ Architecture

mcpy-lens follows a modular, microservices-inspired architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gradio Web    │    │   FastAPI       │    │   Service       │
│   Interface     │◄──►│   Backend       │◄──►│   Registry      │
│   (Port 7860)   │    │   (Port 8090)   │    │   & Manager     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   File Upload   │    │   Discovery     │    │   MCP Service   │
│   & Management  │    │   Engine        │    │   Instances     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

- **Discovery Engine**: AST-based Python function analysis and schema generation
- **Service Registry**: Dynamic service registration and lifecycle management
- **Health Monitor**: Continuous service monitoring and status reporting
- **Wrapper Generator**: Automatic CLI wrapper creation using Typer
- **Web Interface**: Modern Gradio-based frontend for all operations

## 📁 Project Structure

```
mcpy-lens/
├── src/mcpy_lens/              # Core application code
│   ├── api/                    # FastAPI backend
│   ├── discovery/              # Function discovery engine
│   ├── service_registry/       # Service management
│   ├── gradio_app/            # Web interface
│   └── models/                # Data models
├── docs/                      # Documentation
├── plans/                     # Development plans
├── tests/                     # Test suites
├── data/                      # Runtime data
│   ├── uploaded_scripts/      # User scripts
│   ├── services/             # Service configurations
│   ├── wrappers/             # Generated wrappers
│   └── logs/                 # Application logs
└── requirements.txt          # Dependencies
```

## 🔧 Configuration

### Environment Variables
- `MCPY_LENS_HOST`: Backend host (default: 0.0.0.0)
- `MCPY_LENS_PORT`: Backend port (default: 8090)
- `GRADIO_SERVER_PORT`: Frontend port (default: 7860)
- `LOG_LEVEL`: Logging level (default: INFO)

### Configuration Files
- `pyproject.toml`: Project metadata and dependencies
- `config.yaml`: Application configuration (auto-generated)

## 🧪 Testing

### Run Backend Tests
```bash
python -m pytest tests/ -v
```

### Run Frontend Tests
```bash
python run_frontend_tests.py
```

### Manual Testing
```bash
# Test backend connectivity
python test_frontend_setup.py

# Test Gradio app creation
python test_app_creation.py
```

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [Module Design](docs/modules.md)
- [API Reference](docs/api.md)
- [Development Guide](docs/development.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) for the backend API
- [Gradio](https://gradio.app/) for the modern web interface
- [Typer](https://typer.tiangolo.com/) for CLI wrapper generation
- [Pydantic](https://pydantic.dev/) for data validation and settings management

---

**Made with ❤️ for the MCP ecosystem**