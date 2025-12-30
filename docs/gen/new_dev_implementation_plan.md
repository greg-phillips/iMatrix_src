# Implementation Plan: /new_dev Slash Command

**Date:** 2025-12-30
**Author:** Claude Code
**Status:** COMPLETED
**Source Specification:** docs/gen/new_dev_slash_command.md
**Completion Date:** 2025-12-30

---

## Executive Summary

Create a `/new_dev` slash command that automates development environment setup using git worktrees, copies Claude Code configuration, and validates the build. The command creates isolated working directories for parallel feature development.

---

## Current State Analysis

### Branch Status
| Repository | Current Branch | Target Branch |
|------------|---------------|---------------|
| iMatrix | Aptera_1_Clean | Aptera_1_Clean |
| Fleet-Connect-1 | Aptera_1_Clean | Aptera_1_Clean |
| btstack | imatrix_release | imatrix_release |
| mbedtls | detached HEAD (v3.6.2) | v3.6.2 |

### Key Discovery: Submodule Structure
The repositories are **git submodules**, not standalone repos. This affects worktree creation:
- Git directories are in `.git/modules/{repo}/`
- Worktrees must be created from the submodule's git directory
- Command: `git -C iMatrix_Client/{repo} worktree add ...`

### Files to Copy
| File/Directory | Exists | Required |
|----------------|--------|----------|
| .claude/ | Yes | Yes |
| CLAUDE.md | Yes | Yes |
| .cursorrules | No | No |
| .cursorignore | No | No |

### Build Environment
- ARM cross-compiler: `/opt/qconnect_sdk_musl/bin/arm-linux-gcc` (verified)
- Build system: CMake with automatic dependency detection
- Build type: **DebugGDB only** (full GDB debug symbols, ~18MB binary)

---

## Implementation Approach

### Slash Command Format
Based on existing `.claude/commands/build_imatrix_client_prompt.md`, slash commands are:
- Markdown files in `.claude/commands/`
- Contain instructions for Claude to execute
- Filename becomes command name (minus `.md`)

### Command File
**Path:** `.claude/commands/new_dev.md`

### Command Usage
```
/new_dev <environment_name> [options]
```

### Required Options (Mandatory Implementation)

| Option | Description |
|--------|-------------|
| `--no-build` | Skip build validation (just create worktrees + copy config) |
| `--clean` | Remove existing environment before creating new one |
| `--dry-run` | Preview what would be created without making changes |

### Build Configuration
- **Build Type:** DebugGDB (always, no alternatives)
- All builds use full GDB debug symbols for debugging support

---

## Option Behavior Specifications

### `--dry-run`
When specified:
1. Display all actions that would be taken
2. Show directories that would be created
3. Show worktree commands that would be executed
4. Show files that would be copied
5. Show build commands that would be run (unless --no-build)
6. **Do NOT make any changes to the filesystem**

Example output:
```
DRY RUN - No changes will be made

Would create directory: ~/iMatrix/my_feature
Would create worktree: iMatrix → Aptera_1_Clean
Would create worktree: Fleet-Connect-1 → Aptera_1_Clean
Would create worktree: btstack → imatrix_release
Would create worktree: mbedtls → v3.6.2
Would copy: .claude/ → ~/iMatrix/my_feature/.claude/
Would copy: CLAUDE.md → ~/iMatrix/my_feature/CLAUDE.md
Would build: Fleet-Connect-1 (DebugGDB)
```

### `--clean`
When specified:
1. Check if target environment directory exists
2. If exists, properly remove all worktrees first:
   ```bash
   git -C ~/iMatrix/iMatrix_Client/{repo} worktree remove ~/iMatrix/{env_name}/{repo}
   ```
3. Remove the environment directory
4. Proceed with normal creation

**Warning:** This is destructive - any uncommitted changes in the environment will be lost.

### `--no-build`
When specified:
1. Create worktrees normally
2. Copy configuration files normally
3. Skip the build phase entirely
4. Adjust success output to indicate build was skipped

