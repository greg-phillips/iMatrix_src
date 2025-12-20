# CAN Server Idle Timeout Implementation Plan

**Date:** 2025-12-13
**Author:** Claude Code Analysis
**Branch:** debug/can_server_idle (created)
**Status:** Implementation Complete - Awaiting Testing

---

## Problem Statement

The CAN server (`iMatrix/canbus/can_server.c`) stops working after a period of time during testing. Investigation reveals that there is no idle timeout mechanism - if a client connects but stops sending data, the connection remains open indefinitely, potentially causing:
1. Resource exhaustion from stale connections
2. New clients unable to connect properly
3. CAN data processing stalls

## Root Cause Analysis

### Current Behavior (Lines 521-665 of can_server.c)

The `tcp_server_thread` uses `select()` with a 1-second timeout:
```c
struct timeval tv;
tv.tv_sec = 1;
tv.tv_usec = 0;

int sel = select(max_fd + 1, &read_fds, NULL, NULL, &tv);
if (sel == 0)
{
    /* Timeout - check shutdown, continue. */
    continue;  // <-- No idle check performed here!
}
```

When `select()` times out (no data received), the code simply continues the loop without checking how long the client has been idle. This means:
- A client can connect and then go silent indefinitely
- The connection `client_fd` remains open
- No logging of the idle condition occurs
- New clients may be dropped to keep the stale connection

### Missing Functionality

1. **No timestamp tracking** - Last data receive time is not recorded
2. **No idle timeout check** - No mechanism to detect and handle idle clients
3. **No logging** - No visibility into idle disconnection events

## Proposed Solution

### Design Overview

Add an idle timeout mechanism that:
1. Tracks the last time data was received from the connected client
2. Checks elapsed time since last data on each `select()` timeout
3. Closes the connection and logs when idle timeout (10 seconds default) is exceeded
4. Allows new clients to reconnect normally

### Implementation Details

#### 1. Add Idle Timeout Constant

**File:** `iMatrix/canbus/can_server.c`
**Location:** Constants section (line ~97)

```c
#define CAN_SERVER_IDLE_TIMEOUT_SEC 10  /**< Idle timeout in seconds before closing client connection */
```

#### 2. Add Last Activity Timestamp Variable

**File:** `iMatrix/canbus/can_server.c`
**Location:** Within `tcp_server_thread` function, after `client_fd` declaration

```c
imx_time_t last_client_activity = 0;  /**< Timestamp of last data received from client */
```

#### 3. Update Activity Timestamp on Data Received

**File:** `iMatrix/canbus/can_server.c`
**Location:** In the data receive block (around line 609-612)

When data is successfully received, update the activity timestamp:
```c
else
{
    /* We have r new bytes */
    buf_pos += r;
    rx_buf[buf_pos] = '\0';

    /* Update last activity timestamp */
    imx_time_get_time(&last_client_activity);

    // ... rest of parsing code
}
```

#### 4. Initialize Activity Timestamp on New Connection

**File:** `iMatrix/canbus/can_server.c`
**Location:** After accepting new client (around line 579-586)

```c
/* Accept the new client */
client_fd = new_fd;
strncpy(current_client_ip, new_ip, sizeof(current_client_ip) - 1);
current_client_ip[sizeof(current_client_ip) - 1] = '\0';

/* Initialize activity timestamp */
imx_time_get_time(&last_client_activity);

imx_cli_print("[CAN TCP New client connected from %s]\r\n", current_client_ip);
```

#### 5. Add Idle Timeout Check

**File:** `iMatrix/canbus/can_server.c`
**Location:** In the `select()` timeout handling (around line 551-555)

Replace the simple `continue` with idle timeout logic:

```c
else if (sel == 0)
{
    /* Timeout - check for idle client */
    if (client_fd != -1)
    {
        imx_time_t current_time;
        imx_time_get_time(&current_time);
        imx_time_t idle_duration = imx_time_difference(current_time, last_client_activity);

        /* Check if idle timeout exceeded (convert seconds to milliseconds) */
        if (idle_duration >= (CAN_SERVER_IDLE_TIMEOUT_SEC * 1000))
        {
            imx_cli_log_printf(true, "[CAN TCP Server] Client %s idle timeout (%u seconds) - closing connection\r\n",
                              current_client_ip, CAN_SERVER_IDLE_TIMEOUT_SEC);
            close(client_fd);
            client_fd = -1;
            buf_pos = 0;
            cb.cbs.can_bus_E_open = false;
        }
    }
    continue;
}
```

