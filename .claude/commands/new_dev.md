Create a new isolated development environment using git worktrees.

## Usage

```
/new_dev <environment_name> [options]
```

**Arguments:**
- `<environment_name>`: Name for the new environment (alphanumeric and underscores only)
  - Examples: `canbus_refactor`, `bluetooth_fix`, `feature_xyz`

**Options:**
- `--no-build`: Skip build validation (just create worktrees + copy config)
- `--clean`: Remove existing environment before creating new one
- `--dry-run`: Preview what would be created without making changes

**Examples:**
```
/new_dev my_feature
/new_dev bluetooth_fix --no-build
/new_dev canbus_work --clean
/new_dev test_env --dry-run
/new_dev new_feature --clean --no-build
```

---

## Execution Instructions

When this command is invoked, follow these steps precisely:

### Step 1: Parse Arguments

Extract from the command arguments:
1. `environment_name` - the first non-option argument (required)
2. `--dry-run` flag - if present, only show what would be done
3. `--clean` flag - if present, remove existing environment first
4. `--no-build` flag - if present, skip the build phase

**Validation:**
- Environment name must match pattern: `^[a-zA-Z][a-zA-Z0-9_]*$`
- Environment name is required - fail with helpful error if missing

### Step 2: Define Constants

Use these exact paths and values:

```bash
SOURCE_DIR=~/iMatrix/iMatrix_Client
DEST_DIR=~/iMatrix/${environment_name}
```

**Repository Configuration:**
| Repository | Branch | Source Path |
|------------|--------|-------------|
| iMatrix | Aptera_1_Clean | ${SOURCE_DIR}/iMatrix |
| Fleet-Connect-1 | Aptera_1_Clean | ${SOURCE_DIR}/Fleet-Connect-1 |
| btstack | imatrix_release | ${SOURCE_DIR}/btstack |
| mbedtls | v3.6.2 | ${SOURCE_DIR}/mbedtls |

### Step 3: Pre-flight Validation

Verify before proceeding (skip if --dry-run):

1. **Source directory exists:**
   ```bash
   ls -d ~/iMatrix/iMatrix_Client
   ```

2. **All source repositories exist:**
   ```bash
   ls -d ~/iMatrix/iMatrix_Client/iMatrix
   ls -d ~/iMatrix/iMatrix_Client/Fleet-Connect-1
   ls -d ~/iMatrix/iMatrix_Client/btstack
   ls -d ~/iMatrix/iMatrix_Client/mbedtls
   ```

3. **.claude directory exists (required):**
   ```bash
   ls -d ~/iMatrix/iMatrix_Client/.claude
   ```

4. **Target directory check:**
   - If `${DEST_DIR}` exists AND `--clean` NOT specified: FAIL with error
   - If `${DEST_DIR}` exists AND `--clean` specified: proceed to cleanup

5. **ARM cross-compiler exists (skip if --no-build):**
   ```bash
   ls /opt/qconnect_sdk_musl/bin/arm-linux-gcc
   ```

### Step 4: Handle --dry-run

If `--dry-run` is specified, display the following and EXIT (do not make any changes):

```
══════════════════════════════════════════════════════════════════
DRY RUN - No changes will be made
══════════════════════════════════════════════════════════════════

Environment: ${environment_name}
Location:    ~/iMatrix/${environment_name}

ACTIONS THAT WOULD BE TAKEN:

1. Create directory: ~/iMatrix/${environment_name}

2. Create worktrees (detached HEAD mode):
   git -C ~/iMatrix/iMatrix_Client/iMatrix worktree add --detach ~/iMatrix/${environment_name}/iMatrix Aptera_1_Clean
   git -C ~/iMatrix/iMatrix_Client/Fleet-Connect-1 worktree add --detach ~/iMatrix/${environment_name}/Fleet-Connect-1 Aptera_1_Clean
   git -C ~/iMatrix/iMatrix_Client/btstack worktree add --detach ~/iMatrix/${environment_name}/btstack imatrix_release
   git -C ~/iMatrix/iMatrix_Client/mbedtls worktree add --detach ~/iMatrix/${environment_name}/mbedtls v3.6.2

3. Initialize mbedtls submodules:
   git -C ~/iMatrix/${environment_name}/mbedtls submodule update --init --recursive

4. Copy configuration:
   cp -r ~/iMatrix/iMatrix_Client/.claude ~/iMatrix/${environment_name}/
   cp ~/iMatrix/iMatrix_Client/CLAUDE.md ~/iMatrix/${environment_name}/

5. Build (DebugGDB):
   cd ~/iMatrix/${environment_name}/Fleet-Connect-1
   mkdir build && cd build
   cmake .. -DENABLE_TESTING=OFF
   make -j4

══════════════════════════════════════════════════════════════════
Run without --dry-run to execute these actions.
══════════════════════════════════════════════════════════════════
```

