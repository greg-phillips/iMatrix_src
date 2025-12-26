<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/performance_tools_setup.yaml
Generated on: 2025-12-21
Schema version: 1.0
Complexity level: moderate
Auto-populated sections: project structure, hardware defaults, guidelines

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Setup Performance Tools for Fleet-Connect-1

**Date:** 2025-12-21
**Branch:** feature/performance-tools-setup
**Objective:** Create a complete, repeatable profiling toolkit for FC-1 on embedded BusyBox Linux

---

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

This feature creates performance profiling tools for the iMatrix Fleet-Connect-1 project.
Tools are cross-compiled on WSL (host) and transferred to the BusyBox embedded target.

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an NXP i.MX6 (ARM Cortex-A9) processor with 512MB RAM and 512MB FLASH.

Additional hardware notes:
- Limited to LINUX_PLATFORM only
- Target runs BusyBox Linux (minimal userland)
- ARM architecture (armv7l/armhf)
- Cross-compilation required from WSL host

The user's name is Greg

Read and understand the following:

- docs/Fleet-Connect-1_architecture.md
- Profiler/README.md (to be created)

Source files to review:
- Profiler/scripts/ - focus on: build_tools_host.sh, deploy_tools.sh, profile_fc1.sh
- Fleet-Connect-1

Use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Code runs on embedded system from: /home
Binary: /home/FC-1
Platform: BusyBox Linux on NXP i.MX6

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

## Task

### Summary
Build profiling tools on WSL and deploy to BusyBox embedded target

### Description
Create a complete profiling toolkit that:
1. Builds tools on WSL Ubuntu (host development environment)
2. Cross-compiles for ARM (i.MX6 target)
3. Transfers compiled binaries to BusyBox embedded system
4. Enables CPU, memory, IO, and network profiling of /home/FC-1

Target: BusyBox Linux on NXP i.MX6 (ARM)
Host: WSL Ubuntu (this system)
App: /home/FC-1 (compiled WITH debug symbols, do not rename or move)

All profiler scripts, tooling, build outputs, and docs live in:
  ~/iMatrix/iMatrix_Client/Profiler

### Requirements
1. Cross-compile strace for ARM (priority tool)
2. Cross-compile optional tools: iperf3, tcpdump, ethtool, gdbserver
3. Use ARM cross-compiler toolchain on WSL host
4. Deploy binaries to /opt/fc-1-tools/bin on target (or fallback path)
5. All scripts must be POSIX sh (no bashisms)
6. Scripts must use set -eu for safety
7. Generate manifest with checksums for all built binaries
8. Support both perf (if available) and ftrace fallback

### Implementation Notes
- Use /opt/qconnect_sdk_musl/bin/arm-linux-* for cross-compilation
- If musl toolchain unavailable, try arm-linux-gnueabihf-gcc from apt
- strace requires kernel headers for target architecture
- tcpdump depends on libpcap - may be complex, skip if too heavy
- perf requires matching kernel source - only attempt if kernel tools available
- ftrace via /sys/kernel/debug/tracing is the reliable fallback

### Detailed Specifications

#### WSL Host Build Environment

Prerequisites on WSL Ubuntu:
1. ARM cross-compiler (one of):
   - /opt/qconnect_sdk_musl/bin/arm-linux-gcc (preferred, musl-based)
   - apt install gcc-arm-linux-gnueabihf (alternative, glibc-based)

2. Build dependencies:
   sudo apt install build-essential wget tar git

3. Build directory structure:
   ```
   Profiler/
     build/
       target_tools/
         armhf/
           bin/      (compiled binaries)
           lib/      (any shared libs)
           src/      (source downloads)
   ```

#### Cross-Compilation Process

For each tool, the build_tools_host.sh script should:

1. Detect target architecture via SSH: ssh user@target "uname -m"
2. Map architecture to toolchain:
   - armv7l, armv6l => armhf toolchain
   - aarch64 => aarch64 toolchain (not expected for i.MX6)

3. Download source tarballs:
   - strace: https://github.com/strace/strace/releases
   - iperf3: https://github.com/esnet/iperf/releases
   - tcpdump: https://www.tcpdump.org/release/
   - ethtool: https://mirrors.edge.kernel.org/pub/software/network/ethtool/

4. Configure with cross-compiler:
   ```sh
   CC=/opt/qconnect_sdk_musl/bin/arm-linux-gcc \
   ./configure --host=arm-linux --prefix=/opt/fc-1-tools
   ```

5. Build static binaries where possible:
   ```sh
   LDFLAGS="-static" make
   ```

#### Transfer to Embedded Target

The deploy_tools.sh script should:

1. Create target directory:
   ```sh
   ssh user@target "mkdir -p /opt/fc-1-tools/bin" || \
   ssh user@target "mkdir -p ~/fc-1-tools/bin"
   ```

