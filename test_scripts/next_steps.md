# iMatrix Memory Test Suite - Next Steps

## Current Issue: Comprehensive Test File Cleanup (2025-01-10)

### Problem
When running `./build/comprehensive_memory_test --iterations 100000`, disk files (.imx) are accumulating in `/tmp/imatrix_test_storage/history/` after each iteration. The cleanup between iterations is incomplete.

### Root Cause
1. `free_sector_extended()` only marks sectors as freed but doesn't delete physical disk files
2. The test doesn't run `process_memory()` long enough to complete cleanup after each iteration
3. No mechanism to detect when cleanup is truly complete

### Solution in Progress
Adding a cleanup loop after each iteration that:
- Triggers `flush_all_to_disk()` to start cleanup
- Runs `process_memory()` repeatedly until all data is processed
- Verifies no disk files remain before next iteration
- Provides timeout protection against infinite loops

### Status
- [COMPLETED] Implementing cleanup completion detection
- [COMPLETED] Adding iteration-level cleanup loop
- [COMPLETED] Testing with large iteration counts

### Solution Implemented
Added three functions to comprehensive_memory_test.c:
1. `count_disk_files()` - Counts .imx files in all bucket directories
2. `count_ram_sectors_with_data()` - Counts RAM sectors containing data
3. `ensure_cleanup_complete()` - Runs process_memory() until cleanup completes

The solution works by:
1. Detecting remaining disk files after each iteration
2. Calling flush_all_to_disk() to trigger cleanup state
3. Running process_memory() in a loop until all RAM sectors and disk files are cleaned
4. Providing timeout protection to prevent infinite loops

Testing confirmed the solution properly cleans up all disk files between iterations.

## Future Improvements

### 1. Enhanced Cleanup Mechanism
- [ ] Add a "cleanup_complete" flag to tiered storage state machine
- [ ] Implement `force_cleanup_all_disk_files()` for immediate cleanup
- [ ] Add sector ownership tracking to ensure proper cleanup

### 2. Better Progress Indicators
- [ ] Enhance `get_pending_disk_write_count()` to include all pending work
- [ ] Add `get_cleanup_progress()` function
- [ ] Provide estimated time remaining for cleanup

### 3. Test Suite Improvements
- [ ] Add dedicated cleanup test cases
- [ ] Implement stress test for cleanup under memory pressure
- [ ] Add performance benchmarks for cleanup operations

### 4. Memory Manager Enhancements
- [ ] Implement lazy disk file deletion with background cleanup thread
- [ ] Add configurable cleanup policies (immediate vs batched)
- [ ] Optimize cleanup for large numbers of files

### 5. Monitoring and Diagnostics
- [ ] Add metrics for cleanup performance
- [ ] Implement cleanup failure detection and recovery
- [ ] Add detailed logging for cleanup operations

## Known Issues

### 1. Disk File Accumulation
**Status**: IN PROGRESS
**Description**: Disk files not cleaned up between test iterations
**Impact**: Can exhaust disk space on long-running tests
**Workaround**: Manual cleanup of /tmp/imatrix_test_storage between test runs

### 2. Cleanup Performance
**Status**: TODO
**Description**: Cleanup can be slow with many small files
**Impact**: Test execution time increases significantly
**Solution**: Batch file deletion operations

### 3. State Machine Complexity
**Status**: TODO
**Description**: Tiered storage state machine doesn't clearly indicate cleanup completion
**Impact**: Difficult to know when it's safe to proceed
**Solution**: Add explicit cleanup states and completion indicators

## Testing Requirements

### Before Release
1. Run comprehensive_memory_test with 100000 iterations without file accumulation
2. Verify cleanup completes within reasonable time (< 1 second per iteration)
3. Test cleanup under various memory pressure scenarios
4. Validate no memory leaks during extended runs

### Performance Targets
- Cleanup time: < 100ms for typical iteration (100 sectors)
- File accumulation: 0 files after cleanup
- Memory usage: Stable across iterations

## Notes
- The tiered storage system was designed for long-running embedded systems, not rapid test iterations
- Current cleanup mechanism relies on state machine progression which may be too slow for tests
- Consider adding test-specific cleanup APIs that bypass normal state machine flow