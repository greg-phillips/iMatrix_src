# CAN Bus Statistics Enhancement Plan

**Date**: 2025-11-07
**Task**: Add comprehensive packet rate and drop statistics to CAN bus monitoring
**Branch**: feature/can-stats-enhancement (to be created)

---

## Executive Summary

Enhance the CAN bus subsystem with real-time packet rate tracking, drop rate monitoring, and historical statistics. This will provide better visibility into CAN bus health, identify buffer exhaustion issues, and support performance optimization.

### Key Enhancements

1. **Packet Rate Tracking**: Frames per second (FPS) for RX/TX
2. **Drop Rate Statistics**: Dropped packets per second due to buffer full
3. **Ring Buffer Utilization**: Current and peak usage percentages
4. **Historical Data**: Peak rates, total drops, cumulative statistics
5. **Per-Bus Statistics**: Independent tracking for CAN0, CAN1, and Ethernet CAN

---

## Current State Analysis

### Existing Statistics (canbus/can_structs.h)

```c
typedef struct can_stats_ {
    uint32_t tx_frames;      // Total frames transmitted
    uint32_t rx_frames;      // Total frames received
    uint32_t tx_bytes;       // Total bytes transmitted
    uint32_t rx_bytes;       // Total bytes received
    uint32_t tx_errors;      // Transmission errors
    uint32_t rx_errors;      // Reception errors
    uint32_t no_free_msgs;   // Dropped due to ring buffer full
} can_stats_t;
```

### Where Stats Are Updated

**RX Frame Processing** (`can_utils.c:550-638`):
```c
can_stats->rx_bytes += bufLen;      // Line 594
can_stats->rx_frames += 1;          // Line 595
can_stats->no_free_msgs++;          // Line 611 (when ring buffer full)
```

**TX Frame Processing** (`can_utils.c:445-491`):
```c
can_stats->tx_errors += 1;          // Line 475 (on error)
can_stats->tx_bytes += can_msg->can_dlc;  // Line 486
can_stats->tx_frames += 1;          // Line 487
```

### Current Display (`can_server.c:814-832`):
- Shows cumulative counters only
- No rate information
- No buffer utilization
- No historical peaks

---

## Proposed Enhancements

### Enhancement #1: Extended Statistics Structure

**File**: `canbus/can_structs.h`

**Add to can_stats_t**:
```c
typedef struct can_stats_ {
    /* Existing cumulative counters */
    uint32_t tx_frames;
    uint32_t rx_frames;
    uint32_t tx_bytes;
    uint32_t rx_bytes;
    uint32_t tx_errors;
    uint32_t rx_errors;
    uint32_t no_free_msgs;

    /* NEW: Rate tracking (calculated periodically) */
    uint32_t rx_frames_per_sec;       // Current RX frame rate
    uint32_t tx_frames_per_sec;       // Current TX frame rate
    uint32_t rx_bytes_per_sec;        // Current RX byte rate
    uint32_t tx_bytes_per_sec;        // Current TX byte rate
    uint32_t drops_per_sec;           // Current drop rate

    /* NEW: Historical peaks (since boot or reset) */
    uint32_t peak_rx_frames_per_sec;  // Highest RX rate observed
    uint32_t peak_tx_frames_per_sec;  // Highest TX rate observed
    uint32_t peak_drops_per_sec;      // Highest drop rate observed
    imx_time_t peak_rx_time;          // When peak RX occurred
    imx_time_t peak_tx_time;          // When peak TX occurred
    imx_time_t peak_drop_time;        // When peak drops occurred

    /* NEW: Ring buffer utilization */
    uint32_t ring_buffer_size;        // Total pool size
    uint32_t ring_buffer_free;        // Current free count
    uint32_t ring_buffer_in_use;      // Currently allocated
    uint32_t ring_buffer_peak_used;   // Highest usage observed
    uint32_t ring_buffer_utilization_percent;  // Current usage %

    /* NEW: Timing for rate calculation */
    imx_time_t last_rate_calc_time;   // Last time rates were calculated
    uint32_t prev_rx_frames;          // Previous rx_frames for delta
    uint32_t prev_tx_frames;          // Previous tx_frames for delta
    uint32_t prev_rx_bytes;           // Previous rx_bytes for delta
    uint32_t prev_tx_bytes;           // Previous tx_bytes for delta
    uint32_t prev_no_free_msgs;       // Previous drops for delta

    /* NEW: Session statistics (resetable) */
    imx_time_t session_start_time;    // When stats were last reset
    uint32_t session_total_drops;     // Drops this session
    uint32_t session_total_rx;        // RX frames this session
    uint32_t session_total_tx;        // TX frames this session
} can_stats_t;
```

