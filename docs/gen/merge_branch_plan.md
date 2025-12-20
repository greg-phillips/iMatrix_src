# Merge Branch Plan: Aptera_1_Clean_fix → Aptera_1_Clean

**Date:** 2025-12-12
**Author:** Claude Code Analysis
**Status:** Approved - Ready for Implementation
**Document Version:** 1.2

---

## 1. Executive Summary

This document details the merge plan for bringing changes from `Aptera_1_Clean_fix` into the `Aptera_1_Clean` branch for both **iMatrix** and **Fleet-Connect-1** submodules.

### Branch Relationship (Diverged Branches)
```
                    Aptera_1_Clean (has unique commits)
                   /
merge-base ───────
                   \
                    Aptera_1_Clean_fix (has bug fixes)
```

Both branches have diverged from a common ancestor. A proper 3-way merge will combine changes from both.

### Current Branch States
| Repository | Current Branch | Source Branch | Target Branch |
|------------|----------------|---------------|---------------|
| iMatrix | Aptera_1_Clean | origin/Aptera_1_Clean_fix | Aptera_1_Clean |
| Fleet-Connect-1 | Aptera_1_Clean | origin/Aptera_1_Clean_fix | Aptera_1_Clean |

### Commits Unique to Each Branch

**Aptera_1_Clean (to be preserved):**
- iMatrix: 4 commits (Update docs, Diags/CAN fixes, Upload updates, cli_capture fix)
- Fleet-Connect-1: 1 commit (updates for obd2 processing - includes README.md)

**Aptera_1_Clean_fix (to be merged in):**
- 4 commits: OTA fix, FC-1 branch setting, ifplugd_fix.sh, Modem detect fix

### User Decisions (from review)
1. **QUAKE_LIBS:** Directory does not exist locally - will copy files (not symlink)
2. **DebugGDB:** Build type is still needed - will restore after merge
3. **Jenkinsfile:** Branch reference stays as `Aptera_1_Clean_fix` (no change needed)

---

## 2. Actual Merge Results (Verified)

### 2.1 iMatrix Merge (5 files affected)

**Verified merge result** (3-way merge preserves all existing files):

```
cellular_man.c    | 82 ++-- (modem fix + whitespace cleanup)
Jenkinsfile       |  2 +-  (branch reference update)
create_pkg.sh     |  2 +-  (OTA package fix)
ifplugd_fix.sh    |  7 ++  (NEW - wlan0 DHCP cleanup script)
init              |  5 ++  (calls ifplugd_fix.sh)
```

**Key Changes Being Merged:**

| Category | File(s) | Description | Risk |
|----------|---------|-------------|------|
| Bug Fix | cellular_man.c:1787 | Fixed `if` → `else if` for modem type detection (PLS62_W vs PLS63_W) | Low |
| Feature | ifplugd_fix.sh (new) | Script to fix ifplugd wlan0 DHCP cleanup | Low |
| Feature | init script | Added call to ifplugd_fix.sh | Low |
| Jenkins | Jenkinsfile | Changed FC_GATEWAY_BRANCH to 'Aptera_1_Clean_fix' | Low |
| Fix | create_pkg.sh | OTA package creation fix | Low |

**Note:** All files unique to Aptera_1_Clean (docs, diags, upload updates, cli_capture) are PRESERVED.

---

### 2.2 Fleet-Connect-1 Merge (3 files affected)

**Verified merge result** (README.md and other files PRESERVED):

```
CMakeLists.txt        | 29 +--- (path changes, -DebugGDB)
linux_gateway_build.h |  2 +-  (version)
version.h             |  2 +-  (version)
```

**Key Changes:**

| Category | File(s) | Description | Action |
|----------|---------|-------------|--------|
| **BUILD CONFIG** | CMakeLists.txt | Changed QUAKE_LIBS to relative path | Accept + copy qfc directory |
| **BUILD CONFIG** | CMakeLists.txt | Removed sysroot link directories | Accept |
| **RESTORE** | CMakeLists.txt | Removed DebugGDB build type (21 lines) | **Restore after merge** |
| Version | version.h, linux_gateway_build.h | Version updates | Accept |

