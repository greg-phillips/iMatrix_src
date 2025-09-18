# Root Level Tools Documentation

## Overview

This document covers the utility scripts located in the root `/tools/` directory. These are specialized tools for data conversion, sensor creation, traffic analysis, and automation workflows.

## Tools

### convert_sensor_list.py

**Purpose:** Convert Excel sensor lists to C header files with #define statements

**Features:**
- Reads Excel files with sensor ID and name columns
- Generates C header files using blank.h template
- Sanitizes sensor names to valid C identifiers
- Automatically creates output filenames
- Handles special characters and spaces in names

#### Usage
```bash
python3 convert_sensor_list.py <input_excel_file>
```

#### Example
```bash
python3 convert_sensor_list.py "Sensor List.xlsx"
# Output: sensor_list_defines.h
```

#### Input Excel Format
| Sensor ID | Sensor Name |
|-----------|-------------|
| 509 | MPGe |
| 510 | Trip Start Time |
| 511 | Trip End Time |

#### Output C Header
```c
#define MPGE                     509
#define TRIP_START_TIME          510
#define TRIP_END_TIME            511
```

### create_tire_sensors.py

**Purpose:** Create comprehensive tire monitoring sensor definitions

**Features:**
- Creates sensors for all tire positions (A1-A10)
- Supports multiple tire metrics (pressure, temperature, load, etc.)
- Predefined sensor mappings with appropriate ranges
- Batch creation with progress tracking
- Position-aware naming (Left Outer, Right Inner, etc.)

#### Usage
```bash
python3 create_tire_sensors.py -u <email> -f <data_file>
```

#### Example
```bash
python3 create_tire_sensors.py -u user@example.com -f tire_sensors_data.txt
```

#### Sensor Categories
- **Pressure**: 0-1,000,000 Pa range
- **Temperature**: -40°C to 150°C range
- **Load**: 0-5,000 kg range
- **Toe/Camber**: -10° to 10° range
- **Wear**: 0-100% range
- **Lug Nut**: 0-100% torque range

### filter_can.py

**Purpose:** CAN traffic filtering and analysis tool

**Features:**
- Filters CAN messages by ID, data patterns, or time ranges
- Supports multiple input formats (log files, real-time capture)
- Statistical analysis of message frequencies
- Export filtered results to various formats
- Pattern recognition for diagnostic analysis

#### Usage
```bash
python3 filter_can.py -i <input_file> -o <output_file> [filters]
```

#### Example
```bash
# Filter by CAN ID
python3 filter_can.py -i can_traffic.log -o filtered.log --id 0x123

# Filter by time range
python3 filter_can.py -i can_traffic.log -o filtered.log --start 1736899200000 --end 1736985600000
```

### link_hm_wrecker_sensors.sh

**Purpose:** Automated sensor linking for HM Wrecker platform

**Features:**
- Links all HM Wrecker-specific sensors to product
- Hardcoded sensor IDs for HM Wrecker configuration
- Sequential processing with error handling
- Status reporting and confirmation

#### Usage
```bash
./link_hm_wrecker_sensors.sh
```

**Note:** Edit script to update credentials and product ID before running.

#### Linked Sensors
- Energy management sensors (509-537)
- Battery monitoring sensors
- Trip tracking sensors
- Diagnostic sensors

## Installation

### Prerequisites
- Python 3.6 or higher
- pandas library (for Excel processing)
- openpyxl library (for Excel file reading)

### Dependencies
```bash
python3 -m pip install requests urllib3 pandas openpyxl
```

## Detailed Usage Examples

### Excel to C Header Conversion

#### Input Excel File (sensor_list.xlsx)
```
| A       | B                    |
|---------|----------------------|
| ID      | Name                 |
| 509     | MPGe                 |
| 510     | Trip Start Time      |
| 511     | Trip End Time        |
| 512     | Trip Idle Time       |
```

#### Command
```bash
python3 convert_sensor_list.py sensor_list.xlsx
```

#### Output (sensor_list_defines.h)
```c
/* Generated from sensor_list.xlsx */
/* Date: 2025-01-17T10:30:00Z */

#ifndef SENSOR_LIST_DEFINES_H
#define SENSOR_LIST_DEFINES_H

#define MPGE                     509
#define TRIP_START_TIME          510
#define TRIP_END_TIME            511
#define TRIP_IDLE_TIME           512

#endif /* SENSOR_LIST_DEFINES_H */
```

### Tire Sensor Creation

#### Data File Format (tire_sensors_data.txt)
```
A1_LO_PRESSURE, Tire A1 Left Outer Pressure, Pa
A1_LO_TEMPERATURE, Tire A1 Left Outer Temperature, °C
A1_LO_LOAD, Tire A1 Left Outer Load, kg
```

