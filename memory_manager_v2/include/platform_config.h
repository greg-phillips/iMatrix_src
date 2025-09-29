/**
 * @file platform_config.h
 * @brief Platform Configuration and Simulation
 *
 * Unified platform configuration supporting both LINUX and WICED
 * platforms with simulation capabilities for testing.
 */

#ifndef PLATFORM_CONFIG_H
#define PLATFORM_CONFIG_H

#include <stdint.h>
#include <stdbool.h>

/******************************************************
 *                Platform Detection
 ******************************************************/

// Platform identification
#ifdef LINUX_PLATFORM
    #define CURRENT_PLATFORM_NAME "LINUX"
    #define PLATFORM_LINUX 1
    #define PLATFORM_WICED 0
#elif defined(WICED_PLATFORM)
    #define CURRENT_PLATFORM_NAME "WICED"
    #define PLATFORM_LINUX 0
    #define PLATFORM_WICED 1
#else
    #error "No platform defined. Use -DLINUX_PLATFORM or -DWICED_PLATFORM"
#endif

/******************************************************
 *           Platform-Specific Constants
 ******************************************************/

#ifdef LINUX_PLATFORM
    // LINUX Platform Configuration
    #define MAX_SECTORS                 1000000    // Extended sector addressing
    #define MAX_RAM_SECTORS             100        // Maximum RAM sectors before flush
    #define SECTOR_SIZE                 32         // Bytes per sector
    #define MAX_RECORDS_PER_SECTOR      8          // TSD records per sector
    #define MAX_EVENT_RECORDS_PER_SECTOR 4        // Event records per sector
    #define PLATFORM_SECTOR_TYPE        uint32_t   // 32-bit sector addressing
    #define INVALID_SECTOR              0xFFFFFFFF // Invalid sector marker
    #define MEMORY_FOOTPRINT_BUDGET     (2 * 1024) // 2KB memory budget for disk overflow testing
    #define DISK_OVERFLOW_SUPPORT       1          // Disk overflow enabled
    #define EXTENDED_VALIDATION         1          // Full validation enabled
    #define MUTEX_SUPPORT               1          // Full mutex support
    #define FILE_OPERATIONS_SUPPORT     1          // File I/O available
#else // WICED_PLATFORM
    // WICED Platform Configuration
    #define MAX_SECTORS                 2048       // 16-bit sector limit
    #define SECTOR_SIZE                 32         // Bytes per sector
    #define MAX_RECORDS_PER_SECTOR      8          // TSD records per sector
    #define MAX_EVENT_RECORDS_PER_SECTOR 4        // Event records per sector
    #define PLATFORM_SECTOR_TYPE        uint16_t   // 16-bit sector addressing
    #define INVALID_SECTOR              0xFFFF     // Invalid sector marker
    #define MEMORY_FOOTPRINT_BUDGET     (12 * 1024) // 12KB memory budget
    #define DISK_OVERFLOW_SUPPORT       0          // No disk available
    #define MINIMAL_VALIDATION          1          // Essential validation only
    #define MUTEX_SUPPORT               1          // Basic mutex support
    #define FILE_OPERATIONS_SUPPORT     0          // No file I/O
#endif

/******************************************************
 *              Universal Constants
 ******************************************************/

#define TSD_RECORD_SIZE                 4          // Time series data record size
#define EVT_RECORD_SIZE                 8          // Event data record size
#define MAX_SENSOR_ENTRIES              1200       // Maximum sensors supported
#define CHECKSUM_POLYNOMIAL             0x8408     // CRC-16 polynomial
#define INVALID_POSITION                0xFFFF     // Invalid position marker
#define OPERATION_SEQUENCE_MODULO       256        // Sequence counter wraparound
#define STATE_VALIDATION_INTERVAL       100        // Operations between validations

// Memory layout constants
#define METADATA_ALIGNMENT              4          // Memory alignment requirement
#define RESERVED_SECTORS                8          // System reserved sectors
#define SECTOR_HEADER_SIZE              8          // Sector metadata overhead
#define MAX_CHAIN_LENGTH                1000       // Maximum sector chain length

// Disk storage constants (LINUX_PLATFORM only)
#ifdef LINUX_PLATFORM
    #define DISK_STORAGE_PATH           "/usr/qk/etc/sv/FC-1/history/"
    #define RAM_THRESHOLD_PERCENT       80         // Trigger flush to disk at 80% RAM usage
    #define RAM_FULL_PERCENT           100         // RAM completely full
    #define MAX_DISK_FILE_SIZE         (64 * 1024) // 64KB max per disk file
    #define RECORDS_PER_DISK_SECTOR     16384      // Records per 64KB disk file (64KB / 4 bytes)
    #define MAX_DISK_STORAGE_BYTES     (256 * 1024 * 1024) // 256MB total disk limit
    #define CSD_DIR_HOST               "host/"     // CSD type 0 directory
    #define CSD_DIR_MGC                "mgc/"      // CSD type 1 directory
    #define CSD_DIR_CAN                "can_controller/" // CSD type 2 directory
    #define METADATA_FILENAME          "metadata.json"   // Metadata file for recovery
    #define SECTOR_FILE_PREFIX         "sector_"   // Prefix for sector data files
    #define SECTOR_FILE_EXTENSION      ".dat"      // Extension for sector data files
    #define DISK_FILE_TIMESTAMP_FORMAT "%Y%m%d_%H%M%S" // Timestamp format for files
    #define CONSUMPTION_BATCH_SIZE      100        // Read in batches for efficiency
