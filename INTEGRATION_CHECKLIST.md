# Cellular Fixes Integration Checklist

**Date**: 2025-11-22
**Version**: 1.0
**Purpose**: Step-by-step integration guide for cellular fixes

---

## Pre-Integration Checklist

- [ ] **Backup current code**
  ```bash
  cd iMatrix
  git status
  git stash save "Before cellular fixes integration"
  ```

- [ ] **Verify current branch**
  ```bash
  git branch --show-current
  # Should be on appropriate development branch
  ```

- [ ] **Check build environment**
  ```bash
  which cmake
  which gcc
  cmake --version
  ```

---

## Step 1: Copy Implementation Files

### A. Core Implementation Files
- [ ] Copy blacklist management files
  ```bash
  cp cellular_blacklist.h iMatrix/networking/
  cp cellular_blacklist.c iMatrix/networking/
  ```

- [ ] Copy logging enhancement files
  ```bash
  cp cellular_carrier_logging.h iMatrix/networking/
  cp cellular_carrier_logging.c iMatrix/networking/
  ```

- [ ] Copy CLI command implementation
  ```bash
  cp cli_cellular_commands.c iMatrix/cli/
  ```

### B. Verify Files Copied
- [ ] Check all files are in place
  ```bash
  ls -la iMatrix/networking/cellular_blacklist.*
  ls -la iMatrix/networking/cellular_carrier_logging.*
  ls -la iMatrix/cli/cli_cellular_commands.c
  ```

---

## Step 2: Update Build Configuration

- [ ] **Add to CMakeLists.txt**
  ```bash
  cd iMatrix
  cp CMakeLists.txt CMakeLists.txt.backup
  ```

- [ ] **Edit CMakeLists.txt** and add:
  ```cmake
  # In the networking sources section
  set(NETWORKING_SOURCES
      # ... existing files ...
      networking/cellular_blacklist.c
      networking/cellular_carrier_logging.c
  )

  # In the CLI sources section
  set(CLI_SOURCES
      # ... existing files ...
      cli/cli_cellular_commands.c
  )
  ```

---

## Step 3: Apply Code Patches

### A. Backup Original Files
- [ ] Backup cellular_man.c
  ```bash
  cp iMatrix/networking/cellular_man.c iMatrix/networking/cellular_man.c.backup
  ```

- [ ] Backup process_network.c
  ```bash
  cp iMatrix/networking/process_network.c iMatrix/networking/process_network.c.backup
  ```

### B. Apply Patches
- [ ] Apply cellular_man.c patch
  ```bash
  cd iMatrix/networking
  patch -p0 < ../../cellular_blacklist_integration.patch
  ```
  - [ ] Verify no errors
  - [ ] Check for .rej files

- [ ] Apply process_network.c patch
  ```bash
  patch -p0 < ../../network_manager_integration.patch
  ```
  - [ ] Verify no errors
  - [ ] Check for .rej files

### C. Manual Integration (if patches fail)
If patches don't apply cleanly, manually add:

- [ ] **In cellular_man.c**:
  - [ ] Add includes at top:
    ```c
    #include "cellular_blacklist.h"
    #include "cellular_carrier_logging.h"
    ```
  - [ ] Add new states to enum
  - [ ] Add CELL_WAIT_PPP_INTERFACE state handler
  - [ ] Add blacklist clearing in CELL_SCAN_SEND_COPS
  - [ ] Replace logging with enhanced functions

- [ ] **In process_network.c**:
  - [ ] Add include:
    ```c
    #include "cellular_blacklist.h"
    ```
  - [ ] Add PPP failure tracking variables
  - [ ] Add coordination flags
  - [ ] Update NET_SELECT_INTERFACE for PPP handling

---

## Step 4: Update CLI Handler

- [ ] **Backup cli.c**
  ```bash
  cp iMatrix/cli/cli.c iMatrix/cli/cli.c.backup
  ```

- [ ] **Edit cli.c** and add:
  ```c
  // At top with other includes
  extern bool process_cellular_cli_command(const char* command, const char* args);

  // In main command processing function
  if (strncmp(input, "cell", 4) == 0) {
      return process_cellular_cli_command(input, args);
  }
  ```

---

## Step 5: Compile

- [ ] **Clean build directory**
  ```bash
  cd iMatrix
  rm -rf build
  mkdir build
  cd build
  ```

- [ ] **Configure with CMake**
  ```bash
  cmake ..
  ```
  - [ ] Check for configuration errors
  - [ ] Verify all source files found

- [ ] **Build**
  ```bash
  make -j4
  ```
  - [ ] Check for compilation errors
  - [ ] Check for linking errors
  - [ ] Verify executable created

---

## Step 6: Initial Testing

### A. Syntax Verification
- [ ] **Check new CLI commands**
  ```bash
  ./FC-1
  # At prompt:
  cell help
  ```
  - [ ] Should show new commands

