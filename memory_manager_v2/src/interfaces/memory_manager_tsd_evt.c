/*
 * Copyright 2025, iMatrix Systems, Inc.. All Rights Reserved.
 *
 * Memory Manager v2 - Direct replacement for memory_manager_tsd_evt.c
 * This file implements the exact same API but uses Memory Manager v2 internally
 */

/**
 * @file memory_manager_tsd_evt.c
 * @brief TSD/EVT data operations using Memory Manager v2
 *
 * Drop-in replacement for the original memory_manager_tsd_evt.c
 * Uses the embedded v2_state in control_sensor_data_t for all operations
 *
 * @author Memory Manager v2 Team
 * @date 2025
 */

#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "imatrix.h"
#include "storage.h"
#include "imx_platform.h"
#include "../cli/interface.h"
#include "../device/icb_def.h"
#include "../storage.h"
#include "../time/ck_time.h"
#include "memory_manager.h"
#include "memory_manager_internal.h"
#include "memory_manager_core.h"
#include "memory_manager_tsd_evt.h"

// Memory Manager v2 includes
#include "../../include/unified_state.h"
#include "../../include/disk_operations.h"

// Forward declaration for device_config
extern IOT_Device_Config_t device_config;

#ifdef CAN_PLATFORM
#include "../canbus/can_structs.h"
#endif

#ifdef APPLIANCE_GATEWAY
#include "../appliance_routines.h"
#endif

/******************************************************
 *                      Macros
 ******************************************************/
#ifdef PRINT_DEBUGS_ADD_TSD_EVT
    #undef PRINTF
    #define PRINTF(...) if( LOGS_ENABLED( DEBUGS_ADD_TSD_EVT ) ) imx_cli_log_printf(true,__VA_ARGS__)
#elif !defined PRINTF
    #define PRINTF(...)
#endif

/******************************************************
 *               Function Definitions
 ******************************************************/

/**
 * @brief Write TSD or EVT data to memory using Memory Manager v2
 * @param csb Control sensor block pointer
 * @param csd Control sensor data pointer
 * @param entry Entry index to write
 * @param value Data value to write
 * @param add_gps_location Whether to add GPS location data
 */
void write_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                   uint16_t entry, uint32_t value, bool add_gps_location)
{
    if (!csb || !csd) {
        return;
    }

    uint32_t utc_time;

    // Get current time
    if (imx_system_time_syncd() == true) {
        imx_time_get_utc_time(&utc_time);
    } else {
        utc_time = 0; // Tell iMatrix cloud to assign
    }

    write_tsd_evt_time(csb, csd, entry, value, utc_time);

    // Handle GPS location if requested
    if (add_gps_location) {
        float lat = imx_get_latitude();
        float lon = imx_get_longitude();

        if ((lat != 0) && (lon != 0)) {
            // Add the GPS location to the data
            uint16_t i;
            imx_data_32_t gps_data;

            for (i = 0; i < entry; i++) {
                if (csb[i].id == IMX_INTERNAL_SENSOR_GPS_LATITUDE) {
                    gps_data.float_32bit = lat;
                    write_tsd_evt_time(csb, csd, i, gps_data.uint_32bit, utc_time);
                }
                else if (csb[i].id == IMX_INTERNAL_SENSOR_GPS_LONGITUDE) {
                    gps_data.float_32bit = lon;
                    write_tsd_evt_time(csb, csd, i, gps_data.uint_32bit, utc_time);
                }
                else if (csb[i].id == IMX_INTERNAL_SENSOR_GPS_ALTITUDE) {
                    gps_data.float_32bit = imx_get_altitude();
                    write_tsd_evt_time(csb, csd, i, gps_data.uint_32bit, utc_time);
                }
#ifdef CAN_PLATFORM
                else if (csb[i].id == IMX_INTERNAL_SENSOR_VEHICLE_SPEED) {
                    gps_data.float_32bit = imx_get_speed();
                    write_tsd_evt_time(csb, csd, i, gps_data.uint_32bit, utc_time);
                    break;      // Speed is the last entry
                }
#endif
            }
        }
    }
}

/**
 * @brief Write TSD or EVT data with specific timestamp using Memory Manager v2
 * @param csb Control sensor block pointer
 * @param csd Control sensor data pointer
 * @param entry Entry index to write
 * @param value Data value to write
 * @param utc_time UTC timestamp
 */
