# Plan: Update Net Command Output Format

**Date**: 2025-12-14
**Last Updated**: 2025-12-15
**Document Version**: 1.2
**Status**: Implementation Complete - All Alignment Issues Fixed
**Author**: Claude Code Analysis
**Branch**: bugfix/update_net_command_output (created in iMatrix submodule)

---

## Executive Summary

This plan addresses formatting issues in the `net` command output displayed by the `imx_network_connection_status()` function in `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`.

## Current Branch Status

| Submodule | Current Branch |
|-----------|----------------|
| iMatrix | Aptera_1_Clean |
| Fleet-Connect-1 | Aptera_1_Clean |

## Issues Identified

### Issue 1: IP Address Column Shows "VALID" Instead of Actual IP
**Location**: Line 6276
**Current Code**:
```c
has_ip ? "VALID" : "NONE",
```
**Problem**: The IP_ADDR column displays "VALID" or "NONE" instead of the actual IP address.
**Solution**: Create a helper function `get_interface_ip_string()` to retrieve the actual IP address and display it.

### Issue 2: IP_ADDR Column Too Narrow
**Location**: Line 6200, 6268
**Current**: `IP_ADDR` column is 7 characters wide (`%-7s`)
**Required**: 15 characters to accommodate full IPv4 address (e.g., "192.168.100.123")
**Solution**: Expand column width from 7 to 15 characters.

### Issue 3: Vertical Bar Alignment Issues
**Problem**: Multiple sections have inconsistent vertical bar alignment on the right edge.
**Affected Sections**:
- Network traffic table (lines 6445-6452)
- Configuration section (lines 6297-6310)
- System status section (lines 6317-6334)
- DNS cache section (lines 6348-6360)
- Best interface analysis (lines 6373-6383)
- Result status (lines 6408)

### Issue 4: Network Traffic Tables Inconsistent Width
**Location**: Lines 6445-6452
**Problem**: TX and RX rows have different column widths causing misalignment.
**Solution**: Use consistent fixed-width formatting across all traffic rows.

## Proposed Table Width

The table width is defined as 101 characters between the outer vertical bars (103 total with bars):
```
+=====================================================================================================+
```

All rows must fit exactly within this width.

## Implementation Plan

### Phase 1: Create Helper Function
Create `get_interface_ip_string()` function to retrieve the IP address for an interface.

**Function Signature**:
```c
static bool get_interface_ip_string(const char *ifname, char *ip_str, size_t ip_str_size);
```

**Returns**: `true` if valid IP found (and stored in `ip_str`), `false` otherwise (ip_str set to "NONE").

### Phase 2: Update Interface Table Header and Rows
1. Change header from `IP_ADDR` (7 chars) to `IP_ADDRESS` (15 chars)
2. Update format string to accommodate wider column
3. Adjust other columns if needed to maintain 101-char content width

**New Header**:
```
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDRESS      | TEST_TIME         |
```

### Phase 3: Fix Alignment in All Sections

#### 3.1 Configuration Section
Verify and fix format strings in lines 6297-6310.

#### 3.2 System Status Section
Verify and fix format strings in lines 6317-6334.

#### 3.3 DNS Cache Section
Verify and fix format strings in lines 6348-6360.

#### 3.4 Best Interface Analysis
Verify and fix format strings in lines 6373-6383.

#### 3.5 Result Status Section
Verify and fix format string in line 6408.

#### 3.6 Network Traffic Section
Standardize column widths across all four rows (TX/RX traffic and rates).

### Phase 4: Build Verification
After each code change:
1. Run the build
2. Check for compilation errors
3. Check for compilation warnings
4. Fix any issues before proceeding

---

## Detailed Todo List

- [x] **1. Create git branches**
  - [x] 1.1 Create branch `bugfix/update_net_command_output` in iMatrix submodule from `Aptera_1_Clean`

- [x] **2. Create helper function**
  - [x] 2.1 Add `get_interface_ip_string()` function declaration (forward declaration with other statics)
  - [x] 2.2 Implement `get_interface_ip_string()` function (near `has_valid_ip_address()`)

