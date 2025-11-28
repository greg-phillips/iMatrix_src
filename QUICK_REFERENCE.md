# Cellular Blacklist - Quick Reference

**Build**: Nov 24 2025 @ 08:15
**Binary**: FC-1 (13 MB, MD5: 2eb59ec2a2d0598d7e65e6a391eb8608)

---

## What Was Fixed

### 7 Critical Issues Resolved:

1. **Blacklist never added new carriers** → Now adds properly
2. **Blacklist check didn't verify flag** → Now checks blacklisted=true
3. **Blacklisted operators not skipped** → Now has break statement
4. **Only exit code 0xb triggered blacklist** → Now ANY CME ERROR triggers
5. **Script timeouts never blacklisted** → Now blacklists after 3rd timeout
6. **Rescan flag never checked** → Now checked in CELL_ONLINE/DISCONNECTED
7. **Blacklist cleared on every scan** → Now persists until timeout (5 min)

---

## Key Log Messages

### Success Indicators:
```
✅ "New carrier added to blacklist: 311480 (total: 1)"
✅ "Rescan requested, initiating carrier scan"
✅ "Operator 3 (Verizon) is blacklisted, skipping"
✅ "Operator 4 (AT&T) selected as first valid operator"
```

### Failure Indicators (OLD behavior - should NOT see):
```
❌ "Cleared for fresh carrier evaluation"  (removed!)
❌ Repeated failures with same carrier (30+ times)
❌ No blacklist entries after failures
```

---

## Quick Tests

### Test Blacklist Command:
```bash
> cell blacklist
```
Should show entries or "No blacklisted carriers found"

### Monitor Live:
```bash
tail -f /var/log/FC-1.log | grep -E "Blacklist|Rescan|blacklist"
```

### Verify Version:
```bash
tail -50 /var/log/FC-1.log | grep "built on"
```
Must show: `Nov 24 2025 @ 08:15`

---

## Files Modified

| File | Lines Changed |
|------|---------------|
| cellular_blacklist.c | 200-233 (add), 245 (check) |
| cellular_man.c | 2022-2086 (failures), 2812 (skip), 2981-2986 (ONLINE), 3038-3045 (DISCONNECTED), 3203 (REMOVED clear) |

---

## Expected Behavior

### Before Fix:
- Verizon fails → Not blacklisted → Retry Verizon → Infinite loop

### After Fix:
- Verizon fails → Blacklisted → Rescan → Skip Verizon → Try AT&T → Success

---

## Troubleshooting

### Issue: Blacklist not working
**Check**: `tail /var/log/FC-1.log | grep "built on"`
**Must show**: Nov 24 2025 @ 08:15
**If not**: Wrong binary deployed

### Issue: Still stuck in loop
**Check**: `grep "Cleared for fresh" /var/log/FC-1.log`
**Should show**: No matches
**If matches found**: Old binary still running

### Issue: No rescan after failure
**Check**: `grep "Rescan requested" /var/log/FC-1.log`
**Should show**: Messages after each CME ERROR
**If not**: Check cellular_request_rescan flag implementation

---

**Quick Deploy**: `scp FC-1 root@gateway:/tmp/ && ssh root@gateway "sv down FC-1 && mv /tmp/FC-1 /usr/qk/bin/FC-1 && chmod +x /usr/qk/bin/FC-1 && sv up FC-1"`

