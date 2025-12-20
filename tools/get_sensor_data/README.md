# Sensor Data Download Tool with Device Discovery

## Overview

`get_sensor_data.py` is a command-line tool for downloading sensor data from the iMatrix Cloud API with **complete interactive workflows**. The default operation provides a guided experience: list your devices → select device → discover sensors → select sensor → enter dates → download data. It also supports direct mode with specific device/sensor IDs.

## Features

### Core Features
- **Complete Interactive Workflow**: Default mode requires only username - discovers devices, sensors, and prompts for dates
- **Device Discovery**: List all devices in your account with interactive selection
- **Sensor Discovery**: Automatically discover all available sensors on any device
- **Flexible Entry Points**: Start workflow at any level (device, sensor, or data download)
- **Multiple Modes**: Interactive workflows, information-only, or direct download modes
- **Multi-Sensor Download**: Download multiple sensors in a single request with combined JSON output
- **Direct Sensor ID Entry**: Enter sensor IDs directly without menu selection

### Data Features
- Download data for any sensor ID from iMatrix devices
- **Multi-sensor support**: Download multiple sensors at once (comma-separated or multiple `-id` flags)
- Flexible time range selection using epoch milliseconds or human-readable dates
- **Last 24 hours default**: Press Enter at date prompt to use last 24 hours
- Multiple output formats (JSON, CSV, or both)
- **Combined JSON output**: Multi-sensor downloads produce single file with all data
- Automatic statistics calculation (min, max, average, duration)
- **Reproducible command output**: Shows full CLI command to repeat the download
- Built-in sensor definitions for energy sensors (IDs 509-537)

### User Experience
- Secure password entry (optional command-line or prompt)
- Product information display with device details
- Sensor list with names, units, and data types
- Verbose mode for debugging and troubleshooting
- Automatic filename generation based on sensor and date

## Installation

### Prerequisites

- Python 3.6 or higher
- pip package manager

### Dependencies

Install required packages:

```bash
python3 -m pip install requests urllib3
```

## Usage

The tool supports multiple operation modes with different entry points:

### 1. Default Interactive Mode (NEW) - Complete Workflow

**Minimal command** - just provide your username:

```bash
python3 get_sensor_data.py -u <email>
```

**Complete workflow:**
1. **List all your devices** with 4-column display
2. **Select device** interactively
3. **Discover available sensors** on selected device
4. **Select sensor** from interactive menu
5. **Enter date range** with flexible formats
6. **Download data** with statistics

### 2. Partial Interactive Modes (NEW) - Skip Known Steps

#### Skip to Sensor Selection (Device Known)
```bash
python3 get_sensor_data.py -s <serial> -u <email>
```

#### Skip to Date Entry (Device + Sensor Known)
```bash
python3 get_sensor_data.py -s <serial> -id <sensor_id> -u <email>
```

### 3. Information Modes (NEW) - Explore Without Downloading

#### List Available Sensors
```bash
python3 get_sensor_data.py -s <serial> -u <email> --list-sensors
```

#### Show Product Information
```bash
python3 get_sensor_data.py -s <serial> -u <email> --product-info
```

### 4. Direct Mode - No Interaction Needed

When you know everything in advance:

```bash
python3 get_sensor_data.py -s <serial> -ts <start> -te <end> -id <sensor_id> -u <email>
```

### Argument Reference

#### Required Arguments
- `-u, --username`: iMatrix Cloud username (email) - **ONLY REQUIRED ARGUMENT**

#### Optional Arguments (Interactive Prompting if Omitted)
- `-s, --serial`: Device serial number (interactive device selection if omitted)
- `-id, --sensor-id`: Sensor ID(s) to download. Supports multiple sensors:
  - Single: `-id 509`
  - Multiple: `-id 509 -id 514 -id 522`
  - Interactive comma-separated entry: `509, 514, 522`
- `-ts, --start`: Start time (interactive date entry if omitted, Enter for last 24 hours)
- `-te, --end`: End time (interactive date entry if omitted)

