# Plan: Add Direct App CLI Access

**Date:** 2026-01-06
**Branch:** feature/add_direct_app_cli_access
**Author:** Claude Code
**Status:** COMPLETED

---

## Overview

Add a new method to access app CLI commands directly from the main CLI mode using the `app:` prefix, without permanently switching modes.

## Current Behavior

1. **CLI Mode (default)**: User enters iMatrix commands (`debug`, `mem`, `s`, etc.)
2. **App Mode**: User enters Fleet-Connect-1 commands (`loopstatus`, `c`, `debug`, etc.)
3. **Mode Switching**:
   - TAB key toggles between modes
   - `app` command switches to app mode
   - `exit` command returns to CLI mode

## Proposed Behavior

Add support for `app:` prefix in CLI mode:

```
>app: loopstatus
```

This will:
1. Execute `loopstatus` in the app CLI handler
2. Return to CLI mode immediately (no mode switch)
3. CLI stays in its current mode

## Implementation Details

### File to Modify

**`iMatrix/cli/cli.c`** - Line ~914 in `cli_process_ch()` function

### Code Change Location

In the `cli_process_ch()` function, inside the command processing block:

```c
// Current code (around line 912):
token = strtok( command_line, " " );
if( token != NULL ) {
    if( imx_cli_mode == true ) {
        if( strcmp( token, IMX_APP_COMMAND ) == 0x00 ) {
            // Switch to app mode
            ...
        } else {
            // Look up in command table
            ...
        }
    }
    ...
}
```

### Proposed Change

Add a check for `app:` prefix right after the `app` command check:

```c
#define IMX_APP_PREFIX          "app:"   // Prefix for direct app command execution
#define IMX_APP_PREFIX_LEN      4        // Length of "app:"

// Inside cli_process_ch(), after checking for "app" command:
if( strncmp( token, IMX_APP_PREFIX, IMX_APP_PREFIX_LEN ) == 0x00 ) {
    // Direct app command - execute without mode switch
    char *app_token = token + IMX_APP_PREFIX_LEN;
    if( host_cli_handler != NULL && strlen(app_token) > 0 ) {
        cmd_found = (host_cli_handler)( app_token );
    } else if( host_cli_handler == NULL ) {
        imx_cli_print( "No Host CLI Handler present\r\n" );
        cmd_found = true;  // Prevent "Unknown Command" message
    } else {
        imx_cli_print( "Usage: app: <command>\r\n" );
        cmd_found = true;
    }
}
```

### Key Points

1. **No mode switching**: `imx_cli_mode` remains `true` (CLI mode)
2. **Direct execution**: Calls `host_cli_handler` directly with the command after `app:`
3. **Handles edge cases**:
   - No host handler present: Shows error message
   - Empty command after `app:`: Shows usage hint
4. **Preserves strtok state**: The remaining arguments are still available via subsequent `strtok(NULL, " ")` calls in the app handler

### Usage Examples

Both syntaxes are supported:

```
>app:loopstatus           # No space after colon - works
>app: loopstatus          # Space after colon - also works
>app: c                   # Shows app config, returns to CLI mode
>app: debug general       # Enables app debug flag, returns to CLI mode
```

### Syntax Handling

1. **`app:command`** (no space): First token is `app:command`, extract command after `app:`
2. **`app: command`** (with space): First token is `app:`, get next token as command

## Todo List

- [x] Create feature branches in both iMatrix and Fleet-Connect-1
- [x] Add `IMX_APP_PREFIX` constant definition in cli.c
- [x] Implement `app:` prefix detection logic
- [x] Handle edge cases (no handler, empty command)
- [x] Build and verify no compile errors/warnings
- [x] Test on device: basic functionality
- [x] Test on device: verify mode stays in CLI
- [x] Test on device: verify all app commands work with prefix
- [x] Update documentation

## Device Test Results (2026-01-06)

| Test | Command | Result |
|------|---------|--------|
| App help (space) | `app: ?` | ✅ Shows app help, prompt stays `>` |
| App status (no space) | `app:s` | ✅ Shows app status, prompt stays `>` |
| Loopstatus | `app: loopstatus` | ✅ Shows loopstatus, prompt stays `>` |
| Empty prefix | `app:` | ✅ Shows usage message |
| Invalid command | `app: invalidcommand` | ✅ Shows "Unknown app command: invalidcommand" |
| Original app cmd | `app` | ✅ Switches to app mode (prompt shows `app>`) |
| CLI mode cmd | `s` | ✅ CLI commands still work normally |

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `iMatrix/cli/cli.c` | Modify | Add app: prefix handling |

## Testing Plan

1. **Build verification**: Compile successfully with no errors/warnings
2. **Basic test**: `app: loopstatus` shows loop status
3. **Mode test**: After `app:` command, verify CLI mode (no "app" in prompt)
4. **Edge case**: `app:` with no command shows usage
5. **Edge case**: `app:invalidcmd` shows "Unknown Command" from app handler
6. **Comparison**: `app loopstatus` still switches to app mode (existing behavior unchanged)

## Risk Assessment

**Low Risk**:
- Change is isolated to one function in cli.c
- Does not affect existing `app` command behavior
- Does not modify app handler or mode switching logic
- Simple string comparison addition

---

## Implementation Summary

**Completed:** 2026-01-06

### Changes Made

1. **Added constants** in `iMatrix/cli/cli.c`:
   - `IMX_APP_PREFIX "app:"` - The prefix string
   - `IMX_APP_PREFIX_LEN 4` - Length of prefix for efficient comparison

2. **Added prefix handling logic** in `cli_process_ch()` function (lines 921-947):
   - Uses `strncmp()` to check for `app:` prefix
   - Handles both `app:command` and `app: command` syntax
   - Calls `host_cli_handler()` directly without switching modes
   - Handles edge cases: no handler present, empty command

### Code Location

The implementation is in `iMatrix/cli/cli.c`, inside the `cli_process_ch()` function, in the CLI mode command processing section (after the "app" command check, before the command table lookup).

### Build Verification

- Build completed successfully with zero errors
- Zero new warnings introduced
- Binary: `Fleet-Connect-1/build/FC-1`

### Metrics

- **Lines of code added:** ~27 lines
- **Files modified:** 1 (`iMatrix/cli/cli.c`)
- **Recompilations for syntax errors:** 0

---

**Plan Created By:** Claude Code
**Implementation Completed:** 2026-01-06
