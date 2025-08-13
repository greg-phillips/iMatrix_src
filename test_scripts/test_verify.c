#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "../iMatrix/storage.h"
#include "../iMatrix/cs_ctrl/memory_manager.h"
#include "../iMatrix/cs_ctrl/memory_manager_stats.h"
#include "../iMatrix/device/icb_def.h"
#include "memory_test_init.h"
#include "memory_test_csb_csd.h"

// External ICB structure
extern iMatrix_Control_Block_t icb;

int main(void) {
    printf("==============================================\n");
    printf("        iMatrix Verify Test\n");
    printf("==============================================\n\n");

    // Initialize test environment
    if (!init_memory_test_env()) {
        printf("ERROR: Failed to initialize test environment\n");
        return 1;
    }

    // Initialize test CSB/CSD structures  
    init_test_csb_csd();

    // Allocate and write some test data
    printf("1. Writing test data to sensors...\n");
    
    for (int i = 0; i < 3; i++) {
        imx_control_sensor_block_t *csb = &test_sensor_blocks[i];
        control_sensor_data_t *csd = &test_sensor_data[i];
        
        // Write some test values
        for (int j = 0; j < 10; j++) {
            uint32_t value = (i + 1) * 1000 + j;
            write_tsd_evt(csb, csd, j, value, false);
        }
        printf("   - Wrote 10 values to sensor %s\n", csb->name);
    }
    
    printf("\n2. Writing test data to controls...\n");
    for (int i = 0; i < 2; i++) {
        imx_control_sensor_block_t *ccb = &test_control_blocks[i];
        control_sensor_data_t *ccd = &test_control_data[i];
        
        // Write some test values
        for (int j = 0; j < 5; j++) {
            uint32_t value = (i + 1) * 100 + j;
            write_tsd_evt(ccb, ccd, j, value, false);
        }
        printf("   - Wrote 5 values to control %s\n", ccb->name);
    }

    printf("\n3. Running 'ms verify' command...\n");
    printf("----------------------------------------\n");
    
    // Call the memory stats CLI function with verify option (7)
    cli_memory_stats(7);
    
    printf("----------------------------------------\n");
    printf("\n4. Test complete\n");

    // Cleanup
    cleanup_test_csb_csd();
    cleanup_memory_test_env();
    
    return 0;
}