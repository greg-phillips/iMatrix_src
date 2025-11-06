# Network Auto-Configuration - Developer Implementation Guide

## Welcome, Developer!

You've been assigned to implement automatic network configuration from the binary configuration file. This guide will walk you through everything you need to know to successfully implement this feature.

---

## Phase 1: Understanding the System (Day 1)

### Step 1.1: Read the Overview Documents (2 hours)

**Start here - read in this order:**

1. **Fleet-Connect-Overview.md** (30 min)
   - Location: `/docs/Fleet-Connect-Overview.md`
   - Focus on: Section 6 (Network Manager), Section 2 (Architecture)
   - Understand: How the network manager currently works

2. **CLAUDE.md** (30 min)
   - Location: `/CLAUDE.md`
   - Focus on: Repository structure, submodule relationships
   - Understand: How Fleet-Connect-1 and iMatrix interact

3. **network_auto_config_summary.md** (30 min)
   - Location: `/docs/network_auto_config_summary.md`
   - This is the executive summary of what you'll build
   - Pay attention to: Key features, implementation flow diagram

4. **network_auto_configuration_plan.md** (30 min)
   - Location: `/docs/network_auto_configuration_plan.md`
   - This is the detailed design document
   - Study: All 5 phases, integration points, risk mitigation

### Step 1.2: Understand Current Network Code (3 hours)

**Read these files to understand the current implementation:**

1. **imx_client_init.c** (45 min)
   - Location: `/Fleet-Connect-1/init/imx_client_init.c`
   - Focus on: How configuration is loaded (line 381-997)
   - Key function: `imx_client_init()`
   - **What to note**: Configuration is loaded but NOT applied to network

2. **process_network.c** (60 min)
   - Location: `/iMatrix/IMX_Platform/LINUX_Platform/networking/process_network.c`
   - Focus on: Lines 2046-2109 (`init_netmgr_context`)
   - Focus on: Lines 3753-3772 (`network_manager_init`)
   - **What to note**: Network manager uses opportunistic discovery, only reads timing/enable settings

3. **network_mode_config.c** (45 min)
   - Location: `/iMatrix/IMX_Platform/LINUX_Platform/networking/network_mode_config.c`
   - Focus on: Lines 247-370 (`network_mode_apply_staged`)
   - Focus on: Lines 391-425 (`imx_apply_network_mode_from_config`)
   - **What to note**: Currently only LOGS configuration, doesn't apply it

4. **network_interface_writer.c** (30 min)
   - Location: `/iMatrix/IMX_Platform/LINUX_Platform/networking/network_interface_writer.c`
   - Focus on: Lines 292-354 (`write_network_interfaces_file`)
   - Focus on: Lines 361-502 (`generate_hostapd_config`)
   - **What to note**: These functions actually write Linux config files

### Step 1.3: Trace the Boot Sequence (1 hour)

**Follow the code flow:**

1. **Start**: `iMatrix/imatrix_interface.c` - `main()` function (line 258)
2. **Next**: `imatrix_start()` (line 305)
3. **Next**: `imx_init()` (line 394)
4. **Next**: `imx_process()` - main loop (line 730)
5. **Key point**: Line 805 - `network_manager_init()`
6. **Key point**: Line 807 - `imx_apply_network_mode_from_config()`

**Draw this on paper or whiteboard:**
```
main() → imatrix_start() → imx_init() → imx_process()
                                           ↓
                                    [State Machine]
                                           ↓
                           MAIN_IMATRIX_SETUP (line 799)
                                           ↓
                              network_manager_init() (805)
                                           ↓
                    imx_apply_network_mode_from_config() (807)
```

---

## Phase 2: Setup Development Environment (Day 1 afternoon)

### Step 2.1: Build the Current Code

```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1
mkdir -p build
cd build
cmake ..
make
```

**If build fails**, check:
- All submodules initialized: `git submodule update --init --recursive`
- Dependencies installed: ncurses, cURL, cJSON, mbedtls

### Step 2.2: Test Current Behavior

```bash
# Run with -P option to see current config
./Fleet-Connect -P

# Look for network interface configuration in output
```

**Expected output**: Should print network interfaces but they won't be applied.

### Step 2.3: Create Feature Branch

```bash
cd /home/greg/iMatrix/iMatrix_Client
git checkout -b feature/network-auto-configuration
```

---

## Phase 3: Implementation (Days 2-5)

### Day 2: Configuration Hash and State Tracking

**File to create**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.c`

**Tasks:**
1. Copy implementation from `/docs/network_auto_config_implementation.c`
2. Implement these functions first:
   - `calculate_network_config_hash()` - Lines 60-98
   - `read_stored_network_hash()` - Lines 107-130
   - `save_network_hash()` - Lines 139-155

**Test approach:**
```bash
# Write a standalone test program
gcc -o hash_test hash_test.c -lssl -lcrypto

