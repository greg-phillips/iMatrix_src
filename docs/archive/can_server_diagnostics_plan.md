# CAN Server Diagnostics Implementation Plan

**Task**: Add "can server" command to display CAN Ethernet server status and diagnostics

**Date**: 2025-11-03
**Status**: Implementation Ready

---

## Background

The iMatrix CAN subsystem includes a TCP server that receives CAN messages over Ethernet (listening on 192.168.7.1:5555). This server supports multiple input formats (PCAN and APTERA) and processes frames from external sources. Currently, there is no dedicated CLI command to inspect the server's status, configuration, and statistics.

### Current State

- CAN server implementation: `iMatrix/canbus/can_server.c`
- Server state tracked in: `canbus_product_t cb` global structure
- CLI commands in: `iMatrix/cli/cli_canbus.c`
- Existing commands include: `can status`, `can extended`, `can nodes`, etc.

---

## Requirements

### Functional Requirements

1. **Display Server Status**
   - Server enabled/disabled state
   - Server running/stopped/down status
   - Listen address and port
   - Ethernet CAN bus open/closed state
   - Client connection status (if available)

2. **Display Format Configuration**
   - Parser type (PCAN or APTERA)
   - DBC files count (for APTERA format)
   - Virtual bus names and aliases (for APTERA format)

3. **Display Traffic Statistics**
   - TX/RX frames count
   - TX/RX bytes count
   - TX/RX error counts
   - No free messages count

4. **Display Timing Information**
   - Server uptime (if running)
   - Time since last restart/failure (if down)

### Non-Functional Requirements

1. Consistent CLI output format with existing commands
2. Minimal code changes - follow existing patterns
3. No impact on server performance
4. Comprehensive Doxygen documentation

---

## Data Sources

### Available from `canbus_product_t cb` Structure

| Data Field | Location | Description |
|------------|----------|-------------|
| `use_ethernet_server` | `cb.use_ethernet_server` | Server enabled flag |
| `can_bus_E_open` | `cb.cbs.can_bus_E_open` | Ethernet CAN bus open |
| `can_server_down` | `cb.cbs.can_server_down` | Server failure flag |
| `can_bus_server_stopped` | `cb.cbs.can_bus_server_stopped` | Server stopped flag |
| `can_server_down_time` | `cb.cbs.can_server_down_time` | Timestamp of last failure |
| `ethernet_can_format` | `cb.ethernet_can_format` | Format enum (PCAN/APTERA) |
| `dbc_files_count` | `cb.dbc_files_count` | Number of DBC files |
| `dbc_files` | `cb.dbc_files` | Array of DBC file configs |
| `can_eth_stats` | `cb.can_eth_stats` | Statistics structure |

### CAN Ethernet Statistics (`can_stats_t`)

```c
typedef struct can_stats_ {
    uint32_t tx_frames;      // Transmitted frames
    uint32_t rx_frames;      // Received frames
    uint32_t tx_bytes;       // Transmitted bytes
    uint32_t rx_bytes;       // Received bytes
    uint32_t tx_errors;      // Transmission errors
    uint32_t rx_errors;      // Reception errors
    uint32_t no_free_msgs;   // No free message buffers
} can_stats_t;
```

### Constants from `can_server.c`

```c
#define SERVER_IP "192.168.7.1"
#define SERVER_PORT 5555
```

---

## Design

### Command Syntax

```bash
can server
```

No arguments required - displays full server status.

### Example Output

```
=== CAN Ethernet Server Status ===

Server Configuration:
  Enabled:                 Yes
  Status:                  Running
  Listen Address:          192.168.7.1:5555
  Ethernet CAN Bus:        Open

Format Settings:
  Parser Type:             APTERA
  DBC Files Count:         3
  Virtual Buses:
    [0] Powertrain (PT)
    [1] Interior (IN)
    [2] Chassis (CH)

Traffic Statistics:
  RX Frames:               12,345
  TX Frames:               6,789
  RX Bytes:                98,765
  TX Bytes:                45,678
  RX Errors:               0
  TX Errors:               0
  No Free Messages:        0

Server Health:
  Uptime:                  2h 15m 30s

========================================
```

### Alternative Output (Server Disabled)

```
=== CAN Ethernet Server Status ===

Server Configuration:
  Enabled:                 No
  Status:                  Disabled
  Listen Address:          192.168.7.1:5555 (not listening)

Note: Use 'config set ethernet_server 1' to enable server
========================================
```

### Alternative Output (Server Down)