#### Information Mode Flags
- `--list-devices`: List all user devices and select interactively
- `--list-sensors`: List available sensors without downloading data (requires serial)
- `--product-info`: Show product information only (requires serial)

#### Optional Arguments

- `-p, --password`: Password (if omitted, secure prompt appears)
- `-o, --output`: Output format (`json`, `csv`, or `both`) - default: `json`
- `-f, --filename`: Custom output filename (without extension)
- `-v, --verbose`: Enable verbose output for debugging

## Examples

### Default Interactive Mode (NEW) - Complete Workflow

#### Minimal Command (Just Username)
```bash
python3 get_sensor_data.py -u user@example.com
```

**Complete interaction example:**
```
🔍 Fetching your devices...
✅ Found 6 devices in your account

================================================================================
                           USER DEVICES
                            (6 found)
================================================================================
  # Device Name                       Serial Number Product ID   Version
--------------------------------------------------------------------------------
[ 1] 1st Floor Micro Gateway             863095613    984993858    1.034.001
[ 2] AGSoil-1                            81541896     3829380261   1.020.000
[ 3] AQM-1 #1                            815828186    548556236    1.020.000
[ 4] Floor 1 Gateway 0456047521          456047521    984993858    1.022.033
[ 5] Floor 2 Gateway 0915867336          915867336    984993858    1.022.038
[ 6] Greg's Desk NEO-1D                  592978988    1349851161   1.023.000
[ 7] Home Office                         955154708    1472614291   1.023.000
[ 8] Home Office Desk - offline          600988347    1349851161   1.021.001
[ 9] Office Kitchen                      296540475    1349851161   1.023.000
[10] Kitchen  Refrigerator Door          174959126    1272203777   1.020.001

--------------------------------------------------------------------------------
Select a device [1-6], or 'q' to quit:
Enter your choice: 6
✅ Selected: Greg's Desk NEO-1D (Serial: 592978988)

📱 Device Details:
   Name:            Greg's Desk NEO-1D
   Serial Number:   592978988
   MAC Address:     00:06:8b:01:11:eb
   Product ID:      1349851161
   Group ID:        1082477619
   Organization:    298726404
   Version:         1.023.000
   Created:         2025-06-05T10:15:36Z

Proceeding to sensor discovery...

🔍 Discovering sensors for device: 592978988
✅ Successfully discovered 7 sensors

📊 Available sensors (7 found):
--------------------------------------------------------------------------------
[1] Temperature (ID: 58108062)
    Units: Deg. C | Type: IMX_FLOAT
[2] Humidity (ID: 528597925)
    Units: %RH | Type: IMX_FLOAT
...
Select a sensor to download [1-7], or 'q' to quit:
Enter your choice: 1
✅ Selected: Temperature (ID: 58108062)

📅 Date/time range required for data download

Supported formats:
  • Date only: 01/15/25 (midnight to midnight)
  • Date and time: 01/15/25 14:30
  • Epoch milliseconds: 1736899200000

📅 Enter start date/time: 01/15/25
✅ Start: 2025-01-15T00:00:00Z
📅 Enter end date/time: 01/15/25
✅ End: 2025-01-15T23:59:59Z
📊 Date range: 24.0 hours

🚀 Starting sensor data download...
```

### Partial Interactive Mode Examples (NEW)

#### Skip to Sensor Selection (Device Known)
```bash
python3 get_sensor_data.py -s 592978988 -u user@example.com
```
Skips device selection, starts with sensor discovery and date entry.

#### Skip to Date Entry (Device + Sensor Known)
```bash
python3 get_sensor_data.py -s 592978988 -id 58108062 -u user@example.com
```
Skips device and sensor selection, only prompts for dates.

#### Information Modes (No Download)

**List All User Devices**
```bash
python3 get_sensor_data.py -u user@example.com --list-devices
```

**List Device Sensors**
```bash
python3 get_sensor_data.py -s 592978988 -u user@example.com --list-sensors
```

**Show Device Information**
```bash
python3 get_sensor_data.py -s 592978988 -u user@example.com --product-info
```

