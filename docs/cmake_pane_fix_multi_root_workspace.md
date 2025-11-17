# CMake Pane Fix - Multi-Root Workspace Issue

**Date:** 2025-11-16
**Issue:** CMake pane shows iMatrix instead of Fleet-Connect-1, no build targets
**Root Cause:** Multi-root workspace with multiple CMake projects
**Status:** Diagnosis complete - solution ready

---

## Problem Diagnosis

### What the Screenshot Shows

**CMake Pane Display:**
```
PROJECT STATUS
  Folder: iMatrix                    ← Wrong folder!
  Configure: [No Kit Selected]       ← No preset selected
  Build: [N/A - Select Kit]          ← Can't build

PROJECT OUTLINE
  Fleet-Connect-1 [Workspace]        ← Shows as workspace
  iMatrix [Active Workspace]         ← iMatrix is active
```

### Root Cause

**You have a multi-root workspace open** with both:
1. `/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/`
2. `/home/greg/iMatrix/iMatrix_Client/iMatrix/`

**Problem:**
- CMake Tools extension sees BOTH projects
- It's configured for iMatrix (which has CMakeLists.txt but no presets)
- Fleet-Connect-1 has the presets but isn't the active project
- Result: Can't select preset, can't build FC-1

### Evidence

**Workspace files found:**
```
/home/greg/iMatrix/iMatrix_Client/imatrix-fleet.code-workspace
/home/greg/iMatrix/iMatrix_Client/fleet-connect-workspace.code-workspace
/home/greg/iMatrix/iMatrix_Client/cursor-workspace.code-workspace
/home/greg/iMatrix/iMatrix_Client/iMatrix_src.code-workspace
```

---

## Solution Options

### Option 1: Open Fleet-Connect-1 as Single Folder (RECOMMENDED)

**This is the simplest and cleanest solution.**

**Steps:**
1. Close current workspace in VS Code
2. File → Open Folder
3. Navigate to: `/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1`
4. Click "Open"
5. CMake Tools will detect Fleet-Connect-1's CMakeLists.txt
6. Select preset: "ARM Cross-Compile (DebugGDB)"
7. Build

**Advantages:**
- ✅ Clean, single-project view
- ✅ CMake pane shows only Fleet-Connect-1
- ✅ Presets work correctly
- ✅ No confusion about which project is active

**Disadvantages:**
- Can't easily navigate to iMatrix source files
- Have to switch folders to edit iMatrix code

---

### Option 2: Configure Multi-Root Workspace Correctly

**Keep multi-root workspace but configure it properly.**

**Create/Edit:** `imatrix-fleet.code-workspace`

```json
{
    "folders": [
        {
            "name": "Fleet-Connect-1",
            "path": "Fleet-Connect-1"
        },
        {
            "name": "iMatrix",
            "path": "iMatrix"
        },
        {
            "name": "Docs",
            "path": "docs"
        }
    ],
    "settings": {
        "cmake.sourceDirectory": "${workspaceFolder:Fleet-Connect-1}",
        "cmake.buildDirectory": "${workspaceFolder:Fleet-Connect-1}/build",
        "cmake.useCMakePresets": "always",
        "cmake.options.statusBarVisibility": "visible"
    }
}
```

**Key setting:**
```json
"cmake.sourceDirectory": "${workspaceFolder:Fleet-Connect-1}"
```

**This tells CMake Tools to use Fleet-Connect-1 as the primary CMake project.**

**Steps:**
1. Close VS Code
2. Edit or create workspace file (above)
3. Open workspace: File → Open Workspace from File
4. Select: `imatrix-fleet.code-workspace`
5. CMake pane should now show Fleet-Connect-1
6. Select preset and build

**Advantages:**
- ✅ Can navigate both projects easily
- ✅ Side-by-side file access
- ✅ Single VS Code window

**Disadvantages:**
- More complex configuration
- Need to maintain workspace file

---

### Option 3: Use Folder-Specific Settings

**Keep multi-root but use .vscode/settings.json in Fleet-Connect-1.**

**The settings are already there!** But in multi-root workspace, you may need to explicitly select which folder's settings to use.

