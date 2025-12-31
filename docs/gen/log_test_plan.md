# Log Test Subcommand Implementation Plan

**Date**: 2025-12-31
**Status**: IN PROGRESS
**Author**: Claude Code
**Related**: docs/gen/logging_work_plan.md, docs/gen/early_logger_init_plan.md

## Overview

This plan adds a `log test` CLI subcommand that generates test messages to validate the filesystem logger's rotation functionality.

## Requirements

1. Add "test" as a subcommand to the existing `log` CLI command
2. Generate enough messages to trigger log rotation (exceed FS_LOG_MAX_FILE_SIZE)
3. Validate that rotation occurs correctly
4. Report test results to the user

## Test Configuration

For faster testing, temporarily change FS_LOG_MAX_FILE_SIZE:
- **Test value**: 100KB (100 * 1024 = 102,400 bytes)
- **Production value**: 10MB (10 * 1024 * 1024 = 10,485,760 bytes)

## Implementation Details

### File: iMatrix/cli/cli_log.c

Add handling for "test" subcommand:

```c
} else if (strcmp(token, "test") == 0) {
    cli_log_test();
}
```

### New Function: cli_log_test()

```c
/**
 * @brief Test log rotation by generating messages until rotation occurs
 *
 * This function generates test messages to fill the log file past the
 * rotation threshold (FS_LOG_MAX_FILE_SIZE), verifying that:
 * 1. Messages are being written to the log file
 * 2. Log rotation triggers at the correct size
 * 3. A new log file is created after rotation
 *
 * @param None
 * @retval None
 */
static void cli_log_test(void)
{
    // Get initial state
    const char *initial_path = fs_logger_get_current_path();
    size_t initial_size = fs_logger_get_current_size();

    // Generate messages until rotation
    // Each message ~100 bytes, need >100KB for test rotation
    // Generate in batches with progress reporting

    // Verify rotation occurred
    // Report success/failure
}
```

### Message Generation Strategy

- Generate 1500 test messages (for 100KB test threshold)
- Each message ~100 bytes including timestamp and sequence number
- Report progress every 500 messages
- Total generation: ~150KB to ensure rotation triggers
- Verify new log file created after rotation

### Test Message Format

```
[SEQ:0001] Log rotation test message - timestamp: XXXXXX padding padding padding padding
```

## Implementation Steps

1. [x] Create plan document
2. [ ] Temporarily change FS_LOG_MAX_FILE_SIZE to 100KB
3. [ ] Add `log test` subcommand to cli_log.c
4. [ ] Build Fleet-Connect-1
5. [ ] Deploy to gateway and run test
6. [ ] Verify rotation and capture results
7. [ ] Create success report
8. [ ] Change FS_LOG_MAX_FILE_SIZE back to 10MB
9. [ ] Rebuild and redeploy

## Files to Modify

| File | Change |
|------|--------|
| `iMatrix/cli/filesystem_logger.h` | Temporarily change FS_LOG_MAX_FILE_SIZE to 100KB |
| `iMatrix/cli/cli_log.c` | Add "test" subcommand handler |

## Testing Plan

1. SSH to gateway
2. Run `log test` command
3. Observe message generation progress
4. Verify rotation message appears
5. Check `/var/log/` for rotated log files
6. Verify new log file created

## Expected Output

```
=== Log Rotation Test ===
Initial log file: /var/log/fc-1.log
Initial log size: 529 bytes
Generating test messages...
  Progress: 500/1500 messages written
  Progress: 1000/1500 messages written
  Progress: 1500/1500 messages written
Log rotation occurred!
New log file: /var/log/fc-1.log
New log size: XXX bytes
Old log archived to: fc-1.log.1
Test PASSED: Log rotation working correctly
```

## Verification Commands

```bash
# Check log files after test
ls -la /var/log/fc-1*

# Verify content of current log
tail -20 /var/log/fc-1.log

# Verify old log was archived
ls -la /var/log/fc-1.log.1
```

---

*Document created: 2025-12-31*