- [x] **3. Update interface table**
  - [x] 3.1 Update header line from `IP_ADDR` to `IP_ADDRESS` with 15-char width
  - [x] 3.2 Update separator line to match new column widths
  - [x] 3.3 Update interface row format string to use new IP column width
  - [x] 3.4 Replace `has_ip ? "VALID" : "NONE"` with actual IP address from helper function
  - [x] 3.5 Build and verify no errors/warnings

- [x] **4. Fix alignment in sections**
  - [x] 4.1 Fix Configuration section alignment
  - [x] 4.2 Fix System Status section alignment
  - [x] 4.3 Fix DNS Cache section alignment
  - [x] 4.4 Fix Best Interface Analysis alignment
  - [x] 4.5 Fix Result Status alignment
  - [x] 4.6 Build and verify no errors/warnings

- [x] **5. Fix Network Traffic tables**
  - [x] 5.1 Standardize TX traffic row format
  - [x] 5.2 Standardize RX traffic row format
  - [x] 5.3 Standardize TX rates row format
  - [x] 5.4 Standardize RX rates row format
  - [x] 5.5 Build and verify no errors/warnings

- [x] **6. Final verification**
  - [x] 6.1 Compile process_network.c to verify syntax
  - [x] 6.2 Verify zero new compilation errors
  - [x] 6.3 Verify zero new compilation warnings from changes
  - [x] 6.4 Review output format visually (device testing - iterative fixes applied)

- [x] **7. Session 3 Alignment Fixes (2025-12-15)**
  - [x] 7.1 Fix Interface Link Status data rows (Line 6359) - 110→111 chars
  - [x] 7.2 Fix DHCP Interface row (Line 6593) - 102→111 chars
  - [x] 7.3 Fix DHCP Active Clients row (Line 6601) - 105→111 chars
  - [x] 7.4 Fix DHCP Client table rows (Lines 6622-6646) - 108→111 chars
  - [x] 7.5 Fix Best Interface Analysis rows (Lines 6456, 6464) - reduced trailing spaces

- [x] **8. Documentation and merge**
  - [x] 8.1 Update this plan document with completion summary
  - [ ] 8.2 Merge branch back to `Aptera_1_Clean`

---

## Expected Output Format After Changes

