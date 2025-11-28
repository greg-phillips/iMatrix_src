# Testing Instructions - Cellular Serial Port Fix

**Build Date**: 2025-11-21 08:07
**Binary Location**: `/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1`
**Issue Fixed**: Segmentation fault on second AT+COPS? query

---

## Quick Smoke Test (5 minutes)

### Objective
Verify no segmentation faults occur during normal operation with PPP active.

### Procedure
```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
./FC-1 > /tmp/cellular_test_$(date +%Y%m%d_%H%M%S).txt 2>&1 &
TEST_PID=$!
echo "Test started with PID: $TEST_PID"

# Wait 5 minutes
sleep 300

# Check if still running
if kill -0 $TEST_PID 2>/dev/null; then
    echo "✅ SUCCESS: Process still running after 5 minutes"
    kill $TEST_PID
else
    echo "❌ FAILED: Process crashed"
fi

# Check log for errors
grep -i "segmentation\|fault\|error" /tmp/cellular_test_*.txt
```

### Expected Results
- ✅ No "Closing serial port (fd=X) before starting PPP" message
- ✅ **New message**: "AT command port remains open (fd=X) during PPP"
- ✅ First AT+COPS? query succeeds (~20 seconds)
- ✅ Second AT+COPS? query succeeds (~80 seconds)
- ✅ No segmentation faults
- ✅ Process runs for full 5 minutes

### Success Criteria
```log
[00:00:20] [Cellular Connection - Sending AT command: AT+COPS?]  ✅
[00:00:21] [Cellular Connection - AT command port remains open (fd=12) during PPP]  ✅
[00:01:20] [Cellular Connection - Sending AT command: AT+COPS?]  ✅
[00:02:20] [Cellular Connection - Sending AT command: AT+COPS?]  ✅
```

**NO** segmentation faults should appear.

---

## Extended Test (2 hours)

### Objective
Verify stability over extended operation with multiple periodic checks.

### Procedure
```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build

# Run for 2 hours
timeout 7200 ./FC-1 > /tmp/cellular_extended_test.txt 2>&1

# Analyze results
echo "=== Test Summary ==="
grep -c "AT+COPS?" /tmp/cellular_extended_test.txt
echo "Expected: ~120 queries (one per minute)"

grep -c "Segmentation fault" /tmp/cellular_extended_test.txt
echo "Expected: 0 faults"

grep -c "Serial port closed, ready for PPP" /tmp/cellular_extended_test.txt
echo "Expected: 0 (should not close port)"

grep -c "AT command port remains open" /tmp/cellular_extended_test.txt
echo "Expected: 1 (at PPP start)"
```

### Expected Results
- ✅ ~120 AT+COPS? queries over 2 hours
- ✅ All queries succeed
- ✅ Zero segmentation faults
- ✅ Port remains open (cell_fd > 0) throughout
- ✅ PPP connection stable

---

## Operator Scan Test

### Objective
Verify operator scanning works without closing AT command port.

### Procedure
```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
./FC-1 &
FC1_PID=$!

# Wait for PPP to establish
sleep 60

# Trigger operator scan via CLI
echo "cell scan" > /dev/stdin

# Monitor for completion
sleep 120

# Check results
ps aux | grep $FC1_PID
# Should still be running

kill $FC1_PID
```

### Expected Results
- ✅ Scan triggers PPP stop (via network manager)
- ✅ cell_fd remains open during scan (no "Closing serial port" message)
- ✅ AT commands work during scan
- ✅ PPP restarts after scan
- ✅ No segmentation faults

---

## Reset Test

### Objective
Verify cellular reset still closes and reopens port correctly.

### Procedure
```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
./FC-1 > /tmp/reset_test.txt 2>&1 &

# Wait for initialization
sleep 30

# Trigger reset via CLI
echo "cell reset" > /dev/stdin

# Wait for reset to complete
sleep 60

# Check log
grep "Close the serial port" /tmp/reset_test.txt
# Should appear during reset

grep "Serial port reopened" /tmp/reset_test.txt
# Should appear after reset

# Verify still running
ps aux | grep FC-1
```

### Expected Results
- ✅ Reset triggers port close (in CELL_INIT)
- ✅ Port reopens after reset
- ✅ AT commands work after reset
- ✅ No segmentation faults

---

## Signal Quality Monitoring Test

### Objective
Verify AT+CSQ queries work continuously during PPP.

### Procedure
```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
timeout 600 ./FC-1 > /tmp/csq_test.txt 2>&1

# Check AT+CSQ queries
grep "AT+CSQ" /tmp/csq_test.txt | wc -l
echo "Expected: Multiple queries over 10 minutes"

grep -i "error\|fail" /tmp/csq_test.txt | grep -i csq
echo "Expected: No CSQ errors"
```

### Expected Results
- ✅ Multiple AT+CSQ queries succeed
- ✅ Signal strength reported throughout
- ✅ No errors or failures
- ✅ No segmentation faults

---

## Stress Test (Optional)

### Objective
Verify stability under multiple reset cycles.

