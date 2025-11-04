# Hash Table Update Implementation Plan

## Overview

Update the CAN bus hash table initialization to work correctly with the new v12 dynamic logical bus architecture. The hash tables provide O(1) lookup performance for CAN node processing.

**SCOPE EXPANDED**: This implementation now includes **mandatory** support for Ethernet CAN logical buses, fixing a critical array out-of-bounds bug and completing the Ethernet CAN infrastructure.

## Critical Findings

### Array Out-of-Bounds Bug Discovered
During analysis, a **critical latent bug** was discovered in `can_msg_process()`:
- Current code accesses `mgs.can[canbus]` without bounds checking
- `mgs.can[]` array size is 2 (only indices 0 and 1 valid)
- Ethernet CAN messages have `canbus >= 2`
- **Result**: Segfault if Ethernet CAN is ever enabled

### Ethernet CAN Infrastructure Incomplete
- `mgs.ethernet_can_buses` declared but **never allocated**
- Logical buses with `physical_bus_id == 2` are **silently dropped** during initialization
- Hash tables for Ethernet buses **don't exist**
- Feature is partially implemented but non-functional

**Mandatory Fix**: Complete Ethernet CAN hash table support to prevent data loss and crashes.

## Background Analysis

### Current Architecture (v12)

**Logical Buses (config file)**:
- Dynamic array of logical buses (1..N)
- Each logical bus has a `physical_bus_id` field mapping to physical hardware
- Defined in `config_v12_t` structure

**Physical Buses (runtime)**:
- Fixed array: `mgs.can[NO_PHYSICAL_CAN_BUS]` where `NO_PHYSICAL_CAN_BUS = 2`
- Index 0 = Physical CAN Bus 0 (PHYSICAL_CAN_BUS_0)
- Index 1 = Physical CAN Bus 1 (PHYSICAL_CAN_BUS_1)
- Ethernet CAN (bus 2) is handled separately via Ethernet subsystem

**Bus Mapping Process** (imx_client_init.c:960-1005):
1. For each physical bus (0..1):
   - Find all logical buses mapping to it
   - Count total nodes
   - Allocate memory
   - Copy nodes from all mapping logical buses
   - Sort nodes by ID for fast lookup

### The Problem

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Function**: `init_can_node_hash_tables()` (lines 300-309)

**Current Code**:
```c
void init_can_node_hash_tables(void)
{
    for (uint8_t bus = 0; bus < NO_CAN_BUS; bus++) {
        if (mgs.can[bus].count > 0 && mgs.can[bus].nodes != NULL) {
            build_can_node_hash_table(&mgs.can[bus].hash_table,
                                       mgs.can[bus].nodes,
                                       mgs.can[bus].count);
            PRINTF("[CAN Hash] Initialized hash table for CAN bus %u with %u nodes\r\n",
                   bus, mgs.can[bus].count);
        }
    }
}
```

**Issue**:
- Loop uses `NO_CAN_BUS` (value: 3) which includes:
  - CAN_BUS_0 (0)
  - CAN_BUS_1 (1)
  - CAN_BUS_ETH (2)
- But `mgs.can[]` array size is `NO_PHYSICAL_CAN_BUS` (value: 2)
- **Result**: Array out-of-bounds access when `bus = 2`!

**Constants Defined**:
- `iMatrix/canbus/can_structs.h:137-150`:
  ```c
  typedef enum {
      CAN_BUS_0,
      CAN_BUS_1,
      CAN_BUS_ETH,
      NO_CAN_BUS        // Value: 3
  } can_bus_t;

  typedef enum {
      PHYSICAL_CAN_BUS_0,
      PHYSICAL_CAN_BUS_1,
      NO_PHYSICAL_CAN_BUS  // Value: 2
  } physical_can_bus_t;
  ```

- `Fleet-Connect-1/structs.h:152`:
  ```c
  can_node_data_t can[NO_PHYSICAL_CAN_BUS];  // Only 2 elements!
  ```

### Why This Function Wasn't Called

The function `init_can_node_hash_tables()` was never called during initialization, so the bug remained hidden. The hash table lookup code in `can_man.c:762-775` has a fallback to linear search when `hash_table.initialized == false`.

**Current Behavior**: All CAN message lookups use slow O(n) linear search instead of O(1) hash lookup.

## Solution Design

### Overview of Changes

The solution consists of **three major components**:

1. **Fix Physical Bus Hash Tables** - Correct the existing function
2. **Implement Ethernet CAN Infrastructure** - Complete the missing functionality
3. **Add Safety and Diagnostics** - Prevent crashes and enable monitoring

### Component 1: Fix Physical Bus Hash Tables

**Change**: Update `init_can_node_hash_tables()` to loop over physical buses only.

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Location**: Line 302
**Change**:
```c
// OLD (WRONG):
for (uint8_t bus = 0; bus < NO_CAN_BUS; bus++) {

// NEW (CORRECT):
for (uint8_t bus = 0; bus < NO_PHYSICAL_CAN_BUS; bus++) {
```

**Rationale**:
- `mgs.can[]` only has `NO_PHYSICAL_CAN_BUS` elements (2)
- Ethernet CAN handled separately via `mgs.ethernet_can_buses[]`
- Physical buses 0 and 1 are hardware CAN interfaces

### Component 2: Implement Ethernet CAN Hash Tables (NEW - MANDATORY)

#### 2.1 Allocate Ethernet Bus Arrays

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Location**: After line 1005 (after physical bus initialization, before mux setup)

**Purpose**:
- Allocate `mgs.ethernet_can_buses[]` for each logical bus with `physical_bus_id == 2`
- Copy nodes from configuration to runtime structure
- Sort nodes for hash table building
- Setup mux decoding structures

**Code to Add**: See "Step 3A" in Implementation Steps section

#### 2.2 Build Ethernet Hash Tables

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Location**: After `init_can_node_hash_tables()` function

**New Function**: `init_ethernet_can_node_hash_tables()`

**Purpose**:
- Build hash tables for all Ethernet logical buses
- Enable O(1) lookup for Ethernet CAN messages
- Parallel structure to physical bus hash tables

**Code to Add**: See "Step 1B" in Implementation Steps section

### Component 3: Fix Message Processing Safety

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Location**: Line 752 (`can_msg_process()` function)

**Critical Fix**: Add bounds checking and Ethernet bus routing

**Changes**:
1. Add bounds validation at function start
2. Route Ethernet messages to `ethernet_can_buses[]` array
3. Use appropriate hash table based on bus type

**Code to Add**: See "Step 5" in Implementation Steps section

### Component 4: Update Cleanup Function

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Location**: `cleanup_allocated_memory()` function (around line 1356)

**Add Ethernet Bus Cleanup**:
```c
// Free Ethernet CAN BUS node pointers
for (uint16_t i = 0; i < mgs.no_ethernet_can_buses; i++) {
    if (mgs.ethernet_can_buses[i].nodes != NULL) {
        imx_free(mgs.ethernet_can_buses[i].nodes);
        mgs.ethernet_can_buses[i].nodes = NULL;
    }
    mgs.ethernet_can_buses[i].count = 0;
}

// Free ethernet_can_buses array itself
if (mgs.ethernet_can_buses != NULL) {
    imx_free(mgs.ethernet_can_buses);
    mgs.ethernet_can_buses = NULL;
}
mgs.no_ethernet_can_buses = 0;
```

## Implementation Steps

### Step 1A: Fix Physical Bus Hash Table Function

**File**: `Fleet-Connect-1/can_process/can_man.c:302`

**Change**:
```c
void init_can_node_hash_tables(void)
{
    // OLD: for (uint8_t bus = 0; bus < NO_CAN_BUS; bus++) {
    for (uint8_t bus = 0; bus < NO_PHYSICAL_CAN_BUS; bus++) {
        if (mgs.can[bus].count > 0 && mgs.can[bus].nodes != NULL) {
            build_can_node_hash_table(&mgs.can[bus].hash_table,
                                       mgs.can[bus].nodes,
                                       mgs.can[bus].count);
            PRINTF("[CAN Hash] Initialized hash table for physical CAN bus %u with %u nodes\r\n",
                   bus, mgs.can[bus].count);
        }
    }
}
```

