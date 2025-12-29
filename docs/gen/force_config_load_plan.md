<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/force_config_load.yaml
Generated on: 2025-12-26
Schema version: 1.0
Complexity level: simple
Status: ALREADY IMPLEMENTED - NO WORK REQUIRED

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: When starting the FC-1 Application add a new command line option to force a reload of the configuration.

**Date:** 2025-12-26
**Branch:** feature/force_config_load (not needed - already on main branches)
**Status:** COMPLETE - Feature already fully implemented

---

## Implementation Summary

**The `-F` command line option was already fully implemented!** Upon code review, the following components were found to be complete:

### Implementation Details

1. **Global Variable** (`Fleet-Connect-1/init/imx_client_init.c:135`):
   ```c
   bool g_force_config_reload = false;
   ```

2. **Header Declaration** (`Fleet-Connect-1/init/imx_client_init.h:80`):
   ```c
   extern bool g_force_config_reload;
   ```

3. **Command Line Parsing** (`iMatrix/imatrix_interface.c:489-509`):
   - Parses `-F` argument
   - Displays informative message to user
   - Sets `g_force_config_reload = true`
   - Continues with normal startup

4. **Configuration Check Logic** (`Fleet-Connect-1/init/imx_client_init.c:629`):
   ```c
   if ( (old_product_id != mgc.product_id) ||
        (mgc.dev_config_checksum != dev_config->config_checksum) ||
        (mgc.no_predefined != dev_config->internal.sensor_count) ||
        g_force_config_reload ) {
   ```

5. **Help Documentation** (`iMatrix/imatrix_interface.c:296`):
   ```c
   printf("  -F                  Force configuration reload (ignore checksum match)\n");
   ```

### Usage

```bash
# Force configuration reload
./FC-1 -F

# Show help with all options
./FC-1 --help
```

### Build Verification

- Build completed successfully with zero errors
- Zero compilation warnings
- All files compile correctly
- Binary: `Fleet-Connect-1/FC-1` (ARM cross-compiled)

---

## Current Branches (No Changes Required)

- **Fleet-Connect-1**: `Aptera_1_Clean`
- **iMatrix**: `feature/add_debug_modes`

---

## Work Summary

| Metric | Value |
|--------|-------|
| Tokens Used | ~5,000 |
| Recompilations | 1 (verification only) |
| Elapsed Time | ~5 minutes |
| Actual Work Time | 0 minutes (already implemented) |
| User Response Wait | 0 minutes |

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** docs/prompt_work/force_config_load.yaml
**Generated:** 2025-12-26
**Completed:** 2025-12-26 - Feature already implemented, no code changes required
