# Multiple udhcpd Instances Implementation Plan
**Version**: 1.0
**Date**: 2025-11-02
**Author**: Network Configuration Team
**Status**: Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Requirements and Constraints](#system-requirements-and-constraints)
3. [Architecture Overview](#architecture-overview)
4. [Pre-Implementation Checklist](#pre-implementation-checklist)
5. [Detailed Implementation Tasks](#detailed-implementation-tasks)
6. [Code Implementation Guide](#code-implementation-guide)
7. [Testing Plan](#testing-plan)
8. [Deployment Procedures](#deployment-procedures)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Appendix: Complete Code Examples](#appendix-complete-code-examples)

---

## Executive Summary

### Problem Statement
The BusyBox `udhcpd` DHCP server can only bind to **one network interface per process**. The current iMatrix implementation attempts to serve multiple interfaces (eth0, wlan0) but doesn't properly handle the BusyBox limitation, leading to potential DHCP service failures when multiple interfaces need DHCP server functionality.

### Solution Overview
Implement a multi-instance udhcpd architecture where:
- Each network interface runs its own independent udhcpd process
- Each instance has its own configuration file (`udhcpd.eth0.conf`, `udhcpd.wlan0.conf`)
- Each instance maintains separate lease and PID files
- Runit service management handles process lifecycle
- Graceful shutdown and cleanup procedures are implemented

### Expected Outcomes
- ✅ Independent DHCP services per interface
- ✅ Proper process management through runit
- ✅ Clean separation of configuration and state
- ✅ Robust error handling and recovery
- ✅ Backward compatibility with single-interface setups

---

## System Requirements and Constraints

### Environment
- **Platform**: Quake QConnect gateway running BusyBox Linux
- **Init System**: Runit service supervision
- **Service Directory**: `/usr/qk/etc/sv/udhcpd/`
- **Configuration Directory**: `/etc/network/`
- **Lease Directory**: `/var/lib/misc/`
- **PID Directory**: `/var/run/`

### Constraints
1. **BusyBox udhcpd**: One interface per process (hard limitation)
2. **Runit**: Requires foreground process for supervision
3. **File System**: Limited storage, must be efficient
4. **Memory**: Embedded system constraints
5. **Network Isolation**: Each subnet must be independent

### Dependencies
- BusyBox with udhcpd compiled
- Runit service manager
- Network interfaces properly configured with static IPs
- Write access to service directories

---

## Architecture Overview

### Current Architecture (Single Instance)
```
/etc/sv/udhcpd/run
    ↓
udhcpd process → single interface → single config file
```

### Proposed Architecture (Multiple Instances)
```
/etc/sv/udhcpd/run
    ├─→ udhcpd (eth0) → /etc/network/udhcpd.eth0.conf
    │                  → /var/lib/misc/udhcpd.eth0.leases
    │                  → /var/run/udhcpd.eth0.pid
    │
    └─→ udhcpd (wlan0) → /etc/network/udhcpd.wlan0.conf
                       → /var/lib/misc/udhcpd.wlan0.leases
                       → /var/run/udhcpd.wlan0.pid
```

### Process Management Strategy
- **Single Interface Mode**: Direct exec of udhcpd (runit supervised)
- **Dual Interface Mode**:
  - eth0 runs in background with PID tracking
  - wlan0 runs in foreground (runit supervised)
  - Finish script ensures cleanup of both

---

## Pre-Implementation Checklist

### Developer Environment Setup
- [ ] Access to iMatrix source code repository
- [ ] Development environment with cross-compilation tools
- [ ] Test device or VM with BusyBox and runit
- [ ] Network interfaces (eth0, wlan0) available for testing

### Code Review Tasks
- [ ] Review current `generate_udhcpd_run_script()` implementation
- [ ] Understand current network configuration flow
- [ ] Review device_config structure and interface storage
- [ ] Examine existing DHCP configuration generation
- [ ] Check current service management integration

### Documentation Review
- [ ] Read BusyBox udhcpd documentation
- [ ] Review runit service management documentation
- [ ] Understand network configuration state machine
- [ ] Review binary configuration file format

---

## Detailed Implementation Tasks

### Phase 1: Core Implementation (Priority: HIGH)

#### Task 1.1: Update generate_udhcpd_run_script() Function
**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`

**Developer TODO List**:
- [ ] Locate the `generate_udhcpd_run_script()` function (line ~549)
- [ ] Review current implementation for single/dual interface handling
- [ ] Identify the section handling both interfaces (line ~649-700)
- [ ] Update dual-interface logic to run separate processes
- [ ] Implement proper shell function for background process management
- [ ] Add PID file tracking for eth0 background process
- [ ] Ensure wlan0 runs in foreground for runit supervision
- [ ] Add error checking for IP address availability
- [ ] Test script generation with various configurations

**Code Changes Required**:
```c
// In the section handling both interfaces (after line 649):
// 1. Keep the helper function approach
// 2. Modify to run eth0 with explicit PID tracking
// 3. Use exec for wlan0 to maintain runit supervision
```

#### Task 1.2: Create Service Directory Generator
**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`

**Developer TODO List**:
- [ ] Add new function `generate_udhcpd_service_directory()`
- [ ] Create directory `/usr/qk/etc/sv/udhcpd` if not exists
- [ ] Generate run script with proper permissions (755)
- [ ] Generate finish script for cleanup
- [ ] Add symbolic link creation for service activation
- [ ] Implement atomic file operations for safety
- [ ] Add rollback capability on errors

**New Function Skeleton**:
```c
/**
 * @brief Generate complete runit service directory for udhcpd
 * @return 0 on success, negative on error
 */
int generate_udhcpd_service_directory(void)
{
    // TODO: Create directory structure
    // TODO: Generate run script
    // TODO: Generate finish script
    // TODO: Set permissions
    // TODO: Create symlinks
}
```

#### Task 1.3: Implement Finish Script Generator
**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.c`

**Developer TODO List**:
- [ ] Add function `generate_udhcpd_finish_script()`
- [ ] Script must kill background eth0 process using PID file
- [ ] Clean up PID files for both interfaces
- [ ] Optional: Archive lease files for debugging
- [ ] Ensure proper exit codes for runit
- [ ] Test cleanup in various failure scenarios

**Finish Script Template**:
```bash
#!/bin/sh
# Kill eth0 background process if running
[ -f /var/run/udhcpd.eth0.pid ] && kill $(cat /var/run/udhcpd.eth0.pid) 2>/dev/null
# Clean up PID files
rm -f /var/run/udhcpd.*.pid
# Exit cleanly
exit 0
```

### Phase 2: Integration (Priority: HIGH)

#### Task 2.1: Update Header Files
**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/dhcp_server_config.h`

**Developer TODO List**:
- [ ] Add declaration for `generate_udhcpd_service_directory()`
- [ ] Add declaration for `generate_udhcpd_finish_script()`
- [ ] Update any relevant documentation comments
- [ ] Ensure proper include guards

**Additions Required**:
```c
// Add after existing function declarations (around line 104)
int generate_udhcpd_service_directory(void);
int generate_udhcpd_finish_script(void);
```

#### Task 2.2: Integrate with Network Mode Configuration
**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_mode_config.c`

**Developer TODO List**:
- [ ] Locate where `generate_udhcpd_run_script()` is called (line ~380)
- [ ] Add call to `generate_udhcpd_service_directory()` before run script
- [ ] Ensure proper error handling and logging
- [ ] Test integration with network reconfiguration flow

**Integration Point**:
```c
// Around line 380, before generate_udhcpd_run_script()
if (generate_udhcpd_service_directory() != 0) {
    imx_printf("[NETWORK-MODE] Failed to create udhcpd service directory\n");
    // Handle error appropriately
}
```

#### Task 2.3: Update Network Auto Configuration
**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.c`

**Developer TODO List**:
- [ ] Locate `apply_network_configuration()` function
- [ ] Add service directory creation to configuration sequence
- [ ] Ensure service is properly registered with runit
- [ ] Add verification that service directory was created
- [ ] Test with network reconfiguration events

### Phase 3: Enhanced Run Script Implementation (Priority: MEDIUM)

#### Task 3.1: Implement Multi-Process Run Script Logic

**Detailed Implementation for Both Interfaces**:

**Developer TODO List**:
- [ ] Create shell function for DHCP process management
- [ ] Implement wait loops for interface availability
- [ ] Add IP address configuration from device_config
- [ ] Handle hostapd dependency for wlan0
- [ ] Implement proper backgrounding for eth0
- [ ] Use exec for wlan0 (foreground/runit)
- [ ] Add comprehensive logging

**Complete Run Script Structure**:
```bash
#!/bin/sh
exec 2>&1

export PATH=/usr/qk/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Function to run udhcpd for an interface
run_dhcp() {
    local iface=$1
    local ip=$2
    local conf=$3
    local lease=$4
    local pid=$5

    # Wait for interface
    while ! ifconfig $iface >/dev/null 2>&1; do
        echo "Waiting for $iface..."
        sleep 0.5
    done

    # Set IP address
    echo "Configuring $iface with IP $ip"
    ifconfig $iface $ip

    # Create lease file
    mkdir -p /var/lib/misc
    touch $lease

    # Start udhcpd with PID file
    echo "Starting udhcpd for $iface"
    udhcpd -f -p $pid $conf
}

# Check which interfaces need DHCP server
if [ -f /etc/network/udhcpd.eth0.conf ] && [ -f /etc/network/udhcpd.wlan0.conf ]; then
    # Both interfaces - run eth0 in background
    echo "Starting dual-interface DHCP server mode"

    # Start eth0 in background
    run_dhcp eth0 192.168.7.1 /etc/network/udhcpd.eth0.conf \
             /var/lib/misc/udhcpd.eth0.leases /var/run/udhcpd.eth0.pid &

    # Check for hostapd if wlan0 needs it
    if sv check hostapd >/dev/null 2>&1; then
        sv check hostapd >/dev/null || exit 1
    fi

    # Run wlan0 in foreground (for runit)
    exec run_dhcp wlan0 192.168.20.1 /etc/network/udhcpd.wlan0.conf \
                  /var/lib/misc/udhcpd.wlan0.leases /var/run/udhcpd.wlan0.pid

elif [ -f /etc/network/udhcpd.eth0.conf ]; then
    # Only eth0
    echo "Starting eth0 DHCP server"
    exec run_dhcp eth0 192.168.7.1 /etc/network/udhcpd.eth0.conf \
                  /var/lib/misc/udhcpd.eth0.leases /var/run/udhcpd.eth0.pid

elif [ -f /etc/network/udhcpd.wlan0.conf ]; then
    # Only wlan0
    echo "Starting wlan0 DHCP server"

    # Check hostapd dependency
    if sv check hostapd >/dev/null 2>&1; then
        sv check hostapd >/dev/null || exit 1
    fi

    exec run_dhcp wlan0 192.168.20.1 /etc/network/udhcpd.wlan0.conf \
                  /var/lib/misc/udhcpd.wlan0.leases /var/run/udhcpd.wlan0.pid
else
    echo "No DHCP server configuration found"
    exit 0
fi
```

### Phase 4: Testing Implementation (Priority: HIGH)

#### Task 4.1: Unit Testing

**Developer TODO List**:
- [ ] Test `generate_udhcpd_run_script()` with no interfaces
- [ ] Test with eth0 only configuration
- [ ] Test with wlan0 only configuration
- [ ] Test with both interfaces configured
- [ ] Test with missing IP addresses
- [ ] Test with invalid configurations
- [ ] Verify script syntax with `sh -n`
- [ ] Check file permissions are correct

**Test Scenarios**:
```bash
# Test 1: Verify script generation
./test_dhcp_config_generation

# Test 2: Syntax check
sh -n /etc/sv/udhcpd/run

# Test 3: Permissions check
ls -la /etc/sv/udhcpd/
```

#### Task 4.2: Integration Testing

**Developer TODO List**:
- [ ] Test complete network reconfiguration flow
- [ ] Verify DHCP configs are generated correctly
- [ ] Confirm run scripts are created properly
- [ ] Test service starts correctly with runit
- [ ] Verify both udhcpd processes run when needed
- [ ] Test DHCP client connections to each interface
- [ ] Verify lease files are created and updated
- [ ] Test configuration changes and service restart

**Integration Test Steps**:
```bash
# Step 1: Configure both interfaces for server mode
# Update binary config with both eth0 and wlan0 as servers

# Step 2: Trigger reconfiguration
./Fleet-Connect-1 -R

# Step 3: Verify services after reboot
sv status udhcpd
ps | grep udhcpd

# Step 4: Test DHCP clients
# Connect test devices to each interface
```

#### Task 4.3: Failure Mode Testing

**Developer TODO List**:
- [ ] Test with one interface down
- [ ] Test with hostapd not running (wlan0)
- [ ] Test with corrupted config files
- [ ] Test with full disk (can't create lease files)
- [ ] Test service restart after crash
- [ ] Test cleanup after abnormal termination
- [ ] Verify PID file cleanup
- [ ] Test rollback scenarios

### Phase 5: Documentation and Deployment (Priority: MEDIUM)

#### Task 5.1: Code Documentation

**Developer TODO List**:
- [ ] Add doxygen comments to all new functions
- [ ] Document the multi-instance architecture
- [ ] Add inline comments explaining process management
- [ ] Update README files with new behavior
- [ ] Document configuration file formats
- [ ] Add troubleshooting section

#### Task 5.2: User Documentation

**Developer TODO List**:
- [ ] Update operator manual with DHCP behavior
- [ ] Document configuration requirements
- [ ] Add network topology examples
- [ ] Create troubleshooting guide
- [ ] Document service management commands

#### Task 5.3: Deployment Preparation

**Developer TODO List**:
- [ ] Create deployment checklist
- [ ] Prepare rollback procedure
- [ ] Test on target hardware
- [ ] Verify backward compatibility
- [ ] Create migration script if needed
- [ ] Prepare release notes

---

## Code Implementation Guide

### Step-by-Step Function Updates

#### Step 1: Update generate_udhcpd_run_script()

**Location**: `dhcp_server_config.c`, line ~549-750

**Current Code Structure**:
```c
int generate_udhcpd_run_script(void)
{
    // ... initialization ...

    if (!eth0_server && !wlan0_server) {
        // No interfaces
    } else if (eth0_server && !wlan0_server) {
        // Only eth0
    } else if (!eth0_server && wlan0_server) {
        // Only wlan0
    } else {
        // Both interfaces - THIS NEEDS UPDATE
    }
}
```

**Required Changes**:
1. In the "both interfaces" section (starting ~line 649)
2. Keep the helper function approach
3. Modify to properly background eth0
4. Use exec for wlan0

**Updated Code for Both Interfaces Section**:
```c
} else {
    // Both interfaces configured - run as separate processes
    network_interfaces_t *eth0 = find_interface_config("eth0");
    network_interfaces_t *wlan0 = find_interface_config("wlan0");

    // Validate both IPs exist
    if (!eth0 || strlen(eth0->ip_address) == 0) {
        imx_printf("ERROR: eth0 DHCP server enabled but no IP address\n");
        fclose(fp);
        unlink(temp_script);
        return -1;
    }

    if (!wlan0 || strlen(wlan0->ip_address) == 0) {
        imx_printf("ERROR: wlan0 DHCP server enabled but no IP address\n");
        fclose(fp);
        unlink(temp_script);
        return -1;
    }

    // Write multi-instance script
    fprintf(fp, "echo \"Starting dual-interface DHCP server\"\n");
    fprintf(fp, "\n");
    fprintf(fp, "# Function to setup and run udhcpd\n");
    fprintf(fp, "run_dhcp() {\n");
    fprintf(fp, "    iface=$1\n");
    fprintf(fp, "    ip=$2\n");
    fprintf(fp, "    conf=$3\n");
    fprintf(fp, "    pidfile=$4\n");
    fprintf(fp, "    \n");
    fprintf(fp, "    # Wait for interface\n");
    fprintf(fp, "    while ! ifconfig $iface >/dev/null 2>&1; do\n");
    fprintf(fp, "        echo \"Waiting for $iface...\"\n");
    fprintf(fp, "        sleep 0.5\n");
    fprintf(fp, "    done\n");
    fprintf(fp, "    \n");
    fprintf(fp, "    # Configure IP\n");
    fprintf(fp, "    echo \"Setting $iface to $ip\"\n");
    fprintf(fp, "    ifconfig $iface $ip\n");
    fprintf(fp, "    \n");
    fprintf(fp, "    # Create lease file\n");
    fprintf(fp, "    touch /var/lib/misc/udhcpd.$iface.leases\n");
    fprintf(fp, "    \n");
    fprintf(fp, "    # Start udhcpd\n");
    fprintf(fp, "    echo \"Starting udhcpd for $iface\"\n");
    fprintf(fp, "    udhcpd -f -p $pidfile $conf\n");
    fprintf(fp, "}\n");
    fprintf(fp, "\n");
    fprintf(fp, "# Ensure directories exist\n");
    fprintf(fp, "mkdir -p /var/lib/misc /var/run\n");
    fprintf(fp, "\n");
    fprintf(fp, "# Start eth0 DHCP server in background\n");
    fprintf(fp, "echo \"Starting eth0 DHCP (IP: %s)\"\n", eth0->ip_address);
    fprintf(fp, "run_dhcp eth0 %s /etc/network/udhcpd.eth0.conf /var/run/udhcpd.eth0.pid &\n",
            eth0->ip_address);
    fprintf(fp, "ETH0_PID=$!\n");
    fprintf(fp, "echo $ETH0_PID > /var/run/udhcpd.eth0.launcher.pid\n");
    fprintf(fp, "\n");
    fprintf(fp, "# Check hostapd for wlan0 if needed\n");
    fprintf(fp, "if sv check hostapd >/dev/null 2>&1; then\n");
    fprintf(fp, "    sv check hostapd >/dev/null || exit 1\n");
    fprintf(fp, "fi\n");
    fprintf(fp, "\n");
    fprintf(fp, "# Start wlan0 DHCP server in foreground (for runit)\n");
    fprintf(fp, "echo \"Starting wlan0 DHCP (IP: %s)\"\n", wlan0->ip_address);
    fprintf(fp, "exec run_dhcp wlan0 %s /etc/network/udhcpd.wlan0.conf /var/run/udhcpd.wlan0.pid\n",
            wlan0->ip_address);
}
```

#### Step 2: Add Service Directory Generator

**New Function to Add**:
```c
/**
 * @brief Generate complete runit service directory for udhcpd
 *
 * Creates the /usr/qk/etc/sv/udhcpd directory structure with
 * run and finish scripts for proper service management.
 *
 * @return 0 on success, negative on error
 */
int generate_udhcpd_service_directory(void)
{
    const char *service_dir = "/usr/qk/etc/sv/udhcpd";
    const char *finish_script = "/usr/qk/etc/sv/udhcpd/finish";
    char cmd[256];
    int ret;

    imx_printf("[DHCP] Creating udhcpd service directory\n");

    // Create service directory
    snprintf(cmd, sizeof(cmd), "mkdir -p %s", service_dir);
    ret = system(cmd);
    if (ret != 0) {
        imx_printf("ERROR: Failed to create service directory %s\n", service_dir);
        return -1;
    }

    // Generate run script (calls existing function)
    ret = generate_udhcpd_run_script();
    if (ret != 0) {
        imx_printf("ERROR: Failed to generate run script\n");
        return -1;
    }

    // Generate finish script
    ret = generate_udhcpd_finish_script();
    if (ret != 0) {
        imx_printf("ERROR: Failed to generate finish script\n");
        return -1;
    }

    // Create supervise directory for runit
    snprintf(cmd, sizeof(cmd), "mkdir -p %s/supervise", service_dir);
    system(cmd);

    // Set ownership if needed
    snprintf(cmd, sizeof(cmd), "chown -R root:root %s 2>/dev/null", service_dir);
    system(cmd);

    imx_printf("[DHCP] Service directory created successfully\n");
    return 0;
}
```

#### Step 3: Add Finish Script Generator

**New Function to Add**:
```c
/**
 * @brief Generate finish script for graceful udhcpd shutdown
 *
 * Creates a finish script that properly cleans up all udhcpd
 * processes and their associated PID files.
 *
 * @return 0 on success, negative on error
 */
int generate_udhcpd_finish_script(void)
{
    FILE *fp;
    const char *finish_script = "/usr/qk/etc/sv/udhcpd/finish";
    const char *temp_script = "/usr/qk/etc/sv/udhcpd/finish.tmp";

    imx_printf("[DHCP] Generating udhcpd finish script\n");

    // Open temporary file
    fp = fopen(temp_script, "w");
    if (fp == NULL) {
        imx_printf("Error: Failed to open %s: %s\n", temp_script, strerror(errno));
        return -1;
    }

    // Write finish script
    fprintf(fp, "#!/bin/sh\n");
    fprintf(fp, "# Finish script for udhcpd service cleanup\n");
    fprintf(fp, "\n");
    fprintf(fp, "echo \"Stopping udhcpd services...\"\n");
    fprintf(fp, "\n");
    fprintf(fp, "# Kill eth0 background process if running\n");
    fprintf(fp, "if [ -f /var/run/udhcpd.eth0.pid ]; then\n");
    fprintf(fp, "    PID=$(cat /var/run/udhcpd.eth0.pid)\n");
    fprintf(fp, "    if kill -0 $PID 2>/dev/null; then\n");
    fprintf(fp, "        echo \"Stopping eth0 udhcpd (PID $PID)\"\n");
    fprintf(fp, "        kill $PID 2>/dev/null\n");
    fprintf(fp, "        sleep 1\n");
    fprintf(fp, "        # Force kill if still running\n");
    fprintf(fp, "        kill -0 $PID 2>/dev/null && kill -9 $PID 2>/dev/null\n");
    fprintf(fp, "    fi\n");
    fprintf(fp, "fi\n");
    fprintf(fp, "\n");
    fprintf(fp, "# Kill launcher PID if exists\n");
    fprintf(fp, "if [ -f /var/run/udhcpd.eth0.launcher.pid ]; then\n");
    fprintf(fp, "    PID=$(cat /var/run/udhcpd.eth0.launcher.pid)\n");
    fprintf(fp, "    kill $PID 2>/dev/null\n");
    fprintf(fp, "fi\n");
    fprintf(fp, "\n");
    fprintf(fp, "# Clean up all PID files\n");
    fprintf(fp, "rm -f /var/run/udhcpd.*.pid\n");
    fprintf(fp, "\n");
    fprintf(fp, "# Optional: Archive lease files for debugging\n");
    fprintf(fp, "# DATE=$(date +%%Y%%m%%d-%%H%%M%%S)\n");
    fprintf(fp, "# mkdir -p /var/log/dhcp\n");
    fprintf(fp, "# cp /var/lib/misc/udhcpd.*.leases /var/log/dhcp/ 2>/dev/null\n");
    fprintf(fp, "\n");
    fprintf(fp, "echo \"udhcpd services stopped\"\n");
    fprintf(fp, "exit 0\n");

    fclose(fp);

    // Set executable permissions
    if (chmod(temp_script, 0755) != 0) {
        imx_printf("Error: Failed to set permissions on %s: %s\n",
                   temp_script, strerror(errno));
        unlink(temp_script);
        return -1;
    }

    // Atomic rename
    if (rename(temp_script, finish_script) != 0) {
        imx_printf("Error: Failed to rename %s to %s: %s\n",
                   temp_script, finish_script, strerror(errno));
        unlink(temp_script);
        return -1;
    }

    imx_printf("[DHCP] Finish script created successfully\n");
    return 0;
}
```

---

## Testing Plan

### Test Case 1: Single Interface (eth0 only)

**Setup**:
```bash
# Configure eth0 as server, wlan0 as client
# Binary config: eth0=static/192.168.7.1, wlan0=dhcp_client
```

**Verification Steps**:
1. Check configuration files:
   ```bash
   ls -la /etc/network/udhcpd.*.conf
   # Should see only udhcpd.eth0.conf
   ```

2. Check run script:
   ```bash
   cat /usr/qk/etc/sv/udhcpd/run
   # Should show single interface mode for eth0
   ```

3. Start service and verify:
   ```bash
   sv start udhcpd
   ps | grep udhcpd
   # Should show one udhcpd process
   ```

4. Test DHCP client:
   ```bash
   # From another device on eth0 network
   udhcpc -i eth0 -n
   ```

### Test Case 2: Single Interface (wlan0 only)

**Setup**:
```bash
# Configure wlan0 as server, eth0 as client
# Binary config: wlan0=static/192.168.20.1, eth0=dhcp_client
```

**Verification Steps**:
1. Check configuration files:
   ```bash
   ls -la /etc/network/udhcpd.*.conf
   # Should see only udhcpd.wlan0.conf
   ```

2. Verify hostapd dependency:
   ```bash
   sv status hostapd
   # Should be running for AP mode
   ```

3. Start service and verify:
   ```bash
   sv start udhcpd
   ps | grep udhcpd
   # Should show one udhcpd process
   ```

### Test Case 3: Dual Interface Mode

**Setup**:
```bash
# Configure both as servers
# eth0=static/192.168.7.1, wlan0=static/192.168.20.1
```

**Verification Steps**:
1. Check both configuration files exist:
   ```bash
   ls -la /etc/network/udhcpd.*.conf
   # Should see both udhcpd.eth0.conf and udhcpd.wlan0.conf
   ```

2. Start service and verify processes:
   ```bash
   sv start udhcpd
   sleep 2
   ps | grep udhcpd
   # Should show TWO udhcpd processes
   ```

3. Check PID files:
   ```bash
   ls -la /var/run/udhcpd.*.pid
   # Should see both eth0 and wlan0 PID files
   ```

4. Test DHCP on both interfaces:
   ```bash
   # Test eth0 from one client
   # Test wlan0 from another client
   # Verify different IP ranges
   ```

### Test Case 4: Service Restart

**Steps**:
1. Start service:
   ```bash
   sv start udhcpd
   ```

2. Restart service:
   ```bash
   sv restart udhcpd
   ```

3. Verify cleanup and restart:
   ```bash
   # Check old PIDs are gone
   # Check new PIDs are created
   # Verify no orphan processes
   ```

### Test Case 5: Graceful Shutdown

**Steps**:
1. Start service with both interfaces
2. Stop service:
   ```bash
   sv stop udhcpd
   ```

3. Verify cleanup:
   ```bash
   ps | grep udhcpd
   # Should show NO udhcpd processes

   ls /var/run/udhcpd.*.pid
   # Should show no PID files
   ```

---

## Deployment Procedures

### Pre-Deployment Checklist

- [ ] Code review completed
- [ ] All unit tests passing
- [ ] Integration tests successful
- [ ] Documentation updated
- [ ] Rollback procedure prepared
- [ ] Target device prepared

### Deployment Steps

1. **Backup Current Configuration**
   ```bash
   # On target device
   tar -czf /tmp/network_backup_$(date +%Y%m%d).tar.gz \
       /etc/network/ \
       /usr/qk/etc/sv/udhcpd/ \
       /var/lib/misc/udhcpd.*
   ```

2. **Deploy New Code**
   ```bash
   # Copy updated binaries
   scp Fleet-Connect-1 root@device:/usr/bin/
   scp iMatrix root@device:/usr/lib/
   ```

3. **Trigger Configuration Update**
   ```bash
   # On device
   ./Fleet-Connect-1 -R
   # System will reboot
   ```

4. **Verify After Reboot**
   ```bash
   # Check service status
   sv status udhcpd

   # Verify processes
   ps | grep udhcpd

   # Check logs
   tail -f /var/log/messages
   ```

### Rollback Procedure

If issues occur:

1. **Stop Service**
   ```bash
   sv stop udhcpd
   ```

2. **Restore Backup**
   ```bash
   tar -xzf /tmp/network_backup_*.tar.gz -C /
   ```

3. **Restart Old Service**
   ```bash
   sv start udhcpd
   ```

4. **Revert Binary**
   ```bash
   # Restore old binaries from backup
   ```

---

## Troubleshooting Guide

### Problem: Only One DHCP Server Starts

**Symptoms**:
- `ps | grep udhcpd` shows only one process
- One interface not serving DHCP

**Debugging Steps**:
1. Check configuration files:
   ```bash
   ls -la /etc/network/udhcpd.*.conf
   ```

2. Check run script logic:
   ```bash
   cat /usr/qk/etc/sv/udhcpd/run
   ```

3. Check for errors in logs:
   ```bash
   tail -n 50 /var/log/messages | grep udhcpd
   ```

**Common Causes**:
- Missing configuration file for one interface
- Interface not in server mode
- IP address not configured in device_config

### Problem: DHCP Server Not Starting

**Symptoms**:
- No udhcpd processes running
- Service shows as down

**Debugging Steps**:
1. Check service status:
   ```bash
   sv status udhcpd
   ```

2. Try manual start:
   ```bash
   sh -x /usr/qk/etc/sv/udhcpd/run
   ```

3. Check interface status:
   ```bash
   ifconfig eth0
   ifconfig wlan0
   ```

**Common Causes**:
- Interface not up
- Hostapd not running (for wlan0)
- Script syntax error

### Problem: PID Files Not Cleaned

**Symptoms**:
- Stale PID files in /var/run/
- Service won't start due to existing PIDs

**Solution**:
```bash
# Manual cleanup
rm -f /var/run/udhcpd.*.pid
sv restart udhcpd
```

**Prevention**:
- Ensure finish script is properly executed
- Check finish script permissions (must be 755)

### Problem: Wrong IP Range Served

**Symptoms**:
- Clients getting unexpected IP addresses
- DHCP range mismatch

**Debugging**:
1. Check configuration:
   ```bash
   grep "start\|end" /etc/network/udhcpd.*.conf
   ```

2. Verify device_config values:
   ```bash
   ./Fleet-Connect-1 -P | grep -A5 "network"
   ```

**Solution**:
- Update binary configuration file
- Run `./Fleet-Connect-1 -R` to regenerate

---

## Appendix: Complete Code Examples

### A1: Complete Updated generate_udhcpd_run_script()

```c
int generate_udhcpd_run_script(void)
{
    FILE *fp;
    const char *run_script = "/usr/qk/etc/sv/udhcpd/run";
    const char *temp_script = "/usr/qk/etc/sv/udhcpd/run.tmp";
    bool eth0_server = false;
    bool wlan0_server = false;
    struct stat st;

    imx_printf("[DHCP] Generating udhcpd run script\n");

    // Check if service directory exists
    if (stat("/usr/qk/etc/sv/udhcpd", &st) != 0) {
        imx_printf("[DHCP] Service directory does not exist, creating it\n");
        if (system("mkdir -p /usr/qk/etc/sv/udhcpd") != 0) {
            imx_printf("ERROR: Failed to create service directory\n");
            return -1;
        }
    }

    // Check which interfaces have DHCP configs
    eth0_server = is_dhcp_server_enabled("eth0");
    wlan0_server = is_dhcp_server_enabled("wlan0");

    imx_printf("[DHCP] DHCP server status: eth0=%s, wlan0=%s\n",
               eth0_server ? "enabled" : "disabled",
               wlan0_server ? "enabled" : "disabled");

    // Open temporary file
    fp = fopen(temp_script, "w");
    if (fp == NULL) {
        imx_printf("Error: Failed to open %s: %s\n", temp_script, strerror(errno));
        return -1;
    }

    // Write script header
    fprintf(fp, "#!/bin/sh\n");
    fprintf(fp, "exec 2>&1\n");
    fprintf(fp, "\n");
    fprintf(fp, "export PATH=/usr/qk/bin:/sbin:/bin:/usr/sbin:/usr/bin\n");
    fprintf(fp, "\n");

    if (!eth0_server && !wlan0_server) {
        // No interfaces configured
        fprintf(fp, "echo \"No interfaces configured for DHCP server\"\n");
        fprintf(fp, "exit 0\n");

    } else if (eth0_server && !wlan0_server) {
        // Only eth0 - single instance mode
        network_interfaces_t *eth0 = find_interface_config("eth0");

        if (!eth0 || strlen(eth0->ip_address) == 0) {
            imx_printf("ERROR: eth0 DHCP server enabled but no IP address\n");
            fclose(fp);
            unlink(temp_script);
            return -1;
        }

        fprintf(fp, "echo \"Starting udhcpd for eth0 only\"\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Wait for eth0\n");
        fprintf(fp, "while ! ifconfig eth0 >/dev/null 2>&1; do\n");
        fprintf(fp, "    sleep 0.5\n");
        fprintf(fp, "done\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Set IP from config: %s\n", eth0->ip_address);
        fprintf(fp, "ifconfig eth0 %s\n", eth0->ip_address);
        fprintf(fp, "\n");
        fprintf(fp, "# Create lease file\n");
        fprintf(fp, "mkdir -p /var/lib/misc\n");
        fprintf(fp, "touch /var/lib/misc/udhcpd.eth0.leases\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Run in foreground for runit\n");
        fprintf(fp, "exec udhcpd -f /etc/network/udhcpd.eth0.conf\n");

    } else if (!eth0_server && wlan0_server) {
        // Only wlan0 - single instance mode
        network_interfaces_t *wlan0 = find_interface_config("wlan0");

        if (!wlan0 || strlen(wlan0->ip_address) == 0) {
            imx_printf("ERROR: wlan0 DHCP server enabled but no IP address\n");
            fclose(fp);
            unlink(temp_script);
            return -1;
        }

        fprintf(fp, "echo \"Starting udhcpd for wlan0 only\"\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Check hostapd dependency\n");
        fprintf(fp, "if sv check hostapd >/dev/null 2>&1; then\n");
        fprintf(fp, "    sv check hostapd >/dev/null || exit 1\n");
        fprintf(fp, "fi\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Wait for wlan0\n");
        fprintf(fp, "while ! ifconfig wlan0 >/dev/null 2>&1; do\n");
        fprintf(fp, "    sleep 0.5\n");
        fprintf(fp, "done\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Set IP from config: %s\n", wlan0->ip_address);
        fprintf(fp, "ifconfig wlan0 %s\n", wlan0->ip_address);
        fprintf(fp, "\n");
        fprintf(fp, "# Create lease file\n");
        fprintf(fp, "mkdir -p /var/lib/misc\n");
        fprintf(fp, "touch /var/lib/misc/udhcpd.wlan0.leases\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Run in foreground for runit\n");
        fprintf(fp, "exec udhcpd -f /etc/network/udhcpd.wlan0.conf\n");

    } else {
        // Both interfaces - dual instance mode
        network_interfaces_t *eth0 = find_interface_config("eth0");
        network_interfaces_t *wlan0 = find_interface_config("wlan0");

        if (!eth0 || strlen(eth0->ip_address) == 0) {
            imx_printf("ERROR: eth0 DHCP server enabled but no IP address\n");
            fclose(fp);
            unlink(temp_script);
            return -1;
        }

        if (!wlan0 || strlen(wlan0->ip_address) == 0) {
            imx_printf("ERROR: wlan0 DHCP server enabled but no IP address\n");
            fclose(fp);
            unlink(temp_script);
            return -1;
        }

        fprintf(fp, "echo \"Starting dual-interface DHCP server\"\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Create required directories\n");
        fprintf(fp, "mkdir -p /var/lib/misc /var/run\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Function to setup and run udhcpd\n");
        fprintf(fp, "run_dhcp() {\n");
        fprintf(fp, "    local iface=$1\n");
        fprintf(fp, "    local ip=$2\n");
        fprintf(fp, "    local conf=$3\n");
        fprintf(fp, "    \n");
        fprintf(fp, "    # Wait for interface to be available\n");
        fprintf(fp, "    echo \"Waiting for $iface...\"\n");
        fprintf(fp, "    while ! ifconfig $iface >/dev/null 2>&1; do\n");
        fprintf(fp, "        sleep 0.5\n");
        fprintf(fp, "    done\n");
        fprintf(fp, "    \n");
        fprintf(fp, "    # Configure IP address\n");
        fprintf(fp, "    echo \"Configuring $iface with IP $ip\"\n");
        fprintf(fp, "    ifconfig $iface $ip\n");
        fprintf(fp, "    \n");
        fprintf(fp, "    # Create lease file\n");
        fprintf(fp, "    touch /var/lib/misc/udhcpd.$iface.leases\n");
        fprintf(fp, "    \n");
        fprintf(fp, "    # Start udhcpd for this interface\n");
        fprintf(fp, "    echo \"Starting udhcpd for $iface\"\n");
        fprintf(fp, "    udhcpd -f $conf\n");
        fprintf(fp, "}\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Start eth0 DHCP server in background\n");
        fprintf(fp, "echo \"Launching eth0 DHCP server (IP: %s)\"\n", eth0->ip_address);
        fprintf(fp, "run_dhcp eth0 %s /etc/network/udhcpd.eth0.conf &\n", eth0->ip_address);
        fprintf(fp, "ETH0_PID=$!\n");
        fprintf(fp, "echo \"eth0 DHCP server launched with PID $ETH0_PID\"\n");
        fprintf(fp, "# Save launcher PID for cleanup\n");
        fprintf(fp, "echo $ETH0_PID > /var/run/udhcpd.eth0.launcher.pid\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Check hostapd dependency for wlan0\n");
        fprintf(fp, "if sv check hostapd >/dev/null 2>&1; then\n");
        fprintf(fp, "    echo \"Waiting for hostapd...\"\n");
        fprintf(fp, "    sv check hostapd >/dev/null || exit 1\n");
        fprintf(fp, "fi\n");
        fprintf(fp, "\n");
        fprintf(fp, "# Start wlan0 DHCP server in foreground (for runit supervision)\n");
        fprintf(fp, "echo \"Starting wlan0 DHCP server (IP: %s)\"\n", wlan0->ip_address);
        fprintf(fp, "exec run_dhcp wlan0 %s /etc/network/udhcpd.wlan0.conf\n", wlan0->ip_address);
    }

    fclose(fp);

    // Set executable permissions
    if (chmod(temp_script, 0755) != 0) {
        imx_printf("Error: Failed to set permissions on %s: %s\n",
                   temp_script, strerror(errno));
        unlink(temp_script);
        return -1;
    }

    // Atomic rename
    if (rename(temp_script, run_script) != 0) {
        imx_printf("Error: Failed to rename %s to %s: %s\n",
                   temp_script, run_script, strerror(errno));
        unlink(temp_script);
        return -1;
    }

    imx_printf("[DHCP] Run script generated successfully\n");
    return 0;
}
```

### A2: Integration Example for network_mode_config.c

```c
// In apply_network_mode_configuration() or similar function
// Around line 380 where DHCP configuration is handled

// Generate DHCP server configurations if needed
if (any_interface_in_server_mode()) {
    imx_printf("[NETWORK-MODE] Generating DHCP server configuration\n");

    // Create service directory structure first
    if (generate_udhcpd_service_directory() != 0) {
        imx_printf("[NETWORK-MODE] WARNING: Failed to create service directory\n");
        // Continue anyway - may already exist
    }

    // Generate/update run script based on current config
    if (generate_udhcpd_run_script() != 0) {
        imx_printf("[NETWORK-MODE] ERROR: Failed to generate udhcpd run script\n");
        return -1;
    }

    imx_printf("[NETWORK-MODE] DHCP server configuration complete\n");
}
```

---

## Summary

This implementation plan provides a complete roadmap for implementing multiple independent udhcpd instances on the Quake QConnect gateway. The key aspects are:

1. **Architecture**: Each interface runs its own udhcpd process with separate config/lease/PID files
2. **Process Management**: Runit supervises the foreground process, background process tracked via PID
3. **Configuration**: Dynamic generation based on device_config with no hardcoded values
4. **Cleanup**: Proper finish script ensures all processes are terminated gracefully
5. **Testing**: Comprehensive test cases covering all configurations
6. **Deployment**: Safe deployment with rollback procedures

Following this plan step-by-step will result in a robust, production-ready implementation that properly handles the BusyBox udhcpd single-interface limitation while maintaining clean service management through runit.

---

**End of Implementation Plan**