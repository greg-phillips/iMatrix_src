# Ping Command Implementation Plan

**Document Version:** 1.0
**Created:** 2025-11-15
**Author:** Claude Code
**Purpose:** Add a non-blocking ping command to the iMatrix CLI system

---

## Executive Summary

This document provides a detailed implementation plan for adding a new `ping` command to the iMatrix CLI. The command will accept either a Fully Qualified Domain Name (FQDN) or an IPv4 address as an argument and run in non-blocking mode, allowing the user to abort the operation with any keypress.

**Key Implementation Features:**
- Uses standard `ping` command via `popen()` (same pattern as `process_network.c`)
- Non-blocking pipe reads for responsive user interaction
- **Default: 4 ping attempts** (not continuous)
- **Coordination with process_network**: Mutual exclusion to prevent conflicts with network manager ping tests
- Helper functions manage exclusive access flag
- User can abort with any keypress
- Displays standard ping output format with statistics

---

## Current State

### Git Branches
- **iMatrix**: Currently on `Aptera_1_Clean`
- **Fleet-Connect-1**: Currently on `Aptera_1_Clean`

### CLI System Architecture
The iMatrix system has a well-established CLI framework located in `iMatrix/cli/`:
- **cli.c**: Main command dispatcher with command table
- **cli_monitor framework**: Generic framework for non-blocking, continuously updating commands
- **Reference implementation**: cli_can_monitor.c demonstrates the non-blocking pattern

### Template Files Available
- `iMatrix/templates/blank.h` - Header template with copyright and structure
- `iMatrix/templates/blank.c` - Implementation template with doxygen structure

---

## Requirements

### Functional Requirements

1. **Command Syntax**
   ```
   ping <destination>
   ```
   - `<destination>` can be either:
     - IPv4 address (e.g., 8.8.8.8)
     - FQDN (e.g., google.com)

2. **Output Format**
   ```
   PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
   64 bytes from 8.8.8.8: icmp_seq=1 ttl=113 time=20.3 ms
   64 bytes from 8.8.8.8: icmp_seq=2 ttl=113 time=18.4 ms
   <User Aborted>
   --- 8.8.8.8 ping statistics ---
   2 packets transmitted, 2 received, 0% packet loss, time 1080ms
   rtt min/avg/max/mdev = 18.373/19.345/20.317/0.972 ms
   ```

3. **Behavioral Requirements**
   - Non-blocking operation (continues to allow CLI interaction)
   - 2-second timeout for each ping request
   - User can abort with any keypress
   - Display starting message: "Ping: <destination> - use any key to abort"
   - Track sequence numbers
   - Display timeout message for missed replies: "sequence number X Ping Timeout"
   - Display statistics summary on exit

4. **Platform Support**
   - Linux platform only (LINUX_PLATFORM guard)
   - Uses raw ICMP sockets (requires root or CAP_NET_RAW capability)

### Non-Functional Requirements

1. **Code Quality**
   - Extensive doxygen comments for all functions
   - Follow existing code structure and conventions
   - Use KISS principle - simple and maintainable
   - Zero compilation errors or warnings
   - Thread-safe operation

2. **Integration**
   - Add to iMatrix CLI command table
   - Use existing CLI framework patterns
   - Minimal impact to existing code

---

## Technical Design

### Architecture Overview

The ping implementation will follow the proven CAN monitor pattern and reuse the existing ping approach from `process_network.c`:

```
User Types "ping 8.8.8.8"
        ↓
CLI Command Handler (cli_ping)
        ↓
Initialize Ping Context
   - Parse destination (IP or hostname)
   - Build ping command (similar to process_network.c)
   - Start ping process with popen()
   - Set pipe to non-blocking mode
        ↓
Set CLI State to PING_MONITOR
        ↓
Main Loop (called from CLI main loop)
   - Check pipe for ping output (non-blocking)
   - Parse and display ping replies as they arrive
   - Check for user keypress (abort on any key)
   - Track statistics from output
        ↓
User Presses Key or Ping Completes
        ↓
Parse final statistics from ping output
Display Statistics & Cleanup
```

### Implementation Approach

**Key Decision: Use Standard `ping` Command (Same as process_network.c)**

Following the existing pattern in `process_network.c`, we'll use the system `ping` utility via `popen()` rather than raw ICMP sockets. This approach:
- Avoids raw socket privileges requirement
- Reuses proven, tested code patterns
- Simpler implementation and maintenance
- Handles all ICMP protocol details automatically

**Implementation Details:**