### Step 1B: Add Ethernet Bus Hash Table Function

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Location**: After `init_can_node_hash_tables()` function (after line 309)

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

            PRINTF("[CAN Hash] Initialized hash table for Ethernet logical bus %u with %u nodes\r\n",
                   i, mgs.ethernet_can_buses[i].count);
        }
    }
}
```

### Step 2: Add Header Include

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Location**: After line 73

**Add**:
```c
#include "../can_process/can_man.h"
```

### Step 3A: Allocate Ethernet CAN Bus Arrays

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Location**: After line 1005 (after physical bus loop ends, before mux setup comment)

**Insert Complete Ethernet Bus Initialization**:
```c
	/*
	 * Initialize Ethernet CAN logical buses
	 * Each logical bus with physical_bus_id==2 gets its own can_node_data_t entry
	 * This enables proper hash table support for Ethernet CAN messages
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

			if (log_bus->node_count > 0 && log_bus->nodes != NULL) {
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

				/* Sort nodes for hash table building */
				qsort(mgs.ethernet_can_buses[eth_index].nodes,
					  mgs.ethernet_can_buses[eth_index].count,
					  sizeof(can_node_t),
					  compare_nodes_by_id);

				imx_cli_print("  Ethernet logical bus '%s' (%u nodes) → eth_index %u\r\n",
							  log_bus->alias, log_bus->node_count, eth_index);
			} else {
				mgs.ethernet_can_buses[eth_index].nodes = NULL;
				imx_cli_print("  Ethernet logical bus '%s' has no nodes\r\n", log_bus->alias);
			}

			eth_index++;
		}

		imx_cli_print("Successfully allocated %u Ethernet CAN logical bus(es)\r\n",
					  mgs.no_ethernet_can_buses);
	} else {
		mgs.ethernet_can_buses = NULL;
		mgs.no_ethernet_can_buses = 0;
		imx_cli_print("No Ethernet CAN buses configured\r\n");
	}
```

### Step 3B: Setup Ethernet Bus Mux Nodes

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Location**: Modify existing mux setup loop (after line 1022)

**Update Comment and Add Ethernet Loop**:
```c
	/*
	 * Process the Nodes to setup mux decoding structures for physical buses
	 */
	for (uint16_t i = 0; i < NO_PHYSICAL_CAN_BUS; i++) {
		for( uint16_t j = 0; j < mgs.can[i].count; j++ ) {
			if( imx_setup_can_node_signals(&mgs.can[i].nodes[j]) == false ) {
				imx_cli_print("Error: Failed to setup CAN node signals\r\n");
				cleanup_allocated_memory();
				return false;
			}
		}
	}

	/*
	 * Process the Nodes to setup mux decoding structures for Ethernet buses
	 */
	for (uint16_t i = 0; i < mgs.no_ethernet_can_buses; i++) {
		for( uint16_t j = 0; j < mgs.ethernet_can_buses[i].count; j++ ) {
			if( imx_setup_can_node_signals(&mgs.ethernet_can_buses[i].nodes[j]) == false ) {
				imx_cli_print("Error: Failed to setup Ethernet CAN node signals\r\n");
				cleanup_allocated_memory();
				return false;
			}
		}
	}
```

### Step 3C: Call Hash Table Initialization Functions

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Location**: After mux setup loops (after new Ethernet mux loop from Step 3B)

**Insert**:
```c
	/*
	 * Initialize hash tables for fast O(1) CAN node lookup
	 * Must be called after nodes are allocated, copied, and sorted
	 */
	init_can_node_hash_tables();
	imx_cli_print("Physical CAN bus hash tables initialized\r\n");

	/* Initialize hash tables for Ethernet CAN buses */
	if (mgs.no_ethernet_can_buses > 0) {
		init_ethernet_can_node_hash_tables();
		imx_cli_print("Ethernet CAN bus hash tables initialized\r\n");
	}

	mgs.cs_config_valid = true;
```

### Step 4: Update cleanup_allocated_memory()

**File**: `Fleet-Connect-1/init/imx_client_init.c`
**Location**: Function `cleanup_allocated_memory()` around line 1407

**Add Before Return** (after existing CAN bus cleanup):
```c
	// Free Ethernet CAN BUS node pointers
	for (uint16_t i = 0; i < mgs.no_ethernet_can_buses; i++) {
		if (mgs.ethernet_can_buses != NULL && mgs.ethernet_can_buses[i].nodes != NULL) {
			imx_free(mgs.ethernet_can_buses[i].nodes);
			mgs.ethernet_can_buses[i].nodes = NULL;
		}
		if (mgs.ethernet_can_buses != NULL) {
			mgs.ethernet_can_buses[i].count = 0;
		}
	}

	// Free ethernet_can_buses array itself
	if (mgs.ethernet_can_buses != NULL) {
		imx_free(mgs.ethernet_can_buses);
		mgs.ethernet_can_buses = NULL;
	}
	mgs.no_ethernet_can_buses = 0;
```

### Step 5: Fix can_msg_process() for Ethernet CAN Safety

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Location**: Line 752, function `can_msg_process()`

**Replace Entire Function** with safe Ethernet routing:
```c
imx_result_t can_msg_process(can_bus_t canbus, imx_time_t current_time, can_msg_t *msg) {
	/*
	 * Process CAN message through vehicle-specific signal extraction
	 * The vehicle-specific sensor mapping is handled in imx_set_can_sensor()
	 */
	mgs.last_can_msg = current_time;
	PRINTF("CAN[%u] Message: %010" PRIu32 "[0x%06" PRIx32 "] 0x%02" PRIx32 ":0x%02" PRIx32 ":0x%02" PRIx32 ":0x%02" PRIx32 ":0x%02" PRIx32 ":0x%02" PRIx32 ":0x%02" PRIx32 ":0x%02" PRIx32 "\r\n",
	       canbus, msg->can_id, msg->can_id, msg->can_data[0], msg->can_data[1], msg->can_data[2], msg->can_data[3], msg->can_data[4], msg->can_data[5], msg->can_data[6], msg->can_data[7]);

	/* Select correct bus data structure based on canbus ID */
	can_node_data_t *bus_data = NULL;

	if (canbus < NO_PHYSICAL_CAN_BUS) {
		/* Physical CAN bus 0 or 1 */
		bus_data = &mgs.can[canbus];
		PRINTF("Using physical CAN bus %u\r\n", canbus);
	} else if (canbus >= 2) {
		/* Ethernet CAN - map to ethernet_can_buses array */
		uint16_t eth_index = canbus - 2;

		if (eth_index < mgs.no_ethernet_can_buses) {
			bus_data = &mgs.ethernet_can_buses[eth_index];
			PRINTF("Using Ethernet logical bus %u (canbus=%u)\r\n", eth_index, canbus);
		} else {
			PRINTF("[CAN] Invalid Ethernet bus: canbus=%u, eth_index=%u, max=%u\r\n",
			       canbus, eth_index, mgs.no_ethernet_can_buses);
			return IMX_CAN_NODE_NOT_FOUND;
		}
	} else {
		/* Invalid bus ID */
		PRINTF("[CAN] Invalid bus ID: %u\r\n", canbus);
		return IMX_CAN_NODE_NOT_FOUND;
	}

	if (bus_data == NULL) {
		PRINTF("[CAN] Bus data structure is NULL for canbus=%u\r\n", canbus);
		return IMX_CAN_NODE_NOT_FOUND;
	}

	/* Use hash table for O(1) lookup if available, otherwise fall back to linear search */
	if (bus_data->hash_table.initialized) {
		/* Fast O(1) hash table lookup */
		can_node_t *node = lookup_can_node_by_id(&bus_data->hash_table,
		                                          msg->can_id,
		                                          bus_data->nodes);
		if (node != NULL) {
			/*
			 * Process the CAN Message according to the signals for that node
			 * We need to support multiplexed signals
			 */
			decode_can_message(msg, node);
			PRINTF("CAN Message Decoded (hash lookup)\r\n");
			return IMX_SUCCESS;
		}
	} else {
		/* Fallback to linear search if hash table not initialized */
		for (uint16_t i = 0; i < bus_data->count; i++) {
			if ((bus_data->nodes[i].node_id) == (msg->can_id & 0x7FFFFFFF))
			{
				/*
				 * Process the CAN Message according to the signals for that node
				 * We need to support multiplexed signals
				 */
				decode_can_message(msg, &bus_data->nodes[i]);
				PRINTF("CAN Message Decoded (linear search)\r\n");
				return IMX_SUCCESS;
			}
		}
	}

	return IMX_CAN_NODE_NOT_FOUND;
}
```

### Step 6: Implement CLI Command Functions

#### Step 6.1: Add Summary Display Function

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Location**: End of file (after existing functions)

**Add**: `display_can_hash_table_summary()` function (see CLI Command Implementation section)

#### Step 4.2: Add Detailed Display Function

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Location**: After summary function

**Add**: `display_can_hash_table_detailed()` function (see CLI Command Implementation section)

#### Step 4.3: Add Function Declarations

**File**: `Fleet-Connect-1/can_process/can_man.h`
**Location**: Function Declarations section (after `get_can_diagnostic_stats()`)

**Add**:
```c
/**
 * @brief Display hash table summary for all physical CAN buses
 */
