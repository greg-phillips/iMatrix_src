# Memory Manager Diagnostic Messaging Plan

## Executive Summary

This document outlines the implementation plan for adding diagnostic messaging to the iMatrix Memory Manager v2.8. The system will output diagnostic messages using the PRINTF macro whenever memory usage passes 10% threshold boundaries during sector allocation.

---

## Requirements

### Primary Requirement
Output a diagnostic message each time memory usage passes an incremental 10% threshold when a new sector is allocated.

### Specific Details
- **Trigger**: When `allocate_sector_for_sensor()` successfully allocates a sector
- **Thresholds**: 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%, 90%
- **Output**: Use PRINTF macro for logging (already defined in mm2_disk.h)
- **Platform Support**: Both Linux and STM32 platforms

---

## Technical Analysis

### Current Memory Manager Architecture

#### Key Components
1. **Global Memory Pool** (`g_memory_pool`)
   - `total_sectors`: Total number of sectors in pool
   - `free_sectors`: Number of available sectors
   - Used sectors: `total_sectors - free_sectors`

2. **Sector Allocation Function** (`allocate_sector_for_sensor()`)
   - Located in: `iMatrix/cs_ctrl/mm2_pool.c`
   - Line: 281
   - Decrements `free_sectors` when allocating
   - Increments `total_allocations` counter

3. **PRINTF Macro**
   - Defined in: `iMatrix/cs_ctrl/mm2_disk.h`
   - Line: 61
   - Definition: `#define PRINTF(...) if( LOGS_ENABLED( DEBUGS_FOR_MEMORY_MANAGER ) ) imx_cli_log_printf(true, __VA_ARGS__)`

### Memory Usage Calculation
```c
uint32_t used_sectors = g_memory_pool.total_sectors - g_memory_pool.free_sectors;
uint32_t usage_percent = (used_sectors * 100) / g_memory_pool.total_sectors;
```

### Threshold Tracking Strategy

#### Option 1: Static Variable (Simple)
- Track last threshold in static variable
- Compare with current usage after allocation
- Output message if threshold crossed

#### Option 2: Bitfield Tracking (Comprehensive)
- Track which thresholds have been crossed
- Allows detection of both upward and downward crossings
- More complex but provides better diagnostics

#### Selected Approach: Static Variable with Hysteresis
- Track last reported threshold
- Only report when crossing to a new 10% boundary
- Simple, efficient, meets requirements

---

## Implementation Design

### 1. Threshold Tracking Structure
```c
/* Add to mm2_pool.c */
static struct {
    uint32_t last_reported_threshold;  /* Last threshold reported (0, 10, 20, ..., 90) */
    uint32_t initial_check_done;        /* Flag for initialization */
} g_memory_threshold_tracker = {0, 0};
```

### 2. Threshold Detection Function
```c
/**
 * @brief Check and report memory usage threshold crossings
 *
 * Reports when memory usage crosses 10% boundaries (10%, 20%, ..., 90%)
 * Called after successful sector allocation.
 */
static void check_memory_threshold_crossing(void) {
    /* Calculate current usage percentage */
    uint32_t used_sectors = g_memory_pool.total_sectors - g_memory_pool.free_sectors;
    uint32_t usage_percent = (used_sectors * 100) / g_memory_pool.total_sectors;

    /* Round down to nearest 10% threshold */
    uint32_t current_threshold = (usage_percent / 10) * 10;

    /* Initialize on first call */
    if (!g_memory_threshold_tracker.initial_check_done) {
        g_memory_threshold_tracker.last_reported_threshold = current_threshold;
        g_memory_threshold_tracker.initial_check_done = 1;

        /* Report initial state if above 0% */
        if (current_threshold > 0) {
            PRINTF("MM2: Initial memory usage at %u%% threshold (used: %u/%u sectors)\n",
                   current_threshold, used_sectors, g_memory_pool.total_sectors);
        }
        return;
    }

    /* Check if we've crossed to a new threshold */
    if (current_threshold > g_memory_threshold_tracker.last_reported_threshold) {
        /* Report each threshold we've crossed */
        for (uint32_t threshold = g_memory_threshold_tracker.last_reported_threshold + 10;
             threshold <= current_threshold;
             threshold += 10) {
            PRINTF("MM2: Memory usage crossed %u%% threshold (used: %u/%u sectors, %.1f%% actual)\n",
                   threshold, used_sectors, g_memory_pool.total_sectors,
                   (float)(used_sectors * 100.0) / g_memory_pool.total_sectors);
        }
        g_memory_threshold_tracker.last_reported_threshold = current_threshold;
    }
}
```

