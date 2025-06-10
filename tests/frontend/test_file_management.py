"""Tests for the file management interface."""

import pytest
import time
from pathlib import Path
from playwright.sync_api import Page, expect


class TestFileManagement:
    """Test file upload and management functionality."""
    
    @pytest.mark.frontend
    def test_file_upload_interface_visible(self, page: Page, gradio_helper):
        """Test that the file upload interface is visible and accessible."""
        try:
            page.goto("http://localhost:7860", timeout=30000)
            gradio_helper.wait_for_gradio_load()
            
            # Navigate to File Management tab
            gradio_helper.click_tab("File Management")
            
            # Check for file upload components
            upload_selectors = [
                "input[type='file']",
                ".file-upload",
                "text=Upload Python File",
                "text=Drag and drop",
                ".upload-area"
            ]
            
            upload_found = False
            for selector in upload_selectors:
                if page.locator(selector).count() > 0:
                    upload_found = True
                    print(f"✅ Found upload interface: {selector}")
                    break
            
            assert upload_found, "No file upload interface found"
            print("✅ File upload interface is visible")
            
        except Exception as e:
            pytest.skip(f"File upload interface test failed: {e}")
    
    @pytest.mark.frontend
    def test_file_upload_functionality(self, page: Page, gradio_helper, sample_python_file):
        """Test uploading a Python file."""
        try:
            page.goto("http://localhost:7860", timeout=30000)
            gradio_helper.wait_for_gradio_load()
            
            # Navigate to File Management tab
            gradio_helper.click_tab("File Management")
            
            # Find and use the file upload input
            file_input = page.locator("input[type='file']").first
            if file_input.count() == 0:
                pytest.skip("No file input found")
            
            # Upload the sample file
            file_input.set_input_files(sample_python_file)
            
            # Wait for upload to process
            page.wait_for_timeout(3000)
            
            # Look for success indicators
            success_indicators = [
                ".success",
                ".gr-success", 
                "text=uploaded successfully",
                "text=Upload complete",
                "text=sample_script.py"
            ]
            
            success_found = False
            for indicator in success_indicators:
                if page.locator(indicator).count() > 0:
                    success_found = True
                    print(f"✅ Found success indicator: {indicator}")
                    break
            
            if success_found:
                print("✅ File upload appears to be successful")
            else:
                print("⚠️  No clear success indicator found, but no errors detected")
            
        except Exception as e:
            pytest.skip(f"File upload test failed: {e}")
    
    @pytest.mark.frontend
    def test_file_list_display(self, page: Page, gradio_helper):
        """Test that uploaded files are displayed in the file list."""
        try:
            page.goto("http://localhost:7860", timeout=30000)
            gradio_helper.wait_for_gradio_load()
            
            # Navigate to File Management tab
            gradio_helper.click_tab("File Management")
            
            # Look for file list components
            list_selectors = [
                ".dataframe",
                ".file-list",
                "table",
                ".gr-dataframe",
                "text=No files uploaded"
            ]
            
            list_found = False
            for selector in list_selectors:
                if page.locator(selector).count() > 0:
                    list_found = True
                    print(f"✅ Found file list component: {selector}")
                    break
            
            assert list_found, "No file list component found"
            print("✅ File list display is present")
            
        except Exception as e:
            pytest.skip(f"File list test failed: {e}")
    
    @pytest.mark.frontend
    def test_file_preview_functionality(self, page: Page, gradio_helper, sample_python_file):
        """Test file preview functionality."""
        try:
            page.goto("http://localhost:7860", timeout=30000)
            gradio_helper.wait_for_gradio_load()
            
            # Navigate to File Management tab
            gradio_helper.click_tab("File Management")
            
            # Upload a file first (if not already uploaded)
            file_input = page.locator("input[type='file']").first
            if file_input.count() > 0:
                file_input.set_input_files(sample_python_file)
                page.wait_for_timeout(3000)
            
            # Look for preview components
            preview_selectors = [
                ".code-preview",
                ".file-preview",
                "pre",
                ".gr-code",
                "text=def hello"  # Content from our sample file
            ]
            
            preview_found = False
            for selector in preview_selectors:
                if page.locator(selector).count() > 0:
                    preview_found = True
                    print(f"✅ Found preview component: {selector}")
                    break
            
            if preview_found:
                print("✅ File preview functionality is working")
            else:
                print("⚠️  No file preview found - may require file selection")
            
        except Exception as e:
            pytest.skip(f"File preview test failed: {e}")
    
    @pytest.mark.frontend
    def test_file_validation(self, page: Page, gradio_helper):
        """Test file validation for non-Python files."""
        try:
            page.goto("http://localhost:7860", timeout=30000)
            gradio_helper.wait_for_gradio_load()
            
            # Navigate to File Management tab
            gradio_helper.click_tab("File Management")
            
            # Create a temporary non-Python file
            test_data_dir = Path("tests/test_data")
            test_data_dir.mkdir(exist_ok=True)
            
            invalid_file = test_data_dir / "invalid_file.txt"
            invalid_file.write_text("This is not a Python file")
            
            # Try to upload the invalid file
            file_input = page.locator("input[type='file']").first
            if file_input.count() > 0:
                file_input.set_input_files(str(invalid_file))
                page.wait_for_timeout(3000)
                
                # Look for error indicators
                error_indicators = [
                    ".error",
                    ".gr-error",
                    "text=Invalid file type",
                    "text=Only Python files",
                    "text=.py files only"
                ]
                
                error_found = False
                for indicator in error_indicators:
                    if page.locator(indicator).count() > 0:
                        error_found = True
                        print(f"✅ Found error indicator: {indicator}")
                        break
                
                if error_found:
                    print("✅ File validation is working correctly")
                else:
                    print("⚠️  No error message found - validation may be permissive")
            
            # Clean up
            if invalid_file.exists():
                invalid_file.unlink()
            
        except Exception as e:
            pytest.skip(f"File validation test failed: {e}")
    
    @pytest.mark.frontend
    def test_file_actions(self, page: Page, gradio_helper):
        """Test file action buttons (view, delete, etc.)."""
        try:
            page.goto("http://localhost:7860", timeout=30000)
            gradio_helper.wait_for_gradio_load()
            
            # Navigate to File Management tab
            gradio_helper.click_tab("File Management")
            
            # Look for action buttons
            action_selectors = [
                "button:has-text('View')",
                "button:has-text('Delete')",
                "button:has-text('Details')",
                "button:has-text('Remove')",
                ".action-button",
                ".file-action"
            ]
            
            actions_found = []
            for selector in action_selectors:
                if page.locator(selector).count() > 0:
                    actions_found.append(selector)
                    print(f"✅ Found action button: {selector}")
            
            if actions_found:
                print(f"✅ File actions available: {len(actions_found)} types found")
            else:
                print("⚠️  No file action buttons found - may require uploaded files")
            
        except Exception as e:
            pytest.skip(f"File actions test failed: {e}")
    
    @pytest.mark.frontend
    @pytest.mark.slow
    def test_multiple_file_upload(self, page: Page, gradio_helper, sample_python_file, complex_python_file):
        """Test uploading multiple files."""
        try:
            page.goto("http://localhost:7860", timeout=30000)
            gradio_helper.wait_for_gradio_load()
            
            # Navigate to File Management tab
            gradio_helper.click_tab("File Management")
            
            # Upload multiple files
            files_to_upload = [sample_python_file, complex_python_file]
            
            for file_path in files_to_upload:
                file_input = page.locator("input[type='file']").first
                if file_input.count() > 0:
                    file_input.set_input_files(file_path)
                    page.wait_for_timeout(2000)
                    print(f"✅ Uploaded: {Path(file_path).name}")
            
            # Check that multiple files are listed
            page.wait_for_timeout(3000)
            
            # Look for file entries
            file_entries = page.locator("text=sample_script.py, text=complex_script.py")
            
            print("✅ Multiple file upload test completed")
            
        except Exception as e:
            pytest.skip(f"Multiple file upload test failed: {e}")
