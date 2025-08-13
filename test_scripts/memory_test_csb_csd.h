/**
 * @file memory_test_csb_csd.h
 * @brief CSB/CSD structures initialization for memory tests
 * 
 * This header provides functions to initialize proper Control Sensor Block (CSB)
 * and Control Sensor Data (CSD) structures for comprehensive memory testing.
 * 
 * @author Greg Phillips
 * @date 2025-01-09
 * @copyright iMatrix Systems, Inc.
 */

#ifndef MEMORY_TEST_CSB_CSD_H_
#define MEMORY_TEST_CSB_CSD_H_

#include <stdint.h>
#include <stdbool.h>
#include "imatrix.h"
#include "common.h"
#include "device/icb_def.h"

/******************************************************
 *                    Constants
 ******************************************************/

// Test sensor/control counts
#define TEST_NUM_SENSORS        8
#define TEST_NUM_CONTROLS       4

// Test sensor IDs
#define TEST_TEMP_SENSOR_ID     1001
#define TEST_PRESSURE_SENSOR_ID 1002
#define TEST_HUMIDITY_SENSOR_ID 1003
#define TEST_VOLTAGE_SENSOR_ID  1004
#define TEST_CURRENT_SENSOR_ID  1005
#define TEST_SPEED_SENSOR_ID    1006
#define TEST_ACCEL_SENSOR_ID    1007
#define TEST_GPS_SENSOR_ID      1008

// Test control IDs
#define TEST_RELAY_CONTROL_ID   2001
#define TEST_PWM_CONTROL_ID     2002
#define TEST_MODE_CONTROL_ID    2003
#define TEST_ENABLE_CONTROL_ID  2004

/******************************************************
 *               Function Declarations
 ******************************************************/

/**
 * @brief Initialize test sensor CSB/CSD structures
 * 
 * Creates realistic sensor definitions for testing including:
 * - Temperature, pressure, humidity sensors (periodic sampling)
 * - Voltage, current sensors (high-frequency sampling)
 * - Speed, acceleration sensors (event-driven)
 * - GPS sensor (low-frequency sampling)
 * 
 * @param icb Pointer to iMatrix Control Block
 * @return IMX_SUCCESS on success, IMX_FAIL on failure
 */
imx_status_t init_test_sensors(iMatrix_Control_Block_t *icb);

/**
 * @brief Initialize test control CSB/CSD structures
 * 
 * Creates realistic control definitions for testing including:
 * - Relay control (on/off)
 * - PWM control (0-100%)
 * - Mode control (enum values)
 * - Enable/disable control
 * 
 * @param icb Pointer to iMatrix Control Block
 * @return IMX_SUCCESS on success, IMX_FAIL on failure
 */
imx_status_t init_test_controls(iMatrix_Control_Block_t *icb);

/**
 * @brief Populate test sensor with sample data
 * 
 * Generates realistic sample data for a sensor including:
 * - Time-stamped values
 * - Trending data
 * - Periodic variations
 * 
 * @param sensor_index Index of sensor in array
 * @param num_samples Number of samples to generate
 * @return IMX_SUCCESS on success, IMX_FAIL on failure
 */
imx_status_t populate_sensor_data(uint16_t sensor_index, uint32_t num_samples);

/**
 * @brief Populate test control with event data
 * 
 * Generates realistic event data for a control including:
 * - State changes
 * - User commands
 * - System events
 * 
 * @param control_index Index of control in array
 * @param num_events Number of events to generate
 * @return IMX_SUCCESS on success, IMX_FAIL on failure
 */
imx_status_t populate_control_data(uint16_t control_index, uint32_t num_events);

/**
 * @brief Display CSB information
 * 
 * Prints detailed information about a Control Sensor Block
 * for debugging and verification.
 * 
 * @param csb Pointer to CSB structure
 * @param is_sensor true if sensor, false if control
 */
void print_csb_info(const imx_control_sensor_block_t *csb, bool is_sensor);

/**
 * @brief Display CSD information
 * 
 * Prints detailed information about Control Sensor Data
 * for debugging and verification.
 * 
 * @param csd Pointer to CSD structure
 * @param csb Pointer to associated CSB structure
 */
void print_csd_info(const control_sensor_data_t *csd, const imx_control_sensor_block_t *csb);

/**
 * @brief Verify data integrity
 * 
 * Verifies that written data can be read back correctly
 * and maintains integrity through the memory system.
 * 
 * @param sensor_index Index of sensor to verify
 * @return true if data is intact, false otherwise
 */
bool verify_sensor_data_integrity(uint16_t sensor_index);

/**
 * @brief Test TSD operations with proper CSB/CSD
 * 
 * Comprehensive test of Time Series Data operations using
 * properly initialized CSB/CSD structures.
 * 
 * @return Number of test failures (0 = all passed)
 */
int test_tsd_with_proper_structures(void);

/**
 * @brief Test EVT operations with proper CSB/CSD
 * 
 * Comprehensive test of Event data operations using
 * properly initialized CSB/CSD structures.
 * 
 * @return Number of test failures (0 = all passed)
 */
int test_evt_with_proper_structures(void);

/**
 * @brief Cleanup test CSB/CSD structures
 * 
 * Frees all allocated memory and resets structures.
 */
void cleanup_test_csb_csd(void);

#endif /* MEMORY_TEST_CSB_CSD_H_ */