### 3. Integration Points

#### In `allocate_sector_for_sensor()` function:
```c
/* After successful allocation (line ~333 in mm2_pool.c) */
g_memory_pool.total_allocations++;

/* ADD THIS: Check for threshold crossing */
check_memory_threshold_crossing();
```

#### In `init_memory_pool()` function:
```c
/* Reset threshold tracker during initialization */
g_memory_threshold_tracker.last_reported_threshold = 0;
g_memory_threshold_tracker.initial_check_done = 0;
```

### 4. Platform Considerations

#### STM32 Platform
- Avoid floating-point in PRINTF (use integer math)
- Keep messages short due to limited resources
- Consider disabling in production builds

#### Linux Platform
- Full PRINTF support with formatting
- Can include more detailed information
- Always enabled in debug builds

---

## Testing Strategy

### Unit Test Cases

1. **Initial Allocation Test**
   - Start with empty pool
   - Allocate sectors to reach 10%
   - Verify message output at 10% crossing

2. **Multiple Threshold Test**
   - Continuously allocate sectors
   - Verify messages at 20%, 30%, 40%, etc.
   - Ensure no duplicate messages

3. **Rapid Allocation Test**
   - Allocate many sectors quickly
   - Verify all thresholds are reported
   - Check for skipped thresholds

4. **Edge Cases**
   - Pool exactly at threshold boundary
   - Single sector crossing multiple thresholds
   - Pool exhaustion scenario

### Integration Testing

1. **Normal Operation**
   - Run with typical sensor configuration
   - Monitor threshold messages during operation
   - Verify no performance impact

2. **Stress Testing**
   - Maximum sensors active
   - High data rate
   - Verify diagnostic output under load

3. **Platform Testing**
   - Test on both Linux and STM32
   - Verify PRINTF macro works correctly
   - Check log output formatting

---

## Implementation Checklist

### Development Tasks

- [ ] Add threshold tracking structure to mm2_pool.c
- [ ] Implement `check_memory_threshold_crossing()` function
- [ ] Add necessary includes for PRINTF macro
- [ ] Integrate threshold check in `allocate_sector_for_sensor()`
- [ ] Reset tracker in `init_memory_pool()`
- [ ] Add appropriate comments and documentation
- [ ] Handle platform-specific considerations
- [ ] Consider adding configuration option to enable/disable

### Testing Tasks

- [ ] Create unit test for threshold detection
- [ ] Test initial allocation scenario
- [ ] Test multiple threshold crossings
- [ ] Test rapid allocation scenario
- [ ] Test edge cases (boundaries, exhaustion)
- [ ] Perform integration testing
- [ ] Test on Linux platform
- [ ] Test on STM32 platform (if available)

### Documentation Tasks

- [ ] Update function documentation with new behavior
- [ ] Add diagnostic message format to documentation
- [ ] Document configuration options (if added)
- [ ] Update memory manager technical reference

### Code Review Tasks

- [ ] Verify no memory leaks introduced
- [ ] Check thread safety (Linux platform)
- [ ] Validate interrupt safety (STM32 platform)
- [ ] Ensure no performance regression
- [ ] Verify coding standards compliance

---

## Message Format Specification

### Standard Message Format
```
MM2: Memory usage crossed XX% threshold (used: UUUU/TTTT sectors, AA.A% actual)
```

Where:
- `XX`: Threshold percentage (10, 20, 30, etc.)
- `UUUU`: Used sectors count
- `TTTT`: Total sectors count
- `AA.A`: Actual percentage (with decimal)

