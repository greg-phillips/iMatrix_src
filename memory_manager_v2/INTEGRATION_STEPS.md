# Memory Manager v2 - Integration Steps

## Branch Information
- **Branch Name**: `feature/memory-manager-v2-integration`
- **Base Branch**: `main`
- **Status**: Ready for integration

## Quick Integration Guide

### Step 1: Checkout the Branch
```bash
git fetch origin
git checkout feature/memory-manager-v2-integration
```

### Step 2: Run Tests
```bash
cd memory_manager_v2
./test_harness --test=all --verbose
# Expected: 43/43 tests passing
```

### Step 3: Deploy to Development
```bash
./deploy_v2.sh dev
./verify_deployment.sh
```

### Step 4: Integration Testing
Test with the main iMatrix client:
```bash
cd ../iMatrix
# Build with Memory Manager v2
cmake -DMEMORY_MANAGER_V2=1 .
make
# Run iMatrix tests
./run_tests.sh
```

### Step 5: Deploy to Staging
```bash
cd ../memory_manager_v2
./deploy_v2.sh staging
./verify_deployment.sh
```

### Step 6: Production Deployment
```bash
./deploy_v2.sh production
# Monitor for 24 hours
tail -f /var/log/imatrix.log
```

## Integration Points

### Files to Update in iMatrix

1. **CMakeLists.txt**
   - Add Memory Manager v2 source files
   - Add compile definition `-DMEMORY_MANAGER_V2=1`

2. **system_init.c**
   - Add initialization call for v2
   - Configure platform-specific settings

3. **No API Changes Required**
   - All existing calls remain compatible
   - Drop-in replacement

## Validation Checklist

### Pre-Integration
- [ ] Branch checked out successfully
- [ ] All 43 tests passing
- [ ] Deployment script executable

### Development Environment
- [ ] Deployed to dev environment
- [ ] Verification script passes
- [ ] iMatrix builds successfully
- [ ] iMatrix tests pass

### Staging Environment
- [ ] Deployed to staging
- [ ] Performance metrics validated
- [ ] 24-hour stability test passed
- [ ] Flash wear reduction confirmed

### Production Readiness
- [ ] All environments tested
- [ ] Monitoring configured
- [ ] Team briefed on changes
- [ ] Git revert procedure documented

## Key Metrics to Monitor

After deployment, monitor these metrics:
- **RAM Usage**: Should stay below 80%
- **Flush Frequency**: < 1 per hour
- **Disk Storage**: < 256MB total
- **Performance**: > 900K ops/sec
- **Error Rate**: 0% corruption

## Support Commands

### Check Integration Status
```bash
# Verify v2 is active
grep -q "MEMORY_MANAGER_V2" include/platform_config.h && echo "V2 Active" || echo "V2 Not Active"

# Check test results
./test_harness --test=all --quiet && echo "All tests pass" || echo "Tests failing"

# Monitor disk usage
du -sh /var/imatrix/storage/ 2>/dev/null || du -sh /tmp/imatrix_storage/ 2>/dev/null
```

### Quick Diagnostics
```bash
# Run verification
./verify_deployment.sh

# Check specific components
./test_harness --test=36 --verbose  # Disk operations
./test_harness --test=33 --verbose  # Recovery
./test_harness --test=35 --verbose  # Performance
```

## Troubleshooting

### Issue: Tests Failing
```bash
# Run detailed tests
./test_harness --test=all --detailed

# Check build configuration
cmake -DTARGET_PLATFORM=LINUX -DSTORAGE_BACKEND=MOCK .
make clean && make
```

### Issue: Deployment Fails
```bash
# Check permissions
sudo ./deploy_v2.sh dev

# Verify paths exist
ls -la ../iMatrix/cs_ctrl/
```

### Issue: Performance Degradation
```bash
# Run performance test
./test_harness --test=35 --verbose

# Check disk I/O
iostat -x 1 10
```

## Success Criteria

Integration is successful when:
1. ✅ All 43 tests pass consistently
2. ✅ iMatrix builds without errors
3. ✅ iMatrix tests pass with v2
4. ✅ Performance meets requirements (>900K ops/sec)
5. ✅ No corruption errors in 24 hours
6. ✅ Flash wear reduced by >80%

## Contact for Support

If you encounter issues during integration:
1. Check this document first
2. Review DEPLOYMENT_PLAN.md for detailed procedures
3. Run verification scripts
4. Check test logs in memory_manager_v2/

## Next Steps After Integration

1. **Monitor Production** - Watch metrics for 1 week
2. **Document Results** - Update performance reports
3. **Close PR** - Merge to main after validation
4. **Team Training** - Brief team on new capabilities

---

**Branch URL**: https://github.com/greg-phillips/iMatrix_src/tree/feature/memory-manager-v2-integration

**PR URL**: https://github.com/greg-phillips/iMatrix_src/pull/new/feature/memory-manager-v2-integration