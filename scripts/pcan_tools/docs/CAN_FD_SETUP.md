# CAN-FD Configuration Guide

## Overview

CAN-FD (CAN with Flexible Data-Rate) extends classic CAN by allowing:
- Higher data rates (up to 8 Mbit/s in data phase)
- Larger payloads (up to 64 bytes vs 8 bytes)
- Improved error detection

## Current Implementation Status

⚠️ **Note:** CAN-FD support in the PCAN TRC Logger is currently experimental and requires manual configuration.

## CAN-FD Timing Parameters

### Key Parameters

1. **Nominal Bit Rate:** Speed during arbitration phase (up to 1 Mbit/s)
2. **Data Bit Rate:** Speed during data phase (up to 8 Mbit/s)
3. **Sample Point:** Position in bit time where signal is sampled (typically 80%)
4. **Synchronization Jump Width (SJW):** Maximum adjustment for resynchronization

### Timing Calculation

CAN-FD timing requires careful calculation based on:
- System clock frequency
- Desired bit rates
- Network characteristics

## Configuration Examples

### Manual Code Modification

To enable CAN-FD, modify the `create_bus()` function in `pcan_trc_logger.py`:

```python
def create_bus(args: argparse.Namespace) -> can.Bus:
    bus_kwargs: Dict[str, Any] = {
        "interface": "pcan",
        "bitrate": args.bitrate,  # Nominal bitrate
        "receive_own_messages": args.receive_own
    }
    
    if args.fd:
        # Enable CAN-FD
        bus_kwargs["fd"] = True
        
        # Example timing for 500 kbit/s nominal, 2 Mbit/s data
        # These values depend on your specific hardware!
        bus_kwargs["f_clock"] = 80000000  # 80 MHz clock
        bus_kwargs["nom_brp"] = 10        # Nominal prescaler
        bus_kwargs["nom_tseg1"] = 12      # Nominal time segment 1
        bus_kwargs["nom_tseg2"] = 3       # Nominal time segment 2
        bus_kwargs["nom_sjw"] = 1         # Nominal SJW
        
        bus_kwargs["data_brp"] = 4        # Data prescaler
        bus_kwargs["data_tseg1"] = 7      # Data time segment 1
        bus_kwargs["data_tseg2"] = 2      # Data time segment 2
        bus_kwargs["data_sjw"] = 1        # Data SJW
    
    return can.Bus(**bus_kwargs)
```

### Common CAN-FD Configurations

#### Configuration 1: 500k/2M
```python
# Nominal: 500 kbit/s, Data: 2 Mbit/s
"f_clock": 80000000,
"nom_brp": 10,
"nom_tseg1": 12,
"nom_tseg2": 3,
"nom_sjw": 1,
"data_brp": 4,
"data_tseg1": 7,
"data_tseg2": 2,
"data_sjw": 1
```

#### Configuration 2: 250k/1M
```python
# Nominal: 250 kbit/s, Data: 1 Mbit/s
"f_clock": 80000000,
"nom_brp": 20,
"nom_tseg1": 12,
"nom_tseg2": 3,
"nom_sjw": 1,
"data_brp": 8,
"data_tseg1": 7,
"data_tseg2": 2,
"data_sjw": 1
```

#### Configuration 3: 1M/5M
```python
# Nominal: 1 Mbit/s, Data: 5 Mbit/s
"f_clock": 80000000,
"nom_brp": 5,
"nom_tseg1": 12,
"nom_tseg2": 3,
"nom_sjw": 1,
"data_brp": 2,
"data_tseg1": 5,
"data_tseg2": 2,
"data_sjw": 1
```

## Hardware Requirements

### Supported PCAN Devices
- PCAN-USB FD
- PCAN-USB Pro FD
- PCAN-PCI Express FD
- PCAN-miniPCI Express FD
- PCAN-M.2

### Cable Requirements
- Use proper CAN cabling (twisted pair)
- Keep cable lengths short for high data rates
- Ensure proper termination (120Ω split termination recommended)