### Procedure
```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build

for i in {1..10}; do
    echo "=== Reset cycle $i ==="
    ./FC-1 > /tmp/stress_$i.txt 2>&1 &
    FC1_PID=$!

    sleep 60

    # Trigger reset
    echo "cell reset" > /dev/stdin

    sleep 30

    # Check if still running
    if kill -0 $FC1_PID 2>/dev/null; then
        echo "✅ Cycle $i: SUCCESS"
        kill $FC1_PID
    else
        echo "❌ Cycle $i: FAILED"
        break
    fi

    sleep 10
done
```

### Expected Results
- ✅ All 10 cycles complete successfully
- ✅ No segmentation faults across any cycle
- ✅ Port closes and reopens correctly each cycle

---

## Log Analysis

### Key Messages to Look For

**✅ SUCCESS Indicators:**
```log
[Cellular Connection - AT command port remains open (fd=12) during PPP]
[Cellular Connection - Sending AT command: AT+COPS?]
[Cellular Connection - ONLINE AT+COPS command response received.]
```

**✅ Expected During Reset:**
```log
[Cellular Connection - Close the serial port to reopen for a fresh connection]
[Cellular Connection - Serial port reopened (fd=12)]
```

**❌ FAILURE Indicators (should NOT appear):**
```log
Segmentation fault
[Cellular Connection - Closing serial port (fd=X) before starting PPP]
[ERROR] Invalid file descriptor: -1
[Cellular Connection - WARNING: AT command port unexpectedly closed (fd=-1)]
```

---

## Verification Checklist

### After Smoke Test (5 min)
- [ ] No segmentation faults
- [ ] Port stays open message appears
- [ ] First AT+COPS? succeeds
- [ ] Second AT+COPS? succeeds
- [ ] Process runs for full duration

### After Extended Test (2 hours)
- [ ] ~120 AT+COPS? queries completed
- [ ] All queries succeeded
- [ ] Zero segmentation faults
- [ ] PPP connection remained stable

### After Scan Test
- [ ] Scan completed successfully
- [ ] Port stayed open during scan
- [ ] No segmentation faults

### After Reset Test
- [ ] Reset closed port correctly
- [ ] Reset reopened port correctly
- [ ] AT commands work after reset

### Overall Success Criteria
- [ ] **All tests pass without segmentation faults**
- [ ] Port lifecycle correct (open during operation, close only on reset)
- [ ] AT commands work throughout PPP connection
- [ ] Signal monitoring continuous
- [ ] No regressions in existing functionality

---

## What Changed

### Code Modifications
1. **start_pppd()**: Removed port closure (lines 2071-2086)
2. **stop_pppd()**: Removed port reopening (lines 2159-2170)
3. **Reset paths**: Unchanged (CELL_INIT, CELL_PROCESS_RETRY)

### Behavioral Changes
- **Before**: Port closed before PPP, never reopened → crash at 60-80 seconds
- **After**: Port stays open during PPP → continuous monitoring works

### Lines Changed
- Lines removed: ~30
- Lines added: ~10 (comments + validation)
- Net change: -20 lines

---

## Troubleshooting

### If Test Fails with Segmentation Fault

1. **Check which AT command crashed:**
   ```bash
   grep -B 5 "Segmentation fault" /tmp/cellular_test_*.txt
   ```

2. **Check cell_fd value at crash:**
   ```bash
   grep "cell_fd=" /tmp/cellular_test_*.txt | tail -20
   ```

3. **Verify our changes were applied:**
   ```bash
   grep "AT command port remains open" /tmp/cellular_test_*.txt
   # Should appear once at PPP start
   ```

4. **Check for unexpected port closures:**
   ```bash
   grep "Closing serial port" /tmp/cellular_test_*.txt
   # Should only appear during reset, NOT before PPP start
   ```

### If Port Unexpectedly Closed

If you see: `WARNING: AT command port unexpectedly closed (fd=-1)`

This indicates cell_fd was set to -1 somewhere other than reset paths. Check:
- Other code paths that might close cell_fd
- Race conditions with other threads
- Signal handlers that might affect fd

---

## Rollback Procedure

If tests fail and you need to revert:

```bash
cd /home/greg/iMatrix/iMatrix_Client/iMatrix
git checkout HEAD -- IMX_Platform/LINUX_Platform/networking/cellular_man.c

cd ../Fleet-Connect-1/build
make clean
make

# Test reverted version
./FC-1 > /tmp/rollback_test.txt 2>&1
```

**Note**: Reverted version will have the original segfault issue.

---

## Success Confirmation

Once testing is complete and successful, update:

1. **cellular_segfault_issues_summary.md**
   - Mark Issue #2 as FIXED
   - Add test results

2. **Create cellular_serial_port_fix_summary.md**
   - Document implementation
   - Include test results
   - Lessons learned

3. **Update CLAUDE.md**
   - Add to "Debugging Patterns and Lessons Learned"
   - Document port lifecycle management

---

**Testing Started**: _______________
**Testing Completed**: _______________
**Result**: ☐ PASS  ☐ FAIL
**Tester**: _______________
**Notes**: _______________