2. Transfer binaries via SCP:
   ```sh
   scp build/target_tools/armhf/bin/* user@target:/opt/fc-1-tools/bin/
   ```

3. Set executable permissions:
   ```sh
   ssh user@target "chmod +x /opt/fc-1-tools/bin/*"
   ```

4. Verify deployment:
   ```sh
   ssh user@target "/opt/fc-1-tools/bin/strace -V"
   ```

5. Print PATH export instruction:
   ```sh
   echo "Run on target: export PATH=/opt/fc-1-tools/bin:\$PATH"
   ```

#### Directory Structure

Required structure under ~/iMatrix/iMatrix_Client/Profiler:

```
Profiler/
  scripts/
    target_discover.sh      - Discover target capabilities
    verify_fc1.sh           - Verify FC-1 binary exists
    install_tools_target.sh - Install via package manager (if available)
    build_tools_host.sh     - Cross-compile on WSL host
    deploy_tools.sh         - Transfer to target
    setup_fc1_service.sh    - Configure FC-1 as service
    profile_fc1.sh          - Run profiling session
    grab_profiles.sh        - Retrieve profiles to host
  docs/
    FC1_Profiling_On_Target.md
  artifacts/
    target_reports/         - Discovery and verify reports
    profiles/               - Downloaded profile bundles
    logs/                   - Deployment logs
  build/
    target_tools/
      armhf/
        bin/                - Compiled ARM binaries
        lib/                - Shared libraries (if any)
        src/                - Downloaded source tarballs
  tools/
    manifests/              - Build manifests with checksums
```

#### Profiling Capabilities

profile_fc1.sh should capture:

1. System baseline:
   - uname, mounts, df, meminfo, cpuinfo, interrupts
   - ip addr/route, ip -s link, /proc/net/dev
   - dmesg tail, clock source

2. Process monitoring (find FC-1 PID robustly):
   - pidof FC-1
   - pgrep -f "/home/FC-1"
   - ps | grep fallback

3. Interval snapshots (every 2-5 seconds):
   - top -b -n 1 (if available)
   - ps output
   - /proc/<pid>/status, stat, io
   - /proc/diskstats

4. Profiling tools:
   a) strace -c -p <pid> (syscall summary)
   b) perf stat/record (ONLY if verified working)
   c) ftrace function_graph (fallback if /sys/kernel/debug/tracing accessible)

5. Network:
   - ss -s or netstat summary
   - tcpdump short capture (optional)

6. Bundle output as profile_bundle_<timestamp>.tar.gz

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** Profiler/docs/FC1_Profiling_On_Target.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check off the items on the todo list as they are completed.
4. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found fix them immediately.
5. **Final build verification**: Before marking work complete, perform a final clean build to verify:
   - Zero compilation errors
   - Zero compilation warnings
   - All modified files compile successfully
   - The build completes without issues
6. Once I have determined the work is completed successfully add a concise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.
8. Merge the branch back into the original branch.
9. Update all documents with relevant details

### Implementation Steps
1. Verify WSL build environment has ARM cross-compiler
2. Update build_tools_host.sh to use local WSL cross-compilation
3. Test cross-compilation of strace on WSL
4. Update deploy_tools.sh for SCP transfer workflow
5. Test full workflow: build -> deploy -> profile -> retrieve
6. Document any issues or missing tools

### Additional Deliverables
- All scripts in Profiler/scripts/ working and tested
- ARM binaries for strace (minimum) in build/target_tools/armhf/bin/
- Build manifest with checksums in tools/manifests/
- README.md with quickstart workflow

## Guidelines

### Principles
- POSIX sh only - no bashisms for portability
- Use set -eu in all scripts
- Heavily comment all scripts
- Print clear status messages
- Skip unsupported actions with explanation (don't fail silently)
- Use SSH BatchMode and ConnectTimeout for safety
- Never claim perf works unless verified on target

## Questions

### Which ARM cross-compiler to use?
**Answer:** Prefer /opt/qconnect_sdk_musl/bin/arm-linux-gcc (musl). Fallback to apt's gcc-arm-linux-gnueabihf (glibc).

### Should we build static or dynamic binaries?
**Answer:** Prefer static (LDFLAGS=-static) to avoid library dependency issues on BusyBox.

### What if perf is not available?
**Answer:** Use ftrace via /sys/kernel/debug/tracing as fallback. Never pretend perf works if untested.

### Where should tools be installed on target?
**Answer:** Prefer /opt/fc-1-tools/bin (if root). Fallback to ~/fc-1-tools/bin (non-root).

### What is the minimum required tool?
**Answer:** strace is the priority tool. Others (iperf3, tcpdump, ethtool, gdbserver) are optional best-effort.

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** docs/prompt_work/performance_tools_setup.yaml
**Generated:** 2025-12-21
**Auto-populated:** 3 sections
