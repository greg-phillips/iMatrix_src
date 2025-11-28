# Memory Manager Debugging Plan

**Date:** 2025-11-19
**Branch:** bugfix/memory_manager_1
**Task:** Fix memory management corruption issues
**Document Status:** AWAITING USER APPROVAL

---

## Initial Assessment

### Code Review Completed

**Files Reviewed:**
- `mm2_core.h` - Core data structures and constants
- `mm2_internal.h` - Internal function declarations
- `mm2_api.h` - Public API interface
- `memory_manager.h` - Compatibility wrapper
- `mm2_pool.c` - Memory pool management (partial)

**Architecture Understanding:**
✅ **Tiered storage system:** RAM pool (64KB) with disk spillover
✅ **75% efficiency design:** Separate chain table removes embedded pointers
✅ **Dual data types:** TSD (time-series) and EVT (event-based)
✅ **Multi-source support:** Gateway, BLE, CAN upload sources
✅ **Platform differences:** Linux (64KB, 32-bit IDs) vs STM32 (4KB, 16-bit IDs)

**Reference Documentation Created:**
- `/home/greg/iMatrix/iMatrix_Client/docs/mm_details.md` - Comprehensive technical reference

### Log File Analysis

**File Analyzed:** `/home/greg/iMatrix/iMatrix_Client/logs/mm1.txt` (4125 lines)

**Findings:**
- ✅ Normal startup sequence (lines 1-150)
- ✅ MM2 initialization successful
- ✅ 61 sensors activated without errors
- ✅ Disk recovery operations completed normally
- ⚠️ **No obvious corruption detected** in this log file

**Observations:**
1. Log covers approximately 4 seconds of runtime (startup phase)
2. All MM2 operations show SUCCESS status
3. Recovery operations found no disk files (clean start)
4. PPP connection failures are network-related, not MM corruption
5. "Resource busy" errors are GPIO-related, not MM corruption

**Conclusion:** This log file captures normal startup without corruption events.

---

## Questions for User

**CRITICAL:** Before proceeding with implementation, I need clarification:

### 1. Log File Verification

**Question:** Is `mm1.txt` the correct log file showing corruption?

**Options:**
a) **Yes, corruption happens later** - I should generate a longer-running log
b) **No, wrong file** - You'll provide the correct log file
c) **Corruption is subtle** - I missed it and should analyze more carefully

### 2. Reproduction Steps

**Question:** How is the corruption triggered?

**Information Needed:**
- What operations cause corruption? (normal sampling, upload cycles, shutdown?)
- How long does it take to appear? (seconds, minutes, hours?)
- Is it reproducible or intermittent?
- Are there specific sensor types or data patterns that trigger it?

### 3. Symptoms

**Question:** What are the observed corruption symptoms?

**Examples:**
- Segmentation faults or crashes?
- Data loss or duplication?
- Invalid sector chains (circular loops)?
- File system corruption?
- Upload failures?
- Memory leaks?

---

## Proposed Investigation Strategy

### Phase 1: Identify First Corruption (PENDING USER INPUT)

**Option A: Analyze Existing Logs**
If corruption exists in logs I haven't seen yet:
1. Review provided log files in chronological order
2. Search for first error/warning/assertion
3. Identify exact line number and context
4. Stop analysis at first corruption sign

**Option B: Generate New Logs**
If corruption must be reproduced:
1. Enable comprehensive MM2 debugging
2. Run system under normal operation
3. Monitor for corruption indicators
4. Capture full log when corruption occurs

**Option C: Code Inspection**
If corruption is code-based (not runtime):
1. Systematic review of critical paths
2. Look for race conditions, null pointer dereference
3. Check boundary conditions
4. Validate mutex usage

### Phase 2: Root Cause Analysis

Once first corruption is identified:

#### 2.1 Context Gathering
- [ ] Exact timestamp of corruption
- [ ] System state before corruption (memory usage, active sensors)
- [ ] Operation in progress (read, write, spool, recover)
- [ ] Upload source and sensor ID involved
- [ ] Platform (Linux/STM32)

#### 2.2 Code Path Tracing
- [ ] Identify function call stack leading to corruption
- [ ] Review relevant source files
- [ ] Check for similar patterns elsewhere
- [ ] Look for recent changes (git log)

#### 2.3 Hypothesis Formation
- [ ] Propose corruption mechanism
- [ ] Identify vulnerable code sections
- [ ] List potential fixes