void display_can_hash_table_summary(void);

/**
 * @brief Display detailed hash table information for a specific physical bus
 * @param bus Physical bus number (0 or 1)
 */
void display_can_hash_table_detailed(uint8_t bus);
```

#### Step 4.4: Add CLI Handler

**File**: `iMatrix/cli/cli_canbus.c`
**Location**: After line 507 (after "unknown" handler)

**Add**:
```c
        else if (strncmp(token, "hash", 4) == 0)
        {
            /*
             * Display hash table statistics
             * Format: can hash [bus_number]
             */
            char *arg1 = strtok(NULL, " ");

            if (arg1) {
                /* Detailed output for specific bus */
                uint8_t bus = atoi(arg1);

                if (bus >= NO_PHYSICAL_CAN_BUS) {
                    imx_cli_print("Invalid physical bus number. Use 0 or 1.\r\n");
                    return;
                }

                /* Declare external function */
                extern void display_can_hash_table_detailed(uint8_t bus);
                display_can_hash_table_detailed(bus);
            } else {
                /* Summary for all buses */
                extern void display_can_hash_table_summary(void);
                display_can_hash_table_summary();
            }
        }
```

#### Step 4.5: Update Error Message Help Text

**File**: `iMatrix/cli/cli_canbus.c`
**Location**: Line 604

**Change**:
```c
// OLD:
imx_cli_print("Invalid option, canbus <all> | <sim filename1 <filename2>> | <verify> | <status> | <extended> | <nodes [device] [node_id]> | <mapping> | <hm_sensors> | <server> | <send> | <send_file [device] file> | <send_file_sim [device] file> | <send_debug_file [device] file> | <send_test_file [device] file> | <send_file_stop>\r\n");

// NEW:
imx_cli_print("Invalid option, canbus <all> | <sim filename1 <filename2>> | <verify> | <status> | <extended> | <nodes [device] [node_id]> | <mapping> | <hm_sensors> | <server> | <hash [bus]> | <send> | <send_file [device] file> | <send_file_sim [device] file> | <send_debug_file [device] file> | <send_test_file [device] file> | <send_file_stop>\r\n");
```

#### Step 4.6: Update Help Display

**File**: `iMatrix/cli/cli_canbus.c`
**Location**: After line 655 (in help text section)

**Add**:
```c
imx_cli_print("  hash [bus]        - Display hash table statistics (bus: 0 or 1)\r\n");
```

## Testing Plan

### 1. Compilation Test
```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build
cmake ..
make
```

**Expected**: Clean compilation with no errors or warnings

### 2. Initialization Verification

**What to check**:
- Log message appears: "CAN node hash tables initialized for fast message processing"
- For each physical CAN bus with nodes, should see:
  ```
  [CAN Hash] Initialized hash table for CAN bus X with Y nodes
  ```

### 3. Runtime Verification

**Behavior Changes**:
- **Before**: All CAN message lookups use linear search (O(n))
- **After**: CAN message lookups use hash table (O(1))

**Performance Impact**:
- For configurations with many CAN nodes (50-200+), significant speedup
- For small configurations (< 20 nodes), minimal difference

**How to Verify**:
1. Enable CAN debug: `debug DEBUGS_APP_CAN_CTRL`
2. Process CAN messages
3. Look for: "CAN Message Decoded (hash lookup)" vs "(linear search)"
4. Should see "hash lookup" in all messages

## Risk Assessment

### Risks

**1. Array Bounds Bug (CRITICAL)**
- **Current Risk**: Out-of-bounds array access with `NO_CAN_BUS`
- **Mitigation**: Change to `NO_PHYSICAL_CAN_BUS`
- **Severity**: Could cause crash/corruption if function was ever called

**2. Missing Header Include**
- **Risk**: Compilation failure if header not included
- **Mitigation**: Add `#include "../can_process/can_man.h"`
- **Severity**: Low - will fail at compile time

**3. Performance Regression**
- **Risk**: Hash table overhead greater than linear search benefit
- **Mitigation**: Hash table only built once at startup
- **Severity**: Very Low - O(1) always better for repeated lookups

### Safety Measures

1. **Bounds Check**: Loop uses `NO_PHYSICAL_CAN_BUS` matching array size
2. **Null Checks**: Function already checks `mgs.can[bus].nodes != NULL`
3. **Count Validation**: Function checks `mgs.can[bus].count > 0`
4. **Fallback**: Existing code falls back to linear search if hash not initialized

## Expected Outcomes

### Functional

1. ✅ Hash tables built for both physical CAN buses (0 and 1)
2. ✅ CAN message processing uses O(1) hash lookup instead of O(n) search
3. ✅ No array out-of-bounds access
4. ✅ Proper initialization sequence maintained

### Performance

**Before** (linear search):
- Lookup time: O(n) where n = number of nodes per bus
- For 100 nodes: ~100 comparisons per message

**After** (hash table):
- Lookup time: O(1) average case
- For 100 nodes: ~1-2 comparisons per message (with collisions)

**Impact**:
- Heavily loaded CAN bus: Significant CPU reduction
- Light CAN traffic: Minimal difference
- Memory cost: ~8KB per bus (negligible for Linux platform)

### Logging Output Example

```
Mapped logical bus 'PT' (56 nodes) to physical CAN bus 0
Mapped logical bus 'IN' (42 nodes) to physical CAN bus 0
Physical CAN bus 0: 98 total nodes (sorted)
Physical CAN bus 1: 0 total nodes
[CAN Hash] Initialized hash table for CAN bus 0 with 98 nodes
CAN node hash tables initialized for fast message processing
```

## Questions Answered

### Q1: Why wasn't this function being called before?

**A**: The function was implemented but never integrated into the initialization sequence. The hash table lookup code has a fallback to linear search when `hash_table.initialized == false`, so the system worked (slowly) without it.

### Q2: Why use NO_PHYSICAL_CAN_BUS instead of NO_CAN_BUS?

**A**:
- `mgs.can[]` array size is `NO_PHYSICAL_CAN_BUS` (2 elements)
- Represents physical hardware CAN interfaces (CAN0, CAN1)
- Ethernet CAN (bus 2) doesn't use this array - it's handled separately
- Using `NO_CAN_BUS` (3) causes array out-of-bounds access

### Q3: Where does Ethernet CAN processing happen?

