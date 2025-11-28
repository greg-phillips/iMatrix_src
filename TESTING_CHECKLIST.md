# Cellular Fixes Testing Checklist

**Date**: 2025-11-24
**Version**: 1.0
**Purpose**: Comprehensive testing of cellular carrier selection fixes

---

## 🧪 Pre-Test Setup

### Environment Preparation
- [ ] Build successfully compiled with fixes
- [ ] Test gateway with SIM card installed
- [ ] Access to device CLI
- [ ] Log monitoring setup: `tail -f /var/log/cellular.log`
- [ ] Know how to trigger AT commands if needed
- [ ] Backup of working configuration

### Verification Commands
```bash
# Run these BEFORE testing to confirm fixes are present
- [ ] grep -n "clear_blacklist_for_scan" cellular_man.c      # Line 3117
- [ ] grep -n "CELL_WAIT_PPP_INTERFACE" cellular_man.c       # Line 206
- [ ] grep -n "cellular_request_rescan" cellular_man.c       # Line 589
- [ ] grep -n "display_cellular_operators" cellular_man.c    # Line 3810
```

---

## ✅ Functional Tests

### Test 1: Basic Carrier Display
**Objective**: Verify enhanced display works

- [ ] Start application: `./FC-1`
- [ ] Run command: `cell operators`
- [ ] **Verify**: Table displays with columns for Tested and Blacklist
- [ ] **Verify**: Legend shows at bottom
- [ ] **Pass Criteria**: Display renders without errors

**Expected Output**:
```
Idx | Carrier Name         | MCCMNC  | CSQ  | RSSI     | Tested | Blacklist
----+----------------------+---------+------+----------+--------+-------------
```

---

### Test 2: Blacklist Clearing on Scan
**Objective**: Verify blacklist clears on AT+COPS

- [ ] Manually blacklist a carrier: `cell blacklist add 311480`
- [ ] Verify blacklisted: `cell blacklist`
- [ ] Trigger scan: `cell scan`
- [ ] Check logs for: `[Cellular Blacklist] Cleared for fresh carrier evaluation`
- [ ] **Pass Criteria**: Message appears in log

**Command Sequence**:
```bash
cell blacklist add 311480
cell blacklist                    # Should show Verizon
cell scan
grep "Cleared for fresh" /var/log/cellular.log
```

---

### Test 3: Signal Testing Loop
**Objective**: Verify all carriers tested for signal

- [ ] Clear any existing data
- [ ] Trigger scan: `cell scan`
- [ ] Monitor logs during scan
- [ ] **Verify**: See "Testing Carrier X of Y" for each
- [ ] **Verify**: CSQ values recorded for each
- [ ] Run `cell operators` after scan
- [ ] **Verify**: Tested column shows "Yes" for tested carriers
- [ ] **Pass Criteria**: All discovered carriers show as tested

**Log Messages to Confirm**:
```
[Cellular Scan] Testing Carrier 1 of 4
[Cellular Scan] Testing Carrier 2 of 4
[Cellular Scan] Signal strength: XX
```

---

### Test 4: Best Carrier Selection
**Objective**: Verify highest signal selected

- [ ] After scan completes, check `cell operators`
- [ ] Note which carrier has > marker (selected)
- [ ] **Verify**: Selected carrier has highest CSQ
- [ ] Check logs for selection reasoning
- [ ] **Pass Criteria**: Best signal carrier selected (not first valid)

---

### Test 5: PPP Failure Detection
**Objective**: Verify PPP failures trigger blacklisting

- [ ] Connect to a carrier
- [ ] Wait for PPP attempt
- [ ] Kill PPP: `killall pppd`
- [ ] Monitor logs for detection
- [ ] **Verify**: "PPP failed" message appears
- [ ] **Verify**: Carrier gets blacklisted
- [ ] **Verify**: System tries next carrier
- [ ] **Pass Criteria**: Automatic recovery initiated

**Command Sequence**:
```bash
# Terminal 1 - Logs
tail -f /var/log/cellular.log | grep -E "(PPP|blacklist)"

# Terminal 2 - Actions
ps aux | grep pppd         # Find PID
kill <PID>                 # Kill PPP
cell operators             # Check blacklist status
```

---

### Test 6: Blacklist Timeout
**Objective**: Verify temporary blacklist expires

- [ ] Note blacklisted carrier with timeout
- [ ] Wait for timeout (or advance system time)
- [ ] Run `cell operators`
- [ ] **Verify**: Timeout decreases/expires
- [ ] **Pass Criteria**: Blacklist entry shows timeout countdown

---

### Test 7: All Carriers Blacklisted
**Objective**: Verify recovery when all fail

- [ ] Simulate failures for each carrier sequentially
- [ ] Let all carriers get blacklisted
- [ ] **Verify**: Log shows "All carriers blacklisted"
- [ ] **Verify**: Blacklist automatically clears
- [ ] **Verify**: Scan restarts fresh
- [ ] **Pass Criteria**: System recovers without manual intervention

