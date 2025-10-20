# Function Pointer Documentation

## Overview

This document provides comprehensive documentation for the function pointers used throughout the iMatrix and Fleet-Connect-1 codebases. Function pointers are extensively used to implement callback mechanisms, event handling, and modular architecture patterns.

## Table of Contents

1. [CoAP Protocol Function Pointers](#coap-protocol-function-pointers)
2. [CAN Bus Processing Function Pointers](#can-bus-processing-function-pointers)
3. [Network Callback Function Pointers](#network-callback-function-pointers)
4. [CLI Monitor Function Pointers](#cli-monitor-function-pointers)
5. [Device Configuration Function Pointers](#device-configuration-function-pointers)
6. [Vehicle Sensor Function Pointers](#vehicle-sensor-function-pointers)
7. [BLE/GATT Function Pointers](#blegatt-function-pointers)
8. [Thread Function Pointers](#thread-function-pointers)

---

## CoAP Protocol Function Pointers

### CoAP Response Handler

**Definition**: `iMatrix/coap/coap.h`
```c
typedef struct {
    void (*response_fn)(struct message *msg);
} coap_message_t;
```

**Purpose**: Handles responses to CoAP messages sent by the device.

**Context**: Called when a CoAP response is received from the server.

**Parameters**:
- `msg`: Pointer to the received CoAP message structure

**Example Usage**:
```c
void my_response_handler(struct message *msg) {
    if (msg->code == COAP_CODE_CONTENT) {
        // Process successful response
    }
}

coap_message_t coap_msg = {
    .response_fn = my_response_handler
};
```

**Threading**: Called from the network thread; must be thread-safe.

### CoAP Method Handlers

**Definition**: `iMatrix/coap/coap.h`
```c
typedef struct {
    uint16_t (*get_function)(coap_message_t *msg, CoAP_msg_detail_t *cd, uint16_t arg);
    uint16_t (*put_function)(coap_message_t *msg, CoAP_msg_detail_t *cd, uint16_t arg);
    uint16_t (*post_function)(coap_message_t *msg, CoAP_msg_detail_t *cd, uint16_t arg);
    uint16_t (*delete_function)(coap_message_t *msg, CoAP_msg_detail_t *cd, uint16_t arg);
} CoAP_node_t;
```

**Purpose**: Implements REST-like operations for CoAP endpoints.

**Context**: Called when a CoAP request is received for a registered endpoint.

**Parameters**:
- `msg`: CoAP message being processed
- `cd`: Detailed message information including URI and payload
- `arg`: User-defined argument

**Return Value**: 
- CoAP response code (e.g., COAP_CODE_CONTENT, COAP_CODE_NOT_FOUND)

**Example Usage**:
```c
uint16_t sensor_get(coap_message_t *msg, CoAP_msg_detail_t *cd, uint16_t arg) {
    // Read sensor value
    char value[32];
    sprintf(value, "%.2f", read_sensor());
    
    // Set response
    coap_set_payload(msg, value, strlen(value));
    return COAP_CODE_CONTENT;
}

CoAP_node_t sensor_node = {
    .get_function = sensor_get,
    .put_function = NULL,
    .post_function = NULL,
    .delete_function = NULL
};
```

---

## CAN Bus Processing Function Pointers

### CAN Message Processor

**Definition**: `iMatrix/canbus/can_structs.h`
```c
typedef struct canbus_product {
    imx_status_t (*can_msg_process)(can_bus_t canbus, imx_time_t current_time, can_msg_t *msg);
    void (*set_can_sensor)(uint32_t imx_id, double value);
} canbus_product_t;
```

**Purpose**: Processes incoming CAN messages and updates sensor values.

**Context**: Called for each received CAN message.

**Parameters** (can_msg_process):
- `canbus`: CAN bus identifier (CAN_BUS_1, CAN_BUS_2)
- `current_time`: Current system time in milliseconds
- `msg`: Pointer to received CAN message

**Return Value**: IMX_SUCCESS or error code

**Parameters** (set_can_sensor):
- `imx_id`: iMatrix sensor identifier
- `value`: Decoded sensor value

**Example Usage**:
```c
imx_status_t process_can_message(can_bus_t canbus, imx_time_t current_time, can_msg_t *msg) {
    if (msg->id == 0x123) {
        double speed = decode_speed(msg->data);
        set_can_sensor(SENSOR_VEHICLE_SPEED, speed);
    }
    return IMX_SUCCESS;
}

canbus_product_t can_product = {
    .can_msg_process = process_can_message,
    .set_can_sensor = imx_set_can_sensor
};
```

### OBD2 PID Decoder

**Definition**: `Fleet-Connect-1/OBD2/decode_table.h`
```c
typedef void (*pid_decode_func_t)(uint8_t sa, uint8_t pid, const uint8_t *data, uint16_t len);
```

**Purpose**: Decodes OBD2 PID data from vehicle ECUs.

**Context**: Called when an OBD2 response is received.

**Parameters**:
- `sa`: Source address (ECU that sent the response)
- `pid`: Parameter ID being decoded
- `data`: Raw data bytes from OBD2 response
- `len`: Length of data

**Example Usage**:
```c
void decode_engine_rpm(uint8_t sa, uint8_t pid, const uint8_t *data, uint16_t len) {
    if (len >= 2) {
        uint16_t rpm = ((data[0] << 8) | data[1]) / 4;
        save_obd2_value(pid, 0, IMX_UINT16, &rpm);
    }
}
```

---

## Network Callback Function Pointers

### Network Link State Callback

**Definition**: `iMatrix/imx_platform.h`
```c
typedef void (*imx_network_link_callback_t)(void *user_data);
```

**Purpose**: Notifies when network connectivity changes.

**Context**: Called when network link goes up or down.

**Parameters**:
- `user_data`: User-defined context data

**Example Usage**:
```c
void network_state_changed(void *user_data) {
    if (imx_network_is_connected()) {
        // Start cloud synchronization
        start_data_upload();
    } else {
        // Buffer data locally
        enable_local_storage();
    }
}

imx_register_network_callback(network_state_changed, NULL);
```

### TCP Socket Callback

**Definition**: `iMatrix/imx_platform.h`
```c
typedef imx_result_t (*imx_tcp_socket_callback_t)(imx_tcp_socket_t* socket, void* arg);
```

**Purpose**: Handles TCP socket events (connection, data received, disconnection).

**Context**: Called from the network thread when socket events occur.

**Parameters**:
- `socket`: TCP socket that triggered the event
- `arg`: User-defined argument

**Return Value**: IMX_SUCCESS or error code

**Threading**: Must be thread-safe and non-blocking.

---

## CLI Monitor Function Pointers

### Monitor Content Generator

**Definition**: `iMatrix/cli/cli_monitor.h`
```c
typedef void (*monitor_generate_content_fn)(void *ctx);
```

**Purpose**: Generates content for CLI monitor display.

**Context**: Called periodically to refresh monitor display.

**Parameters**:
- `ctx`: Monitor-specific context data

**Example Usage**:
```c
void generate_system_stats(void *ctx) {
    cli_printf("CPU Usage: %d%%\n", get_cpu_usage());
    cli_printf("Memory: %d/%d KB\n", get_used_memory(), get_total_memory());
    cli_printf("Uptime: %s\n", format_uptime());
}
```

### Monitor Key Processor

**Definition**: `iMatrix/cli/cli_monitor.h`
```c
typedef bool (*monitor_process_key_fn)(char ch);
```

**Purpose**: Processes keyboard input in monitor mode.

**Context**: Called when a key is pressed while monitor is active.

**Parameters**:
- `ch`: Character pressed

**Return Value**: 
- `true`: Key was handled
- `false`: Key not handled, use default behavior

---

## Device Configuration Function Pointers

### Configuration Functions

**Definition**: `iMatrix/common.h`
```c
typedef struct functions {
    void (*load_config_defaults)(uint16_t arg);
    void (*init)(uint16_t arg);
    imx_result_t (*update)(uint16_t arg, void *value);
} imx_functions_t;
```

**Purpose**: Provides standardized interface for device modules.

**load_config_defaults**:
- Called to load default configuration values
- `arg`: Module-specific argument

**init**:
- Called to initialize the module
- `arg`: Module-specific argument

**update**:
- Called to update module configuration
- `arg`: Configuration parameter ID
- `value`: New value
- Returns: IMX_SUCCESS or error code

**Example Usage**:
```c
void gps_load_defaults(uint16_t arg) {
    gps_config.update_rate = 1000;  // 1 Hz
    gps_config.enabled = true;
}

void gps_init(uint16_t arg) {
    gps_uart_init();
    gps_parser_init();
}

imx_result_t gps_update(uint16_t arg, void *value) {
    switch (arg) {
        case GPS_UPDATE_RATE:
            gps_config.update_rate = *(uint32_t*)value;
            return IMX_SUCCESS;
        default:
            return IMX_INVALID_PARAM;
    }
}

imx_functions_t gps_functions = {
    .load_config_defaults = gps_load_defaults,
    .init = gps_init,
    .update = gps_update
};
```

---

## Vehicle Sensor Function Pointers

### Sensor Update Function

**Definition**: `Fleet-Connect-1/can_process/vehicle_sensor_mappings.h`
```c
typedef imx_result_t (*sensor_update_func_t)(double value);
```

**Purpose**: Updates a specific vehicle sensor with a new value.

**Context**: Called when a CAN message contains data for this sensor.

**Parameters**:
- `value`: Decoded and scaled sensor value

**Return Value**: IMX_SUCCESS or error code

**Example Usage**:
```c
imx_result_t update_vehicle_speed(double value) {
    if (value < 0 || value > 300) {
        return IMX_INVALID_PARAM;
    }
    
    vehicle_data.speed = value;
    notify_speed_change(value);
    return IMX_SUCCESS;
}

vehicle_sensor_mapping_t speed_sensor = {
    .sensor_id = 0x123,
    .update_func = update_vehicle_speed,
    .name = "Vehicle Speed"
};
```

---

## BLE/GATT Function Pointers

### GATT Command Function

**Definition**: `iMatrix/ble/imx_gatt_control_flow.c`
```c
typedef struct {
    void (*func)();
} gatt_command_t;
```

**Purpose**: Executes BLE GATT operations in sequence.

**Context**: Called during BLE device discovery and connection.

**Example Usage**:
```c
void discover_services() {
    gatt_client_discover_primary_services(&connection);
}

void discover_characteristics() {
    gatt_client_discover_characteristics(&connection, service_handle);
}

gatt_command_t commands[] = {
    { .func = discover_services },
    { .func = discover_characteristics }
};
```

---

## Thread Function Pointers

### Thread Entry Point

**Definition**: `iMatrix/imx_platform.h`
```c
typedef void (*imx_thread_function_t)(void *arg);
```

**Purpose**: Standard thread entry point.

**Context**: Called when a thread starts execution.

**Parameters**:
- `arg`: Thread-specific argument

**Example Usage**:
```c
void data_collection_thread(void *arg) {
    thread_context_t *ctx = (thread_context_t *)arg;
    
    while (!ctx->stop_requested) {
        collect_sensor_data();
        imx_thread_sleep(ctx->interval_ms);
    }
}

imx_thread_t thread;
thread_context_t ctx = { .interval_ms = 1000 };
imx_thread_create(&thread, data_collection_thread, &ctx);
```

**Threading**: This IS the thread function; must handle its own synchronization.

---

## Best Practices

### General Guidelines

1. **Error Handling**: Always validate parameters and return meaningful error codes
2. **Thread Safety**: Use appropriate synchronization when accessing shared data
3. **Non-blocking**: Callbacks should execute quickly and not block
4. **Resource Management**: Clean up any resources allocated in callbacks
5. **Null Checks**: Always check function pointers before calling

### Registration Pattern

```c
// Safe function pointer registration
imx_result_t register_callback(callback_fn_t callback, void *user_data) {
    if (callback == NULL) {
        return IMX_INVALID_PARAM;
    }
    
    // Store callback and user data
    g_callback = callback;
    g_user_data = user_data;
    
    return IMX_SUCCESS;
}

// Safe function pointer invocation
void trigger_callback() {
    if (g_callback != NULL) {
        g_callback(g_user_data);
    }
}
```

### Callback Context

Always provide context through user_data parameter:
```c
typedef struct {
    uint32_t device_id;
    void *buffer;
    size_t buffer_size;
    // Other context fields
} callback_context_t;
```

This allows callbacks to access necessary data without relying on global variables.