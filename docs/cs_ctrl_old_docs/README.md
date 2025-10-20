# iMatrix Memory Manager v2.8 (MM2) - Documentation Index

## Overview

This directory contains comprehensive documentation for the iMatrix Memory Manager v2.8 (MM2), a complete replacement for the legacy memory manager. MM2 achieves 75% space efficiency through separated chain management and supports both Linux and STM32 platforms.

## Documentation Files

### 1. MM2_TECHNICAL_DOCUMENTATION.md (41KB)
**Complete API Reference and Architecture Guide**

Covers:
- System overview and design principles
- All data structures with field descriptions
- Complete public API function signatures
- Internal implementation functions
- System workflows and state machines
- Platform-specific implementations
- Disk spooling subsystem
- Power management
- Compatibility layer
- Structural issues and recommendations

**Audience**: Developers, architects, code reviewers

### 2. MM2_IMPLEMENTATION_GUIDE.md (31KB)
**Practical Usage and Integration**

Contains:
- Quick start examples
- Common usage patterns (TSD, EVT, multi-source)
- Memory efficiency calculations with mathematical proofs
- Detailed code walkthroughs
- Error handling patterns
- Testing strategies with examples
- Integration examples
- Best practices and anti-patterns

**Audience**: Application developers, integrators

### 3. MM2_TROUBLESHOOTING_GUIDE.md (27KB)
**Debugging and Problem Resolution**

Includes:
- Common issues with step-by-step solutions
- Advanced debugging techniques
- Error code reference table
- Platform-specific problem resolution
- Performance problem diagnosis
- Data corruption investigation
- Memory leak detection
- Automated diagnostic tools

**Audience**: Support engineers, testers, field engineers

### 4. MM2_API_QUICK_REFERENCE.md (11KB)
**Cheat Sheet and Quick Lookup**

Features:
- All API functions with signatures
- Upload source enumeration
- Return code meanings
- Key data structures
- Typical usage pattern
- Platform differences table
- Memory efficiency formulas
- Common pitfalls
- Performance tips

**Audience**: All developers (quick reference)

### 5. MM2_BUILD_FIXES.md (4.8KB)
**Build Error Resolutions (2025-10-12)**

Documents:
- Multiple definition conflict fix
- Missing power management function stubs
- File locations and changes
- Verification steps

**Audience**: Build engineers, CI/CD maintainers

### 6. MM2_LEGACY_CLEANUP.md (6.8KB)
**Migration Status and Cleanup (2025-10-12)**

Details:
- Files removed (v1 backup directory)
- Files retained (MM2 core + compatibility)
- Architecture diagram
- Migration status
- Remaining work
- Recommendations

**Audience**: Project managers, migration team

---

## Quick Start

1. **New to MM2?** Start with `MM2_API_QUICK_REFERENCE.md`
2. **Implementing integration?** Read `MM2_IMPLEMENTATION_GUIDE.md`
3. **Need full details?** Consult `MM2_TECHNICAL_DOCUMENTATION.md`
4. **Debugging issues?** Use `MM2_TROUBLESHOOTING_GUIDE.md`
5. **Build problems?** Check `MM2_BUILD_FIXES.md`

---

## MM2 vs Legacy Memory Manager

### Key Improvements
- **75% space efficiency** (vs 62.5% in legacy)
- **Upload source segregation** (multi-path uploads)
- **Separated chain management** (metadata separate from data)
- **Platform-aware design** (Linux with disk, STM32 RAM-only)
- **Power-safe operations** (abort recovery, atomic writes)
- **Better statistics** (comprehensive tracking)

### Migration Status
- ✅ MM2 implementation complete (v2.8)
- ✅ Build errors resolved
- ✅ Legacy v1 backup removed
- ✅ Compatibility layer active
- ⚠️ Fleet-Connect-1 has 16 legacy API calls (migration needed)

### Files Structure

