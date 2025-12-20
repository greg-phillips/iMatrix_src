# Net Command Output Alignment Fix Plan

**Date**: 2025-12-14
**Last Updated**: 2025-12-15
**Status**: COMPLETE - All alignment issues fixed
**Target Width**: 111 characters total (1 + 109 + 1)

## Analysis

The separator line defines the table width:
```
+=============================================================================================================+
```
This is 111 characters: `+` (1) + `=` (109) + `+` (1)

Every content line must be exactly 111 characters:
- Position 1: `|`
- Positions 2-110: content (109 characters)
- Position 111: `|`

---

## Line-by-Line Fix Plan

### Section 1: NETWORK MANAGER STATE Header
**Title**: "NETWORK MANAGER STATE" (21 chars)
**Padding**: (109 - 21) / 2 = 44 spaces each side
**Format**: `|` + 44 spaces + title + 44 spaces + `|` = 111 chars

### Section 2: Status Row
**Current output problem**: `| Status: ONLINE  | State: NET_ONLINE            | Interface: ppp0  | Duration: 00:42    | DTLS: OK       |`
**Analysis**: Need to verify total width is 111

### Section 3: Interface Table
**Header Row**: Should be 111 chars
**Data Rows**: Verified correct format already

### Section 4: INTERFACE LINK STATUS (Line 6349)
**Title**: "INTERFACE LINK STATUS" (21 chars)
**Current**: Only 107 characters - TOO SHORT
**Fix**: `|` + 44 spaces + title + 44 spaces + `|` = 111 chars

**Data Rows (Line 6355)**:
**Current**: `| %-9s | %-95s |`
**Calc**: 1 + 1 + 9 + 1 + 1 + 1 + 95 + 1 + 1 = 111 (CORRECT)
**Issue**: The inner content (95 chars) is producing wrong length
**Fix**: Need to verify get_interface_status_string() returns proper length

### Section 5: CONFIGURATION (Lines 6361-6376)
**Title**: "CONFIGURATION" (13 chars)
**Padding**: (109 - 13) / 2 = 48 spaces each side
**Current**: Wrong padding

**Row 1** (Line 6363):
- Current format has wrong total
- Need: exactly 109 chars between outer `|`

**Row 2** (Line 6368):
- Need: exactly 109 chars between outer `|`

**Row 3** (Line 6373):
- Need: exactly 109 chars between outer `|`

### Section 6: SYSTEM STATUS (Lines 6381-6400)
**Title**: "SYSTEM STATUS" (13 chars)
**Padding**: (109 - 13) / 2 = 48 spaces each side

**Row 1** (Line 6383): Fix padding
**Row 2** (Line 6389/6395): Fix padding

### Section 7: DNS CACHE (Lines 6405-6427)
**Title**: "DNS CACHE" (9 chars)
**Padding**: (109 - 9) / 2 = 50 spaces each side

**Data Rows**: Fix format strings

### Section 8: BEST INTERFACE ANALYSIS (Lines 6435-6450)
**Title**: "BEST INTERFACE ANALYSIS" (23 chars)
**Padding**: (109 - 23) / 2 = 43 spaces each side

**Data Row**: Fix trailing padding

### Section 9: RESULT STATUS (Lines 6455-6474)
**Title**: "RESULT STATUS" (13 chars)
**Padding**: (109 - 13) / 2 = 48 spaces each side

**Data Row**: Fix format

### Section 10: Network Traffic (Lines 6511-6518)
**All 4 rows**: Need consistent 109-char content width

### Section 11: DHCP SERVER STATUS (Lines 6536-6634)
**Title**: "DHCP SERVER STATUS" (18 chars)
**Padding**: (109 - 18) / 2 = 45.5 -> 45 left, 46 right

**All rows**: Need consistent 109-char content width

---

## Exact Format Strings Required

All title lines should use this pattern:
```c
imx_cli_print("|%*s%s%*s|\r\n", left_pad, "", title, right_pad, "");
```

Or use fixed strings calculated exactly.

### Calculated Title Strings (109 chars between outer `|`):

1. **NETWORK MANAGER STATE** (21 chars): 44 + 21 + 44 = 109
2. **INTERFACE LINK STATUS** (21 chars): 44 + 21 + 44 = 109
3. **CONFIGURATION** (13 chars): 48 + 13 + 48 = 109
4. **SYSTEM STATUS** (13 chars): 48 + 13 + 48 = 109
5. **DNS CACHE** (9 chars): 50 + 9 + 50 = 109
6. **BEST INTERFACE ANALYSIS** (23 chars): 43 + 23 + 43 = 109
7. **RESULT STATUS** (13 chars): 48 + 13 + 48 = 109
8. **DHCP SERVER STATUS** (18 chars): 45 + 18 + 46 = 109 (asymmetric)

---

## Implementation Checklist

- [x] Line 6238: Fix NETWORK MANAGER STATE title
- [x] Line 6257: Fix status row format
- [x] Line 6349: Fix INTERFACE LINK STATUS title
- [x] Line 6355/6359: Fix interface status data row format (`%-95s` → `%-96s`)
- [x] Line 6361: Fix CONFIGURATION title
- [x] Line 6363: Fix config row 1
- [x] Line 6368: Fix config row 2
- [x] Line 6373: Fix config row 3
- [x] Line 6381: Fix SYSTEM STATUS title
- [x] Line 6383: Fix system status row 1
- [x] Line 6389: Fix system status row 2
- [x] Line 6405: Fix DNS CACHE title
- [x] Line 6414: Fix DNS cache data row (primed)
- [x] Line 6422: Fix DNS cache data row (not primed)
- [x] Line 6435/6451: Fix BEST INTERFACE ANALYSIS title
- [x] Line 6439/6456: Fix best interface data row (55 trailing spaces)
- [x] Line 6446/6464: Fix best interface data row (none) (58 trailing spaces)
- [x] Line 6455/6472: Fix RESULT STATUS title
- [x] Line 6474: Fix result status row
- [x] Line 6479: Fix verifying interface row
- [x] Line 6489: Fix blacklist row
- [x] Line 6495: Fix PPP ping failures row
- [x] Line 6511-6517: Fix all network traffic rows
- [x] Line 6536: Fix DHCP SERVER STATUS title
- [x] Line 6568/6593: Fix DHCP interface summary row (`%-19s` → `%-28s`)
- [x] Line 6575/6601: Fix DHCP active clients row (`%-27s` → `%-33s`)
- [x] Line 6583/6609: Fix DHCP warning row
- [x] Line 6593-6595/6622-6623: Fix DHCP client table header (STATUS 19→22 chars)
- [x] Line 6618/6646: Fix DHCP client data row (`%-19s` → `%-22s`)
- [x] Line 6627/6656: Fix DHCP overflow row

## Completion Notes

All 111-character alignment verified through device testing on 2025-12-15.
Build verification: Zero errors, zero warnings across 6 builds.