### Code Flow Summary

```
Client connects
    |
    v
Initialize last_client_activity timestamp
    |
    v
Enter select() loop
    |
    +---> select() returns > 0 (data available)
    |         |
    |         v
    |     Receive data, update last_client_activity
    |         |
    |         +---> Parse and process CAN frames
    |
    +---> select() returns 0 (timeout)
    |         |
    |         v
    |     Check if client connected AND idle > 10s
    |         |
    |         +---> Yes: Log and close connection
    |         |
    |         +---> No: Continue loop
    |
    +---> select() returns < 0 (error)
              |
              v
          Handle error
```

## Implementation Todo List

- [x] 1. Create new git branch `debug/can_server_idle` from `Aptera_1_Clean` for iMatrix
- [x] 2. Add `CAN_SERVER_IDLE_TIMEOUT_SEC` constant to can_server.c
- [x] 3. Add `last_client_activity` variable in tcp_server_thread
- [x] 4. Initialize activity timestamp when new client connects
- [x] 5. Update activity timestamp when data is received
- [x] 6. Add idle timeout check in select() timeout handler
- [x] 7. Run linter and fix any warnings
- [x] 8. Build and verify no compile errors or warnings
- [x] 9. Final clean build verification
- [x] 10. Document work completion

## Files to Modify

| File | Changes |
|------|---------|
| `iMatrix/canbus/can_server.c` | Add idle timeout constant, activity tracking, and timeout check |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Legitimate slow data sources disconnected | Low | Medium | 10 second timeout is conservative for CAN data rates |
| Regression in connection handling | Low | High | No changes to core connection/parsing logic |
| Memory leaks | Very Low | Medium | Only closing existing fd, no new allocations |

## Testing Recommendations

1. **Normal operation**: Verify CAN data flows with active client
2. **Idle timeout**: Connect client, stop sending, verify 10s disconnect with logging
3. **Reconnection**: After idle timeout, verify new client can connect
4. **Rapid connect/disconnect**: Verify no resource leaks
5. **Check logs**: Verify idle timeout logged with correct client IP

## Success Criteria

1. Idle clients are disconnected after 10 seconds of no data
2. Disconnection is logged with client IP address
3. New clients can connect after idle timeout
4. Normal CAN data flow is not affected
5. Zero compile errors or warnings
6. No regression in existing functionality

---

## Work Completion Summary

**Implementation Date:** 2025-12-13

### Changes Made

Added idle timeout mechanism to `iMatrix/canbus/can_server.c`:

1. **New constant** (line 98): `CAN_SERVER_IDLE_TIMEOUT_SEC = 10` - configurable idle timeout
2. **New variable** (line 485): `last_client_activity` - tracks last data receive timestamp
3. **Connection init** (line 586-587): Initialize activity timestamp when client connects
4. **Data receive update** (line 619): Update activity timestamp on each successful recv()
5. **Idle timeout check** (lines 553-574): On select() timeout, check idle duration and close if exceeded

### Code Diff Summary

```
+#define CAN_SERVER_IDLE_TIMEOUT_SEC 10

 static void *tcp_server_thread(void *arg)
 {
     ...
+    imx_time_t last_client_activity = 0;
     ...
     // On new connection:
+    imx_time_get_time(&last_client_activity);
     ...
     // On data receive:
+    imx_time_get_time(&last_client_activity);
     ...
     // On select timeout:
+    if (client_fd != -1) {
+        // Check idle duration and close if > 10 seconds
+        // Log: "[CAN TCP Server] Client %s idle timeout..."
+    }
```

### Build Verification

- **Clean build**: PASS
- **Warnings in can_server.c**: 0 (no new warnings introduced)
- **Binary generated**: FC-1 [100%]

### Statistics

**Recompilations for Syntax Errors:** 0
**Lines of Code Added:** ~20
**Files Modified:** 1 (iMatrix/canbus/can_server.c)

---

**Implementation By:** Claude Code
**Completed:** 2025-12-13
