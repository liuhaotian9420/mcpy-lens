#!/usr/bin/env python3
"""
Test script to verify Stage 3 implementation is complete and working.
"""

import requests
import json
import tempfile
import os
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8090/api/v1"

def create_test_script():
    """Create a simple test Python script."""
    test_script_content = '''#!/usr/bin/env python3
"""Test script for mcpy-lens Stage 3 functionality."""

def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

def multiply_numbers(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y

def greet_user(name: str, greeting: str = "Hello") -> str:
    """Greet a user with a custom greeting."""
    return f"{greeting}, {name}!"

if __name__ == "__main__":
    print("This is a test script")
    result = add_numbers(5, 3)
    print(f"5 + 3 = {result}")
'''
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script_content)
        return f.name

def test_stage3_functionality():
    """Test all Stage 3 functionality."""
    print("🧪 Testing Stage 3 Implementation...")
    
    # Step 1: Upload a test script
    print("\n1. Uploading test script...")
    test_file_path = create_test_script()
    
    try:
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test_script.py', f, 'text/x-python')}
            response = requests.post(f"{BASE_URL}/upload_script", files=files)
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return False
        
        upload_result = response.json()
        script_id = upload_result['script_id']
        print(f"✅ Script uploaded successfully: {script_id}")
        
        # Step 2: Discover tools
        print("\n2. Discovering tools...")
        response = requests.get(f"{BASE_URL}/scripts/{script_id}/discover")
        if response.status_code != 200:
            print(f"❌ Tool discovery failed: {response.status_code}")
            return False
        
        discovery_result = response.json()
        print(f"✅ Discovered {len(discovery_result['tools'])} tools")
        
        # Step 3: Validate entry point
        print("\n3. Validating entry point...")
        response = requests.get(f"{BASE_URL}/scripts/{script_id}/validate_entry_point")
        if response.status_code != 200:
            print(f"❌ Entry point validation failed: {response.status_code}")
            return False
        
        validation_result = response.json()
        print(f"✅ Entry point validation: has_entry_point={validation_result['has_entry_point']}")
        
        # Step 4: Select functions for tools (NEW)
        print("\n4. Selecting functions for tools...")
        selection_data = {
            "selected_functions": ["add_numbers", "greet_user"],
            "metadata": {"selection_reason": "test"}
        }
        response = requests.post(
            f"{BASE_URL}/scripts/{script_id}/functions/select",
            json=selection_data
        )
        if response.status_code != 200:
            print(f"❌ Function selection failed: {response.status_code} - {response.text}")
            return False
        
        selection_result = response.json()
        print(f"✅ Selected {len(selection_result['selected_functions'])} functions")
        
        # Step 5: Get selected functions (NEW)
        print("\n5. Getting selected functions...")
        response = requests.get(f"{BASE_URL}/scripts/{script_id}/functions/selected")
        if response.status_code != 200:
            print(f"❌ Get selected functions failed: {response.status_code}")
            return False
        
        selected_result = response.json()
        print(f"✅ Retrieved {len(selected_result['selected_functions'])} selected functions")
        
        # Step 6: Configure script parameters (NEW)
        print("\n6. Configuring script parameters...")
        params_data = {
            "parameters": [
                {
                    "name": "verbose",
                    "type": "bool",
                    "description": "Enable verbose output",
                    "required": False,
                    "default_value": False
                },
                {
                    "name": "output_file",
                    "type": "str",
                    "description": "Output file path",
                    "required": True
                }
            ]
        }
        response = requests.post(
            f"{BASE_URL}/scripts/{script_id}/cli_params",
            json=params_data
        )
        if response.status_code != 200:
            print(f"❌ Script parameters configuration failed: {response.status_code} - {response.text}")
            return False
        
        params_result = response.json()
        print(f"✅ Configured {len(params_result['parameters'])} script parameters")
        
        # Step 7: Get script parameters (NEW)
        print("\n7. Getting script parameters...")
        response = requests.get(f"{BASE_URL}/scripts/{script_id}/cli_params")
        if response.status_code != 200:
            print(f"❌ Get script parameters failed: {response.status_code}")
            return False
        
        get_params_result = response.json()
        print(f"✅ Retrieved {len(get_params_result['parameters'])} script parameters")
        
        # Step 8: Generate whole-file CLI wrapper (NEW)
        print("\n8. Generating whole-file CLI wrapper...")
        wrapper_data = {
            "wrapper_name": "test_wrapper",
            "description": "Test CLI wrapper for the entire script"
        }
        response = requests.post(
            f"{BASE_URL}/scripts/{script_id}/generate_cli_wrapper",
            json=wrapper_data
        )
        if response.status_code != 200:
            print(f"❌ CLI wrapper generation failed: {response.status_code} - {response.text}")
            return False
        
        wrapper_result = response.json()
        print(f"✅ Generated CLI wrapper: {wrapper_result['wrapper_name']}")
        
        print("\n🎉 All Stage 3 functionality tests passed!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on port 8090.")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        # Clean up temporary file
        if os.path.exists(test_file_path):
            os.unlink(test_file_path)

if __name__ == "__main__":
    success = test_stage3_functionality()
    exit(0 if success else 1)