If `--no-build` is also specified, replace step 5 with:
```
5. Build: SKIPPED (--no-build specified)
```

### Step 5: Handle --clean

If `--clean` is specified AND target directory exists:

1. **Remove worktrees properly** (in this order):
   ```bash
   git -C ~/iMatrix/iMatrix_Client/iMatrix worktree remove ~/iMatrix/${environment_name}/iMatrix --force 2>/dev/null || true
   git -C ~/iMatrix/iMatrix_Client/Fleet-Connect-1 worktree remove ~/iMatrix/${environment_name}/Fleet-Connect-1 --force 2>/dev/null || true
   git -C ~/iMatrix/iMatrix_Client/btstack worktree remove ~/iMatrix/${environment_name}/btstack --force 2>/dev/null || true
   git -C ~/iMatrix/iMatrix_Client/mbedtls worktree remove ~/iMatrix/${environment_name}/mbedtls --force 2>/dev/null || true
   ```

2. **Remove directory:**
   ```bash
   rm -rf ~/iMatrix/${environment_name}
   ```

3. **Prune stale worktrees:**
   ```bash
   git -C ~/iMatrix/iMatrix_Client/iMatrix worktree prune
   git -C ~/iMatrix/iMatrix_Client/Fleet-Connect-1 worktree prune
   git -C ~/iMatrix/iMatrix_Client/btstack worktree prune
   git -C ~/iMatrix/iMatrix_Client/mbedtls worktree prune
   ```

Display: `Cleaned existing environment: ${environment_name}`

### Step 6: Create Environment Directory

```bash
mkdir -p ~/iMatrix/${environment_name}
```

### Step 7: Create Worktrees

Execute each command and verify success. Use `--detach` to allow multiple worktrees at the same commit:

```bash
# iMatrix (detached HEAD at Aptera_1_Clean)
git -C ~/iMatrix/iMatrix_Client/iMatrix worktree add --detach ~/iMatrix/${environment_name}/iMatrix Aptera_1_Clean

# Fleet-Connect-1 (detached HEAD at Aptera_1_Clean)
git -C ~/iMatrix/iMatrix_Client/Fleet-Connect-1 worktree add --detach ~/iMatrix/${environment_name}/Fleet-Connect-1 Aptera_1_Clean

# btstack (detached HEAD at imatrix_release)
git -C ~/iMatrix/iMatrix_Client/btstack worktree add --detach ~/iMatrix/${environment_name}/btstack imatrix_release

# mbedtls (detached HEAD at v3.6.2)
git -C ~/iMatrix/iMatrix_Client/mbedtls worktree add --detach ~/iMatrix/${environment_name}/mbedtls v3.6.2
```

**Note:** Worktrees are created in detached HEAD mode to avoid conflicts when the same branch is checked out in iMatrix_Client.

**Error handling:** If any worktree creation fails, display the error and stop.

### Step 7.5: Initialize Submodules

mbedtls has a framework submodule that must be initialized:

```bash
git -C ~/iMatrix/${environment_name}/mbedtls submodule update --init --recursive
```

### Step 8: Copy Claude Configuration

```bash
# Copy .claude directory (required)
cp -r ~/iMatrix/iMatrix_Client/.claude ~/iMatrix/${environment_name}/

# Copy CLAUDE.md if it exists
[ -f ~/iMatrix/iMatrix_Client/CLAUDE.md ] && cp ~/iMatrix/iMatrix_Client/CLAUDE.md ~/iMatrix/${environment_name}/

# Copy cursor files if they exist
[ -f ~/iMatrix/iMatrix_Client/.cursorrules ] && cp ~/iMatrix/iMatrix_Client/.cursorrules ~/iMatrix/${environment_name}/
[ -f ~/iMatrix/iMatrix_Client/.cursorignore ] && cp ~/iMatrix/iMatrix_Client/.cursorignore ~/iMatrix/${environment_name}/
```

### Step 9: Build (Skip if --no-build)

If `--no-build` is NOT specified:

```bash
cd ~/iMatrix/${environment_name}/Fleet-Connect-1
rm -rf build
mkdir build
cd build
cmake .. -DENABLE_TESTING=OFF 2>&1 | tee ~/iMatrix/${environment_name}/cmake_config.log
make -j4 2>&1 | tee ~/iMatrix/${environment_name}/build.log
```