### Direct Mode Examples (Enhanced with New Date Formats)

#### Basic Usage with Human-Readable Dates
```bash
python3 get_sensor_data.py -s 1234567890 -ts "01/15/25" -te "01/16/25" -id 509 -u user@example.com
```

#### Download with Specific Time Range
```bash
python3 get_sensor_data.py -s 1234567890 -ts "01/15/25 09:00" -te "01/15/25 17:00" -id 509 -u user@example.com
```

#### Original Epoch Milliseconds Format (Still Supported)
```bash
python3 get_sensor_data.py -s 1234567890 -ts 1736899200000 -te 1736985600000 -id 509 -u user@example.com
```

#### Download Trip Energy Recovered with Date Range
```bash
python3 get_sensor_data.py -s 1987654321 -ts "01/15/25" -te "01/16/25" -id 518 -u user@example.com -o csv
```

#### Download Peak Regenerative Power with Time Window
```bash
python3 get_sensor_data.py -s 1987654321 -ts "01/15/25 08:00" -te "01/15/25 18:00" -id 531 -u user@example.com -o both -f regen_power
```

#### Interactive Date Entry with Known Sensor
```bash
# Prompts for dates when not provided
python3 get_sensor_data.py -s 1234567890 -id 509 -u user@example.com
```

### Download with Verbose Output for Debugging

```bash
python3 get_sensor_data.py -s 1234567890 -ts 1736899200000 -te 1736985600000 -id 509 -u user@example.com -v
```

## Multi-Sensor Download

Download data from multiple sensors in a single request with combined JSON output.

### Command Line Multi-Sensor

Use multiple `-id` flags to specify sensors:

```bash
# Download three sensors at once
python3 get_sensor_data.py -s 592978988 -id 509 -id 514 -id 522 -ts "01/15/25" -te "01/16/25" -u user@example.com
```

### Interactive Multi-Sensor Selection

During sensor selection, choose **[D] Direct entry** to enter multiple sensor IDs:

```
📊 Sensor Type Selection:
[1] Predefined Energy Sensors (509-537)
[2] Native Device Sensors
[D] Direct entry - Enter sensor ID(s) directly

Enter your choice: D

Enter sensor ID(s) (comma-separated for multiple, e.g., 509, 514, 522):
> 509, 514, 522

✅ Selected 3 sensors: [509, 514, 522]
```

### Combined Output Format

Multi-sensor downloads produce a single JSON file containing all sensor data:

**Filename format:** `{serial}_{id1}_{id2}_{id3}_{date}.json`

Example: `592978988_509_514_522_20250115.json`

```json
{
  "metadata": {
    "serial": "592978988",
    "sensor_count": 3,
    "sensor_ids": [509, 514, 522],
    "start_time": "2025-01-15T00:00:00Z",
    "end_time": "2025-01-16T00:00:00Z",
    "download_time": "2025-01-17T10:30:00Z"
  },
  "sensors": [
    {
      "sensor_id": 509,
      "sensor_name": "MPGe",
      "sensor_units": "mpge",
      "data_points": 1440,
      "statistics": {
        "min": 0.0,
        "max": 100.0,
        "average": 50.5,
        "duration_hours": 24.0
      },
      "data": [
        {"time": 1736899200000, "value": 45.2, "formatted_time": "2025-01-15T00:00:00Z"}
      ]
    },
    {
      "sensor_id": 514,
      "sensor_name": "Trip MPGe",
      ...
    }
  ]
}
```

### Reproducible Command Output

After every download, the tool displays the full CLI command to reproduce the request:

```
📋 To reproduce this request:
   python3 get_sensor_data.py -u user@example.com -s 592978988 -id 509 -id 514 -id 522 -ts 1736899200000 -te 1736985599000 -o json
```

This is useful for:
- Saving exact parameters for future use
- Creating automation scripts
- Sharing download configurations with colleagues
- Debugging and support requests

## Date and Time Input

The tool supports **interactive date entry** and **multiple date formats**! You no longer need to calculate epoch timestamps manually.

### Supported Formats

