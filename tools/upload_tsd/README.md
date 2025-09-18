# Time Series Data Upload Tools

This directory contains scripts for uploading time series data to the iMatrix Cloud API.

## upload_sine_wave.py

Generates and uploads sine wave pattern time series data to the iMatrix Cloud API. Designed for testing time series data uploads with a predictable pattern.

### Features

- Generates sine wave data with values ranging from 0 to 100
- Adds marker values (101, 102, 103, 104) after each cycle for easy identification
- Repeats the pattern 5 times for a total of 320 data points
- Supports both development and production API endpoints
- Includes dry-run mode for testing without uploading
- JSON display option to view the exact payload before sending
- Batch uploading to handle large datasets efficiently

### Data Pattern

The script generates the following pattern:
1. **Sine Wave**: 60 samples over 1 hour (1 sample per minute)
   - Values calculated as: `50 + 50 * sin(2π * t/60)`
   - Range: 0 to 100
2. **Marker Values**: After each sine wave cycle, adds 4 sequential values:
   - 101, 102, 103, 104 (easy to identify cycle boundaries)
3. **Repetition**: Entire sequence (64 samples) repeated 5 times
   - Total: 320 data points spanning approximately 5.3 hours

### Installation

```bash
# Install required Python dependencies
pip3 install requests urllib3
```

### Usage

All four parameters are **mandatory**: username (`-U`), password (`-P`), serial number (`-s`), and start time (`-T`).

#### Basic Usage
```bash
python3 upload_sine_wave.py -U user@example.com -P mypassword -s 1000000001 -T 1735689600000
```

#### Dry Run (preview data without uploading)
```bash
python3 upload_sine_wave.py -U user@example.com -P mypassword -s 1000000001 -T 1735689600000 --dry-run
```

#### Use Production API
```bash
python3 upload_sine_wave.py -U user@example.com -P mypassword -s 1000000001 -T 1735689600000 --pro
```

#### Custom Sensor ID (default is 126)
```bash
python3 upload_sine_wave.py -U user@example.com -P mypassword -s 1000000001 -T 1735689600000 -S 500
```

#### Display Full JSON Payload (Dry Run - No Upload)
```bash
python3 upload_sine_wave.py -U user@example.com -P mypassword -s 1000000001 -T 1735689600000 --dry-run --show-json
```

#### Display JSON and Upload
```bash
python3 upload_sine_wave.py -U user@example.com -P mypassword -s 1000000001 -T 1735689600000 --show-json
```

### Command Line Options

| Option | Description | Required | Default |
|--------|-------------|----------|---------|
| `-U, --username` | iMatrix Cloud username (email) | **Yes** | - |
| `-P, --password` | iMatrix Cloud password | **Yes** | - |
| `-s, --serial` | Device serial number | **Yes** | - |
| `-T, --start-time` | Start time in milliseconds since epoch | **Yes** | - |
| `-S, --sensor-id` | Sensor ID for the data | No | 126 |
| `--dry-run` | Generate and display data without uploading | No | False |
| `--show-json` | Display the full JSON payload that will be sent | No | False |
| `--pro` | Use production API endpoint | No | False (uses dev) |

### Time Calculation

To calculate the start time in milliseconds:

```python
from datetime import datetime

# For a specific date/time
dt = datetime(2024, 1, 1, 12, 0, 0)  # Jan 1, 2024, 12:00:00
start_time_ms = int(dt.timestamp() * 1000)
print(start_time_ms)  # 1704110400000

# For current time
import time
current_time_ms = int(time.time() * 1000)
```

### API Endpoints

- **Development**: `https://api-dev.imatrixsys.com/api/v1/`
- **Production**: `https://api.imatrixsys.com/api/v1/`

### Data Format

The script uploads data in the following format:

```json
{
  "data": {
    "1000000001": {
      "126": [
        {"time": 1735689600000, "value": 50.0},
        {"time": 1735689660000, "value": 55.23},
        ...
      ]
    }
  }
}
```

The `--show-json` option displays the complete JSON payload with all 320 data points.

### Example Output

#### Standard Upload
```
📅 Start time: 2025-01-01T00:00:00
📊 Generating sine wave data starting at 2025-01-01T00:00:00
  Cycle 1/5...
  Cycle 2/5...
  Cycle 3/5...
  Cycle 4/5...
  Cycle 5/5...
✅ Generated 320 data points
   Time range: 2025-01-01T00:00:00 to 2025-01-01T05:19:00
🔐 Logging in to development API...
✅ Login successful.

📤 Uploading 320 data points in 4 batches...
   Batch 1/4: Uploading points 1-100... ✅
   Batch 2/4: Uploading points 101-200... ✅
   Batch 3/4: Uploading points 201-300... ✅
   Batch 4/4: Uploading points 301-320... ✅
✅ All data uploaded successfully!

✨ Done!
```

#### Dry Run with JSON Display
```
📅 Start time: 2024-12-31T16:00:00
📊 Generating sine wave data starting at 2024-12-31T16:00:00
  Cycle 1/5...
  ...
✅ Generated 320 data points

📋 JSON PAYLOAD:
{
  "data": {
    "650465129": {
      "126": [
        {
          "time": 1735689600000,
          "value": 50.0
        },
        {
          "time": 1735689660000,
          "value": 55.23
        },
        ...
      ]
    }
  }
}

✅ JSON displayed (dry-run mode, not uploaded)
✨ Done!
```

### Troubleshooting

1. **Missing Required Parameters**: All four parameters are mandatory:
   ```
   upload_sine_wave.py: error: the following arguments are required: -P/--password, -s/--serial
   ```
   Solution: Ensure you provide `-U`, `-P`, `-s`, and `-T` on the command line.

2. **SSL Certificate Warnings**: The script disables SSL verification for development. This is intentional for the dev environment.

3. **Authentication Failed**: Ensure your username and password are correct for the selected environment (dev/prod).

4. **Invalid Start Time**: The start time must be in milliseconds since epoch (January 1, 1970).
   ```python
   # Convert datetime to milliseconds
   import datetime
   dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
   ms = int(dt.timestamp() * 1000)
   ```

5. **Upload Failures**: The script uploads in batches of 100 points. If a batch fails, check:
   - Network connectivity
   - API service status  
   - Authentication token validity
   - Correct JSON format (use `--show-json` to verify)

### Security Notes

- **Never commit credentials to version control** - Use command-line args or environment variables
- The password is required on the command line (no interactive prompt for automation compatibility)
- The script disables SSL verification for development only
- Always use `--pro` flag with proper SSL certificates in production
- Consider using a credentials file with restricted permissions for production use