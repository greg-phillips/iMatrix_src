# Add -R (Reset Network Configuration) Command Line Option - Implementation Plan

**Date**: 2025-11-02
**Status**: READY FOR REVIEW
**Purpose**: Force network configuration rewrite regardless of hash match

---

## Overview

Add a new `-R` command line option that forces the system to rewrite the network configuration files even if the MD5 hash indicates the configuration hasn't changed.

**Use Case**: When configuration files are manually deleted or corrupted, the hash check prevents them from being regenerated. The -R option bypasses the hash check.

---

## Current System Architecture

### Hash-Based Change Detection

**File**: `iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.c`

**Function**: `imx_apply_network_mode_from_config()` (lines 665-751)

**Current Flow**:
```
1. Calculate hash of current network config from device_config
   ↓
2. Read stored hash from /usr/qk/etc/sv/network_config.state
   ↓
3. Compare hashes:
   - If DIFFERENT → Apply configuration + Save hash + Reboot
   - If SAME → Skip configuration (no changes)
   ↓
4. Return 0 (no changes) or 1 (reboot pending)
```

**Key Code** (lines 703-746):
```c
// Calculate hash of current network configuration
calculate_network_config_hash(current_hash);

// Read stored hash from state file
if (read_stored_network_hash(stored_hash) != 0) {
    config_changed = true;  // First boot
} else {
    // Compare hashes
    config_changed = (strcmp(current_hash, stored_hash) != 0);
}

if (config_changed) {
    // Apply configuration
    int changes_applied = apply_network_configuration();
    // Schedule reboot
    schedule_network_reboot();
    return 1;
} else {
    imx_cli_log_printf(true, "Network configuration unchanged\n");
}
```

**Problem**: If config files deleted but hash matches, nothing happens!

---

## Proposed Solution

### Architecture

Add a **force reconfiguration flag** that bypasses the hash check.

```
Command Line:
   -R option → Set force flag → Call imx_apply_network_mode_from_config()
                                      ↓
                              Skip hash comparison
                                      ↓
                              Force apply configuration
                                      ↓
                              Save new hash
                                      ↓
                              Reboot system
```

### Components To Modify

1. **network_auto_config.h** - Add public function declaration
2. **network_auto_config.c** - Add force flag and logic
3. **imatrix_interface.c** - Add -R command line parsing

---

## Implementation Details

### Part 1: Add Force Flag (network_auto_config.c)

#### Step 1.1: Add Static Flag Variable

**Location**: After line 115 (Variable Definitions section)

```c
/******************************************************
 *               Variable Definitions
 ******************************************************/
extern IOT_Device_Config_t device_config;
extern iMatrix_Control_Block_t icb;

/** Force network reconfiguration flag (set by -R option) */
static bool g_force_network_reconfig = false;
```

#### Step 1.2: Add Public Function to Set Flag

**Location**: After validate_network_configuration() function (around line 640)

```c
/**
 * @brief Force network reconfiguration on next application
 *
 * Sets a flag that causes imx_apply_network_mode_from_config() to
 * bypass the hash check and force reapplication of network configuration.
 * Used by the -R command line option.
 *
 * @note Flag is automatically cleared after forcing reconfiguration
 * @note This will cause a system reboot to apply changes
 */
void imx_force_network_reconfig(void)
{
    g_force_network_reconfig = true;
    imx_cli_log_printf(true, "Network reconfiguration will be forced (bypassing hash check)\n");
}
```

#### Step 1.3: Modify Hash Comparison Logic

**Location**: Line 714 in imx_apply_network_mode_from_config()

**OLD CODE**:
```c
} else {
    imx_cli_log_printf(true, "Stored config hash: %s\n", stored_hash);
    // Compare hashes
    config_changed = (strcmp(current_hash, stored_hash) != 0);
}
```

**NEW CODE**:
```c
} else {
    imx_cli_log_printf(true, "Stored config hash: %s\n", stored_hash);

    // Check if forced reconfiguration requested
    if (g_force_network_reconfig) {
        imx_cli_log_printf(true, "FORCED reconfiguration requested (-R option)\n");
        imx_cli_log_printf(true, "Bypassing hash check and forcing configuration rewrite\n");
        config_changed = true;
        g_force_network_reconfig = false;  // Clear flag after use
    } else {
        // Normal operation: Compare hashes
        config_changed = (strcmp(current_hash, stored_hash) != 0);
    }
}
```