**A**: Ethernet CAN is processed through a separate code path:
- Parsed in `iMatrix/canbus/can_ethernet_parser.c`
- Virtual buses created per DBC file on Ethernet
- Uses unified queue system for message routing
- Does not use `mgs.can[]` physical bus array

### Q4: What happens if a logical bus maps to bus 2 (Ethernet)?

**A**:
- In v12, logical buses with `physical_bus_id = 2` are aggregated separately
- The loop in `imx_client_init.c:960` only processes buses 0 and 1
- Ethernet CAN node processing is handled by the Ethernet CAN subsystem
- Those nodes don't get added to `mgs.can[]` array

### Q5: Is there any risk of breaking existing functionality?

**A**: Very low risk:
- Only changes loop bound from wrong value (3) to correct value (2)
- Adds initialization call that should have been there from the start
- Fallback to linear search still works if hash table fails to build
- No changes to CAN message processing logic itself

## Detailed Todo List

### Phase 1: Core Hash Table Fixes

- [x] **Read and understand implementation context**
  - [x] Review hash table implementation in can_man.c
  - [x] Understand physical vs logical bus architecture
  - [x] Verify array bounds and structure definitions
  - [x] Locate initialization sequence in imx_client_init.c
  - [x] **Discover Ethernet CAN infrastructure gaps**
  - [x] **Identify array out-of-bounds bug in can_msg_process()**

- [ ] **Step 1A: Fix physical bus hash table function**
  - [ ] Open Fleet-Connect-1/can_process/can_man.c
  - [ ] Go to line 302
  - [ ] Change `NO_CAN_BUS` to `NO_PHYSICAL_CAN_BUS`
  - [ ] Update log message to say "physical CAN bus"
  - [ ] Save file

- [ ] **Step 1B: Add Ethernet bus hash table function**
  - [ ] In same file (can_man.c)
  - [ ] After line 309 (after init_can_node_hash_tables)
  - [ ] Add `init_ethernet_can_node_hash_tables()` function
  - [ ] Save file

- [ ] **Step 2: Add header include**
  - [ ] Open Fleet-Connect-1/init/imx_client_init.c
  - [ ] Add `#include "../can_process/can_man.h"` after line 73
  - [ ] Save file

### Phase 2: Ethernet CAN Infrastructure (MANDATORY)

- [ ] **Step 3A: Allocate Ethernet CAN bus arrays**
  - [ ] In imx_client_init.c
  - [ ] After line 1005 (after physical bus loop)
  - [ ] Add Ethernet bus counting loop
  - [ ] Allocate `mgs.ethernet_can_buses` array
  - [ ] Copy nodes from logical buses with physical_bus_id==2
  - [ ] Sort nodes for hash table building
  - [ ] Save file

- [ ] **Step 3B: Setup Ethernet bus mux nodes**
  - [ ] In imx_client_init.c
  - [ ] Update comment at line 1020
  - [ ] After physical bus mux loop (after line 1030)
  - [ ] Add Ethernet bus mux setup loop
  - [ ] Save file

- [ ] **Step 3C: Call hash table initialization functions**
  - [ ] In imx_client_init.c
  - [ ] After Ethernet mux loop
  - [ ] Call `init_can_node_hash_tables()` for physical buses
  - [ ] Call `init_ethernet_can_node_hash_tables()` for Ethernet buses
  - [ ] Move `mgs.cs_config_valid = true` to after hash init
  - [ ] Save file

- [ ] **Step 4: Update cleanup function**
  - [ ] In imx_client_init.c
  - [ ] Function `cleanup_allocated_memory()` around line 1407
  - [ ] Add loop to free Ethernet bus nodes
  - [ ] Free `mgs.ethernet_can_buses` array
  - [ ] Reset `mgs.no_ethernet_can_buses` to 0
  - [ ] Save file

### Phase 3: Fix Critical Safety Bug

- [ ] **Step 5: Fix can_msg_process() for Ethernet routing**
  - [ ] Open Fleet-Connect-1/can_process/can_man.c
  - [ ] Go to line 752 (function `can_msg_process()`)
  - [ ] Replace entire function with safe Ethernet routing version
  - [ ] Add bus_data pointer selection logic
  - [ ] Add bounds checking for Ethernet buses
  - [ ] Update hash table and linear search to use bus_data
  - [ ] Save file

### Phase 4: CLI Command Implementation

- [ ] **Step 6.1: Add summary display function**
  - [ ] In can_man.c
  - [ ] End of file
  - [ ] Add `display_can_hash_table_summary()` with physical + Ethernet support
  - [ ] Save file

- [ ] **Step 6.2: Add detailed display function**
  - [ ] In can_man.c
  - [ ] After summary function
  - [ ] Add `display_can_hash_table_detailed()` with bus type detection
  - [ ] Save file

- [ ] **Step 6.3: Add function declarations**
  - [ ] Open Fleet-Connect-1/can_process/can_man.h
  - [ ] After line 155
  - [ ] Add declarations for all three new functions
  - [ ] Save file

- [ ] **Step 6.4: Add CLI handler**
  - [ ] Open iMatrix/cli/cli_canbus.c
  - [ ] After line 507 (after "unknown" handler)
  - [ ] Add "hash" subcommand handler
  - [ ] Save file

- [ ] **Step 6.5-6.6: Update CLI help text**
  - [ ] In cli_canbus.c
  - [ ] Update error message at line 604
  - [ ] Add help line after line 655
  - [ ] Save file

### Phase 5: Build and Test

- [ ] **Compile and verify**
  - [ ] Run: `cd Fleet-Connect-1/build && cmake .. && make`
  - [ ] Verify clean compilation
  - [ ] Check for any warnings
  - [ ] Document any issues found

- [ ] **Initialization testing**
  - [ ] Run Fleet-Connect with v12 config
  - [ ] Verify physical bus hash table init messages
  - [ ] Verify Ethernet bus allocation messages (if config has physical_bus_id=2)
  - [ ] Verify Ethernet hash table init messages
  - [ ] Check no segfaults during startup

- [ ] **Runtime testing**
  - [ ] Enable CAN debug: `debug DEBUGS_APP_CAN_CTRL`
  - [ ] Process physical CAN messages - verify "hash lookup" messages
  - [ ] If Ethernet CAN enabled: send test frames, verify routing
  - [ ] Check no crashes with Ethernet messages

- [ ] **CLI command testing**
  - [ ] Test `can hash` - verify shows all buses with totals
  - [ ] Test `can hash 0` - verify physical bus 0 details
  - [ ] Test `can hash 1` - verify physical bus 1 details
  - [ ] Test `can hash 2` - verify Ethernet bus 0 details (if configured)
  - [ ] Test `can hash 3` - verify Ethernet bus 1 details (if configured)
  - [ ] Test invalid bus numbers - verify error handling
  - [ ] Verify statistics match actual configuration

## File Locations Reference

### Files to Modify

1. **Fleet-Connect-1/can_process/can_man.c** (4 changes)
   - Line 302: Fix loop bound in `init_can_node_hash_tables()` → `NO_PHYSICAL_CAN_BUS`
   - After line 309: Add `init_ethernet_can_node_hash_tables()` function
   - Line 752: Replace `can_msg_process()` with safe Ethernet routing version
   - End of file: Add `display_can_hash_table_summary()` function
   - End of file: Add `display_can_hash_table_detailed()` function

2. **Fleet-Connect-1/can_process/can_man.h** (1 change)
   - After line 155: Add declarations for 3 new functions

3. **Fleet-Connect-1/init/imx_client_init.c** (5 changes)
   - After line 73: Add `#include "../can_process/can_man.h"`
   - After line 1005: Add Ethernet CAN bus allocation (Step 3A)
   - After line 1030: Add Ethernet mux setup loop (Step 3B)
   - After Ethernet mux loop: Call hash init functions (Step 3C)
   - Line 1407: Update `cleanup_allocated_memory()` for Ethernet buses (Step 4)

