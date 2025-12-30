<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/new_dev.yaml
Generated on: 2025-12-30
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Create 'new_dev' Slash Command for Development Environment Setup

**Date:** 2025-12-30
**Branch:** feature/new_dev_slash_command

---

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH
The wifi communications uses a combination Wi-Fi/Bluetooth chipset
The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.

The user's name is Greg

Read and understand the following:

- Fleet-Connect-1/docs/BUILD_SYSTEM_DOCUMENTATION.md
- Fleet-Connect-1/docs/Fleet-Connect-1_Developer_Overview.md
- Fleet-Connect-1/CMakeLists.txt
- Fleet-Connect-1/CMakePresets.json
- Fleet-Connect-1/increment_version.py
- iMatrix/CMakeLists.txt
- mbedtls/CMakeLists.txt
- ~/iMatrix/iMatrix_Client/.claude/commands/
- ~/iMatrix/iMatrix_Client/.claude/settings.json
- ~/iMatrix/iMatrix_Client/CLAUDE.md

use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

Create a new slash command called "new_dev" that automates the creation of a
complete development environment using git worktrees, copies Claude Code configuration,
and validates the setup by building the codebase.

## Command Specification

**Name:** /new_dev
**Usage:** /new_dev <environment_name>
**Argument:** environment_name - A descriptive name for the development environment
              (e.g., "canbus_refactor", "bluetooth_fix")

## Behavior

When invoked, the command should execute the following phases:

### Phase 1: Environment Setup
1. Create a new directory named <environment_name> in ~/iMatrix/ (sibling to iMatrix_Client)
2. For each repository listed below, create a git worktree from the specified branch
3. Report progress for each repository

### Phase 2: Claude Code Configuration
4. Copy the .claude directory from ~/iMatrix/iMatrix_Client/ to the new environment
   - Source: ~/iMatrix/iMatrix_Client/.claude
   - Destination: ~/iMatrix/<environment_name>/.claude
5. Copy any root-level Claude configuration files from ~/iMatrix/iMatrix_Client/:
   - .claude/ (directory - required)
   - CLAUDE.md (if exists)
   - .cursorrules (if exists)
   - .cursorignore (if exists)
6. Verify the configuration was copied successfully

### Phase 3: Build
7. Navigate to Fleet-Connect-1 directory
8. Remove any existing build directory: `rm -rf build`
9. Create and enter build directory: `mkdir build && cd build`
10. Configure with CMake: `cmake ..`
    - CMakeLists.txt auto-detects ARM cross-compiler at /opt/qconnect_sdk_musl/
    - Automatically builds dependencies (mbedTLS, iMatrix) via add_subdirectory()
    - Defaults to DebugGDB build type if not specified
11. Build: `make -j4`
12. Capture build output for error/warning analysis

### Phase 4: Build Validation
13. Verify FC-1 binary was created in build directory
14. Verify architecture is ARM EABI5: `file build/FC-1`
15. Parse build output for compilation errors and warnings
16. Report final status

## Required Repositories

| Repository | Branch | Local Directory |
|------------|--------|-----------------|
| https://github.com/sierratelecom/iMatrix-WICED-6.6-Client | Aptera_1_Clean | iMatrix |
| https://github.com/sierratelecom/Fleet-Connect-1 | Aptera_1_Clean | Fleet-Connect-1 |
| https://github.com/sierratelecom/btstack | imatrix_release | btstack |
| https://github.com/sierratelecom/mbedtls | mbedtls-3.6.2 | mbedtls |

## Directory Layout

**Before** running `/new_dev my_feature`:
```
~/iMatrix/
└── iMatrix_Client/           # Main development environment (source for config)
    ├── .claude/              # Claude Code configuration (SOURCE)
    │   ├── commands/         # Custom slash commands
    │   ├── settings.json     # Claude Code settings
    │   └── ...
    ├── CLAUDE.md             # Project context (SOURCE)
    ├── iMatrix/              # Main cloned repo
    ├── Fleet-Connect-1/      # Main cloned repo
    ├── btstack/              # Main cloned repo
    └── mbedtls/              # Main cloned repo
```

