# CAN Test Program

A standalone test program for CAN bus functionality on the iMX6 embedded target. This program demonstrates how to use the CAN Driver and J1939 module to receive and send CAN messages.

## Features

- Receive raw CAN frames
- Receive J1939 protocol messages
- Send raw CAN messages
- Send J1939 messages (single and multi-frame)
- CAN ID filtering

## Prerequisites

Before building the CAN test program, Fleet-Connect-1 must be built first to generate the required libraries (iMatrix, mbedtls).

## Building

```bash
cd test_system
mkdir build && cd build

CC=/opt/qconnect_sdk_musl/bin/arm-linux-gcc \
CXX=/opt/qconnect_sdk_musl/bin/arm-linux-g++ \
cmake -DCMAKE_SYSROOT=/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot ..

make
```

The executable will be created at `build/can_test`.

## Command Line Options

### Required Arguments

| Option | Long Form | Description |
|--------|-----------|-------------|
| `-i` | `--interface` | CAN interface to use: `0` (CAN0) or `1` (CAN1) |
| `-b` | `--baud` | Baud rate: `250`, `500`, or `1000` (kbps) |

### Optional Arguments

| Option | Long Form | Description |
|--------|-----------|-------------|
| `-j` | `--j1939` | Enable J1939 protocol mode (disables raw CAN mode) |
| `-s` | `--send` | Send periodic test messages (every 5 seconds) |
| `-f` | `--filter` | Enable CAN ID filtering (filters for 18FFBC32 and 18FFBC19) |

## Usage Examples

### Basic Raw CAN Monitoring

Monitor all raw CAN traffic on CAN0 at 250 kbps:

```bash
./can_test --interface 0 --baud 250
```

Or using short options:

```bash
./can_test -i 0 -b 250
```

### Monitor CAN1 at 500 kbps

```bash
./can_test -i 1 -b 500
```

### Monitor at 1 Mbps

```bash
./can_test -i 0 -b 1000
```

### J1939 Protocol Mode

Monitor J1939 messages on CAN0 at 250 kbps:

```bash
./can_test --interface 0 --baud 250 --j1939
```

### Send Test Messages

Monitor and send periodic raw CAN messages (every 5 seconds):

```bash
./can_test -i 0 -b 250 --send
```

Send J1939 messages:

```bash
./can_test -i 0 -b 250 --j1939 --send
```

### With CAN ID Filtering

Only receive messages with CAN IDs 18FFBC32 and 18FFBC19:

```bash
./can_test -i 0 -b 250 --filter
```

### Combined Options

J1939 mode with filtering and message sending on CAN1 at 500 kbps:

```bash
./can_test --interface 1 --baud 500 --j1939 --send --filter
```

## Output Format

### Raw CAN Mode

```
RAW RX: 0x18FFBC32 - 00 01 02 03 04 05 06 07
```

- `0x18FFBC32` - CAN ID (29-bit)
- `00 01 02...` - Data bytes (up to 8)

### J1939 Mode

```
J1939 RX: 18FFBC32 - PGN=FFBC dst=FF src=32 pri=6 - 00 01 02 03 04 05 06 07
```

- `18FFBC32` - Reconstructed CAN ID
- `PGN=FFBC` - Parameter Group Number
- `dst=FF` - Destination address (FF = broadcast)
- `src=32` - Source address
- `pri=6` - Priority (0-7)
- `00 01 02...` - Data bytes

## Filter Configuration

When filtering is enabled (`-f`), the program configures two filters:

1. **Filter 1**: CAN ID `0x18FFBC32` with mask `0x1FFFFFFF` (exact match)
2. **Filter 2**: CAN ID `0x18FFBC19` with mask `0x00FFFF00` (PGN filtering only)

## Test Messages

When sending is enabled (`-s`), the program transmits test messages every 5 seconds:

- **Raw CAN**: Sends CAN ID `0x18FFBC32` with payload `00 01 02 03 04 05 06 07`
- **J1939**: Sends PGN `0xFEBF` with 8 bytes to broadcast address (255)

## Thread Safety

The program demonstrates proper mutex usage for thread-safe CAN operations:

```c
pthread_mutex_t canMutex;
pthread_mutex_init(&canMutex, NULL);
CANEV_setMutex(&canMutex);
```

## Processing Loop

The main loop calls `CANEV_processCan()` every 10ms, which is required for proper J1939 protocol timeout handling.

## Exit

Press `Ctrl+C` to terminate the program.

---

**Date:** 2025-12-15