### Enhancement #2: Rate Calculation Function

**File**: `canbus/can_utils.c` (new function)

**Function**: `imx_update_can_statistics()`

```c
/**
 * @brief Update CAN statistics with rate calculations
 *
 * Should be called periodically (e.g., every 1 second) to calculate:
 * - Frames per second (RX/TX)
 * - Bytes per second (RX/TX)
 * - Drops per second
 * - Ring buffer utilization
 * - Peak values
 *
 * @param current_time Current system time in milliseconds
 * @return None
 */
void imx_update_can_statistics(imx_time_t current_time) {
    /* Update each bus statistics */
    update_bus_statistics(&cb.can0_stats, &can0_ring, current_time);
    update_bus_statistics(&cb.can1_stats, &can1_ring, current_time);
    update_bus_statistics(&cb.can_eth_stats, &can2_ring, current_time);
}

/**
 * @brief Update statistics for a single CAN bus
 *
 * Calculates rates, updates peaks, and tracks utilization.
 *
 * @param stats Pointer to bus statistics structure
 * @param ring Pointer to ring buffer for utilization tracking
 * @param current_time Current system time
 * @return None
 */
static void update_bus_statistics(can_stats_t *stats,
                                  can_ring_buffer_t *ring,
                                  imx_time_t current_time) {
    /* Calculate time delta */
    imx_time_t time_delta = current_time - stats->last_rate_calc_time;

    /* Only calculate if at least 1 second has elapsed */
    if (time_delta < 1000) {
        return;
    }

    /* Convert to seconds for rate calculation */
    float time_delta_sec = (float)time_delta / 1000.0f;

    /* Calculate RX frame rate */
    uint32_t rx_delta = stats->rx_frames - stats->prev_rx_frames;
    stats->rx_frames_per_sec = (uint32_t)((float)rx_delta / time_delta_sec);

    /* Calculate TX frame rate */
    uint32_t tx_delta = stats->tx_frames - stats->prev_tx_frames;
    stats->tx_frames_per_sec = (uint32_t)((float)tx_delta / time_delta_sec);

    /* Calculate RX byte rate */
    uint32_t rx_bytes_delta = stats->rx_bytes - stats->prev_rx_bytes;
    stats->rx_bytes_per_sec = (uint32_t)((float)rx_bytes_delta / time_delta_sec);

    /* Calculate TX byte rate */
    uint32_t tx_bytes_delta = stats->tx_bytes - stats->prev_tx_bytes;
    stats->tx_bytes_per_sec = (uint32_t)((float)tx_bytes_delta / time_delta_sec);

    /* Calculate drop rate */
    uint32_t drops_delta = stats->no_free_msgs - stats->prev_no_free_msgs;
    stats->drops_per_sec = (uint32_t)((float)drops_delta / time_delta_sec);

    /* Update peak values */
    if (stats->rx_frames_per_sec > stats->peak_rx_frames_per_sec) {
        stats->peak_rx_frames_per_sec = stats->rx_frames_per_sec;
        stats->peak_rx_time = current_time;
    }

    if (stats->tx_frames_per_sec > stats->peak_tx_frames_per_sec) {
        stats->peak_tx_frames_per_sec = stats->tx_frames_per_sec;
        stats->peak_tx_time = current_time;
    }

    if (stats->drops_per_sec > stats->peak_drops_per_sec) {
        stats->peak_drops_per_sec = stats->drops_per_sec;
        stats->peak_drop_time = current_time;
    }

    /* Calculate ring buffer utilization */
    stats->ring_buffer_free = can_ring_buffer_free_count(ring);
    stats->ring_buffer_in_use = stats->ring_buffer_size - stats->ring_buffer_free;
    stats->ring_buffer_utilization_percent =
        (stats->ring_buffer_in_use * 100) / stats->ring_buffer_size;

    /* Track peak buffer usage */
    if (stats->ring_buffer_in_use > stats->ring_buffer_peak_used) {
        stats->ring_buffer_peak_used = stats->ring_buffer_in_use;
    }

    /* Save current values for next delta calculation */
    stats->prev_rx_frames = stats->rx_frames;
    stats->prev_tx_frames = stats->tx_frames;
    stats->prev_rx_bytes = stats->rx_bytes;
    stats->prev_tx_bytes = stats->tx_bytes;
    stats->prev_no_free_msgs = stats->no_free_msgs;
    stats->last_rate_calc_time = current_time;
}
```

