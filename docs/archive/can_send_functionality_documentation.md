# CAN Send Functionality Documentation

## Overview
The iMatrix system provides comprehensive CAN bus transmission capabilities for sending messages on multiple CAN buses. This document details the CAN send functionality, including API usage, message structures, and transmission flow.

## Architecture

### Core Components

1. **High-Level API**: `write_can_message()` - Primary interface for CAN transmission
2. **Hardware Abstraction**: Platform-specific drivers (Quake hardware)
3. **Message Structures**: Standardized CAN message format
4. **Error Handling**: Comprehensive error detection and recovery

## CAN Message Structure

### can_msg_t Structure
```c
typedef struct can_msg {
    uint32_t can_id;                        // CAN identifier (11-bit or 29-bit)
    uint8_t can_data[MAX_CAN_FRAME_LENGTH]; // Data payload (up to 8 bytes)
    uint8_t can_dlc;                         // Data length code (0-8)
} can_msg_t;
```

**Field Descriptions:**
- `can_id`: The CAN identifier. Supports both standard (11-bit) and extended (29-bit) identifiers
- `can_data`: Array containing the message payload, maximum 8 bytes
- `can_dlc`: Data Length Code indicating the number of valid bytes in can_data

## Primary Send API

### write_can_message()

**Function Signature:**
```c
bool write_can_message(can_bus_t can_bus, can_msg_t *can_msg)
```

**Purpose:** Send a CAN message on the specified CAN bus

**Parameters:**
- `can_bus`: Target CAN bus (CAN_BUS_0, CAN_BUS_1)
- `can_msg`: Pointer to the message structure to send

**Returns:**
- `true`: Message successfully transmitted
- `false`: Transmission failed

**Location:** `/home/greg/iMatrix/iMatrix_Client/iMatrix/canbus/can_utils.c:959`

### Implementation Details

The function performs the following operations:

1. **Bus Selection**: Validates and selects the target CAN bus
2. **Statistics Tracking**: Updates transmission statistics
3. **Hardware Interface**: Calls platform-specific driver
4. **Error Handling**: Manages transmission errors and recovery
5. **Debug Logging**: Optional detailed logging of transmitted messages

### Code Flow

```c
bool write_can_message(can_bus_t can_bus, can_msg_t *can_msg)
{
    // 1. Select CAN bus and statistics structure
    if (can_bus == CAN_BUS_0) {
        can_stats = &cb.can0_stats;
        quake_canbus = DRV_CAN_0;
    } else if (can_bus == CAN_BUS_1) {
        can_stats = &cb.can1_stats;
        quake_canbus = DRV_CAN_1;
    }
    
    // 2. Log transmission (debug mode)
    PRINTF_CAN_DATA("[CAN BUS Send: %u - CAN ID: 0x%08lx...]");
    
    // 3. Send via hardware driver (thread-safe)
    pthread_mutex_lock(&canMutex);
    faultCode = CANEV_sendRawCan(quake_canbus, can_msg->can_id, 
                                  can_msg->can_data, can_msg->can_dlc);
    pthread_mutex_unlock(&canMutex);
    
    // 4. Handle result
    if (faultCode != 0) {
        // Error handling and recovery
        can_stats->tx_errors++;
        if (consecutive_errors > MAX_CONSECUTIVE_ERRORS) {
            init_physical_canbus_interface(); // Reset interface
        }
        return false;
    }
    
    // 5. Update statistics
    can_stats->tx_bytes += can_msg->can_dlc;
    can_stats->tx_frames++;
    return true;
}
```

## Hardware Driver Interface

### CANEV_sendRawCan()

**Function Signature:**
```c
FaultCode CANEV_sendRawCan(CanDrvInterface whichBus, uint32_t canId, 
                           uint8_t *buf, uint8_t bufLen)
```

**Purpose:** Low-level CAN transmission via Quake hardware

**Parameters:**
- `whichBus`: Hardware interface identifier (DRV_CAN_0, DRV_CAN_1)
- `canId`: CAN identifier to transmit
- `buf`: Pointer to data buffer
- `bufLen`: Number of bytes to transmit (max 8)

**Returns:**
- `OK` (0): Success
- Non-zero: Error code indicating failure reason