**After** running `/new_dev my_feature`:
```
~/iMatrix/
├── iMatrix_Client/           # Main development environment (unchanged)
│   └── ...
│
└── my_feature/               # NEW ENVIRONMENT CREATED
    ├── .claude/              # COPIED from iMatrix_Client
    │   ├── commands/         # All slash commands available
    │   ├── settings.json
    │   └── ...
    ├── CLAUDE.md             # COPIED from iMatrix_Client
    ├── iMatrix/              # WORKTREE → iMatrix-WICED-6.6-Client:Aptera_1_Clean
    ├── Fleet-Connect-1/      # WORKTREE → Fleet-Connect-1:Aptera_1_Clean
    │   ├── CMakeLists.txt
    │   └── build/
    │       ├── FC-1          # Built ARM binary
    │       └── FC-1.map
    ├── btstack/              # WORKTREE → btstack:imatrix_release
    └── mbedtls/              # WORKTREE → mbedtls:mbedtls-3.6.2
```

## Claude Configuration Copy Commands

```bash
# Source and destination paths
SOURCE_DIR=~/iMatrix/iMatrix_Client
DEST_DIR=~/iMatrix/<environment_name>

# Copy .claude directory (required for slash commands and tools)
cp -r ${SOURCE_DIR}/.claude ${DEST_DIR}/

# Copy root-level config files if they exist
[ -f ${SOURCE_DIR}/CLAUDE.md ] && cp ${SOURCE_DIR}/CLAUDE.md ${DEST_DIR}/
[ -f ${SOURCE_DIR}/.cursorrules ] && cp ${SOURCE_DIR}/.cursorrules ${DEST_DIR}/
[ -f ${SOURCE_DIR}/.cursorignore ] && cp ${SOURCE_DIR}/.cursorignore ${DEST_DIR}/
```

## Build Commands Reference

```bash
# Navigate to Fleet-Connect-1
cd ~/iMatrix/<environment_name>/Fleet-Connect-1

# Clean build
rm -rf build
mkdir build && cd build

# Configure and build (CMake auto-detects ARM compiler and builds dependencies)
cmake ..
make -j4

# Verify build
file FC-1
# Expected: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV)
```

## Build Types

| Build Type | Command | Binary Size | Use Case |
|------------|---------|-------------|----------|
| DebugGDB (default) | `cmake ..` | ~18MB | GDB debugging, full symbols |
| Debug | `cmake -DCMAKE_BUILD_TYPE=Debug ..` | ~13MB | Standard debug |
| Release | `cmake -DCMAKE_BUILD_TYPE=Release ..` | ~8MB | Production |

## Build Validation Output

Display a summary after build completes:
```
══════════════════════════════════════════════════════════════════
NEW DEVELOPMENT ENVIRONMENT CREATED
══════════════════════════════════════════════════════════════════
Environment: my_feature
Location:    ~/iMatrix/my_feature

REPOSITORY STATUS:
  ✓ iMatrix          → Aptera_1_Clean
  ✓ Fleet-Connect-1  → Aptera_1_Clean
  ✓ btstack          → imatrix_release
  ✓ mbedtls          → mbedtls-3.6.2

CLAUDE CODE CONFIGURATION (from ~/iMatrix/iMatrix_Client/):
  ✓ .claude/         (slash commands, MCP configs)
  ✓ CLAUDE.md        (project context)
  ○ .cursorrules     (not found - skipped)
  ○ .cursorignore    (not found - skipped)

BUILD RESULTS:
  Status:     PASS / FAIL
  Build Type: DebugGDB
  Binary:     FC-1 (ARM EABI5)
  Size:       XX MB
  Errors:     0
  Warnings:   0
  Build time: XX seconds

ARM Cross-Compiler: /opt/qconnect_sdk_musl/bin/arm-linux-gcc
══════════════════════════════════════════════════════════════════

Ready to use! Open this directory in Cursor/VS Code:
  cd ~/iMatrix/my_feature && cursor .
══════════════════════════════════════════════════════════════════
```