4. **iMatrix/cli/cli_canbus.c** (3 changes)
   - After line 507: Add "hash" command handler
   - Line 604: Update error message help text
   - After line 655: Add help text for "hash" command

### Key Structure Definitions

1. **iMatrix/canbus/can_structs.h**
   - Lines 137-150: `can_bus_t` and `physical_can_bus_t` enums
   - Lines 313-330: `can_node_hash_table_t` structure
   - Lines 332-337: `can_node_data_t` structure

2. **Fleet-Connect-1/structs.h**
   - Line 152: `mgs.can[NO_PHYSICAL_CAN_BUS]` array declaration

### Function Locations

1. **Hash Table Functions** (`Fleet-Connect-1/can_process/can_man.c`):
   - Line 196: `hash_can_node_id()` - Hash function
   - Line 214: `build_can_node_hash_table()` - Build hash table
   - Line 269: `lookup_can_node_by_id()` - Hash lookup
   - Line 300: `init_can_node_hash_tables()` - Initialize all tables

2. **Initialization** (`Fleet-Connect-1/init/imx_client_init.c`):
   - Line 367: `imx_client_init()` - Main initialization function
   - Line 960: Logical bus to physical bus mapping
   - Line 1022: Mux node setup
   - Line 1030: **INSERT HASH TABLE INIT HERE**

## Success Criteria

### Compilation
- ✅ No compilation errors
- ✅ No warnings related to changes
- ✅ All dependent modules compile

### Initialization
- ✅ Hash tables initialized for both physical buses
- ✅ Correct node counts logged
- ✅ No crashes or errors during startup

### Runtime
- ✅ CAN messages processed correctly
- ✅ Hash table lookups used instead of linear search
- ✅ No performance degradation
- ✅ System operates normally under CAN traffic

## Additional Notes

### Why Hash Tables Matter

**Performance Impact Example**:
- Configuration with 100 CAN nodes per bus
- 1000 CAN messages/second processing rate
- Linear search: 100 comparisons × 1000 msg = 100,000 ops/sec
- Hash lookup: 1.5 comparisons × 1000 msg = 1,500 ops/sec
- **Improvement: 98.5% reduction in lookup operations**

### Memory Overhead

Hash table memory usage per bus:
```
Buckets: 256 pointers × 8 bytes = 2,048 bytes
Entries: 2,048 entries × 24 bytes = 49,152 bytes
Total: ~51 KB per bus
```

For 2 physical buses: ~102 KB total (negligible on Linux platform)

### Future Considerations

1. **Ethernet CAN Hash Tables**: Consider adding hash tables for Ethernet CAN virtual buses in future
2. **Hash Table Sizing**: Current `CAN_NODE_HASH_SIZE` (256) may need tuning for very large node counts
3. **Collision Monitoring**: Add statistics tracking for hash collisions

## CLI Command Implementation: "can hash"

### Command Specification

**Purpose**: Provide diagnostic information about CAN bus hash table status and performance for both physical and Ethernet CAN buses

**Syntax**:
```
can hash              - Display summary for ALL CAN buses (physical + Ethernet)
can hash 0            - Display detailed hash table info for physical bus 0
can hash 1            - Display detailed hash table info for physical bus 1
can hash 2            - Display detailed hash table info for Ethernet logical bus 0
can hash 3            - Display detailed hash table info for Ethernet logical bus 1
can hash N            - Display detailed hash table info for Ethernet logical bus N-2
```

**Bus Numbering**:
- **0, 1**: Physical CAN buses (hardware interfaces CAN0, CAN1)
- **2+**: Ethernet logical buses (canbus = 2 + ethernet_bus_index)
  - canbus 2 → ethernet_can_buses[0]
  - canbus 3 → ethernet_can_buses[1]
  - canbus N → ethernet_can_buses[N-2]

### Summary Output (no argument)

Display for ALL buses (physical + Ethernet):
- Bus number and type (Physical vs Ethernet)
- Status (initialized/not initialized)
- Total nodes configured
- Hash table status
- Entry count (nodes indexed)
- Collision statistics (if available)

**Example Output**:
```
=== CAN Hash Table Summary ===

Physical Bus 0 (CAN0):
  Status: Initialized
  Nodes: 32
  Hash entries: 32
  Hash buckets used: 30/256 (11.7%)
  Max chain length: 2
  Average chain length: 1.07

Physical Bus 1 (CAN1):
  Status: Not configured
  Nodes: 0

Ethernet Logical Bus 0 (canbus=2, alias='PT'):
  Status: Initialized
  Nodes: 56
  Hash entries: 56
  Hash buckets used: 52/256 (20.3%)
  Max chain length: 2
  Average chain length: 1.08

Ethernet Logical Bus 1 (canbus=3, alias='IN'):
  Status: Initialized
  Nodes: 57
  Hash entries: 57
  Hash buckets used: 54/256 (21.1%)
  Max chain length: 2
  Average chain length: 1.06

Total Buses Configured: 4 (2 physical, 2 Ethernet)
Total Nodes: 145
Total Hash Entries: 145

================================
```

### Detailed Output (with bus argument)

Display comprehensive information for specified bus (physical or Ethernet):
- Bus type identification
- All summary information
- Bucket utilization histogram
- Top 10 longest collision chains with node IDs
- Hash distribution quality metrics
- Memory usage statistics
- Performance estimates

**Example Output (Physical Bus)**:
```
=== Hash Table Details: Physical Bus 0 (CAN0) ===

Configuration:
  Hash table size: 256 buckets
  Max entries: 2048
  Entry count: 98
  Buckets used: 86/256 (33.6%)

Collision Statistics:
  Empty buckets: 170 (66.4%)
  Single entry: 79 (30.9%)
  Two entries: 5 (2.0%)
  Three+ entries: 2 (0.8%)
  Max chain length: 3
  Avg chain length: 1.14

Top Collision Chains:
  1. Bucket 127: 3 nodes [0x18FF4DF3, 0x0CFF4D01, 0x18FEF100]
  2. Bucket 45:  2 nodes [0x18FEF200, 0x0CFF4E00]
  3. Bucket 89:  2 nodes [0x18FF50F3, 0x0CFF5001]

Memory Usage:
  Bucket array: 2,048 bytes (256 × 8 bytes)
  Entry array: 49,152 bytes (2048 × 24 bytes)
  Actual nodes: 98 entries
  Overhead: 90.7% unused capacity
  Total: 51,200 bytes (~50 KB)

Performance Estimate:
  Lookups per message: ~1.14 comparisons (O(1))
  Linear search equivalent: ~49 comparisons (O(n))
  Speedup factor: 43x

====================================================
```

**Example Output (Ethernet Bus)**:
```
=== Hash Table Details: Ethernet Logical Bus 0 ===
Bus Info: canbus=2, alias='PT', DBC='Powertrain_V2.1.1.dbc'

Configuration:
  Hash table size: 256 buckets
  Max entries: 2048
  Entry count: 56
  Buckets used: 52/256 (20.3%)

Collision Statistics:
  Empty buckets: 204 (79.7%)
  Single entry: 50 (19.5%)
  Two entries: 2 (0.8%)
  Three+ entries: 0 (0.0%)
  Max chain length: 2
  Avg chain length: 1.08

Top Collision Chains:
  1. Bucket 127: 2 nodes [0x18FF4DF3, 0x0CFF4D01]
  2. Bucket 89:  2 nodes [0x18FF50F3, 0x0CFF5001]

Memory Usage:
  Bucket array: 2,048 bytes (256 × 8 bytes)
  Entry array: 49,152 bytes (2048 × 24 bytes)
  Actual nodes: 56 entries
  Overhead: 97.3% unused capacity
  Total: 51,200 bytes (~50 KB)

Performance Estimate:
  Lookups per message: ~1.08 comparisons (O(1))
  Linear search equivalent: ~28 comparisons (O(n))
  Speedup factor: 26x

====================================================
```

### Implementation Location