1. **Coordination with process_network**
   - **CRITICAL**: `process_network` runs periodic ping tests that must not conflict with CLI ping
   - Use mutual exclusion flag to coordinate between CLI ping and process_network ping
   - Helper functions:
     - `cli_ping_request_exclusive_access()` - Wait for process_network ping to complete, then set flag
     - `cli_ping_release_exclusive_access()` - Clear flag to allow process_network to resume
     - `cli_ping_is_network_ping_active()` - Check if process_network is currently pinging
   - CLI ping waits (with timeout) for any active process_network ping to finish before starting
   - Process_network checks flag before running pings and skips if CLI ping is active

2. **Ping Process Management**
   - Execute ping command: `ping -c 4 -W 2 <destination> 2>&1`
   - **Default count: 4 ping attempts** (not continuous)
   - Use `popen()` to capture stdout/stderr
   - Set pipe to non-blocking mode with `fcntl()`
   - Track process completion

3. **State Management**
   - Track ping state (active/inactive)
   - Parse sequence numbers from output
   - Extract RTT values from reply lines
   - Accumulate statistics (sent/received/lost)
   - Parse final statistics line when available
   - Maintain exclusive access flag state

4. **Non-Blocking Operation**
   - Set pipe file descriptor to O_NONBLOCK
   - Use `select()` or `poll()` to check for available data
   - Read available data without blocking
   - Check for keyboard input without blocking
   - Continue main application processing

### File Structure

**New Files to Create:**

1. **iMatrix/cli/cli_ping.h**
   - Function declarations
   - Structure definitions for ping context
   - Constants (timeout values, buffer sizes, etc.)
   - Linux platform guards

2. **iMatrix/cli/cli_ping.c**
   - Main implementation
   - ICMP packet creation and parsing
   - Socket management
   - Statistics tracking
   - Display formatting

**Files to Modify:**

1. **iMatrix/cli/cli.c**
   - Add ping command to command table
   - Add CLI state for ping mode
   - Include cli_ping.h header
   - Add CLI_PING_MONITOR case to state machine

2. **iMatrix/cli/cli.h**
   - Add CLI_PING_MONITOR enum value to cli_states
   - Add forward declaration for `cli_ping_is_active()` (for process_network)

3. **iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c**
   - Add #include "cli/cli_ping.h"
   - Before executing ping tests, check `cli_ping_is_active()`
   - If CLI ping is active, skip network manager ping test for this cycle
   - Add comment explaining coordination

4. **iMatrix/CMakeLists.txt**
   - Add cli_ping.c to source file list (Linux platform only)

### Data Structures

```c
/**
 * @brief Ping statistics tracking (parsed from ping output)
 */
typedef struct {
    uint32_t packets_sent;      /**< Total packets transmitted */
    uint32_t packets_received;  /**< Total packets received */
    uint32_t packets_lost;      /**< Total packets lost */
    double rtt_min;             /**< Minimum round-trip time (ms) */
    double rtt_max;             /**< Maximum round-trip time (ms) */
    double rtt_avg;             /**< Average round-trip time (ms) */
    double rtt_mdev;            /**< Mean deviation of RTT (ms) */
    uint32_t start_time_ms;     /**< Start time in milliseconds */
    uint32_t total_time_ms;     /**< Total elapsed time (ms) */
} ping_statistics_t;

/**
 * @brief Ping context for maintaining state
 */
typedef struct {
    char destination[256];      /**< Target hostname or IP as entered by user */
    char resolved_ip[256];      /**< Resolved IP from ping output (if hostname used) */
    FILE *pipe;                 /**< Pipe to ping process */
    int pipe_fd;                /**< File descriptor for non-blocking reads */
    pid_t ping_pid;             /**< Process ID of ping command */
    bool active;                /**< Ping operation active flag */
    bool has_exclusive_access;  /**< Whether we have exclusive ping access */
    uint32_t start_time;        /**< Start timestamp (seconds) */
    bool header_displayed;      /**< Whether ping header has been shown */
    bool stats_parsed;          /**< Whether final statistics have been parsed */
    char line_buffer[512];      /**< Buffer for partial line assembly */
    size_t line_buffer_len;     /**< Current length of partial line */
    ping_statistics_t stats;    /**< Statistics tracking */
} ping_context_t;

/**
 * @brief Global coordination flag (shared with process_network)
 *
 * This flag coordinates ping operations between CLI and process_network:
 * - false: process_network can run pings normally
 * - true: CLI ping is active, process_network should skip pings
 */
static volatile bool g_cli_ping_exclusive_mode = false;
```

### Key Functions

**Coordination Helper Functions:**

