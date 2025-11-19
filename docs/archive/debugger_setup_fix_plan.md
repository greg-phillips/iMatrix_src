# Remote Debugger Setup Fix Plan

## Document Information
- **Created**: 2025-11-10
- **Author**: Claude Code
- **Status**: READY FOR IMPLEMENTATION
- **Target**: Remote debugging of Fleet-Connect-1 (FC-1) on ARM iMX6 targets from x86_64 development host

---

## Problem Analysis

### Current Status
✅ **Binary**: FC-1 compiled with debug symbols (`-g`, not stripped, debug_info present)
✅ **Build Type**: CMAKE_BUILD_TYPE=Debug
✅ **Launch Configuration**: .vscode/launch.json properly configured for remote debugging
✅ **OS**: Ubuntu 22.04.5 LTS (Jammy Jellyfish)
✅ **Package Available**: gdb-multiarch available in Ubuntu repos

❌ **CRITICAL ISSUE**: `gdb-multiarch` is NOT installed
❌ **Impact**: Cannot debug ARM binaries from x86_64 host

### Architecture Mismatch
- **Host**: x86_64 (development machine)
- **Target**: ARM EABI5 (iMX6 gateway devices)
- **Binary**: `/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1` (ARM 32-bit)
- **Required Tool**: gdb-multiarch (GDB with multi-architecture support)

### Current Debug Configuration
The `.vscode/launch.json` has **12 remote debug configurations** targeting various devices:
- 10.2.0.12:2002 (LAN 12)
- 10.2.0.13:2002 (LAN 13)
- 10.2.0.14:2002 (LAN 14)
- 10.2.0.18:2002 (LAN 18)
- 10.2.0.25:2002 (LAN 25)
- 10.2.0.179:2002 (LAN 179)
- 10.2.0.189:2002 (LAN 189)
- 192.168.0.77:2002 (LAN 77)
- 192.168.0.80:2002 (LAN 80)
- 192.168.0.147:2002 (LAN 147)
- 192.168.7.1:2002 (LAN 7.1)

All configurations specify:
```json
"miDebuggerPath": "/usr/bin/gdb-multiarch",
"miDebuggerServerAddress": "<IP>:2002",
```

### Error Symptoms
When attempting to launch debugger in Cursor/VS Code:
- ❌ "gdb-multiarch: command not found"
- ❌ Cannot connect to remote target
- ❌ Debug session fails to start

---

## Solution Plan

### Phase 1: Install gdb-multiarch

**Step 1.1: Install Package**
```bash
sudo apt-get update
sudo apt-get install -y gdb-multiarch
```

**Expected Output:**
```
Reading package lists... Done
Building dependency tree... Done
The following NEW packages will be installed:
  gdb-multiarch
[...]
Setting up gdb-multiarch (12.1-0ubuntu1~22.04.2) ...
```

**Step 1.2: Verify Installation**
```bash
gdb-multiarch --version
```

**Expected:**
```
GNU gdb (Ubuntu 12.1-0ubuntu1~22.04.2) 12.1
[...]
This GDB was configured as "--host=x86_64-linux-gnu --target=arm-linux-gnueabihf".
```

**Step 1.3: Test ARM Binary Support**
```bash
gdb-multiarch -batch -ex "file /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1" -ex "info target"
```

**Expected:**
- Should load ARM binary without errors
- Display target architecture as "arm"

---

### Phase 2: Verify Target Configuration

**Step 2.1: Verify gdbserver on Target Device**

On the target device (e.g., 10.2.0.18), gdbserver must be running:
```bash
# SSH to target
ssh root@10.2.0.18

# Check if gdbserver is installed
which gdbserver

# Check if FC-1 is running
ps aux | grep FC-1

# Start gdbserver (if not already running via systemd)
gdbserver :2002 /path/to/FC-1 [args]
```

**Alternative: Attach to Running Process**
```bash
# Find FC-1 PID
PID=$(pidof FC-1)

# Attach gdbserver
gdbserver :2002 --attach $PID
```

**Step 2.2: Verify Network Connectivity**
From development host:
```bash
# Test if target is reachable
ping -c 3 10.2.0.18

# Test if gdbserver port is open
nc -zv 10.2.0.18 2002
# Expected: "Connection to 10.2.0.18 2002 port [tcp/*] succeeded!"
```

