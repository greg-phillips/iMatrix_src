# CAN Send File Simulation - Implementation Complete

## Overview
✅ **IMPLEMENTED** - A new CAN file send simulation command `send_file_sim <filename>` that cycles through ignition states while sending CAN frames from a file. This simulates vehicle ignition on/off cycles with a 30-second interval between states.

## Requirements
1. **Command**: `can send_file_sim <filename>` 
2. **Stop Command**: Uses existing `can send_file_stop` command
3. **State Machine**: 4-state cycle with ignition simulation
4. **Timing**: 30-second intervals between state transitions
5. **Helper Function**: `send_can_ignition_state()` to return current ignition state

## State Machine Design

### States
```
State 1 (IGNITION_OFF_WAIT):
  - Set sim_ignition = false
  - Wait 30 seconds
  - Transition to State 2

State 2 (IGNITION_ON_WAIT):
  - Set sim_ignition = true
  - Wait 30 seconds
  - Transition to State 3

State 3 (FILE_SENDING):
  - Send file in real-time (same as current send_file)
  - When file complete, transition to State 4

State 4 (CYCLE_COMPLETE):
  - Reset to State 1
  - Continue loop until stop command
```

## Implementation Plan

### 1. Update Header File (can_file_send.h)

#### Add New State Machine States
```c
typedef enum {
    // Existing states...
    CAN_FILE_SIM_IGNITION_OFF_WAIT,  /**< Simulation: Ignition off, waiting */
    CAN_FILE_SIM_IGNITION_ON_WAIT,   /**< Simulation: Ignition on, waiting */
    CAN_FILE_SIM_SENDING,             /**< Simulation: Sending file */
    CAN_FILE_SIM_CYCLE_COMPLETE       /**< Simulation: Cycle complete, restart */
} can_file_state_t;
```

#### Add Function Declarations
```c
void can_file_send_sim_start(uint8_t device, const char *filename);
bool send_can_ignition_state(void);
```

### 2. Update Implementation File (can_file_send.c)

#### Add Static Variables
```c
/* Simulation mode variables */
static bool sim_mode_active = false;
static bool sim_ignition = false;
static imx_time_t sim_state_start_time = 0;
static const uint32_t SIM_STATE_WAIT_MS = 30000;  /* 30 seconds */
static char sim_filename[CAN_FILE_MAX_PATH_LEN];
static uint8_t sim_device = 0;
```

#### Implement Helper Function
```c
/**
 * @brief Get current simulated ignition state
 * @return true if ignition is on, false if off
 */
bool send_can_ignition_state(void)
{
    return sim_ignition;
}
```

#### Implement Simulation Start Function
```c
/**
 * @brief Start CAN file simulation with ignition cycling
 * @param device CAN device to use (0=can0, 1=can1, 2=caneth)
 * @param filename Path to PCAN trace file
 */
void can_file_send_sim_start(uint8_t device, const char *filename)
{
    /* Validate inputs */
    if (!filename || strlen(filename) == 0) {
        imx_cli_print("Error: No filename specified\r\n");
        return;
    }
    
    if (device > 2) {
        imx_cli_print("Error: Invalid device %u\r\n", device);
        return;
    }
    
    /* Check if already running */
    if (current_state != CAN_FILE_IDLE) {
        imx_cli_print("Error: File operation already in progress\r\n");
        return;
    }
    
    /* Store simulation parameters */
    strncpy(sim_filename, filename, CAN_FILE_MAX_PATH_LEN - 1);
    sim_filename[CAN_FILE_MAX_PATH_LEN - 1] = '\0';
    sim_device = device;
    
    /* Initialize simulation state */
    sim_mode_active = true;
    sim_ignition = false;
    imx_time_get_time(&sim_state_start_time);
    user_stop_requested = false;
    
    /* Start in ignition off state */
    current_state = CAN_FILE_SIM_IGNITION_OFF_WAIT;
    
    imx_cli_print("Starting CAN file simulation:\r\n");
    imx_cli_print("  File: %s\r\n", sim_filename);
    imx_cli_print("  Device: %s\r\n", device == 0 ? "can0" : (device == 1 ? "can1" : "caneth"));
    imx_cli_print("  Mode: Simulation with ignition cycling\r\n");
    imx_cli_print("  State: IGNITION OFF (30s)\r\n");
}
```

