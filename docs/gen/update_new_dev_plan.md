# Plan: Update /new_dev Slash Command

**Date**: 2025-12-30
**Status**: Completed
**Source**: `/home/greg/iMatrix/iMatrix_Client/docs/gen/new_dev_improvements.md`
**Target**: `/home/greg/iMatrix/iMatrix_Client/.claude/commands/new_dev.md`

---

## Overview

Update the `/new_dev` slash command to fix incorrect paths discovered during execution and optionally add improvements for faster environment creation.

---

## Required Fixes (High Priority)

### Fix 1: Correct mbedTLS Path Check

**Location**: Step 3.5, lines 113-114

**Current (Incorrect)**:
```bash
# 3. mbedTLS Built Libraries (REQUIRED)
MBEDTLS_OK=false
[ -d ~/iMatrix/iMatrix_Client/mbedtls/build_arm ] && MBEDTLS_OK=true
```

**Corrected**:
```bash
# 3. mbedTLS Built Libraries (REQUIRED)
MBEDTLS_OK=false
[ -f ~/iMatrix/iMatrix_Client/mbedtls/build/library/libmbedtls.a ] && MBEDTLS_OK=true
```

**Also update these references**:
- Line 135: Status display path
- Line 250: Dry-run display path
- Lines 539-546: Error message for mbedTLS not built

---

### Fix 2: Correct build_mbedtls.sh Path

**Location**: Step 3.5, lines 199-203

**Current (Incorrect)**:
```bash
If user selects option 1, run:
cd ~/iMatrix/iMatrix_Client/Fleet-Connect-1
./build_mbedtls.sh
```

**Corrected**:
```bash
If user selects option 1, run:
cd ~/iMatrix/iMatrix_Client/iMatrix
./build_mbedtls.sh
```

**Also update these references**:
- Lines 543-544: Error message instructions

---

## Summary of All Path Corrections

| Section | Line(s) | Current Value | Correct Value |
|---------|---------|---------------|---------------|
| Step 3.5 check | 114 | `mbedtls/build_arm` | `mbedtls/build/library/libmbedtls.a` |
| Step 3.5 status | 135 | `mbedtls/build_arm/` | `mbedtls/build/library/` |
| Step 4 dry-run | 250 | `mbedtls/build_arm/` | `mbedtls/build/library/` |
| Step 3.5 build cmd | 200-201 | `Fleet-Connect-1` | `iMatrix` |
| Error message | 539 | `mbedtls/build_arm/` | `mbedtls/build/library/` |
| Error instructions | 543-544 | `Fleet-Connect-1` | `iMatrix` |

---

## Optional Improvements (Medium Priority)

### Improvement 1: Add `--auto-deps` Flag

**Location**: Step 1 (argument parsing), Step 3.5 (dependency handling)

**Changes**:
1. Add to options list:
   ```
   --auto-deps: Automatically install missing dependencies without prompting
   ```

2. Modify Step 3.5 behavior:
   - If `--auto-deps` is set and mbedTLS missing → build automatically
   - If `--auto-deps` is set and CMSIS-DSP missing → clone automatically
   - Skip AskUserQuestion prompts for installable dependencies

---

### Improvement 2: Add Timing Breakdown (Low Priority)

**Location**: Step 10 (results display)

**Add timing output**:
```
TIMING BREAKDOWN:
  Pre-flight checks:     X.Xs
  Worktree creation:     X.Xs
  Submodule init:        X.Xs
  Configuration copy:    X.Xs
  Build:                XX.Xs
  ─────────────────────────────
  Total:                XX.Xs
```

---

## Implementation Steps

### Phase 1: Required Fixes

1. [x] Edit line 114: Change `build_arm` directory check to `build/library/libmbedtls.a` file check
2. [x] Edit line 135: Update status display path
3. [x] Edit line 250: Update dry-run display path
4. [x] Edit lines 200-201: Change `Fleet-Connect-1` to `iMatrix`
5. [x] Edit line 539: Update error message path
6. [x] Edit lines 543-544: Update error message instructions
7. [x] Edit line 188: Update AskUserQuestion prompt path (additional fix found)

### Phase 2: Optional Improvements (If Requested)

7. [ ] Add `--auto-deps` flag to usage section
8. [ ] Add `--auto-deps` to argument parsing (Step 1)
9. [ ] Modify Step 3.5 to auto-install when flag is set
10. [ ] Add timing breakdown to output (Step 10)

---

## Verification

After updates, verify with:
```bash
/new_dev test_verification --dry-run
```

Check that:
- mbedTLS path shows `mbedtls/build/library/`
- build_mbedtls.sh instructions show `iMatrix/` directory

---

## Files Modified

| File | Changes |
|------|---------|
| `.claude/commands/new_dev.md` | Path corrections (6 locations) |

---

## Rollback

If issues arise, restore from git:
```bash
git checkout HEAD -- .claude/commands/new_dev.md
```
