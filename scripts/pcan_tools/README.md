# PCAN TRC Logger

A robust Python tool for logging CAN bus traffic from PEAK-System PCAN interfaces to TRC format files.

## Overview

The PCAN TRC Logger is designed to capture and save CAN bus traffic from PCAN-USB, PCAN-PCI, and PCAN-LAN interfaces. It creates TRC (PEAK trace) format files that can be analyzed with PEAK's PCAN-View software or other compatible tools.

### Key Features

- ✅ Support for all PCAN interface types (USB, PCI, LAN)
- ✅ Classic CAN and CAN-FD support (FD requires additional configuration)
- ✅ Automatic file naming with timestamps
- ✅ Time-based or manual recording duration
- ✅ Graceful shutdown with Ctrl+C
- ✅ Statistics tracking and display
- ✅ Verbose logging modes for debugging
- ✅ Input validation and error handling
- ✅ Support for multiple PCAN channels

## Installation

### Prerequisites

- Python 3.7 or higher
- PCAN drivers installed (from PEAK-System)
- PCAN-Basic API library

### Python Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install python-can>=4.0.0
```

### PCAN Driver Installation

#### Linux
```bash
# Download and install PCAN drivers from PEAK-System
wget https://www.peak-system.com/fileadmin/media/linux/files/peak-linux-driver-8.x.tar.gz
tar -xzf peak-linux-driver-8.x.tar.gz
cd peak-linux-driver-8.x
make
sudo make install
```

#### Windows
Download and install PCAN-Basic from: https://www.peak-system.com/PCAN-Basic.239.0.html

#### macOS
Install via Homebrew:
```bash
brew tap vanderbilt-design-studio/pcan
brew install pcan-basic
```

## Usage

### Basic Usage

Log CAN traffic at 500 kbit/s:
```bash
./pcan_trc_logger.py --bitrate 500000
```

### Common Examples

#### 1. Log for a specific duration
```bash
# Log for 60 seconds
./pcan_trc_logger.py --bitrate 500000 --duration 60
```

#### 2. Save to a specific file
```bash
./pcan_trc_logger.py --bitrate 250000 --outfile my_log.trc
```

#### 3. Append to existing file
```bash
./pcan_trc_logger.py --bitrate 500000 --outfile session.trc --append
```

#### 4. Use a specific PCAN channel
```bash
./pcan_trc_logger.py --bitrate 500000 --channel PCAN_USBBUS2
```

#### 5. Log with verbose output
```bash
# Show INFO messages
./pcan_trc_logger.py --bitrate 500000 -v

# Show DEBUG messages
./pcan_trc_logger.py --bitrate 500000 -vv
```

#### 6. Log own transmitted messages
```bash
./pcan_trc_logger.py --bitrate 500000 --receive-own
```

#### 7. Display statistics every 5 seconds
```bash
./pcan_trc_logger.py --bitrate 500000 --stats-interval 5
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--bitrate` | CAN bitrate in bit/s (required) | - |
| `--channel` | PCAN channel name | PCAN_USBBUS1 |
| `--device-id` | PCAN device ID (overrides channel) | None |
| `--outfile` | Output TRC file path | pcan_YYYYMMDD_HHMMSS.trc |
| `--append` | Append to existing file | False |
| `--channel-number` | Channel number in TRC header | 1 |
| `--duration` | Logging duration in seconds | Until Ctrl+C |
| `--receive-own` | Log transmitted frames | False |
| `--stats-interval` | Statistics display interval (seconds) | 10.0 |
| `-v, --verbose` | Increase verbosity | 0 |
| `--fd` | Enable CAN-FD mode (experimental) | False |

### Supported Channels

- PCAN_USBBUS1 to PCAN_USBBUS8
- PCAN_PCIBUS1, PCAN_PCIBUS2
- PCAN_LANBUS1, PCAN_LANBUS2

### Common Bitrates

- 10000 (10 kbit/s)
- 20000 (20 kbit/s)
- 50000 (50 kbit/s)
- 100000 (100 kbit/s)
- 125000 (125 kbit/s)
- 250000 (250 kbit/s)
- 500000 (500 kbit/s) - Most common
- 800000 (800 kbit/s)
- 1000000 (1 Mbit/s)

## Output Format

The tool generates TRC files compatible with PEAK-System's PCAN-View software. These files contain:

- Timestamp for each message
- CAN ID (standard or extended)
- Data length code (DLC)
- Data bytes
- Message flags (RTR, error frames, etc.)

### Example TRC Content
```
;##########################################################################
;### PCAN-View Trace File
;##########################################################################
;   Start time: 13.09.2024 14:30:45.123
;   Channel: 1
;##########################################################################
;   Message   Time    ID    Rx/Tx   Type   DLC  Data
;##########################################################################
1)    0.000000  0x123  Rx  STD  8  01 02 03 04 05 06 07 08
2)    0.001234  0x456  Rx  STD  4  AA BB CC DD
3)    0.002345  0x789  Rx  EXT  2  11 22
```

## Advanced Features

### Using Device ID

If you have multiple PCAN adapters, you can select a specific one by device ID:

```bash
# List available devices (requires additional tooling)
pcaninfo

