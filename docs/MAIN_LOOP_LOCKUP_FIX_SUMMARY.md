# Main Loop Lockup Fix - Summary

**Date:** November 16, 2025
**Branch:** bugfix/network-stability
**Status:** ✓ RESOLVED AND VERIFIED
**Test Result:** 24+ minutes stable operation

---

## Problem

Main loop froze after 4-8 minutes of operation:
- Timer stopped executing (last run 3-10 minutes ago)
- GPS circular buffer overflow errors
- System responsive via PTY but main processing frozen
- Appeared to be mutex deadlock but mutex tracking showed 0 locks

---

## Root Cause

**GPS Data Race Conditions** (not mutex deadlock):

1. **Circular Buffer Race:**
   - GPS thread reinitialized buffer while main loop was reading
   - Main loop entered infinite loop with corrupted buffer state
   - No synchronization between threads

2. **Global Variable Race:**
   - GPS variables written WITHOUT mutex in process_nmea.c
   - Same variables read WITH mutex in get_location.c
   - Violated fundamental mutex protection rules

---

## Solution

### 1. Mutex Tracking Infrastructure
- Created comprehensive mutex tracking system
- Tracks 7 mutexes: lock holders, durations, contentions
- CLI command: `mutex` and `mutex verbose`
- Compile-time optional (ENABLE_MUTEX_TRACKING)

### 2. Breadcrumb Diagnostics
- 40+ execution tracking points across call stack
- Handler → imx_process → do_everything → GPS processing
- CLI command: `loopstatus` shows exact blocking location
- Critical for pinpointing GPS issue at position 6712

### 3. GPS Circular Buffer Protection
- Added `nmeaCB_mutex` protecting buffer operations
- GPS thread locks during write/reinit
- Main loop locks during read
- Prevents corruption from concurrent access

### 4. GPS Data Mutex Protection
- Exported `gps_data_mutex` from get_location.c
- Protected ALL GPS variable writes in process_nmea.c
- Variables: latitude, longitude, altitude, fixQuality, horizontalDilution, course, magnetic_variation
- Ensured consistent mutex usage

### 5. Satellite Data Protection
- Added tracking for `satellite_mutex`
- Protects satellite array updates
- Now visible in mutex tracking

---

## Files Changed

**New Files (2):**
- iMatrix/platform_functions/mutex_tracker.h
- iMatrix/platform_functions/mutex_tracker.c

**Modified Files (16):**

*iMatrix Submodule:*
- CMakeLists.txt
- cli/cli.c, cli_commands.c, cli_commands.h
- IMX_Platform/LINUX_Platform/networking/process_network.c
- imatrix_interface.c
- location/get_location.c, get_location.h, process_nmea.c
- quake/quake_gps.c
- cs_ctrl/hal_sample.c

*Fleet-Connect-1 Submodule:*
- linux_gateway.c
- do_everything.c, do_everything.h
- cli/fcgw_cli.c, fcgw_cli.h

---

## Verification

**Mutex Health:**
- 7 mutexes tracked
- 19,350+ lock operations
- 0.02% contention rate
- 0 currently locked (healthy)

**System Stability:**
- 24+ minutes continuous operation
- No lockups
- No GPS buffer errors
- All threads running normally

**Diagnostics Working:**
- `mutex verbose` shows detailed statistics
- `loopstatus` tracks execution positions
- `threads -v` shows thread health

---

## Tools for Future Debugging

### mutex Command
```
> mutex              # Show currently locked mutexes
> mutex verbose      # Show all mutexes with full statistics
```

**Shows:** Lock holder (function/file/line), duration, contentions, statistics

### loopstatus Command
```
> app
app> loopstatus      # Show main loop breadcrumb position
```

**Shows:** Handler position, imx_process position, do_everything position, timing

**Use when:** Main loop appears frozen or slow

### Breadcrumb Position Codes

Quick reference for common positions:
- **0-3**: Handler (before/after imx_process, before/after do_everything)
- **30**: Before process_network() in NORMAL state
- **50**: Before imatrix_upload()
- **67**: Before process_location()
- **6710-6715**: Inside process_nmea()
- **67120+**: Inside process_nmea_sentence()

---

## Lessons Learned

1. **Breadcrumb diagnostics are game-changers** - Identified exact blocking location in massive codebase
2. **Not all blocking is deadlock** - Race conditions can freeze systems without mutex cycles
3. **Multiple mutex systems complicate debugging** - Had pthread, imx_mutex_t, and tracking wrappers
4. **Consistent mutex usage is critical** - ALL accesses (read AND write) must use same mutex
5. **Test systematically** - Each breadcrumb refinement narrowed the search space

---

## Network Stability Work Remaining

**See:** `docs/network_stability_handoff.md`

Issues to fix:
1. State machine transition deadlock (NET_SELECT_INTERFACE → NET_INIT)
2. PPP0 connection failures (connect script failing)
3. WiFi unnecessary disconnections (needs 15s grace period)
4. Interface selection logic (not finding valid interfaces)

All diagnostic tools in place. System stable. Ready for network debugging phase.

---

**Status:** MAIN LOOP LOCKUP - RESOLVED ✓
**Next Phase:** Network Stability Fixes
**Branch:** bugfix/network-stability (ready for network work)