```
iMatrix/cs_ctrl/
├── docs/                           ← Documentation (you are here)
│   ├── README.md                   ← This file
│   ├── MM2_TECHNICAL_DOCUMENTATION.md
│   ├── MM2_IMPLEMENTATION_GUIDE.md
│   ├── MM2_TROUBLESHOOTING_GUIDE.md
│   ├── MM2_API_QUICK_REFERENCE.md
│   ├── MM2_BUILD_FIXES.md
│   └── MM2_LEGACY_CLEANUP.md
│
├── MM2 Core Implementation (17 files)
│   ├── mm2_api.c/h                 ← Public API
│   ├── mm2_core.h                  ← Data structures
│   ├── mm2_internal.h              ← Internal functions
│   ├── mm2_pool.c                  ← Memory pool
│   ├── mm2_write.c                 ← Write operations
│   ├── mm2_read.c                  ← Read operations
│   ├── mm2_disk*.c/h               ← Disk spooling (Linux)
│   ├── mm2_file_management.c       ← File lifecycle
│   ├── mm2_startup_recovery.c      ← Recovery
│   ├── mm2_power.c                 ← Power management
│   ├── mm2_power_abort.c           ← Abort recovery
│   └── mm2_stm32.c                 ← STM32 specific
│
├── Compatibility Bridge (4 files)
│   ├── mm2_compatibility.c         ← Legacy API stubs
│   ├── memory_manager.h            ← Type mappings
│   ├── memory_manager_stats.c/h    ← CLI wrappers
│   └── cs_memory_mgt.c/h           ← Sensor init (uses MM2)
│
└── Testing Framework (4 files)
    ├── memory_test_framework.c/h
    └── memory_test_suites.c/h
```

---

## Support and Contribution

### Reporting Issues
- Document issue with reproduction steps
- Include platform (Linux/STM32)
- Provide memory statistics output
- Include relevant log excerpts

### Contributing
- Follow existing code style
- Add Doxygen comments for all functions
- Update documentation for API changes
- Include tests for new features

### Contact
For questions about MM2:
- Review documentation first
- Check troubleshooting guide
- Consult API quick reference
- Review implementation examples

---

## Version History

**v2.8** (2025-10-12)
- Complete MM2 implementation
- Build error fixes
- Legacy v1 backup removed
- Comprehensive documentation (120KB across 6 files)

**v2.0** (2025-10-07)
- Initial MM2 development
- 75% efficiency achieved
- Platform abstraction implemented

**v1.x** (Legacy)
- Original memory manager
- Now fully replaced by MM2

---

## Quick Reference

### Include Headers
```c
#include "mm2_api.h"           // For MM2 direct usage
#include "memory_manager.h"    // For compatibility mode
```

### Basic Usage
```c
// Initialize
imx_memory_manager_init(0);

// Configure sensor
imx_configure_sensor(IMX_UPLOAD_TELEMETRY, &csb, &csd);
imx_activate_sensor(IMX_UPLOAD_TELEMETRY, &csb, &csd);

// Write
imx_data_32_t value = {.float_32bit = 23.5f};
imx_write_tsd(IMX_UPLOAD_TELEMETRY, &csb, &csd, value);

// Read
tsd_evt_value_t samples[100];
uint16_t filled;
imx_read_bulk_samples(IMX_UPLOAD_TELEMETRY, &csb, &csd,
                     samples, 100, 100, &filled);

// Upload & ACK
if (upload_success) {
    imx_erase_all_pending(IMX_UPLOAD_TELEMETRY, &csb, &csd, filled);
}
```

### Diagnostics
```c
// Memory stats
mm2_stats_t stats;
imx_get_memory_stats(&stats);

// Validate chains
imx_validate_sector_chains(IMX_UPLOAD_TELEMETRY, &csb, &csd);
```

---

## Documentation Metrics

| Document | Size | Sections | Audience |
|----------|------|----------|----------|
| Technical Documentation | 41KB | 10 | Developers, Architects |
| Implementation Guide | 31KB | 8 | Application Developers |
| Troubleshooting Guide | 27KB | 8 | Support Engineers |
| API Quick Reference | 11KB | 1 | All Developers |
| Build Fixes | 4.8KB | 3 | Build Engineers |
| Legacy Cleanup | 6.8KB | 4 | Migration Team |
| **Total** | **120KB** | **34** | **All Roles** |

---

**Last Updated**: 2025-10-12
**MM2 Version**: 2.8
**Documentation Status**: Complete
**Migration Status**: Compatibility layer active
