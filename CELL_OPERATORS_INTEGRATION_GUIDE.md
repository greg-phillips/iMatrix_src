# Cell Operators Command Integration Guide

**Date**: 2025-11-22
**Time**: 16:00
**Version**: 1.0
**Purpose**: Add tested and blacklist status to `cell operators` command

---

## Overview

The `cell operators` command needs to show:
1. **Whether each carrier has been tested** for signal strength
2. **Whether each carrier is blacklisted** and the timeout remaining
3. Clear visual indicators for current status

---

## Files to Modify

### 1. cellular_blacklist.c

Add the functions from `cellular_blacklist_additions.c`:

```bash
# Add to cellular_blacklist.c
cat cellular_blacklist_additions.c >> iMatrix/networking/cellular_blacklist.c
```

Key functions added:
- `get_blacklist_timeout_remaining()` - Returns seconds until blacklist expires
- `get_blacklist_entry()` - Gets blacklist entry for a carrier
- `display_blacklist()` - Shows detailed blacklist table
- `remove_from_blacklist()` - Removes specific carrier

### 2. cellular_blacklist.h

Add function prototypes:

```c
// Add to cellular_blacklist.h
time_t get_blacklist_timeout_remaining(const char* mccmnc);
blacklist_entry_t* get_blacklist_entry(const char* mccmnc);
void display_blacklist(void);
int get_blacklist_summary(char* buffer, size_t size);
bool remove_from_blacklist(const char* mccmnc);
bool should_retry_carrier(const char* mccmnc);
void get_blacklist_status_string(const char* mccmnc, char* buffer, size_t size);
```

### 3. cellular_man.c

Apply the patch or manually add:

```bash
# Apply patch
cd iMatrix/IMX_Platform/LINUX_Platform/networking
patch -p0 < ../../../../cellular_operators_display.patch
```

Or manually add the `display_cellular_operators()` function from the patch.

### 4. operator_info_t Structure Update

Ensure the structure has these fields:

```c
typedef struct {
    char operator_id[16];        // MCCMNC
    char operator_name[64];      // Carrier name
    int status;                  // 0=unknown, 1=available, 2=current, 3=forbidden
    int technology;              // Network technology
    unsigned long numeric;       // Numeric MCCMNC
    int signal_strength;         // CSQ value (0-31, 99=unknown)
    bool blacklisted;            // Local blacklist flag
    bool tested;                 // Has been tested for signal
} operator_info_t;
```

---

## Display Format

### Full Table Format

```
================================================================================
 Cellular Carriers - Scan Status
================================================================================
Idx | Carrier Name         | MCCMNC  | Status    | Tech | CSQ  | RSSI     | Tested | Blacklist
----+----------------------+---------+-----------+------+------+----------+--------+-------------
 1  | Verizon Wireless     | 311480  | Available | LTE  | 16   | -81 dBm  | Yes    | -
 2* | T-Mobile            | 310260  | Available | LTE  | 14   | -85 dBm  | Yes    | 2m 30s
 3  | AT&T                | 310410  | Available | LTE  | -    | -        | No     | -
 4  | FirstNet            | 313100  | Forbidden | LTE  | 18   | -77 dBm  | Yes    | Permanent
================================================================================

Summary:
  Total carriers: 4
  Tested: 3/4 (75%)
  Available: 3
  Blacklisted: 2

Legend:
  * = Currently testing  > = Selected carrier
  Status: Available/Current/Forbidden
  Tech: GSM/UTRAN/LTE/5G  CSQ: 0-31 (higher=better)
  Blacklist shows timeout remaining
```

### Key Features

1. **Visual Indicators**:
   - `*` = Currently being tested
   - `>` = Selected/connected carrier
   - `-` = Not tested or N/A

2. **Blacklist Status**:
   - `-` = Not blacklisted
   - `2m 30s` = Temporary (time remaining)
   - `Permanent` = Blocked for session
   - `Local` = Marked bad locally

3. **Signal Strength**:
   - CSQ: 0-31 (cellular signal quality)
   - RSSI: Shown in dBm for clarity
   - `-` if not tested

---

## CLI Commands

### Primary Commands

```bash
cell operators    # Show all carriers with test/blacklist status
cell ops         # Shorthand for above
cell blacklist   # Show detailed blacklist info
cell clear       # Clear all blacklisted carriers
cell scan        # Test all carriers for signal
```

### Debug Commands

```bash
cell test <mccmnc>              # Test specific carrier
cell blacklist add <mccmnc>     # Manually blacklist
cell blacklist remove <mccmnc>  # Remove from blacklist
cell retry                       # Clear expired entries
```

---

## Implementation Steps

### Step 1: Add Display Function

```c
// In cellular_man.c, add this function
void display_cellular_operators(void)
{
    // See cellular_operators_display.patch for full implementation
    // Shows table with tested and blacklist status
}
```

### Step 2: Update CLI Handler

```c
// In cli.c or cli_cellular_commands.c
bool process_cellular_cli_command(const char* command)
{
    if (strcmp(command, "cell operators") == 0 ||
        strcmp(command, "cell ops") == 0) {
        display_cellular_operators();
        return true;
    }
    // ... other commands
}
```

### Step 3: Ensure Data Population

When testing carriers, ensure these fields are set:

```c
// When signal test completes
scan_operators[i].tested = true;
scan_operators[i].signal_strength = csq_value;

// When blacklisting
scan_operators[i].blacklisted = true;
```

---

## Testing

### Test Scenarios

1. **Before any scan**:
   - Should show "No carriers discovered"

2. **After AT+COPS=? but before testing**:
   - Shows carriers with "Tested: No"

3. **During signal testing**:
   - Current carrier marked with `*`
   - Shows partial results

4. **After scan complete**:
   - All carriers show CSQ/RSSI
   - Best carrier marked with `>`

5. **With blacklisted carriers**:
   - Shows timeout remaining
   - Permanent blacklists marked

### Verification Commands

```bash
# Trigger a scan
cell scan

# While scanning, check status
cell operators   # Should show * on current carrier

# After failure, check blacklist
cell blacklist   # Should show failed carrier

# Check operators again
cell operators   # Should show blacklist timeout
```

---

## Troubleshooting

### Issue: "Tested" always shows No

**Check**: Ensure `op->tested = true` is set after CSQ response:
```c
case CELL_SCAN_WAIT_CSQ:
    // After getting CSQ
    scan_operators[i].tested = true;
    scan_operators[i].signal_strength = csq;
```

### Issue: Blacklist status not shown

**Check**: Ensure `is_carrier_blacklisted()` is called with correct MCCMNC:
```c
if (is_carrier_blacklisted(op->operator_id)) {
    // Show blacklist status
}
```

### Issue: Table formatting broken

**Check**: Ensure strings are properly truncated:
```c
char name[22];
strncpy(name, op->operator_name, 21);
name[21] = '\0';
```

---

## Summary

The enhanced `cell operators` command provides critical visibility into:
- Which carriers have actually been tested
- Which are currently blacklisted and why
- How long until blacklisted carriers can be retried
- Current testing/selection state

This is essential for debugging connectivity issues and understanding why certain carriers aren't being selected.

---

**Implementation Status**: Ready for Integration
**Files Provided**: All necessary code and patches included

---

*End of Integration Guide*