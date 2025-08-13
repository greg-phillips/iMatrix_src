/**
 * @file bare_minimal_test.c
 * @brief Bare minimal test - just init_ext_memory
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
    printf("Bare minimal test - Only init_ext_memory\n");
    
    // Just clear the structures
    memset(&icb, 0, sizeof(iMatrix_Control_Block_t));
    memset(&device_config, 0, sizeof(IOT_Device_Config_t));
    
    // Set minimal required fields
    device_config.ext_sram_size = 0;
    device_config.slave_processor = false;
    
    init_ext_memory(0);
    
    printf("Test completed\n");
    fflush(stdout);
    return 0;
}