**Note:** `-DENABLE_TESTING=OFF` disables mbedTLS test suite building which requires Python 3.

**Capture build results:**
- Check if `FC-1` binary exists
- Get binary size: `ls -lh FC-1`
- Verify architecture: `file FC-1` (should show "ARM, EABI5")
- Count errors: `grep -c "error:" build.log || echo 0`
- Count warnings: `grep -c "warning:" build.log || echo 0`

### Step 10: Display Results

**Success output (with build):**

```
══════════════════════════════════════════════════════════════════
NEW DEVELOPMENT ENVIRONMENT CREATED
══════════════════════════════════════════════════════════════════
Environment: ${environment_name}
Location:    ~/iMatrix/${environment_name}

REPOSITORY STATUS:
  [checkmark] iMatrix          -> Aptera_1_Clean
  [checkmark] Fleet-Connect-1  -> Aptera_1_Clean
  [checkmark] btstack          -> imatrix_release
  [checkmark] mbedtls          -> v3.6.2

CLAUDE CODE CONFIGURATION:
  [checkmark] .claude/         (slash commands, settings)
  [checkmark] CLAUDE.md        (project context)

BUILD RESULTS:
  Status:     PASS
  Build Type: DebugGDB
  Binary:     FC-1 (ARM EABI5)
  Size:       ${size}
  Errors:     ${error_count}
  Warnings:   ${warning_count}

ARM Cross-Compiler: /opt/qconnect_sdk_musl/bin/arm-linux-gcc
══════════════════════════════════════════════════════════════════

Ready to use! Open this directory in Cursor/VS Code:
  cd ~/iMatrix/${environment_name} && cursor .

══════════════════════════════════════════════════════════════════
```

**Success output (with --no-build):**

```
══════════════════════════════════════════════════════════════════
NEW DEVELOPMENT ENVIRONMENT CREATED
══════════════════════════════════════════════════════════════════
Environment: ${environment_name}
Location:    ~/iMatrix/${environment_name}

REPOSITORY STATUS:
  [checkmark] iMatrix          -> Aptera_1_Clean
  [checkmark] Fleet-Connect-1  -> Aptera_1_Clean
  [checkmark] btstack          -> imatrix_release
  [checkmark] mbedtls          -> v3.6.2

CLAUDE CODE CONFIGURATION:
  [checkmark] .claude/         (slash commands, settings)
  [checkmark] CLAUDE.md        (project context)

BUILD: SKIPPED (--no-build specified)

To build manually:
  cd ~/iMatrix/${environment_name}/Fleet-Connect-1
  mkdir build && cd build
  cmake .. -DENABLE_TESTING=OFF && make -j4

══════════════════════════════════════════════════════════════════

Ready to use! Open this directory in Cursor/VS Code:
  cd ~/iMatrix/${environment_name} && cursor .

══════════════════════════════════════════════════════════════════
```

---

## Error Messages

**Missing environment name:**
```
ERROR: Environment name is required

Usage: /new_dev <environment_name> [options]

Options:
  --no-build  Skip build validation
  --clean     Remove existing environment first
  --dry-run   Preview actions without making changes

Example: /new_dev my_feature
```

**Invalid environment name:**
```
ERROR: Invalid environment name: "${environment_name}"

Environment name must:
  - Start with a letter
  - Contain only letters, numbers, and underscores
  - Examples: my_feature, bluetooth_fix, feature_v2
```

**Environment already exists (without --clean):**
```
ERROR: Environment already exists: ~/iMatrix/${environment_name}

Options:
  1. Use --clean to remove and recreate: /new_dev ${environment_name} --clean
  2. Choose a different name
  3. Manually remove: rm -rf ~/iMatrix/${environment_name}
```

**Source repository missing:**
```
ERROR: Source repository not found: ~/iMatrix/iMatrix_Client/${repo}

Ensure all repositories are properly cloned in iMatrix_Client.
```

**ARM compiler not found:**
```
ERROR: ARM cross-compiler not found at /opt/qconnect_sdk_musl/bin/arm-linux-gcc

The build cannot proceed without the ARM toolchain.
Use --no-build to skip build validation.
```

**Build failed:**
```
ERROR: Build failed with ${error_count} errors

Build logs saved to:
  - ~/iMatrix/${environment_name}/cmake_config.log
  - ~/iMatrix/${environment_name}/build.log

Environment preserved for debugging.
```
