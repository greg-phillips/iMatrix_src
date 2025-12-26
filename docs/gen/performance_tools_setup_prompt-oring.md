<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/performance_tools_setup.yaml
Generated on: 2025-12-21
Schema version: 1.0
Complexity level: moderate
Auto-populated sections: project structure, hardware defaults, user info, guidelines

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim Setup Performance Tools

**Date:** 2025-12-21
**Branch:** feature/performance-tools-setup
**Objective:** Setup Performance Tools for the project

---

## Code Structure:

**iMatrix (Core Library):** Contains all core telematics functionality (data logging, comms, peripherals).

**Fleet-Connect-1 (Main Application):** Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

**Additional Context:**
This feature is to setup the performance tools for the iMatrix Fleet-Connect-1 project.

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH.
The wifi communications uses a combination Wi-Fi/Bluetooth chipset.
The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.

**Hardware Notes:**
- Limited to LINUX_PLATFORM only

The user's name is Greg.

Read and understand the following:

- docs/Fleet-Connect-1_architecture.md

Source files to review:
- iMatrix
- Fleet-Connect-1

Use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Code runs on embedded system.

Always create extensive comments using doxygen style.

**Use the KISS principle - do not over-engineer. Keep it simple and maintainable.**

---

## Task

### CONTEXT / FACTS
- Target: BusyBox Linux on NXP i.MX6 (ARM).
- App is already compiled WITH debug symbols.
- App is run with the command EXACTLY: /home/FC-1 (do not rename or move it).
- All profiler scripts, tooling, build outputs, and docs MUST live in:
  `~/iMatrix/iMatrix_Client/Profiler`
- Goal: create a complete, repeatable profiling toolkit (host + target deploy) for FC-1:
  CPU, scheduling, memory, IO, network; perf if possible, ftrace fallback if not.

### HARD REQUIREMENT: DIRECTORY + FILE PLACEMENT
Work ONLY under:
```
~/iMatrix/iMatrix_Client/Profiler
```
If the directory doesn't exist, create it.
Do NOT scatter files elsewhere in the repo.
All outputs must be relative to this Profiler directory:
```
~/iMatrix/iMatrix_Client/Profiler/{scripts,docs,artifacts,build,tools}
```

### DELIVERABLES (MUST CREATE EXACTLY THESE FILES UNDER Profiler/)
Create these files:
1. `~/iMatrix/iMatrix_Client/Profiler/scripts/target_discover.sh`
2. `~/iMatrix/iMatrix_Client/Profiler/scripts/verify_fc1.sh`
3. `~/iMatrix/iMatrix_Client/Profiler/scripts/install_tools_target.sh`
4. `~/iMatrix/iMatrix_Client/Profiler/scripts/build_tools_host.sh`
5. `~/iMatrix/iMatrix_Client/Profiler/scripts/deploy_tools.sh`
6. `~/iMatrix/iMatrix_Client/Profiler/scripts/setup_fc1_service.sh`
7. `~/iMatrix/iMatrix_Client/Profiler/scripts/profile_fc1.sh`
8. `~/iMatrix/iMatrix_Client/Profiler/scripts/grab_profiles.sh`
9. `~/iMatrix/iMatrix_Client/Profiler/docs/FC1_Profiling_On_Target.md`
10. `~/iMatrix/iMatrix_Client/Profiler/README.md`

All scripts must be POSIX sh (no bashisms), safe (set -eu), and heavily commented.
Scripts must print clear status messages and skip unsupported actions with an explanation.

### REQUIRED DIRECTORY STRUCTURE (CREATE IT)
```
Profiler/
  scripts/
  docs/
  artifacts/
    target_reports/
    profiles/
    logs/
  build/
    target_tools/
  tools/
    bin/               (optional host helper bins)
    manifests/
```

---

### A) TARGET DISCOVERY

Implement `scripts/target_discover.sh` so I can run from the Profiler directory:
```sh
./scripts/target_discover.sh user@target
```

It should SSH in and collect:
- `uname -a`
- `/etc/os-release` (if present)
- BusyBox version (`busybox | head -n 1`, etc.)
- arch + libc hints (`uname -m`; `ldd --version` if present; `/lib/libc*` heuristics)
- kernel perf_event hints:
  - `/proc/config.gz` if present (grep PERF_EVENT, FTRACE)
  - `/sys/kernel/debug/tracing` presence (if readable)
  - attempt a harmless perf probe ONLY if perf exists
