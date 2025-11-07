# CAN Performance Improvement Plan

**Date**: November 7, 2025
**Branch**: To be created from feature/fix-upload-read-bugs
**Status**: 🚨 **CRITICAL - 90% Packet Drop Rate**

---

## 🚨 Critical Problem Statement

**Current State** (from CAN server statistics):
```
RX Frames:             1,041,286 total
Dropped (Buffer Full): 942,605  ← 90.5% DROP RATE!
Drop Rate:             566 drops/sec (peak 1,851 drops/sec)
RX Rate:               829 fps (peak 2,117 fps)
Buffer Usage:          92% (464/500 messages)
Peak Buffer Usage:     96% (481/500 messages)
```

**The Problem**: System is dropping **9 out of every 10 CAN packets** due to buffer exhaustion.

---

## 📊 Root Cause Analysis

### Current Buffer Sizes (from code analysis)

**Ring Buffers** (can_utils.c:122):
```c
#define CAN_MSG_POOL_SIZE  500  ← Per bus (CAN0, CAN1, Ethernet)
```

**Unified Queue** (can_unified_queue.h:68):
```c
#define UNIFIED_QUEUE_SIZE 1500  ← Total (3 buses × 500)
```

**Processing Batch** (can_unified_queue.h:69):
```c
#define MAX_BATCH_SIZE     100   ← Messages per dequeue
```

### Bottleneck Calculation

**At peak traffic** (2,117 fps):
- Messages arriving per second: 2,117
- Buffer capacity: 500 messages
- **Buffer fills in**: 500 / 2,117 = **0.236 seconds** (236ms)

**Processing must complete in < 236ms to avoid drops**

**Current processing**:
- Dequeue batch: 100 messages
- Must process 100 messages in < 47ms (236ms / 5 batches to clear 500)
- **If processing takes longer**, buffer fills and packets drop

### Identified Bottlenecks

1. **Ring Buffer Too Small**
   - Current: 500 messages
   - Fills in: 236ms at peak
   - Needs: 2-3 seconds of buffering = 4,000-6,000 messages

2. **Unified Queue Size**
   - Current: 1,500 total
   - Should scale with ring buffer increase

3. **Processing Speed**
   - Current batch: 100 messages
   - Unknown processing time per message
   - Likely too slow for 2,117 fps bursts

4. **Linear Search in Ring Buffer**
   - Alloc uses linear search from head position
   - O(n) worst case (can_ring_buffer.c:117-136)
   - Gets slower as buffer size increases

5. **Mutex Contention**
   - RX thread locks mutex to allocate (can_utils.c:560)
   - Processing locks mutex to return (unified_queue.c:246)
   - Possible contention at high rates

---

## 🎯 Proposed Solutions

### Solution 1: Increase Buffer Sizes (IMMEDIATE FIX)

**Rationale**: At 2,117 fps peak, need 2-3 seconds of buffering

**Changes Required**:

**File**: `canbus/can_utils.c:122`
```c
// CURRENT:
#define CAN_MSG_POOL_SIZE  500

// PROPOSED:
#define CAN_MSG_POOL_SIZE  4000  /* 2 seconds at 2000 fps */
```

**File**: `canbus/can_unified_queue.h:68`
```c
// CURRENT:
#define UNIFIED_QUEUE_SIZE 1500

// PROPOSED:
#define UNIFIED_QUEUE_SIZE 12000  /* 3 buses × 4000 */
```

**Memory Impact**:
- Current per bus: 500 × sizeof(can_msg_t) ≈ 500 × 24 = 12KB
- Proposed per bus: 4000 × 24 = 96KB
- Total increase: 3 buses × 84KB = **252KB additional RAM**

**Acceptable for Linux platform (1GB RAM)** ✅

### Solution 2: Increase Processing Batch Size

**Rationale**: Reduce mutex lock/unlock overhead

**File**: `canbus/can_unified_queue.h:69`
```c
// CURRENT:
#define MAX_BATCH_SIZE  100

// PROPOSED:
#define MAX_BATCH_SIZE  200  /* Process more per cycle */
```

**Impact**: Fewer dequeue calls, less mutex overhead

### Solution 3: Optimize Ring Buffer Allocation (MEDIUM COMPLEXITY)

**Current Issue**: Linear search O(n) gets slower with larger buffers

**File**: `canbus/can_ring_buffer.c:110-140`

**Current Algorithm**:
```c
can_msg_t* can_ring_buffer_alloc(can_ring_buffer_t *ring) {
    do {
        if (!ring->in_use[pos]) {
            // Found free slot
        }
        pos = (pos + 1) % ring->max_size;
    } while (pos != start_pos);  ← O(n) worst case!
}
```

**Proposed**: Maintain free list for O(1) allocation
```c
typedef struct {
    uint16_t *free_list;  /* Array of free indices */
    uint16_t free_head;   /* Next free index to allocate */
    /* ... existing fields ... */
} can_ring_buffer_t;
```

**Impact**: Constant time allocation even with 4000 message buffer

### Solution 4: Profile Processing Time (DIAGNOSTIC)

**Add timing instrumentation** to identify slow code paths:

