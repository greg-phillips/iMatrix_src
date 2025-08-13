/**
 * @file ultra_minimal_test.c
 * @brief Ultra minimal test to debug stack issues
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

// Include iMatrix headers
#include "storage.h"
#include "device/icb_def.h"
#include "imatrix.h"
#include "cs_ctrl/memory_manager.h"

// External variables from storage.c
extern iMatrix_Control_Block_t icb;
extern IOT_Device_Config_t device_config;

int main(void)
{
    printf("Ultra minimal test - Testing init_ext_memory\n");
    
    // Just clear the structures
    printf("Clearing structures...\n");
    memset(&icb, 0, sizeof(iMatrix_Control_Block_t));
    memset(&device_config, 0, sizeof(IOT_Device_Config_t));
    
    // Set minimal required fields
    device_config.ext_sram_size = 0;
    device_config.slave_processor = false;
    
    printf("About to call init_ext_memory(0)...\n");
    printf("Stack check before init_ext_memory\n");
    fflush(stdout);
    init_ext_memory(0);
    printf("Returned from init_ext_memory\n");
    fflush(stdout);
    
    printf("Getting memory statistics...\n");
    imx_memory_statistics_t *stats = imx_get_memory_statistics();
    if (stats) {
        printf("Total sectors: %u\n", stats->total_sectors);
        printf("Free sectors: %u\n", stats->free_sectors);
    }
    
    printf("Allocating a sector...\n");
    platform_sector_t sector = imx_get_free_sector();
    if (sector != PLATFORM_INVALID_SECTOR) {
        printf("Allocated sector: %u\n", sector);
        
        // Test writing a small amount of data
        printf("Writing 1 uint32_t to sector...\n");
        uint32_t test_data = 0xDEADBEEF;
        write_rs(sector, 0, &test_data, 1);  // Write 1 uint32_t value
        printf("Write completed\n");
        
        // Test reading back
        printf("Reading 1 uint32_t from sector...\n");
        uint32_t read_data = 0;
        read_rs(sector, 0, &read_data, 1);  // Read 1 uint32_t value
        printf("Read data: 0x%08X\n", read_data);
        
        printf("Freeing sector...\n");
        free_sector(sector);
        printf("Sector freed\n");
    }
    
    printf("Test completed without crash!\n");
    return 0;
}