# Test hash calculation consistency
./hash_test config1.bin  # Note the hash
./hash_test config1.bin  # Should be same hash
./hash_test config2.bin  # Should be different hash
```

**Success criteria:**
- Hash is 32 hex characters
- Same config produces same hash
- Different config produces different hash

---

### Day 3: Configuration Application Logic

**Continue in**: `network_auto_config.c`

**Tasks:**
1. Implement `apply_network_configuration()` - Lines 242-290
2. Implement `apply_eth0_config()` - Lines 165-193
3. Implement `apply_wlan0_config()` - Lines 202-232
4. Implement `apply_ppp0_config()` - Lines 241-250

**Integration point:**
- These functions call existing functions from `network_interface_writer.c`
- Don't reinvent the wheel - reuse what exists

**Test approach:**
- Create test config with known values
- Call `apply_network_configuration()`
- Check if `/etc/network/interfaces` was created
- Verify contents match expected configuration

**Success criteria:**
- Config files generated correctly
- No crashes or errors
- All interface types handled

---

### Day 4: Reboot Management

**Continue in**: `network_auto_config.c`

**Tasks:**
1. Implement `schedule_network_reboot()` - Lines 295-315
2. Implement `is_network_reboot()` - Lines 324-334
3. Implement reboot counter functions - Lines 343-379
4. Implement `imx_handle_network_reboot_pending()` - Lines 569-601

**Modify**: `device/icb_def.h`
- Add fields to `iMatrix_Control_Block_t`:
```c
bool network_config_reboot;
imx_time_t network_reboot_time;
```

**Test approach:**
- Mock the reboot by setting flag but not actually rebooting
- Verify countdown logic
- Test reboot loop prevention

**Success criteria:**
- Countdown works correctly
- Reboot flag is set/cleared properly
- Counter prevents infinite loops

---

### Day 5: Main Integration

**Files to modify:**

1. **iMatrix/imatrix_interface.c** (lines 805-807):
```c
#ifdef LINUX_PLATFORM
    network_manager_init();

    // Apply network interface configuration from saved settings
    int network_config_result = imx_apply_network_mode_from_config();
    if (network_config_result > 0) {
        imx_cli_log_printf(true, "Network configuration will be applied after reboot\n");
        icb.state = MAIN_IMATRIX_NETWORK_REBOOT_PENDING;
        break;
    } else if (network_config_result < 0) {
        imx_cli_log_printf(true, "Warning: Failed to apply network configuration\n");
    }
#endif
```

2. **Add new state case** (around line 689):
```c
case MAIN_IMATRIX_NETWORK_REBOOT_PENDING:
    if (imx_handle_network_reboot_pending(current_time)) {
        processing_complete = false;
        uint32_t remaining = (icb.network_reboot_time - current_time) / 1000;
        imx_set_display(IMX_DISPLAY_REBOOT_COUNTDOWN, false);
    } else {
        icb.state = MAIN_IMATRIX_SETUP;
    }
    break;
```

3. **Update state enum** in `device/icb_def.h`:
```c
typedef enum {
    // ... existing states ...
    MAIN_IMATRIX_CHECK_TO_RESTART_WIFI,
    MAIN_IMATRIX_NETWORK_REBOOT_PENDING,  // ADD THIS
    MAIN_IMATRIX_POST_MFG_LOAD_1,
    // ...
} main_state_t;
```

4. **Update state names array** (line 1135):
```c
char *icb_states[MAIN_NO_STATES] = {
    // ... existing states ...
    "MAIN_IMATRIX_CHECK_TO_RESTART_WIFI",
    "MAIN_IMATRIX_NETWORK_REBOOT_PENDING",  // ADD THIS
    "MAIN_IMATRIX_POST_MFG_LOAD_1",
    // ...
};
```

5. **Update CMakeLists.txt**:
```cmake
# In iMatrix/IMX_Platform/LINUX_Platform/CMakeLists.txt
set(LINUX_PLATFORM_SOURCES
    # ... existing ...
    ${CMAKE_CURRENT_SOURCE_DIR}/networking/network_auto_config.c
)
```

**Test approach:**
- Full rebuild: `make clean && make`
- Run application with unchanged config → should NOT reboot
- Modify config hash file → should trigger reboot

---

## Phase 4: Testing (Days 6-7)

### Test Plan Execution

**Reference**: `/docs/network_auto_config_modifications.md` - Section 12

### Test 1: No Configuration Change
```bash
# Boot system
./Fleet-Connect

# Expected: No reboot, normal operation
# Check: Log should say "Network configuration unchanged"
```

### Test 2: Configuration Change - eth0 Static IP
```bash
# Modify config file: Change eth0 to static IP
# Boot system
./Fleet-Connect

# Expected:
# - "Network configuration has changed"
# - 5-second countdown
# - System reboots
# After reboot: eth0 has static IP
```

### Test 3: Configuration Change - WiFi AP Mode
```bash
# Modify config: Change wlan0 to server mode
# Boot system

# Expected:
# - hostapd config generated
# - DHCP server config generated
# - System reboots
# After reboot: wlan0 in AP mode
```

### Test 4: Reboot Loop Prevention
```bash
# Corrupt the config to cause repeated failures
# Boot 3 times

# Expected:
# - 1st boot: Tries to apply, reboots
# - 2nd boot: Tries to apply, reboots
# - 3rd boot: Tries to apply, reboots
# - 4th boot: Stops trying, logs error, uses defaults
```

### Test 5: CLI Override
```bash
# While system running, use CLI:
net eth0 static 192.168.1.50 255.255.255.0