**File**: `canbus/can_utils.c:process_can_queues()`
```c
void process_can_queues(imx_time_t current_time) {
    imx_time_t start_time = current_time;

    /* Dequeue and process */
    count = unified_queue_dequeue_batch(...);
    for (i = 0; i < count; i++) {
        process_rx_can_msg(...);
    }

    imx_time_t end_time;
    imx_time_get_time(&end_time);
    uint32_t processing_time_ms = end_time - start_time;

    if (processing_time_ms > 10) {  /* Threshold */
        PRINTF("[CAN PERF] Processed %u messages in %u ms (%.1f msg/ms)\r\n",
               count, processing_time_ms, (float)count / processing_time_ms);
    }
}
```

### Solution 5: Reduce Memory Allocations in Signal Extraction

**Hypothesis**: Signal extraction may be slow due to memory operations

**Need to Profile**:
- can_signal_extraction.c
- can_sample.c

---

## 📋 Detailed Implementation Plan

### Phase 1: Immediate Fix (High Priority)
- [ ] Create new branch: `feature/improve-can-performance`
- [ ] Increase CAN_MSG_POOL_SIZE: 500 → 4000
- [ ] Increase UNIFIED_QUEUE_SIZE: 1500 → 12000
- [ ] Increase MAX_BATCH_SIZE: 100 → 200
- [ ] Build and test
- [ ] Expected: Drop rate < 5%

### Phase 2: Optimization (Medium Priority)
- [ ] Add timing instrumentation to process_can_queues()
- [ ] Profile processing time per message
- [ ] Identify slow code paths
- [ ] Optimize ring buffer allocation (free list)

### Phase 3: Advanced (If Needed)
- [ ] Consider lock-free ring buffer
- [ ] Separate RX thread from processing thread
- [ ] Pre-parse CAN frames in RX callback
- [ ] Batch signal extraction

---

## 🧪 Testing Strategy

### Test 1: Baseline with Increased Buffers
```bash
# Build with 4000/12000/200 sizes
make clean && make

# Run and monitor
> can server
# Watch for:
# - Drop rate should drop dramatically
# - Buffer usage should be < 50%
# - Zero drops at normal rates
```

### Test 2: Stress Test
```bash
# Send high-rate CAN traffic
# Use can send_file with dense trace

# Monitor continuously
watch -n 1 "echo 'can server' | nc localhost <cli_port>"

# Verify:
# - Peak buffer usage < 80%
# - Drop rate < 5% even at peak
```

### Test 3: Performance Profiling
```bash
# Enable performance logging
export DEBUGS_FOR_CANBUS=1

# Check processing times
grep "CAN PERF" logs/test.txt
# Should show messages/ms throughput
```

---

## ⚠️ Risks and Mitigation

### Risk 1: Memory Exhaustion
**Risk**: 252KB additional RAM might impact other subsystems
**Mitigation**: Linux has 1GB RAM - 252KB is <0.03%
**Probability**: LOW

### Risk 2: Processing Still Too Slow
**Risk**: Larger buffers just delay the problem
**Mitigation**: Phase 2 profiling will identify bottlenecks
**Probability**: MEDIUM

### Risk 3: Regression in CAN Functionality
**Risk**: Changes break existing functionality
**Mitigation**: Only changing constants, not logic
**Probability**: LOW

---

## 🎯 Success Criteria

**Must Achieve**:
- ✅ Drop rate < 5% at normal traffic (829 fps)
- ✅ Drop rate < 20% at peak traffic (2,117 fps)
- ✅ Buffer usage < 70% at normal traffic
- ✅ No functional regressions

**Stretch Goals**:
- ✅ Drop rate < 1% at peak
- ✅ Buffer usage < 50% at peak
- ✅ Processing time < 5ms per 100 messages

---

## 📝 Questions for User

Before proceeding with implementation:

1. **Memory Constraints**: Is +252KB RAM acceptable for Linux platform?

2. **Buffer Size**: Start with conservative 4000 or aggressive 8000?

3. **Testing**: Can you generate sustained 2,000+ fps CAN traffic for stress testing?

4. **Phased Approach**:
   - Option A: Implement Phase 1 only (buffer increase) and test
   - Option B: Implement Phases 1+2 (buffers + profiling) together

5. **Branch Strategy**: Create from current feature/fix-upload-read-bugs or from Aptera_1?

---

## 📊 Current Architecture Understanding

### Message Flow:
```
TCP Server (can_server.c)
    ↓ parse CAN frame
canFrameHandlerWithTimestamp() (can_utils.c:550)
    ↓ lock mutex
can_ring_buffer_alloc() (can_ring_buffer.c:110)
    ↓ if NULL → DROP! (90% of cases!)
unified_queue_enqueue() (can_unified_queue.c:168)
    ↓ unlock mutex
[Message in queue]
    ↓
process_can_queues() (can_utils.c:697)
    ↓ dequeue batch (100 messages)
process_rx_can_msg() (can_utils.c:732)
    ↓ extract signals
return_to_source_pool() (can_unified_queue.c:432)
```

### Bottleneck Points:
1. **Ring buffer exhaustion** ← PRIMARY ISSUE (92% full)
2. **Unified queue capacity** ← SECONDARY (needs to match ring buffer)
3. **Processing speed** ← UNKNOWN (needs profiling)

---

**Status**: Analysis complete, awaiting user input on questions above before creating detailed implementation plan.

**Recommendation**: Start with Phase 1 (buffer increases) as immediate fix, then profile if drops persist.