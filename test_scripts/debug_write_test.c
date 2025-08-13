#include <stdio.h>
#include <stdint.h>
#include <string.h>

int main() {
    // Test data similar to what's used in the test
    uint32_t test_data[4] = {0x12345678, 0x9ABCDEF0, 0xFEDCBA98, 0x87654321};
    
    // Show what's in memory
    printf("Test data as uint32_t array:\n");
    for (int i = 0; i < 4; i++) {
        printf("  [%d]: 0x%08X\n", i, test_data[i]);
    }
    
    printf("\nTest data as bytes:\n");
    uint8_t *byte_ptr = (uint8_t*)test_data;
    for (int i = 0; i < 16; i++) {
        printf("  byte[%2d]: 0x%02X", i, byte_ptr[i]);
        if (i % 4 == 3) printf(" (from uint32_t[%d])", i/4);
        printf("\n");
    }
    
    // Write to file using fwrite
    FILE *fp = fopen("test_write.bin", "wb");
    if (fp) {
        size_t written = fwrite(test_data, 1, 16, fp);
        printf("\nWrote %zu bytes to file\n", written);
        fclose(fp);
        
        // Read it back
        uint32_t read_data[4] = {0};
        fp = fopen("test_write.bin", "rb");
        if (fp) {
            size_t read = fread(read_data, 1, 16, fp);
            printf("Read %zu bytes from file\n", read);
            fclose(fp);
            
            printf("\nRead data as uint32_t array:\n");
            for (int i = 0; i < 4; i++) {
                printf("  [%d]: 0x%08X\n", i, read_data[i]);
            }
        }
    }
    
    return 0;
}