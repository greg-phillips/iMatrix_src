# Submodule Sync Instructions for Build System

## Issue Resolution: wrp_config.c Compile Error

### Problem
Build system at `/home/quakeuser/qconnect_sw/svc_sdk/source/user/imatrix_dev/` shows error:
```
Fleet-Connect-1/init/wrp_config.c:56:52: fatal error: error_handler.h: No such file or directory
```

### Solution Applied
✅ **Fixed in commit:** `075533d` ("CE" - Compile Error fix)
✅ **Location:** Fleet-Connect-1/init/wrp_config.c
✅ **Changes made:**
- Removed `#include "error_handler.h"` from line 56
- Added local `error_severity_t` typedef (lines 61-66)
- Implemented standalone `log_error_message()` function (lines 86-108)
- Works for both CAN_DM and Fleet-Connect-1 codebases

### Sync Steps for Build System

#### On Development Machine (already done):
1. ✅ Fleet-Connect-1 updated to commit `075533d`
2. ✅ Fleet-Connect-1 pushed to origin/Aptera_1
3. 🔄 Parent repository update staged (ready to commit)

#### On Build System (`/home/quakeuser/...`):
```bash
cd /home/quakeuser/qconnect_sw/svc_sdk/source/user/imatrix_dev

# Pull latest changes from parent repository
git pull

# Update Fleet-Connect-1 submodule to commit 075533d
cd Fleet-Connect-1
git fetch origin
git checkout Aptera_1
git pull origin Aptera_1

# Verify correct commit
git log -1
# Should show: "commit 075533d97d16327d41351e7403123858399d4377"
# Message: "CE"

# Return to parent and update submodule reference
cd ..
git submodule update --init --recursive

# Clean build
cd Fleet-Connect-1/build
rm -rf *
cmake ..
make clean
make
```

### Verification
After sync, verify line 56 of wrp_config.c is blank:
```bash
cd Fleet-Connect-1/init
sed -n '50,70p' wrp_config.c
```

Expected output should show:
- Line 55: `#include "../../iMatrix/memory/imx_memory.h"`
- Line 56: (blank line)
- Line 60: `/* Local definition for error severity (from CAN_DM error_handler.h) */`

### Commit Details
- **Fleet-Connect-1 branch:** Aptera_1
- **Latest commit:** 992e573 (Remove LOGS_ENABLED from wrp_config.c)
- **Previous commits:**
  - 1843817 (Migrate CAN bus HW config to mgs structure)
  - 6e705f4 (Fix C89 compliance)
  - 075533d (Fix error_handler.h issue)
- **Starting commit:** e7bf15c69c3ddcf0ac0f99f2e320e17ac84cfb58
- **Total commits ahead:** 4 commits

### Fixes Included in Latest Commits

1. **075533d** - Missing error_handler.h
   - Made wrp_config.c standalone with local error handling

2. **6e705f4** - C89 compliance (label/declaration)
   - Moved variable declarations to top of scope

3. **1843817** - Global variable migration
   - Moved g_canbus_hw_config to mgs structure
   - Proper separation: config file I/O vs runtime state

4. **992e573** - LOGS_ENABLED macro dependency
   - Removed Fleet-Connect-1 specific macro from standalone file

### Alternative: Direct Checkout
If the above doesn't work, directly checkout the latest commit:
```bash
cd /home/quakeuser/qconnect_sw/svc_sdk/source/user/imatrix_dev/Fleet-Connect-1
git fetch origin
git checkout 992e573
```

---
**Note:** This fix makes wrp_config.c standalone, working for both CAN_DM and Fleet-Connect-1 without external dependencies.