void write_tsd_evt_time(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                        uint16_t entry, uint32_t value, uint32_t utc_time)
{
    if (!csb || !csd) {
        return;
    }

    IMX_MUTEX_LOCK(&data_store_mutex);

    // Direct access to embedded v2 state - no lookup needed!
    unified_sensor_state_t *state = &csd[entry].v2_state;

    // Write using v2
    memory_error_t result = write_tsd_evt_unified(state, value, utc_time);

    if (result == MEMORY_SUCCESS) {
        // Update legacy fields to maintain compatibility
        csd[entry].no_samples = GET_AVAILABLE_RECORDS(state);
        csd[entry].last_sample_time = utc_time;
        csd[entry].last_value.uint_32bit = value;
        csd[entry].valid = 1;

        // Update data store info for compatibility
        #ifdef LINUX_PLATFORM
        csd[entry].ds.start_sector = state->first_sector;
        csd[entry].ds.end_sector = state->active_sector;
        csd[entry].ds.count = state->records_in_active;
        #else
        csd[entry].ds.start_sector = state->sector_number;
        csd[entry].ds.end_sector = state->sector_number;
        csd[entry].ds.count = GET_AVAILABLE_RECORDS(state);
        #endif

        PRINTF("Write TSD/EVT: Entry %u, Value %u, Time %u, Total records: %u\r\n",
               entry, value, utc_time, state->total_records);

        #ifdef LINUX_PLATFORM
        // Check if we need to flush to disk (80% RAM threshold)
        if (should_trigger_flush()) {
            PRINTF("RAM threshold reached, triggering flush to disk\r\n");
            flush_all_to_disk();
        }
        #endif
    } else {
        PRINTF("Write TSD/EVT failed: Entry %u, Error %d\r\n", entry, result);
    }

    IMX_MUTEX_UNLOCK(&data_store_mutex);
}

/**
 * @brief Read TSD or EVT data using Memory Manager v2
 * @param csb Control sensor block pointer
 * @param csd Control sensor data pointer
 * @param entry Entry index to read
 * @param value Pointer to store read value
 */
void read_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                  uint16_t entry, uint32_t *value)
{
    if (!csb || !csd || !value) {
        return;
    }

    IMX_MUTEX_LOCK(&data_store_mutex);

    // Direct access to embedded v2 state
    unified_sensor_state_t *state = &csd[entry].v2_state;

    // Check if data is available
    if (GET_AVAILABLE_RECORDS(state) == 0) {
        *value = 0;
        IMX_MUTEX_UNLOCK(&data_store_mutex);
        return;
    }

    // Read using v2
    uint32_t timestamp;
    memory_error_t result = read_tsd_evt_unified(state, value, &timestamp);

    if (result == MEMORY_SUCCESS) {
        // Update pending count
        csd[entry].no_pending++;

        PRINTF("Read TSD/EVT: Entry %u, Value %u, Pending: %u\r\n",
               entry, *value, csd[entry].no_pending);
    } else {
        PRINTF("Read TSD/EVT failed: Entry %u, Error %d\r\n", entry, result);
        *value = 0;
    }

    IMX_MUTEX_UNLOCK(&data_store_mutex);
}

/**
 * @brief Erase pending TSD/EVT data using Memory Manager v2
 * @param csb Control sensor block pointer
 * @param csd Control sensor data pointer
 * @param entry Entry index to erase
 */
void erase_tsd_evt(imx_control_sensor_block_t *csb, control_sensor_data_t *csd, uint16_t entry)
{
    if (!csb || !csd) {
        return;
    }

    IMX_MUTEX_LOCK(&data_store_mutex);

    // Direct access to embedded v2 state
    unified_sensor_state_t *state = &csd[entry].v2_state;

    // Check for impossible state
    if (csd[entry].ds.count == 0 && csd[entry].no_pending > 0) {
        imx_cli_log_printf(true, "IMPOSSIBLE STATE DETECTED: Entry %u (%s) has count=0 but pending=%u!\r\n",
                           entry, csb[entry].name, csd[entry].no_pending);
        imx_cli_log_printf(true, "  EMERGENCY RESET: Forcing complete metadata synchronization\r\n");

        // Reset to consistent state
        csd[entry].no_samples = 0;
        csd[entry].no_pending = 0;
        csd[entry].ds.count = 0;
        csd[entry].ds.start_index = 0;

        // Reset v2 state
        reset_unified_state(state);

        IMX_MUTEX_UNLOCK(&data_store_mutex);
        return;
    }

    if (csd[entry].no_pending == 0) {
        IMX_MUTEX_UNLOCK(&data_store_mutex);
        return;
    }

    uint16_t records_to_erase = csd[entry].no_pending;

    PRINTF("ERASE TSD/EVT: Entry %u (%s), Erasing %u records\r\n",
           entry, csb[entry].name, records_to_erase);

    // Erase using v2
    memory_error_t result = atomic_erase_records(state, records_to_erase);

    if (result == MEMORY_SUCCESS) {
        // Clear pending count
        csd[entry].no_pending = 0;

        // Update sample count
        csd[entry].no_samples = GET_AVAILABLE_RECORDS(state);

        // Update data store info
        csd[entry].ds.start_index = GET_READ_POSITION(state);

        PRINTF("  AFTER ERASE: no_samples=%u, available=%u\r\n",
               csd[entry].no_samples, GET_AVAILABLE_RECORDS(state));
    } else {
        PRINTF("Erase TSD/EVT failed: Entry %u, Error %d\r\n", entry, result);
    }

    IMX_MUTEX_UNLOCK(&data_store_mutex);
}

/**
 * @brief Revert pending TSD/EVT data
 *
 * Used when a transaction needs to be rolled back
 *
 * @param csb Control sensor block pointer
 * @param csd Control sensor data pointer
 * @param no_items Number of items to revert
 */