#### Update Process Function for Simulation States
```c
void can_file_send_process(imx_time_t current_time)
{
    switch (current_state) {
        case CAN_FILE_SIM_IGNITION_OFF_WAIT:
            /* Check if 30 seconds have elapsed */
            if (imx_is_later(current_time, sim_state_start_time + SIM_STATE_WAIT_MS)) {
                /* Transition to ignition on */
                sim_ignition = true;
                imx_time_get_time(&sim_state_start_time);
                current_state = CAN_FILE_SIM_IGNITION_ON_WAIT;
                imx_cli_print("Simulation: IGNITION ON (30s)\r\n");
            }
            break;
            
        case CAN_FILE_SIM_IGNITION_ON_WAIT:
            /* Check if 30 seconds have elapsed */
            if (imx_is_later(current_time, sim_state_start_time + SIM_STATE_WAIT_MS)) {
                /* Start file sending */
                imx_cli_print("Simulation: Starting file transmission\r\n");
                can_file_send_start(sim_device, sim_filename, 0);  /* Mode 0 = real-time */
                current_state = CAN_FILE_SIM_SENDING;
            }
            break;
            
        case CAN_FILE_SIM_SENDING:
            /* Monitor existing file send process */
            if (thread_ctrl.thread_active) {
                /* Still sending */
                if (thread_ctrl.stop_requested || !thread_ctrl.running) {
                    /* Thread stopping */
                    if (!thread_ctrl.thread_active) {
                        /* File send complete, restart cycle */
                        imx_cli_print("Simulation: File complete, restarting cycle\r\n");
                        current_state = CAN_FILE_SIM_CYCLE_COMPLETE;
                    }
                }
            } else {
                /* File send complete or stopped */
                current_state = CAN_FILE_SIM_CYCLE_COMPLETE;
            }
            break;
            
        case CAN_FILE_SIM_CYCLE_COMPLETE:
            /* Reset to beginning of cycle */
            sim_ignition = false;
            imx_time_get_time(&sim_state_start_time);
            current_state = CAN_FILE_SIM_IGNITION_OFF_WAIT;
            imx_cli_print("Simulation: IGNITION OFF (30s)\r\n");
            break;
            
        // Existing states...
    }
    
    /* Check for stop request in simulation mode */
    if (sim_mode_active && user_stop_requested) {
        imx_cli_print("Simulation stopped by user\r\n");
        sim_mode_active = false;
        sim_ignition = false;
        if (thread_ctrl.thread_active) {
            can_file_send_stop();
        }
        current_state = CAN_FILE_IDLE;
    }
}
```

#### Update Stop Function
```c
void can_file_send_stop(void)
{
    /* Handle simulation mode */
    if (sim_mode_active) {
        sim_mode_active = false;
        sim_ignition = false;
        imx_cli_print("Stopping simulation mode\r\n");
    }
    
    // Existing stop logic...
}
```

### 3. Update CLI Handler (cli_canbus.c)

#### Add New Command Handler
```c
else if (strncmp(token, "send_file_sim", 13) == 0)
{
    /*
     * Send CAN frames from file with ignition simulation
     * Format: can send_file_sim [device] <filename>
     */
    char *arg1 = strtok(NULL, " ");
    char *arg2 = strtok(NULL, " ");
    char *filename = NULL;
    uint8_t device = 0;  /* Default to can0 */
    
    if (arg2) {
        /* Two args: first is device, second is filename */
        if (strcmp(arg1, "can0") == 0) {
            device = 0;
        } else if (strcmp(arg1, "can1") == 0) {
            device = 1;
        } else if (strcmp(arg1, "caneth") == 0) {
            device = 2;
        } else {
            /* First arg is not a device, assume it's filename */
            filename = arg1;
            /* arg2 is unexpected */
            imx_cli_print("Invalid arguments. Usage: can send_file_sim [device] <filename>\r\n");
            imx_cli_print("  device: can0, can1, or caneth (default: can0)\r\n");
            return;
        }
        if (device != 0 || strcmp(arg1, "can0") == 0) {
            filename = arg2;
        }
    } else if (arg1) {
        /* One arg: it's the filename, use default device */
        filename = arg1;
    } else {
        /* No args: show usage */
        imx_cli_print("Usage: can send_file_sim [device] <filename>\r\n");
        imx_cli_print("  device: can0, can1, or caneth (default: can0)\r\n");
        imx_cli_print("  Simulates ignition cycling while sending CAN frames\r\n");
        imx_cli_print("  Cycle: 30s off -> 30s on -> send file -> repeat\r\n");
        return;
    }
    
    /* Start simulation */
    can_file_send_sim_start(device, filename);
    return;
}
```

