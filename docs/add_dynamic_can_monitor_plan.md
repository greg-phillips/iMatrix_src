# Dynamic CAN Monitor Implementation Plan

**Document Version:** 1.0
**Date:** 2025-11-12
**Author:** Claude Code
**Feature Branches:**
- iMatrix: `feature/dynamic-can-monitor` (from `Aptera_1_Clean`)
- Fleet-Connect-1: `feature/dynamic-can-monitor` (from `Aptera_1_Clean`)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements Analysis](#requirements-analysis)
3. [Architecture Overview](#architecture-overview)
4. [Detailed Design](#detailed-design)
5. [Implementation Tasks](#implementation-tasks)
6. [Testing Plan](#testing-plan)
7. [Files to Modify/Create](#files-to-modifycreate)
8. [Risk Assessment](#risk-assessment)

---

## Executive Summary

### Goal

Add a dynamically updating CAN BUS monitor display (1Hz refresh) that shows comprehensive statistics for:
- Physical CAN 0 and CAN 1 buses
- CAN Ethernet Server (bus 2)
- All logical buses on CAN Ethernet (bus 2+)

### Approach

Leverage the existing `cli_monitor` framework (used by `cli_memory_monitor`) to create a similar non-blocking, auto-updating display for CAN statistics. The monitor will use the existing `can_stats_t` structures already present in the system.

### Key Benefits

1. **Reuses proven architecture**: Uses the same framework as memory monitor
2. **Non-blocking**: Runs concurrently with other system processes
3. **Minimal changes**: Statistics structures already exist, just need display code
4. **Extensible**: Easy to add more statistics or views in the future

---

## Requirements Analysis

### Functional Requirements

1. **Display Physical Bus Statistics**
   - CAN 0: RX/TX frames, bytes, rates, errors, buffer utilization
   - CAN 1: RX/TX frames, bytes, rates, errors, buffer utilization

2. **Display CAN Ethernet Server Statistics**
   - Connection status (Open/Closed)
   - Format type (PCAN/APTERA)
   - Overall traffic statistics for Ethernet CAN (bus 2)
   - **Dropped frames count and rate (CRITICAL)**
   - **Buffer utilization with progress bar (CRITICAL)**
   - Buffer peak usage
   - Malformed frame count

3. **Display Logical Bus Statistics** (for APTERA format only)
   - Per-logical bus breakdown (PT, IN, etc.)
   - Individual RX/TX statistics for each logical bus
   - Only for buses on physical CAN Ethernet (bus 2+)

4. **Display Modes**
   - Summary view: All buses side-by-side
   - Grouped view: Physical bus sections with logical bus breakdowns
   - Toggle between views with keypresses

5. **Interactive Features**
   - Press 'q' to quit
   - Press 'p' to pause/resume updates
   - Press 'v' to toggle view modes
   - Press 'r' to reset statistics (if supported)
   - Press 's' to take snapshot
   - 1-second refresh rate

6. **Runtime Behavior**
   - Non-blocking: Other processes continue while monitor runs
   - Uses ANSI terminal control for smooth updates
   - Returns to normal CLI when exited

### Non-Functional Requirements

1. **Performance**: Minimal CPU overhead (< 1% additional load)
2. **Compatibility**: Linux platform only (like memory monitor)
3. **Code Quality**: Follow iMatrix coding standards, extensive Doxygen comments
4. **Maintainability**: Clear separation of concerns, modular design

---

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────┐
│          User Terminal (SSH/Console)         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              iMatrix CLI System              │
│  ┌───────────────────────────────────────┐  │
│  │  Command: canstats                    │  │
│  └───────────────────────────────────────┘  │
│                    ↓                        │
│  ┌───────────────────────────────────────┐  │
│  │  cli_can_monitor.c (NEW)              │  │
│  │  - Initialize monitor context         │  │
│  │  - Register with cli_monitor framework│  │
│  └───────────────────────────────────────┘  │
│                    ↓                        │
│  ┌───────────────────────────────────────┐  │
│  │  cli_monitor.c (EXISTING FRAMEWORK)   │  │
│  │  - Manages display buffer             │  │
│  │  - Handles input processing           │  │
│  │  - Periodic refresh at 1Hz            │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│            CAN Bus Subsystem                 │
│  ┌───────────────────────────────────────┐  │
│  │  canbus_product_t (cb)                │  │
│  │  - can0_stats (physical CAN 0)        │  │
│  │  - can1_stats (physical CAN 1)        │  │
│  │  - can_eth_stats (Ethernet CAN)       │  │
│  │  - cbs (CAN bus status)               │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │  config_v12_t *device_config_v12      │  │
│  │  - logical_buses[] (logical configs)  │  │
│  │    - stats (per-logical bus stats)    │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Component Diagram

```
cli_can_monitor.c (NEW)
    ├── Initialization
    │   ├── cli_can_monitor_init()
    │   └── Register with cli_monitor framework
    │
    ├── Content Generation
    │   ├── generate_can_content()
    │   ├── display_physical_buses()
    │   ├── display_ethernet_server()
    │   └── display_logical_buses()
    │
    ├── User Interaction
    │   ├── process_can_key()
    │   └── Handle view toggle, pause, etc.
    │
    └── Cleanup
        └── cleanup_can_monitor()

cli_monitor.c (EXISTING)
    ├── Framework Core
    │   ├── cli_monitor_init()
    │   ├── cli_monitor_update()
    │   └── cli_monitor_cleanup()
    │
    ├── Display Management
    │   ├── cli_monitor_add_line()
    │   ├── cli_monitor_add_box_top()
    │   ├── cli_monitor_add_box_line()
    │   └── cli_monitor_add_box_bottom()
    │
    └── Input Processing
        └── cli_monitor_process_char()
```

---

## Detailed Design

### Data Structures

#### Monitor Context Structure

```c
/**
 * @brief CAN monitor context
 *
 * Maintains state for the CAN monitor including display preferences,
 * snapshot data, and previous values for trend calculation.
 */
typedef struct {
    /* Display preferences */
    enum {
        VIEW_SUMMARY,        /* All buses side-by-side */
        VIEW_GROUPED,        /* Physical buses with logical breakdowns */
        VIEW_DETAILED        /* Detailed view of selected bus */
    } view_mode;

    /* Previous values for trend calculation */
    uint32_t prev_can0_rx_frames;
    uint32_t prev_can0_tx_frames;
    uint32_t prev_can1_rx_frames;
    uint32_t prev_can1_tx_frames;
    uint32_t prev_eth_rx_frames;
    uint32_t prev_eth_tx_frames;

    /* Snapshot values */
    can_stats_t snapshot_can0;
    can_stats_t snapshot_can1;
    can_stats_t snapshot_eth;
    bool snapshot_taken;

    /* Selected bus for detailed view */
    uint8_t selected_bus_id;

} can_monitor_context_t;
```

### Display Layout

#### Summary View

```
+---------------------------------------------------------------------------------+
|                            CAN Bus Monitor                                      |
|  Last Updated: 2025-11-12 15:23:45                                             |
+---------------------------------------------------------------------------------+
|  Physical Buses                                                                 |
+---------------------------+---------------------------+-------------------------+
|  CAN 0                    |  CAN 1                    |  Ethernet (Bus 2)       |
|  Status:    Open          |  Status:    Open          |  Status:    Open        |
|  RX:        1234 fps      |  RX:         567 fps      |  RX:         890 fps    |
|  TX:         456 fps      |  TX:         123 fps      |  TX:         234 fps    |
|  RX Bytes:  45.2 KB/s     |  RX Bytes:  23.1 KB/s     |  RX Bytes:  34.5 KB/s   |
|  TX Bytes:  12.3 KB/s     |  TX Bytes:   5.6 KB/s     |  TX Bytes:  10.2 KB/s   |
|  Errors:         0        |  Errors:         0        |  Errors:         2      |
|  Drops:          0        |  Drops:          0        |  Drops:          5      |
|  Buffer:    [====-----] 50%  Buffer:    [===------] 30%  Buffer:    [=====---] 60% |
+---------------------------+---------------------------+-------------------------+
|  Ethernet CAN Server                                                            |
+---------------------------------------------------------------------------------+
|  Format:           APTERA                                                       |
|  Malformed Frames: 3                                                            |
|  Dropped Frames:   5        Drop Rate: 2 drops/sec  ⚠                          |
|  Buffer Usage:     [============--------] 60% (240/400)                         |
|  Peak Buffer:      85% (340/400)                                                |
|  Virtual Buses:    3 (PT, IN, Chassis)                                          |
+---------------------------------------------------------------------------------+
|  Logical Buses (Ethernet)                                                       |
+---------------------------+---------------------------+-------------------------+
|  [2] PT (Powertrain)      |  [3] IN (Infotainment)    |  [4] Chassis            |
|  RX:         345 fps      |  RX:         234 fps      |  RX:         311 fps    |
|  TX:         123 fps      |  TX:          89 fps      |  TX:          22 fps    |
|  Peak RX:    450 fps      |  Peak RX:    300 fps      |  Peak RX:    400 fps    |
+---------------------------+---------------------------+-------------------------+
|  Press 'v' to change view, 's' for snapshot, 'r' to reset, 'q' to quit         |
+---------------------------------------------------------------------------------+
```

#### Grouped View

```
+---------------------------------------------------------------------------------+
|                      CAN Bus Monitor (Grouped View)                             |
|  Last Updated: 2025-11-12 15:23:45                                             |
+---------------------------------------------------------------------------------+
|  === Physical CAN Bus 0 ===                                                     |
|  Status:                 Open                                                   |
|  RX Frames:              1234 fps    (Peak: 1500 fps)  ↑                       |
|  TX Frames:               456 fps    (Peak:  600 fps)  -                       |
|  RX Bytes:               45.2 KB/s   (Peak: 60.0 KB/s)                         |
|  TX Bytes:               12.3 KB/s   (Peak: 15.0 KB/s)                         |
|  RX Errors:                  0                                                  |
|  TX Errors:                  0                                                  |
|  Buffer Usage:           [==========----------]  50% (200/400)                  |
|  Peak Buffer Usage:      75% (300/400)                                          |
+---------------------------------------------------------------------------------+
|  === Physical CAN Bus 1 ===                                                     |
|  Status:                 Open                                                   |
|  RX Frames:               567 fps    (Peak:  700 fps)  ↓                       |
|  TX Frames:               123 fps    (Peak:  200 fps)  -                       |
|  RX Bytes:               23.1 KB/s   (Peak: 30.0 KB/s)                         |
|  TX Bytes:                5.6 KB/s   (Peak:  8.0 KB/s)                         |
|  RX Errors:                  0                                                  |
|  TX Errors:                  0                                                  |
|  Buffer Usage:           [======--------------]  30% (120/400)                  |
|  Peak Buffer Usage:      60% (240/400)                                          |
+---------------------------------------------------------------------------------+
|  === Ethernet CAN (Physical Bus 2) ===                                          |
|  Server Status:          Running                                                |
|  Server Format:          APTERA                                                 |
|  Connection:             Open                                                   |
|  RX Frames:               890 fps    (Peak: 1100 fps)  ↑                       |
|  TX Frames:               234 fps    (Peak:  300 fps)  -                       |
|  RX Bytes:               34.5 KB/s   (Peak: 45.0 KB/s)                         |
|  TX Bytes:               10.2 KB/s   (Peak: 15.0 KB/s)                         |
|  RX Errors:                  2                                                  |
|  TX Errors:                  1                                                  |
|  Malformed Frames:           3                                                  |
|  Dropped Frames:             5       Drop Rate: 2 drops/sec  ⚠                 |
|  Buffer Usage:           [============--------]  60% (240/400)  ⚠              |
|  Peak Buffer Usage:      85% (340/400)                                          |
|                                                                                 |
|  --- Logical Buses on Ethernet ---                                              |
|                                                                                 |
|  [2] Powertrain (PT):                                                           |
|      RX: 345 fps  (Peak: 450 fps)      TX: 123 fps  (Peak: 150 fps)            |
|                                                                                 |
|  [3] Infotainment (IN):                                                         |
|      RX: 234 fps  (Peak: 300 fps)      TX:  89 fps  (Peak: 120 fps)            |
|                                                                                 |
|  [4] Chassis:                                                                   |
|      RX: 311 fps  (Peak: 400 fps)      TX:  22 fps  (Peak:  30 fps)            |
+---------------------------------------------------------------------------------+
|  Press 'v' to change view, 's' for snapshot, 'r' to reset, 'q' to quit         |
+---------------------------------------------------------------------------------+
```

### Key Functions

#### Initialization

```c
/**
 * @brief Initialize the CAN bus monitor
 *
 * Sets up the monitor context and registers with the generic
 * CLI monitor framework. Initializes display preferences and
 * clears any previous state.
 *
 * @return true if initialization successful, false on error
 */
bool cli_can_monitor_init(void);
```

#### Content Generation

```c
/**
 * @brief Generate CAN monitor content
 *
 * Main content generator called by the framework every refresh cycle (1Hz).
 * Reads current CAN statistics and formats them for display using the
 * cli_monitor_add_*() functions.
 *
 * @param ctx Context pointer (can_monitor_context_t)
 */
static void generate_can_content(void *ctx);

/**
 * @brief Display physical CAN bus statistics
 *
 * Shows statistics for CAN 0 and CAN 1 physical buses including
 * traffic rates, error counts, and buffer utilization.
 */
static void display_physical_buses(void);

/**
 * @brief Display Ethernet CAN server status
 *
 * Shows server configuration (format type, connection status)
 * and overall Ethernet CAN statistics.
 */
static void display_ethernet_server(void);

/**
 * @brief Display logical bus statistics
 *
 * For APTERA format only: Shows per-logical bus breakdown of
 * traffic statistics for all Ethernet logical buses.
 */
static void display_logical_buses(void);

/**
 * @brief Format CAN statistics into display string
 *
 * Utility function to format can_stats_t into human-readable
 * strings with units (fps, KB/s, etc.).
 *
 * @param stats Pointer to statistics structure
 * @param buffer Output buffer
 * @param size Buffer size
 */
static void format_can_stats(const can_stats_t *stats, char *buffer, size_t size);
```

#### Key Processing

```c
/**
 * @brief Process CAN monitor specific keys
 *
 * Handles custom key presses for CAN monitor functionality:
 * - 'v'/'V': Toggle view mode (summary/grouped/detailed)
 * - 's'/'S': Take snapshot of current statistics
 * - 'c'/'C': Clear snapshot
 * - 'r'/'R': Reset statistics (if supported)
 * - '0'-'9': Select bus for detailed view
 *
 * @param ch Character to process
 * @return true if key was handled, false for default handling
 */
static bool process_can_key(char ch);
```

#### Helper Functions

```c
/**
 * @brief Get trend indicator for value
 *
 * Compares current value to previous and returns trend character.
 *
 * @param current Current value
 * @param previous Previous value
 * @return '↑' if increasing, '↓' if decreasing, '-' if stable
 */
static char get_trend_indicator(uint32_t current, uint32_t previous);

/**
 * @brief Check if logical bus is on Ethernet
 *
 * Determines if a logical bus is on physical bus 2 (Ethernet).
 *
 * @param bus Pointer to logical bus config
 * @return true if bus is on Ethernet (bus 2+)
 */
static bool is_ethernet_logical_bus(const logical_bus_config_t *bus);
```

---

## Implementation Tasks

### Phase 1: Foundation (Day 1)

#### Task 1.1: Create Core Files
- [ ] Create `iMatrix/cli/cli_can_monitor.h`
  - Function declarations
  - Structure definitions
  - Public API documentation
- [ ] Create `iMatrix/cli/cli_can_monitor.c`
  - Basic structure with stub functions
  - Include proper copyright header
  - Follow blank.c template

**Estimated Time:** 1 hour

#### Task 1.2: Add CLI Command Registration
- [ ] Modify `iMatrix/cli/cli.c`
  - Add `CLI_CAN_MONITOR` state to enum (around line 100)
  - Add `canstats` command to command table
  - Register handler function
- [ ] Add function pointer: `{"canstats", &cli_can_monitor, 0, "CAN bus statistics monitor"}`

**Estimated Time:** 30 minutes

#### Task 1.3: Update Build System
- [ ] Modify `iMatrix/CMakeLists.txt`
  - Add `cli/cli_can_monitor.c` to source list (in Linux platform section)
- [ ] Test compilation: `cd iMatrix/build && cmake .. && make`

**Estimated Time:** 15 minutes

### Phase 2: Basic Implementation (Day 1-2)

#### Task 2.1: Implement Initialization
- [ ] Write `cli_can_monitor_init()`
  - Initialize monitor context structure
  - Set default view mode
  - Clear previous values
  - Register with cli_monitor framework
- [ ] Write `cleanup_can_monitor()`
  - Clean up resources
  - Reset context

**Estimated Time:** 1 hour

#### Task 2.2: Implement Physical Bus Display
- [ ] Write `display_physical_buses()`
  - Access `cb.can0_stats` and `cb.can1_stats`
  - Format statistics using cli_monitor_add_box_line()
  - Add trend indicators
  - Show buffer utilization with progress bars
- [ ] Test with physical CAN buses active

**Estimated Time:** 2 hours

#### Task 2.3: Implement Ethernet Server Display
- [ ] Write `display_ethernet_server()`
  - Access `cb.can_eth_stats`
  - Show server status from `cb.cbs`
  - Display format type from `cb.ethernet_can_format`
  - Show malformed frame count
- [ ] Test with Ethernet CAN server running

**Estimated Time:** 1.5 hours

### Phase 3: Logical Bus Support (Day 2-3)

#### Task 3.1: Implement Logical Bus Display
- [ ] Write `display_logical_buses()`
  - Check if `device_config_v12` is available
  - Iterate through `logical_buses[]` array
  - Filter for Ethernet buses only (physical_bus_id == CAN_BUS_ETH)
  - Display per-logical bus statistics
- [ ] Handle case where no logical buses exist

**Estimated Time:** 2 hours

#### Task 3.2: Implement View Modes
- [ ] Create view mode toggle logic
  - Summary view: All buses in table format
  - Grouped view: Hierarchical with logical bus breakdowns
  - Detailed view: Single bus focus
- [ ] Update `process_can_key()` to handle 'v' key
- [ ] Test switching between views

**Estimated Time:** 2 hours

### Phase 4: Interactive Features (Day 3)

#### Task 4.1: Implement Key Processing
- [ ] Write `process_can_key()`
  - Handle 'v'/'V': Toggle view mode
  - Handle 's'/'S': Take snapshot
  - Handle 'c'/'C': Clear snapshot
  - Handle 'r'/'R': Reset statistics (if API exists)
  - Handle '0'-'9': Select bus for detailed view
- [ ] Add key legend to help line

**Estimated Time:** 1.5 hours

#### Task 4.2: Implement Snapshot Feature
- [ ] Add snapshot storage to context
  - Save current statistics
  - Mark snapshot as taken
- [ ] Add snapshot comparison display
  - Show deltas from snapshot
  - Use +/- indicators
- [ ] Test snapshot functionality

**Estimated Time:** 1 hour

### Phase 5: Polish and Testing (Day 3-4)

#### Task 5.1: Add Helper Functions
- [ ] Implement `format_can_stats()`
  - Format frames per second
  - Format bytes per second with units (B/s, KB/s, MB/s)
  - Format percentages
- [ ] Implement `get_trend_indicator()`
  - Compare values
  - Return appropriate character
- [ ] Add utility functions as needed

**Estimated Time:** 1 hour

#### Task 5.2: Error Handling
- [ ] Add NULL pointer checks
  - Check cb structure
  - Check device_config_v12
  - Check logical_buses array
- [ ] Handle edge cases
  - No buses open
  - Server not running
  - No logical buses configured
- [ ] Add informative error messages

**Estimated Time:** 1 hour

#### Task 5.3: Documentation
- [ ] Add comprehensive Doxygen comments
  - File header with description
  - Function headers with parameters and return values
  - Structure documentation
  - Code comments for complex logic
- [ ] Update CLI help text
- [ ] Create user guide section

**Estimated Time:** 1.5 hours

#### Task 5.4: Code Review and Cleanup
- [ ] Run linter/formatter
  - Check code style consistency
  - Fix any warnings
- [ ] Review for memory leaks
- [ ] Check thread safety (monitor runs in CLI thread)
- [ ] Verify all error paths cleaned up

**Estimated Time:** 1 hour

### Phase 6: Integration Testing (Day 4)

#### Task 6.1: Unit Testing
- [ ] Test with only CAN 0 active
- [ ] Test with only CAN 1 active
- [ ] Test with only Ethernet active
- [ ] Test with all buses active
- [ ] Test with no buses active
- [ ] Test with PCAN format
- [ ] Test with APTERA format
- [ ] Test with multiple logical buses

**Estimated Time:** 2 hours

#### Task 6.2: System Testing
- [ ] Test monitor startup/shutdown
- [ ] Test view mode switching
- [ ] Test snapshot feature
- [ ] Test with high traffic loads
- [ ] Test with error conditions
- [ ] Verify no impact on CAN processing performance
- [ ] Test concurrent with other CLI commands

**Estimated Time:** 2 hours

#### Task 6.3: Performance Validation
- [ ] Measure CPU usage during monitoring
  - Target: < 1% additional overhead
- [ ] Measure memory usage
  - Target: < 100KB additional memory
- [ ] Verify refresh rate accuracy (1Hz)
- [ ] Test sustained operation (hours)

**Estimated Time:** 1 hour

---

## Testing Plan

### Unit Tests

1. **Initialization Tests**
   - Monitor initializes successfully
   - Context properly zeroed
   - Framework registration successful

2. **Display Function Tests**
   - Physical buses display correctly
   - Ethernet server display correct
   - Logical buses display correctly
   - Handle NULL pointers gracefully
   - Handle empty configurations

3. **Key Processing Tests**
   - View toggle works
   - Snapshot works
   - Invalid keys handled
   - Help displayed correctly

### Integration Tests

1. **CAN Bus Scenarios**
   - All buses active
   - Single bus active
   - No buses active
   - Buses starting/stopping during monitoring

2. **Format Tests**
   - PCAN format display
   - APTERA format display
   - No format configured

3. **Logical Bus Tests**
   - Multiple logical buses
   - Single logical bus
   - No logical buses
   - Mixed physical/logical

### System Tests

1. **Performance Tests**
   - Monitor during high CAN traffic
   - Monitor during low CAN traffic
   - Long-running monitor session (24 hours)
   - Multiple monitor start/stop cycles

2. **Stability Tests**
   - Monitor with network changes
   - Monitor with config reloads
   - Monitor with device disconnections

3. **Usability Tests**
   - Readable display layout
   - Responsive to key presses
   - Clear error messages
   - Helpful documentation

---

## Files to Modify/Create

### New Files

1. **iMatrix/cli/cli_can_monitor.h**
   - Monitor API declarations
   - Structure definitions
   - ~150 lines

2. **iMatrix/cli/cli_can_monitor.c**
   - Monitor implementation
   - ~800-1000 lines

### Modified Files

1. **iMatrix/cli/cli.c**
   - Add CLI_CAN_MONITOR state to enum
   - Add canstats command to table
   - ~5 line changes

2. **iMatrix/CMakeLists.txt**
   - Add cli_can_monitor.c to sources
   - ~2 line changes

3. **iMatrix/cli/cli.h** (if needed)
   - Add state constant
   - Add function declarations
   - ~3 line changes

### Documentation Files

1. **docs/add_dynamic_can_monitor_plan.md** (this file)
   - Implementation plan

2. **docs/add_dynamic_can_monitor_implementation.md** (post-implementation)
   - Implementation summary
   - Metrics and outcomes
   - Lessons learned

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Statistics structures not populated correctly | Low | Medium | Verify stats update in existing code first |
| Logical bus array access issues | Medium | High | Add extensive NULL checks and bounds validation |
| Performance impact on CAN processing | Low | High | Profile before/after, ensure < 1% overhead |
| Terminal compatibility issues | Low | Medium | Test on multiple terminal types |
| Memory leaks in display code | Low | Medium | Use valgrind, thorough cleanup testing |

### Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Logical bus display more complex than expected | Medium | Medium | Allocate extra time, simplify if needed |
| Integration issues with cli_monitor | Low | Medium | Study existing memory monitor carefully |
| Testing reveals edge cases | Medium | Low | Build in buffer time for fixes |

### Quality Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Display formatting issues | Low | Low | Test with various data values |
| Missing error handling | Medium | Medium | Code review checklist, defensive programming |
| Incomplete documentation | Low | Medium | Document as you code, final review |

---

## Success Criteria

### Must Have
- [x] Monitor displays physical CAN 0 and CAN 1 statistics
- [x] Monitor displays Ethernet CAN server statistics
- [x] Monitor displays logical bus statistics (APTERA format)
- [x] 1-second refresh rate
- [x] Non-blocking operation
- [x] Quit with 'q' key
- [x] No crashes or memory leaks
- [x] Compiles without errors or warnings

### Should Have
- [x] View mode toggle (summary/grouped)
- [x] Snapshot feature
- [x] Trend indicators (up/down/stable)
- [x] Progress bars for buffer usage
- [x] Comprehensive error handling
- [x] Full Doxygen documentation

### Nice to Have
- [ ] Statistics reset feature (if API available)
- [ ] Detailed view of selected bus
- [ ] Save statistics to file
- [ ] Configurable refresh rate
- [ ] Color coding for warnings/errors

---

## Estimated Timeline

- **Phase 1 (Foundation)**: 2 hours
- **Phase 2 (Basic Implementation)**: 4.5 hours
- **Phase 3 (Logical Bus Support)**: 4 hours
- **Phase 4 (Interactive Features)**: 2.5 hours
- **Phase 5 (Polish and Testing)**: 4.5 hours
- **Phase 6 (Integration Testing)**: 5 hours

**Total Estimated Time**: 22.5 hours (~3 days)

**Actual Time Tracking**: (To be filled during implementation)
- Start: [DATE/TIME]
- Phase 1 Complete: [DATE/TIME]
- Phase 2 Complete: [DATE/TIME]
- Phase 3 Complete: [DATE/TIME]
- Phase 4 Complete: [DATE/TIME]
- Phase 5 Complete: [DATE/TIME]
- Phase 6 Complete: [DATE/TIME]
- End: [DATE/TIME]

---

## References

### Key Source Files
- `iMatrix/cli/cli_memory_monitor.c` - Reference implementation
- `iMatrix/cli/cli_monitor.h` - Generic monitor framework API
- `iMatrix/cli/cli_monitor.c` - Generic monitor framework implementation
- `iMatrix/canbus/can_structs.h` - CAN statistics structures
- `iMatrix/canbus/can_server.c` - CAN server with stats display
- `iMatrix/templates/blank.c` - C file template
- `iMatrix/templates/blank.h` - H file template

### Documentation
- `docs/comprehensive_code_review_report.md` - Architecture overview
- `docs/developer_onboarding_guide.md` - Development guidelines
- `docs/CLI_and_Debug_System_Complete_Guide.md` - CLI system documentation
- `CAN_DM/docs/CONFIG_V13_FORMAT_GUIDE.md` - Configuration format

### External References
- iMatrix Memory Manager documentation
- CAN bus DBC file specifications
- ANSI terminal control sequences

---

## Appendix A: Code Snippets

### Monitor Configuration Example

```c
/* Monitor configuration */
static cli_monitor_config_t can_monitor_config = {
    .title = "CAN Bus Monitor",
    .refresh_rate_ms = 1000,  /* 1 second refresh */
    .generate = generate_can_content,
    .process_key = process_can_key,
    .cleanup = cleanup_can_monitor,
    .context = &monitor_ctx,
    .width = 200,
    .height = 75,
    .show_help_line = true
};
```

### Statistics Access Example

```c
/* Access physical bus statistics */
extern canbus_product_t cb;

/* Physical CAN 0 */
can_stats_t *can0_stats = &cb.can0_stats;
uint32_t rx_frames = can0_stats->rx_frames;
uint32_t rx_fps = can0_stats->rx_frames_per_sec;

/* Ethernet CAN */
can_stats_t *eth_stats = &cb.can_eth_stats;
bool server_open = cb.cbs.can_bus_E_open;
ethernet_can_format_t format = cb.ethernet_can_format;

/* Logical buses (APTERA format only) */
extern config_v12_t *device_config_v12;
if (device_config_v12 != NULL && cb.ethernet_can_format == CAN_FORMAT_APTERA) {
    for (uint16_t i = 0; i < device_config_v12->num_logical_buses; i++) {
        logical_bus_config_t *lbus = &device_config_v12->logical_buses[i];
        if (lbus->physical_bus_id == CAN_BUS_ETH) {
            can_stats_t *stats = &lbus->stats;
            uint32_t rx = stats->rx_frames_per_sec;
            /* ... display stats ... */
        }
    }
}
```

---

## Appendix B: Detailed TODO List

### Pre-Implementation
- [x] Read all background documentation
- [x] Analyze memory monitor implementation
- [x] Understand CAN statistics structures
- [x] Understand CLI monitor framework
- [x] Create implementation plan
- [ ] Get user approval of plan

### Implementation Checklist

#### Foundation
- [ ] Create cli_can_monitor.h with proper header
- [ ] Create cli_can_monitor.c with proper header
- [ ] Add CLI_CAN_MONITOR state to cli.c enum
- [ ] Add canstats command to command table in cli.c
- [ ] Add cli_can_monitor.c to CMakeLists.txt
- [ ] Verify compilation with stubs

#### Core Implementation
- [ ] Implement cli_can_monitor_init()
- [ ] Implement generate_can_content() stub
- [ ] Implement display_physical_buses()
- [ ] Test physical bus display
- [ ] Implement display_ethernet_server()
- [ ] Test Ethernet server display
- [ ] Implement display_logical_buses()
- [ ] Test logical bus display

#### Interactive Features
- [ ] Implement process_can_key()
- [ ] Add view mode toggle ('v' key)
- [ ] Add snapshot feature ('s' key)
- [ ] Add snapshot clear ('c' key)
- [ ] Test all key handlers

#### Polish
- [ ] Add all helper functions
- [ ] Add comprehensive error handling
- [ ] Add NULL pointer checks everywhere
- [ ] Add Doxygen comments to all functions
- [ ] Add file and structure documentation
- [ ] Run linter and fix all issues
- [ ] Run build and fix all warnings

#### Testing
- [ ] Test with CAN 0 only
- [ ] Test with CAN 1 only
- [ ] Test with Ethernet only
- [ ] Test with all buses
- [ ] Test with no buses
- [ ] Test PCAN format
- [ ] Test APTERA format
- [ ] Test multiple logical buses
- [ ] Test view switching
- [ ] Test snapshot feature
- [ ] Run valgrind for memory leaks
- [ ] Measure CPU usage
- [ ] Measure memory usage
- [ ] Long-running stability test (1 hour+)

#### Documentation
- [ ] Update this plan with actual times
- [ ] Create implementation completion document
- [ ] Document any deviations from plan
- [ ] Document lessons learned
- [ ] Update CLI help documentation

#### Git Operations
- [ ] Commit changes with descriptive messages
- [ ] Test builds one final time
- [ ] Merge feature branch back to Aptera_1_Clean
- [ ] Tag release if appropriate

---

**End of Implementation Plan**
