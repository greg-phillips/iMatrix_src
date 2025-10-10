/**
 * @file ss_crc.c
 * @brief CRC32C (Castagnoli) implementation for sensor storage integrity
 *
 * Fast software implementation using pre-calculated lookup table.
 * Optimized for embedded systems while maintaining good performance
 * on larger platforms.
 *
 * @author iMatrix Sensor Storage System
 * @date 2025
 */

#include "ss_crc.h"
#include <string.h>

/**
 * @brief CRC32C lookup table (256 entries)
 *
 * Pre-calculated table for fast CRC32C calculation using
 * the Castagnoli polynomial 0x82F63B78.
 */
static uint32_t crc32c_table[256];

/**
 * @brief Flag indicating if CRC table has been initialized
 */
static bool crc_table_initialized = false;

/**
 * @brief Generate CRC32C lookup table
 *
 * Builds the 256-entry lookup table used for fast CRC calculation.
 * Uses the Castagnoli polynomial for better error detection properties.
 */
static void generate_crc32c_table(void)
{
    uint32_t polynomial = SS_CRC32C_POLYNOMIAL;

    for (uint32_t i = 0; i < 256; i++) {
        uint32_t crc = i;

        for (int j = 0; j < 8; j++) {
            if (crc & 1) {
                crc = (crc >> 1) ^ polynomial;
            } else {
                crc >>= 1;
            }
        }

        crc32c_table[i] = crc;
    }

    crc_table_initialized = true;
}

int ss_crc32c_init(void)
{
    if (!crc_table_initialized) {
        generate_crc32c_table();
    }

    return 0;
}

uint32_t ss_crc32c_calculate(const void *data, size_t length)
{
    if (!crc_table_initialized) {
        ss_crc32c_init();
    }

    if (!data || length == 0) {
        return SS_CRC32C_INIT_VALUE ^ SS_CRC32C_FINAL_XOR;
    }

    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t crc = SS_CRC32C_INIT_VALUE;

    for (size_t i = 0; i < length; i++) {
        uint8_t table_index = (crc ^ bytes[i]) & 0xFF;
        crc = (crc >> 8) ^ crc32c_table[table_index];
    }

    return crc ^ SS_CRC32C_FINAL_XOR;
}

uint32_t ss_crc32c_start(void)
{
    if (!crc_table_initialized) {
        ss_crc32c_init();
    }

    return SS_CRC32C_INIT_VALUE;
}

uint32_t ss_crc32c_update(uint32_t crc, const void *data, size_t length)
{
    if (!crc_table_initialized) {
        ss_crc32c_init();
    }

    if (!data || length == 0) {
        return crc;
    }

    const uint8_t *bytes = (const uint8_t *)data;

    for (size_t i = 0; i < length; i++) {
        uint8_t table_index = (crc ^ bytes[i]) & 0xFF;
        crc = (crc >> 8) ^ crc32c_table[table_index];
    }

    return crc;
}

uint32_t ss_crc32c_finalize(uint32_t crc)
{
    return crc ^ SS_CRC32C_FINAL_XOR;
}

bool ss_crc32c_verify(const void *data, size_t length, uint32_t expected_crc)
{
    uint32_t calculated_crc = ss_crc32c_calculate(data, length);
    return calculated_crc == expected_crc;
}

uint32_t ss_crc32c_sector(const void *header, size_t header_size,
                          const void *payload, size_t payload_size)
{
    if (!crc_table_initialized) {
        ss_crc32c_init();
    }

    uint32_t crc = ss_crc32c_start();

    if (header && header_size > 0) {
        crc = ss_crc32c_update(crc, header, header_size);
    }

    if (payload && payload_size > 0) {
        crc = ss_crc32c_update(crc, payload, payload_size);
    }

    return ss_crc32c_finalize(crc);
}