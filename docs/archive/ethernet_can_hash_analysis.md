# Ethernet CAN Hash Table Analysis

## Executive Summary

**Current Status**: Ethernet CAN buses **DO NOT have hash tables** and the infrastructure for them is **NOT YET IMPLEMENTED**.

**Critical Discovery**: There is a latent array out-of-bounds bug in `can_msg_process()` that would trigger if Ethernet CAN messages were routed to it with `canbus >= 2`.

## Current Architecture

### Physical Bus Storage (Implemented)

**Structure**: `structs.h:152`
```c
can_node_data_t can[NO_PHYSICAL_CAN_BUS];  // Only 2 elements: [0] and [1]
```

**Hash Tables**: Each element has:
```c
typedef struct can_node_data {
    uint32_t count;
    can_node_t *nodes;
    can_node_hash_table_t hash_table;  // ← Hash table for O(1) lookup
} can_node_data_t;
```

**Initialized By**: `init_can_node_hash_tables()` in `can_man.c:300-309`

### Ethernet Bus Storage (PLANNED BUT NOT IMPLEMENTED)

**Structure**: `structs.h:153-154`
```c
uint16_t no_ethernet_can_buses;           // Count (never set!)
can_node_data_t *ethernet_can_buses;      // Dynamic array (never allocated!)
```

**Status**:
- ✅ Structure members declared
- ❌ Never allocated memory
- ❌ Never initialized
- ❌ Hash tables never built
- ❌ No initialization function exists

**Evidence**: Comment in `imx_client_init.c:1006-1018`:
```c
/*
 * Allocate space for the Ethernet CAN BUS nodes
 *
 * The configuration for the Ethernet CAN nodes contains all the signals
 * for all the Ethernet CAN BUS nodes. The Alias of the actual CAN BUS is
 * stored in the Signal Alias field. The Alias is used to match the signals
 * to the correct Ethernet CAN BUS node. The code below sorts them into the
 * correct Ethernet CAN BUS node. To be used when processing the signals.
 *
 * mgs->no_ethernet_can_buses
 * for each Ethernet CAN BUS node:
 *   mgs->ethernet_can_buses[ethernet_can_bus_index].count
 *   mgs->ethernet_can_buses[ethernet_can_bus_index].nodes
 */
```

This is a **TODO comment** - the code doesn't exist!

## How Ethernet CAN Currently Works

### 1. Message Reception

**File**: `iMatrix/canbus/can_server.c`

**TCP Server** listens on `192.168.7.1:5555` and receives ASCII frames in two formats:

**PCAN Format**:
```
6D3#006E020700000000
```
- Simple: `<CAN_ID>#<data_bytes>`
- Always routes to `canbus = 2` (can_server.c:175)

**APTERA Format**:
```
(1744047259.669072) Powertrain 212#0800000000000000
```
- Format: `(timestamp) VirtualCANName CANID#DATA`
- Virtual name matched against `cb.dbc_files[]` array (can_server.c:335-351)
- Canbus calculated as: `canbus = 2 + array_index` (can_server.c:354)

### 2. Message Routing

**File**: `iMatrix/canbus/can_utils.c:576-582`

```c
} else if (quake_canbus >= 2) {
    /* Ethernet - get logical bus from thread-local (set by parser) */
    canbus = quake_canbus;        // ← Preserves canbus >= 2
    can_stats = &cb.can_eth_stats;
    can_ring = &can2_ring;        // ← Uses ethernet message pool

    PRINTF("[CAN BUS - Ethernet frame with logical bus: %d]\r\n", canbus);
}
```

**Key Point**: Message is queued with `canbus >= 2` value!

### 3. Message Processing - THE BUG!

**File**: `Fleet-Connect-1/can_process/can_man.c:752-792`

```c
imx_result_t can_msg_process(can_bus_t canbus, imx_time_t current_time, can_msg_t *msg) {
    // ...

    /* Use hash table for O(1) lookup if available */
    if (mgs.can[canbus].hash_table.initialized) {  // ← ARRAY OUT-OF-BOUNDS!
        can_node_t *node = lookup_can_node_by_id(&mgs.can[canbus].hash_table,
                                                  msg->can_id,
                                                  mgs.can[canbus].nodes);  // ← ARRAY OUT-OF-BOUNDS!
        // ...
    } else {
        /* Fallback to linear search */
        for (uint16_t i = 0; i < mgs.can[canbus].count; i++) {  // ← ARRAY OUT-OF-BOUNDS!
            if ((mgs.can[canbus].nodes[i].node_id) == (msg->can_id & 0x7FFFFFFF))  // ← ARRAY OUT-OF-BOUNDS!
            // ...
        }
    }
}
```