---

## Detailed Implementation Plan

### Phase 1: Create Slash Command File

#### Task 1.1: Create new_dev.md
Create `.claude/commands/new_dev.md` with:
- Command description and usage
- Step-by-step instructions for Claude to follow
- Error handling guidance
- Output format specifications

### Phase 2: Environment Validation Logic

#### Task 2.1: Pre-flight Checks
The command should validate:
1. Environment name is provided and valid (alphanumeric + underscore)
2. Target directory doesn't already exist (or --clean flag)
3. Source repositories exist in iMatrix_Client
4. Required branches exist in each repo
5. .claude directory exists in source
6. ARM cross-compiler is available

#### Task 2.2: Error Messages
Define clear error messages for each validation failure.

### Phase 3: Worktree Creation Logic

#### Task 3.1: Repository Worktree Commands
For each repository, the command sequence is:

```bash
# For submodule repos (iMatrix, Fleet-Connect-1)
git -C ~/iMatrix/iMatrix_Client/{repo} worktree add \
    ~/iMatrix/{env_name}/{repo} {branch}

# For regular repos (btstack, mbedtls)
git -C ~/iMatrix/iMatrix_Client/{repo} worktree add \
    ~/iMatrix/{env_name}/{repo} {branch}
```

#### Task 3.2: Repository Configuration
| Repository | Branch | Notes |
|------------|--------|-------|
| iMatrix | Aptera_1_Clean | Core library |
| Fleet-Connect-1 | Aptera_1_Clean | Main application |
| btstack | imatrix_release | Bluetooth stack |
| mbedtls | v3.6.2 | TLS library |

### Phase 4: Configuration Copy Logic

#### Task 4.1: Copy Commands
```bash
# Create destination directory
mkdir -p ~/iMatrix/{env_name}

# Copy .claude directory (required)
cp -r ~/iMatrix/iMatrix_Client/.claude ~/iMatrix/{env_name}/

# Copy CLAUDE.md
cp ~/iMatrix/iMatrix_Client/CLAUDE.md ~/iMatrix/{env_name}/
```

### Phase 5: Build Validation Logic

#### Task 5.1: Build Sequence
```bash
cd ~/iMatrix/{env_name}/Fleet-Connect-1
rm -rf build
mkdir build && cd build
cmake .. 2>&1 | tee cmake_config.log
make -j4 2>&1 | tee build.log
```

#### Task 5.2: Validation Checks
1. Verify `FC-1` binary exists
2. Verify ARM architecture: `file FC-1` should show "ARM, EABI5"
3. Count errors and warnings from build output
4. Calculate binary size

### Phase 6: Output Format

#### Task 6.1: Success Output
```
══════════════════════════════════════════════════════════════════
NEW DEVELOPMENT ENVIRONMENT CREATED
══════════════════════════════════════════════════════════════════
Environment: {env_name}
Location:    ~/iMatrix/{env_name}

REPOSITORY STATUS:
  ✓ iMatrix          → Aptera_1_Clean
  ✓ Fleet-Connect-1  → Aptera_1_Clean
  ✓ btstack          → imatrix_release
  ✓ mbedtls          → v3.6.2

CLAUDE CODE CONFIGURATION:
  ✓ .claude/         (slash commands, settings)
  ✓ CLAUDE.md        (project context)

BUILD RESULTS:
  Status:     PASS
  Build Type: DebugGDB
  Binary:     FC-1 (ARM EABI5)
  Size:       XX MB
  Errors:     0
  Warnings:   0

Ready to use:
  cd ~/iMatrix/{env_name} && cursor .
══════════════════════════════════════════════════════════════════
```

---

## Todo List

### Pre-Implementation
- [ ] Create feature branch for this work