# Use specific device
./pcan_trc_logger.py --bitrate 500000 --device-id 0x51
```

### CAN-FD Support

CAN-FD support is experimental. For full configuration, see `docs/CAN_FD_SETUP.md`.

Basic CAN-FD usage:
```bash
./pcan_trc_logger.py --bitrate 500000 --fd
```

## Troubleshooting

### Common Issues

#### 1. "Failed to open PCAN bus"
- Check that PCAN drivers are installed
- Verify the interface is connected
- Ensure you have permission to access the device
- Try running with sudo (Linux)

#### 2. "Invalid bitrate"
- Use a standard bitrate (see Common Bitrates section)
- Ensure bitrate matches your CAN network

#### 3. "Permission denied"
- On Linux, add user to `dialout` group: `sudo usermod -a -G dialout $USER`
- Log out and back in for changes to take effect

#### 4. No messages received
- Verify CAN bus termination (120Ω resistors)
- Check that other nodes are transmitting
- Ensure bitrate matches the network
- Try `--receive-own` to see if transmission works

### Debug Mode

Enable debug output to troubleshoot issues:
```bash
./pcan_trc_logger.py --bitrate 500000 -vv
```

## Integration Examples

### Bash Script Integration
```bash
#!/bin/bash
# Log CAN data during a test sequence

# Start logging in background
./pcan_trc_logger.py --bitrate 500000 --outfile test_run.trc &
LOGGER_PID=$!

# Run your test
./run_test_sequence.sh

# Stop logging
kill -INT $LOGGER_PID
wait $LOGGER_PID
```

### Python Integration
```python
import subprocess
import time

# Start logger process
logger = subprocess.Popen([
    './pcan_trc_logger.py',
    '--bitrate', '500000',
    '--outfile', 'automated_test.trc',
    '--duration', '30'
])

# Your test code here
time.sleep(5)
# ...

# Wait for logger to finish
logger.wait()
```

## Performance Considerations

- The logger can handle high-speed CAN traffic (up to 1 Mbit/s)
- For very high message rates, consider:
  - Disabling statistics display (`--stats-interval 0`)
  - Reducing verbosity (no `-v` flags)
  - Using SSD storage for output files
  - Ensuring adequate CPU resources

## File Size Estimation

Approximate file sizes for continuous logging:

| Bitrate | Message Rate | File Size/Hour |
|---------|--------------|----------------|
| 125 kbit/s | ~1000 msg/s | ~100 MB |
| 250 kbit/s | ~2000 msg/s | ~200 MB |
| 500 kbit/s | ~4000 msg/s | ~400 MB |
| 1 Mbit/s | ~8000 msg/s | ~800 MB |

## Contributing

Contributions are welcome! Please see the `docs/CONTRIBUTING.md` file for guidelines.

## License

MIT License - See LICENSE file for details.

## Support

For issues, questions, or feature requests:
- Check the `docs/TROUBLESHOOTING.md` guide
- Review existing issues on GitHub
- Contact iMatrix Systems support

## Version History

- **v1.1.0** (2024-09-13)
  - Added statistics tracking
  - Improved error handling
  - Added input validation
  - Enhanced logging capabilities
  - Fixed unused make_bus() function
  
- **v1.0.0** (2024-09-01)
  - Initial release
  - Basic CAN logging functionality
  - TRC file output support

## See Also

- [PEAK-System PCAN-View](https://www.peak-system.com/PCAN-View.242.0.html)
- [python-can Documentation](https://python-can.readthedocs.io/)
- [CAN Bus Fundamentals](https://www.csselectronics.com/pages/can-bus-simple-intro-tutorial)