**File**: `iMatrix/cli/cli_canbus.c`
**Function**: `cli_canbus()` (modify existing)

**Add handler** around line 500 (after "unknown" handler):
```c
else if (strncmp(token, "hash", 4) == 0)
{
    /*
     * Display hash table statistics
     * Format: can hash [bus_number]
     * Bus numbers: 0-1 for physical, 2+ for Ethernet logical buses
     */
    char *arg1 = strtok(NULL, " ");

    if (arg1) {
        /* Detailed output for specific bus */
        uint8_t canbus = atoi(arg1);

        /* Declare external functions */
        extern void display_can_hash_table_detailed(uint8_t canbus);
        display_can_hash_table_detailed(canbus);
    } else {
        /* Summary for all buses (physical + Ethernet) */
        extern void display_can_hash_table_summary(void);
        display_can_hash_table_summary();
    }
}
```

### New Functions Required

#### Function 1: Summary Display (Updated for Physical + Ethernet)

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Function**: `display_can_hash_table_summary()`

```c
/**
 * @brief Display hash table summary for all CAN buses (physical + Ethernet)
 *
 * Shows initialization status, node counts, and basic statistics
 * for each bus's hash table.
 *
 * @return None
 */
void display_can_hash_table_summary(void)
{
    extern Mobile_Gateway_Status_t mgs;
    extern canbus_product_t cb;
    uint32_t total_nodes = 0;
    uint32_t total_entries = 0;
    uint16_t total_buses = 0;

    imx_cli_print("\r\n=== CAN Hash Table Summary ===\r\n\r\n");

    /* Display physical buses */
    for (uint8_t bus = 0; bus < NO_PHYSICAL_CAN_BUS; bus++) {
        imx_cli_print("Physical Bus %u (CAN%u):\r\n", bus, bus);

        if (!mgs.can[bus].hash_table.initialized) {
            imx_cli_print("  Status: Not initialized\r\n");
            imx_cli_print("  Nodes: %u\r\n", mgs.can[bus].count);
            imx_cli_print("\r\n");
            if (mgs.can[bus].count > 0) total_buses++;
            continue;
        }

        imx_cli_print("  Status: Initialized\r\n");
        imx_cli_print("  Nodes: %u\r\n", mgs.can[bus].count);
        imx_cli_print("  Hash entries: %u\r\n", mgs.can[bus].hash_table.entry_count);

        /* Calculate bucket statistics */
        uint16_t buckets_used = 0;
        uint16_t max_chain = 0;
        uint32_t total_chain_length = 0;

        for (uint16_t i = 0; i < CAN_NODE_HASH_SIZE; i++) {
            if (mgs.can[bus].hash_table.buckets[i] != NULL) {
                buckets_used++;
                uint16_t chain_len = 0;
                can_node_hash_entry_t *entry = mgs.can[bus].hash_table.buckets[i];
                while (entry != NULL) {
                    chain_len++;
                    entry = entry->next;
                }
                if (chain_len > max_chain) max_chain = chain_len;
                total_chain_length += chain_len;
            }
        }

        float bucket_usage = (buckets_used * 100.0f) / CAN_NODE_HASH_SIZE;
        float avg_chain = buckets_used > 0 ? (float)total_chain_length / buckets_used : 0.0f;

        imx_cli_print("  Hash buckets used: %u/%u (%.1f%%)\r\n",
                      buckets_used, CAN_NODE_HASH_SIZE, bucket_usage);
        imx_cli_print("  Max chain length: %u\r\n", max_chain);
        imx_cli_print("  Avg chain length: %.2f\r\n", avg_chain);
        imx_cli_print("\r\n");

        total_nodes += mgs.can[bus].count;
        total_entries += mgs.can[bus].hash_table.entry_count;
        total_buses++;
    }

    /* Display Ethernet logical buses */
    for (uint16_t i = 0; i < mgs.no_ethernet_can_buses; i++) {
        /* Get alias from DBC files if available */
        const char *alias = "unknown";
        if (cb.dbc_files != NULL && i < cb.dbc_files_count) {
            alias = cb.dbc_files[i].alias;
        }

        imx_cli_print("Ethernet Logical Bus %u (canbus=%u, alias='%s'):\r\n",
                      i, i + 2, alias);

        if (!mgs.ethernet_can_buses[i].hash_table.initialized) {
            imx_cli_print("  Status: Not initialized\r\n");
            imx_cli_print("  Nodes: %u\r\n", mgs.ethernet_can_buses[i].count);
            imx_cli_print("\r\n");
            if (mgs.ethernet_can_buses[i].count > 0) total_buses++;
            continue;
        }

        imx_cli_print("  Status: Initialized\r\n");
        imx_cli_print("  Nodes: %u\r\n", mgs.ethernet_can_buses[i].count);
        imx_cli_print("  Hash entries: %u\r\n", mgs.ethernet_can_buses[i].hash_table.entry_count);

        /* Calculate bucket statistics */
        uint16_t buckets_used = 0;
        uint16_t max_chain = 0;
        uint32_t total_chain_length = 0;

        for (uint16_t j = 0; j < CAN_NODE_HASH_SIZE; j++) {
            if (mgs.ethernet_can_buses[i].hash_table.buckets[j] != NULL) {
                buckets_used++;
                uint16_t chain_len = 0;
                can_node_hash_entry_t *entry = mgs.ethernet_can_buses[i].hash_table.buckets[j];
                while (entry != NULL) {
                    chain_len++;
                    entry = entry->next;
                }
                if (chain_len > max_chain) max_chain = chain_len;
                total_chain_length += chain_len;
            }
        }

        float bucket_usage = (buckets_used * 100.0f) / CAN_NODE_HASH_SIZE;
        float avg_chain = buckets_used > 0 ? (float)total_chain_length / buckets_used : 0.0f;

        imx_cli_print("  Hash buckets used: %u/%u (%.1f%%)\r\n",
                      buckets_used, CAN_NODE_HASH_SIZE, bucket_usage);
        imx_cli_print("  Max chain length: %u\r\n", max_chain);
        imx_cli_print("  Avg chain length: %.2f\r\n", avg_chain);
        imx_cli_print("\r\n");

        total_nodes += mgs.ethernet_can_buses[i].count;
        total_entries += mgs.ethernet_can_buses[i].hash_table.entry_count;
        total_buses++;
    }

    /* Print totals */
    if (total_buses > 0) {
        imx_cli_print("Total Buses Configured: %u (%u physical, %u Ethernet)\r\n",
                      total_buses, NO_PHYSICAL_CAN_BUS, mgs.no_ethernet_can_buses);
        imx_cli_print("Total Nodes: %u\r\n", total_nodes);
        imx_cli_print("Total Hash Entries: %u\r\n\r\n", total_entries);
    }

    imx_cli_print("================================\r\n\r\n");
}
```

#### Function 2: Detailed Display (Updated for Physical + Ethernet)

**File**: `Fleet-Connect-1/can_process/can_man.c`
**Function**: `display_can_hash_table_detailed()`