### Implementation
- [ ] Create `.claude/commands/new_dev.md` with command structure
- [ ] Add argument parsing for environment_name and options
- [ ] Implement `--dry-run` option (preview mode)
- [ ] Implement `--clean` option (remove existing environment)
- [ ] Implement `--no-build` option (skip build validation)
- [ ] Add Phase 1: Pre-flight validation instructions
- [ ] Add Phase 2: Environment directory creation
- [ ] Add Phase 3: Worktree creation for all 4 repos
- [ ] Add Phase 4: Claude configuration copy
- [ ] Add Phase 5: Build execution and validation (DebugGDB only)
- [ ] Add Phase 6: Output formatting

### Testing
- [ ] Test `--dry-run` option shows preview without changes
- [ ] Test basic command with a sample environment name
- [ ] Test `--clean` option removes existing environment
- [ ] Test `--no-build` option skips build phase
- [ ] Verify worktrees are created correctly
- [ ] Verify .claude directory is copied
- [ ] Verify build completes successfully (DebugGDB)
- [ ] Verify FC-1 binary is ARM EABI5
- [ ] Test error handling (existing directory, missing branch, etc.)

### Documentation
- [ ] Update this plan with implementation notes
- [ ] Add usage examples to command file

### Cleanup
- [ ] Remove test environment(s) created during testing
- [ ] Merge feature branch back to main

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Worktree fails for submodule | Medium | High | Test with actual submodule structure first |
| Build fails in new environment | Low | Medium | Preserve environment for debugging |
| Branch doesn't exist | Low | High | Validate branch existence before creating worktrees |
| Disk space issues | Low | Low | Check available space before starting |

---

## Future Enhancements (Post-MVP)

These can be added later if needed:
- `--branch <name>` flag to use different branch for all repos
- `--jobs N` flag to control parallel compilation (default: 4)
- `/remove_dev <environment_name>` companion command to properly remove worktrees

---

## Files to Create/Modify

| Path | Action | Description |
|------|--------|-------------|
| `.claude/commands/new_dev.md` | Create | The slash command implementation |

---

## Estimated Complexity

- **Lines of code:** ~150-200 lines (markdown with bash commands)
- **Testing cycles:** 2-3 (initial test, fix issues, final validation)
- **Build validations:** 1 clean build in test environment

---

## Approval Checklist

Please review and confirm:

- [ ] Implementation approach is acceptable
- [ ] Worktree-based isolation is the right choice
- [ ] Required options are correct: `--no-build`, `--clean`, `--dry-run`
- [ ] DebugGDB-only build policy is correct
- [ ] Output format meets expectations
- [ ] Todo list covers all requirements

---

## Implementation Completion Summary

### Work Completed

1. **Created `/new_dev` slash command** at `.claude/commands/new_dev.md` (370+ lines)
   - Full argument parsing for environment_name and options
   - All three required options implemented: `--dry-run`, `--clean`, `--no-build`
   - Comprehensive step-by-step instructions for Claude to follow
   - Error handling for all failure scenarios
   - Formatted output for success and failure cases

2. **Key Technical Discoveries & Fixes:**
   - Git worktrees require `--detach` flag when branches are already checked out in main repo
   - mbedtls has a `framework` submodule that must be initialized in new worktrees
   - mbedtls build requires `-DENABLE_TESTING=OFF` to avoid Python 3 dependency
   - Tag `v3.6.2` used instead of `mbedtls-3.6.2` (correct tag format)

3. **Testing Performed:**
   - Validated worktree creation for all 4 repositories
   - Verified submodule initialization for mbedtls
   - Confirmed full build success (FC-1 binary: 13MB, ARM EABI5)
   - Tested cleanup of worktrees

### Files Created/Modified

| File | Action | Lines |
|------|--------|-------|
| `.claude/commands/new_dev.md` | Created | 370+ |
| `docs/gen/new_dev_implementation_plan.md` | Updated | ~300 |

### Metrics

- **Recompilations for syntax errors:** 0
- **Build test result:** PASS (FC-1 13MB ARM EABI5)
- **Test environment cleanup:** Successful

### Branch Information

- **Feature branch:** `feature/new_dev_slash_command`
- **Base branch:** `main`

---

**Implementation Complete.**