### Example Output
```
MM2: Memory usage crossed 10% threshold (used: 205/2048 sectors, 10.0% actual)
MM2: Memory usage crossed 20% threshold (used: 410/2048 sectors, 20.0% actual)
MM2: Memory usage crossed 30% threshold (used: 615/2048 sectors, 30.0% actual)
```

---

## Risk Assessment

### Low Risk
- Simple addition to existing code
- No changes to core allocation logic
- Uses existing PRINTF infrastructure
- Can be disabled if issues arise

### Potential Issues
1. **Performance Impact**: Minimal, only simple calculation on allocation
2. **Log Flooding**: Limited to 9 messages maximum per pool lifetime
3. **Thread Safety**: Protected by existing pool lock
4. **Platform Compatibility**: PRINTF macro handles platform differences

---

## Alternative Approaches Considered

### 1. Continuous Monitoring
- Check thresholds periodically
- Rejected: Adds overhead without allocation

### 2. Callback System
- Register callbacks for thresholds
- Rejected: Over-engineering for simple requirement

### 3. Event System
- Generate events on threshold crossing
- Rejected: Requires additional infrastructure

### 4. Statistical Sampling
- Sample usage periodically
- Rejected: May miss threshold crossings

---

## Conclusion

This plan provides a simple, efficient implementation for memory manager diagnostic messaging. The approach:
- Meets all stated requirements
- Minimizes performance impact
- Integrates cleanly with existing code
- Provides useful diagnostic information
- Maintains platform compatibility

The implementation can be completed in approximately 2-3 hours including testing.

---

## Appendix: Code Snippets

### Complete Implementation for mm2_pool.c

```c
/* Add after includes section */
#ifdef DPRINT_DEBUGS_FOR_MEMORY_MANAGER
    #undef PRINTF
    #define PRINTF(...) if( LOGS_ENABLED( DEBUGS_FOR_MEMORY_MANAGER ) ) imx_cli_log_printf(true, __VA_ARGS__)
#else
    #define PRINTF(...)
#endif

/* Add threshold tracker structure */
static struct {
    uint32_t last_reported_threshold;
    uint32_t initial_check_done;
} g_memory_threshold_tracker = {0, 0};

/* Add threshold detection function */
static void check_memory_threshold_crossing(void) {
    uint32_t used_sectors = g_memory_pool.total_sectors - g_memory_pool.free_sectors;
    uint32_t usage_percent = (used_sectors * 100) / g_memory_pool.total_sectors;
    uint32_t current_threshold = (usage_percent / 10) * 10;

    if (!g_memory_threshold_tracker.initial_check_done) {
        g_memory_threshold_tracker.last_reported_threshold = current_threshold;
        g_memory_threshold_tracker.initial_check_done = 1;
        if (current_threshold > 0) {
            PRINTF("MM2: Initial memory usage at %u%% threshold (used: %u/%u sectors)\n",
                   current_threshold, used_sectors, g_memory_pool.total_sectors);
        }
        return;
    }

    if (current_threshold > g_memory_threshold_tracker.last_reported_threshold) {
        for (uint32_t threshold = g_memory_threshold_tracker.last_reported_threshold + 10;
             threshold <= current_threshold;
             threshold += 10) {
            PRINTF("MM2: Memory usage crossed %u%% threshold (used: %u/%u sectors)\n",
                   threshold, used_sectors, g_memory_pool.total_sectors);
        }
        g_memory_threshold_tracker.last_reported_threshold = current_threshold;
    }
}

/* Modify allocate_sector_for_sensor() - add after line 333 */
g_memory_pool.total_allocations++;
check_memory_threshold_crossing();  /* ADD THIS LINE */

/* Modify init_memory_pool() - add near end before return */
g_memory_threshold_tracker.last_reported_threshold = 0;
g_memory_threshold_tracker.initial_check_done = 0;
```

---

*Document Version: 1.0*
*Date: 2025-11-05*
*Author: Memory Manager Development Team*