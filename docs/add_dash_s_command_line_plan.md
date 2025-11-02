# Implementation Plan: Add -S and -I Command Line Options to Fleet-Connect-1

**Created**: 2025-11-02
**Updated**: 2025-11-02 (Corrected implementation location)
**Status**: READY FOR REVIEW
**Developer**: Claude Code

---

## Executive Summary

**Target File**: `iMatrix/imatrix_interface.c` (main entry point for Linux platform)
**Objective**: Add `-S` (summary) and `-I` (index) command-line options to match CAN_DM functionality
**Reference**: Existing `-P` option in same file (lines 263-297) serves as implementation template
**Effort**: ~60 minutes (implementation + testing + documentation)

**Key Changes**:
1. Add `-S` option: Print configuration summary (follow existing -P pattern)
2. Add `-I` option: Display file index for v4+ config files (follow CAN_DM pattern)
3. Update function documentation
4. Both options auto-locate config and exit immediately

---

## 1. Background and Objectives

### Current State Analysis

After reviewing the codebase, I found:

1. **CAN_DM.c** (lines 622-794):
   - Has `-P <filename>`: Print full configuration details and exit
   - Has `-S <filename>`: Print configuration summary and exit
   - Has `-I <filename>`: Display configuration file index (v4+ files only)
   - All three options print and exit immediately without starting the application

2. **iMatrix/imatrix_interface.c** (lines 259-303):
   - **This is the ACTUAL main() entry point for Fleet-Connect-1 on Linux**
   - Already has `-P`: Print configuration (auto-finds file in IMATRIX_STORAGE_PATH) and exit
   - Uses `find_cfg_file()`, `read_config()`, and `print_config()` functions
   - **NEEDS UPDATING** to add `-S` and `-I` options

3. **Fleet-Connect-1/linux_gateway.c**:
   - NOT the main entry point (called by imatrix_interface.c)
   - Does NOT need modification for this task

### Objectives

Enhance command-line options in `iMatrix/imatrix_interface.c` to match CAN_DM behavior:

1. **Update existing `-P` option**: Already implemented, keep as-is (reference implementation)
2. **Add `-S` option**: Print configuration summary and exit
3. **Add `-I` option**: Display configuration file index (v4+ files) and exit
4. All options should:
   - Automatically locate configuration file in IMATRIX_STORAGE_PATH (like existing -P)
   - Print requested information
   - Exit immediately (return 0 on success, 1 on error)
   - NOT start normal gateway operation (imatrix_start())

### Available Functions

From `Fleet-Connect-1/init/wrp_config.h`:
```c
config_t *read_config(const char *filename);
int print_config(const config_t *config);           // Full details
int print_config_summary(const config_t *config);   // Summary
void free_call_config(config_t *fc_cfg);            // Cleanup
```

From `Fleet-Connect-1/init/imx_client_init.c`:
```c
char *find_cfg_file(const char *directory_path);    // Auto-locate config
```

---

## 2. Detailed Implementation Plan

### Phase 1: Extend Command-Line Parsing in iMatrix/imatrix_interface.c

**Location**: `iMatrix/imatrix_interface.c` main() function (lines 259-303)

**Current Implementation** (EXISTING - DO NOT MODIFY):
- Lines 259-303: main() function with `-P` option already implemented
- Pattern: Auto-locate config, read, print, cleanup, exit
- This is our **REFERENCE IMPLEMENTATION**

**Changes Required**:

1. **Add `-S` option handling** (after existing `-P` block):
   - Follow exact same pattern as `-P`
   - Use `print_config_summary()` instead of `print_config()`
   - Auto-locate configuration file like `-P` does
   - Exit immediately after printing

2. **Add `-I` option handling** (after `-S` block):
   - Follow CAN_DM.c pattern (lines 666-772)
   - Read file header manually to get version and index
   - If version >= 4: read and display index using `print_config_index()`
   - If version < 4: display message that index not available
   - Also print summary for completeness
   - Exit immediately after printing

3. **Update function comment** (line 256-258):
   - Add `-S` and `-I` to command line options list