1. **cli_ping_request_exclusive_access()**
   - Wait for any active process_network ping to complete (with timeout)
   - Poll `process_network_is_ping_active()` flag
   - Maximum wait time: 10 seconds
   - Once clear, set `g_cli_ping_exclusive_mode = true`
   - Return success if access granted, failure if timeout
   - Display status message if waiting

2. **cli_ping_release_exclusive_access()**
   - Clear `g_cli_ping_exclusive_mode = false`
   - Allow process_network to resume normal ping operations
   - Called in cleanup path (always, even on error)

3. **cli_ping_is_active()**
   - Public accessor function for process_network to check
   - Returns current value of `g_cli_ping_exclusive_mode`
   - process_network calls this before executing pings

**Core Ping Functions:**

4. **cli_ping(uint16_t arg)**
   - Entry point for ping command
   - Parse CLI arguments to extract destination
   - Validate destination (basic syntax check)
   - Request exclusive access (wait for process_network)
   - If access granted, initialize ping context
   - If access denied/timeout, display error and abort
   - Start ping process
   - Set CLI state to PING_MONITOR

5. **cli_ping_init(const char *destination)**
   - Requires exclusive access already granted
   - Build ping command string (similar to process_network.c)
   - Execute command: `ping -c 4 -W 2 <destination> 2>&1`
   - Open pipe with popen()
   - Get pipe file descriptor with fileno()
   - Set pipe to non-blocking mode with fcntl(O_NONBLOCK)
   - Initialize statistics structure
   - Display initial message: "Ping: <destination> - use any key to abort"
   - Return success/failure

6. **cli_ping_update(void)**
   - Called from main CLI loop when in PING state
   - Check pipe for available data using select()
   - Read available lines without blocking
   - Parse ping output lines:
     - Header line (PING ... bytes of data)
     - Reply lines (64 bytes from ...)
     - Timeout indicators
     - Statistics lines (packets transmitted, rtt min/avg/max/mdev)
   - Display parsed output to CLI
   - Track sequence numbers from output
   - Update statistics structure
   - Check if ping process completed (pipe EOF)
   - If complete: cleanup and return to normal CLI mode
   - Always release exclusive access when done

7. **cli_ping_process_char(char ch)**
   - Handle any character as abort signal
   - Kill ping process (SIGTERM)
   - Wait briefly for process to exit
   - Read any remaining output
   - Display "<User Aborted>" message
   - Display final statistics
   - Cleanup and exit ping mode (calls cli_ping_cleanup)

8. **cli_ping_cleanup(void)**
   - **CRITICAL**: Always call `cli_ping_release_exclusive_access()` first
   - Close pipe (pclose())
   - Ensure ping process is terminated
   - Free any allocated resources
   - Reset ping context
   - Return CLI to normal state
   - This function must be called in all exit paths (success, abort, error)

9. **cli_ping_parse_reply_line(const char *line)**
   - Extract sequence number from reply
   - Extract TTL value
   - Extract RTT time value
   - Update statistics (received count, RTT tracking)
   - Format and display reply line

10. **cli_ping_parse_statistics_line(const char *line)**
    - Parse "N packets transmitted, M received..."
    - Parse "rtt min/avg/max/mdev = ..."
    - Update statistics structure
    - Set stats_parsed flag

11. **cli_ping_display_final_statistics()**
    - Display "<User Aborted>" message if user initiated
    - Display statistics summary line
    - Display RTT statistics line
    - Format matches standard ping output

### Integration Points

**In cli.c:**
```c
// Add to command table
{"ping", &cli_ping, 0, "Ping host/IP - 'ping <destination>'"},

// Add to cli_process() state machine
case CLI_PING_MONITOR:
    cli_ping_update();
    break;
```

**In cli.h:**
```c
typedef enum {
    CLI_NORMAL,
    CLI_APP_MODE,
    // ... other states ...
    CLI_PING_MONITOR,
} cli_states_t;
```

---

## Implementation Todo List

### Phase 1: Setup and Structure ✓
- [x] Document current git branches
- [x] Review CLI architecture and patterns
- [x] Review CAN monitor implementation
- [x] Create implementation plan

### Phase 2: Branch Management
- [ ] Create new feature branch `feature/ping-command` from `Aptera_1_Clean` in iMatrix
- [ ] Verify branch creation

### Phase 3: Create Ping Implementation Files
- [ ] Create `iMatrix/cli/cli_ping.h` from blank.h template
  - [ ] Add copyright header
  - [ ] Add LINUX_PLATFORM guards
  - [ ] Define ping_context_t structure
  - [ ] Define ping_statistics_t structure
  - [ ] Declare global coordination flag extern
  - [ ] Add function declarations (including coordination helpers)
  - [ ] Add constants (timeout, packet size, ping count=4, etc.)