## Testing CAN-FD

### Basic Test Script
```python
#!/usr/bin/env python3
import can

# Create CAN-FD bus
bus = can.Bus(
    interface="pcan",
    channel="PCAN_USBBUS1",
    fd=True,
    bitrate=500000,        # Nominal
    data_bitrate=2000000,  # Data phase
    # Add timing parameters as needed
)

# Send CAN-FD message
msg = can.Message(
    arbitration_id=0x123,
    is_fd=True,
    bitrate_switch=True,  # Use data bitrate in data phase
    data=[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
          0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10],  # 16 bytes
)

try:
    bus.send(msg)
    print("CAN-FD message sent successfully")
except can.CanError as e:
    print(f"Error sending message: {e}")

bus.shutdown()
```

### Verification Steps

1. **Check Hardware Support:**
   ```bash
   # Linux: Check for FD capability
   ip link show can0
   # Look for "fd" in the output
   ```

2. **Test Basic CAN First:**
   ```bash
   # Ensure classic CAN works before trying FD
   ./pcan_trc_logger.py --bitrate 500000 --duration 10
   ```

3. **Enable CAN-FD Gradually:**
   - Start with FD frames at nominal rate only
   - Then enable bitrate switching
   - Finally increase data rate

## Troubleshooting CAN-FD

### Common Issues

#### "CAN-FD not supported"
- Verify hardware supports FD
- Update PCAN drivers to latest version
- Check python-can version (need 4.0+)

#### Timing Errors
- Calculate timing based on actual clock frequency
- Use PEAK's timing calculator tool
- Start with proven configurations

#### Communication Failures
- Ensure all nodes support CAN-FD
- Check that timing matches across network
- Verify proper termination for high speeds

### Debug Commands

```bash
# Linux: Set CAN-FD interface manually
sudo ip link set can0 type can bitrate 500000 dbitrate 2000000 fd on
sudo ip link set can0 up

# Check interface configuration
ip -details link show can0
```

## Future Implementation Plans

The following features are planned for future versions:

1. **Automatic Timing Calculation**
   - Input: nominal and data bitrates
   - Output: optimal timing parameters

2. **Configuration File Support**
   ```yaml
   can_fd:
     nominal_bitrate: 500000
     data_bitrate: 2000000
     sample_point: 0.8
     dsample_point: 0.7
   ```

3. **Command-Line Parameters**
   ```bash
   ./pcan_trc_logger.py --fd --nom-bitrate 500000 --data-bitrate 2000000
   ```

4. **Auto-Detection**
   - Detect FD-capable hardware
   - Suggest optimal configurations

## References

- [CAN-FD Specification (Bosch)](https://www.bosch-semiconductors.com/ip-modules/can-transceivers/can-fd/)
- [PEAK-System CAN-FD Documentation](https://www.peak-system.com/produktcd/Pdf/English/PEAK_CAN_FD_Primer_EN.pdf)
- [python-can FD Documentation](https://python-can.readthedocs.io/en/stable/interfaces/pcan.html#canfd)
- [CAN in Automation (CiA) CAN-FD Info](https://www.can-cia.org/can-knowledge/can/can-fd/)

## Example Use Cases

### Automotive Testing
```bash
# ECU flash programming (high data rate needed)
./pcan_trc_logger.py --fd --bitrate 500000 --data-bitrate 5000000 --outfile ecu_flash.trc
```

### Industrial Automation
```bash
# High-speed sensor data collection
./pcan_trc_logger.py --fd --bitrate 250000 --data-bitrate 1000000 --duration 3600
```

### Development Testing
```bash
# Protocol compliance testing
./pcan_trc_logger.py --fd --bitrate 1000000 --data-bitrate 8000000 --stats-interval 1 -vv
```

## Contributing

To contribute CAN-FD improvements:
1. Test with your specific hardware
2. Document timing parameters that work
3. Submit pull request with configuration examples
4. Include test results and hardware details