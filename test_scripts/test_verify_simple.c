#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// Minimal includes needed for cli_memory_stats
#include "../iMatrix/storage.h"
#include "../iMatrix/cs_ctrl/memory_manager_stats.h"
#include "../iMatrix/device/icb_def.h"
#include "memory_test_init.h"
#include "memory_test_csb_csd.h"

// External ICB structure
extern iMatrix_Control_Block_t icb;
extern IOT_Device_Config_t device_config;

int main(void) {
    printf("==============================================\n");
    printf("        iMatrix Verify Command Test\n");
    printf("==============================================\n\n");

    // Initialize test environment
    if (!init_memory_test_env()) {
        printf("ERROR: Failed to initialize test environment\n");
        return 1;
    }

    // Initialize test CSB/CSD structures  
    init_test_csb_csd();

    printf("1. Writing test data...\n");
    
    // Allocate some test sectors and write data
    for (int i = 0; i < 5; i++) {
        int32_t sector = imx_get_free_sector();
        if (sector >= 0) {
            uint32_t test_data[4] = {i, i+1, i+2, i+3};
            write_rs((platform_sector_t)sector, 0, test_data, 4);
            printf("   - Wrote data to sector %d\n", sector);
        }
    }

    printf("\n2. Running 'ms verify' command...\n");
    printf("========================================\n");
    
    // Call the memory stats CLI function with verify option (7)
    cli_memory_stats(7);
    
    printf("========================================\n");
    printf("\n3. Test complete\n");

    // Cleanup
    cleanup_test_csb_csd();
    cleanup_memory_test_env();
    
    return 0;
}