**Note:** README.md added in Aptera_1_Clean is PRESERVED (not deleted).

---

## 3. Required Pre-Merge Actions

### 3.1 Copy QUAKE_LIBS Directory

The relative path `../../../qfc/arm_musl/libs` requires the following structure:
```
/home/greg/iMatrix/
├── qfc/                          ← NEW: copy from existing location
│   └── arm_musl/
│       └── libs/
└── iMatrix_Client/
    └── Fleet-Connect-1/
```

**Action:** Copy directory from source location to `/home/greg/iMatrix/qfc`

```bash
cp -r $HOME/qconnect_sw/svc_sdk/source/qfc /home/greg/iMatrix/qfc
```

**Verification:**
```bash
ls -la /home/greg/iMatrix/qfc/arm_musl/libs/
```

---

### 3.2 Restore DebugGDB Build Type (Post-Merge)

After merging, restore the DebugGDB build configuration to CMakeLists.txt:

```cmake
# DebugGDB build type for optimal GDB debugging support
# This build type is specifically designed to make debugging mutex deadlocks easier
# by disabling all optimizations and preserving complete stack frame information
if(CMAKE_BUILD_TYPE STREQUAL "DebugGDB")
    set(CMAKE_C_FLAGS_DEBUGGDB "-g3 -O0 -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-inline -fno-inline-functions -DDEBUG_MUTEX_TRACKING" CACHE STRING "Flags for DebugGDB build" FORCE)
    set(CMAKE_CXX_FLAGS_DEBUGGDB "-g3 -O0 -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-inline -fno-inline-functions -DDEBUG_MUTEX_TRACKING" CACHE STRING "Flags for DebugGDB build" FORCE)
    message(STATUS "========================================")
    message(STATUS "DebugGDB Build Configuration Active")
    message(STATUS "========================================")
    message(STATUS "  Optimization:          -O0 (disabled)")
    message(STATUS "  Debug Info:            -g3 (maximum)")
    message(STATUS "  Frame Pointers:        Preserved")
    message(STATUS "  Sibling Calls:         Not optimized")
    message(STATUS "  Function Inlining:     Disabled")
    message(STATUS "  Mutex Tracking:        Enabled")
    message(STATUS "========================================")
    message(STATUS "Binary will be larger (~18MB) but GDB-friendly")
    message(STATUS "Stack traces will be complete and readable")
    message(STATUS "========================================")
endif()
```

**Location:** Insert after line 25 (after version extraction, before `# Application name`)

---

## 4. Merge Strategy

### 4.1 Approach: Temporary Test Branch with Post-Merge Fixes

1. Create symlink for QUAKE_LIBS
2. Create temporary test branches in both repositories
3. Merge `Aptera_1_Clean_fix` into temporary branches
4. Restore DebugGDB build type in Fleet-Connect-1
5. Verify local build succeeds
6. Seek user approval
7. Fast-forward merge temporary branches into `Aptera_1_Clean`
8. Delete temporary branches

### 4.2 Why This Approach?
- Preserves `Aptera_1_Clean` until validation complete
- Allows easy rollback if issues found
- Enables testing without affecting production branch
- Maintains DebugGDB capability for development

---

## 5. Implementation Todo List

### Phase 1: Preparation
- [ ] Copy directory: `cp -r $HOME/qconnect_sw/svc_sdk/source/qfc /home/greg/iMatrix/qfc`
- [ ] Verify copy works: `ls /home/greg/iMatrix/qfc/arm_musl/libs/`
- [ ] Confirm no uncommitted changes in either submodule

