# iMatrix Tools Directory

**Version:** 1.0
**Date:** January 17, 2025
**Purpose:** Comprehensive toolkit for iMatrix Cloud API integration and data management

## Overview

This directory contains a complete suite of tools for working with the iMatrix Cloud platform, covering data management, device configuration, development utilities, and automation scripts. All tools are designed to work with the iMatrix API and provide both interactive and automated workflows.

## Tool Categories

### 📊 Data Management Tools
Tools for downloading, uploading, and processing sensor data and location information.

| Tool | Purpose | Interactive | Batch |
|------|---------|-------------|-------|
| [get_sensor_data.py](get_sensor_data/) | Download sensor data with device discovery | ✅ | ✅ |
| [get_loc.py](get_loc./) | Download GPS data and convert to GeoJSON | ❌ | ✅ |
| [upload_tsd.py](upload_tsd/) | Upload time series data from CSV files | ❌ | ✅ |
| [upload_sine_wave.py](upload_tsd/) | Generate and upload test sine wave data | ❌ | ✅ |

### 🔗 Configuration Tools
Tools for managing sensor definitions, product linking, and system configuration.

| Tool | Purpose | Interactive | Batch |
|------|---------|-------------|-------|
| [link_sensor.py](link_sensor/) | Link individual sensors to products | ❌ | ✅ |
| [upload_internal_sensor.py](upload_internal/) | Upload internal sensor definitions | ❌ | ✅ |
| [convert_sensor_list.py](.) | Convert Excel sensor lists to C headers | ❌ | ✅ |
| [create_tire_sensors.py](.) | Create tire monitoring sensor definitions | ❌ | ✅ |

### 🧪 Development Tools
Tools for testing, analysis, and development workflows.

| Tool | Purpose | Interactive | Batch |
|------|---------|-------------|-------|
| [filter_can.py](.) | CAN traffic filtering and analysis | ❌ | ✅ |

### 🖼️ Media Tools
Tools for managing images and media assets.

| Tool | Purpose | Interactive | Batch |
|------|---------|-------------|-------|
| [upload_image.py](upload_image/) | Upload images with registry management | ❌ | ✅ |

### ⚙️ Automation Scripts
Shell scripts for batch processing and workflow automation.

| Tool | Purpose | Target |
|------|---------|--------|
| [link_sensors.sh](link_sensor/) | Batch link sensors 508-537 to products | Energy sensors |
| [link_hm_wrecker_sensors.sh](.) | Link HM Wrecker specific sensors | HM Truck platform |
| [upload_list.sh](upload_internal/) | Batch upload internal sensor definitions | System setup |

## Quick Start Guide

### 1. First Time Setup

**Install Dependencies**
```bash
python3 -m pip install requests urllib3 pandas openpyxl
```

**Get API Credentials**
- Username: Your iMatrix Cloud email
- Password: Your iMatrix Cloud password
- API Access: Ensure your account has API permissions

### 2. Common Workflows

#### Explore Your Data (No Prior Knowledge Needed)
```bash
# See all your devices and download sensor data
cd tools/get_sensor_data
python3 get_sensor_data.py -u your-email@example.com
```

#### Download Location History
```bash
# Get GPS track as GeoJSON for Google Maps
cd tools/get_loc.
python3 get_loc.py -s 1234567890 -ts 1736899200000 -te 1736985600000 -u your-email@example.com
```

#### Upload Sensor Data
```bash
# Upload CSV time series data
cd tools/upload_tsd
python3 upload_tsd.py -U your-email@example.com -G 1234567890 -C 1234567890 -D data.csv
```

### 3. Configuration Tasks

#### Link Sensors to Products
```bash
# Link individual sensor
cd tools/link_sensor
python3 link_sensor.py -u your-email@example.com -pid 1235419592 -sid 509

# Batch link energy sensors (508-537)
cd tools/link_sensor
./link_sensors.sh
```

#### Upload Sensor Definitions
```bash
# Upload single sensor definition
cd tools/upload_internal
python3 upload_internal_sensor.py -u your-email@example.com -f sensor_509.json

# Batch upload all sensors
cd tools/upload_internal
./upload_list.sh
```

## Tool Selection Guide

### I want to...

**📈 Download sensor data from my devices**
→ Use [get_sensor_data.py](get_sensor_data/) - Interactive device and sensor discovery