#### Update Help Text
Add to the help output:
```c
imx_cli_print("  send_file_sim [dev] <file> - Send with ignition simulation\r\n");
```

### 4. Integration Points

#### Main Processing Loop
The existing main loop that calls `can_file_send_process()` will handle the simulation states automatically.

#### Status Display
Could add simulation status to existing status display:
```c
if (sim_mode_active) {
    imx_cli_print("Simulation Mode: Active\r\n");
    imx_cli_print("  Ignition: %s\r\n", sim_ignition ? "ON" : "OFF");
    imx_cli_print("  State: %s\r\n", get_state_name(current_state));
}
```

## Implementation Status

### Phase 1: Core Implementation ✅ COMPLETE
- ✅ Updated can_file_send.h with new states and function declarations
- ✅ Added static variables for simulation mode in can_file_send.c
- ✅ Implemented send_can_ignition_state() helper function
- ✅ Implemented can_file_send_sim_start() function
- ✅ Updated can_file_send_process() with simulation state handling
- ✅ Updated can_file_send_stop() to handle simulation mode

### Phase 2: CLI Integration ✅ COMPLETE
- ✅ Added send_file_sim command handler in cli_canbus.c
- ✅ Updated help text to include new command
- ✅ Command parsing supports device and filename arguments

### Phase 3: System Integration ✅ COMPLETE
- ✅ Added imx_can_file_sim_active() to check simulation state
- ✅ Modified imx_get_ignition() to return simulated ignition state
- ✅ Modified imx_get_speed() to return 0 when ignition is off in simulation
- ✅ Integration with existing vehicle state functions

### Phase 4: Documentation ✅ COMPLETE
- ✅ Updated can_send_functionality_documentation.md
- ✅ Documented simulation behavior and timing
- ✅ Added usage examples and integration details

## Testing Scenarios

1. **Basic Simulation**
   - Start simulation with valid file
   - Verify 30-second timing for each state
   - Confirm file sends during ignition on phase

2. **Stop During Various States**
   - Stop during ignition off wait
   - Stop during ignition on wait
   - Stop during file sending
   - Verify clean shutdown in all cases

3. **Multiple Cycles**
   - Let simulation run through multiple complete cycles
   - Verify consistent timing and behavior

4. **Error Cases**
   - Invalid filename
   - Invalid device
   - Start while another operation is running

5. **Integration**
   - Verify other modules can read ignition state
   - Check interaction with existing send_file commands

## Implementation Notes

### Key Features Implemented
- The simulation uses the existing file send infrastructure with state management overlay
- 30-second timing implemented using `imx_is_later()` for millisecond accuracy
- Ignition state accessible globally via `send_can_ignition_state()`
- Stop command works at any point in the simulation cycle
- File is re-opened for each cycle to ensure fresh start
- Full integration with vehicle state functions (speed, ignition)

### System Integration

#### Vehicle State Functions Modified
1. **imx_get_ignition()** (process_location_state.c)
   - Checks `imx_can_file_sim_active()`
   - Returns simulated ignition state when simulation is active
   - Falls back to hardware detection when not simulating

2. **imx_get_speed()** (get_J1939_sensors.c)
   - Checks simulation mode status
   - Returns 0.0 when simulation ignition is OFF
   - Processes normal speed when ignition is ON
   - Ensures realistic vehicle behavior during simulation

### API Functions Added

```c
// Check if simulation is active
bool imx_can_file_sim_active(void);

// Get current simulated ignition state
bool send_can_ignition_state(void);

// Start simulation
void can_file_send_sim_start(uint8_t device, const char *filename);
```

## Questions Addressed

1. **File reopening**: The file will be reopened for each cycle by calling `can_file_send_start()` in state 3
2. **Thread safety**: Uses existing thread control mechanisms
3. **Timing accuracy**: Uses millisecond-precision timing functions
4. **State persistence**: Static variables maintain state between process calls