### Phase 2: Merge Execution
- [ ] Create temporary branch `temp-merge-test` in iMatrix
- [ ] Create temporary branch `temp-merge-test` in Fleet-Connect-1
- [ ] Merge `origin/Aptera_1_Clean_fix` into temp branches (iMatrix)
- [ ] Merge `origin/Aptera_1_Clean_fix` into temp branches (Fleet-Connect-1)
- [ ] Resolve any merge conflicts (if any)

### Phase 3: Post-Merge Fixes
- [ ] Restore DebugGDB build type section in Fleet-Connect-1/CMakeLists.txt
- [ ] Commit the DebugGDB restoration

### Phase 4: Build Verification
- [ ] Configure cmake for Fleet-Connect-1
- [ ] Build FC-1 binary
- [ ] Verify zero compilation errors
- [ ] Verify zero compilation warnings

### Phase 5: Final Merge (requires user approval)
- [ ] Get user approval on build success
- [ ] Fast-forward `Aptera_1_Clean` to temp branch (iMatrix)
- [ ] Fast-forward `Aptera_1_Clean` to temp branch (Fleet-Connect-1)
- [ ] Delete temporary branches
- [ ] Update parent repository submodule references

### Phase 6: Post-Merge
- [ ] Push changes to remote (on user approval)
- [ ] Document completion in this file

---

## 6. User Decisions Summary

| Question | Decision |
|----------|----------|
| QUAKE_LIBS path setup | Copy files from `$HOME/qconnect_sw/svc_sdk/source/qfc` to `/home/greg/iMatrix/qfc` |
| DebugGDB build type | **Restore after merge** - still needed for development |
| Jenkinsfile branch reference | Keep as `Aptera_1_Clean_fix` - no change needed |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| QUAKE_LIBS copy issues | Low | High | Verify copy before merge |
| Missing sysroot libraries | Low | High | Test build thoroughly |
| DebugGDB restoration error | Low | Low | Use exact original code |
| Jenkins build failure | Low | Medium | Path change supports Jenkins structure |

---

## 8. Approval

**Awaiting user approval before proceeding with implementation.**

Please confirm:
1. Copy approach for QUAKE_LIBS is acceptable
2. DebugGDB restoration plan is correct
3. Proceed with merge execution

---

## 9. Completion Summary

**Status:** COMPLETED SUCCESSFULLY

### Work Completed
1. Analyzed branch relationship - identified diverged branches requiring 3-way merge
2. Corrected initial misunderstanding about file deletions (were additions in target branch)
3. Copied qfc library files to `/home/greg/qfc/arm_musl/libs/`
4. Merged `Aptera_1_Clean_fix` into `Aptera_1_Clean` for both repositories
5. Restored DebugGDB build type in Fleet-Connect-1/CMakeLists.txt
6. Verified successful build with zero errors/warnings
7. Fast-forwarded `Aptera_1_Clean` branches to merged state

### Final Commit History

**iMatrix (Aptera_1_Clean):**
```
6c6beb47 Merge Aptera_1_Clean_fix: modem fix, ifplugd_fix.sh, OTA package fix
0be283f9 Update docs
5d6588e7 Fixed OTA package create.
```

**Fleet-Connect-1 (Aptera_1_Clean):**
```
563663d Restore DebugGDB build type after merge
d8ca31e Merge Aptera_1_Clean_fix: CMakeLists.txt path updates, version updates
5f4d491 updates for obd2 processing
```

### Metrics
- **Recompilations Required:** 2 (cmake cache cleanup needed)
- **Merge Conflicts:** 0
- **Build Result:** SUCCESS (FC-1 binary: 10.1 MB)

### Notes
- qfc libraries copied to `/home/greg/qfc/arm_musl/libs/` (existing empty directory populated)
- DebugGDB build type preserved for development debugging
- All existing files in Aptera_1_Clean preserved (README.md, docs, etc.)
- Changes NOT pushed to remote - awaiting user confirmation

---

**Plan Created By:** Claude Code Analysis
**Completed:** 2025-12-12
