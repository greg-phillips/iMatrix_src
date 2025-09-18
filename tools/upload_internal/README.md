# Internal Sensor Management Tools

## Overview

The `upload_internal` directory contains tools for creating and managing internal sensor definitions in the iMatrix Cloud system. These tools are used to define new sensor types that can be used across multiple products and devices.

## Tools

### upload_internal_sensor.py

**Purpose:** Upload individual internal sensor definitions from JSON files

**Features:**
- Creates predefined sensors in iMatrix Cloud
- JSON-based sensor definition format
- Comprehensive validation of sensor parameters
- Support for all iMatrix data types and units
- Dry-run mode for validation without upload
- Detailed error reporting and troubleshooting

### upload_list.sh

**Purpose:** Batch upload multiple sensor definitions

**Features:**
- Automated batch processing of sensor JSON files
- Sequential upload with status tracking
- Error handling for failed uploads
- Designed for initial system setup

## Installation

### Prerequisites
- Python 3.6 or higher
- Bash shell (for .sh scripts)
- pip package manager

### Dependencies
```bash
python3 -m pip install requests urllib3
```

## Usage

### Individual Sensor Upload

#### Basic Command Structure
```bash
python3 upload_internal_sensor.py -u <email> -f <json_file>
```

#### Required Arguments
- `-u, --username`: iMatrix Cloud username (email)
- `-f, --file`: JSON sensor definition file

#### Optional Arguments
- `-p, --password`: Password (secure prompt if omitted)
- `--validate-only`: Validate JSON without uploading
- `--pro`: Use production API (default: development)

### Batch Upload

#### Run Batch Script
```bash
./upload_list.sh
```

**Note:** Edit script to update credentials and file list before running.

## Examples

### Upload Single Sensor
```bash
# Upload MPGe sensor definition
python3 upload_internal_sensor.py -u user@example.com -f sensor_509.json
```

### Validate Before Upload
```bash
# Check JSON format without uploading
python3 upload_internal_sensor.py -u user@example.com -f sensor_509.json --validate-only
```

### Upload to Production
```bash
# Upload to production API
python3 upload_internal_sensor.py -u user@example.com -f sensor_509.json --pro
```

### Batch Upload Energy Sensors
```bash
# Upload all energy sensors (509-537)
for i in {509..537}; do
    echo "Uploading sensor $i..."
    python3 upload_internal_sensor.py -u user@example.com -f ../sensor_${i}.json
    sleep 1  # Avoid rate limiting
done
```

## JSON Sensor Definition Format

### Basic Structure
```json
{
    "id": 509,
    "type": 1,
    "name": "MPGe",
    "units": "mpge",
    "unitsType": "IMX_NATIVE",
    "dataType": "IMX_FLOAT",
    "defaultValue": 0,
    "mode": "scalar",
    "states": 0,
    "iconUrl": "https://storage.googleapis.com/imatrix-files/icon.svg",
    "thresholdQualificationTime": 0,
    "minAdvisoryEnabled": false,
    "minAdvisory": 0,
    "minWarningEnabled": false,
    "minWarning": 0,
    "minAlarmEnabled": false,
    "minAlarm": 0,
    "maxAdvisoryEnabled": false,
    "maxAdvisory": 0,
    "maxWarningEnabled": false,
    "maxWarning": 0,
    "maxAlarmEnabled": false,
    "maxAlarm": 0,
    "maxGraph": 10000,
    "minGraph": 0,
    "calibrationMode": 0,
    "calibrateValue1": 0,
    "calibrateValue2": 0,
    "calibrateValue3": 0,
    "calibrationRef1": 0,
    "calibrationRef2": 0,
    "calibrationRef3": 0
}
```

### Required Fields
- **id**: Unique sensor identifier (integer)
- **type**: Sensor type (typically 1 for predefined)
- **name**: Human-readable sensor name
- **units**: Unit of measurement
- **unitsType**: Unit category (IMX_NATIVE, IMX_METRIC, IMX_IMPERIAL)
- **dataType**: Data type (IMX_FLOAT, IMX_INT32, etc.)
- **defaultValue**: Default value when no data available
- **mode**: Measurement mode (scalar, array, etc.)
- **states**: Number of discrete states (0 for continuous)

### Data Types Supported
- **IMX_INT8**: 8-bit signed integer (-128 to 127)
- **IMX_UINT8**: 8-bit unsigned integer (0 to 255)
- **IMX_INT16**: 16-bit signed integer (-32,768 to 32,767)
- **IMX_UINT16**: 16-bit unsigned integer (0 to 65,535)
- **IMX_INT32**: 32-bit signed integer
- **IMX_UINT32**: 32-bit unsigned integer
- **IMX_FLOAT**: 32-bit floating point
- **IMX_STRING**: Text string

### Units Types
- **IMX_NATIVE**: Native units (custom or dimensionless)
- **IMX_METRIC**: Metric system units (km, kg, °C)
- **IMX_IMPERIAL**: Imperial system units (miles, lb, °F)

## Validation Rules

### JSON Validation
- All required fields must be present
- Data types must be from valid list
- ID must be unique (not already used)
- Numeric values must be within reasonable ranges

### Sensor ID Guidelines
- **1-99**: Reserved for system sensors
- **100-499**: Product-specific sensors
- **500-508**: Core system sensors (in use)
- **509-537**: Energy and trip sensors (in use)
- **538+**: Available for new sensors

## API Integration

### Endpoints Used
- **Authentication**: `POST /login`
- **Create Sensor**: `POST /sensors/predefined`

### Request Validation
The API validates:
- Required field presence
- Data type validity
- ID uniqueness
- Permission levels
- JSON format correctness

## Error Handling

### Common Error Codes
- **400**: Invalid JSON format or missing required fields
- **401**: Authentication failed
- **403**: Insufficient permissions
- **409**: Sensor ID already exists
- **422**: Validation failed (invalid data types, etc.)

### Troubleshooting Steps
1. **Validate JSON**: Use `--validate-only` flag first
2. **Check ID**: Ensure sensor ID is not already used
3. **Verify Fields**: Confirm all required fields present
4. **Test Permissions**: Verify account has sensor creation rights
5. **Check API**: Ensure API server is accessible

## Workflow Integration

### Complete Sensor Setup Process
1. **Design Sensor**: Define purpose, units, and data type
2. **Create JSON**: Use existing sensor files as templates
3. **Validate**: Test JSON format with `--validate-only`
4. **Upload**: Create sensor definition in iMatrix Cloud
5. **Link**: Use [link_sensor.py](../link_sensor/) to associate with products
6. **Test**: Use [get_sensor_data.py](../get_sensor_data/) to verify functionality

### Batch Setup Process
1. **Prepare Files**: Create all sensor JSON files
2. **Edit Script**: Update upload_list.sh with file names
3. **Run Batch**: Execute batch upload script
4. **Verify**: Check all sensors created successfully
5. **Link**: Use batch linking for product association

## Related Tools

### Direct Dependencies
- **[link_sensor.py](../link_sensor/)**: Link uploaded sensors to products
- **[get_sensor_data.py](../get_sensor_data/)**: Test sensor functionality

### Workflow Tools
- **[convert_sensor_list.py](../convert_sensor_list.py)**: Convert Excel to JSON format
- **[create_tire_sensors.py](../create_tire_sensors.py)**: Specialized tire sensor creation

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-17 | Initial documentation |
|  |  | - Complete usage guide |
|  |  | - JSON format specification |
|  |  | - Validation rules documentation |
|  |  | - Workflow integration guide |

---

*Part of the iMatrix Tools Suite - See [main README](../README.md) for complete tool overview*