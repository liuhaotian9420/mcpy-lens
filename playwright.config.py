"""Playwright configuration for mcpy-lens frontend testing."""

import os
from pathlib import Path
from playwright.sync_api import Playwright, Browser, BrowserContext, Page
import pytest

# Test configuration
BASE_URL = "http://localhost:7860"  # Gradio default port
API_BASE_URL = "http://localhost:8090"  # FastAPI backend port
TIMEOUT = 30000  # 30 seconds default timeout
SLOW_TIMEOUT = 60000  # 60 seconds for slow operations

# Browser configuration
BROWSERS = ["chromium", "firefox", "webkit"]
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("PLAYWRIGHT_SLOW_MO", "0"))

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "tests" / "test_data"
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Playwright configuration
def pytest_configure(config):
    """Configure pytest for Playwright testing."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "frontend: marks tests as frontend/UI tests"
    )

@pytest.fixture(scope="session")
def browser_context_args():
    """Configure browser context arguments."""
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
        "record_video_dir": "test-results/videos" if not HEADLESS else None,
        "record_video_size": {"width": 1280, "height": 720},
    }

@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Configure browser launch arguments."""
    return {
        "headless": HEADLESS,
        "slow_mo": SLOW_MO,
        "args": [
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
        ] if not HEADLESS else [],
    }

# Test utilities
class GradioTestHelper:
    """Helper class for Gradio-specific testing operations."""
    
    def __init__(self, page: Page):
        self.page = page
        self.base_url = BASE_URL
        
    def wait_for_gradio_load(self, timeout: int = TIMEOUT):
        """Wait for Gradio interface to fully load."""
        # Wait for the main Gradio container
        self.page.wait_for_selector(".gradio-container", timeout=timeout)
        # Wait for any loading spinners to disappear
        self.page.wait_for_function(
            "() => !document.querySelector('.loading')",
            timeout=timeout
        )
        
    def click_tab(self, tab_name: str):
        """Click on a specific tab in the Gradio interface."""
        tab_selector = f"button:has-text('{tab_name}')"
        self.page.click(tab_selector)
        self.page.wait_for_timeout(1000)  # Wait for tab content to load
        
    def upload_file(self, file_path: str, input_selector: str = "input[type='file']"):
        """Upload a file using Gradio file input."""
        self.page.set_input_files(input_selector, file_path)
        self.page.wait_for_timeout(2000)  # Wait for upload to process
        
    def wait_for_success_message(self, timeout: int = TIMEOUT):
        """Wait for a success message to appear."""
        self.page.wait_for_selector(".success, .gr-success", timeout=timeout)
        
    def wait_for_error_message(self, timeout: int = TIMEOUT):
        """Wait for an error message to appear."""
        self.page.wait_for_selector(".error, .gr-error", timeout=timeout)
        
    def get_table_data(self, table_selector: str = ".dataframe"):
        """Extract data from a Gradio DataFrame component."""
        table = self.page.query_selector(table_selector)
        if not table:
            return []
            
        rows = table.query_selector_all("tr")
        data = []
        for row in rows:
            cells = row.query_selector_all("td, th")
            row_data = [cell.inner_text() for cell in cells]
            if row_data:
                data.append(row_data)
        return data
        
    def fill_form_field(self, label: str, value: str):
        """Fill a form field by its label."""
        # Try different selectors for Gradio form fields
        selectors = [
            f"label:has-text('{label}') + input",
            f"label:has-text('{label}') + textarea",
            f"input[placeholder*='{label}']",
            f"textarea[placeholder*='{label}']",
        ]
        
        for selector in selectors:
            element = self.page.query_selector(selector)
            if element:
                element.fill(value)
                return
                
        raise ValueError(f"Could not find form field with label: {label}")
        
    def select_dropdown_option(self, dropdown_label: str, option: str):
        """Select an option from a Gradio dropdown."""
        # Click the dropdown
        dropdown_selector = f"label:has-text('{dropdown_label}') + .dropdown"
        self.page.click(dropdown_selector)
        
        # Select the option
        option_selector = f".dropdown-option:has-text('{option}')"
        self.page.click(option_selector)
        
    def click_button(self, button_text: str):
        """Click a button by its text."""
        button_selector = f"button:has-text('{button_text}')"
        self.page.click(button_selector)
        self.page.wait_for_timeout(1000)  # Wait for action to process

@pytest.fixture
def gradio_helper(page: Page):
    """Provide a GradioTestHelper instance."""
    return GradioTestHelper(page)

# Test data fixtures
@pytest.fixture
def sample_python_file():
    """Create a sample Python file for testing."""
    content = '''#!/usr/bin/env python3
"""Sample Python script for testing."""

def hello(name: str = "World") -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

if __name__ == "__main__":
    print(hello())
    print(add_numbers(2, 3))
'''
    
    file_path = TEST_DATA_DIR / "sample_script.py"
    file_path.write_text(content)
    return str(file_path)

@pytest.fixture
def complex_python_file():
    """Create a more complex Python file for testing."""
    content = '''#!/usr/bin/env python3
"""Complex Python script with multiple functions and parameters."""

import json
import sys
from typing import List, Dict, Optional

def process_data(data: List[Dict], filter_key: str = "active") -> List[Dict]:
    """Process a list of data dictionaries."""
    return [item for item in data if item.get(filter_key, False)]

def calculate_stats(numbers: List[float]) -> Dict[str, float]:
    """Calculate basic statistics for a list of numbers."""
    if not numbers:
        return {}
    
    return {
        "mean": sum(numbers) / len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "count": len(numbers)
    }

def main():
    """Main function for CLI execution."""
    if len(sys.argv) > 1:
        data = json.loads(sys.argv[1])
        result = process_data(data)
        print(json.dumps(result))
    else:
        print("Usage: python script.py '<json_data>'")

if __name__ == "__main__":
    main()
'''
    
    file_path = TEST_DATA_DIR / "complex_script.py"
    file_path.write_text(content)
    return str(file_path)