# Expected: CLI commands still work independently
```

### Test 6: State File Corruption
```bash
# Corrupt the state file
echo "INVALID" > /usr/qk/etc/sv/network_config.state

# Boot system
# Expected: Treats as first boot, applies config
```

---

## Phase 5: Documentation and Review (Day 8)

### Code Documentation Checklist

- [ ] All functions have Doxygen comments
- [ ] Complex logic has inline comments
- [ ] Error conditions are documented
- [ ] Function parameters documented
- [ ] Return values documented

### User Documentation

Create or update:
1. **User Guide**: How network auto-config works from user perspective
2. **Admin Guide**: Troubleshooting network configuration issues
3. **CLI Reference**: Document any new commands

### Code Review Preparation

**Before submitting for review:**

1. **Run static analysis:**
```bash
cppcheck --enable=all network_auto_config.c
```

2. **Check for memory leaks:**
```bash
valgrind --leak-check=full ./Fleet-Connect
```

3. **Format code:**
- Use existing code style (K&R, 4-space indents)
- Follow patterns in surrounding code

4. **Create checklist:**
- [ ] All tests pass
- [ ] No compiler warnings
- [ ] No memory leaks
- [ ] Documentation complete
- [ ] Integration points tested

---

## Common Pitfalls to Avoid

### 1. State File Permissions
**Problem**: State file not readable after reboot
**Solution**: Use `chmod 0600` after creating state files

### 2. Hash Calculation Consistency
**Problem**: Same config produces different hashes
**Solution**: Ensure all fields are zeroed before hashing, use fixed order

### 3. Reboot During Development
**Problem**: System keeps rebooting during testing
**Solution**: Comment out actual reboot call, use flag for testing:
```c
#ifdef TESTING_MODE
    imx_cli_log_printf(true, "Would reboot now (testing mode)\n");
    return true;
#else
    imx_platform_reboot();
#endif
```

### 4. Configuration Validation
**Problem**: Invalid config causes crashes
**Solution**: Always validate before applying:
```c
if (!validate_network_configuration()) {
    return -1;
}
```

### 5. File Atomicity
**Problem**: Partial writes due to crash/power loss
**Solution**: Write to temp file, then rename:
```c
fwrite(temp_file, ...);
rename(temp_file, actual_file);
```

---

## Getting Help

### When Stuck:

1. **Read the code comments** in the implementation files
2. **Search for similar patterns** in existing code
3. **Check error logs** in `/var/log/` or console output
4. **Test incrementally** - don't try to implement everything at once

### Questions to Ask:

- "How does the current code handle this scenario?"
- "What happens if this file doesn't exist?"
- "What if this function is called during a reboot?"
- "How do I test this without a full system?"

### Debug Techniques:

1. **Add extensive logging:**
```c
imx_cli_log_printf(true, "[DEBUG] Hash: %s\n", hash);
imx_cli_log_printf(true, "[DEBUG] Config changed: %d\n", changed);
```

2. **Use breakpoints** (if debugging):
```bash
gdb ./Fleet-Connect
break imx_apply_network_mode_from_config
run
```

3. **Print state transitions:**
```c
imx_cli_log_printf(true, "State: %s -> %s\n",
    old_state_name, new_state_name);
```

---

## Success Criteria

### You're done when:

✅ All test cases pass
✅ No compiler warnings
✅ No memory leaks (valgrind clean)
✅ Documentation complete
✅ Code review approved
✅ Integration tests pass
✅ Performance acceptable (<1 second boot time impact)

### Acceptance Test:

```bash
# The ultimate test:
# 1. Configure network via config file
# 2. Boot system
# 3. Verify network automatically configured
# 4. Change config
# 5. Boot system
# 6. Verify network reconfigured automatically
# 7. Verify system stable after 10+ reboots
```

---

## Timeline Summary

| Day | Phase | Hours | Key Deliverable |
|-----|-------|-------|-----------------|
| 1 | Reading & Understanding | 6 | Knowledge of codebase |
| 1 | Environment Setup | 2 | Working build |
| 2 | Hash & State Tracking | 8 | Hash functions working |
| 3 | Config Application | 8 | Config files generated |
| 4 | Reboot Management | 8 | Reboot logic working |
| 5 | Integration | 8 | Full system integrated |
| 6 | Testing | 8 | All tests passing |
| 7 | Testing & Fixes | 8 | Edge cases handled |
| 8 | Documentation & Review | 8 | Production ready |

**Total: ~8 days of focused work**

---

## Final Notes

- **Take your time** understanding the current code before changing it
- **Test incrementally** - don't wait until everything is done
- **Ask questions early** - don't struggle alone for hours
- **Document as you go** - don't wait until the end
- **Commit frequently** - small, logical commits are easier to review

**Remember**: You're not just adding a feature, you're improving a production system used in real vehicles. Quality and reliability are paramount.

Good luck! 🚀

---

*Document Version: 1.0*
*Created: 2025-10-31*
*For questions, contact: Greg Phillips*