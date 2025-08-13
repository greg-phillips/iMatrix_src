# VS Code Build Issues - Troubleshooting Guide

## Issue: VS Code Building from Wrong Directory

**Problem:** VS Code CMake Tools is building from `/home/greg/iMatrix_src/build` instead of `/home/greg/iMatrix_src/test_scripts/build`.

**Root Cause:** VS Code detected multiple possible CMake projects and chose the wrong one.

## Solutions Applied ✅

### 1. Updated VS Code Configuration Files
- **Fixed absolute paths** in all `.vscode/*.json` files
- **Disabled auto-configure** to prevent interference
- **Set explicit source directory** to `/home/greg/iMatrix_src/test_scripts`

### 2. How to Fix in VS Code

#### Method 1: Reset CMake Cache (Recommended)
1. **Ctrl+Shift+P** → "CMake: Delete Cache and Reconfigure"
2. **Ctrl+Shift+P** → "CMake: Configure"
3. Select `/home/greg/iMatrix_src/test_scripts/CMakeLists.txt` when prompted

#### Method 2: Select Correct Kit
1. **Ctrl+Shift+P** → "CMake: Select a Kit"
2. Choose GCC kit
3. **Ctrl+Shift+P** → "CMake: Select Variant" 
4. Choose Debug or Release

#### Method 3: Manual Configuration
1. Open **CMake Tools** sidebar (CMake icon)
2. Click **Configure** button
3. If prompted for source directory, select `/home/greg/iMatrix_src/test_scripts`

## Verification Steps

### 1. Check Build Directory
In VS Code terminal (**Ctrl+`**):
```bash
pwd
# Should show: /home/greg/iMatrix_src/test_scripts/build
```

### 2. Verify CMake Configuration
```bash
# Should build from correct directory
cmake --build . --target simple_memory_test
```

### 3. Run Tests
```bash
./simple_memory_test
# Should show: "iMatrix Simple Memory Test"
```

## Manual Build Commands

If VS Code is still having issues, use these commands:

```bash
# From VS Code terminal (Ctrl+`)
cd /home/greg/iMatrix_src/test_scripts
mkdir -p build && cd build
cmake ..
make

# Run tests
./simple_memory_test
./tiered_storage_test  
./performance_test
```

## Common VS Code Issues & Fixes

### Issue: "Cannot find CMakeLists.txt"
**Fix:** Ensure you opened the correct folder:
```bash
# Open correct directory in VS Code
code /home/greg/iMatrix_src/test_scripts
```

### Issue: IntelliSense Errors
**Fix:** 
1. **Ctrl+Shift+P** → "C/C++: Reset IntelliSense Database"
2. **Ctrl+Shift+P** → "Developer: Reload Window"

### Issue: "Kit not found" 
**Fix:**
1. **Ctrl+Shift+P** → "CMake: Scan for Kits"
2. Select GCC compiler

### Issue: Build Targets Not Showing
**Fix:**
1. **Ctrl+Shift+P** → "CMake: Clean Rebuild"
2. Check CMake Tools sidebar for targets:
   - simple_memory_test
   - tiered_storage_test  
   - performance_test

## VS Code Settings Summary

The issue has been fixed by updating these files with absolute paths:

- `.vscode/settings.json` - CMake source/build directories
- `.vscode/tasks.json` - Build task paths
- `.vscode/launch.json` - Debug executable paths
- `.vscode/c_cpp_properties.json` - Include paths

## Success Indicators

✅ **Working correctly when:**
- Build output shows `/home/greg/iMatrix_src/test_scripts/build`
- Terminal opens in correct build directory
- All 3 test executables build successfully
- Debug configurations work with F5

❌ **Still having issues when:**
- Build output shows `/home/greg/iMatrix_src/build` 
- Cannot find test executables
- IntelliSense cannot find iMatrix headers

## Quick Fix Commands

```bash
# Reset everything
cd /home/greg/iMatrix_src/test_scripts
rm -rf build .vscode/cmake-tools-*
code .

# Then in VS Code:
# Ctrl+Shift+P → "CMake: Configure"
# Ctrl+Shift+P → "CMake: Build"
```

The configuration is now fixed to use absolute paths, so VS Code should build from the correct directory.