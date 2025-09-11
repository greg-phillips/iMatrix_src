# CAN File Send API Reference

## Overview
The CAN File Send module provides comprehensive functionality for transmitting CAN frames from PCAN trace files. It supports multiple operation modes including real-time playback, debug mode, test mode, and ignition simulation mode.

## File Format Support

### PCAN Trace Format
```
;$FILEVERSION=2.0
;$STARTTIME=45123.456789
;   Time        Type  ID         Data
   0.000000     Rx    18FF4DF3   01 02 03 04 05 06 07 08
   0.123456     Rx    123        AA BB CC
```

### Simplified Format
```
18FF2DF3  8  F2 FA 13 14 2B 57 B4 DC
123       3  AA BB CC
```

## API Functions

### Core Functions

#### can_file_send_init()
```c
void can_file_send_init(void)
```
**Purpose:** Initialize the CAN file send module  
**Parameters:** None  
**Returns:** None  
**Notes:** Called during system initialization

#### can_file_send_set_filename()
```c
void can_file_send_set_filename(const char *filename)
```
**Purpose:** Set the filename for upload  
**Parameters:**
- `filename`: Path to the PCAN trace file  
**Returns:** None  
**Notes:** Must be called before starting upload

#### can_file_send_start()
```c
void can_file_send_start(uint8_t mode, uint8_t device)
```
**Purpose:** Start file upload with specified mode  
**Parameters:**
- `mode`: Operation mode (0=normal, 1=debug, 2=test)
- `device`: CAN interface (0=can0, 1=can1, 2=caneth)  
**Returns:** None  
**Notes:** Creates sender thread for high-performance transmission

#### can_file_send_stop()
```c
void can_file_send_stop(void)
```
**Purpose:** Stop the file upload process  
**Parameters:** None  
**Returns:** None  
**Notes:** Cleanly terminates thread and closes file

#### can_file_send_request_stop()
```c
void can_file_send_request_stop(void)
```
**Purpose:** Request stop of file upload (user initiated)  
**Parameters:** None  
**Returns:** None  
**Notes:** Sets flag for clean shutdown on next cycle

#### can_file_send_process()
```c
void can_file_send_process(imx_time_t current_time)
```
**Purpose:** Process the file upload state machine  
**Parameters:**
- `current_time`: Current system time in milliseconds  
**Returns:** None  
**Notes:** Called periodically from main loop

### Simulation Mode Functions

#### can_file_send_sim_start()
```c
void can_file_send_sim_start(uint8_t device, const char *filename)
```
**Purpose:** Start CAN file simulation with ignition cycling  
**Parameters:**
- `device`: CAN device (0=can0, 1=can1, 2=caneth)
- `filename`: Path to PCAN trace file  
**Returns:** None  
**Notes:** Initiates 4-state simulation cycle

#### send_can_ignition_state()
```c
bool send_can_ignition_state(void)
```
**Purpose:** Get current simulated ignition state  
**Parameters:** None  
**Returns:** 
- `true`: Ignition is ON
- `false`: Ignition is OFF  
**Notes:** Valid only during simulation mode

#### imx_can_file_sim_active()
```c
bool imx_can_file_sim_active(void)
```
**Purpose:** Check if simulation mode is active  
**Parameters:** None  
**Returns:**
- `true`: Simulation is running
- `false`: Normal operation  
**Notes:** Used by vehicle state functions

### Status Functions

#### can_file_send_print_status()
```c
void can_file_send_print_status(void)
```
**Purpose:** Print current upload status  
**Parameters:** None  
**Returns:** None  
**Notes:** Displays detailed statistics and state

#### can_file_send_get_state()
```c
can_file_state_t can_file_send_get_state(void)
```
**Purpose:** Get current state machine state  
**Parameters:** None  
**Returns:** Current state enum value  
**Notes:** For debugging and monitoring

#### imx_can_test_mode()
```c
bool imx_can_test_mode(void)
```
**Purpose:** Check if system is in test mode  
**Parameters:** None  
**Returns:**
- `true`: Test mode active (reading from file)
- `false`: Normal operation  
**Notes:** Excludes display-only mode

## State Machine

