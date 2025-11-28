# Cellular Blacklist - Deployment Checklist

**Date**: 2025-11-24
**Build Time**: Nov 24 2025 @ 08:15
**Binary**: `/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1`
**Size**: 13 MB (12,801,056 bytes)
**MD5**: `2eb59ec2a2d0598d7e65e6a391eb8608`

---

## Pre-Deployment Verification

### Build Verification:
- [x] Source code compiled successfully
- [x] No compilation errors or warnings
- [x] Binary size reasonable (13 MB)
- [x] MD5 checksum recorded
- [x] Build timestamp verified (08:15)

### Code Review Completed:
- [x] Blacklist add logic verified
- [x] Blacklist check logic verified
- [x] Operator skipping logic verified
- [x] CME ERROR handling verified
- [x] Script timeout handling verified
- [x] Rescan flag checking verified
- [x] **CRITICAL**: Blacklist clear removed
- [x] Time-based expiry mechanism verified

---

## Deployment Steps

### 1. Backup Current System
```bash
# On gateway:
cp /usr/qk/bin/FC-1 /usr/qk/bin/FC-1.backup-$(date +%Y%m%d-%H%M)
cp /var/log/FC-1.log /var/log/FC-1.log.backup-$(date +%Y%m%d-%H%M)
```

**Status**: [ ] Completed

### 2. Copy New Binary
```bash
# From development machine:
scp /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1 root@gateway:/usr/qk/bin/FC-1.new

# Verify transfer:
ssh root@gateway "md5sum /usr/qk/bin/FC-1.new"
# Should match: 2eb59ec2a2d0598d7e65e6a391eb8608
```

**Status**: [ ] Completed
**MD5 Match**: [ ] Yes / [ ] No

### 3. Stop Service
```bash
# On gateway:
sv down FC-1

# Verify stopped:
sv status FC-1
# Should show: down
```

**Status**: [ ] Completed

### 4. Replace Binary
```bash
# On gateway:
mv /usr/qk/bin/FC-1 /usr/qk/bin/FC-1.old
mv /usr/qk/bin/FC-1.new /usr/qk/bin/FC-1
chmod +x /usr/qk/bin/FC-1

# Verify:
ls -lh /usr/qk/bin/FC-1*
```

**Status**: [ ] Completed

### 5. Start Service
```bash
# On gateway:
sv up FC-1

# Verify started:
sv status FC-1
# Should show: run
```

**Status**: [ ] Completed

### 6. Verify Build Version
```bash
# On gateway:
tail -50 /var/log/FC-1.log | grep "built on"
# Should show: Fleet Connect built on Nov 24 2025 @ 08:15
```

**Status**: [ ] Completed
**Build Time Match**: [ ] Yes / [ ] No

---

## Post-Deployment Testing

### Test 1: Basic Functionality
```bash
# Monitor startup:
tail -f /var/log/FC-1.log
```

**Checkpoints**:
- [ ] Service started successfully
- [ ] Cellular modem initialized
- [ ] AT commands responding
- [ ] No crash or segfault

**Status**: [ ] PASS / [ ] FAIL

### Test 2: Blacklist Commands
```bash
# On gateway CLI:
> cell blacklist

# Expected output:
# "Blacklist Status:" followed by entries or "No blacklisted carriers found"
```

**Status**: [ ] PASS / [ ] FAIL

### Test 3: Connection Establishment
```bash
# Monitor logs:
tail -f /var/log/FC-1.log | grep -E "carrier|operator|selected|ONLINE"
```

**Checkpoints**:
- [ ] Operators scanned successfully
- [ ] Carrier selected
- [ ] PPP connection attempted
- [ ] Connection established (or failure detected)

**Status**: [ ] PASS / [ ] FAIL

### Test 4: Failure Scenario (if occurs naturally)
```bash
# Monitor for failures:
tail -f /var/log/FC-1.log | grep -E "CME ERROR|script timeout|Blacklist"
```

**Expected Behavior**:
- [ ] Failure detected (CME ERROR or timeout)
- [ ] Carrier blacklisted
- [ ] "New carrier added to blacklist" message
- [ ] Rescan requested
- [ ] "Rescan requested, initiating carrier scan" message
- [ ] AT+COPS=? executed
- [ ] Blacklisted carrier skipped
- [ ] Alternative carrier selected

**Status**: [ ] PASS / [ ] FAIL / [ ] NOT TESTED (no failure)