### Phase 2: Implement -S Option (Print Configuration Summary)

**Implementation Approach**:
- Insert AFTER existing `-P` block (after line 297 in imatrix_interface.c)
- Copy the exact pattern from `-P` implementation
- Change only the print function call

**Code to Add** (insert after line 297):
```c
        else if (strcmp(argv[i], "-S") == 0) {
            /* Print configuration summary option */
            printf("Looking for configuration file in: %s\n", IMATRIX_STORAGE_PATH);

            /* Find the configuration file */
            extern char *find_cfg_file(const char *directory_path);
            char *config_file = find_cfg_file(IMATRIX_STORAGE_PATH);

            if (config_file == NULL) {
                printf("Error: Failed to find configuration file in %s\n", IMATRIX_STORAGE_PATH);
                return 1;
            }

            printf("Found configuration file: %s\n", config_file);

            /* Read the configuration */
            extern config_t *read_config(const char *filename);
            config_t *config = read_config(config_file);

            if (config == NULL) {
                printf("Error: Failed to read configuration file: %s\n", config_file);
                free(config_file);
                return 1;
            }

            /* Print the configuration summary */
            extern int print_config_summary(const config_t *config);
            print_config_summary(config);

            /* Clean up and exit */
            free(config_file);
            return 0;
        }
```

### Phase 3: Implement -I Option (Display Configuration Index)

**Implementation Approach**:
- Insert AFTER `-S` block
- Based on CAN_DM.c implementation (lines 666-772)
- Manually read file header to extract version and index
- Display index structure for v4+ files

**Code to Add** (insert after -S block):
```c
        else if (strcmp(argv[i], "-I") == 0) {
            /* Display configuration file index option (v4+ files) */
            printf("Looking for configuration file in: %s\n", IMATRIX_STORAGE_PATH);

            /* Find the configuration file */
            extern char *find_cfg_file(const char *directory_path);
            char *config_file = find_cfg_file(IMATRIX_STORAGE_PATH);

            if (config_file == NULL) {
                printf("Error: Failed to find configuration file in %s\n", IMATRIX_STORAGE_PATH);
                return 1;
            }

            printf("Found configuration file: %s\n", config_file);

            /* Open file for binary reading */
            FILE *f = fopen(config_file, "rb");
            if (!f) {
                printf("Error: Failed to open configuration file '%s'\n", config_file);
                free(config_file);
                return 1;
            }

            /* Read signature (little-endian) */
            uint8_t sig_buf[4];
            if (fread(sig_buf, 1, 4, f) != 4) {
                printf("Error: Failed to read file signature\n");
                fclose(f);
                free(config_file);
                return 1;
            }
            uint32_t signature = ((uint32_t)sig_buf[0]) |
                                ((uint32_t)sig_buf[1] << 8) |
                                ((uint32_t)sig_buf[2] << 16) |
                                ((uint32_t)sig_buf[3] << 24);

            uint32_t expected_sig = 0xCAFEBABE;
            if (signature != expected_sig) {
                printf("Error: Invalid file signature (0x%08X)\n", signature);
                fclose(f);
                free(config_file);
                return 1;
            }

            /* Read version (little-endian) */
            uint8_t ver_buf[2];
            if (fread(ver_buf, 1, 2, f) != 2) {
                printf("Error: Failed to read file version\n");
                fclose(f);
                free(config_file);
                return 1;
            }
            uint16_t version = ((uint16_t)ver_buf[0]) | ((uint16_t)ver_buf[1] << 8);

            printf("\n=== Configuration File Analysis ===\n");
            printf("File: %s\n", config_file);
            printf("Signature: 0x%08X (valid)\n", signature);
            printf("Version: %u\n", version);

            if (version >= 4) {
                /* Read and display the index */
                extern int print_config_index(const config_index_t *index);
                extern typedef struct config_index config_index_t;  /* From wrp_config.h */

                config_index_t file_index;
                uint8_t buf[4];

                /* Read num_sections (16-bit little-endian) */
                if (fread(ver_buf, 1, 2, f) != 2) {
                    printf("Error: Failed to read index\n");
                    fclose(f);
                    free(config_file);
                    return 1;
                }
                file_index.num_sections = ((uint16_t)ver_buf[0]) | ((uint16_t)ver_buf[1] << 8);

                /* Helper macro to read uint32 little-endian */
                #define READ_UINT32_LE(var) do { \
                    if (fread(buf, 1, 4, f) != 4) { \
                        printf("Error: Failed to read index entry\n"); \
                        fclose(f); \
                        free(config_file); \
                        return 1; \
                    } \
                    (var) = ((uint32_t)buf[0]) | ((uint32_t)buf[1] << 8) | \
                           ((uint32_t)buf[2] << 16) | ((uint32_t)buf[3] << 24); \
                } while(0)

                /* Read all index entries */
                READ_UINT32_LE(file_index.product.offset);
                READ_UINT32_LE(file_index.product.size);
                READ_UINT32_LE(file_index.control_sensors.offset);
                READ_UINT32_LE(file_index.control_sensors.size);

                for (int j = 0; j < 3; j++) {  /* NO_CAN_BUS = 3 */
                    READ_UINT32_LE(file_index.can_bus[j].offset);
                    READ_UINT32_LE(file_index.can_bus[j].size);
                }

                READ_UINT32_LE(file_index.network.offset);
                READ_UINT32_LE(file_index.network.size);
                READ_UINT32_LE(file_index.internal_sensors.offset);
                READ_UINT32_LE(file_index.internal_sensors.size);
                READ_UINT32_LE(file_index.dbc_settings.offset);
                READ_UINT32_LE(file_index.dbc_settings.size);

                #undef READ_UINT32_LE

                /* Display the index */
                print_config_index(&file_index);

                /* Get file size for checksum location */
                fseek(f, 0, SEEK_END);
                long file_size = ftell(f);
                printf("\nFile size: %ld bytes\n", file_size);
                printf("Checksum location: 0x%08lX (last 4 bytes)\n", file_size - 4);
            } else {
                printf("\nNote: Version %u files do not contain an index.\n", version);
                printf("Index is available in version 4 and later.\n");
            }

            fclose(f);

            /* Also read and display summary using normal functions */
            extern config_t *read_config(const char *filename);
            extern int print_config_summary(const config_t *config);
            config_t *dev_config = read_config(config_file);
            if (dev_config != NULL) {
                printf("\n");
                print_config_summary(dev_config);
                free(dev_config);
            }

            free(config_file);
            return 0;
        }
```