- [ ] Create `iMatrix/cli/cli_ping.c` from blank.c template
  - [ ] Add copyright header and doxygen file comment
  - [ ] Add required includes (stdio, signal, fcntl, etc.)
  - [ ] Define global coordination flag `g_cli_ping_exclusive_mode`
  - [ ] Implement cli_ping_request_exclusive_access() - coordination
  - [ ] Implement cli_ping_release_exclusive_access() - coordination
  - [ ] Implement cli_ping_is_active() - public accessor for process_network
  - [ ] Implement cli_ping() command entry point with coordination
  - [ ] Implement cli_ping_init() - popen ping with count=4
  - [ ] Implement cli_ping_update() - non-blocking pipe read and parse
  - [ ] Implement cli_ping_process_char() - user abort handler
  - [ ] Implement cli_ping_cleanup() - MUST release exclusive access
  - [ ] Implement cli_ping_parse_reply_line() - parse ping output
  - [ ] Implement cli_ping_parse_statistics_line() - parse final stats
  - [ ] Implement cli_ping_display_final_statistics() - format output
  - [ ] Implement set_pipe_nonblocking() helper
  - [ ] Add comprehensive error handling
  - [ ] Add extensive comments explaining coordination

### Phase 4: Integration
- [ ] Modify `iMatrix/cli/cli.h`
  - [ ] Add CLI_PING_MONITOR to cli_states_t enum
  - [ ] Add forward declaration: `bool cli_ping_is_active(void);`

- [ ] Modify `iMatrix/cli/cli.c`
  - [ ] Add #include "cli_ping.h" (with LINUX_PLATFORM guard)
  - [ ] Add ping command to command table: `{"ping", &cli_ping, 0, "Ping host/IP - 'ping <destination>'"}`
  - [ ] Add CLI_PING_MONITOR case to cli_process() state machine
  - [ ] Add CLI_PING_MONITOR case to character processing (call cli_ping_process_char)

- [ ] Modify `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
  - [ ] Add #include "cli/cli_ping.h" at top
  - [ ] Locate ping execution function (execute_ping or similar)
  - [ ] Add check before ping: `if (cli_ping_is_active()) { skip ping; return; }`
  - [ ] Add comment: "/* Skip ping if CLI ping command is active */"

- [ ] Modify `iMatrix/CMakeLists.txt`
  - [ ] Find LINUX_PLATFORM source list
  - [ ] Add cli/cli_ping.c to LINUX_PLATFORM sources

### Phase 5: Build and Test
- [ ] Build with CMake
- [ ] Fix any compilation errors
- [ ] Fix any compilation warnings
- [ ] Verify zero errors/warnings
- [ ] Test basic ping functionality (8.8.8.8)
- [ ] Test with hostname resolution (google.com)
- [ ] Test user abort functionality
- [ ] Test timeout handling
- [ ] Test statistics display
- [ ] Test edge cases (invalid host, network down, etc.)

### Phase 6: Documentation and Cleanup
- [ ] Review all code for comment completeness
- [ ] Verify doxygen comments on all functions
- [ ] Verify code follows KISS principle
- [ ] Add implementation summary to this document
- [ ] Record metrics (tokens, compile errors, time, etc.)

### Phase 7: Branch Merge
- [ ] Perform final clean build
- [ ] Commit all changes
- [ ] Merge feature/ping-command back to Aptera_1_Clean
- [ ] Verify merge successful
- [ ] Delete feature branch if appropriate

---

## Risk Assessment

### Low Risk
- ✓ Well-defined requirements
- ✓ Proven pattern to follow (CAN monitor and process_network.c)
- ✓ Isolated implementation (new files)
- ✓ Clear integration points
- ✓ No special privileges required (uses standard ping command)
- ✓ Existing code patterns to reuse from process_network.c

### Medium Risk
- ⚠ Process management (ping subprocess needs proper cleanup)
- ⚠ Non-blocking pipe read handling
- ⚠ Output parsing variations (BusyBox vs GNU ping)

### Mitigation Strategies
- Reuse proven patterns from process_network.c
- Implement comprehensive error handling
- Proper signal handling for subprocess termination
- Test with both BusyBox and GNU ping output formats
- Ensure pipe cleanup in all exit paths

---

## Testing Strategy

### Unit Testing
1. **Socket Creation**
   - Valid socket creation
   - Permission errors
   - Resource errors

2. **Hostname Resolution**
   - Valid IPv4 addresses
   - Valid hostnames
   - Invalid hostnames
   - DNS timeout

3. **ICMP Packet Handling**
   - Checksum calculation
   - Packet construction
   - Reply parsing
   - TTL extraction

4. **Statistics Tracking**
   - Packet counting
   - RTT calculation
   - Loss percentage
   - Standard deviation

### Integration Testing
1. **CLI Integration**
   - Command parsing
   - State transitions
   - User abort
   - Multiple invocations

2. **Real-World Scenarios**
   - Local gateway ping
   - Internet host (8.8.8.8)
   - Hostname resolution (google.com)
   - Unreachable host
   - Network interface down

---

## Acceptance Criteria

### Functional
- [ ] Command accepts both IP addresses and hostnames
- [ ] Non-blocking operation confirmed
- [ ] User can abort with any keypress
- [ ] 2-second timeout enforced
- [ ] Sequence numbers tracked correctly
- [ ] Output format matches specification
- [ ] Statistics calculated correctly

### Quality
- [ ] Zero compilation errors
- [ ] Zero compilation warnings
- [ ] All functions have doxygen comments
- [ ] Code follows existing patterns
- [ ] KISS principle applied
- [ ] No memory leaks (tested with valgrind)
- [ ] Thread-safe operation

### Integration
- [ ] Successfully added to command table
- [ ] CLI state management working
- [ ] No impact on other CLI commands
- [ ] Clean build on Linux platform
- [ ] Platform guards in place

---

## Questions for User - ANSWERED ✓

User responses received:

1. **Platform**: ✓ Linux-only implementation confirmed (LINUX_PLATFORM guard)
2. **Implementation Approach**: ✓ Use same functionality that existing ping in `~/iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c` does (i.e., use `popen()` with system ping command)
3. **Ping Rate**: ✓ 1 ping per second is acceptable (matches standard ping behavior)
4. **Packet Size**: ✓ Standard ping packet size acceptable (56 bytes data)

**Implementation Decision:**
Following the user's guidance, we'll use the same `popen()` + system `ping` command approach used in `process_network.c` rather than raw ICMP sockets. This simplifies the implementation significantly and reuses proven code patterns.

---

## Appendix: Reference Code Patterns

### Setting Pipe to Non-Blocking Mode
```c
/**
 * @brief Set pipe to non-blocking mode
 * @param[in] pipe FILE pointer from popen()
 * @return true if successful, false on error
 */