#### 1. Interactive Mode with Last 24 Hours Default
When dates are not provided, the tool will prompt you. **Press Enter without input to use the last 24 hours**:

```bash
python3 get_sensor_data.py -s 1234567890 -u user@example.com

📅 Date/time range required for data download

Supported formats:
  • Press Enter for last 24 hours (default)
  • Date only: 01/15/25 (assumes midnight to midnight)
  • Date and time: 01/15/25 14:30
  • Epoch milliseconds: 1736899200000
  • Enter 'q' to quit

📅 Enter start date/time (or Enter for last 24h):
✅ Using last 24 hours:
   Start: 2025-01-17T10:30:00Z
   End:   2025-01-18T10:30:00Z
📊 Date range: 24.0 hours
```

**Or enter specific dates:**
```
📅 Enter start date/time (or Enter for last 24h): 01/15/25
✅ Start: 2025-01-15T00:00:00Z
📅 Enter end date/time: 01/15/25
✅ End: 2025-01-15T23:59:59Z
📊 Date range: 24.0 hours
```

#### 2. Command-Line Date Formats (NEW)

**Date Only (Midnight to Midnight)**
```bash
python3 get_sensor_data.py -s 1234567890 -ts "01/15/25" -te "01/16/25" -u user@example.com
```

**Date with Specific Time**
```bash
python3 get_sensor_data.py -s 1234567890 -ts "01/15/25 09:00" -te "01/15/25 17:00" -u user@example.com
```

**Mixed Formats**
```bash
python3 get_sensor_data.py -s 1234567890 -ts "01/15/25" -te 1736985600000 -u user@example.com
```

#### 3. Epoch Milliseconds (Original)
```bash
python3 get_sensor_data.py -s 1234567890 -ts 1736899200000 -te 1736985600000 -u user@example.com
```

### Date Format Reference

| Format | Example | Start Time | End Time |
|--------|---------|------------|----------|
| `mm/dd/yy` | `01/15/25` | 00:00:00 | 23:59:59 |
| `mm/dd/yy hh:mm` | `01/15/25 14:30` | 14:30:00 | (as specified) |
| Epoch milliseconds | `1736899200000` | (as specified) | (as specified) |

### Year Conversion Rules
- **00-49**: Interpreted as 2000-2049 (e.g., `25` = `2025`)
- **50-99**: Interpreted as 1950-1999 (e.g., `98` = `1998`)

## Legacy Timestamp Conversion

For manual timestamp calculation, here are conversion examples:

### Python

```python
from datetime import datetime

# Convert date to epoch milliseconds
dt = datetime(2025, 1, 15, 0, 0, 0)
epoch_ms = int(dt.timestamp() * 1000)
print(epoch_ms)  # 1736899200000

# Current time in epoch milliseconds
now_ms = int(datetime.now().timestamp() * 1000)
```

### Bash

```bash
# Date to epoch milliseconds
date -d "2025-01-15 00:00:00" +%s000

# Current time in epoch milliseconds
date +%s000
```

### Online Tools