```
+=====================================================================================================+
|                                        NETWORK MANAGER STATE                                        |
+=====================================================================================================+
| Status: ONLINE  | State: NET_SELECT_INTERFACE  | Interface: NONE  | Duration: 01:23    | DTLS: INIT |
+=====================================================================================================+
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDRESS      | TEST_TIME |
+-----------+---------+---------+---------+-------+---------+-----------+-----------------+-----------+
| eth0      | NO      | NO      | NO      |     0 |       0 | NONE      | NONE            | NONE      |
| wlan0     | REASSOC | NO      | NO      |     0 |       0 | NONE      | 192.168.1.100   | 72489 ms  |
| ppp0      | NO      | NO      | NO      |     0 |       0 | NONE      | NONE            | NONE      |
+=====================================================================================================+
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Column width changes break alignment | Medium | Careful calculation of format strings |
| IP retrieval fails in edge cases | Low | Graceful fallback to "NONE" |
| Build failures | Medium | Incremental builds after each change |

---

## Metrics Tracking

| Metric | Session 1-2 | Session 3 | Total |
|--------|-------------|-----------|-------|
| Tokens Used | ~25,000 | ~8,000 | ~33,000 |
| Recompilations for Syntax Errors | 0 | 0 | 0 |
| Elapsed Time | ~15 minutes | ~10 minutes | ~25 minutes |
| Builds Performed | 3 | 3 | 6 |

---

## Completion Summary

### Work Completed

1. **Created new helper function** `get_interface_ip_string()` (lines 2656-2705)
   - Retrieves actual IPv4 address for a network interface
   - Returns formatted string like "192.168.1.100" or "NONE" if no valid IP
   - Uses same logic as existing `has_valid_ip_address()` function

2. **Updated interface table** (lines 6264-6344)
   - Changed column header from `IP_ADDR` (7 chars) to `IP_ADDRESS` (15 chars)
   - Now displays actual IP addresses instead of "VALID"/"NONE"
   - Expanded table width from 103 to 111 characters to accommodate larger IP column

3. **Fixed alignment in all sections** (Session 2 - Detailed line-by-line fixes)
   - Target width: 111 characters total (| + 109 content + |)
   - All title lines properly centered with calculated padding
   - Fixed format strings to ensure exactly 111 characters per line:
     - **Interface Link Status title**: 44 spaces + 21 chars + 44 spaces
     - **Configuration title**: 48 spaces + 13 chars + 48 spaces
     - **Configuration rows**: Adjusted field widths (%-14s, %-15u, trailing spaces)
     - **System Status title**: 48 spaces + 13 chars + 48 spaces
     - **System Status rows**: Adjusted field widths (%-27s, %-23s)
     - **DNS Cache title**: 50 spaces + 9 chars + 50 spaces
     - **DNS Cache rows**: Changed %-31s to %-32s
     - **Best Interface Analysis title**: 43 spaces + 23 chars + 43 spaces
     - **Best Interface rows**: Fixed trailing space counts
     - **Result Status title**: 48 spaces + 13 chars + 48 spaces
     - **Result Status rows**: Fixed %-77s to %-75s, adjusted trailing spaces
     - **Network Traffic rows**: Changed %-26s to %-31s
     - **DHCP Server Status title**: 45 spaces + 18 chars + 46 spaces
     - **DHCP Server rows**: Adjusted field widths and client table formatting

4. **Standardized Network Traffic tables**
   - All four rows (TX traffic, RX traffic, TX rates, RX rates) now use consistent column widths
   - Changed final column from %-26s to %-31s for exact 111 char width

5. **Session 3 Final Alignment Fixes (2025-12-15)**
   Device testing revealed 5 additional alignment issues. All fixed:

   | Line | Section | Was | Fix | Result |
   |------|---------|-----|-----|--------|
   | 6359 | Interface Link Status data rows | 110 chars | `%-95s` → `%-96s` | 111 chars |
   | 6456 | Best Interface Analysis (valid) | ~115 chars | Reduced trailing spaces to 55 | 111 chars |
   | 6464 | Best Interface Analysis (NONE) | ~113 chars | Reduced trailing spaces to 58 | 111 chars |
   | 6593 | DHCP Interface row | 102 chars | `%-19s` → `%-28s` | 111 chars |
   | 6601 | DHCP Active Clients row | 105 chars | `%-27s` → `%-33s` | 111 chars |
   | 6622-6646 | DHCP Client table | 108 chars | STATUS `%-19s` → `%-22s` | 111 chars |

### Files Modified

- `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
  - Added forward declaration at line 446
  - Added `get_interface_ip_string()` implementation at lines 2656-2705
  - Updated `imx_network_connection_status()` function throughout (lines 6229-6638)

### Expected Output Format

```
+=============================================================================================================+
|                                            NETWORK MANAGER STATE                                            |
+=============================================================================================================+
| Status: ONLINE  | State: NET_ONLINE              | Interface: wlan0 | Duration: 01:23    | DTLS: CONN     |
+=============================================================================================================+
| INTERFACE | ACTIVE  | TESTING | LINK_UP | SCORE | LATENCY | COOLDOWN  | IP_ADDRESS      | TEST_TIME         |
+-----------+---------+---------+---------+-------+---------+-----------+-----------------+-------------------+
| eth0      | NO      | NO      | YES     |     0 |       0 | NONE      | 192.168.7.1     | NONE              |
| wlan0     | YES     | NO      | YES     |     8 |      15 | NONE      | 192.168.1.100   | 5000 ms ago       |
| ppp0      | NO      | NO      | NO      |     0 |       0 | NONE      | NONE            | NONE              |
+=============================================================================================================+
```

### Branch Information

- **Branch**: `bugfix/update_net_command_output` in iMatrix submodule
- **Base Branch**: `Aptera_1_Clean`
- **Status**: All alignment issues fixed - Ready for final device verification and merge

### Build Verification

All changes compile successfully with:
- Zero compilation errors
- Zero new compilation warnings
- Verified with 6 incremental builds across 3 sessions

---