**Problem**:
- `mgs.can[]` has size 2 (indices 0 and 1 only)
- When `canbus = 2` (PCAN format): **SEGFAULT**
- When `canbus = 3+` (APTERA with multiple virtual buses): **SEGFAULT**

### 4. Why Doesn't It Crash?

**Hypothesis**: One or more of the following:
1. Ethernet CAN server is disabled by default (`cb.use_ethernet_server == false`)
2. Configuration files don't include Ethernet CAN buses (`physical_bus_id != 2`)
3. There's bounds checking elsewhere that prevents messages from reaching `can_msg_process()`
4. The system is actually crashing but hasn't been tested with Ethernet CAN

## The Missing Piece: Ethernet CAN Hash Tables

### What SHOULD Happen (Not Implemented)

**During Initialization** (`imx_client_init.c`):

```c
/* Count logical buses with physical_bus_id == 2 */
uint16_t ethernet_bus_count = 0;
for (uint16_t i = 0; i < dev_config->num_logical_buses; i++) {
    if (dev_config->logical_buses[i].physical_bus_id == 2) {
        ethernet_bus_count++;
    }
}

/* Allocate ethernet_can_buses array */
if (ethernet_bus_count > 0) {
    mgs.ethernet_can_buses = (can_node_data_t *)imx_calloc(
        ethernet_bus_count,
        sizeof(can_node_data_t)
    );
    mgs.no_ethernet_can_buses = ethernet_bus_count;

    /* For each Ethernet logical bus */
    uint16_t eth_index = 0;
    for (uint16_t i = 0; i < dev_config->num_logical_buses; i++) {
        if (dev_config->logical_buses[i].physical_bus_id == 2) {
            /* Copy nodes for this Ethernet logical bus */
            mgs.ethernet_can_buses[eth_index].count =
                dev_config->logical_buses[i].node_count;

            mgs.ethernet_can_buses[eth_index].nodes = (can_node_t *)imx_calloc(
                dev_config->logical_buses[i].node_count,
                sizeof(can_node_t)
            );

            memcpy(mgs.ethernet_can_buses[eth_index].nodes,
                   dev_config->logical_buses[i].nodes,
                   sizeof(can_node_t) * dev_config->logical_buses[i].node_count);

            /* Sort nodes for hash table building */
            qsort(mgs.ethernet_can_buses[eth_index].nodes,
                  mgs.ethernet_can_buses[eth_index].count,
                  sizeof(can_node_t),
                  compare_nodes_by_id);

            eth_index++;
        }
    }

    /* Build hash tables for Ethernet buses */
    for (uint16_t i = 0; i < mgs.no_ethernet_can_buses; i++) {
        build_can_node_hash_table(&mgs.ethernet_can_buses[i].hash_table,
                                   mgs.ethernet_can_buses[i].nodes,
                                   mgs.ethernet_can_buses[i].count);
    }
}
```

**During Message Processing** (`can_man.c`):

```c
imx_result_t can_msg_process(can_bus_t canbus, imx_time_t current_time, can_msg_t *msg) {
    can_node_data_t *bus_data = NULL;

    /* Select correct bus data structure */
    if (canbus < NO_PHYSICAL_CAN_BUS) {
        /* Physical CAN bus 0 or 1 */
        bus_data = &mgs.can[canbus];
    } else if (canbus >= 2 && (canbus - 2) < mgs.no_ethernet_can_buses) {
        /* Ethernet CAN - map to ethernet_can_buses array */
        bus_data = &mgs.ethernet_can_buses[canbus - 2];
    } else {
        /* Invalid bus */
        return IMX_CAN_NODE_NOT_FOUND;
    }

    /* Use hash table for O(1) lookup */
    if (bus_data->hash_table.initialized) {
        can_node_t *node = lookup_can_node_by_id(&bus_data->hash_table,
                                                  msg->can_id,
                                                  bus_data->nodes);
        // ... rest of processing
    }
}
```

## Current Workaround

