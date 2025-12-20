# PPP Connection Refactoring Plan - KISS Version

**Document:** PPP Connection Refactoring Plan v3 (Simplified)
**Date:** November 19, 2025
**Objective:** Fix PPP connection by using correct startup script and adding basic visibility
**Principle:** KISS - Keep It Simple, Stupid

---

## Executive Summary

**Current Problem:** PPP connection fails because code uses `pon` command which needs missing `/etc/ppp/peers/provider` file.

**Simple Solution:** Use `/etc/start_pppd.sh` which exists on the system and add basic log monitoring.

**Scope:** Minimal changes to 2 files, estimated 2-3 hours total implementation time.

---

## Problem Analysis

### What's Breaking (from net3.txt logs)

```
Nov 15 23:55:21 iMatrix daemon.err pppd[1394]: Connect script failed
```

**Root Cause:**
1. Code calls `pon` command (line 1811 in cellular_man.c)
2. `pon` requires `/etc/ppp/peers/provider` configuration file (missing)
3. System has `/etc/start_pppd.sh` script (working) but code doesn't use it

### Current Code Problem

```c
// cellular_man.c line 1811
void start_pppd(void) {
    snprintf(cmd, sizeof(cmd), "pon");  // WRONG: needs missing config file
    system(cmd);
}
```

### Fix Required

```c
void start_pppd(void) {
    system("/etc/start_pppd.sh");  // RIGHT: use existing script
}
```

---

## Simple Implementation Plan

### Phase 1: Fix PPP Startup (30 minutes)

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

#### Change 1: Update start_pppd() function

```c
/**
 * @brief Start PPPD daemon using system startup script
 *
 * Uses /etc/start_pppd.sh which handles:
 * - Modem device verification
 * - Chat script execution
 * - PPPD daemon launch with proper options
 */
void start_pppd(void)
{
    char cmd[CMD_LENGTH + 1];

    // Check if pppd is already running
    if (system("pidof pppd >/dev/null 2>&1") == 0) {
        PRINTF("[Cellular Connection - PPPD already running, skipping start]\r\n");
        return;
    }

    // Check if start script exists
    if (access("/etc/start_pppd.sh", X_OK) != 0) {
        PRINTF("[Cellular Connection - ERROR: /etc/start_pppd.sh not found or not executable]\r\n");
        PRINTF("[Cellular Connection - PPP connection unavailable]\r\n");
        return;
    }

    // Start PPPD using system script (PPPD Daemon approach from QConnect Guide p.26)
    PRINTF("[Cellular Connection - Starting PPPD: /etc/start_pppd.sh]\r\n");
    int result = system("/etc/start_pppd.sh");

    if (result != 0) {
        PRINTF("[Cellular Connection - WARNING: start_pppd.sh returned %d]\r\n", result);
    }

    pppd_start_count++;
    PRINTF("[Cellular Connection - PPPD start initiated (count=%d)]\r\n", pppd_start_count);
}
```

#### Change 2: Update stop_pppd() function

```c
/**
 * @brief Stop PPPD daemon gracefully
 */
void stop_pppd(bool cellular_reset)
{
    char cmd[CMD_LENGTH + 1];

    // Check if pppd is running
    if (system("pidof pppd >/dev/null 2>&1") != 0) {
        PRINTF("[Cellular Connection - PPPD not running, skipping stop]\r\n");
        return;
    }

    // Stop gracefully with SIGTERM (allows ip-down script to run)
    PRINTF("[Cellular Connection - Stopping PPPD (cellular_reset=%s)]\r\n",
           cellular_reset ? "true" : "false");

    system("killall -TERM pppd 2>/dev/null");

    // Give it 2 seconds to exit gracefully
    sleep(2);

    // Force kill if still running
    if (system("pidof pppd >/dev/null 2>&1") == 0) {
        PRINTF("[Cellular Connection - PPPD did not exit gracefully, forcing kill]\r\n");
        system("killall -9 pppd 2>/dev/null");
    }

    // Clean up lock files
    system("rm -f /var/lock/LCK..ttyACM0 2>/dev/null");

    pppd_stop_count++;
    PRINTF("[Cellular Connection - PPPD stopped (count=%d)]\r\n", pppd_stop_count);
}
```

---

### Phase 2: Add Basic Status Visibility (1 hour)

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/cellular_man.c`

#### Add Simple Log Check Function

```c
/**
 * @brief Check PPP connection status from logs
 *
 * Provides basic visibility into connection state by checking
 * /var/log/pppd/current for key messages.
 *
 * @return Connection state string for logging
 */
