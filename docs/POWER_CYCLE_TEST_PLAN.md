# Power Cycle Test Plan: Data Erasure Verification

**Date**: 2026-01-02
**Last Updated**: 2026-01-02 19:32
**Purpose**: Verify SIGTERM handler properly erases all data on shutdown for clean testing restarts
**Status**: ✅ TEST PASSED

---

## Overview

This test plan validates the **clean shutdown for testing** functionality:
1. SIGTERM signal handler is registered at startup
2. RAM data is **erased** during controlled shutdown (for clean testing)
3. Disk files are **erased** during controlled shutdown
4. System starts with clean state (0 records, 0 disk files)

**Note**: This is for **testing purposes** - data is intentionally erased, not preserved.

---

## Pre-Test Checklist

Before starting the test:

- [ ] FC-1 is running with tiered storage active (RAM >= 80%)
- [ ] Disk files exist in `/tmp/mm2/` directories
- [ ] Note current `ms disk` output (file count, total size)
- [ ] Note current `ms` summary (pending records, total records)
- [ ] Save current log file for comparison

---

## Phase 1: Pre-Shutdown Baseline

### Step 1.1: Capture Current State

```bash
# Connect to device
ssh -p 22222 root@192.168.7.1

# Capture memory status
echo "ms" | nc localhost 23 > /tmp/pre_shutdown_ms.txt

# Capture disk status
echo "ms disk" | nc localhost 23 > /tmp/pre_shutdown_disk.txt

# List all disk files with sizes
find /tmp/mm2 -type f -exec ls -la {} \; > /tmp/pre_shutdown_files.txt

# Calculate total disk usage
du -sh /tmp/mm2/

# Copy log file
cp /var/log/fc-1.log /tmp/pre_shutdown.log
```

### Step 1.2: Record Key Metrics

| Metric | Value |
|--------|-------|
| RAM sectors used | |
| RAM sectors free | |
| Total pending records | |
| Total records | |
| Disk files count | |
| Disk space used | |
| Active sensors | |

---

## Phase 2: Controlled Shutdown

### Step 2.1: Initiate Shutdown

```bash
# Stop FC-1 service (triggers shutdown sequence)
sv stop FC-1

# Wait for shutdown to complete
sleep 5

# Verify FC-1 stopped
sv status FC-1
```

### Step 2.2: Expected Shutdown Log Messages

Look for these messages in the log during shutdown:

```
# Shutdown initiation
[SHUTDOWN] FC-1 shutdown initiated
[SHUTDOWN] Starting graceful shutdown sequence

# Memory flush operations
[MM2] Flushing RAM data to disk...
[MM2-FLUSH] Flushing sensor X to disk
[MM2-FLUSH] Wrote N records to disk for sensor X
[TIERED] Flushed N sectors to disk

# File finalization
[MM2-DISK] Closing active spool file: /tmp/mm2/...
[MM2-DISK] File finalized: X bytes written

# Shutdown complete
[SHUTDOWN] Graceful shutdown complete
[MM2] All data flushed to disk
```

### Step 2.3: Verify Shutdown Logs

```bash
# Check shutdown sequence in log
grep -E "SHUTDOWN|FLUSH|Closing.*spool|finalized" /var/log/fc-1.log | tail -50
```

---

## Phase 3: Post-Shutdown Verification

### Step 3.1: Verify Disk Files Exist

```bash
# List all spool files
find /tmp/mm2 -type f -name "*.dat" -exec ls -la {} \;

# Compare with pre-shutdown file list
diff /tmp/pre_shutdown_files.txt <(find /tmp/mm2 -type f -exec ls -la {} \;)

# Check total disk usage (should be >= pre-shutdown)
du -sh /tmp/mm2/
```

### Step 3.2: Verify File Integrity

```bash
# Check file headers are valid (first 4 bytes should be magic number)
for f in /tmp/mm2/*/*.dat; do
    echo "=== $f ==="
    hexdump -C "$f" | head -2
done
```

### Step 3.3: Record Post-Shutdown State

| Metric | Pre-Shutdown | Post-Shutdown | Delta |
|--------|--------------|---------------|-------|
| Disk files count | | | |
| Disk space used | | | |
| Files per source | | | |

---

## Phase 4: Power Up / Restart

### Step 4.1: Start FC-1

```bash
# Start FC-1 service
sv start FC-1

# Wait for initialization
sleep 30

# Verify running
sv status FC-1
```

### Step 4.2: Expected Startup Log Messages

Look for these messages during startup:

```
# Startup initialization
[MM2] Memory Manager v2.8 initializing...
[MM2] RAM pool: 2048 sectors allocated

# Disk recovery
[MM2-RECOVERY] Scanning disk spool directories...
[MM2-RECOVERY] Found N files in /tmp/mm2/gateway/
[MM2-RECOVERY] Found N files in /tmp/mm2/hosted/
[MM2-RECOVERY] Found N files in /tmp/mm2/can/

# File validation
[MM2-RECOVERY] Validating file: sensor_X_seq_N.dat
[MM2-RECOVERY] File valid: X records, Y bytes

# Recovery complete
[MM2-RECOVERY] Disk recovery complete: N files, M bytes restored
[MM2-RECOVERY] Total pending records restored: X
```

### Step 4.3: Verify Recovery Logs

```bash
# Check recovery sequence in log
grep -E "RECOVERY|Scanning|Found.*files|Validating|restored" /var/log/fc-1.log | head -50
```

