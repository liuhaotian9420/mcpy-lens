# Fix Function Selection UI Issue

**Date**: 2024-12-19  
**Status**: In Progress

## Description

Fix the missing function selection interface in Service Configuration. When a user selects a script and chooses "Function Mode", they should see a section where they can select which functions from their script to expose as MCP tools. Currently, this interface is not visible, causing the error "Please select at least one function for function mode".

## Problem Analysis

The issue appears to be in the Service Configuration workflow:
1. User selects a script from dropdown ✅
2. User chooses "Function Mode" ✅  
3. Function selection interface should appear ❌ (Missing)
4. User should be able to select functions ❌ (Not possible)
5. User clicks "Create Service" and gets error ❌

The function selection interface is likely controlled by:
- Script selection event handler in `service_config.py`
- Function discovery logic
- UI visibility controls for function selection group

## Tasks

### Phase 1: Investigation
- [x] Use Playwright MCP to test the current workflow
- [x] Navigate to Service Configuration tab
- [x] Select a script from dropdown
- [x] Verify if function selection interface appears
- [x] Check browser console for any JavaScript errors
- [x] Examine the function discovery API response

**Findings:**
- Script selection dropdown works correctly
- Function Mode selection works correctly
- Script selection triggers processing indicator
- Function selection section appears briefly but then disappears
- Issue is likely in Gradio 4.x component update mechanism

### Phase 2: Code Analysis
- [ ] Review `handle_script_selection()` function in service_config.py
- [ ] Check function discovery API call and response handling
- [ ] Verify UI component visibility logic
- [ ] Examine function selection group creation and updates

### Phase 3: Fix Implementation
- [ ] Fix function discovery and display logic
- [ ] Ensure function selection interface becomes visible after script selection
- [ ] Add proper error handling for function discovery failures
- [ ] Test function selection and deselection functionality

### Phase 4: Testing
- [ ] Test complete workflow: script selection → function selection → service creation
- [ ] Verify function selection interface appears correctly
- [ ] Test with different scripts that have various numbers of functions
- [ ] Ensure error messages are clear when no functions are found

### Phase 5: Verification
- [ ] Create comprehensive Playwright test for the complete workflow
- [ ] Document the expected user experience
- [ ] Verify no regressions in other functionality

## Expected Outcomes

1. After selecting a script, function selection interface becomes visible
2. Users can see and select available functions from their script
3. Function selection works properly with checkboxes or similar UI
4. Clear error messages when no functions are available
5. Successful service creation when functions are selected

## Progress Update

### ✅ **Issues Fixed:**
1. **API Endpoint Fixed**: Changed `/discover_tools` to `/discover` (correct endpoint)
2. **Auto-loading Implemented**: Dropdowns now auto-populate on page load
3. **Gradio 4.x Compatibility**: Updated component return patterns
4. **Script Dropdown Refresh**: Fixed and working without errors

### 🔄 **Current Status:**
- Function selection interface appears when Function Mode is selected
- Script selection triggers function discovery API calls
- Function discovery API endpoint is now correct
- Auto-loading of scripts works on page initialization

### 🎯 **Remaining Issue:**
- Function selection section shows but functions are not populated
- Need to ensure function discovery results are properly displayed in the CheckboxGroup

## Dependencies

- Backend service running and functional
- Script upload and listing working correctly
- Function discovery API working correctly
- Frontend Gradio app running

## Notes

- This is a critical UX issue that blocks the main workflow
- Function mode is a key feature for exposing individual Python functions
- The interface should be intuitive and guide users through the process