**Steps:**
1. In CMake pane, click the folder dropdown
2. Select "Fleet-Connect-1" (not iMatrix)
3. CMake should re-scan and find CMakePresets.json
4. Select preset
5. Build

---

## Recommended Solution

### Use Option 1 for Now (Simplest)

**Immediate fix:**

```bash
# Open Fleet-Connect-1 as single folder
code /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1
```

**Then in VS Code:**
1. Wait for CMake Tools to activate
2. `Ctrl+Shift+P` → "CMake: Select Configure Preset"
3. Choose: **"ARM Cross-Compile (DebugGDB)"**
4. `Ctrl+Shift+P` → "CMake: Configure"
5. Wait for "Configuring done"
6. `F7` to build

**This should work immediately!**

---

## Long-Term Solution

### Create Optimized Multi-Root Workspace

**For best of both worlds (Fleet-Connect-1 AND iMatrix access):**

**Create:** `/home/greg/iMatrix/iMatrix_Client/fleet-connect-dev.code-workspace`

```json
{
    "folders": [
        {
            "name": "Fleet-Connect-1 (Main)",
            "path": "Fleet-Connect-1"
        },
        {
            "name": "iMatrix (Library)",
            "path": "iMatrix"
        },
        {
            "name": "Documentation",
            "path": "docs"
        }
    ],
    "settings": {
        // Force CMake to use Fleet-Connect-1 as the active project
        "cmake.sourceDirectory": "${workspaceFolder:Fleet-Connect-1 (Main)}",
        "cmake.buildDirectory": "${workspaceFolder:Fleet-Connect-1 (Main)}/build",

        // Always use presets
        "cmake.useCMakePresets": "always",

        // Show CMake status in status bar
        "cmake.options.statusBarVisibility": "visible",

        // Don't auto-configure
        "cmake.configureOnOpen": false,

        // Parse build errors
        "cmake.parseBuildDiagnostics": true,

        // Environment variables for CMake
        "cmake.environment": {
            "QCONNECT_SDK": "/opt/qconnect_sdk_musl",
            "CMAKE_SYSROOT": "/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot",
            "CMAKE_C_COMPILER": "/opt/qconnect_sdk_musl/bin/arm-linux-gcc",
            "CMAKE_CXX_COMPILER": "/opt/qconnect_sdk_musl/bin/arm-linux-g++",
            "QUAKE_LIBS": "/home/greg/qconnect_sw/svc_sdk/source/qfc/arm_musl/libs",
            "ARM_MATH": "/home/greg/iMatrix/iMatrix_Client/CMSIS-DSP"
        },

        // C/C++ configuration
        "C_Cpp.default.configurationProvider": "ms-vscode.cmake-tools"
    },
    "extensions": {
        "recommendations": [
            "ms-vscode.cmake-tools",
            "ms-vscode.cpptools",
            "twxs.cmake"
        ]
    }
}
```

**Save this file and open it:**
```bash
code /home/greg/iMatrix/iMatrix_Client/fleet-connect-dev.code-workspace
```

---

## Step-by-Step Fix

### Immediate Action (5 Minutes)

**1. Close current VS Code window**

**2. Open Fleet-Connect-1 ONLY as a folder**
```bash
code /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1
```

**3. CMake Tools should activate**
- Look for CMake icon in left sidebar
- May take 5-10 seconds to scan project

**4. Select Configure Preset**
- `Ctrl+Shift+P`
- Type: "CMake: Select Configure Preset"
- You should see: "ARM Cross-Compile (DebugGDB)"
- Select it

**5. Verify Preset Selected**
- Check status bar (bottom)
- Should show: `[DebugGDB]` or `[arm-cross-debug]`

**6. Configure Project**
- `Ctrl+Shift+P`
- "CMake: Configure"
- OR: Press `Shift+F7`
- OR: Click "Configure" in CMake pane

**7. Watch OUTPUT Panel**
```
[cmake] Configuring project: Fleet_Connect
[cmake] Configuring done
[cmake] Generating done
```

**8. Check CMake Pane**
- Should now show:
  - Folder: Fleet_Connect
  - Configure: ARM Cross-Compile (DebugGDB)
  - Build: Build ARM Debug
  - Targets: FC-1, imatrix, mbedtls, etc.

