/**
 * @file size_check_test.c
 * @brief Check sizes of critical structures
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>

// Include iMatrix headers
#include "storage.h"
#include "device/icb_def.h"
#include "imatrix.h"

// External variables
extern iMatrix_Control_Block_t icb;
extern IOT_Device_Config_t device_config;

int main(void)
{
    printf("=== Size Check Test ===\n");
    
    printf("Storage constants:\n");
    printf("  SRAM_SECTOR_SIZE = %d\n", SRAM_SECTOR_SIZE);
    printf("  SAT_NO_SECTORS = %d\n", SAT_NO_SECTORS);
    printf("  INTERNAL_RS_LENGTH = %d\n", INTERNAL_RS_LENGTH);
    printf("  NO_SAT_BLOCKS = %d\n", NO_SAT_BLOCKS);
    
    printf("\nStructure sizes:\n");
    printf("  sizeof(iMatrix_Control_Block_t) = %lu\n", sizeof(iMatrix_Control_Block_t));
    printf("  sizeof(IOT_Device_Config_t) = %lu\n", sizeof(IOT_Device_Config_t));
    printf("  sizeof(sector_assignment_table_t) = %lu\n", sizeof(sector_assignment_table_t));
    
    printf("\nAddresses:\n");
    printf("  &icb = %p\n", (void*)&icb);
    printf("  &device_config = %p\n", (void*)&device_config);
    
    printf("\nExpected rs array size = SAT_NO_SECTORS * SRAM_SECTOR_SIZE = %d * %d = %d bytes\n",
           SAT_NO_SECTORS, SRAM_SECTOR_SIZE, SAT_NO_SECTORS * SRAM_SECTOR_SIZE);
    
    printf("\n=== Test completed ===\n");
    return 0;
}