```
=== CAN Ethernet Server Status ===

Server Configuration:
  Enabled:                 Yes
  Status:                  Down (restarting)
  Listen Address:          192.168.7.1:5555

Server Health:
  Last Failure:            5 seconds ago
  Next Retry:              In 0 seconds

========================================
```

---

## Implementation Plan

### 1. Add Helper Function in `can_server.c`

Create a new function to display detailed server status:

```c
/**
 * @brief Display CAN Ethernet server status and diagnostics
 *
 * This function provides comprehensive diagnostics for the CAN Ethernet
 * server including configuration, statistics, and health information.
 *
 * @param[in] None
 * @return None
 */
void imx_display_can_server_status(void);
```

**Location**: `iMatrix/canbus/can_server.c` (after `stop_can_server()`)

**Implementation Details**:
- Access `cb` global variable (already extern'd)
- Use `imx_cli_print()` for output
- Format numbers with thousands separators for readability
- Calculate uptime from `can_server_down_time` if applicable
- Display format-specific details (PCAN vs APTERA)

### 2. Add Function Declaration in `can_server.h`

```c
void imx_display_can_server_status(void);
```

**Location**: `iMatrix/canbus/can_server.h` (in Function Declarations section)

### 3. Update CLI Command Handler in `cli_canbus.c`

Add new case in `cli_canbus()` function:

```c
else if (strncmp(token, "server", 6) == 0)
{
    /*
     * Display CAN Ethernet server status
     */
    imx_display_can_server_status();
}
```

**Location**: `iMatrix/cli/cli_canbus.c` (after line 583, before hm_sensors check)

### 4. Update Help Text

Update the help text in two locations in `cli_canbus()`:

1. After line 593 (error message):
```c
imx_cli_print("Invalid option, canbus <all> | <sim filename1 <filename2>> | <verify> | <status> | <extended> | <nodes [device] [node_id]> | <mapping> | <hm_sensors> | <server> | <send> | <send_file [device] file> | <send_file_sim [device] file> | <send_debug_file [device] file> | <send_test_file [device] file> | <send_file_stop>\r\n");
```

2. After line 649 (available subcommands list):
```c
imx_cli_print("  server            - Display CAN Ethernet server status\r\n");
```

---

## Implementation Steps

### Step 1: Implement `imx_display_can_server_status()`

**File**: `iMatrix/canbus/can_server.c`

```c
/**
 * @brief Display CAN Ethernet server status and diagnostics
 *
 * This function provides comprehensive diagnostics for the CAN Ethernet
 * server including configuration, statistics, and health information.
 *
 * Output includes:
 * - Server configuration (enabled, status, listen address)
 * - Format settings (parser type, DBC files for APTERA)
 * - Traffic statistics (frames, bytes, errors)
 * - Server health (uptime or downtime)
 *
 * @param[in] None
 * @return None
 *
 * @note Requires CAN_PLATFORM to be defined
 * @note Uses global canbus_product_t cb for status information
 */
void imx_display_can_server_status(void)
{
    imx_cli_print("\r\n=== CAN Ethernet Server Status ===\r\n\r\n");

    /* Server Configuration Section */
    imx_cli_print("Server Configuration:\r\n");
    imx_cli_print("  Enabled:                 %s\r\n",
                  cb.use_ethernet_server ? "Yes" : "No");

    /* Determine server status */
    const char *status_str;
    if (!cb.use_ethernet_server) {
        status_str = "Disabled";
    } else if (cb.cbs.can_server_down) {
        status_str = "Down (restarting)";
    } else if (cb.cbs.can_bus_server_stopped) {
        status_str = "Stopped";
    } else if (cb.cbs.can_bus_E_open) {
        status_str = "Running";
    } else {
        status_str = "Initializing";
    }

    imx_cli_print("  Status:                  %s\r\n", status_str);
    imx_cli_print("  Listen Address:          %s:%d", SERVER_IP, SERVER_PORT);

    if (!cb.use_ethernet_server) {
        imx_cli_print(" (not listening)");
    }
    imx_cli_print("\r\n");

    if (cb.use_ethernet_server) {
        imx_cli_print("  Ethernet CAN Bus:        %s\r\n",
                      cb.cbs.can_bus_E_open ? "Open" : "Closed");
    }

    /* Format Settings Section */
    if (cb.use_ethernet_server) {
        imx_cli_print("\r\nFormat Settings:\r\n");

        const char *format_str;
        switch (cb.ethernet_can_format) {
            case CAN_FORMAT_PCAN:
                format_str = "PCAN";
                break;
            case CAN_FORMAT_APTERA:
                format_str = "APTERA";
                break;
            default:
                format_str = "Unknown";
                break;
        }

        imx_cli_print("  Parser Type:             %s\r\n", format_str);

        /* For APTERA format, show DBC files and virtual buses */
        if (cb.ethernet_can_format == CAN_FORMAT_APTERA && cb.dbc_files_count > 0) {
            imx_cli_print("  DBC Files Count:         %u\r\n", cb.dbc_files_count);
            imx_cli_print("  Virtual Buses:\r\n");

            for (uint32_t i = 0; i < cb.dbc_files_count; i++) {
                imx_cli_print("    [%u] %s (%s)\r\n",
                              i,
                              cb.dbc_files[i].bus_name,
                              cb.dbc_files[i].alias);
            }
        }
    }

    /* Traffic Statistics Section */
    if (cb.use_ethernet_server) {
        imx_cli_print("\r\nTraffic Statistics:\r\n");
        imx_cli_print("  RX Frames:               %lu\r\n",
                      (unsigned long)cb.can_eth_stats.rx_frames);
        imx_cli_print("  TX Frames:               %lu\r\n",
                      (unsigned long)cb.can_eth_stats.tx_frames);
        imx_cli_print("  RX Bytes:                %lu\r\n",
                      (unsigned long)cb.can_eth_stats.rx_bytes);
        imx_cli_print("  TX Bytes:                %lu\r\n",
                      (unsigned long)cb.can_eth_stats.tx_bytes);
        imx_cli_print("  RX Errors:               %lu\r\n",
                      (unsigned long)cb.can_eth_stats.rx_errors);
        imx_cli_print("  TX Errors:               %lu\r\n",
                      (unsigned long)cb.can_eth_stats.tx_errors);
        imx_cli_print("  No Free Messages:        %lu\r\n",
                      (unsigned long)cb.can_eth_stats.no_free_msgs);
    }

    /* Server Health Section */
    if (cb.use_ethernet_server) {
        imx_cli_print("\r\nServer Health:\r\n");

        if (cb.cbs.can_server_down) {
            /* Calculate time since failure */
            imx_time_t current_time;
            imx_time_get_time(&current_time);
            imx_time_t down_duration = imx_time_difference(current_time,
                                                           cb.cbs.can_server_down_time);

            uint32_t seconds = down_duration / 1000;
            imx_cli_print("  Last Failure:            %u seconds ago\r\n", seconds);

            /* Calculate time until retry (5 second retry period from can_process.c) */
            const uint32_t RETRY_PERIOD = 5000; // milliseconds
            if (down_duration < RETRY_PERIOD) {
                uint32_t retry_in = (RETRY_PERIOD - down_duration) / 1000;
                imx_cli_print("  Next Retry:              In %u seconds\r\n", retry_in);
            } else {
                imx_cli_print("  Next Retry:              Retrying now\r\n");
            }
        } else if (cb.cbs.can_bus_E_open) {
            /* Server is running - could calculate uptime if we track start time */
            imx_cli_print("  Status:                  Healthy\r\n");
        }
    } else {
        imx_cli_print("\r\nNote: Use configuration to enable Ethernet CAN server\r\n");
    }

    imx_cli_print("\r\n========================================\r\n\r\n");
}
```

### Step 2: Update Header File

**File**: `iMatrix/canbus/can_server.h`

Add function declaration after `stop_can_server()`:

```c
bool start_can_server(void);
void stop_can_server(void);
void imx_display_can_server_status(void);  // ADD THIS LINE

#endif /* CAN_SERVER_H_ */
```

### Step 3: Update CLI Handler

**File**: `iMatrix/cli/cli_canbus.c`

**Location 1** - Add case handler (after line 591, before `else` block):

```c
        else if (strncmp(token, "hm_sensors", 10) == 0)
        {
            /*
             * Display HM Wrecker sensor configuration
             * Format: can hm_sensors
             */
            extern void display_hm_wrecker_sensor_config(void);
            display_hm_wrecker_sensor_config();
        }
        else if (strncmp(token, "server", 6) == 0)  // ADD THIS BLOCK
        {
            /*
             * Display CAN Ethernet server status and diagnostics
             * Format: can server
             */
            extern void imx_display_can_server_status(void);
            imx_display_can_server_status();
        }
        else
        {
```

**Location 2** - Update error message (line 594):

```c
            imx_cli_print("Invalid option, canbus <all> | <sim filename1 <filename2>> | <verify> | <status> | <extended> | <nodes [device] [node_id]> | <mapping> | <hm_sensors> | <server> | <send> | <send_file [device] file> | <send_file_sim [device] file> | <send_debug_file [device] file> | <send_test_file [device] file> | <send_file_stop>\r\n");
```

**Location 3** - Update help text (after line 643):

```c
        imx_cli_print("  mapping           - Display vehicle sensor mappings\r\n");
        imx_cli_print("  hm_sensors        - Display HM Wrecker sensor configuration\r\n");
        imx_cli_print("  server            - Display CAN Ethernet server status\r\n");  // ADD THIS LINE
        imx_cli_print("  send <dev> <id> <data> - Send CAN frame\r\n");
```

---

## Testing Plan

### Test Case 1: Server Disabled

**Setup**: Configure system with `use_ethernet_server = false`

**Command**: `can server`

**Expected Output**:
- Status shows "Disabled"
- Listen address shows "(not listening)"
- Minimal information displayed
- Note about enabling server

### Test Case 2: Server Running (PCAN Format)

**Setup**:
- Configure with PCAN format
- Start server successfully
- Send some test frames

**Command**: `can server`

**Expected Output**:
- Status shows "Running"
- Parser type shows "PCAN"
- Statistics show non-zero values
- Server health shows "Healthy"

### Test Case 3: Server Running (APTERA Format)

**Setup**:
- Configure with APTERA format
- Multiple DBC files configured
- Start server successfully

**Command**: `can server`

**Expected Output**:
- Status shows "Running"
- Parser type shows "APTERA"
- DBC files list displayed with virtual bus names
- Virtual buses shown with indices

### Test Case 4: Server Down (Restarting)

**Setup**:
- Trigger server failure
- Execute command during 5-second retry period

**Command**: `can server`

**Expected Output**:
- Status shows "Down (restarting)"
- Last failure time shown
- Next retry countdown shown

### Test Case 5: Server Stopped

**Setup**:
- Set `can_bus_server_stopped = true`

**Command**: `can server`

**Expected Output**:
- Status shows "Stopped"
- Appropriate diagnostic information

### Test Case 6: Integration with Existing Commands

**Commands**:
```bash
can          # Should show help including 'server' option
can status   # Existing command should still work
can extended # Existing command should still work
can server   # New command
```

**Expected**: All commands work without interference

---

## Files to Modify

1. `iMatrix/canbus/can_server.c` - Add `imx_display_can_server_status()` function
2. `iMatrix/canbus/can_server.h` - Add function declaration
3. `iMatrix/cli/cli_canbus.c` - Add command handler and update help text

## External Dependencies

### Required Headers (already included)
- `imatrix.h` - For `imx_cli_print()`, time functions
- `can_structs.h` - For `canbus_product_t`, enums
- `can_server.h` - For constants `SERVER_IP`, `SERVER_PORT`

### External Functions Used
- `imx_cli_print()` - CLI output
- `imx_time_get_time()` - Get current time
- `imx_time_difference()` - Calculate time delta

### External Variables
- `extern canbus_product_t cb;` - Already declared in can_server.c

---

## Backward Compatibility

- No breaking changes to existing commands
- No changes to configuration file format
- No changes to server behavior
- Purely additive feature

---

## Documentation Requirements

1. **Doxygen Comments**: Full function documentation in can_server.c
2. **Inline Comments**: Explain each section of output
3. **Code Comments**: Document status determination logic
4. **Help Text**: Clear description in CLI help

---

## Success Criteria

✓ Command `can server` displays comprehensive server diagnostics
✓ All server states are correctly identified and displayed
✓ PCAN and APTERA format details shown appropriately
✓ Statistics are formatted and displayed correctly
✓ No impact on existing commands or server performance
✓ Code follows existing patterns and style
✓ Full Doxygen documentation included
✓ All test cases pass

---

## Review Checklist

Before implementation:
- [ ] Review design with user
- [ ] Confirm output format meets requirements
- [ ] Verify all data sources are accessible
- [ ] Check for any missing functionality

During implementation:
- [ ] Follow existing code style
- [ ] Add comprehensive Doxygen comments
- [ ] Use existing helper functions where possible
- [ ] Maintain consistency with other CLI commands

After implementation:
- [ ] Test all scenarios (disabled, running, down, stopped)
- [ ] Verify both PCAN and APTERA formats
- [ ] Check help text updated in all locations
- [ ] Verify no impact on existing commands
- [ ] Review output formatting and alignment

---

**End of Implementation Plan**