#endif

// Performance and limits
#define MAX_PENDING_RECORDS             (MAX_RECORDS_PER_SECTOR * 2) // Pending limit
#define CORRUPTION_DETECTION_THRESHOLD  5          // Max corruption events before reset
#define PERFORMANCE_VALIDATION_INTERVAL 1000       // Operations between perf checks

/******************************************************
 *                Type Definitions
 ******************************************************/

/**
 * @brief Platform-adaptive sector type
 */
typedef PLATFORM_SECTOR_TYPE platform_sector_t;

/**
 * @brief Error codes for memory operations
 */
typedef enum {
    MEMORY_SUCCESS = 0,
    MEMORY_ERROR_INVALID_PARAMETER,
    MEMORY_ERROR_INSUFFICIENT_SPACE,
    MEMORY_ERROR_BOUNDS_VIOLATION,
    MEMORY_ERROR_CONSISTENCY_FAILURE,
    MEMORY_ERROR_INITIALIZATION_FAILED,
    MEMORY_ERROR_PLATFORM_UNSUPPORTED,
    MEMORY_ERROR_CHECKSUM_MISMATCH,
    MEMORY_ERROR_SEQUENCE_VIOLATION,
    MEMORY_ERROR_IMPOSSIBLE_STATE,
    MEMORY_ERROR_CORRUPTION_DETECTED,
    MEMORY_ERROR_DISK_FULL,
    MEMORY_ERROR_DISK_IO_FAILED,
    MEMORY_ERROR_MODE_TRANSITION_FAILED
} memory_error_t;

/**
 * @brief Operating modes for hybrid RAM/disk system
 */
typedef enum {
    MODE_RAM_ONLY = 0,          // Normal RAM operation
    MODE_DISK_ACTIVE,           // Disk mode active
    MODE_TRANSITIONING,         // During flush operation
    MODE_RECOVERING            // Startup recovery
} operation_mode_t;

#ifdef LINUX_PLATFORM
/**
 * @brief Disk file metadata structure for persistence
 */
typedef struct {
    uint32_t sector_id;              // Sector identifier
    uint32_t record_count;           // Records in this file
    uint32_t first_record_id;        // First record's sequence number
    uint32_t last_record_id;         // Last record's sequence number
    uint32_t checksum;               // File integrity check
    uint64_t timestamp;              // Creation/modification time
    uint32_t csd_type;               // CSD type (0=host, 1=mgc, 2=can)
    uint32_t file_size;              // Actual file size in bytes
} disk_sector_metadata_t;

/**
 * @brief Mode tracking per CSD for diagnostics
 */
typedef struct {
    operation_mode_t current_mode;    // Current operating mode
    uint32_t ram_usage_percent;       // Current RAM usage percentage
    uint32_t last_disk_sector;        // Last sector written to disk
    uint32_t current_disk_sector;     // Current sector being processed
    bool flush_in_progress;           // Flush operation active
    uint64_t mode_transition_count;   // Total mode transitions
    uint64_t records_dropped;         // Records dropped due to full conditions
    uint64_t last_flush_timestamp;    // Timestamp of last flush operation
} mode_state_t;

/**
 * @brief System-wide diagnostics structure
 */
typedef struct {
    uint64_t total_mode_transitions;
    uint64_t ram_to_disk_flushes;
    uint64_t disk_to_ram_switches;
    uint64_t records_dropped_ram_full;
    uint64_t records_dropped_disk_full;
    uint64_t recovery_operations;
    uint64_t disk_write_failures;
    uint64_t time_in_ram_mode_ms;
    uint64_t time_in_disk_mode_ms;
    double avg_ram_usage_percent;
    double avg_flush_time_ms;
} system_diagnostics_t;
#endif

/**
 * @brief Platform capabilities structure
 */
typedef struct {
    const char *platform_name;
    uint32_t max_sectors;
    uint32_t sector_size;
    uint32_t memory_budget;
    bool disk_overflow_supported;
    bool extended_validation_enabled;
    bool file_operations_available;
    uint16_t max_records_per_sector;
    uint16_t max_event_records_per_sector;
} platform_capabilities_t;

/******************************************************
 *               Function Declarations
 ******************************************************/

/**
 * @brief Get current platform capabilities
 */
const platform_capabilities_t *get_platform_capabilities(void);

/**
 * @brief Initialize platform-specific systems
 */
memory_error_t init_platform_systems(void);

/**
 * @brief Validate platform requirements
 */
bool validate_platform_requirements(void);

/**
 * @brief Get platform memory constraints
 */
uint32_t get_platform_memory_limit(void);

/**
 * @brief Check if platform supports feature
 */
bool platform_supports_disk_overflow(void);
bool platform_supports_extended_validation(void);
bool platform_supports_file_operations(void);

/**
 * @brief Platform-adaptive memory allocation
 */
platform_sector_t platform_allocate_sector(void);
memory_error_t platform_free_sector(platform_sector_t sector);

/**
 * @brief Platform logging and debug support
 */
void platform_log_info(const char *message);
void platform_log_error(const char *message);
void platform_log_debug(const char *message);

#endif /* PLATFORM_CONFIG_H */