- tool availability: perf, strace, ltrace, gdbserver, tcpdump, ethtool, ip, ss/netstat, top, ps
- package manager detection: opkg/apk/apt/yum/dnf/none
- init/service detection: /etc/sv (runit), /etc/init.d, systemd
- CPU info: /proc/cpuinfo, core count, cpufreq governor paths if exist
- memory/storage: /proc/meminfo, df -h, mount
- network: ip addr, ip route, ip -s link, /proc/net/dev

Save locally as:
```
artifacts/target_reports/target_report_<host>_<timestamp>.txt
```
Also echo a short summary to stdout.

---

### B) VERIFY FC-1 EXISTS AND IS EXECUTABLE

Implement `scripts/verify_fc1.sh`:
```sh
./scripts/verify_fc1.sh user@target
```

It must:
- Check `/home/FC-1` exists and is executable.
- Capture:
  - `ls -l /home/FC-1`
  - if available: `file /home/FC-1`
  - if available: `readelf -h /home/FC-1` (or `strings | head` fallback)
- Save locally:
  ```
  artifacts/target_reports/fc1_verify_<host>_<timestamp>.txt
  ```
- If missing, exit non-zero with clear next steps.

---

### C) INSTALL TOOLS ON TARGET (IF PACKAGE MANAGER EXISTS)

Implement `scripts/install_tools_target.sh`:
```sh
./scripts/install_tools_target.sh user@target
```

It must:
- Detect opkg/apk/apt and attempt installs of (as available):
  strace, tcpdump, ethtool, iperf3, procps, sysstat, lsof
  and perf if available in that distro.
- Print what succeeded and what did not.
- If no package manager OR important tools missing, exit with code 2 and instruct to run host-build path.

---

### D) HOST BUILD FALLBACK (NO PACKAGE MANAGER OR MISSING TOOLS)

Implement `scripts/build_tools_host.sh`:
```sh
./scripts/build_tools_host.sh user@target
```

It must:
- Determine target arch via ssh (`uname -m`) and map:
  - armv7l/armv6* => armhf toolchain
  - aarch64 => aarch64 toolchain
- Build (or fetch + build) deployable binaries into:
  ```
  build/target_tools/<arch>/{bin,lib}
  ```
- Priority:
  1. strace
- Optional (best-effort):
  - iperf3
  - tcpdump (note libpcap dependency; if too heavy, skip cleanly)
  - ethtool
  - gdbserver (optional)
- Perf:
  - DO NOT pretend perf works.
  - Only attempt perf build if a matching kernel tools/perf source is available and feasible.
  - Otherwise: explicitly plan to use ftrace + /proc sampling in profile_fc1.sh.

Must generate a manifest:
```
tools/manifests/target_tools_<arch>_<timestamp>.txt
```
with checksums for produced binaries.

---

### E) DEPLOY TOOLS TO TARGET

Implement `scripts/deploy_tools.sh`:
```sh
./scripts/deploy_tools.sh user@target
```

It must:
- Deploy host-built tools from `build/target_tools/<arch>/bin` to:
  - Prefer: `/opt/fc-1-tools/bin` (if root writable)
  - Fallback: `/home/<user>/fc-1-tools/bin`
- Print PATH export instructions that the user can run in the session:
  ```sh
  export PATH=/opt/fc-1-tools/bin:$PATH
  ```
  (or fallback path)
- Verify deployed tools run (e.g., `strace -V`) and log results.

Log locally:
```
artifacts/logs/deploy_tools_<host>_<timestamp>.txt
```

---

### F) SERVICE SETUP FOR /home/FC-1 (NO MOVING THE BINARY)

Implement `scripts/setup_fc1_service.sh`:
```sh
./scripts/setup_fc1_service.sh user@target
```

It must:
- Always run FC-1 as `/home/FC-1`
- Create runtime dirs:
  - Prefer (if writable):
    - `/var/log/fc-1/`
    - `/var/log/fc-1/profiles/`
    - `/var/run/fc-1/`
  - Fallback (no root):
    - `/home/<user>/fc-1-logs/`
    - `/home/<user>/fc-1-profiles/`
    - `/home/<user>/fc-1-run/`