void revert_tsd_evt_pending_data(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                                 uint16_t no_items)
{
    if (!csb || !csd) {
        return;
    }

    for (uint16_t entry = 0; entry < no_items; entry++) {
        if (csd[entry].no_pending != 0) {
            // Just clear pending count - data remains in v2 state
            csd[entry].no_pending = 0;
        }
    }
}

/**
 * @brief Erase all pending data for multiple entries
 *
 * @param csb Control sensor block pointer
 * @param csd Control sensor data pointer
 * @param no_items Number of items to process
 */
void erase_tsd_evt_pending_data(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                                uint16_t no_items)
{
    if (!csb || !csd) {
        return;
    }

    for (uint16_t entry = 0; entry < no_items; entry++) {
        if (csd[entry].no_pending > 0) {
            erase_tsd_evt(csb, csd, entry);
        }
    }
}

/**
 * @brief Free application sectors
 *
 * @param csd Control sensor data pointer
 */
void imx_free_app_sectors(control_sensor_data_t *csd)
{
    // With v2, sectors are managed internally
    // This function is kept for compatibility but doesn't need to do anything
    PRINTF("imx_free_app_sectors: No-op with Memory Manager v2\r\n");
}

/**
 * @brief Reset a CSD entry
 *
 * @param csd Control sensor data pointer
 * @param entry Entry to reset
 */
void reset_csd_entry(control_sensor_data_t *csd, uint16_t entry)
{
    if (!csd) {
        return;
    }

    // Reset legacy fields
    csd[entry].no_samples = 0;
    csd[entry].no_pending = 0;
    csd[entry].errors = 0;
    csd[entry].ds.start_sector = INVALID_SECTOR;
    csd[entry].ds.end_sector = INVALID_SECTOR;
    csd[entry].ds.start_index = 0;
    csd[entry].ds.count = 0;
    csd[entry].valid = 0;

    // Reset v2 state
    reset_unified_state(&csd[entry].v2_state);
}

/**
 * @brief Initialize Memory Manager v2 for all CSDs
 *
 * This function should be called during system initialization
 */
void init_memory_manager_v2(void)
{
    #ifdef LINUX_PLATFORM
    // Create disk storage directories
    create_storage_directories();
    #endif

    // Initialize HOST CSD states
    control_sensor_data_t *host_cd = get_host_cd();
    control_sensor_data_t *host_sd = get_host_sd();

    if (host_cd) {
        uint16_t no_controls = get_host_no_controls();
        for (uint16_t i = 0; i < no_controls; i++) {
            init_unified_state(&host_cd[i].v2_state, false);
            host_cd[i].v2_state.csd_type = CSD_TYPE_HOST;
            host_cd[i].v2_state.sensor_id = i;
        }
        imx_cli_log_printf(false, "Initialized %u HOST control v2 states\r\n", no_controls);
    }

    if (host_sd) {
        uint16_t no_sensors = get_host_no_sensors();
        for (uint16_t i = 0; i < no_sensors; i++) {
            init_unified_state(&host_sd[i].v2_state, true);  // Event data for sensors
            host_sd[i].v2_state.csd_type = CSD_TYPE_HOST;
            host_sd[i].v2_state.sensor_id = i + 1000;  // Offset to distinguish from controls
        }
        imx_cli_log_printf(false, "Initialized %u HOST sensor v2 states\r\n", no_sensors);
    }

    #ifdef CAN_PLATFORM
    // Initialize CAN CSD states
    control_sensor_data_t *can_cd = get_can_cd();
    control_sensor_data_t *can_sd = get_can_sd();

    if (can_cd) {
        uint16_t no_controls = get_can_no_controls();
        for (uint16_t i = 0; i < no_controls; i++) {
            init_unified_state(&can_cd[i].v2_state, false);
            can_cd[i].v2_state.csd_type = CSD_TYPE_CAN_CONTROLLER;
            can_cd[i].v2_state.sensor_id = i + 2000;  // Offset for CAN controls
        }
        imx_cli_log_printf(false, "Initialized %u CAN control v2 states\r\n", no_controls);
    }

    if (can_sd) {
        uint16_t no_sensors = get_can_no_sensors();
        for (uint16_t i = 0; i < no_sensors; i++) {
            init_unified_state(&can_sd[i].v2_state, true);
            can_sd[i].v2_state.csd_type = CSD_TYPE_CAN_CONTROLLER;
            can_sd[i].v2_state.sensor_id = i + 3000;  // Offset for CAN sensors
        }
        imx_cli_log_printf(false, "Initialized %u CAN sensor v2 states\r\n", no_sensors);
    }
    #endif

    // MGC would be initialized here when implemented

    #ifdef LINUX_PLATFORM
    // Scan for and recover from disk
    imx_cli_log_printf(false, "Scanning for recovery data...\r\n");
    // recover_all_states_from_disk();  // TODO: Implement recovery
    #endif

    imx_cli_log_printf(false, "Memory Manager v2 initialization complete\r\n");
}