```c
/**
 * @brief Display detailed hash table information for a specific CAN bus
 *
 * Shows comprehensive statistics including collision analysis, memory usage,
 * and performance estimates. Handles both physical (0-1) and Ethernet (2+) buses.
 *
 * @param[in] canbus Bus number (0-1 for physical, 2+ for Ethernet logical buses)
 * @return None
 */
void display_can_hash_table_detailed(uint8_t canbus)
{
    extern Mobile_Gateway_Status_t mgs;
    extern canbus_product_t cb;
    can_node_data_t *bus_data = NULL;
    const char *bus_type = NULL;
    const char *bus_name = NULL;
    const char *alias = NULL;
    char bus_label[64];

    /* Determine bus type and get bus_data pointer */
    if (canbus < NO_PHYSICAL_CAN_BUS) {
        /* Physical CAN bus */
        bus_data = &mgs.can[canbus];
        bus_type = "Physical";
        snprintf(bus_label, sizeof(bus_label), "Physical Bus %u (CAN%u)", canbus, canbus);
    } else {
        /* Ethernet logical bus */
        uint16_t eth_index = canbus - 2;

        if (eth_index >= mgs.no_ethernet_can_buses) {
            imx_cli_print("Error: Invalid bus number %u (Ethernet index %u >= %u)\r\n",
                          canbus, eth_index, mgs.no_ethernet_can_buses);
            return;
        }

        bus_data = &mgs.ethernet_can_buses[eth_index];
        bus_type = "Ethernet";

        /* Get alias and DBC filename if available */
        if (cb.dbc_files != NULL && eth_index < cb.dbc_files_count) {
            alias = cb.dbc_files[eth_index].alias;
            bus_name = cb.dbc_files[eth_index].bus_name;
            snprintf(bus_label, sizeof(bus_label),
                     "Ethernet Logical Bus %u (canbus=%u, alias='%s')",
                     eth_index, canbus, alias);
        } else {
            snprintf(bus_label, sizeof(bus_label),
                     "Ethernet Logical Bus %u (canbus=%u)",
                     eth_index, canbus);
        }
    }

    imx_cli_print("\r\n=== Hash Table Details: %s ===\r\n", bus_label);

    /* Show DBC filename for Ethernet buses */
    if (canbus >= 2 && bus_name != NULL) {
        imx_cli_print("DBC File: %s\r\n", bus_name);
    }
    imx_cli_print("\r\n");

    if (!bus_data->hash_table.initialized) {
        imx_cli_print("Hash table not initialized for this bus.\r\n");
        imx_cli_print("Nodes configured: %u\r\n\r\n", bus_data->count);
        return;
    }

    /* Configuration */
    imx_cli_print("Configuration:\r\n");
    imx_cli_print("  Bus Type: %s\r\n", bus_type);
    imx_cli_print("  Hash table size: %u buckets\r\n", CAN_NODE_HASH_SIZE);
    imx_cli_print("  Max entries: %u\r\n", MAX_CAN_NODES);
    imx_cli_print("  Entry count: %u\r\n", bus_data->hash_table.entry_count);

    /* Analyze bucket utilization */
    uint16_t empty = 0, single = 0, two = 0, three_plus = 0;
    uint16_t max_chain = 0;
    uint32_t total_chain_length = 0;
    uint16_t buckets_used = 0;

    for (uint16_t i = 0; i < CAN_NODE_HASH_SIZE; i++) {
        can_node_hash_entry_t *entry = bus_data->hash_table.buckets[i];
        if (entry == NULL) {
            empty++;
            continue;
        }

        buckets_used++;
        uint16_t chain_len = 0;
        while (entry != NULL) {
            chain_len++;
            entry = entry->next;
        }

        if (chain_len == 1) single++;
        else if (chain_len == 2) two++;
        else three_plus++;

        if (chain_len > max_chain) max_chain = chain_len;
        total_chain_length += chain_len;
    }

    float bucket_usage = (buckets_used * 100.0f) / CAN_NODE_HASH_SIZE;
    float avg_chain = buckets_used > 0 ? (float)total_chain_length / buckets_used : 0.0f;

    imx_cli_print("  Buckets used: %u/%u (%.1f%%)\r\n\r\n",
                  buckets_used, CAN_NODE_HASH_SIZE, bucket_usage);

    /* Collision statistics */
    imx_cli_print("Collision Statistics:\r\n");
    imx_cli_print("  Empty buckets: %u (%.1f%%)\r\n", empty, (empty * 100.0f) / CAN_NODE_HASH_SIZE);
    imx_cli_print("  Single entry: %u (%.1f%%)\r\n", single, (single * 100.0f) / CAN_NODE_HASH_SIZE);
    imx_cli_print("  Two entries: %u (%.1f%%)\r\n", two, (two * 100.0f) / CAN_NODE_HASH_SIZE);
    imx_cli_print("  Three+ entries: %u (%.1f%%)\r\n", three_plus, (three_plus * 100.0f) / CAN_NODE_HASH_SIZE);
    imx_cli_print("  Max chain length: %u\r\n", max_chain);
    imx_cli_print("  Avg chain length: %.2f\r\n\r\n", avg_chain);

    /* Top collision chains */
    if (max_chain > 1) {
        imx_cli_print("Top Collision Chains:\r\n");
        uint8_t displayed = 0;
        for (uint16_t i = 0; i < CAN_NODE_HASH_SIZE && displayed < 10; i++) {
            can_node_hash_entry_t *entry = bus_data->hash_table.buckets[i];
            if (entry == NULL) continue;

            /* Count chain length */
            uint16_t chain_len = 0;
            can_node_hash_entry_t *temp = entry;
            while (temp != NULL) {
                chain_len++;
                temp = temp->next;
            }

            if (chain_len > 1) {
                displayed++;
                imx_cli_print("  %u. Bucket %3u: %u nodes [", displayed, i, chain_len);

                bool first = true;
                temp = entry;
                while (temp != NULL && chain_len <= 5) {  /* Limit display to 5 nodes */
                    if (!first) imx_cli_print(", ");
                    imx_cli_print("0x%08X", temp->node_id);
                    first = false;
                    temp = temp->next;
                }
                if (chain_len > 5) {
                    imx_cli_print(", ...");
                }
                imx_cli_print("]\r\n");
            }
        }
        imx_cli_print("\r\n");
    }

    /* Memory usage */
    uint32_t bucket_mem = CAN_NODE_HASH_SIZE * sizeof(can_node_hash_entry_t*);
    uint32_t entry_mem = MAX_CAN_NODES * sizeof(can_node_hash_entry_t);
    uint32_t total_mem = bucket_mem + entry_mem;
    float overhead = (1.0f - ((float)bus_data->hash_table.entry_count / MAX_CAN_NODES)) * 100.0f;

    imx_cli_print("Memory Usage:\r\n");
    imx_cli_print("  Bucket array: %lu bytes (%u × %zu bytes)\r\n",
                  bucket_mem, CAN_NODE_HASH_SIZE, sizeof(can_node_hash_entry_t*));
    imx_cli_print("  Entry array: %lu bytes (%u × %zu bytes)\r\n",
                  entry_mem, MAX_CAN_NODES, sizeof(can_node_hash_entry_t));
    imx_cli_print("  Actual nodes: %u entries\r\n", bus_data->hash_table.entry_count);
    imx_cli_print("  Overhead: %.1f%% unused capacity\r\n", overhead);
    imx_cli_print("  Total: %lu bytes (~%lu KB)\r\n\r\n", total_mem, total_mem / 1024);

    /* Performance estimate */
    uint16_t node_count = bus_data->count;
    float linear_compares = node_count / 2.0f;  /* Average for linear search */
    float speedup = (avg_chain > 0) ? (linear_compares / avg_chain) : 0.0f;

    imx_cli_print("Performance Estimate:\r\n");
    imx_cli_print("  Lookups per message: ~%.2f comparisons (O(1))\r\n", avg_chain);
    imx_cli_print("  Linear search equivalent: ~%.0f comparisons (O(n))\r\n", linear_compares);
    imx_cli_print("  Speedup factor: %.0fx\r\n\r\n", speedup);

    imx_cli_print("====================================================\r\n\r\n");
}
```

### Function Declarations

**File**: `Fleet-Connect-1/can_process/can_man.h`
**Location**: After `init_can_node_hash_tables()` declaration (after line 155)

Add to function declarations section:
```c
/**
 * @brief Initialize CAN node hash tables for Ethernet logical buses
 *
 * Builds hash tables for O(1) CAN node lookup performance on Ethernet buses.
 * Should be called after Ethernet CAN nodes are loaded during initialization.
 *
 * @return None
 */
void init_ethernet_can_node_hash_tables(void);

/**
 * @brief Display hash table summary for all CAN buses (physical + Ethernet)
 *
 * Shows initialization status and statistics for all configured buses.
 *
 * @return None
 */
void display_can_hash_table_summary(void);

/**
 * @brief Display detailed hash table information for a specific CAN bus
 *
 * Handles both physical (0-1) and Ethernet (2+) buses.
 *
 * @param canbus Bus number (0-1 for physical, 2+ for Ethernet logical buses)
 * @return None
 */
void display_can_hash_table_detailed(uint8_t canbus);
```