---

## Phase 5: Post-Startup Verification

### Step 5.1: Capture Post-Startup State

```bash
# Capture memory status
echo "ms" | nc localhost 23 > /tmp/post_startup_ms.txt

# Capture disk status
echo "ms disk" | nc localhost 23 > /tmp/post_startup_disk.txt

# List disk files
find /tmp/mm2 -type f -exec ls -la {} \; > /tmp/post_startup_files.txt
```

### Step 5.2: Compare States

| Metric | Pre-Shutdown | Post-Startup | Match? |
|--------|--------------|--------------|--------|
| Disk files count | | | |
| Disk space used | | | |
| Pending records | | | |
| Files tracked by MM2 | | | |

### Step 5.3: Verify Data Accessibility

```bash
# Check if pending data can be read
# Use ms use to see per-sensor pending counts
echo "ms use" | nc localhost 23

# Verify disk files are being read for upload
grep -E "disk.*read|reading.*disk|upload.*disk" /var/log/fc-1.log | tail -20
```

---

## Phase 6: Validation Criteria

### PASS Criteria

- [ ] All disk files present after shutdown match pre-shutdown count
- [ ] Disk space used post-shutdown >= pre-shutdown
- [ ] Startup recovery logs show files discovered
- [ ] Startup recovery logs show files validated
- [ ] `ms disk` shows correct file count after restart
- [ ] Pending record counts restored correctly
- [ ] No "corrupt" or "invalid" messages in recovery logs
- [ ] No data loss (total records preserved)

### FAIL Criteria

- [ ] Disk files missing after shutdown
- [ ] Disk files moved to `/tmp/mm2/corrupted/`
- [ ] Recovery logs show validation failures
- [ ] `ms disk` shows 0 files when files exist on disk
- [ ] Pending records not restored
- [ ] Error messages during recovery

---

## Troubleshooting

### Issue: Files exist but ms disk shows 0

**Cause**: Startup recovery not scanning disk directories
**Check**: `grep "RECOVERY" /var/log/fc-1.log`
**Fix**: Verify `mm2_startup_recovery.c` is being called

### Issue: Files marked as corrupted

**Cause**: File header validation failed
**Check**: `ls -la /tmp/mm2/corrupted/`
**Fix**: Check file format matches expected header structure

### Issue: Pending counts not restored

**Cause**: Per-source pending tracking not restored from disk
**Check**: Compare pre/post pending counts per sensor
**Fix**: Verify recovery code updates `pending_by_source` structure

### Issue: Shutdown didn't flush data

**Cause**: Shutdown sequence not triggered or incomplete
**Check**: Look for shutdown log messages
**Fix**: Ensure `sv stop` triggers graceful shutdown handler

---

## Quick Test Commands

```bash
# One-liner to capture baseline
ssh -p 22222 root@192.168.7.1 "echo 'ms disk' | nc localhost 23; du -sh /tmp/mm2; find /tmp/mm2 -name '*.dat' | wc -l"

# One-liner to stop and verify files persist
ssh -p 22222 root@192.168.7.1 "sv stop FC-1; sleep 3; du -sh /tmp/mm2; find /tmp/mm2 -name '*.dat' | wc -l"

# One-liner to restart and check recovery
ssh -p 22222 root@192.168.7.1 "sv start FC-1; sleep 30; grep RECOVERY /var/log/fc-1.log | tail -20"
```

---

## Test Execution Log

| Step | Time | Result | Notes |
|------|------|--------|-------|
| Deploy correct binary | 19:28 | ✅ PASS | Binary from mm1_issue deployed, MD5 verified |
| Verify signal handler | 19:28 | ✅ PASS | `Signal handlers registered for clean shutdown` in log |
| Pre-shutdown baseline | 19:30 | ✅ PASS | 183/2048 sectors (8.9%), 69 records |
| Controlled shutdown | 19:30 | ✅ PASS | `sv stop FC-1` triggered clean shutdown |
| Shutdown log messages | 19:30 | ✅ PASS | All 6 [SHUTDOWN] messages appeared in 7ms |
| Post-shutdown verification | 19:31 | ✅ PASS | 0 .dat files found in /tmp/mm2 |
| Restart FC-1 | 19:31 | ✅ PASS | Service started, pid 2426 |
| Post-startup verification | 19:31 | ✅ PASS | 61/2048 sectors (3.0%), 32 fresh records |
| Recovery verification | 19:31 | ✅ PASS | All sensors show "Discovered 0 files" |
| Final validation | 19:32 | ✅ PASS | Clean state confirmed |

---

## Actual Shutdown Log Output

```
[00:01:16.898] [SHUTDOWN] Signal received - clean shutdown
[00:01:16.898] [SHUTDOWN] Clearing disk data...
[00:01:16.902] [SHUTDOWN] Disk data cleared successfully
[00:01:16.903] [SHUTDOWN] Clearing RAM data...
[00:01:16.904] [SHUTDOWN] RAM data cleared
[00:01:16.905] [SHUTDOWN] Clean shutdown complete
```

**Shutdown Duration**: 7ms (from 16.898 to 16.905)

---

**Test Status**: ✅ PASSED
**Tester**: Claude Code
**Date Completed**: 2026-01-02 19:32
**Binary Tested**: `/home/greg/iMatrix/mm1_issue/Fleet-Connect-1/build/FC-1`
**Binary MD5**: `f712a6f4efc60bb3c4aa0cc20ea525b1`