---

## 3. Implementation Checklist

### Pre-Implementation
- [x] Read and understand CAN_DM.c command-line parsing (lines 622-794)
- [x] Read and understand imatrix_interface.c existing -P implementation (lines 259-303)
- [x] Verify available functions in wrp_config.h
- [x] Identify CORRECT location for changes (iMatrix/imatrix_interface.c)
- [x] Create comprehensive implementation plan document
- [ ] **GET USER APPROVAL BEFORE PROCEEDING**

### Implementation Tasks

**Code Changes** (iMatrix/imatrix_interface.c):
- [ ] Update function comment (lines 256-258) to document -S and -I options
- [ ] Add -S option handling (insert after line 297, before closing brace)
- [ ] Add -I option handling (insert after -S block)
- [ ] Verify all external function declarations are correct
- [ ] Add proper error handling and cleanup for both options

**Testing Tasks**:
- [ ] Test existing -P option (verify still works correctly)
- [ ] Test new -S option with valid configuration file
- [ ] Test new -I option with v4+ configuration file
- [ ] Test -I option with pre-v4 configuration file (should show "not available" message)
- [ ] Test normal operation (no command-line options)
- [ ] Test error handling with missing/corrupted configuration file

### Documentation Tasks
- [ ] Update Fleet-Connect-1/CLAUDE.md with new command-line options
- [ ] Update docs/Fleet-Connect-Overview.md command-line options section
- [ ] Add usage examples to documentation
- [ ] Update progress.md with implementation steps

---

## 4. Expected Usage Examples

### Print Full Configuration (EXISTING)
```bash
# Print detailed configuration and exit (ALREADY WORKS)
./Fleet-Connect -P
```