static bool set_pipe_nonblocking(FILE *pipe)
{
    int fd = fileno(pipe);
    if (fd < 0) {
        return false;
    }

    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) {
        return false;
    }

    if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
        return false;
    }

    return true;
}
```

### Non-Blocking Pipe Read
```c
/**
 * @brief Check for available data on pipe without blocking
 * @return true if data available, false if no data
 */
static bool check_pipe_data_available(void)
{
    fd_set read_fds;
    struct timeval tv = {0, 0};  // Don't wait at all

    FD_ZERO(&read_fds);
    FD_SET(ping_ctx.pipe_fd, &read_fds);

    int ret = select(ping_ctx.pipe_fd + 1, &read_fds, NULL, NULL, &tv);
    return (ret > 0);
}
```

### Parsing Ping Reply Line (from process_network.c pattern)
```c
/**
 * @brief Parse ping reply line for RTT
 * @param[in] line Output line from ping command
 * @return RTT in milliseconds, or -1.0 if not a reply line
 */
static double parse_ping_reply(const char *line)
{
    /* Look for: "64 bytes from 192.168.1.1: icmp_seq=1 time=1.234 ms" */
    if (strstr(line, "bytes from") && strstr(line, "time=")) {
        char *time_start = strstr(line, "time=");
        if (time_start) {
            time_start += 5; /* Skip "time=" */
            char *time_end = strstr(time_start, " ms");
            if (time_end) {
                char time_str[32];
                int len = time_end - time_start;
                if (len > 0 && len < sizeof(time_str)) {
                    strncpy(time_str, time_start, len);
                    time_str[len] = '\0';
                    return atof(time_str);
                }
            }
        }
    }
    return -1.0;
}
```

---

## Implementation Notes

*This section will be updated during implementation with important findings, decisions, and issues encountered.*

---

## Completion Summary

*This section will be filled upon completion with:*
- Total tokens used
- Number of recompilations required
- Time taken (elapsed and actual work time)
- Time waiting on user responses
- Summary of implementation
- Lessons learned
- Known issues or limitations

---

**Plan Status**: AWAITING USER APPROVAL
**Next Step**: User review and approval of plan

---