static const char* get_ppp_status_string(void)
{
    static char status_buffer[256];
    FILE *fp;
    char line[256];
    bool has_connect = false;
    bool has_lcp = false;
    bool has_ipcp = false;
    bool has_ip = false;
    bool has_error = false;

    // Check if log file exists
    if (access("/var/log/pppd/current", R_OK) != 0) {
        return "NO_LOG_FILE";
    }

    // Read last 50 lines of log
    fp = popen("tail -n 50 /var/log/pppd/current 2>/dev/null", "r");
    if (fp == NULL) {
        return "LOG_READ_ERROR";
    }

    // Scan for key indicators
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "Connect script failed")) {
            has_error = true;
        } else if (strstr(line, "CONNECT")) {
            has_connect = true;
        } else if (strstr(line, "LCP ConfAck")) {
            has_lcp = true;
        } else if (strstr(line, "IPCP ConfAck")) {
            has_ipcp = true;
        } else if (strstr(line, "local  IP address")) {
            has_ip = true;
            // Extract IP if found
            char *ip_start = strstr(line, "address");
            if (ip_start) {
                ip_start += 8; // Skip "address "
                snprintf(status_buffer, sizeof(status_buffer),
                         "CONNECTED (IP: %s)", ip_start);
                // Remove newline
                char *newline = strchr(status_buffer, '\n');
                if (newline) *newline = ')';
                pclose(fp);
                return status_buffer;
            }
        }
    }

    pclose(fp);

    // Determine state based on what we found
    if (has_error) {
        return "ERROR (Connect script failed)";
    } else if (has_ip) {
        return "CONNECTED";
    } else if (has_ipcp) {
        return "IPCP_NEGOTIATION";
    } else if (has_lcp) {
        return "LCP_NEGOTIATION";
    } else if (has_connect) {
        return "CHAT_CONNECTED";
    }

    // Check if daemon is running
    if (system("pidof pppd >/dev/null 2>&1") == 0) {
        return "STARTING";
    }

    return "STOPPED";
}

/**
 * @brief Print PPP connection status (called by CLI or periodic check)
 */
void print_ppp_status(void)
{
    const char *status = get_ppp_status_string();

    PRINTF("\r\n+============ PPP STATUS ============+\r\n");
    PRINTF("| Daemon:  %s\r\n",
           (system("pidof pppd >/dev/null 2>&1") == 0) ? "RUNNING" : "STOPPED");
    PRINTF("| Device:  %s\r\n",
           (system("ifconfig ppp0 >/dev/null 2>&1") == 0) ? "ppp0 UP" : "ppp0 DOWN");
    PRINTF("| State:   %s\r\n", status);

    // Show IP if connected
    if (strstr(status, "CONNECTED")) {
        system("ifconfig ppp0 2>/dev/null | grep 'inet addr' | head -1");
    }

    PRINTF("+====================================+\r\n");
}
```

---

### Phase 3: Enhanced Monitoring in Network Manager (30 minutes)

**File:** `iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`

#### Update PPP Monitoring Section (lines 4646-4676)

```c
// Enhanced PPP0 monitoring with basic status visibility
if (ctx->cellular_started && !ctx->states[IFACE_PPP].active)
{
    unsigned long time_since_start = imx_time_difference(current_time, ctx->ppp_start_time);

    // Check if ppp0 has IP
    if (has_valid_ip_address("ppp0")) {
        NETMGR_LOG_PPP0(ctx, "PPP0 CONNECTED - Device has IP address");

        // Get IP details
        char ip_cmd[256];
        snprintf(ip_cmd, sizeof(ip_cmd),
                 "ifconfig ppp0 2>/dev/null | grep 'inet addr' | head -1");
        system(ip_cmd); // Prints IP info to log

        // Mark as active
        MUTEX_LOCK(ctx->states[IFACE_PPP].mutex);
        ctx->states[IFACE_PPP].active = true;
        MUTEX_UNLOCK(ctx->states[IFACE_PPP].mutex);
    }
    else {
        // Not connected yet - check status from cellular_man
        const char *ppp_status = get_ppp_status_string();

        // Log status periodically (every 5 seconds)
        if (time_since_start % 5000 < 1000) {
            NETMGR_LOG_PPP0(ctx, "PPP0 Status: %s (%lu ms elapsed)",
                           ppp_status, time_since_start);

            // Check for specific error conditions
            if (strstr(ppp_status, "ERROR")) {
                NETMGR_LOG_PPP0(ctx, "PPP0 connection failed - will retry");
                NETMGR_LOG_PPP0(ctx, "Check /var/log/pppd/current for details");
                ctx->cellular_started = false; // Allow retry
            }
        }

        // Timeout after 30 seconds
        if (time_since_start > 30000) {
            NETMGR_LOG_PPP0(ctx, "PPP0 connection timeout after %lu ms", time_since_start);
            NETMGR_LOG_PPP0(ctx, "Final status: %s", ppp_status);
            NETMGR_LOG_PPP0(ctx, "Resetting for retry");
            ctx->cellular_started = false;
        }
    }
}
```

---

### Phase 4: Add Simple CLI Command (30 minutes)

**File:** `iMatrix/cli/cli.c`

#### Add PPP Status Command

Add to command table:

```c
{ "ppp", do_ppp_status, "Show PPP connection status" },
```

Add handler function:

```c
/**
 * @brief CLI command to show PPP status
 */