**Step 2.3: Firewall Check**
```bash
# On target device
iptables -L -n | grep 2002
# Should allow incoming connections on port 2002
```

---

### Phase 3: Test Remote Debugging

**Step 3.1: Manual GDB Connection Test**
```bash
# From development host
gdb-multiarch /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1

# In GDB:
(gdb) target remote 10.2.0.18:2002
(gdb) info threads
(gdb) bt
(gdb) quit
```

**Expected:**
```
Remote debugging using 10.2.0.18:2002
[Thread debugging using libthread_db enabled]
[New Thread 0x76f5a460 (LWP 1234)]
[New Thread 0x76d59460 (LWP 1235)]
[...]
```

**Step 3.2: Test in Cursor/VS Code**
1. Open Fleet-Connect-1 project in Cursor
2. Set breakpoint in source file (e.g., `linux_gateway.c:main()`)
3. Select debug configuration: "LAN 18 iMatrix Fleet Connect Gateway App"
4. Press F5 or click "Start Debugging"
5. Verify:
   - ✅ Debug console shows "Connected to remote target"
   - ✅ Breakpoint is hit
   - ✅ Can inspect variables
   - ✅ Can step through code

---

### Phase 4: Troubleshooting

#### Issue: "Cannot connect to remote target"

**Possible Causes:**
1. gdbserver not running on target
2. Firewall blocking port 2002
3. Wrong IP address in launch.json
4. Target binary different from host binary (version mismatch)

**Solutions:**
```bash
# On target:
sudo systemctl status gdbserver  # Check if systemd service exists
sudo iptables -A INPUT -p tcp --dport 2002 -j ACCEPT  # Open port
netstat -tulpn | grep 2002  # Verify listening

# On host:
telnet 10.2.0.18 2002  # Test raw connection
```

#### Issue: "No symbol table is loaded"

**Cause:** Binary on host doesn't match binary on target

**Solution:**
```bash
# Rebuild and deploy
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
make clean && make
scp FC-1 root@10.2.0.18:/usr/bin/FC-1
ssh root@10.2.0.18 'killall -9 FC-1; gdbserver :2002 /usr/bin/FC-1'
```

#### Issue: "Warning: Cannot insert breakpoint"

**Cause:** Position-independent code (PIE) or Address Space Layout Randomization (ASLR)

**Solution:**
```bash
# On target:
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space  # Disable ASLR temporarily
```

#### Issue: SIGUSR1 Interrupts Debugging

**Already Handled:** launch.json includes:
```json
"setupCommands": [
    {
        "text": "-q -exec handle SIGUSR1 nostop -exec handle SIGUSR1 noprint",
        "ignoreFailures": true
    }
]
```

---

## Implementation Checklist

### Pre-Implementation
- [x] Identify root cause (gdb-multiarch missing)
- [x] Verify binary has debug symbols
- [x] Verify launch.json configuration
- [ ] **Install gdb-multiarch**

### Installation Phase
- [ ] Run `sudo apt-get update`
- [ ] Run `sudo apt-get install -y gdb-multiarch`
- [ ] Verify installation with `gdb-multiarch --version`
- [ ] Test loading ARM binary