### Enhancement #3: Statistics Initialization

**File**: `canbus/can_utils.c:setup_can_bus()`

**Add after ring buffer initialization (around line 486)**:
```c
/* Initialize statistics tracking */
memset(&cb.can0_stats, 0, sizeof(can_stats_t));
memset(&cb.can1_stats, 0, sizeof(can_stats_t));
memset(&cb.can_eth_stats, 0, sizeof(can_stats_t));

/* Set ring buffer sizes */
cb.can0_stats.ring_buffer_size = CAN_MSG_POOL_SIZE;
cb.can1_stats.ring_buffer_size = CAN_MSG_POOL_SIZE;
cb.can_eth_stats.ring_buffer_size = CAN_MSG_POOL_SIZE;

/* Initialize timing */
imx_time_t current_time;
imx_time_get_time(&current_time);
cb.can0_stats.last_rate_calc_time = current_time;
cb.can0_stats.session_start_time = current_time;
cb.can1_stats.last_rate_calc_time = current_time;
cb.can1_stats.session_start_time = current_time;
cb.can_eth_stats.last_rate_calc_time = current_time;
cb.can_eth_stats.session_start_time = current_time;

PRINTF("[CAN BUS - Statistics tracking initialized]\r\n");
```

### Enhancement #4: Periodic Update Integration

**File**: `canbus/can_process.c` or main loop

**Add to periodic processing**:
```c
/* Update CAN statistics every cycle */
imx_update_can_statistics(current_time);
```

### Enhancement #5: Enhanced Display Function

**File**: `canbus/can_server.c:imx_display_can_server_status()`

**User Requirement**: Statistics integrated into existing can server command output

