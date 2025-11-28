# Quick Reference Guide - Cellular Fixes

**Date**: 2025-11-24
**Purpose**: Quick lookup for cellular carrier selection fixes

---

## 🚀 One-Page Summary

### The Problem
System gets stuck with failed carriers, never recovers

### The Solution
Clear blacklist on scan + monitor PPP + automatic retry

### The Critical Fix
```c
// File: cellular_man.c, Line: 3117
clear_blacklist_for_scan();  // THIS IS THE MOST IMPORTANT LINE
```

---

## 📍 Key File Locations

```
iMatrix_Client/
├── iMatrix/
│   ├── IMX_Platform/LINUX_Platform/networking/
│   │   ├── cellular_man.c          ← Main fixes here (line 3117)
│   │   └── process_network.c       ← Coordination flags
│   └── networking/
│       ├── cellular_blacklist.c    ← Blacklist system
│       └── cellular_carrier_logging.c ← Enhanced logging
└── Documentation/
    ├── DEVELOPER_HANDOVER_DOCUMENT.md ← Start here
    └── FIXES_APPLIED_REPORT.md        ← Verification
```

---

## 🔧 Critical Code Locations

| What | Where | Line | Why Critical |
|------|-------|------|--------------|
| Blacklist clearing | cellular_man.c | 3117 | Without this, stuck forever |
| PPP monitor state | cellular_man.c | 206 | Detects failures |
| Coordination flags | cellular_man.c | 589 | Prevents races |
| Display function | cellular_man.c | 3810 | See what's happening |

---

## 💻 CLI Commands

### Most Used
```bash
cell operators    # See all carriers with status
cell scan        # Force rescan (clears blacklist)
cell blacklist   # See who's blacklisted
cell clear       # Manually clear blacklist
```

### Debugging
```bash
# Watch the logs
tail -f /var/log/cellular.log | grep "Cellular"

# Check for critical message
grep "Blacklist] Cleared" /var/log/cellular.log

# See carrier testing
grep "Testing Carrier" /var/log/cellular.log
```

---

## ✅ Quick Verification

Run these commands to verify fixes are present:

```bash
cd iMatrix/IMX_Platform/LINUX_Platform/networking

# 1. Check blacklist clearing (MOST CRITICAL)
grep -n "clear_blacklist_for_scan" cellular_man.c
# Should show line 3117

# 2. Check PPP states
grep -n "CELL_WAIT_PPP_INTERFACE" cellular_man.c
# Should show line 206

# 3. Check coordination
grep -n "cellular_request_rescan" cellular_man.c
# Should show line 589

# 4. Check display function
grep -n "display_cellular_operators" cellular_man.c
# Should show line 3810
```

If all 4 are present, fixes are properly applied ✅

---

## 🔄 State Machine Flow

```
Start
  ↓
CELL_SCAN_GET_OPERATORS
  ├─ clear_blacklist_for_scan() ← CRITICAL!
  └─ AT+COPS=?
  ↓
CELL_SCAN_TEST_CARRIER
  ├─ Test each carrier
  └─ Get signal strength
  ↓
CELL_SCAN_SELECT_BEST
  ├─ Choose highest CSQ
  └─ Skip blacklisted
  ↓
CELL_WAIT_PPP_INTERFACE ← NEW!
  ├─ Monitor PPP
  └─ Timeout → Blacklist
  ↓
Success or Retry
```

---

## 🐛 Common Issues & Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Stuck with failed carrier | Check line 3117 has `clear_blacklist_for_scan()` |
| No carrier display | Add display function from line 3810 |
| PPP failures ignored | Add PPP states at line 206-207 |
| Build errors | Install mbedtls: `sudo apt-get install libmbedtls-dev` |

---

## 📊 What to Expect

### Before Fixes
```
- Carrier fails → Stuck forever
- No visibility → Can't debug
- Manual reset → Field trips
```

### After Fixes
```
- Carrier fails → Tries next one
- Full logging → See everything
- Self-healing → No intervention
```

### In the Logs
```
[Cellular Blacklist] Cleared for fresh carrier evaluation  ← Must see this
[Cellular Scan] Testing Carrier 1 of 4                     ← Testing each
[Cellular] PPP failed for carrier Verizon                  ← Detects failure
[Cellular] Blacklisting failed carrier and retrying        ← Automatic recovery
```

---

## 🎯 Testing in 5 Minutes

```bash
# 1. Start the application
./FC-1

# 2. Check carrier display works
cell operators

# 3. Force a scan
cell scan

# 4. Watch the logs (in another terminal)
tail -f /var/log/cellular.log

# 5. Should see:
# - "Blacklist] Cleared" message
# - Each carrier being tested
# - Best carrier selected
```

---

## 📝 If Something's Wrong

1. **First**: Check line 3117 in cellular_man.c
2. **Second**: Verify all 4 grep commands above
3. **Third**: Check build actually includes changes
4. **Last**: See DEVELOPER_HANDOVER_DOCUMENT.md

---

## 🔑 Remember

**THE SINGLE MOST IMPORTANT THING**:

The line `clear_blacklist_for_scan();` at line 3117 in cellular_man.c

Without this, nothing else matters - system stays broken.

---

**That's it! Everything else is details.**

---

*Quick Reference v1.0 - 2025-11-24*