static void do_ppp_status(int argc, char *argv[])
{
    (void)argc;
    (void)argv;

    // Call function from cellular_man
    print_ppp_status();

    // Show recent log entries if requested
    if (argc > 1 && strcmp(argv[1], "log") == 0) {
        PRINTF("\r\n==== Recent PPPD Log ====\r\n");
        system("tail -n 20 /var/log/pppd/current 2>/dev/null");
        PRINTF("========================\r\n");
    }
}
```

---

## Testing Plan

### 1. Basic Connectivity Test

```bash
# Start cellular and watch logs
tail -f /var/log/messages

# In CLI, check status
ppp
ppp log

# Verify IP assignment
ifconfig ppp0
```

### 2. Error Condition Test

```bash
# Test with modem unplugged
# Test with wrong APN
# Test with no cellular signal
```

### 3. Recovery Test

```bash
# Kill pppd manually and verify auto-recovery
killall pppd
# Watch network manager restart it
```

---

## Risk Analysis

### Low Risk Changes
- Using existing `/etc/start_pppd.sh` script that's already configured
- Adding read-only log parsing (no state changes)
- Keeping all existing retry logic intact

### What We're NOT Changing
- Not modifying core state machines
- Not changing network manager logic
- Not adding complex new modules
- Not modifying system configuration files

---

## Implementation Checklist

- [ ] Backup current cellular_man.c
- [ ] Update start_pppd() to use `/etc/start_pppd.sh`
- [ ] Update stop_pppd() for graceful shutdown
- [ ] Add get_ppp_status_string() function
- [ ] Add print_ppp_status() function
- [ ] Update process_network.c monitoring
- [ ] Add CLI command
- [ ] Test basic connectivity
- [ ] Test error conditions
- [ ] Document changes in commit

---

## Expected Outcomes

### Before Fix
```
[NETMGR-PPP0] PPP0 not ready (device=missing, pppd=running)
[NETMGR-PPP0] PPP0 connect script likely failing - no device after 34004 ms
```

### After Fix
```
[NETMGR-PPP0] PPP0 Status: CHAT_CONNECTED (5234 ms elapsed)
[NETMGR-PPP0] PPP0 Status: LCP_NEGOTIATION (7455 ms elapsed)
[NETMGR-PPP0] PPP0 Status: IPCP_NEGOTIATION (8932 ms elapsed)
[NETMGR-PPP0] PPP0 CONNECTED - Device has IP address
         inet addr:10.183.192.75  P-t-P:10.64.64.64  Mask:255.255.255.255
```

---

## Alternative Approach (If /etc/start_pppd.sh Missing)

If `/etc/start_pppd.sh` doesn't exist on target system:

```c
void start_pppd(void)
{
    // Direct pppd launch with required options
    const char *pppd_cmd = "pppd /dev/ttyACM0 115200 "
                          "connect '/usr/sbin/chat -v -f /etc/ppp/chat-script' "
                          "defaultroute usepeerdns noauth persist "
                          "logfile /var/log/pppd/current";

    system(pppd_cmd);
}
```

---

## Summary

**Total Implementation Time:** 2-3 hours

**Lines of Code Changed:** ~150 lines

**Files Modified:** 3 files
1. cellular_man.c - Fix startup and add status
2. process_network.c - Enhanced monitoring
3. cli.c - Add status command

**Testing Time:** 1 hour

This simplified approach:
- Fixes the root problem (wrong startup method)
- Adds basic visibility into connection state
- Maintains system simplicity
- Avoids over-engineering
- Can be enhanced later if needed

---

*End of Document*