### Phase 3: Fix Implementation

#### 3.1 Targeted Fixes
Based on root cause, implement minimal fixes:
- Add boundary checks
- Fix race conditions
- Correct offset calculations
- Validate chain integrity
- Add null pointer checks

#### 3.2 Build Verification
After each fix:
```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1
mkdir -p build && cd build
cmake ..
make
```
- ✅ Zero compilation errors
- ✅ Zero compilation warnings
- ✅ All modified files compile

#### 3.3 Incremental Testing
- Test fix in isolation
- Verify corruption resolved
- Check for side effects
- Document behavior change

### Phase 4: Validation

#### 4.1 Regression Testing
- [ ] Run memory test suites
- [ ] Verify normal operations still work
- [ ] Check all upload sources (Gateway, BLE, CAN)
- [ ] Test both TSD and EVT sensors

#### 4.2 Long-Running Test
- [ ] Run system for extended period
- [ ] Monitor for corruption recurrence
- [ ] Validate memory usage stays stable

#### 4.3 Code Review
- [ ] Review all changes for correctness
- [ ] Ensure proper error handling
- [ ] Verify thread safety (Linux)
- [ ] Check platform compatibility

---

## Debug Tooling Preparation

### MM2 Debugging Flags

```bash
# Enable comprehensive MM2 debugging
debug DEBUGS_FOR_MEMORY_MANAGER
```

### CLI Commands for Investigation

```bash
# Memory statistics
ms stats

# Sensor state
ms sensor <sensor_id>

# Chain validation
ms validate

# Force garbage collection (testing)
ms gc
```

### Instrumentation Points

**Critical Functions to Instrument:**

1. **`mm2_pool.c:allocate_sector_for_sensor()`**
   - Log every allocation with sensor_id and sector_id
   - Track free_list state before/after
   - Detect double-allocation

2. **`mm2_pool.c:free_sector()`**
   - Log every deallocation
   - Validate sector was actually in-use
   - Detect double-free

3. **`mm2_write.c:imx_write_tsd()`**
   - Log write operations
   - Track offset increments
   - Validate sector availability

4. **`mm2_read.c:imx_read_bulk_samples()`**
   - Log read operations
   - Track pending data marking
   - Validate chain walking

5. **`mm2_write.c:imx_erase_all_pending()`**
   - Log ACK handling
   - Track sector freeing
   - Validate chain updates

### Assertion Strategy

Add runtime checks:
```c
// Validate sector ID
assert(sector_id < g_memory_pool.total_sectors);

// Validate chain entry
assert(chain_table[sector_id].in_use);

// Validate no circular chains
assert(loop_counter < MAX_SECTORS);

// Validate mutex ownership
assert(pthread_mutex_lock(&pool_lock) == 0);
```

---

## Potential Corruption Scenarios (Hypothetical)

Based on code review, here are likely corruption patterns to investigate:

### Scenario 1: Chain Corruption

**Mechanism:**
- Sector freed while still in chain
- Results in dangling pointer via `next_sector_id`
- Next allocation reuses sector, breaking chain

**Debug Approach:**
- Add chain validation before/after every free
- Track sector ownership throughout lifecycle

### Scenario 2: Offset Overflow

**Mechanism:**
- `ram_write_offset` or `ram_read_offset` exceeds sector capacity
- Writes overflow into next sector's data
- Corrupts neighboring sensor's data

**Debug Approach:**
- Add boundary checks before offset increments
- Assert offset <= capacity

### Scenario 3: Race Condition (Linux)

**Mechanism:**
- Two threads modify chain_table simultaneously
- Missing mutex lock
- Chain pointers become inconsistent

**Debug Approach:**
- Audit all `pool_lock` usage
- Add thread ID logging
- Use ThreadSanitizer

### Scenario 4: Double-Free

**Mechanism:**
- Sector freed twice
- Corrupts free_list structure
- Leads to allocation of same sector to two sensors

**Debug Approach:**
- Assert `in_use == 1` before freeing
- Track free history

### Scenario 5: Disk File Corruption (Linux)

**Mechanism:**
- File header checksum mismatch
- Truncated write during power loss
- Recovery reads garbage data

**Debug Approach:**
- Add robust header validation
- Implement atomic file writes
- Move corrupted files to `/tmp/mm2/corrupted/`

### Scenario 6: Pending Count Mismatch