**Replace traffic statistics section (lines 814-832)**:
```c
/* Traffic Statistics Section */
if (cb.use_ethernet_server) {
    imx_cli_print("\r\nTraffic Statistics:\r\n");

    /* Cumulative counters */
    imx_cli_print("  Cumulative:\r\n");
    imx_cli_print("    RX Frames:             %lu\r\n",
                  (unsigned long)cb.can_eth_stats.rx_frames);
    imx_cli_print("    TX Frames:             %lu\r\n",
                  (unsigned long)cb.can_eth_stats.tx_frames);
    imx_cli_print("    RX Bytes:              %lu\r\n",
                  (unsigned long)cb.can_eth_stats.rx_bytes);
    imx_cli_print("    TX Bytes:              %lu\r\n",
                  (unsigned long)cb.can_eth_stats.tx_bytes);
    imx_cli_print("    Dropped (Buffer Full): %lu\r\n",
                  (unsigned long)cb.can_eth_stats.no_free_msgs);
    imx_cli_print("    RX Errors:             %lu\r\n",
                  (unsigned long)cb.can_eth_stats.rx_errors);
    imx_cli_print("    TX Errors:             %lu\r\n",
                  (unsigned long)cb.can_eth_stats.tx_errors);
    imx_cli_print("    Malformed Frames:      %lu\r\n",
                  (unsigned long)cb.can_eth_malformed_frames);

    /* Current rates */
    imx_cli_print("\r\n  Current Rates:\r\n");
    imx_cli_print("    RX Frame Rate:         %u fps\r\n",
                  cb.can_eth_stats.rx_frames_per_sec);
    imx_cli_print("    TX Frame Rate:         %u fps\r\n",
                  cb.can_eth_stats.tx_frames_per_sec);
    imx_cli_print("    RX Byte Rate:          %u Bps\r\n",
                  cb.can_eth_stats.rx_bytes_per_sec);
    imx_cli_print("    TX Byte Rate:          %u Bps\r\n",
                  cb.can_eth_stats.tx_bytes_per_sec);
    imx_cli_print("    Drop Rate:             %u drops/sec\r\n",
                  cb.can_eth_stats.drops_per_sec);

    /* Peak rates */
    imx_cli_print("\r\n  Peak Rates:\r\n");
    imx_cli_print("    Peak RX:               %u fps\r\n",
                  cb.can_eth_stats.peak_rx_frames_per_sec);
    imx_cli_print("    Peak TX:               %u fps\r\n",
                  cb.can_eth_stats.peak_tx_frames_per_sec);
    imx_cli_print("    Peak Drops:            %u drops/sec\r\n",
                  cb.can_eth_stats.peak_drops_per_sec);

    /* Ring buffer utilization */
    imx_cli_print("\r\n  Ring Buffer:\r\n");
    imx_cli_print("    Total Size:            %u messages\r\n",
                  cb.can_eth_stats.ring_buffer_size);
    imx_cli_print("    Free Messages:         %u\r\n",
                  cb.can_eth_stats.ring_buffer_free);
    imx_cli_print("    In Use:                %u (%u%%)\r\n",
                  cb.can_eth_stats.ring_buffer_in_use,
                  cb.can_eth_stats.ring_buffer_utilization_percent);
    imx_cli_print("    Peak Usage:            %u messages (%u%%)\r\n",
                  cb.can_eth_stats.ring_buffer_peak_used,
                  (cb.can_eth_stats.ring_buffer_peak_used * 100) / cb.can_eth_stats.ring_buffer_size);

    /* Health indicators */
    if (cb.can_eth_stats.drops_per_sec > 0) {
        imx_cli_print("\r\n  WARNING: Packets being dropped! Consider:\r\n");
        imx_cli_print("    - Increasing ring buffer size (currently %u)\r\n",
                      cb.can_eth_stats.ring_buffer_size);
        imx_cli_print("    - Reducing CAN traffic rate\r\n");
        imx_cli_print("    - Optimizing message processing speed\r\n");
    }

    if (cb.can_eth_stats.ring_buffer_utilization_percent > 80) {
        imx_cli_print("\r\n  WARNING: Ring buffer >80%% full (%u%%)\r\n",
                      cb.can_eth_stats.ring_buffer_utilization_percent);
    }
}
```

### Enhancement #6: Statistics Reset Function (Optional)

**File**: `canbus/can_utils.c` (new function)

```c
/**
 * @brief Reset CAN statistics for specified bus
 *
 * Clears all counters and resets session tracking.
 * Preserves ring buffer size configuration.
 *
 * @param bus CAN bus to reset (CAN_BUS_0, CAN_BUS_1, or 2 for Ethernet)
 * @return None
 */
void imx_reset_can_statistics(uint32_t bus) {
    can_stats_t *stats;

    switch (bus) {
        case CAN_BUS_0:
            stats = &cb.can0_stats;
            break;
        case CAN_BUS_1:
            stats = &cb.can1_stats;
            break;
        case 2:  /* Ethernet */
            stats = &cb.can_eth_stats;
            break;
        default:
            PRINTF("Invalid bus ID for stats reset: %u\r\n", bus);
            return;
    }

    /* Save ring buffer size (don't reset) */
    uint32_t saved_ring_size = stats->ring_buffer_size;

    /* Clear everything */
    memset(stats, 0, sizeof(can_stats_t));

    /* Restore non-resetable values */
    stats->ring_buffer_size = saved_ring_size;

    /* Initialize timing */
    imx_time_t current_time;
    imx_time_get_time(&current_time);
    stats->last_rate_calc_time = current_time;
    stats->session_start_time = current_time;

    PRINTF("[CAN BUS %u - Statistics reset]\r\n", bus);
}
```

---

## Implementation Checklist

