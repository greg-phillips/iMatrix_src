# Add Debug Subcommands for CAN, Network, and CoAP

**Date:** 2025-12-26
**Branch:** feature/add_debug_modes
**Starting Branch:** Aptera_1_Clean (both iMatrix and Fleet-Connect-1)
**Status:** Implemented - Ready for Testing

---

## Overview

Add three new debug CLI subcommands that enable multiple related debug flags at once:
- `debug can` - Enable all CAN bus related debug flags
- `debug network` - Enable all network subsystem debug flags
- `debug coap` - Enable all CoAP protocol debug flags

Each command will also support an `off` variant to disable the group flags.

---

## Design Decisions

1. **Additive Mode**: Commands add flags to existing settings (OR operation), matching existing `debug +0x...` behavior
2. **Off Variants**: Include `debug can off`, `debug network off`, `debug coap off` to remove flags
3. **Exact Hex Values**: Use the exact hex values specified in the YAML spec for consistency with documentation

---

## Flag Definitions

### CAN Subsystem Flags (9 flags)
| Flag | Hex Value | Description |
|------|-----------|-------------|
| DEBUGS_FOR_CANBUS | 0x0000020000000000 | CAN Bus |
| DEBUGS_FOR_CANBUS_DATA | 0x0000040000000000 | CAN Bus Data |
| DEBUGS_FOR_CANBUS_SAMPLE | 0x0000080000000000 | CAN Bus Sample |
| DEBUGS_FOR_CANBUS_EVENT | 0x0000100000000000 | CAN Bus Event |
| DEBUGS_CAN_REGISTRATION | 0x0000200000000000 | CAN Registration |
| DEBUGS_CAN_DECODE_DEBUG | 0x0000400000000000 | CAN Decode |
| DEBUGS_CAN_DECODE_ERROR | 0x0000800000000000 | CAN Decode Errors |
| DEBUGS_FOR_CAN_SERVER | 0x0001000000000000 | CAN TCP Server |
| DEBUGS_FOR_CAN_ETH_FRAME | 0x0002000000000000 | CAN Ethernet Frame parsing |

**Combined CAN mask:** `0x0003FE0000000000`

### Network Subsystem Flags (6 flags)
| Flag | Hex Value | Description |
|------|-----------|-------------|
| DEBUGS_FOR_WIFI | 0x0000000000020000 | Wi-Fi Connections |
| DEBUGS_FOR_ETH0_NETWORKING | 0x0000000000040000 | ETH0 Networking |
| DEBUGS_FOR_WIFI0_NETWORKING | 0x0000000000080000 | WIFI0 Networking |
| DEBUGS_FOR_PPP0_NETWORKING | 0x0000000000100000 | PPP0 Networking |
| DEBUGS_FOR_NETWORKING_SWITCH | 0x0000000000200000 | Networking Switch |
| DEBUGS_FOR_CELLUAR | 0x0000000800000000 | Cellular |

**Combined Network mask:** `0x00000008003E0000`

### CoAP Subsystem Flags (4 flags)
| Flag | Hex Value | Description |
|------|-----------|-------------|
| DEBUGS_FOR_XMIT | 0x0000000000000002 | CoAP Xmit |
| DEBUGS_FOR_RECV | 0x0000000000000004 | CoAP Recv |
| DEBUGS_FOR_COAP_DEFINES | 0x0000000000000008 | CoAP Support Routines |
| DEBUGS_FOR_UDP | 0x0000000000000010 | UDP transport |

**Combined CoAP mask:** `0x000000000000001E`

### CAN Server Flags (5 flags - subset of CAN for server/decode debugging)
| Flag | Hex Value | Description |
|------|-----------|-------------|
| DEBUGS_FOR_CANBUS_EVENT | 0x0000100000000000 | CAN Bus Event |
| DEBUGS_CAN_DECODE_DEBUG | 0x0000400000000000 | CAN Decode |
| DEBUGS_CAN_DECODE_ERROR | 0x0000800000000000 | CAN Decode Errors |
| DEBUGS_FOR_CAN_SERVER | 0x0001000000000000 | CAN TCP Server |
| DEBUGS_FOR_CAN_ETH_FRAME | 0x0002000000000000 | CAN Ethernet Frame parsing |

**Combined CAN Server mask:** `0x0003D00000000000`

---

## Implementation Plan

### Files to Modify

1. **iMatrix/cli/cli_debug.c** - Add subcommand handling

### Code Changes

Add handling in `cli_debug()` function for the new subcommands:
- Parse "can", "network", "coap" tokens
- Check for optional "off" argument
- Apply OR (add) or AND-NOT (remove) operation to `device_config.log_messages`

### New CLI Syntax

```bash
debug can              # Add all CAN debug flags
debug can off          # Remove all CAN debug flags
debug canserver        # Add CAN server/decode debug flags
debug canserver off    # Remove CAN server/decode debug flags
debug network          # Add all network debug flags
debug network off      # Remove all network debug flags
debug coap             # Add all CoAP debug flags
debug coap off         # Remove all CoAP debug flags
```

---

## Todo List

- [x] Create plan document
- [x] Create feature branch in iMatrix submodule
- [x] Implement debug subcommands in cli_debug.c
- [x] Build and verify no compile errors or warnings
- [ ] Test the new debug subcommands (on target hardware)
- [x] Update help text for debug command (included in `debug ?` output)

---

## Testing Plan

1. Build Fleet-Connect-1 with changes
2. Run and verify:
   - `debug can` adds all CAN flags
   - `debug can off` removes all CAN flags
   - `debug network` adds all network flags
   - `debug network off` removes all network flags
   - `debug coap` adds all CoAP flags
   - `debug coap off` removes all CoAP flags
   - Existing debug commands still work
   - `debug ?` shows all flags correctly

---

---

## Implementation Summary

**Completed:** 2025-12-26

### Changes Made

**File Modified:** `iMatrix/cli/cli_debug.c`

1. Added macro definitions for combined debug flag masks:
   - `DEBUG_CAN_FLAGS` (0x0003FE0000000000ULL) - 9 CAN flags
   - `DEBUG_CANSERVER_FLAGS` (0x0003D00000000000ULL) - 5 CAN server/decode flags
   - `DEBUG_NETWORK_FLAGS` (0x00000008003E0000ULL) - 6 network flags
   - `DEBUG_COAP_FLAGS` (0x000000000000001EULL) - 4 CoAP flags

2. Added handling in `cli_debug()` for new subcommands:
   - `debug can` / `debug can off`
   - `debug canserver` / `debug canserver off`
   - `debug network` / `debug network off`
   - `debug coap` / `debug coap off`

3. Updated `debug ?` help output to show subsystem shortcuts

### Build Verification
- Build completed successfully with no errors
- No warnings related to the changes
- Binary size: ~13MB (unchanged from baseline)

### Metrics
- Files modified: 1
- Lines added: ~80
- Build time: ~30 seconds (incremental)

---

**Plan Created By:** Claude Code
**Generated:** 2025-12-26