**Mechanism:**
- `pending_count` doesn't match actual records
- ACK erases wrong amount of data
- Data lost or duplicated

**Debug Approach:**
- Cross-validate counts during read/ACK
- Log discrepancies

---

## Implementation Checklist

### Pre-Implementation
- [x] Current branches documented (Aptera_1_Clean)
- [x] New branch created (bugfix/memory_manager_1)
- [x] Code architecture understood
- [x] Reference documentation created
- [ ] **BLOCKED:** First corruption identified
- [ ] Root cause hypothesis formed

### Implementation Phase
- [ ] Minimal fix implemented
- [ ] Code compiles without errors/warnings
- [ ] Fix tested in isolation
- [ ] Regression tests pass
- [ ] Documentation updated

### Validation Phase
- [ ] Long-running test (no recurrence)
- [ ] All upload sources tested
- [ ] Both TSD and EVT validated
- [ ] Performance impact assessed

### Completion Phase
- [ ] Final clean build verified
- [ ] All warnings resolved
- [ ] Changes documented in this plan
- [ ] Merge to original branch
- [ ] Update project documentation

---

## Resource Requirements

### Time Estimates

**Phase 1 - Corruption Identification:**
- If in existing logs: 1-2 hours
- If reproduction needed: 2-4 hours
- If code inspection: 4-8 hours

**Phase 2 - Root Cause Analysis:**
- Simple issue (offset error): 1-2 hours
- Complex issue (race condition): 4-8 hours
- Architecture issue: 8-16 hours

**Phase 3 - Fix Implementation:**
- Per issue: 1-4 hours
- Build/test cycles: 0.5-1 hour each

**Phase 4 - Validation:**
- Testing: 2-4 hours
- Long-running validation: 8-24 hours (mostly unattended)

**Total Estimate:** 8-48 hours (depends on complexity)

### Tools Needed

- ✅ Text editor (VS Code / vim)
- ✅ CMake build system
- ✅ GCC compiler
- ✅ GDB debugger (if segfaults occur)
- ⚠️ Valgrind (memory leak detection) - verify availability
- ⚠️ ThreadSanitizer (race detection) - verify availability

---

## Risk Assessment

### Low Risk Fixes
- Adding boundary checks
- Improving error messages
- Adding assertions
- Enhancing logging

### Medium Risk Fixes
- Changing offset calculation logic
- Modifying chain linking
- Adjusting mutex usage
- Updating file I/O

### High Risk Fixes
- Refactoring core allocation logic
- Changing data structures
- Modifying API signatures
- Platform-specific code changes

**Mitigation Strategy:**
- Fix one issue at a time
- Test after each change
- Maintain git commit history
- Keep rollback option available

---

## Success Criteria

### Must Have
1. ✅ First corruption identified and documented
2. ✅ Root cause understood and explained
3. ✅ Fix implemented with minimal code changes
4. ✅ System compiles without errors/warnings
5. ✅ Corruption no longer reproducible
6. ✅ No regression in normal operations

### Should Have
1. ✅ Similar issues prevented elsewhere
2. ✅ Debug logging improved
3. ✅ Documentation updated
4. ✅ Test coverage added

### Nice to Have
1. Automated test for corruption scenario
2. Performance optimization
3. Code cleanup/refactoring

---

## Next Steps - AWAITING USER INPUT

**TO PROCEED, I NEED:**

1. **Confirmation:** Is `mm1.txt` the correct log file with corruption?
   - If NO: Please provide the correct log file path
   - If YES: Should I generate a longer-running log to capture corruption?

2. **Reproduction:** How do I trigger the corruption?
   - Operations to perform?
   - Duration of test?
   - Expected symptoms?

3. **Symptoms:** What exactly happens when corruption occurs?
   - Crash/segfault?
   - Data loss?
   - Wrong output?
   - File errors?

**ONCE I HAVE THIS INFORMATION:**
- I will identify the first corruption in the logs
- Perform root cause analysis
- Propose specific fixes
- Implement and test incrementally
- Verify resolution

---

## Notes

- Branch `bugfix/memory_manager_1` is ready for work
- Reference documentation provides comprehensive architecture guide
- Log analysis tooling is prepared
- Build system verified and ready

**STATUS:** Plan complete, awaiting user approval and additional information to proceed.

---

**Plan Created By:** Claude Code
**Based On:** YAML specification from `specs/dev/debug_mm_prompt.md`
**Date Generated:** 2025-11-19