**Result**: When flag is set, hash comparison is skipped and config is forced to apply.

---

### Part 2: Add Function Declaration (network_auto_config.h)

**Location**: After line 111 (after imx_apply_network_mode_from_config declaration)

```c
int imx_apply_network_mode_from_config(void);

/**
 * @brief Force network reconfiguration regardless of hash
 *
 * Sets a flag that forces the next call to imx_apply_network_mode_from_config()
 * to bypass the hash check and reapply network configuration. Used by the
 * -R command line option to regenerate network configuration files even if
 * the configuration hasn't changed.
 *
 * @note Causes automatic system reboot to apply changes
 * @note Flag is automatically cleared after use
 */
void imx_force_network_reconfig(void);

bool imx_handle_network_reboot_pending(imx_time_t current_time);
```

---

### Part 3: Add -R Command Line Option (imatrix_interface.c)

**Location**: After the -I option handler (around line 450)

#### Step 3.1: Add -R Option Handler

```c
        else if (strcmp(argv[i], "-R") == 0) {
            /* Reset network configuration option */
            printf("=== Network Configuration Reset ===\n");
            printf("This option forces regeneration of network configuration files\n");
            printf("regardless of whether the configuration has changed.\n");
            printf("\n");

            /* Set force reconfiguration flag */
            extern void imx_force_network_reconfig(void);  /* From network_auto_config.c */
            imx_force_network_reconfig();

            printf("Network reconfiguration has been scheduled.\n");
            printf("The system will apply configuration and reboot automatically.\n");
            printf("\n");

            /* Continue normal startup - don't exit */
            /* The configuration will be applied when imx_apply_network_mode_from_config() is called */
        }
```

**Note**: Unlike -P, -S, -I which exit immediately, -R continues with normal startup so the network configuration function gets called.

#### Step 3.2: Update Usage Comments

**Location**: Lines 256-260 (command line options comment)

**OLD**:
```c
 * Command line options:
 *   -P : Print configuration file details (verbose) and exit
 *   -S : Print configuration file summary and exit
 *   -I : Display configuration file index (v4+ files) and exit
 */
```

**NEW**:
```c
 * Command line options:
 *   -P : Print configuration file details (verbose) and exit
 *   -S : Print configuration file summary and exit
 *   -I : Display configuration file index (v4+ files) and exit
 *   -R : Reset network configuration (force rewrite regardless of hash)
 */
```

---

## Expected Behavior

### Without -R Option (Normal)
```bash
$ ./Fleet-Connect-1

Output:
Checking network configuration...
Current config hash: a1b2c3d4e5f6...
Stored config hash: a1b2c3d4e5f6...
Network configuration unchanged      ← Skips reconfiguration
```

### With -R Option (Forced)
```bash
$ ./Fleet-Connect-1 -R

Output:
=== Network Configuration Reset ===
This option forces regeneration of network configuration files
regardless of whether the configuration has changed.

Network reconfiguration has been scheduled.
The system will apply configuration and reboot automatically.

[... normal boot sequence ...]

Checking network configuration...
FORCED reconfiguration requested (-R option)
Bypassing hash check and forcing configuration rewrite  ← Hash check bypassed!
Network configuration has changed                        ← Forced to "changed"

*******************************************************
*   APPLYING NETWORK CONFIGURATION CHANGES            *
*******************************************************

[... configuration applied ...]

======================================
NETWORK CONFIGURATION CHANGED
System will reboot in 5 seconds
======================================
```

---

## Files To Modify

### 1. `iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.h`
**Changes**:
- Add `void imx_force_network_reconfig(void);` declaration

**Lines**: ~1 new function declaration

### 2. `iMatrix/IMX_Platform/LINUX_Platform/networking/network_auto_config.c`
**Changes**:
- Add static flag `g_force_network_reconfig`
- Add `imx_force_network_reconfig()` function
- Modify hash comparison logic to check flag

**Lines**: ~25 new lines

### 3. `iMatrix/imatrix_interface.c`
**Changes**:
- Add -R option handler
- Update command line options comment

**Lines**: ~20 new lines

**Total**: ~46 lines added

---

## Safety Considerations

