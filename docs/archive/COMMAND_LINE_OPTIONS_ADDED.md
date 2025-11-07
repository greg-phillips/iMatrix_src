# Command Line Options Enhancement - iMatrix Gateway

**Date**: November 7, 2025
**Branch**: `feature/fix-upload-read-bugs`
**Status**: ✅ COMPLETE

---

## 🎯 New Command Line Options Added

### 1. `--clear_history` - Delete All Disk History
**Purpose**: Remove all saved disk-based sensor history (spool files)

**Usage**:
```bash
./imatrix_gateway --clear_history
```

**What It Does**:
- Recursively deletes `/tmp/mm2/` directory tree
- Removes all spool files for all upload sources (gateway, ble, can, etc.)
- Removes all sensor subdirectories
- Cleans up directory structure

**Output Example**:
```
=======================================================
   CLEAR DISK HISTORY (--clear_history)
=======================================================

WARNING: This will DELETE ALL disk-based sensor history!
         All unsent/pending data will be permanently lost.
         This operation CANNOT be undone.

History location: /tmp/mm2/

Proceeding with deletion...

Clearing all disk-based history from: /tmp/mm2
  Deleted: /tmp/mm2/gateway/sensor_42_seq_0.dat
  Deleted: /tmp/mm2/gateway/sensor_42_seq_1.dat
  Deleted: /tmp/mm2/ble/sensor_100_seq_0.dat
  ... (more files)

Disk history cleared:
  Files deleted: 142
  Directories removed: 15

Disk history cleared successfully.
=======================================================
```

### 2. `--help` and `-?` - Display Help
**Purpose**: Show all available command line options

**Usage**:
```bash
./imatrix_gateway --help
./imatrix_gateway -?
```

**Output**:
```
=======================================================
   iMatrix Gateway - Command Line Options
=======================================================

Usage: imatrix_gateway [OPTIONS]

Configuration Options:
  -P                  Print detailed configuration from file
  -S                  Print configuration summary
  -I                  Display configuration file index/analysis

System Options:
  -R                  Reset network configuration (force regeneration)
  --clear_history     Delete all disk-based sensor history
                      WARNING: Deletes all unsent data! Cannot be undone.

Information:
  --help, -?          Display this help message

Examples:
  imatrix_gateway                  Normal startup (default)
  imatrix_gateway -S               Print config summary and start
  imatrix_gateway --clear_history  Clear all history and exit
  imatrix_gateway --help           Show this help

Notes:
  - Configuration file location: /usr/qk/etc/sv/memory_test
  - Disk history location: /tmp/mm2/ (Linux)
  - Most options will start the system after processing
  - Use Ctrl+C to stop the running system

=======================================================
```

---

## 📁 Files Modified

| File | Changes | Purpose |
|------|---------|---------|
| **iMatrix/cs_ctrl/mm2_file_management.c** | +163 lines | `imx_clear_all_disk_history()` function |
| **iMatrix/cs_ctrl/mm2_api.h** | +25 lines | Function declaration |
| **iMatrix/imatrix_interface.c** | +105 lines | Command line parsing + help |

**Total**: 3 files, ~293 lines

---

## 🔧 Implementation Details

### Function: `imx_clear_all_disk_history()`

**File**: `cs_ctrl/mm2_file_management.c:458-622`

**Algorithm**:
```
1. Open MM2_BASE_SPOOL_PATH (/tmp/mm2/)
2. For each upload source directory (gateway, ble, can, etc.):
   3. For each sensor directory within source:
      4. For each spool file within sensor:
         5. Delete file
      6. Remove empty sensor directory
   7. Remove empty source directory
8. Remove base directory if empty
9. Return success with counts
```

**Features**:
- Recursive directory traversal
- Safe deletion (checks errno, continues on ENOENT)
- Verbose output option
- Counts files and directories deleted
- Handles missing directories gracefully

**Safety**:
- Only called during startup (before MM2 init) or on explicit command
- No active memory structures affected
- Returns immediately if directory doesn't exist

### Command Line Parsing

**File**: `imatrix_interface.c:309-500`