### Test 5: Blacklist Persistence
```bash
# After blacklist triggered:
> cell blacklist
# Note the blacklisted carrier

# Wait 1 minute, check again:
> cell blacklist
# Should STILL show the blacklisted carrier (NOT cleared)

# Watch logs for next scan:
tail -f /var/log/FC-1.log | grep -E "blacklist|skipping"
# Should see: "Operator X is blacklisted, skipping"
# Should NOT see: "Cleared for fresh carrier evaluation"
```

**Checkpoints**:
- [ ] Blacklist entry persists after 1 minute
- [ ] Blacklisted carrier skipped in subsequent scans
- [ ] NO "Cleared for fresh" message in logs

**Status**: [ ] PASS / [ ] FAIL / [ ] NOT TESTED

### Test 6: Timeout Expiry (Optional - takes 5 minutes)
```bash
# After carrier blacklisted, wait 5 minutes:
> cell blacklist
# Should eventually show: "No blacklisted carriers found"

# Or watch logs:
tail -f /var/log/FC-1.log | grep "Removing carrier.*from blacklist"
```

**Status**: [ ] PASS / [ ] FAIL / [ ] NOT TESTED

---

## Issue Resolution

### If Service Won't Start:
```bash
# Check logs:
tail -100 /var/log/FC-1.log

# Common issues:
# - Missing library: ldd /usr/qk/bin/FC-1
# - Permission: chmod +x /usr/qk/bin/FC-1
# - Port in use: lsof /dev/ttyUSB*
```

### If Blacklist Not Working:
```bash
# Check version:
tail -50 /var/log/FC-1.log | grep "built on"
# Must show: Nov 24 2025 @ 08:15

# Verify blacklist messages:
grep -i blacklist /var/log/FC-1.log | tail -20

# Expected patterns:
# - "New carrier added to blacklist"
# - "Carrier is blacklisted"
# - "is blacklisted, skipping"
```

### If Rescan Not Triggered:
```bash
# Check for rescan messages:
grep "Rescan requested" /var/log/FC-1.log | tail -10

# Should see after failures:
# "Requesting carrier rescan after CME ERROR"
# "Rescan requested, initiating carrier scan"
```

### Rollback Procedure:
```bash
# If issues occur:
sv down FC-1
cp /usr/qk/bin/FC-1.old /usr/qk/bin/FC-1
sv up FC-1

# Verify rollback:
tail -50 /var/log/FC-1.log | grep "built on"
```

---

## Sign-Off

### Deployment Team:
- **Deployed By**: ________________
- **Date**: ________________
- **Time**: ________________

### Testing Results:
- **Basic Functionality**: [ ] PASS / [ ] FAIL
- **Blacklist Commands**: [ ] PASS / [ ] FAIL
- **Connection**: [ ] PASS / [ ] FAIL
- **Failure Handling**: [ ] PASS / [ ] FAIL / [ ] NOT TESTED
- **Blacklist Persistence**: [ ] PASS / [ ] FAIL / [ ] NOT TESTED

### Final Status:
- [ ] **APPROVED** - System working correctly
- [ ] **CONDITIONAL** - Working with minor issues
- [ ] **REJECTED** - Rolled back due to issues

### Notes:
```
_____________________________________________________________
_____________________________________________________________
_____________________________________________________________
_____________________________________________________________
```

---

## Success Metrics (First 24 Hours)

Track these metrics after deployment:

### Connection Stability:
- [ ] Number of PPP connection attempts: _______
- [ ] Number of successful connections: _______
- [ ] Number of failures: _______
- [ ] Unique carriers tried: _______

### Blacklist Activity:
- [ ] Carriers blacklisted: _______
- [ ] Rescans triggered: _______
- [ ] Alternative carriers selected: _______
- [ ] Blacklist timeouts: _______

### System Behavior:
- [ ] Stuck in infinite loop: YES / NO
- [ ] Carrier rotation working: YES / NO
- [ ] Service uptime: _______ hours
- [ ] Crashes/restarts: _______

---

## Contact Information

### Support:
- **Developer**: Greg
- **On-Call**: ________________
- **Escalation**: ________________

### Documentation:
- Complete solution: `CELLULAR_BLACKLIST_COMPLETE_SOLUTION.md`
- Review analysis: `CELLULAR_FIX_COMPREHENSIVE_REVIEW.md`
- Binary location: `/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1`

---

**End of Checklist**