### Target Verification Phase
- [ ] SSH to target device (e.g., 10.2.0.18)
- [ ] Verify gdbserver installed
- [ ] Check if FC-1 process running
- [ ] Start gdbserver on port 2002 (or verify it's running)
- [ ] Test network connectivity from host
- [ ] Test port 2002 accessibility

### Testing Phase
- [ ] Manual GDB connection test
- [ ] Launch debugger in Cursor
- [ ] Set breakpoint
- [ ] Start debugging session
- [ ] Verify breakpoint hit
- [ ] Test variable inspection
- [ ] Test step-through debugging

### Documentation Phase
- [ ] Document working setup
- [ ] Create troubleshooting guide for team
- [ ] Update project README with debug instructions

---

## Quick Start Guide (Post-Installation)

### For New Team Members

**1. Install Prerequisites:**
```bash
sudo apt-get update
sudo apt-get install -y gdb-multiarch
```

**2. Verify Binary Built with Debug Symbols:**
```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
file FC-1  # Should show "with debug_info, not stripped"
```

**3. Start gdbserver on Target:**
```bash
# SSH to target
ssh root@<target-ip>

# Option A: Start with gdbserver
gdbserver :2002 /usr/bin/FC-1

# Option B: Attach to running process
gdbserver :2002 --attach $(pidof FC-1)
```

**4. Debug in Cursor:**
- Open project in Cursor
- Select appropriate target from debug dropdown (e.g., "LAN 18")
- Set breakpoints
- Press F5

---

## Configuration Files Reference

### Current launch.json Location
```
/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/.vscode/launch.json
```

### Configuration Template
```json
{
    "name": "Remote ARM Debugging",
    "type": "cppdbg",
    "request": "launch",
    "program": "${workspaceFolder}/build/FC-1",
    "miDebuggerServerAddress": "<target-ip>:2002",
    "miDebuggerPath": "/usr/bin/gdb-multiarch",
    "args": [],
    "stopAtEntry": false,
    "cwd": "${workspaceFolder}",
    "environment": [],
    "externalConsole": false,
    "MIMode": "gdb",
    "setupCommands": [
        {
            "description": "Ignore SIGUSR1 signals",
            "text": "-q -exec handle SIGUSR1 nostop -exec handle SIGUSR1 noprint",
            "ignoreFailures": true
        }
    ]
}
```

---

## Additional Enhancements (Optional)

### Enhanced Debug Configuration with Logging

Add to launch.json configurations:
```json
{
    "logging": {
        "engineLogging": true,
        "trace": true,
        "traceResponse": true
    },
    "sourceFileMap": {
        "/home/greg/iMatrix/iMatrix_Client": "${workspaceFolder}"
    }
}
```

### GDB Init File for Convenience

Create `~/.gdbinit`:
```gdb
# Pretty printing
set print pretty on
set print array on
set print array-indexes on

# History
set history save on
set history size 10000

# Auto-load safe path
add-auto-load-safe-path /home/greg/iMatrix/iMatrix_Client

# ARM-specific
set architecture arm
```

---

## Success Criteria

1. ✅ gdb-multiarch installed and working
2. ✅ Can load ARM binary in gdb-multiarch
3. ✅ Can connect to remote target
4. ✅ Can set and hit breakpoints
5. ✅ Can inspect variables and memory
6. ✅ Can step through code (step in/over/out)
7. ✅ SIGUSR1 handled correctly (not interrupting debug)

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **gdbserver not on target** | High | Medium | Install via `apt-get install gdbserver` on target |
| **Binary version mismatch** | High | Low | Always rebuild and redeploy before debugging |
| **Network connectivity issues** | High | Low | Verify with ping and nc before debugging |
| **Firewall blocking port** | Medium | Low | Document firewall rules, add to setup guide |
| **ASLR interferes with breakpoints** | Medium | Low | Disable ASLR on target during debug sessions |

---

## Time Estimates

- **Installation**: 5 minutes
- **Target verification**: 10 minutes
- **Testing**: 15 minutes
- **Documentation**: 10 minutes
- **Total**: ~40 minutes

---

## References

- **GDB Manual**: https://sourceware.org/gdb/documentation/
- **Remote Debugging Guide**: https://sourceware.org/gdb/onlinedocs/gdb/Remote-Debugging.html
- **VS Code C++ Debugging**: https://code.visualstudio.com/docs/cpp/cpp-debug
- **gdbserver Documentation**: https://sourceware.org/gdb/onlinedocs/gdb/Server.html

---

## Next Steps

**IMMEDIATE ACTION REQUIRED:**

```bash
# Run this command to fix the debugger:
sudo apt-get update && sudo apt-get install -y gdb-multiarch

# Verify:
gdb-multiarch --version

# Test connection (replace with your target IP):
ping -c 3 10.2.0.18
nc -zv 10.2.0.18 2002
```

Once gdb-multiarch is installed, the Cursor debugger will work immediately with the existing launch.json configuration.

---

**Status**: READY TO IMPLEMENT
**Blocking Issue**: gdb-multiarch not installed
**Solution**: Single package installation
**Effort**: <5 minutes
