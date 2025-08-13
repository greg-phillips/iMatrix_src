#include <stdio.h>
#include <stdint.h>

int main() {
    uint32_t test_data[4] = {0x12345678, 0x9ABCDEF0, 0xFEDCBA98, 0x87654321};
    
    printf("sizeof(test_data) = %zu bytes\n", sizeof(test_data));
    printf("test_data[0] = 0x%08X\n", test_data[0]);
    printf("test_data[1] = 0x%08X\n", test_data[1]);
    printf("test_data[2] = 0x%08X\n", test_data[2]);
    printf("test_data[3] = 0x%08X\n", test_data[3]);
    
    return 0;
}