**🗺️ Get GPS location history**
→ Use [get_loc.py](get_loc./) - Downloads lat/lon and creates GeoJSON

**📤 Upload time series data**
→ Use [upload_tsd.py](upload_tsd/) - CSV to iMatrix Cloud with validation

**🔗 Configure sensor-to-product links**
→ Use [link_sensor.py](link_sensor/) - Individual or batch sensor linking

**🛠️ Create new sensor definitions**
→ Use [upload_internal_sensor.py](upload_internal/) - JSON sensor definitions

**🖼️ Upload device images or icons**
→ Use [upload_image.py](upload_image/) - Image upload with registry

**🔧 Convert Excel sensor lists**
→ Use [convert_sensor_list.py](.) - Excel to C header conversion

**🚛 Set up HM Truck sensors**
→ Use [link_hm_wrecker_sensors.sh](.) - Automated HM Wrecker setup

**🧪 Generate test data**
→ Use [upload_sine_wave.py](upload_tsd/) - Sine wave test data

**🔍 Analyze CAN traffic**
→ Use [filter_can.py](.) - CAN message filtering and analysis

## Authentication

All tools use the same authentication pattern:
- **Username**: `-u your-email@example.com`
- **Password**: `-p password` (optional, secure prompt if omitted)
- **API Environment**: Development (default) or Production (`--pro` flag)

## Common Data Formats

### Input Formats
- **CSV Files**: Time series data, sensor lists
- **Excel Files**: Sensor definitions, configuration data
- **JSON Files**: Sensor definitions, API responses
- **Binary Files**: Images, icons

### Output Formats
- **JSON**: Structured data with metadata and statistics
- **CSV**: Tabular data with headers and comments
- **GeoJSON**: Location data for mapping applications
- **C Headers**: Sensor definitions for embedded systems

## Directory Structure

```
tools/
├── README.md                       # This file - master overview
├── convert_sensor_list.py          # Excel to C header converter
├── create_tire_sensors.py          # Tire sensor creation tool
├── filter_can.py                   # CAN traffic analysis
├── link_hm_wrecker_sensors.sh      # HM Wrecker automation
│
├── get_loc./                       # Location data tools
│   ├── README.md
│   └── get_loc.py
│
├── get_sensor_data/                # Sensor data management
│   ├── README.md
│   ├── get_sensor_data.py
│   └── [documentation files]
│
├── link_sensor/                    # Sensor linking tools
│   ├── README.md
│   ├── link_sensor.py
│   └── link_sensors.sh
│
├── upload_image/                   # Image management
│   ├── README.md
│   └── upload_image.py
│
├── upload_internal/                # Internal sensor management
│   ├── README.md
│   ├── upload_internal_sensor.py
│   └── upload_list.sh
│
└── upload_tsd/                     # Time series data tools
    ├── README.md
    ├── upload_tsd.py
    └── upload_sine_wave.py
```

## Security Notes

### API Access
- All tools use secure HTTPS connections
- SSL warnings disabled for development (should be enabled in production)
- Credentials can be provided via command-line or secure prompt
- No credentials are stored or logged

### Best Practices
- Use environment variables for credentials in automation
- Test with development API before production
- Validate input data before upload
- Monitor API rate limits for batch operations

## Support and Documentation

### Getting Help
- Each subdirectory has detailed README with examples
- Use `-h` flag with any Python script for help
- Verbose mode (`-v`) available for debugging
- Error messages include suggestions for resolution

### Related Documentation
- [Fleet-Connect-1 Energy Reports](../docs/ENERGY_REPORTS_EXAMPLES.md)
- [CAN Bus Integration Guide](../docs/FLEET_CONNECT_1_REVIEW.md)
- [API Documentation](https://api.imatrixsys.com/api-docs/swagger/)

### Contributing
- Follow existing code patterns when modifying tools
- Add comprehensive docstrings to new functions
- Include usage examples in documentation
- Test with both development and production APIs

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-17 | Initial comprehensive documentation |
|  |  | - Added master tool overview |
|  |  | - Categorized all tools by function |
|  |  | - Created quick start guide |
|  |  | - Added tool selection guide |

---

*For detailed documentation on specific tools, see the README files in each subdirectory.*