### CLI Help Text Update

**File**: `iMatrix/cli/cli_canbus.c`
**Location**: Line 604 and line 646

Update the help text to include the new "hash" command:

**Line 604** (error message):
```c
imx_cli_print("Invalid option, canbus <all> | <sim filename1 <filename2>> | <verify> | <status> | <extended> | <nodes [device] [node_id]> | <mapping> | <hm_sensors> | <server> | <hash [bus]> | <send> | <send_file [device] file> | <send_file_sim [device] file> | <send_debug_file [device] file> | <send_test_file [device] file> | <send_file_stop>\r\n");
```

**Line 646** (help display):
```c
imx_cli_print("  hash [bus]        - Display hash table statistics (bus: 0 or 1)\r\n");
```

### Implementation Steps for CLI Command

1. **Add display functions to can_man.c** (Steps 4.1-4.2 below)
2. **Add function declarations to can_man.h** (Step 4.3)
3. **Add CLI handler to cli_canbus.c** (Step 4.4)
4. **Update help text in cli_canbus.c** (Step 4.5-4.6)
5. **Test the command** (Step 4.7)

### Testing the CLI Command

**Basic tests**:
```bash
can hash           # Should show summary for all buses (physical + Ethernet)
can hash 0         # Should show detailed info for physical bus 0
can hash 1         # Should show detailed info for physical bus 1
can hash 2         # Should show detailed info for Ethernet logical bus 0
can hash 3         # Should show detailed info for Ethernet logical bus 1
can hash 99        # Should show error (invalid bus - no Ethernet bus 97)
```

**Expected behavior**:
- Summary shows ALL buses (physical CAN 0-1, Ethernet logical buses 0-N)
- Total counts at bottom show combined statistics
- Detailed view works for any valid bus number
- Ethernet buses show DBC alias and filename
- Graceful error handling for invalid bus numbers

---

## Implementation Summary

### What This Implementation Accomplishes

#### 1. Fixes Critical Bugs
- **Array Out-of-Bounds in `init_can_node_hash_tables()`**: Changes loop from `NO_CAN_BUS` (3) to `NO_PHYSICAL_CAN_BUS` (2)
- **Array Out-of-Bounds in `can_msg_process()`**: Adds bounds checking and proper routing for Ethernet buses
- **Segfault Prevention**: Prevents crashes when Ethernet CAN is enabled

#### 2. Completes Ethernet CAN Infrastructure
- **Allocates `mgs.ethernet_can_buses[]` array**: Properly stores Ethernet logical buses
- **Copies nodes from v12 config**: Logical buses with `physical_bus_id == 2` no longer dropped
- **Builds hash tables for Ethernet**: Enables O(1) lookup for Ethernet CAN messages
- **Sets up mux decoding**: Supports multiplexed signals on Ethernet buses

#### 3. Enables O(1) Hash Table Lookups
- **Physical CAN buses**: Hash tables now initialized and used
- **Ethernet CAN buses**: Hash tables built for all logical buses
- **Performance gain**: 98.5% reduction in lookup operations for large configs
- **Scalability**: Supports unlimited Ethernet logical buses (limited only by memory)

#### 4. Provides Diagnostic Tools
- **`can hash` command**: Summary of all buses (physical + Ethernet)
- **`can hash N` command**: Detailed statistics for any bus
- **Performance metrics**: Shows actual speedup from hash tables
- **Collision analysis**: Helps tune hash table size if needed

### Files Modified: 4 files, 13 total changes

| File | Changes | Lines Modified |
|------|---------|----------------|
| can_man.c | 5 changes | ~200 lines added, 40 modified |
| can_man.h | 1 change | ~15 lines added |
| imx_client_init.c | 5 changes | ~120 lines added, 10 modified |
| cli_canbus.c | 3 changes | ~20 lines added, 2 modified |
| **Total** | **13 changes** | **~355 lines added, 52 modified** |

### Memory Impact

**Before**:
- Physical buses: 2 × 51 KB = 102 KB
- Ethernet buses: 0 KB (not allocated)
- **Total: 102 KB**

**After**:
- Physical buses: 2 × 51 KB = 102 KB
- Ethernet buses: N × 51 KB (N = number of Ethernet logical buses)
- **Example (2 Ethernet buses): 102 + 102 = 204 KB total**

**Note**: All allocations are one-time at startup, negligible on Linux platform.

### Performance Impact

**Message Processing**:
- **Before**: O(n) linear search for all messages
- **After**: O(1) hash table lookup for all messages
- **Speedup**: 20x-100x depending on node count

**Configuration with 100 nodes per bus**:
- Linear search: ~50 comparisons per message
- Hash lookup: ~1.5 comparisons per message
- **33x speedup per message!**

### Risk Mitigation

**Bugs Fixed**:
- ✅ Array out-of-bounds in initialization
- ✅ Array out-of-bounds in message processing
- ✅ Segfault when Ethernet CAN enabled
- ✅ Lost configuration data (physical_bus_id=2 buses dropped)

**Safety Added**:
- ✅ Bounds checking in message processing
- ✅ Graceful error messages for invalid buses
- ✅ Proper memory cleanup on errors
- ✅ Null pointer checks throughout

**Testing Added**:
- ✅ CLI diagnostic command
- ✅ Hash table initialization logging
- ✅ Statistics validation capability

### Success Criteria

#### Compilation
- ✅ No compilation errors
- ✅ No warnings
- ✅ All dependent modules compile

#### Initialization (Physical Buses)
- ✅ Hash tables built for CAN bus 0 and 1
- ✅ Correct node counts logged
- ✅ "Physical CAN bus hash tables initialized" message appears

#### Initialization (Ethernet Buses)
- ✅ Ethernet buses allocated if `physical_bus_id == 2` exists in config
- ✅ Nodes copied and sorted for each Ethernet logical bus
- ✅ Hash tables built for all Ethernet buses
- ✅ "Ethernet CAN bus hash tables initialized" message appears
- ✅ No crashes during startup

#### Runtime
- ✅ Physical CAN messages processed with hash lookup
- ✅ Ethernet CAN messages routed to correct logical bus
- ✅ No array out-of-bounds errors
- ✅ No segfaults under any CAN traffic pattern

#### CLI Command
- ✅ `can hash` shows ALL buses (physical + Ethernet)
- ✅ `can hash 0-1` shows physical bus details
- ✅ `can hash 2+` shows Ethernet bus details
- ✅ Statistics accurate and informative
- ✅ Error handling for invalid bus numbers

### Next Steps After Implementation

1. **Test with Ethernet CAN Config**: Create v12 config with `physical_bus_id = 2` buses
2. **Validate APTERA Format**: Test multi-virtual-bus Ethernet CAN
3. **Performance Benchmarking**: Measure actual speedup with real CAN traffic
4. **Documentation Update**: Update Fleet-Connect-Overview.md with Ethernet CAN details

### Related Documents

- **`docs/ethernet_can_hash_analysis.md`**: Deep dive into Ethernet CAN architecture
- **`docs/update_hash_processing.md`**: Original task requirements
- **`Fleet-Connect-1/docs/Fleet-Connect-Overview.md`**: System architecture
- **`Fleet-Connect-1/docs/NEW_DEVELOPER_GUIDE_V12.md`**: v12 configuration guide

---

**Plan Created**: 2025-11-04
**Last Updated**: 2025-11-04 (expanded for Ethernet CAN mandatory support)
**Author**: Claude Code
**Status**: Comprehensive Plan Ready for Implementation
**Scope**: Hash tables for ALL CAN buses (physical + Ethernet) + Critical bug fixes