### Normal States
```c
typedef enum {
    CAN_FILE_IDLE = 0,           // Waiting for command
    CAN_FILE_UPLOAD_INIT,        // Opening file
    CAN_FILE_UPLOAD_READING,     // Reading frames
    CAN_FILE_UPLOAD_WAITING,     // Timing control
    CAN_FILE_UPLOAD_SENDING,     // Transmitting
    CAN_FILE_UPLOAD_COMPLETE,    // Finished
    CAN_FILE_UPLOAD_ERROR        // Error occurred
} can_file_state_t;
```

### Simulation States
```c
    CAN_FILE_SIM_IGNITION_OFF_WAIT,  // Ignition off (30s)
    CAN_FILE_SIM_IGNITION_ON_WAIT,   // Ignition on (30s)
    CAN_FILE_SIM_SENDING,             // Sending file
    CAN_FILE_SIM_CYCLE_COMPLETE       // Restart cycle
```

## Operation Modes

### Mode 0: Real-Time Playback
- Sends frames with original timing from file
- Maintains inter-frame delays
- High-performance threaded operation

### Mode 1: Debug Mode
- Sends one frame per second
- Useful for debugging and analysis
- Allows detailed observation

### Mode 2: Test Mode
- Displays frames without sending
- Validates file format
- No CAN bus transmission

### Simulation Mode
- 30-second ignition OFF period
- 30-second ignition ON period
- File transmission during ON state
- Continuous cycle until stopped

## CLI Commands

### Basic Commands
```bash
# Send file with real-time timing
can send_file [device] <filename>

# Send file in debug mode (1 fps)
can send_debug_file [device] <filename>

# Display file without sending
can send_test_file [device] <filename>

# Simulation mode with ignition cycling
can send_file_sim [device] <filename>

# Stop any active upload
can send_file_stop

# Display current status
can send_file_status
```

### Examples
```bash
# Default device (can0)
can send_file /data/trace.trc

# Specific device
can send_file can1 /data/trace.trc

# Simulation mode
can send_file_sim caneth /data/vehicle.trc

# Stop upload
can send_file_stop
```

## Integration Points

### Vehicle State Functions
The simulation mode integrates with:

#### imx_get_ignition()
- Returns simulated state during simulation
- Falls back to hardware when not simulating

#### imx_get_speed()
- Returns 0 when simulation ignition is OFF
- Normal speed processing when ON

### Thread Architecture
- Main thread: State machine control
- Sender thread: High-performance transmission
- Buffer size: 100 frames
- Thread sleep: 100 microseconds

## Configuration

### Compile-Time Options
```c
#define DEBUG_SEND_INTERVAL_MS  1000   // Debug mode interval
#define FRAME_BUFFER_SIZE       100    // Frame buffer size
#define THREAD_SLEEP_US         100    // Thread sleep time
#define SUMMARY_INTERVAL_MS     10000  // Status update interval
```

### Runtime Configuration
- Device selection (can0, can1, caneth)
- Mode selection (normal, debug, test, simulation)
- File path specification

## Error Handling

### Common Errors
- File not found
- Invalid file format
- CAN transmission failure
- Thread creation failure

### Recovery
- Automatic cleanup on error
- Thread termination handling
- File handle cleanup
- State reset to IDLE

## Performance

### Metrics
- Frame buffer: 100 frames
- Thread sleep: 100μs
- Summary interval: 10 seconds
- Simulation intervals: 30 seconds

### Optimization
- Threaded transmission
- Buffered file reading
- Mutex-protected shared data
- Efficient timing control

## Limitations

1. **File Format:** PCAN trace or simplified format only
2. **Data Length:** Maximum 8 bytes per frame
3. **Timing:** Millisecond precision
4. **Buffer:** 100 frames maximum
5. **Simulation:** Fixed 30-second intervals

## Best Practices

1. **File Validation:** Test with display mode first
2. **Device Selection:** Verify correct CAN bus
3. **Timing Accuracy:** Use real-time mode for replay
4. **Resource Cleanup:** Always use stop command
5. **Error Monitoring:** Check status regularly

## Troubleshooting

### Upload Not Starting
- Check file exists and is readable
- Verify no other upload is active
- Confirm valid device selection

### Frames Not Sending
- Check CAN bus connection
- Verify interface is initialized
- Monitor error statistics

### Simulation Issues
- Ensure file is valid format
- Check ignition state transitions
- Verify integration functions

## Version History

- **1.0**: Initial implementation with basic modes
- **1.1**: Added threading for performance
- **1.2**: Added simulation mode with ignition cycling
- **1.3**: Integration with vehicle state functions

---
*Last Updated: 2025*