### B. Basic Functionality
- [ ] **Test cell operators command**
  ```bash
  cell operators
  ```
  - [ ] Should show carrier table (even if empty)

- [ ] **Test cell blacklist command**
  ```bash
  cell blacklist
  ```
  - [ ] Should show blacklist (likely empty)

- [ ] **Test cell scan command**
  ```bash
  cell scan
  ```
  - [ ] Should trigger scan with enhanced logging

---

## Step 7: Functional Testing

### A. Test Scenarios
- [ ] **Scenario 1: Normal Scan**
  - [ ] Initiate scan
  - [ ] Verify detailed logging for each carrier
  - [ ] Check summary table appears
  - [ ] Verify carrier selection reasoning

- [ ] **Scenario 2: PPP Failure**
  - [ ] Simulate PPP failure (kill pppd)
  - [ ] Verify carrier gets blacklisted
  - [ ] Confirm automatic rescan triggers
  - [ ] Check next carrier selected

- [ ] **Scenario 3: Manual Blacklist**
  - [ ] Use `cell blacklist add 311480`
  - [ ] Run scan
  - [ ] Verify Verizon skipped
  - [ ] Use `cell clear`
  - [ ] Verify blacklist cleared

### B. Log Verification
- [ ] **Check for enhanced logging**
  ```bash
  tail -f /var/log/FC-1.log | grep "Cellular Scan"
  ```

  Should see:
  - [ ] Carrier details (name, MCCMNC, status)
  - [ ] Signal strength with RSSI in dBm
  - [ ] Signal quality assessment
  - [ ] Summary table
  - [ ] Selection reasoning

---

## Step 8: Performance Verification

- [ ] **Monitor memory usage**
  ```bash
  ps aux | grep FC-1
  # Note VSZ and RSS values
  ```

- [ ] **Check scan timing**
  - [ ] Note scan start time in logs
  - [ ] Note scan completion time
  - [ ] Should be < 3 minutes

- [ ] **Verify PPP establishment**
  - [ ] PPP should come up within 30 seconds
  - [ ] Check with: `ip link show ppp0`

---

## Step 9: Error Recovery Testing

- [ ] **Test all carriers blacklisted**
  - [ ] Manually blacklist all carriers
  - [ ] Trigger scan
  - [ ] Verify blacklist auto-clears
  - [ ] Confirm retry attempts

- [ ] **Test invalid carrier entries**
  - [ ] System should skip empty entries
  - [ ] No crashes or hangs

- [ ] **Test forbidden carrier handling**
  - [ ] If forbidden carrier has best signal
  - [ ] Should select next best available

---

## Step 10: Documentation

- [ ] **Update local documentation**
  - [ ] Add new CLI commands to help text
  - [ ] Update any user guides

- [ ] **Create test report**
  ```markdown
  ## Cellular Fixes Test Report
  Date: [DATE]
  Version: [VERSION]

  ### Tests Performed:
  - [ ] Normal scan with logging
  - [ ] PPP failure recovery
  - [ ] Blacklist management
  - [ ] CLI commands

  ### Results:
  [Document results]

  ### Issues Found:
  [List any issues]
  ```

---

## Rollback Plan

If issues are encountered:

1. **Immediate Rollback**
   ```bash
   cd iMatrix
   git checkout -- .
   git clean -fd
   ```

2. **Restore from Backup**
   ```bash
   cd iMatrix/networking
   mv cellular_man.c.backup cellular_man.c
   mv process_network.c.backup process_network.c
   cd ../cli
   mv cli.c.backup cli.c
   ```

3. **Rebuild**
   ```bash
   cd iMatrix
   make clean
   make
   ```

---

## Post-Integration

### Success Criteria
- [ ] All new CLI commands work
- [ ] Enhanced logging visible
- [ ] Carrier blacklisting functional
- [ ] PPP monitoring active
- [ ] No memory leaks
- [ ] No performance degradation

### Sign-off
- [ ] Developer testing complete
- [ ] Code review performed
- [ ] Documentation updated
- [ ] Ready for deployment

---

## Troubleshooting

### Compilation Errors

**Issue**: Undefined reference to blacklist functions
**Solution**: Ensure cellular_blacklist.c is in CMakeLists.txt

**Issue**: Header file not found
**Solution**: Check include paths and file locations

### Runtime Issues

**Issue**: CLI commands not recognized
**Solution**: Verify cli.c integration

**Issue**: No enhanced logging
**Solution**: Check log_carrier_details() calls added

**Issue**: Blacklist not working
**Solution**: Verify clear_blacklist_for_scan() in COPS state

---

## Notes Section

Use this section to document any specific issues or modifications needed for your environment:

```
[Your notes here]
```

---

**Checklist Version**: 1.0
**Date**: 2025-11-22
**Status**: Ready for Integration

✅ When all items are checked, the integration is complete!