#### Command
```bash
python3 create_tire_sensors.py -u user@example.com -f tire_sensors_data.txt --start-id 200 --end-id 500
```

#### Generated Sensors
- Creates sensors with appropriate ranges for each metric type
- Assigns unique IDs in specified range
- Links to tire monitoring product automatically

### CAN Traffic Analysis

#### Filter by Message ID
```bash
# Extract all messages with CAN ID 0x18FF4DF3
python3 filter_can.py -i vehicle_can.log -o engine_data.log --id 0x18FF4DF3
```

#### Time-Based Filtering
```bash
# Extract 1-hour window of CAN traffic
python3 filter_can.py -i full_log.can -o hour_sample.can --start 1736899200000 --end 1736902800000
```

#### Statistical Analysis
```bash
# Generate traffic statistics
python3 filter_can.py -i can_traffic.log --stats-only
```

## API Integration

### Common Endpoints
All tools use these authentication patterns:
- **Development API**: `https://api-dev.imatrixsys.com/api/v1`
- **Production API**: `https://api.imatrixsys.com/api/v1`
- **Authentication**: `POST /login`

### File Upload Process
1. **Validation**: Check file type, size, and format
2. **Authentication**: Login to iMatrix API
3. **Upload**: POST file as multipart data
4. **Registry**: Update local tracking database
5. **Confirmation**: Return URL and metadata

## Troubleshooting

### Common Issues

#### Excel Processing Errors
- **File not found**: Check Excel file path and name
- **Permission denied**: Ensure file is not open in Excel
- **Format issues**: Use .xlsx format, not .xls
- **Missing columns**: Ensure ID and Name columns exist

#### Image Upload Problems
- **File too large**: Resize or compress images
- **Unsupported format**: Convert to PNG, JPG, or SVG
- **Upload timeout**: Check network connection
- **API quota**: May have upload limits per hour

#### CAN Filtering Issues
- **Invalid format**: Check input file format
- **Memory issues**: Process large files in chunks
- **Filter syntax**: Verify filter expressions are correct

### Debug Mode

#### Verbose Output
```bash
# Enable detailed logging
python3 upload_image.py -u user@example.com -f image.png --verbose
```

#### Validation Only
```bash
# Test file without uploading
python3 upload_image.py -u user@example.com -f image.png --validate-only
```

## Security Considerations

### File Safety
- **Scan uploads**: Ensure images are safe and appropriate
- **Size limits**: Prevent excessive storage usage
- **Type validation**: Only allow approved image formats
- **Content review**: Check uploaded content appropriateness

### API Security
- **Credentials**: Never commit passwords to scripts
- **Rate limiting**: Add delays between bulk uploads
- **Production use**: Enable SSL verification for production
- **Access control**: Verify upload permissions

## Workflow Integration

### Complete Asset Pipeline
1. **Prepare**: Optimize images for web usage
2. **Upload**: Use `upload_image.py` to get URLs
3. **Register**: Track uploads in registry
4. **Configure**: Use URLs in sensor definitions
5. **Deploy**: Update devices with new assets

### Development Workflow
1. **Convert**: Use `convert_sensor_list.py` for C integration
2. **Create**: Use `create_tire_sensors.py` for bulk sensors
3. **Upload**: Use `upload_image.py` for visual assets
4. **Link**: Use [link_sensor.py](link_sensor/) for associations
5. **Test**: Use [get_sensor_data.py](get_sensor_data/) for verification

## Performance Optimization

### Batch Processing
- **Sequential uploads**: Add delays to avoid rate limiting
- **Error recovery**: Retry failed uploads automatically
- **Progress tracking**: Monitor large batch operations
- **Memory management**: Process large files efficiently

### Image Optimization
- **Compression**: Reduce file sizes before upload
- **Format selection**: Choose optimal format for content type
- **Dimension limits**: Resize to appropriate dimensions
- **Metadata removal**: Strip EXIF data to reduce size

## Related Tools

### Prerequisite Tools
- **Image editing software**: For preparing optimized images
- **Excel/LibreOffice**: For creating sensor definition spreadsheets

### Integration Tools
- **[upload_internal_sensor.py](upload_internal/)**: Use uploaded image URLs
- **[link_sensor.py](link_sensor/)**: Associate sensors with products
- **[get_sensor_data.py](get_sensor_data/)**: Test configured sensors

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-17 | Initial documentation |
|  |  | - Complete tool documentation |
|  |  | - Usage examples for all scripts |
|  |  | - Integration workflow guides |
|  |  | - Troubleshooting sections |

---

*Part of the iMatrix Tools Suite - See [main README](README.md) for complete tool overview*