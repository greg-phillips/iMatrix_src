# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **iMatrix Sensor Data Download Tool** (`get_sensor_data.py`) - a comprehensive Python application for downloading sensor data from the iMatrix Cloud API with complete interactive workflows and device discovery capabilities.

The tool is part of the larger iMatrix ecosystem and serves as the primary interface for users to access historical sensor data from IoT devices in their accounts.

## Core Architecture

### Multi-Mode Design Pattern
The application follows a **progressive disclosure** pattern with five distinct operational modes:

1. **Complete Interactive Mode** (Default): Full device → sensor → date workflow
2. **Partial Interactive Mode**: Skip known steps (device-specific or sensor-specific entry)
3. **Information-Only Mode**: Device and sensor discovery without downloading
4. **Direct Mode**: No interaction required (all parameters provided)
5. **Multi-Sensor Mode**: Download multiple sensors at once with combined JSON output

### Key Components

#### Authentication & API Layer (`get_sensor_data.py:110-164`)
- `login_to_imatrix()` - Handles API authentication with dev/prod environment switching
- `get_api_base_url()` - Environment-aware URL configuration
- Uses token-based authentication with `x-auth-token` header

#### Device Discovery System (`get_sensor_data.py:166-434`)
- `get_user_devices()` - Fetches all user devices via `/things/` endpoint
- `get_product_info()` - Retrieves device details via `/products/{id}` endpoint
- `discover_device_sensors()` - Complete device sensor discovery workflow
- `get_sensor_details()` - Individual sensor information via `/sensors/{id}` endpoint

#### Interactive User Interface (`get_sensor_data.py:465-630`)
- `display_device_list()` - 4-column device selection table
- `select_device_interactive()` - Device selection with validation
- `display_sensor_menu()` - Interactive sensor selection interface
- `print_device_details()` - Formatted device information display

#### Date/Time Processing (`get_sensor_data.py:676-947`)
- `parse_flexible_datetime()` - Multi-format date parsing (epoch, human-readable)
- `prompt_for_date_range()` - Interactive date entry with format guidance, supports blank input for last 24 hours
- `get_timestamps_interactive()` - Unified timestamp handling workflow
- Supports: epoch milliseconds, `mm/dd/yy`, `mm/dd/yy hh:mm` formats
- **Blank input = last 24 hours**: Press Enter to use current time minus 24 hours

#### Data Management (`get_sensor_data.py:948-1244`)
- `fetch_sensor_history()` - Downloads data via `/things/{serial}/sensor/{id}/history/{start}/{end}`
- `parse_sensor_data()` - Converts API response to structured format
- `calculate_statistics()` - Min/max/average/duration statistics
- `save_as_json()` / `save_as_csv()` - Multiple output format support

#### Multi-Sensor Support
- `prompt_sensor_type_selection()` - Returns `Tuple[str, Optional[List[int]]]` for sensor type and direct IDs
- `download_multiple_sensors()` - Iterates through sensor list and downloads all data
- `save_combined_json()` - Saves multi-sensor data to single combined JSON file
- `print_combined_summary()` - Displays statistics summary for all downloaded sensors
- `generate_multi_sensor_filename()` - Creates filename with all sensor IDs: `{serial}_{id1}_{id2}_{id3}_{date}.json`

#### Reproducible Command Output
- `generate_cli_command()` - Builds full CLI command string with all parameters
- `print_reproducible_command()` - Displays command that can reproduce the download

## Development Commands

### Running the Tool

#### Interactive Mode (Complete Workflow)
```bash
python3 get_sensor_data.py -u <email>
```

#### Information-Only Operations
```bash
# List all user devices
python3 get_sensor_data.py -u <email> --list-devices

# Show device sensors
python3 get_sensor_data.py -s <serial> -u <email> --list-sensors

# Show device information
python3 get_sensor_data.py -s <serial> -u <email> --product-info
```

#### Direct Data Download
```bash
# With human-readable dates
python3 get_sensor_data.py -s <serial> -ts "01/15/25" -te "01/16/25" -id <sensor_id> -u <email>

# With epoch timestamps
python3 get_sensor_data.py -s <serial> -ts <start_ms> -te <end_ms> -id <sensor_id> -u <email>

# Press Enter for last 24 hours (interactive date prompt)
python3 get_sensor_data.py -s <serial> -id <sensor_id> -u <email>
# Then press Enter at date prompt for quick last-24-hours download
```

#### Multi-Sensor Download
```bash
# Download multiple sensors with separate -id flags
python3 get_sensor_data.py -s <serial> -id 509 -id 514 -id 522 -ts "01/15/25" -te "01/16/25" -u <email>

# Interactive multi-sensor: choose [D] Direct entry, then enter comma-separated IDs
# Example: 509, 514, 522
```

### Testing and Debugging

#### Verbose Mode
```bash
python3 get_sensor_data.py -v -u <email>
```
Shows API URLs, detailed error messages, and request/response debugging.

#### Environment Switching
```bash
# Production (default)
python3 get_sensor_data.py -u <email>

# Development API
python3 get_sensor_data.py -dev -u <email>
```

### Dependencies
```bash
python3 -m pip install requests urllib3
```