**Output Example**:
```
Looking for configuration file in: /usr/qk/etc/sv/memory_test
Found configuration file: /usr/qk/etc/sv/memory_test/HM_Wrecker_cfg.bin

=== Configuration File Details ===
[Full detailed output with all sensors, CAN nodes, network interfaces, etc.]
```

### Print Configuration Summary (NEW)
```bash
# Print summary and exit
./Fleet-Connect -S
```

**Output Example**:
```
Looking for configuration file in: /usr/qk/etc/sv/memory_test
Found configuration file: /usr/qk/etc/sv/memory_test/HM_Wrecker_cfg.bin

=== Configuration Summary ===
Product:                 HM Wrecker (ID: 12345)
Control/Sensor Blocks:   45
Total CAN Nodes:         87
Total CAN Signals:       234
Network Interfaces:      2
  - eth0                Mode: static   IP: 192.168.1.100
  - wlan0               Mode: dhcp     IP: (none)
Internal Sensors:        12
```

### Display Configuration Index (NEW)
```bash
# Display configuration file index (v4+ files only)
./Fleet-Connect -I
```

**Output Example (v4+ file)**:
```
Looking for configuration file in: /usr/qk/etc/sv/memory_test
Found configuration file: /usr/qk/etc/sv/memory_test/HM_Wrecker_cfg.bin

=== Configuration File Analysis ===
File: /usr/qk/etc/sv/memory_test/HM_Wrecker_cfg.bin
Signature: 0xCAFEBABE (valid)
Version: 4

=== Configuration File Index ===
Section                  Offset      Size
------------------------------------------------
Product                  0x00000010  256 bytes
Control/Sensors          0x00000110  1024 bytes
CAN Bus 0                0x00000510  4096 bytes
CAN Bus 1                0x00001510  2048 bytes
CAN Bus 2 (Ethernet)     0x00001D10  512 bytes
Network Interfaces       0x00001F10  256 bytes
Internal Sensors         0x00002010  128 bytes
DBC Settings             0x00002090  512 bytes

File size: 12345 bytes
Checksum location: 0x00003039 (last 4 bytes)

[Also displays summary]
```

**Output Example (pre-v4 file)**:
```
Looking for configuration file in: /usr/qk/etc/sv/memory_test
Found configuration file: /usr/qk/etc/sv/memory_test/Old_Product_cfg.bin

=== Configuration File Analysis ===
File: /usr/qk/etc/sv/memory_test/Old_Product_cfg.bin
Signature: 0xCAFEBABE (valid)
Version: 3

Note: Version 3 files do not contain an index.
Index is available in version 4 and later.

[Displays summary instead]
```

### Normal Operation (No Options)
```bash
# Start gateway normally
./Fleet-Connect
```

**Output**: Normal gateway startup messages and operation

---

## 5. Error Handling

### Configuration File Not Found
```
Error: Failed to find configuration file in /usr/qk/etc/sv/memory_test
Exit code: 1
```

### Configuration File Read Error
```
Found configuration file: /usr/qk/etc/sv/memory_test/corrupted.cfg.bin
Error: Failed to read configuration file: /usr/qk/etc/sv/memory_test/corrupted.cfg.bin
Exit code: 1
```

---

## 6. Testing Plan

### Unit Testing
1. **Test with valid configuration file**:
   - Run `./Fleet-Connect -P` → Verify full details printed and exit(0)
   - Run `./Fleet-Connect -S` → Verify summary printed and exit(0)

2. **Test with no configuration file**:
   - Temporarily rename config file
   - Run `./Fleet-Connect -P` → Verify error message and exit(1)
   - Run `./Fleet-Connect -S` → Verify error message and exit(1)
   - Restore config file

3. **Test normal operation**:
   - Run `./Fleet-Connect` (no options) → Verify normal startup

4. **Test invalid option**:
   - Run `./Fleet-Connect -X` → Verify ignored and normal startup

### Integration Testing
1. Verify configuration file auto-location works correctly
2. Verify all configuration sections are printed correctly
3. Verify memory cleanup (no leaks)
4. Test on actual target hardware (QUAKE 1180)