**9. Build**
- Press `F7`
- OR: Click "Build All Projects" in CMake pane
- OR: Status bar → Click hammer icon

**10. Verify Success**
```bash
file build/FC-1
# Should show: ARM, EABI5
```

---

## Why Multi-Root Causes Issues

### The Problem

**When you open a multi-root workspace:**
```
Workspace
├── Fleet-Connect-1/     (has CMakeLists.txt + CMakePresets.json)
└── iMatrix/             (has CMakeLists.txt, NO presets)
```

**CMake Tools behavior:**
1. Scans all folders for CMakeLists.txt
2. Finds both Fleet-Connect-1 AND iMatrix
3. Defaults to first one alphabetically or first in workspace
4. In your case: Selected iMatrix
5. iMatrix has no CMakePresets.json
6. Result: "[No Kit Selected]" - can't build

### The Fix

**Tell CMake Tools which folder is the PRIMARY project:**

**In workspace file:**
```json
"cmake.sourceDirectory": "${workspaceFolder:Fleet-Connect-1}"
```

**OR: Open Fleet-Connect-1 as single folder** (simpler!)

---

## Verification After Fix

### CMake Pane Should Show

```
PROJECT STATUS
  Folder: Fleet_Connect                          ✅
  Configure: ARM Cross-Compile (DebugGDB)        ✅
  Build: Build ARM Debug                         ✅

PROJECT OUTLINE
  📁 Fleet_Connect
    ├── 🎯 FC-1                                  ✅ Build target!
    ├── 📚 imatrix
    ├── 📚 mbedtls
    ├── 📚 mbedcrypto
    └── 📚 mbedx509
```

### Status Bar Should Show

```
CMake: [DebugGDB] [arm-cross-debug] | Build: FC-1 ✅
```

---

## Testing the Fix

### Test 1: Configure

1. Click "Configure All Projects" in CMake pane
2. Check OUTPUT panel
3. Should see: "Configuring done"

**Pass:** ✅ Configuration succeeded
**Fail:** ❌ Check OUTPUT for errors

### Test 2: Build

1. Click "Build All Projects" or press `F7`
2. Watch build progress in OUTPUT
3. Should reach [100%]

**Pass:** ✅ FC-1 binary created
**Fail:** ❌ Check PROBLEMS panel

### Test 3: Target Selection

1. Click "FC-1" in status bar
2. Should see list of targets:
   - FC-1
   - imatrix
   - mbedtls
   - Others...

**Pass:** ✅ Can select targets
**Fail:** ❌ No targets shown - reconfigure needed

---

## Quick Fix Script

**Save this as `open_fc1_vscode.sh`:**

```bash
#!/bin/bash
# Open Fleet-Connect-1 in VS Code with correct CMake configuration

echo "Opening Fleet-Connect-1 in VS Code..."
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1

# Open as single folder (not workspace)
code .

echo ""
echo "VS Code opened!"
echo ""
echo "Next steps:"
echo "1. Wait for CMake Tools to activate (5-10 seconds)"
echo "2. Press Ctrl+Shift+P"
echo "3. Type: CMake: Select Configure Preset"
echo "4. Choose: ARM Cross-Compile (DebugGDB)"
echo "5. Press Shift+F7 to configure"
echo "6. Press F7 to build"
echo ""
echo "Done!"
```

**Make executable and run:**
```bash
chmod +x open_fc1_vscode.sh
./open_fc1_vscode.sh
```

---

## Summary

### The Issue
- Multi-root workspace has multiple CMake projects
- CMake pane defaulted to iMatrix
- iMatrix has no CMakePresets.json
- Can't select ARM preset
- Can't build

### The Solution
**Open Fleet-Connect-1 as SINGLE FOLDER** (not workspace)

```bash
code /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1
```

**Then:**
1. Select ARM Cross-Compile (DebugGDB) preset
2. Configure (Shift+F7)
3. Build (F7)

### Expected Result
- CMake pane shows Fleet_Connect folder
- Preset is selectable and working
- FC-1 appears as build target
- F7 builds successfully
- Binary is ARM EABI5

---

**Next Step:** Close current VS Code, open Fleet-Connect-1 folder only, follow steps above.