**Location:** `/home/greg/iMatrix/iMatrix_Client/iMatrix/quake/drivers/CanEvents.h:136`

## Usage Examples

### Example 1: Sending OBD2 Request

```c
// From process_obd2.c - OBD2 diagnostic message transmission
uint8_t simma_can_tx(can_t *frame)
{
    if (write_can_message(ODB2_CAN_BUS_INTERFACE, (can_msg_t *)frame) == true) {
        return 0;  // Success
    } else {
        return 1;  // Failure
    }
}
```

### Example 2: Direct CAN Message Send

```c
// Construct and send a CAN message
can_msg_t msg;
msg.can_id = 0x18FF4DF3;  // Extended CAN ID
msg.can_dlc = 8;           // 8 bytes of data

// Fill data payload
msg.can_data[0] = 0x01;
msg.can_data[1] = 0x02;
// ... fill remaining bytes

// Send on CAN bus 0
if (write_can_message(CAN_BUS_0, &msg)) {
    printf("Message sent successfully\n");
} else {
    printf("Send failed\n");
}
```

## Error Handling

### Error Recovery Mechanism

The system implements automatic error recovery:

1. **Error Counting**: Tracks consecutive transmission errors
2. **Threshold Detection**: Monitors for MAX_CONSECUTIVE_ERRORS (configurable)
3. **Interface Reset**: Automatically resets CAN interface after threshold
4. **Statistics Tracking**: Maintains transmission error statistics

### Error Types

Common fault codes from CANEV_sendRawCan():
- Bus off conditions
- Transmit buffer full
- Invalid parameters
- Hardware failures

## Statistics and Monitoring

### CAN Statistics Structure

```c
typedef struct can_stats {
    uint32_t tx_frames;   // Total frames transmitted
    uint32_t tx_bytes;    // Total bytes transmitted
    uint32_t tx_errors;   // Transmission errors
    // ... additional fields
} can_stats_t;
```

Statistics are maintained per CAN bus:
- `cb.can0_stats`: CAN Bus 0 statistics
- `cb.can1_stats`: CAN Bus 1 statistics

## Thread Safety

### Mutex Protection

All CAN transmissions are protected by mutex:
```c
pthread_mutex_lock(&canMutex);
// Hardware access
pthread_mutex_unlock(&canMutex);
```

This ensures:
- Thread-safe access to hardware
- Atomic transmission operations
- Prevention of message corruption

## Configuration

### Batch Sending

The system supports batch transmission control:

```c
bool get_can_send_batch(void);     // Check batch mode status
void set_can_send_batch(bool send_batch);  // Enable/disable batch mode
```

**Location:** `/home/greg/iMatrix/iMatrix_Client/iMatrix/canbus/can_imx_upload.h:78-80`

### Platform Configuration

Platform-specific compilation flags:
- `QUAKE_1180_5002`: Enable for Quake 1180-5002 hardware
- `QUAKE_1180_5102`: Enable for Quake 1180-5102 hardware

## Debug Support

### Debug Macros

Enable detailed CAN transmission logging:
```c
#define PRINTF_CAN_DATA(...)  \
    if (APP_LOGS_ENABLED(DEBUGS_APP_CAN_DATA)) { \
        imx_cli_log_printf(__VA_ARGS__); \
    }
```

Debug output includes:
- CAN bus number
- CAN ID (hex and decimal)
- Complete data payload
- Error messages and codes

## Integration Points

### OBD2 System
- **File**: `/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/OBD2/process_obd2.c`
- **Function**: `simma_can_tx()`
- **Purpose**: Send OBD2 diagnostic requests

### CAN Upload System
- **File**: `/home/greg/iMatrix/iMatrix_Client/iMatrix/canbus/can_imx_upload.c`
- **Functions**: Batch control and timing management
- **Purpose**: Manage CAN data upload to cloud

### Vehicle Registration
- **Usage**: Send registration messages during vehicle initialization
- **Context**: CAN controller registration flow

## CAN File Simulation Mode

### Overview
The CAN file simulation mode (`send_file_sim`) provides a sophisticated testing capability that simulates vehicle ignition cycling while sending CAN frames from a file. This mode is particularly useful for testing vehicle state transitions and system behavior under different ignition conditions.

### Command Usage
```bash
can send_file_sim [device] <filename>
```