**Options Processed** (in order):
1. `--help` or `-?` → Display help and exit
2. `--clear_history` → Clear disk history and exit
3. `-P` → Print detailed config and exit
4. `-S` → Print config summary and exit
5. `-I` → Display config index and exit
6. `-R` → Reset network config and **continue** (doesn't exit)
7. (no args) → Normal startup

**Note**: Most options exit after processing, except `-R` which continues to normal startup.

---

## 🧪 Testing Instructions

### Test 1: Help Display
```bash
# Test both help options
./imatrix_gateway --help
./imatrix_gateway -?

# Both should display same help output and exit
echo $?  # Should be 0 (success)
```

### Test 2: Clear History (Without Existing History)
```bash
# Ensure no history exists
rm -rf /tmp/mm2/

# Run clear_history
./imatrix_gateway --clear_history

# Expected output:
# "No history directory found - nothing to clean"
# "Disk history cleared successfully."
echo $?  # Should be 0 (success)
```

### Test 3: Clear History (With Existing History)
```bash
# Create test history structure
mkdir -p /tmp/mm2/gateway/sensor_42
echo "test data" > /tmp/mm2/gateway/sensor_42/seq_0.dat
mkdir -p /tmp/mm2/ble/sensor_100
echo "test data" > /tmp/mm2/ble/sensor_100/seq_0.dat

# Verify files exist
find /tmp/mm2 -type f

# Run clear_history
./imatrix_gateway --clear_history

# Expected output:
#   Deleted: /tmp/mm2/gateway/sensor_42/seq_0.dat
#   Deleted: /tmp/mm2/ble/sensor_100/seq_0.dat
#   Files deleted: 2
#   Directories removed: 4

# Verify files are gone
ls /tmp/mm2 2>&1  # Should show "No such file or directory"

echo $?  # Should be 0 (success)
```

### Test 4: Normal Startup Still Works
```bash
# Run without options
./imatrix_gateway

# Should start normally (no command line processing)
```

### Test 5: Unknown Option Handling
```bash
# Try invalid option
./imatrix_gateway --invalid_option

# Should start normally (unrecognized options are ignored)
```

---

## 📊 Expected Behavior

### --clear_history Output Patterns

**No history exists**:
```
Clearing all disk-based history from: /tmp/mm2
No history directory found - nothing to clean

Disk history cleared:
  Files deleted: 0
  Directories removed: 0
  (No history files found)

Disk history cleared successfully.
```

**History exists**:
```
Clearing all disk-based history from: /tmp/mm2
  Deleted: /tmp/mm2/gateway/sensor_2/data_20251107_120530.dat
  Deleted: /tmp/mm2/gateway/sensor_2/data_20251107_120545.dat
  ... (more files)

Disk history cleared:
  Files deleted: 45
  Directories removed: 12

Disk history cleared successfully.
```

**Permission error**:
```
Error: Failed to open /tmp/mm2: Permission denied

Error: Failed to clear disk history (code: -20)
```

---

## 🔒 Safety Considerations

### When It's Safe to Use --clear_history:
- ✅ Before starting the system
- ✅ During development/testing
- ✅ When resetting to clean state
- ✅ After confirming all data uploaded

### When It's NOT Safe:
- ❌ While system is running (will delete active files!)
- ❌ If unsent data is important
- ❌ In production without backup

### Protection Mechanisms:
- Only works on Linux (guarded by `#ifdef LINUX_PLATFORM`)
- Prints clear warning before deleting
- Verbose output shows what's being deleted
- Handles missing directories gracefully
- Only called during startup (before MM2 initialization)

---

## 🎓 Use Cases

### Development/Testing:
```bash
# Clear history between test runs
./imatrix_gateway --clear_history
./imatrix_gateway  # Fresh start

# Check history size
du -sh /tmp/mm2
./imatrix_gateway --clear_history
du -sh /tmp/mm2  # Should be gone
```

### Production Cleanup:
```bash
# Stop running system
systemctl stop imatrix

# Clear old history
./imatrix_gateway --clear_history

# Restart fresh
systemctl start imatrix
```

### Troubleshooting:
```bash
# If suspect corrupted disk files
systemctl stop imatrix
./imatrix_gateway --clear_history
systemctl start imatrix
# System will start with clean slate
```

---

## 🆚 Comparison with Other Options

| Option | Exits | Starts System | Deletes Data |
|--------|-------|---------------|--------------|
| `--help` | ✅ Yes | ❌ No | ❌ No |
| `-?` | ✅ Yes | ❌ No | ❌ No |
| `--clear_history` | ✅ Yes | ❌ No | ✅ **Yes** |
| `-P` | ✅ Yes | ❌ No | ❌ No |
| `-S` | ✅ Yes | ❌ No | ❌ No |
| `-I` | ✅ Yes | ❌ No | ❌ No |
| `-R` | ❌ No | ✅ Yes | ❌ No |
| (none) | ❌ No | ✅ Yes | ❌ No |

---

## 📝 Code Documentation

All functions have complete Doxygen headers:

- `display_command_line_help()` - Full help display with formatting
- `imx_clear_all_disk_history()` - Recursive directory deletion with verbose output

Both functions include:
- Purpose description
- Parameter documentation
- Return value description
- Usage examples
- Safety warnings

---

## ✅ Testing Checklist

- [ ] `--help` displays help and exits
- [ ] `-?` displays help and exits
- [ ] `--clear_history` deletes all history files
- [ ] `--clear_history` removes all directories
- [ ] `--clear_history` handles missing directory gracefully
- [ ] Verbose output shows files being deleted
- [ ] Returns success code 0 on completion
- [ ] Returns error code 1 on failure
- [ ] Normal startup (no args) still works
- [ ] Existing options (-P, -S, -I, -R) still work

---

## 🎉 Summary

**Added**:
- ✅ `--clear_history` option with disk cleanup
- ✅ `--help` option for user guidance
- ✅ `-?` option (alias for help)
- ✅ Helper function display

**Benefits**:
- Easy cleanup for testing/development
- Clear user guidance with --help
- Safe destructive operation with warnings
- Verbose output for transparency

**Files Modified**: 3
**Lines Added**: ~293
**Status**: Ready to build and test