---

## 7. Benefits and Use Cases

### Development Benefits
- **Quick configuration verification** without starting gateway
- **Troubleshooting** configuration file issues
- **Documentation** of system setup
- **Automated testing** of configuration changes

### Production Use Cases
- **Pre-deployment verification**: Ensure configuration is correct before deployment
- **System documentation**: Generate configuration reports for records
- **Remote troubleshooting**: Get configuration details without full gateway startup
- **Configuration comparison**: Compare configurations across multiple devices

---

## 8. References

### Source Files to Modify
- **iMatrix/imatrix_interface.c** (lines 259-303): Main entry point - add -S and -I options

### Source Files Referenced (for implementation patterns)
- **CAN_DM/src/core/CAN_DM.c** (lines 622-794): Reference for -P/-S/-I implementation
- **iMatrix/imatrix_interface.c** (lines 263-297): EXISTING -P implementation (our template)
- **Fleet-Connect-1/init/wrp_config.h**: Function declarations for config operations
- **Fleet-Connect-1/init/wrp_config.c**: Function implementations
- **Fleet-Connect-1/init/imx_client_init.c**: `find_cfg_file()` function

### Documentation Files to Update
- **Fleet-Connect-1/CLAUDE.md**: Command-line options section
- **docs/Fleet-Connect-Overview.md**: Usage documentation
- **docs/progress.md**: Implementation tracking

---

## 9. Risk Assessment

### Low Risk Items
- Adding command-line parsing before existing code
- Using existing well-tested functions (read_config, print_config)
- Early exit prevents interference with normal operation

### Mitigation Strategies
- Keep changes minimal and isolated
- Follow existing CAN_DM implementation pattern exactly
- Test thoroughly before deployment
- Add comprehensive error handling
- Ensure proper memory cleanup

---

## 10. Timeline Estimate

### Implementation (Post-Approval)
- **Update function comments**: Add -S and -I to documentation - 5 minutes
- **Implement -S option**: Add code block to imatrix_interface.c - 10 minutes
- **Implement -I option**: Add code block with index reading logic - 20 minutes
- **Testing**: Test all three options (-P, -S, -I) - 15 minutes
- **Documentation**: Update CLAUDE.md and Fleet-Connect-Overview.md - 10 minutes

**Total Estimated Time**: ~60 minutes

---

## 11. User Review Responses

Questions were asked and answered:

1. ✅ **Is the approach (matching CAN_DM.c implementation) correct?**
   - Answer: **Yes** - Follow CAN_DM.c implementation pattern

2. ✅ **Should both -P and -S auto-locate the configuration file in IMATRIX_STORAGE_PATH?**
   - Answer: **Yes** - Refer to existing -P implementation (auto-locate pattern)

3. ✅ **Should we add -I option as well (for configuration index display)?**
   - Answer: **Yes** - Add -I option for configuration file index display

4. ✅ **Any specific formatting requirements for the output?**
   - Answer: **Best practices** - Follow existing formatting patterns

5. ✅ **Any additional command-line options needed while we're implementing this?**
   - Answer: **Not at this stage** - Only -S and -I for now

---

## 12. Implementation Summary

### What We're Adding

**File to Modify**: `iMatrix/imatrix_interface.c` (lines 259-303)

**New Options**:
1. **`-S`**: Print configuration summary (similar to existing -P)
   - ~35 lines of code
   - Identical pattern to -P, different print function

2. **`-I`**: Display configuration file index (v4+ files)
   - ~85 lines of code
   - Reads binary file header manually
   - Displays index structure and file analysis
   - Falls back to summary for pre-v4 files

**Code Location**:
- Insert both blocks AFTER existing `-P` block (line 297)
- BEFORE the closing of the for loop and the normal startup code

### Next Steps

1. **✅ AWAITING USER APPROVAL** of this updated plan
2. Upon approval, implement -S option
3. Upon approval, implement -I option
4. Test all three options thoroughly
5. Update documentation
6. Mark task complete

---

**End of Implementation Plan**