### How Ethernet CAN Messages Are Actually Processed

Looking at the code, I believe the answer is:

**Option 1: Messages Aggregated to Physical Buses**

The initialization code in `imx_client_init.c:960-1005` aggregates ALL logical buses to physical buses:

```c
for (uint16_t phys_bus = 0; phys_bus < NO_PHYSICAL_CAN_BUS; phys_bus++) {
    /* Count nodes for this physical bus across all logical buses */
    for (uint16_t log_bus = 0; log_bus < dev_config->num_logical_buses; log_bus++) {
        if (dev_config->logical_buses[log_bus].physical_bus_id == phys_bus) {
            total_nodes_for_bus += dev_config->logical_buses[log_bus].node_count;
        }
    }
    // ... allocate and copy nodes
}
```

**Notice**: This loop ONLY processes `phys_bus < NO_PHYSICAL_CAN_BUS` (i.e., buses 0 and 1).

**Result**: Logical buses with `physical_bus_id == 2` are **COMPLETELY IGNORED** during initialization!

**Option 2: Ethernet CAN Not Used Yet**

The most likely answer: **Ethernet CAN is not currently enabled** in production configurations. The infrastructure exists but:
- No v12 configs have `physical_bus_id = 2` yet
- Ethernet CAN server disabled by default
- Feature is incomplete and untested

## Answer to Your Question

### "How are multiple logical buses on the Ethernet interface hash tables initialized?"

**Short Answer**: **They aren't.** The feature is not implemented yet.

**Long Answer**:

1. **Declaration Exists**: `mgs.ethernet_can_buses` is declared in `structs.h:154`

2. **Never Allocated**: No code allocates this array

3. **Never Initialized**: No code calls `build_can_node_hash_table()` for Ethernet buses

4. **No Initialization Function**: There's no equivalent of `init_can_node_hash_tables()` for Ethernet

5. **Logical Buses with bus_id=2**: These are **silently dropped** during initialization (imx_client_init.c:960 loop skips them)