- [epochconverter.com](https://www.epochconverter.com/)
- [currentmillis.com](https://currentmillis.com/)

## Output Formats

### JSON Format

The JSON output includes metadata, statistics, and the raw data:

```json
{
  "metadata": {
    "serial": "1234567890",
    "sensor_id": 509,
    "sensor_name": "MPGe",
    "sensor_units": "mpge",
    "start_time": "2025-01-15T00:00:00Z",
    "end_time": "2025-01-16T00:00:00Z",
    "download_time": "2025-01-17T10:30:00Z",
    "data_points": 1440
  },
  "statistics": {
    "min": 0.0,
    "max": 100.0,
    "average": 50.5,
    "count": 1440,
    "first_time": "2025-01-15T00:00:00Z",
    "last_time": "2025-01-15T23:59:00Z",
    "duration_hours": 24.0
  },
  "data": [
    {
      "time": 1736899200000,
      "value": 45.2,
      "formatted_time": "2025-01-15T00:00:00Z"
    }
  ]
}
```

### CSV Format

The CSV output includes metadata as comments and data in tabular format:

```csv
# Sensor Data Export
# Serial: 1234567890
# Sensor: MPGe (ID: 509)
# Units: mpge
# Start: 2025-01-15T00:00:00Z
# End: 2025-01-16T00:00:00Z
# Data Points: 1440
# Min Value: 0.0
# Max Value: 100.0
# Average: 50.50
#
timestamp_ms,value,formatted_time
1736899200000,45.2,2025-01-15T00:00:00Z
1736899260000,45.3,2025-01-15T00:01:00Z
```

## Sensor ID Reference

### Energy and Trip Sensors (509-537)

| ID | Sensor Name | Units | Description |
|----|-------------|-------|-------------|
| 509 | MPGe | mpge | Miles Per Gallon equivalent |
| 510 | Trip UTC Start Time | Time | Trip start timestamp |
| 511 | Trip UTC End Time | Time | Trip end timestamp |
| 512 | Trip idle time | Seconds | Total idle duration |
| 513 | Trip Wh/km | Wh/km | Energy consumption rate |
| 514 | Trip MPGe | mpge | Trip fuel economy |
| 515 | Trip l/100km | l/100km | Fuel consumption equivalent |
| 516 | Trip CO2 Emissions | kg | Carbon dioxide emissions |
| 517 | Trip Power | kWh | Total power consumed |
| 518 | Trip Energy Recovered | kWH | Regenerative energy |
| 519 | Trip Charge | kWH | Energy charged |
| 520 | Trip Average Charge Rate | kW | Mean charging power |
| 521 | Trip Peak Charge Rate | kW | Maximum charging power |
| 522 | Trip Average Speed | km | Mean velocity |
| 523 | Trip Maximum Speed | km | Peak velocity |
| 524 | Trip number hard accelerations | Qty | Aggressive acceleration count |
| 525 | Trip number hard braking | Qty | Aggressive braking count |
| 526 | Trip number hard turns | Qty | Aggressive turning count |
| 527 | Maximum deceleration | g | Peak deceleration force |
| 528 | Trip fault Codes | Code | Error codes during trip |
| 529 | Peak power | kW | Maximum power draw |
| 530 | Range gained per minute | km/min | Charging speed in range |
| 531 | Peak Regenerative Power | kW | Maximum regen power |
| 532 | Peak Brake Pedal | % | Maximum brake application |
| 533 | Peak Accel Pedal | % | Maximum accelerator application |
| 534 | DTC OBD2 Codes | Code | OBD2 diagnostic codes |
| 535 | DTC J1939 Codes | Code | J1939 diagnostic codes |
| 536 | DTC HM Truck Codes | Code | Manufacturer diagnostic codes |
| 537 | DTC Echassie Codes | Code | Chassis diagnostic codes |

### Common Sensors

| ID | Sensor Name | Units |
|----|-------------|-------|
| 2 | Latitude | degrees |
| 3 | Longitude | degrees |
| 500 | Cumulative Throughput | kWh |
| 501 | Charge Rate | kW |
| 502 | Estimated Range | km |
| 503 | Battery State of Health | % |
| 504 | Trip Distance | km |
| 505 | Charging Status | state |
| 506 | Trip Meter | km |

## Troubleshooting

### Common Issues

#### Authentication Failed
- Verify your username (email) is correct
- Check your password
- Ensure your account has API access enabled

#### Device Discovery Issues (NEW)

**Device Not Found (404 Error)**
- Verify the device serial number is correct
- Check if the device exists in your organization
- Ensure you have access permissions for the device

**No Sensors Found**
- Device may not have any configured sensors
- Check device setup in iMatrix Cloud
- Try using `--product-info` to see device details

**Sensor Details Not Available**
- Some sensors may not have detailed information
- This is normal - the tool will skip sensors without details
- Use `-v` flag to see which sensors are being skipped

#### Data Download Issues

**No Data Found**
- Verify the time range contains data
- Check if the device was online during that period
- Ensure the selected sensor actually records data

**Date/Time Format Issues (NEW)**
- **Invalid date format**: Use `mm/dd/yy` or `mm/dd/yy hh:mm`
- **Invalid time format**: Time must be `hh:mm` (24-hour format)
- **Date out of range**: Check month (1-12), day (1-31), year (00-99)
- **Time out of range**: Hours (0-23), minutes (0-59)

**Examples of valid formats:**
- `01/15/25` (January 15, 2025 midnight to midnight)
- `01/15/25 14:30` (January 15, 2025 at 2:30 PM)
- `1736899200000` (epoch milliseconds)

**Invalid Timestamp Format (Legacy)**
- Timestamps must be in milliseconds, not seconds
- To convert seconds to milliseconds, multiply by 1000
- Use the new date formats instead: `01/15/25`

**Missing Time Arguments**
- The tool will now prompt for dates if not provided
- Use `--list-sensors` or `--product-info` for information-only modes

#### Connection Errors
- Check your internet connection
- Verify the API server is accessible
- Try using the `-v` flag for verbose output
- Some API endpoints may have rate limits - add delays between requests

### Debug Mode

Use the verbose flag to see detailed information:

```bash
python3 get_sensor_data.py -s 1234567890 -ts 1736899200000 -te 1736985600000 -id 509 -u user@example.com -v
```

This will show:
- Full API URLs being accessed
- Detailed error messages
- Response status codes

## Advanced Usage

### Batch Download Multiple Sensors

Create a shell script to download multiple sensors:

```bash
#!/bin/bash

SERIAL="1234567890"
START="1736899200000"
END="1736985600000"
EMAIL="user@example.com"

# List of sensor IDs to download
SENSORS=(509 513 518 531)

for SENSOR_ID in "${SENSORS[@]}"; do
    echo "Downloading sensor $SENSOR_ID..."
    python3 get_sensor_data.py -s "$SERIAL" -ts "$START" -te "$END" -id "$SENSOR_ID" -u "$EMAIL" -o both
    sleep 2  # Avoid rate limiting
done
```

### Process Downloaded Data

Example Python script to process the JSON output:

```python
import json
import pandas as pd

# Load the data
with open('1234567890_MPGe_20250115.json', 'r') as f:
    data = json.load(f)

# Convert to pandas DataFrame
df = pd.DataFrame(data['data'])
df['timestamp'] = pd.to_datetime(df['time'], unit='ms')

# Analysis
print(f"Average: {df['value'].mean()}")
print(f"Peak: {df['value'].max()}")

# Plot
df.plot(x='timestamp', y='value', title='MPGe Over Time')
```

## API Rate Limits

- The iMatrix API may have rate limits
- Add delays between multiple requests
- Consider downloading larger time ranges in single requests

## Security Notes

- Never commit passwords to version control
- Use environment variables for credentials in scripts
- The tool disables SSL warnings for development - enable SSL verification in production

## Support

For issues or questions:
- Check the troubleshooting section above
- Review the verbose output (`-v` flag)
- Contact iMatrix support for API access issues

## License

This tool is provided as-is for use with iMatrix Cloud systems.

## Version History

- 2.0.0 (2025-12-08): Multi-sensor download and enhanced features
  - **Multi-sensor download**: Download multiple sensors in a single request
  - **Combined JSON output**: Single file containing all sensor data
  - **Direct sensor ID entry**: [D] option in sensor menu for comma-separated IDs
  - **Multiple -id flags**: Command line support for `-id 509 -id 514 -id 522`
  - **Last 24 hours default**: Press Enter at date prompt for quick access
  - **Reproducible command output**: Full CLI command displayed after download
  - **Enhanced filename format**: Includes all sensor IDs (`serial_id1_id2_id3_date.json`)

- 1.0.0 (2025-01-17): Initial release with support for sensors 509-537
  - JSON and CSV output formats
  - Statistics calculation
  - Sensor definitions for energy metrics

## Contributing

To add new sensor definitions:
1. Edit the `SENSOR_DEFINITIONS` dictionary in the script
2. Add the sensor ID, name, and units
3. Test with the new sensor ID