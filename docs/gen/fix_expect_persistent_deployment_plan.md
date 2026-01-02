# Plan: Fix Expect Deployment to Persistent Location

**Date**: 2026-01-02
**Author**: Claude Code
**Status**: COMPLETED
**Last Updated**: 2026-01-02

---

## Problem Statement

The expect program deployed via `scripts/fc1 cmd` is being lost after device reboot because:
1. `/usr/local` on the target is likely a volatile filesystem (tmpfs/ramdisk)
2. The SCP to `/tmp/` may be failing silently, causing tar extraction to fail

Error observed:
```
tar (child): /tmp/expect-arm.tar.gz: Cannot open: No such file or directory
sh: /usr/local/bin/expect-wrapper: not found
```

## Root Cause Analysis

On embedded systems like the QConnect gateway:
- `/tmp` is typically tmpfs (RAM-based, cleared on reboot)
- `/usr/local` may also be volatile or non-existent
- Persistent storage is usually limited to specific locations like `/usr/qk/`

## Solution

Deploy expect tools to `/usr/qk/etc/sv/FC-1/expect/` which is:
1. Already used by FC-1 (known persistent)
2. Logically grouped with FC-1 tooling
3. Within the existing service directory structure

## Implementation Plan

### Phase 1: Update fc1 Script

- [x] Change `REMOTE_EXPECT_DIR` from `/usr/local` to `/usr/qk/etc/sv/FC-1/expect`
- [x] Update expect-wrapper path references (uses relative paths, no change needed)
- [x] Add error checking for SCP operations
- [x] Test deployment

### Phase 2: Verify on Target

- [x] Verify expect deploys correctly
- [ ] Verify persists after reboot (pending - requires physical reboot)
- [x] Test `fc1 cmd` functionality

---

## Files Modified

| File | Changes |
|------|---------|
| `scripts/fc1` | Updated `REMOTE_EXPECT_DIR` to `/usr/qk/etc/sv/FC-1/expect`, improved `deploy_expect()` with better error handling |

---

## Implementation Summary

**Completed**: 2026-01-02

### Changes Made

1. **Updated `REMOTE_EXPECT_DIR`** (scripts/fc1:34):
   - Changed from `/usr/local` to `/usr/qk/etc/sv/FC-1/expect`
   - Added comment explaining the rationale for persistent storage

2. **Improved `deploy_expect()` function** (scripts/fc1:144-189):
   - Added SCP error checking with explicit failure messages
   - Added verification that file arrived on target before extraction
   - Added extraction error handling with cleanup
   - Added post-deployment verification of expect-wrapper

### Testing Results

Verified working commands:
```bash
scripts/fc1 cmd "?"    # Shows full CLI help
scripts/fc1 cmd "v"    # Shows version info
scripts/fc1 cmd "ms"   # Memory statistics
```

### Deployment Location

| Component | Path |
|-----------|------|
| expect binary | `/usr/qk/etc/sv/FC-1/expect/bin/expect` |
| expect-wrapper | `/usr/qk/etc/sv/FC-1/expect/bin/expect-wrapper` |
| libtcl8.6.so | `/usr/qk/etc/sv/FC-1/expect/lib/libtcl8.6.so` |
| Tcl init scripts | `/usr/qk/etc/sv/FC-1/expect/lib/tcl8.6/` |

---

## Approval Checklist

- [x] Approach documented
- [x] Implementation complete
- [x] Testing on hardware verified