6. **Current State**:
   - If Ethernet CAN is used, messages would hit the bug in `can_msg_process()`
   - Would cause segfault when accessing `mgs.can[2]` (doesn't exist)
   - OR would show all nodes as "unknown" if physical_bus_id=2 nodes aren't loaded

## The Complete Picture

```
v12 Configuration File
└── logical_buses[] (dynamic array)
    ├── Bus 0: physical_bus_id=2, alias="PT"    ← Ethernet, IGNORED!
    ├── Bus 1: physical_bus_id=2, alias="IN"    ← Ethernet, IGNORED!
    └── Bus 2: physical_bus_id=0, alias="OBD"   ← Physical CAN0, LOADED

Runtime Initialization:
  ├── mgs.can[0] ← Aggregates ALL logical buses with physical_bus_id=0
  ├── mgs.can[1] ← Aggregates ALL logical buses with physical_bus_id=1
  └── mgs.ethernet_can_buses ← NEVER ALLOCATED, logical buses with physical_bus_id=2 LOST

Hash Table Initialization:
  ├── mgs.can[0].hash_table ← init_can_node_hash_tables() builds this
  ├── mgs.can[1].hash_table ← init_can_node_hash_tables() builds this
  └── mgs.ethernet_can_buses[*].hash_table ← NEVER HAPPENS (array doesn't exist)

Message Processing:
  ├── CAN_BUS_0 (canbus=0) → mgs.can[0] ✅ Works
  ├── CAN_BUS_1 (canbus=1) → mgs.can[1] ✅ Works
  └── CAN_BUS_ETH (canbus>=2) → mgs.can[2+] ❌ ARRAY OUT-OF-BOUNDS BUG!
```

## Why It Doesn't Crash (Yet)

### Hypothesis 1: Feature Not Enabled
- Ethernet CAN server disabled in all current configs
- `cb.use_ethernet_server == false`
- TCP server never starts
- No messages ever arrive with `canbus >= 2`

### Hypothesis 2: No Bus 2 Configurations
- All current v12 configs only use `physical_bus_id = 0` or `1`
- No logical buses map to Ethernet (physical_bus_id = 2)
- Feature exists but isn't used yet

### Hypothesis 3: Different Code Path
- Ethernet CAN messages might be processed differently
- Could have special handling before reaching `can_msg_process()`
- Need to verify actual message flow

## What Needs to Be Implemented

### Phase 1: Allocate Ethernet Bus Arrays

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Location**: After line 1005 (after physical bus initialization)

```c
/*
 * Initialize Ethernet CAN logical buses
 * Each logical bus with physical_bus_id==2 gets its own can_node_data_t entry
 */
uint16_t ethernet_bus_count = 0;
for (uint16_t i = 0; i < dev_config->num_logical_buses; i++) {
    if (dev_config->logical_buses[i].physical_bus_id == 2) {
        ethernet_bus_count++;
    }
}

if (ethernet_bus_count > 0) {
    imx_cli_print("Initializing %u Ethernet CAN logical bus(es)\r\n", ethernet_bus_count);

    /* Allocate ethernet_can_buses array */
    mgs.ethernet_can_buses = (can_node_data_t *)imx_calloc(
        ethernet_bus_count,
        sizeof(can_node_data_t)
    );

    if (mgs.ethernet_can_buses == NULL) {
        imx_cli_print("Error: Failed to allocate memory for Ethernet CAN buses\r\n");
        cleanup_allocated_memory();
        return false;
    }

    mgs.no_ethernet_can_buses = ethernet_bus_count;

    /* Copy nodes for each Ethernet logical bus */
    uint16_t eth_index = 0;
    for (uint16_t i = 0; i < dev_config->num_logical_buses; i++) {
        logical_bus_config_t *log_bus = &dev_config->logical_buses[i];

        if (log_bus->physical_bus_id != 2) {
            continue;  /* Skip non-Ethernet buses */
        }

        /* Allocate and copy nodes for this Ethernet bus */
        mgs.ethernet_can_buses[eth_index].count = log_bus->node_count;
        mgs.ethernet_can_buses[eth_index].nodes = (can_node_t *)imx_calloc(
            log_bus->node_count,
            sizeof(can_node_t)
        );

        if (mgs.ethernet_can_buses[eth_index].nodes == NULL) {
            imx_cli_print("Error: Failed to allocate nodes for Ethernet bus %u\r\n", eth_index);
            cleanup_allocated_memory();
            return false;
        }

        memcpy(mgs.ethernet_can_buses[eth_index].nodes,
               log_bus->nodes,
               sizeof(can_node_t) * log_bus->node_count);

        /* Sort nodes for hash table */
        qsort(mgs.ethernet_can_buses[eth_index].nodes,
              mgs.ethernet_can_buses[eth_index].count,
              sizeof(can_node_t),
              compare_nodes_by_id);

        imx_cli_print("  Ethernet logical bus '%s' (%u nodes) → eth_index %u\r\n",
                      log_bus->alias, log_bus->node_count, eth_index);

        /* Setup mux decoding structures */
        for (uint16_t j = 0; j < mgs.ethernet_can_buses[eth_index].count; j++) {
            if (!imx_setup_can_node_signals(&mgs.ethernet_can_buses[eth_index].nodes[j])) {
                imx_cli_print("Error: Failed to setup Ethernet CAN node signals\r\n");
                cleanup_allocated_memory();
                return false;
            }
        }

        eth_index++;
    }

    imx_cli_print("Successfully initialized %u Ethernet CAN logical bus(es)\r\n",
                  mgs.no_ethernet_can_buses);
} else {
    mgs.ethernet_can_buses = NULL;
    mgs.no_ethernet_can_buses = 0;
    imx_cli_print("No Ethernet CAN buses configured\r\n");
}
```

### Phase 2: Initialize Ethernet Hash Tables

**File**: `Fleet-Connect-1/can_process/can_man.c`

**Add New Function**:
```c
/**
 * @brief Initialize CAN node hash tables for Ethernet logical buses
 *
 * Builds hash tables for O(1) CAN node lookup performance on Ethernet buses.
 * This function should be called after Ethernet CAN nodes are loaded
 * during system initialization.
 *
 * @return None
 */
void init_ethernet_can_node_hash_tables(void)
{
    extern Mobile_Gateway_Status_t mgs;

    for (uint16_t i = 0; i < mgs.no_ethernet_can_buses; i++) {
        if (mgs.ethernet_can_buses[i].count > 0 &&
            mgs.ethernet_can_buses[i].nodes != NULL) {

            build_can_node_hash_table(&mgs.ethernet_can_buses[i].hash_table,
                                       mgs.ethernet_can_buses[i].nodes,
                                       mgs.ethernet_can_buses[i].count);

            PRINTF("[CAN Hash] Initialized hash table for Ethernet bus %u with %u nodes\r\n",
                   i, mgs.ethernet_can_buses[i].count);
        }
    }
}
```

**Call After Physical Bus Hash Init** (imx_client_init.c):
```c
/* Initialize hash tables for physical buses */
init_can_node_hash_tables();

/* Initialize hash tables for Ethernet buses */
if (mgs.no_ethernet_can_buses > 0) {
    init_ethernet_can_node_hash_tables();
}
```

### Phase 3: Fix Message Processing

**File**: `Fleet-Connect-1/can_process/can_man.c:752`

**Update `can_msg_process()`**:
```c
imx_result_t can_msg_process(can_bus_t canbus, imx_time_t current_time, can_msg_t *msg) {
    can_node_data_t *bus_data = NULL;

    /* Select correct bus data structure based on canbus ID */
    if (canbus < NO_PHYSICAL_CAN_BUS) {
        /* Physical CAN bus 0 or 1 */
        bus_data = &mgs.can[canbus];
    } else if (canbus >= 2) {
        /* Ethernet CAN - map to ethernet_can_buses array */
        uint16_t eth_index = canbus - 2;

        if (eth_index < mgs.no_ethernet_can_buses) {
            bus_data = &mgs.ethernet_can_buses[eth_index];
        } else {
            PRINTF("[CAN] Invalid Ethernet bus index: canbus=%u, eth_index=%u, max=%u\r\n",
                   canbus, eth_index, mgs.no_ethernet_can_buses);
            return IMX_CAN_NODE_NOT_FOUND;
        }
    } else {
        /* Invalid bus ID */
        return IMX_CAN_NODE_NOT_FOUND;
    }

    if (bus_data == NULL) {
        return IMX_CAN_NODE_NOT_FOUND;
    }

    /* Use hash table for O(1) lookup */
    if (bus_data->hash_table.initialized) {
        can_node_t *node = lookup_can_node_by_id(&bus_data->hash_table,
                                                  msg->can_id,
                                                  bus_data->nodes);
        // ... rest of processing
    }
    // ... fallback to linear search
}
```

## Impact on Current Implementation Plan

### Current Plan Scope (Phase 1)
- ✅ Fix `init_can_node_hash_tables()` to use `NO_PHYSICAL_CAN_BUS`
- ✅ Call initialization function in `imx_client_init.c`
- ✅ Add `can hash` CLI command for **physical buses only**

**Result**: Solves the immediate problem for physical CAN buses 0 and 1.

### Future Work (Out of Scope)
- Phase 1: Allocate `mgs.ethernet_can_buses` array
- Phase 2: Initialize Ethernet hash tables
- Phase 3: Fix `can_msg_process()` to handle Ethernet buses safely
- Phase 4: Extend `can hash` CLI to show Ethernet buses

## Recommendations

### Immediate Action (Current PR)
1. Proceed with physical bus hash table fix
2. Document Ethernet CAN limitation in plan
3. Add warning if Ethernet buses detected but not initialized
4. CLI command shows physical buses only (0 and 1)

### Follow-Up Work (Separate PR/Issue)
1. Implement Ethernet CAN bus allocation
2. Implement Ethernet hash table initialization
3. Fix array bounds bug in `can_msg_process()`
4. Add bounds checking throughout codebase
5. Test with actual Ethernet CAN configuration

### Safety Measures to Add Now

**File**: `can_man.c:752` - Add bounds check:
```c
imx_result_t can_msg_process(can_bus_t canbus, imx_time_t current_time, can_msg_t *msg) {
    /* Bounds check to prevent array out-of-bounds access */
    if (canbus >= NO_PHYSICAL_CAN_BUS) {
        PRINTF("[CAN] ERROR: Ethernet CAN not yet supported (canbus=%u >= %u)\r\n",
               canbus, NO_PHYSICAL_CAN_BUS);
        return IMX_CAN_NODE_NOT_FOUND;
    }

    // ... rest of existing code
}
```

This prevents crashes until Ethernet CAN is properly implemented.

---

**Analysis Date**: 2025-11-04
**Analyst**: Claude Code
**Status**: Critical findings - Ethernet CAN incomplete