## API Integration Architecture

### Endpoint Usage Pattern
The tool uses a **discovery-first** approach to the iMatrix API:

1. **Authentication**: `POST /api/v1/login`
2. **Device Discovery**: `GET /api/v1/things/?per_page=100`
3. **Product Info**: `GET /api/v1/products/{product_id}`
4. **Sensor Details**: `GET /api/v1/sensors/{sensor_id}`
5. **Data Download**: `GET /api/v1/things/{serial}/sensor/{sensor_id}/history/{start}/{end}`

### Error Handling Strategy
- **Progressive degradation**: Continue workflow even if some sensor details unavailable
- **User-friendly messages**: Convert API errors to actionable guidance
- **Retry mechanisms**: Built-in for network issues and user input errors
- **Graceful cancellation**: 'q' to quit at any interactive prompt

## Key Data Structures

### Device Object
```python
{
    "sn": 592978988,                    # Serial number (used for API calls)
    "name": "Greg's Desk NEO-1D",       # Display name
    "productId": 1349851161,            # Product ID for /products/ endpoint
    "groupId": 1082477619,              # Organization grouping
    "organizationId": 298726404,        # Organization ID
    "currentVersion": "1.023.000"       # Firmware version
}
```

### Sensor Object
```python
{
    "id": 58108062,                     # Sensor ID for API calls
    "name": "Temperature",              # Display name
    "units": "Deg. C",                  # Measurement units
    "dataType": "IMX_FLOAT",           # Data type
    "productId": 1349851161            # Parent product
}
```

### Built-in Sensor Definitions
The tool includes predefined definitions for energy sensors (IDs 509-537) in `SENSOR_DEFINITIONS` dictionary for enhanced display when sensor details API unavailable.

## Code Conventions and Patterns

### Function Organization
- **API functions**: Return data or raise SystemExit on failure
- **UI functions**: Handle user interaction and input validation
- **Data functions**: Pure data transformation without side effects
- **Main workflow**: Orchestrates components based on argument parsing

### Error Handling Pattern
```python
try:
    response = requests.get(url, headers=headers, timeout=30, verify=False)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Error: {response.status_code}")
        sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"❌ Network error: {e}")
    sys.exit(1)
```

### Argument Parsing Strategy
- **Optional arguments**: Enable progressive disclosure
- **Mode flags**: `--list-devices`, `--list-sensors`, `--product-info`
- **Environment flags**: `-dev` for API environment switching
- **Output control**: `-o` for format, `-f` for filename, `-v` for verbose
- **Multi-sensor**: `-id` uses `action='append'` to collect multiple sensor IDs

## Common Development Workflows

### Adding New Sensor Types
1. Update `SENSOR_DEFINITIONS` dictionary with new sensor IDs
2. Test with `--list-sensors` to verify API response handling
3. Validate data download for new sensor types

### Extending API Coverage
1. Add new API endpoint functions following existing patterns
2. Implement error handling and verbose logging
3. Update help text and documentation
4. Test with both dev and production environments

### UI Enhancement
1. Follow existing emoji-based status indicators (🔍, ✅, ❌, 📊)
2. Maintain 4-column table formatting for consistency
3. Provide clear cancellation options ('q' to quit)
4. Include input validation with retry prompts

### Output Format Changes
1. Modify `save_as_json()` or `save_as_csv()` functions
2. Ensure statistics calculation remains consistent
3. Update filename generation if needed
4. Test with various data sizes and sensor types

## Testing Approach

### Manual Testing Scenarios
1. **Complete workflow**: Test full device → sensor → date → download flow
2. **Partial workflows**: Test each entry point (device-known, sensor-known)
3. **Error conditions**: Invalid devices, missing sensors, network failures
4. **Date formats**: All supported input formats and edge cases
5. **Environment switching**: Dev vs production API endpoints
6. **Multi-sensor download**: Test combined JSON output with multiple `-id` flags
7. **Direct sensor entry**: Test [D] option with comma-separated IDs (e.g., `509, 514, 522`)
8. **Last 24 hours default**: Test blank Enter at date prompt
9. **Reproducible command**: Verify CLI command output matches actual parameters

### Debugging Tools
- **Verbose mode** (`-v`): Shows API URLs and detailed responses
- **Information modes**: Test API connectivity without data download
- **Error reproduction**: Use invalid parameters to verify error handling

## Security Considerations

- **SSL verification disabled**: `verify=False` in requests (development convenience)
- **Password handling**: Secure prompt when not provided via command line
- **Token management**: Tokens are request-scoped, not persistent
- **API rate limiting**: Built-in delays between discovery requests

## Integration Notes

This tool is designed to work with other iMatrix ecosystem tools:
- **Parent tools directory**: Part of larger iMatrix toolkit at `/tools/`
- **Shared patterns**: Follows same API authentication patterns as `get_loc.py`
- **Output compatibility**: JSON format compatible with other analysis tools
- **Configuration consistency**: Uses same dev/prod environment switching

When modifying this tool, maintain compatibility with the broader iMatrix toolkit conventions and ensure changes don't break automation scripts that depend on the tool's output format or command-line interface.