- Service options:
  1. If runit present (`/etc/sv`): create `/etc/sv/FC-1/run` that execs `/home/FC-1`
     - redirect stdout/stderr to a log file if no runit logger service
  2. Else if `/etc/init.d` present: install init script
  3. Else if systemd present: install a unit
  4. Else (no root): create userland wrappers:
     - `/home/<user>/fc1_run.sh` (nohup /home/FC-1 > ... 2>&1 &; write pidfile)
     - `/home/<user>/fc1_stop.sh`
     - `/home/<user>/fc1_status.sh`

Must print exact start/stop/status commands for the detected mode.

---

### G) PROFILING RUN + ARTIFACTS

Implement `scripts/profile_fc1.sh`:
```sh
./scripts/profile_fc1.sh user@target [--duration 60] [--no-tcpdump]
```

It must:
- Create a timestamped profile directory on target:
  - Prefer: `/var/log/fc-1/profiles/<timestamp>/`
  - Fallback: `/home/<user>/fc-1-profiles/<timestamp>/`
- Capture baseline:
  uname, mounts, df, meminfo, cpuinfo, interrupts,
  ip addr/route, ip -s link, /proc/net/dev,
  dmesg tail (if permitted), clock source (if available)
- Find FC-1 PID robustly:
  - `pidof FC-1`
  - `pgrep -f "/home/FC-1"`
  - `ps | grep` fallback
- Collect interval snapshots (every ~2s or 5s) during duration:
  - `top -b -n 1` (if available)
  - ps output
  - `/proc/<pid>/status`, `/proc/<pid>/stat`, `/proc/<pid>/io` (if exists)
  - `/proc/diskstats` sampling
- Profiling:
  1. **strace summary:**
     - Prefer: `strace -c -p <pid> -o strace_summary.txt -T -tt` for duration (handle attach permission failures)
     - If cannot attach: optionally run `/home/FC-1` under strace for a short controlled run only IF safe; otherwise skip.
  2. **perf (ONLY IF VERIFIED):**
     - If `perf stat true` works, run perf stat for duration and capture output.
     - If `perf record` works, do a short record window and save perf.data.
  3. **ftrace fallback:**
     - If `/sys/kernel/debug/tracing` is accessible, use function_graph for a short window and save trace.
     - If not accessible, clearly state not available.
  4. **network:**
     - `ss -s` or `netstat` summary
     - optional tcpdump short capture unless `--no-tcpdump`
- Bundle:
  Create `profile_bundle_<timestamp>.tar.gz` in the profile directory.

---

### H) GRAB PROFILES BACK TO HOST

Implement `scripts/grab_profiles.sh`:
```sh
./scripts/grab_profiles.sh user@target
```

It must:
- Locate newest `profile_bundle_*.tar.gz` on the target (in both preferred and fallback locations)
- SCP it back to:
  ```
  artifacts/profiles/<host>/<timestamp>.tar.gz
  ```
- Print the local path of the downloaded bundle.

---

### I) DOCUMENTATION

Create:
- `docs/FC1_Profiling_On_Target.md` (complete how-to)
- `README.md` (quickstart)

Quickstart in README.md must be exactly (with placeholders):
```sh
cd ~/iMatrix/iMatrix_Client/Profiler
TARGET=user@192.168.x.x
./scripts/target_discover.sh "$TARGET"
./scripts/verify_fc1.sh "$TARGET"
./scripts/install_tools_target.sh "$TARGET" || true
# If install_tools_target.sh exits 2, do:
./scripts/build_tools_host.sh "$TARGET"
./scripts/deploy_tools.sh "$TARGET"
./scripts/setup_fc1_service.sh "$TARGET"
./scripts/profile_fc1.sh "$TARGET" --duration 60
./scripts/grab_profiles.sh "$TARGET"
```

---

### IMPLEMENTATION RULES
- Do not ask me questions unless absolutely required; auto-detect wherever possible.
- Use ssh with strict options (BatchMode, ConnectTimeout).
- Never claim perf works unless scripts verify it on the target.
- Keep everything deterministic and runnable from the Profiler directory.

---

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/performance_tools_setup_prompt.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** docs/prompt_work/performance_tools_setup.yaml
**Generated:** 2025-12-21
**Auto-populated:** 4 sections