---

## 🔄 Recovery Scenarios

### Scenario 1: Single Carrier Recovery
- [ ] Blacklist one carrier
- [ ] Verify others still tried
- [ ] **Pass**: System continues with remaining carriers

### Scenario 2: Location Change Simulation
- [ ] Blacklist current carrier
- [ ] Trigger new scan
- [ ] **Pass**: Blacklist clears, all carriers retried

### Scenario 3: Persistent Failure
- [ ] Let carrier fail 3 times
- [ ] Check if marked permanent
- [ ] **Pass**: Permanent blacklist for session

---

## 📊 Performance Tests

### Test 8: Scan Timing
- [ ] Measure scan start to completion time
- [ ] **Target**: < 3 minutes for full scan
- [ ] **Pass**: Completes within timeout

### Test 9: Carrier Switch Time
- [ ] Time from failure detection to new carrier
- [ ] **Target**: < 60 seconds
- [ ] **Pass**: Switch happens quickly

### Test 10: Memory Usage
- [ ] Check memory before/after multiple scans
- [ ] **Pass**: No memory leaks detected

---

## 🛠️ CLI Command Tests

### Display Commands
- [ ] `cell` - Shows basic status
- [ ] `cell operators` - Shows carrier table
- [ ] `cell blacklist` - Shows blacklist details
- [ ] `cell ppp` - Shows PPP status

### Control Commands
- [ ] `cell scan` - Triggers scan successfully
- [ ] `cell clear` - Clears blacklist
- [ ] `cell retry` - Clears expired entries
- [ ] `cell test 311480` - Tests specific carrier

### Debug Commands
- [ ] `cell blacklist add 311480` - Adds to blacklist
- [ ] `cell blacklist remove 311480` - Removes from blacklist

---

## 🐛 Edge Cases

### Test 11: Empty Carrier List
- [ ] Test with no carriers available
- [ ] **Pass**: No crash, appropriate message

### Test 12: Forbidden Carriers
- [ ] Test with forbidden carrier having best signal
- [ ] **Pass**: Selects next best available

### Test 13: Malformed AT Response
- [ ] Test with corrupted AT+COPS response
- [ ] **Pass**: Handles gracefully, no crash

### Test 14: Rapid State Changes
- [ ] Trigger multiple scans rapidly
- [ ] **Pass**: State machine remains stable

---

## 📝 Regression Tests

### Original Issues (Must Not Return)
- [ ] **net11.txt issue**: Stuck with Verizon
  - Verify: System now rotates carriers

- [ ] **net12.txt issue**: Poor logging
  - Verify: Full signal details logged

- [ ] **net13.txt issue**: Fixes not working
  - Verify: All fixes actually applied

---

## 📋 Test Results Summary

### Quick Pass/Fail Checklist
- [ ] Blacklist clears on scan? **YES/NO**
- [ ] All carriers tested? **YES/NO**
- [ ] Best signal selected? **YES/NO**
- [ ] PPP failures detected? **YES/NO**
- [ ] Automatic recovery works? **YES/NO**
- [ ] Display shows all info? **YES/NO**

### Metrics Achieved
- Scan completion time: _____ seconds
- Carrier switch time: _____ seconds
- Recovery success rate: _____%
- Memory stability: **PASS/FAIL**

---

## 🔍 Log Analysis

### Key Messages to Find
```bash
# Must see these in logs:
grep "Blacklist] Cleared" /var/log/cellular.log
grep "Testing Carrier" /var/log/cellular.log
grep "Selected best carrier" /var/log/cellular.log
grep "PPP established" /var/log/cellular.log
```

### Error Messages (Should NOT See)
```bash
# These indicate problems:
grep "CRITICAL" /var/log/cellular.log
grep "Segmentation fault" /var/log/cellular.log
grep "Stuck in state" /var/log/cellular.log
```

---

## 📊 Test Report Template

```markdown
## Cellular Fixes Test Report

**Date**: [DATE]
**Tester**: [NAME]
**Build Version**: [VERSION]
**Device**: [GATEWAY MODEL]

### Summary
- Total Tests Run: ___/14
- Tests Passed: ___
- Tests Failed: ___
- Blocked Tests: ___

### Critical Findings
1. [Issue if any]
2. [Issue if any]

### Recommendations
[PASS/FAIL for deployment]

### Notes
[Any observations]
```

---

## ✅ Sign-Off Criteria

**Ready for Production When:**
- [ ] All functional tests (1-7) pass
- [ ] Recovery scenarios work
- [ ] No regression to original issues
- [ ] Performance within targets
- [ ] No memory leaks
- [ ] CLI commands functional
- [ ] 24-hour stability test passes

**Sign-Off**:
- Developer: __________ Date: __________
- QA: __________ Date: __________
- Manager: __________ Date: __________

---

**Testing Checklist v1.0 - Complete**

*Use this checklist for every test cycle to ensure comprehensive validation*