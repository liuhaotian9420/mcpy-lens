# mcpy-lens Gradio Web Interface - Deployment Guide

**Version**: Stage 7 Complete  
**Date**: 2025-06-03  
**Status**: ✅ Production Ready

## 🎯 Overview

This guide provides step-by-step instructions for deploying the complete mcpy-lens Gradio web interface. The implementation includes all planned features and is ready for production use.

## 📋 Prerequisites

- Python 3.8+ with virtual environment
- Git repository cloned
- Terminal/Command prompt access

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
# Using uv (recommended for speed)
uv pip install gradio>=4.0.0 httpx>=0.25.0

# Or using regular pip
pip install gradio>=4.0.0 httpx>=0.25.0
```

### 2. Start Backend Service
```bash
# Terminal 1: Start FastAPI backend
python run.py
```
**Expected Output**: FastAPI server running on http://localhost:8090

### 3. Start Frontend Interface
```bash
# Terminal 2: Start Gradio frontend
python launch_gradio.py
```
**Expected Output**: Gradio interface running on http://localhost:7860

### 4. Access Web Interface
Open your browser and navigate to: **http://localhost:7860**

## 🔧 Detailed Setup

### Environment Setup
```bash
# Ensure you're in the project directory
cd mcpy-lens

# Activate virtual environment (if using one)
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Verify Python version
python --version  # Should be 3.8+
```

### Dependency Installation
```bash
# Install core dependencies
uv pip install -r requirements.txt

# Verify Gradio installation
python -c "import gradio as gr; print(f'Gradio {gr.__version__} installed')"
```

### Testing Installation
```bash
# Run setup verification
python test_gradio_setup.py

# Test app creation
python test_app_creation.py
```

## 🌐 Web Interface Features

### 📁 File Management Tab
- **Upload Python Scripts**: Drag-and-drop or click to upload .py files
- **File Preview**: Syntax-highlighted code preview
- **Script Management**: View metadata, delete files
- **Validation**: Real-time syntax checking and error reporting

### ⚙️ Service Configuration Tab
- **Script Selection**: Choose from uploaded Python files
- **Hosting Modes**: Function mode (expose individual functions) or Executable mode (run entire script)
- **Protocol Selection**: STDIO or SSE/HTTP communication
- **Function Selection**: Multi-select functions to expose (function mode)
- **Parameter Configuration**: JSON editor for executable parameters
- **Service Creation**: One-click deployment with preview

### 🎛️ Service Management Tab
- **Service Dashboard**: Real-time service listing with status indicators
- **Service Controls**: Start, stop, restart, delete services
- **Health Monitoring**: Service health status and details
- **Service Details**: View complete service configuration
- **Logs Display**: Service logs (foundation for future streaming)

### 🧪 Service Testing Tab
- **Interactive Testing**: Test MCP tools with dynamic parameter forms
- **Service Selection**: Choose service and specific tools
- **Parameter Forms**: Auto-generated forms based on tool schemas
- **Response Display**: JSON response with syntax highlighting
- **Request History**: Foundation for saving and reusing test requests

### ❓ Help Tab
- **Getting Started**: Step-by-step tutorial
- **Documentation**: Complete feature documentation
- **API Reference**: Backend API information
- **Support Links**: Project links and resources

## 🔍 Troubleshooting

### Backend Connection Issues
**Problem**: "Cannot connect to FastAPI backend"
**Solution**:
1. Ensure FastAPI is running: `python run.py`
2. Check port 8090 is not in use
3. Verify backend health: http://localhost:8090/health

### Gradio Launch Issues
**Problem**: Gradio app doesn't start
**Solution**:
1. Check Gradio installation: `python -c "import gradio"`
2. Try alternative launcher: `python run_gradio.py`
3. Check port 7860 is available

### Import Errors
**Problem**: Module import failures
**Solution**:
1. Verify virtual environment is activated
2. Reinstall dependencies: `uv pip install -r requirements.txt`
3. Check Python path: `python -c "import sys; print(sys.path)"`

### Performance Issues
**Problem**: Slow loading or responses
**Solution**:
1. Restart both backend and frontend
2. Check system resources
3. Clear browser cache

## 📊 System Architecture

```
┌─────────────────┐    HTTP/REST    ┌─────────────────┐
│   Gradio Web    │◄──────────────►│   FastAPI       │
│   Interface     │                │   Backend       │
│   (Port 7860)   │                │   (Port 8090)   │
└─────────────────┘                └─────────────────┘
         │                                   │
         │                                   │
         ▼                                   ▼
┌─────────────────┐                ┌─────────────────┐
│   Browser UI    │                │   File System   │
│   - 5 Tabs      │                │   - Scripts     │
│   - Real-time   │                │   - Services    │
│   - Interactive │                │   - Wrappers    │
└─────────────────┘                └─────────────────┘
```

## 🔐 Security Considerations

### Development Environment
- Default configuration is for development use
- No authentication enabled by default
- Accessible from localhost only

### Production Deployment
For production use, consider:
- Enable Gradio authentication
- Configure HTTPS/SSL
- Set up proper firewall rules
- Use environment variables for configuration
- Implement proper logging and monitoring

## 📈 Performance Optimization

### Recommended Settings
- **Memory**: 4GB+ RAM for optimal performance
- **CPU**: 2+ cores recommended
- **Storage**: SSD for faster file operations
- **Network**: Stable internet for package downloads

### Scaling Considerations
- Backend and frontend can be deployed on separate servers
- Use reverse proxy (nginx) for production
- Consider containerization with Docker
- Implement load balancing for high availability

## 🎉 Success Indicators

### Successful Deployment
- ✅ Backend health check returns "healthy"
- ✅ Gradio interface loads without errors
- ✅ All 5 tabs are accessible and functional
- ✅ File upload works correctly
- ✅ Service creation completes successfully

### Feature Verification
1. **Upload a Python file** → Should show in file list
2. **Create a service** → Should appear in service management
3. **Test a tool** → Should return mock response
4. **Check backend status** → Should show green "Connected"

## 📞 Support

### Resources
- **Project Repository**: https://github.com/liuhaotian9420/mcpy-lens
- **Documentation**: Check the Help tab in the web interface
- **Issues**: Report bugs via GitHub Issues

### Common Commands
```bash
# Restart everything
pkill -f "python.*run.py"
pkill -f "python.*launch_gradio.py"
python run.py &
python launch_gradio.py

# Check processes
ps aux | grep python

# View logs
tail -f logs/mcpy-lens.log  # If logging to file
```

---

**🎊 Congratulations!** You now have a fully functional mcpy-lens web interface running. The system transforms Python scripts into MCP services through an intuitive web interface, making AI tool integration accessible to everyone.