### 1. Flag Lifecycle
- **Set**: When -R option parsed (before network config applied)
- **Checked**: In imx_apply_network_mode_from_config()
- **Cleared**: Immediately after forcing config_changed = true
- **Result**: One-time use, no persistent state

### 2. Hash Still Saved
Even with -R, the hash is still saved after applying configuration:
```c
if (save_network_hash(current_hash) != 0) {
    imx_cli_log_printf(true, "Warning: Failed to save configuration hash\n");
}
```

This ensures the next boot without -R will be normal (no repeated forced reconfig).

### 3. Reboot Still Required
The -R option doesn't skip the reboot - it's still necessary for network changes to take effect.

### 4. Validation Still Applied
The validate_network_configuration() check still runs:
```c
if (!validate_network_configuration()) {
    imx_cli_log_printf(true, "Error: Invalid network configuration\n");
    return -1;
}
```

So invalid configurations are still rejected even with -R.

---

## Use Cases

### Use Case 1: Deleted Configuration Files
```bash
# Oops! Accidentally deleted network config
rm /etc/network/interfaces
rm /etc/network/udhcpd.eth0.conf

# Normal boot - hash matches, files NOT regenerated
./Fleet-Connect-1
# Network doesn't work!

# Force regeneration
./Fleet-Connect-1 -R
# Files regenerated! Network works after reboot.
```

### Use Case 2: Corrupted Configuration
```bash
# Config file got corrupted
echo "garbage" > /etc/network/interfaces

# Force clean regeneration
./Fleet-Connect-1 -R
```

### Use Case 3: Testing Configuration
```bash
# Developer wants to test config generation multiple times
./Fleet-Connect-1 -R
# Reboot
./Fleet-Connect-1 -R
# Reboot
# Each time regenerates files
```

---

## Testing Plan

### Test 1: Basic Functionality
1. Build code with -R option added
2. Run `./Fleet-Connect-1 -R`
3. Verify output shows "FORCED reconfiguration requested"
4. Verify configuration applied
5. Verify system reboots

### Test 2: Hash Saved After Force
1. Run `./Fleet-Connect-1 -R`
2. System reboots
3. Check `/usr/qk/etc/sv/network_config.state` contains current hash
4. Next boot WITHOUT -R should skip reconfiguration

### Test 3: Files Regenerated
1. Delete `/etc/network/interfaces`
2. Delete `/etc/network/udhcpd.eth0.conf`
3. Run `./Fleet-Connect-1 -R`
4. Verify files regenerated with correct IPs
5. Verify system works after reboot

### Test 4: Invalid Config Rejected
1. Modify binary config to have invalid data
2. Run `./Fleet-Connect-1 -R`
3. Verify validation still catches errors
4. Verify config NOT applied

### Test 5: Multiple -R Calls
1. Run `./Fleet-Connect-1 -R`
2. Reboot
3. Run `./Fleet-Connect-1 -R` again
4. Verify works multiple times

---

## Code Review Checklist

- [ ] Flag is static (file scope, not global)
- [ ] Flag is cleared after use (prevents persistence)
- [ ] Function has proper Doxygen comments
- [ ] -R option has clear user messages
- [ ] Validation still applied with -R
- [ ] Hash still saved after forced application
- [ ] No memory leaks
- [ ] No race conditions
- [ ] Backwards compatible (old code still works)

---

## Alternative Approaches Considered

### Alternative 1: Delete Hash File
```bash
rm /usr/qk/etc/sv/network_config.state
./Fleet-Connect-1
```

**Pros**: No code changes needed
**Cons**: Requires root access, not user-friendly, hidden mechanism

### Alternative 2: Add --force-reconfig Long Option
```bash
./Fleet-Connect-1 --force-reconfig
```

**Pros**: More descriptive
**Cons**: Longer to type, breaks pattern with existing -P, -S, -I options

### Alternative 3: Command Line Flag with No Auto-Reboot
```bash
./Fleet-Connect-1 -R
# Regenerates files but doesn't reboot
# User manually reboots when ready
```

**Pros**: More control
**Cons**: Inconsistent with automatic reboot behavior

**Selected**: Original approach (Alternative 0) - matches existing patterns

---

## Risk Assessment

### Low Risk
✅ New code addition (not modifying existing logic)
✅ Flag is one-time use (cleared after use)
✅ Validation still applied
✅ Hash still saved (next boot is normal)
✅ Backwards compatible (no -R = normal behavior)

