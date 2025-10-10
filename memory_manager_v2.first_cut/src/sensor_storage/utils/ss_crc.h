/**
 * @file ss_crc.h
 * @brief CRC32C (Castagnoli) implementation for sensor storage integrity
 *
 * Provides fast CRC32C calculation for sector integrity checking.
 * CRC32C is preferred over standard CRC32 for better error detection
 * properties and hardware acceleration availability on some platforms.
 *
 * Features:
 * - Software table-based implementation (fast on all platforms)
 * - Incremental CRC calculation support
 * - Optimized for both small (STM32) and large (Linux) sectors
 * - Platform-agnostic interface
 *
 * @author iMatrix Sensor Storage System
 * @date 2025
 */

#ifndef SS_CRC_H
#define SS_CRC_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief CRC32C polynomial (Castagnoli)
 */
#define SS_CRC32C_POLYNOMIAL 0x82F63B78

/**
 * @brief CRC32C initial value
 */
#define SS_CRC32C_INIT_VALUE 0xFFFFFFFF

/**
 * @brief CRC32C final XOR value
 */
#define SS_CRC32C_FINAL_XOR 0xFFFFFFFF

/**
 * @brief Initialize CRC32C lookup table
 *
 * Must be called once during system initialization before using
 * any CRC functions. This function is thread-safe and idempotent.
 *
 * @return 0 on success, negative error code on failure
 */
int ss_crc32c_init(void);

/**
 * @brief Calculate CRC32C for a buffer
 *
 * Calculates complete CRC32C checksum for the given data buffer.
 * This is the most common function for single-pass CRC calculation.
 *
 * @param data Pointer to data buffer
 * @param length Number of bytes to process
 * @return CRC32C checksum value
 */
uint32_t ss_crc32c_calculate(const void *data, size_t length);

/**
 * @brief Start incremental CRC32C calculation
 *
 * Initializes CRC state for incremental calculation across multiple
 * data segments. Use with ss_crc32c_update() and ss_crc32c_finalize().
 *
 * @return Initial CRC state value
 */
uint32_t ss_crc32c_start(void);

/**
 * @brief Update incremental CRC32C with more data
 *
 * Continues CRC calculation with additional data. Can be called
 * multiple times to process data in chunks.
 *
 * @param crc Current CRC state from ss_crc32c_start() or previous update
 * @param data Pointer to additional data
 * @param length Number of bytes to process
 * @return Updated CRC state value
 */
uint32_t ss_crc32c_update(uint32_t crc, const void *data, size_t length);

/**
 * @brief Finalize incremental CRC32C calculation
 *
 * Completes incremental CRC calculation and returns final checksum.
 * The CRC state should not be used after this call.
 *
 * @param crc Final CRC state from ss_crc32c_update()
 * @return Final CRC32C checksum value
 */
uint32_t ss_crc32c_finalize(uint32_t crc);

/**
 * @brief Verify data integrity using CRC32C
 *
 * Convenience function that calculates CRC32C for data and compares
 * against expected checksum. Returns true if checksums match.
 *
 * @param data Pointer to data buffer
 * @param length Number of bytes to verify
 * @param expected_crc Expected CRC32C value
 * @return true if CRC matches, false if corruption detected
 */
bool ss_crc32c_verify(const void *data, size_t length, uint32_t expected_crc);

/**
 * @brief Calculate CRC32C for sector header + payload
 *
 * Specialized function for sector CRC calculation that processes
 * the sector header (excluding CRC field) and payload data.
 *
 * @param header Pointer to sector header structure
 * @param header_size Size of header structure
 * @param payload Pointer to sector payload data
 * @param payload_size Size of payload data
 * @return CRC32C checksum for sector
 */
uint32_t ss_crc32c_sector(const void *header, size_t header_size,
                          const void *payload, size_t payload_size);

#ifdef __cplusplus
}
#endif

#endif /* SS_CRC_H */