### Phase 1: Structure Enhancement
- [ ] Modify `can_stats_t` structure in `canbus/can_structs.h`
- [ ] Add rate tracking fields
- [ ] Add historical peak fields
- [ ] Add ring buffer utilization fields
- [ ] Add timing fields

### Phase 2: Core Functions
- [ ] Implement `update_bus_statistics()` in `can_utils.c`
- [ ] Implement `imx_update_can_statistics()` in `can_utils.c`
- [ ] Add function declarations to `can_utils.h`

### Phase 3: Initialization
- [ ] Update `setup_can_bus()` to initialize new fields
- [ ] Set ring_buffer_size for each bus
- [ ] Initialize timing fields

### Phase 4: Integration
- [ ] Add `imx_update_can_statistics()` call to main processing loop
- [ ] Call every ~1 second for rate calculations
- [ ] Ensure it's called for all three buses

### Phase 5: Display Enhancement
- [ ] Update `imx_display_can_server_status()` in `can_server.c`
- [ ] Add rate information
- [ ] Add buffer utilization
- [ ] Add health warnings

### Phase 6: Additional Features
- [ ] Implement `imx_reset_can_statistics()` function
- [ ] Implement `imx_display_all_can_statistics()` function
- [ ] Add CLI commands for stats display/reset

### Phase 7: Testing
- [ ] Verify rate calculations are accurate
- [ ] Test under high load (>1000 fps)
- [ ] Test drop rate tracking with buffer exhaustion
- [ ] Verify peak tracking works correctly
- [ ] Test stats reset functionality

### Phase 8: Documentation
- [ ] Add Doxygen comments to all new functions
- [ ] Update user documentation
- [ ] Create examples for interpretation

---

## CLI Commands to Add

```c
/* In CLI command table */
{"canstats",     cmd_can_statistics,      "Display CAN bus statistics"},
{"canstats0",    cmd_can0_statistics,     "Display CAN0 statistics"},
{"canstats1",    cmd_can1_statistics,     "Display CAN1 statistics"},
{"canstatseth",  cmd_caneth_statistics,   "Display Ethernet CAN statistics"},
{"canreset",     cmd_can_reset_stats,     "Reset CAN statistics"},
```

---

## Example Output

```
=== CAN Bus Statistics ===

Metric                      CAN0          CAN1      Ethernet
------------------------------------------------------------------
Total RX Frames              125430       0             892341
Total TX Frames              1250         0             0
Dropped (Buffer Full)        0            0             142

RX Rate                      450 fps      0 fps         3200 fps
TX Rate                      5 fps        0 fps         0 fps
Drop Rate                    0 d/s        0 d/s         12 d/s

Buffer Usage                 35%          0%            87%
Free Messages                325          500           65

⚠️  WARNING: Packets being dropped on Ethernet CAN!
⚠️  WARNING: Ring buffer utilization >80% on Ethernet CAN!

========================================
```

---

## Benefits

1. **Performance Monitoring**: Real-time visibility into traffic patterns
2. **Capacity Planning**: See when buffers are approaching limits
3. **Problem Detection**: Immediate notification of packet drops
4. **Historical Analysis**: Peak rate tracking for system sizing
5. **Debugging**: Correlate drops with system events

---

## Estimated Complexity

- **Structure Changes**: Simple (add fields)
- **Rate Calculation**: Medium (delta calculation, timing)
- **Display Updates**: Simple (format changes)
- **Integration**: Medium (find correct call point)
- **Testing**: Medium (need load generation)

**Total Effort**: ~4-6 hours (including testing)

---

## Questions Before Implementation

1. **Update Frequency**: Should statistics be updated every 1 second, or different interval?

2. **Display Format**: Do you want:
   - Single bus detailed view (current approach)
   - Multi-bus comparison table (new function)
   - Both options available?

3. **CLI Integration**: Should I add dedicated CLI commands, or integrate into existing commands?

4. **Thresholds**: What warning thresholds?
   - Buffer utilization > 80%?
   - Drop rate > 10/sec?

5. **Testing**: Can you generate high CAN traffic for testing, or should I create test scenarios?

---

**Status**: Plan complete - awaiting approval to proceed with implementation
**Next Step**: Answer questions, then begin Phase 1

