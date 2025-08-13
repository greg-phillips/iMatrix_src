#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "storage.h"
#include "cs_ctrl/memory_manager.h"

// Test the disk_file_header_t structure size
typedef struct __attribute__((packed)) {
    uint32_t magic;                  // 0xDEADBEEF
    uint32_t version;                // File format version
    uint16_t sensor_id;              // Associated sensor
    uint16_t sector_count;           // Number of sectors in file
    uint16_t sector_size;            // Size of each sector (SRAM_SECTOR_SIZE)
    uint16_t record_type;            // TSD_RECORD_SIZE or EVT_RECORD_SIZE
    uint16_t entries_per_sector;     // NO_TSD_ENTRIES_PER_SECTOR or NO_EVT_ENTRIES_PER_SECTOR
    imx_utc_time_t created;          // File creation timestamp
    uint32_t file_checksum;          // Entire file checksum
    uint32_t reserved[4];            // Future expansion
} test_disk_file_header_t;

int main() {
    printf("Testing file creation issue...\n");
    printf("sizeof(disk_file_header_t) = %zu\n", sizeof(disk_file_header_t));
    printf("sizeof(test_disk_file_header_t) = %zu\n", sizeof(test_disk_file_header_t));
    printf("SRAM_SECTOR_SIZE = %d\n", SRAM_SECTOR_SIZE);
    
    // Test direct file creation
    FILE *fp = fopen("/tmp/test_file.bin", "wb");
    if (fp) {
        disk_file_header_t header;
        memset(&header, 0, sizeof(header));
        header.magic = 0xDEADBEEF;
        
        size_t header_written = fwrite(&header, 1, sizeof(header), fp);
        printf("Header bytes written: %zu\n", header_written);
        
        uint8_t data[SRAM_SECTOR_SIZE];
        memset(data, 0xAA, sizeof(data));
        size_t data_written = fwrite(data, 1, sizeof(data), fp);
        printf("Data bytes written: %zu\n", data_written);
        
        fclose(fp);
        
        // Check file size
        system("ls -la /tmp/test_file.bin");
    }
    
    return 0;
}