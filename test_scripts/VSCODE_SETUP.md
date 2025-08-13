# VS Code Setup for iMatrix Test Scripts

This guide explains how to set up VS Code for building and debugging the iMatrix test scripts and programs using CMake.

## Prerequisites

### 1. Install System Dependencies
```bash
sudo apt update
sudo apt install cmake build-essential gdb
```

### 2. Install VS Code Extensions
Install these extensions in VS Code:

**Required:**
- **CMake Tools** (by Microsoft) - ID: `ms-vscode.cmake-tools`
- **CMake** (by twxs) - ID: `twxs.cmake`
- **C/C++** (by Microsoft) - ID: `ms-vscode.cpptools`

**Optional but Recommended:**
- **GitLens** (by GitKraken) - Enhanced Git support
- **Error Lens** - Inline error display

## Setup Instructions

### 1. Open Project in VS Code
```bash
# Open the test_scripts directory in VS Code
code /home/greg/iMatrix_src/test_scripts
```

### 2. Configure CMake (First Time)
1. **Ctrl+Shift+P** → Type "CMake: Configure"
2. Select your compiler (usually GCC)
3. Choose build variant (Debug recommended for development)

### 3. Verify Configuration
The following files are already configured:
- `.vscode/settings.json` - CMake and project settings
- `.vscode/c_cpp_properties.json` - IntelliSense configuration
- `.vscode/tasks.json` - Build and test tasks
- `.vscode/launch.json` - Debug configurations

## Building and Running

### Method 1: CMake Tools Extension (Recommended)
1. **View** → **Command Palette** (**Ctrl+Shift+P**)
2. Type "CMake: Build" to build all targets
3. Or use the CMake sidebar:
   - Click the CMake icon in the left sidebar
   - Expand "Project Outline"
   - Right-click any target to build/run

### Method 2: Tasks (Keyboard Shortcuts)
- **Ctrl+Shift+P** → "Tasks: Run Task" → Select task:
  - **"Build All"** - Build all test programs
  - **"Build Simple Memory Test"** - Build only simple_memory_test
  - **"Run All Tests"** - Build and run all tests
  - **"Run Simple Memory Test"** - Build and run simple test

### Method 3: Terminal
- **Ctrl+`** to open integrated terminal
- Terminal opens in `/home/greg/iMatrix_src/test_scripts/build`
- Run: `make` or `./simple_memory_test`

## Debugging

### Debug Individual Tests
1. Open a test file (e.g., `simple_memory_test.c`)
2. **F5** to start debugging
3. Or **Ctrl+Shift+P** → "Debug: Start Debugging"
4. Select debug configuration:
   - **"Debug Simple Memory Test"**
   - **"Debug Tiered Storage Test"**
   - **"Debug Performance Test"**

### Set Breakpoints
1. Click in the left margin next to line numbers
2. Red dot appears indicating breakpoint
3. **F5** to start debugging - execution stops at breakpoints

### Debug Features
- **F5**: Start debugging
- **F10**: Step over
- **F11**: Step into
- **Shift+F11**: Step out
- **F9**: Toggle breakpoint
- **Ctrl+Shift+F5**: Restart debugging

## IntelliSense and Code Navigation

### Features Available
- **Auto-completion** for iMatrix functions
- **Go to Definition** (**F12** or **Ctrl+Click**)
- **Find All References** (**Shift+F12**)
- **Error underlining** for syntax errors
- **Function signatures** on hover

### Include Paths Configured
- `../iMatrix/` - Main iMatrix headers
- `../iMatrix/IMX_Platform/LINUX_Platform/` - Platform headers
- `../mbedtls/include/` - mbedTLS headers

## Troubleshooting

### CMake Not Found
```bash
# Install CMake if missing
sudo apt install cmake
```

### Extension Issues
1. **Ctrl+Shift+P** → "Developer: Reload Window"
2. Or reinstall extensions

### Build Errors
1. Check **Problems** panel (**Ctrl+Shift+M**)
2. Verify all paths in `.vscode/c_cpp_properties.json`
3. Clean and rebuild: **Ctrl+Shift+P** → "CMake: Clean Rebuild"

### IntelliSense Issues
1. **Ctrl+Shift+P** → "C/C++: Reset IntelliSense Database"
2. Verify `compileCommands` path in c_cpp_properties.json

## Quick Reference

### Keyboard Shortcuts
| Action | Shortcut |
|--------|----------|
| Build All | **Ctrl+Shift+P** → "CMake: Build" |
| Run Task | **Ctrl+Shift+P** → "Tasks: Run Task" |
| Start Debug | **F5** |
| Toggle Breakpoint | **F9** |
| Go to Definition | **F12** |
| Open Terminal | **Ctrl+`** |
| Command Palette | **Ctrl+Shift+P** |

### Build Targets
- `simple_memory_test` - Basic memory testing
- `tiered_storage_test` - Tiered storage testing  
- `performance_test` - Performance and stress testing

### Test Commands
```bash
# In terminal (Ctrl+`)
make                    # Build all
./simple_memory_test    # Run simple test
./tiered_storage_test   # Run tiered storage test
./performance_test      # Run performance test
make run_all_tests      # Run all tests
```

## Project Structure
```
test_scripts/
├── .vscode/                    # VS Code configuration
│   ├── settings.json          # Project settings
│   ├── c_cpp_properties.json  # IntelliSense config
│   ├── tasks.json             # Build tasks
│   └── launch.json            # Debug config
├── CMakeLists.txt             # CMake build script
├── simple_memory_test.c       # Basic test program
├── tiered_storage_test.c      # Tiered storage test
├── performance_test.c         # Performance test
├── build/                     # Build directory
│   ├── simple_memory_test     # Built executable
│   ├── tiered_storage_test    # Built executable
│   └── performance_test       # Built executable
└── VSCODE_SETUP.md           # This file
```

The setup is now complete! You can start building and debugging the iMatrix test scripts and programs directly in VS Code.