## Files to Modify

| Path | Action | Description |
|------|--------|-------------|
| .claude/commands/ | create new file | The new_dev slash command implementation |

## Implementation Notes

### Prerequisites
- All source repositories must already be cloned in ~/iMatrix/iMatrix_Client/
- ARM toolchain must be installed at /opt/qconnect_sdk_musl/
- ~/.claude directory must exist in iMatrix_Client for configuration copy

### Key Paths
- **Source config**: ~/iMatrix/iMatrix_Client/.claude
- **Source repos**: ~/iMatrix/iMatrix_Client/{iMatrix,Fleet-Connect-1,btstack,mbedtls}
- **New environment**: ~/iMatrix/<environment_name>/

### Worktree Setup
- Worktrees are created from the repos in ~/iMatrix/iMatrix_Client/
- Each worktree checks out the specified branch
- Verify source branches exist before creating worktrees
- Handle case where environment directory already exists

### Claude Configuration Copy
- **Required**: .claude directory (contains slash commands, MCP configs)
- **Optional**: CLAUDE.md, .cursorrules, .cursorignore
- If .claude doesn't exist in source, FAIL with helpful error
- Consider using symlinks instead of copy (--symlink flag) for shared config

### Copy vs Symlink Decision
- **Copy (default)**: Each environment has independent config, safe for experimentation
- **Symlink (optional)**: Changes to slash commands affect all environments immediately
- Recommend: Copy by default, add --symlink flag for shared config

### Build System Details (from CMakeLists.txt)
- **Auto-detection**: CMakeLists.txt automatically finds ARM compiler at /opt/qconnect_sdk_musl/
- **Dependencies**: mbedTLS and iMatrix are built via add_subdirectory() - no separate steps needed
- **Default build type**: DebugGDB (optimized for GDB debugging with full symbols)
- **Version increment**: Build number auto-increments via increment_version.py
- **Security flags**: Stack protection (-fstack-protector-all) and FORTIFY_SOURCE enabled

### Build Time Expectations
- Clean build: ~5-6 minutes on 4-core system
- Incremental build: 5-30 seconds
- DebugGDB builds are larger (~18MB) but have complete stack traces

### Error Handling
- If ARM compiler not found, CMake fails with helpful message
- If QUAKE_LIBS directory missing, CMake fails with path error
- If .claude directory not found in iMatrix_Client, FAIL (required for tooling)
- Preserve environment on build failure for debugging

### Exit Codes
- 0: Environment created AND build passed
- 1: Environment/worktree creation failed
- 2: Claude config copy failed (.claude not found)
- 3: CMake configuration failed
- 4: Make build failed (environment preserved)

### Log Capture
- Save CMake output to ~/iMatrix/<environment_name>/cmake_config.log
- Save make output to ~/iMatrix/<environment_name>/build.log
- On failure, display relevant portion of log

## Optional Enhancements (if time permits)

- `--no-build` flag to skip build validation (just create worktrees + copy config)
- `--no-claude-config` flag to skip .claude directory copy
- `--symlink-config` flag to symlink .claude instead of copy (shared config)
- `--dry-run` flag to preview what would be created
- `--clean` flag to remove existing environment before creating
- `--release` flag to use Release build type
- `--debug` flag to use Debug build type (vs default DebugGDB)
- `--jobs N` flag to control parallel compilation (default: 4)

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/new_dev_slash_command.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check off the items on the todo list as they are completed.
4. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found fix them immediately.
5. **Final build verification**: Before marking work complete, perform a final clean build to verify:
   - Zero compilation errors
   - Zero compilation warnings
   - All modified files compile successfully
   - The build completes without issues
6. Once I have determined the work is completed successfully add a concise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.
8. Merge the branch back into the original branch.
9. Update all documents with relevant details

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** docs/prompt_work/new_dev.yaml
**Generated:** 2025-12-30