### Medium Risk
⚠️ Could be misused (running -R repeatedly)
   - Mitigation: Still respects reboot loop protection
   - After 3 reboots, fallback to defaults kicks in

⚠️ User might expect instant effect
   - Mitigation: Clear message about reboot requirement

### No High Risk
✅ No security implications
✅ No data loss risk
✅ No breaking changes

---

## Documentation Updates

### Update Command Line Help

If there's a help option or README:

```
-R    Force network configuration reset

      Forces regeneration of all network configuration files regardless
      of whether the configuration has changed. Use this option to recover
      from deleted or corrupted network configuration files.

      Note: System will automatically reboot to apply the changes.

      Example:
        ./Fleet-Connect-1 -R
```

---

## Implementation Checklist

### Phase 1: Add Infrastructure
- [ ] Add g_force_network_reconfig flag to network_auto_config.c
- [ ] Add imx_force_network_reconfig() function to network_auto_config.c
- [ ] Add function declaration to network_auto_config.h

### Phase 2: Modify Hash Logic
- [ ] Update imx_apply_network_mode_from_config() to check flag
- [ ] Add diagnostic messages for forced reconfiguration
- [ ] Clear flag after use

### Phase 3: Add Command Line Option
- [ ] Add -R option parsing in imatrix_interface.c main()
- [ ] Add user-friendly messages
- [ ] Update command line options comment

### Phase 4: Testing
- [ ] Build and verify compilation
- [ ] Test basic -R functionality
- [ ] Test with deleted files
- [ ] Test hash saved correctly
- [ ] Test next boot is normal
- [ ] Test multiple -R calls

### Phase 5: Documentation
- [ ] Update docs/add_dash_R_implementation_plan.md (this file)
- [ ] Add implementation notes
- [ ] Document any issues found

---

## Success Criteria

All must be true:

- [ ] Code compiles without errors or warnings
- [ ] -R option forces configuration rewrite
- [ ] Hash comparison bypassed when -R used
- [ ] Configuration files regenerated
- [ ] System reboots automatically
- [ ] Hash saved after forced application
- [ ] Next boot (without -R) is normal
- [ ] Validation still applied with -R
- [ ] Clear diagnostic messages shown
- [ ] No regressions in normal operation (without -R)

---

## Example Output

### Normal Boot (No Changes)
```
Checking network configuration...
Current config hash: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
Stored config hash: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
Network configuration unchanged
```

### With -R Option
```
=== Network Configuration Reset ===
This option forces regeneration of network configuration files
regardless of whether the configuration has changed.

Network reconfiguration has been scheduled.
The system will apply configuration and reboot automatically.

[... boot continues ...]

Checking network configuration...
Network reconfiguration will be forced (bypassing hash check)
Current config hash: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
Stored config hash: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
FORCED reconfiguration requested (-R option)
Bypassing hash check and forcing configuration rewrite
Network configuration has changed

*******************************************************
*   APPLYING NETWORK CONFIGURATION CHANGES            *
*******************************************************

[... applies configuration ...]

======================================
NETWORK CONFIGURATION CHANGED
System will reboot in 5 seconds
======================================
```

---

## Questions for Review

1. **Should -R also clear the reboot attempt counter?**
   - Currently: No - uses existing counter
   - Alternative: Clear counter on -R to allow multiple forced reboots
   - Recommendation: Keep current behavior (safer)

2. **Should -R delete the stored hash file?**
   - Currently: No - just bypasses comparison, hash is saved after
   - Alternative: Delete hash file to force "first boot" behavior
   - Recommendation: Keep current behavior (cleaner)

3. **Should -R work multiple times in a row?**
   - Currently: Yes - flag is set each time
   - Alternative: Limit to once per boot
   - Recommendation: Keep current behavior (useful for testing)

4. **Should there be a confirmation prompt?**
   - Currently: No - executes immediately
   - Alternative: Add "Are you sure?" prompt
   - Recommendation: No prompt (matches -P, -S, -I pattern)

---

## Summary

This is a **simple, low-risk addition** that provides a useful recovery mechanism when network configuration files are corrupted or deleted.

**Total Code**: ~46 lines
**Complexity**: Low
**Risk**: Low
**Utility**: High (debugging, recovery, testing)

**Ready for implementation?**

---

*End of Implementation Plan - Awaiting Review*