**Parameters:**
- `device`: Optional CAN interface (can0, can1, caneth). Default: can0
- `filename`: Path to PCAN trace file containing CAN frames

### State Machine
The simulation operates on a 4-state cycle:

1. **IGNITION_OFF_WAIT** (30 seconds)
   - Sets `sim_ignition = false`
   - Vehicle systems see ignition as OFF
   - Speed returns 0
   
2. **IGNITION_ON_WAIT** (30 seconds)
   - Sets `sim_ignition = true`
   - Vehicle systems see ignition as ON
   - Prepares for file transmission
   
3. **FILE_SENDING**
   - Transmits CAN frames from file with original timing
   - Ignition remains ON
   - Normal vehicle operation simulation
   
4. **CYCLE_COMPLETE**
   - Returns to state 1
   - Continuous loop until stopped

### API Functions

#### send_can_ignition_state()
```c
bool send_can_ignition_state(void)
```
Returns the current simulated ignition state.

#### can_file_send_sim_start()
```c
void can_file_send_sim_start(uint8_t device, const char *filename)
```
Starts the simulation with specified device and file.

### System Integration

#### Vehicle State Functions
The simulation integrates with core vehicle state functions:

1. **imx_get_ignition()**
   - Checks if simulation is active
   - Returns simulated ignition state when in simulation mode
   - Falls back to hardware detection when not simulating

2. **imx_get_speed()**
   - Returns 0 when simulation ignition is OFF
   - Returns actual CAN/GPS speed when ignition is ON
   - Ensures realistic vehicle behavior during simulation

### Implementation Details

#### State Variables
```c
static bool sim_mode_active = false;      // Simulation mode flag
static bool sim_ignition = false;         // Current ignition state
static imx_time_t sim_state_start_time;   // State transition timing
static const uint32_t SIM_STATE_WAIT_MS = 30000;  // 30-second intervals
```

#### Timing Control
- Uses `imx_is_later()` for accurate millisecond timing
- 30-second intervals between state transitions
- Real-time file playback during transmission phase

### Use Cases

1. **Testing Power Management**
   - Verify system behavior during ignition transitions
   - Test power-down sequences
   - Validate wake-up procedures

2. **CAN Data Validation**
   - Replay recorded vehicle sessions
   - Test with known good/bad data sets
   - Validate signal processing

3. **System Integration Testing**
   - Test full system response to ignition cycles
   - Verify data logging during state changes
   - Validate event generation

### Example Session
```bash
# Start simulation with recorded data
can send_file_sim can0 /data/vehicle_trace.trc

# Output:
Starting CAN file simulation:
  File: /data/vehicle_trace.trc
  Device: can0
  Mode: Simulation with ignition cycling
  State: IGNITION OFF (30s)

# After 30 seconds:
Simulation: IGNITION ON (30s)

# After another 30 seconds:
Simulation: Starting file transmission
[CAN frames transmitted...]

# After file completion:
Simulation: File complete, restarting cycle
Simulation: IGNITION OFF (30s)

# Stop simulation
can send_file_stop
```

### Debug Support
Enable CAN data logging to monitor simulation:
```bash
debug DEBUGS_APP_CAN_DATA
```

### Limitations
- File must be in PCAN trace format
- 30-second intervals are fixed (not configurable)
- Single file per simulation session
- File is reopened for each cycle

## Best Practices

1. **Always Check Return Values**: Verify transmission success
2. **Use Appropriate Bus**: Ensure correct CAN bus selection
3. **Validate Message Data**: Check DLC and data validity before sending
4. **Handle Errors Gracefully**: Implement retry logic where appropriate
5. **Monitor Statistics**: Track transmission performance
6. **Thread Safety**: Always use provided APIs, not direct hardware access

## Limitations

- Maximum data payload: 8 bytes per CAN frame
- Extended frames require appropriate CAN ID format
- Hardware-dependent transmission rate limits
- Consecutive error threshold triggers interface reset

## Summary

The CAN send functionality provides a robust, thread-safe mechanism for transmitting CAN messages across multiple buses. The layered architecture separates high-level API from hardware specifics, while comprehensive error handling ensures system reliability. The integration with OBD2, upload systems, and vehicle registration demonstrates its versatility in the iMatrix ecosystem.