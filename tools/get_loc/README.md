# Location Data Tools

## Overview

The `get_loc` directory contains tools for downloading and processing GPS location data from iMatrix devices. The primary tool converts latitude/longitude sensor data into GeoJSON format suitable for mapping applications like Google Maps.

## Tools

### get_loc.py

**Purpose:** Download GPS location history and convert to GeoJSON format

**Features:**
- Downloads latitude (sensor ID 2) and longitude (sensor ID 3) data
- Matches timestamps between lat/lon data points
- Outputs GeoJSON format compatible with mapping applications
- Secure authentication with password prompt
- Error handling for missing or mismatched data

## Installation

### Prerequisites
- Python 3.6 or higher
- pip package manager

### Dependencies
```bash
python3 -m pip install requests urllib3
```

## Usage

### Basic Command Structure
```bash
python3 get_loc.py -s <serial> -ts <start_ms> -te <end_ms> -u <email>
```

### Required Arguments
- `-s, --serial`: Device serial number (32-bit integer)
- `-ts, --start`: Start time in epoch milliseconds
- `-te, --end`: End time in epoch milliseconds
- `-u, --username`: iMatrix Cloud username (email)

### Optional Arguments
- `-p, --password`: Password (secure prompt if omitted)

## Examples

### Basic Location Download
```bash
python3 get_loc.py -s 1234567890 -ts 1736899200000 -te 1736985600000 -u user@example.com
```

### With Password on Command Line
```bash
python3 get_loc.py -s 1234567890 -ts 1736899200000 -te 1736985600000 -u user@example.com -p mypassword
```

### Download Week of Location Data
```bash
# January 15-22, 2025
python3 get_loc.py -s 1234567890 -ts 1736899200000 -te 1737504000000 -u user@example.com
```

## Output Format

### GeoJSON File
The tool creates a GeoJSON file named `{serial}-{start}.geojson` containing:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.4194, 37.7749]
      },
      "properties": {
        "timestamp": 1736899200000
      }
    }
  ]
}
```

### File Naming
- **Format**: `{serial}-{start_timestamp}.geojson`
- **Example**: `1234567890-1736899200000.geojson`

## Integration with Mapping Services

### Google Maps
1. Upload the GeoJSON file to Google My Maps
2. The file will display as a track with timestamps
3. Each point shows the timestamp when clicked

### Other Mapping Applications
- **QGIS**: Direct GeoJSON import
- **ArcGIS**: Supported format
- **Leaflet**: JavaScript mapping library
- **OpenLayers**: Web mapping framework

## API Integration

### Endpoints Used
- **Authentication**: `POST /login`
- **Latitude Data**: `GET /things/{serial}/sensor/2/history/{start}/{end}`
- **Longitude Data**: `GET /things/{serial}/sensor/3/history/{start}/{end}`

### Sensor IDs
- **Sensor 2**: Latitude (degrees)
- **Sensor 3**: Longitude (degrees)

## Timestamp Conversion

### Epoch Milliseconds
The tool requires timestamps in epoch milliseconds. Convert using:

**Python:**
```python
from datetime import datetime
dt = datetime(2025, 1, 15, 0, 0, 0)
epoch_ms = int(dt.timestamp() * 1000)
```

**Bash:**
```bash
date -d "2025-01-15 00:00:00" +%s000
```

**Online Tools:**
- [epochconverter.com](https://www.epochconverter.com/)

## Troubleshooting

### Common Issues

#### No Location Data
- Verify the device has GPS capability
- Check if location tracking is enabled
- Ensure the device was moving during the time period

#### Mismatched Timestamps
- Some lat/lon points may not have exact timestamp matches
- The tool only outputs points where both lat and lon exist
- This is normal for devices with different sampling rates

#### Empty GeoJSON
- Check that the time range contains GPS data
- Verify the device was powered on and connected
- Try a longer time range

### Error Messages

#### Authentication Failed
- Check username and password
- Verify API access permissions

#### Device Not Found
- Verify the serial number is correct
- Check device registration in iMatrix Cloud

#### API Errors
- Check internet connection
- Verify API server availability
- Try with verbose mode for detailed errors

## Related Tools

### Complementary Tools
- **[get_sensor_data.py](../get_sensor_data/)**: Download any sensor data with device discovery
- **[upload_tsd.py](../upload_tsd/)**: Upload location data to iMatrix Cloud
- **[filter_can.py](../filter_can.py)**: Analyze GPS data from CAN bus

### Workflow Integration
1. **Discovery**: Use `get_sensor_data.py` to explore available sensors
2. **Location Download**: Use `get_loc.py` for GPS track data
3. **Analysis**: Import GeoJSON into mapping applications
4. **Correlation**: Combine with other sensor data for analysis

## Technical Details

### Data Processing
1. **Download**: Fetches lat/lon data separately
2. **Matching**: Aligns timestamps between sensors
3. **Filtering**: Only includes points with both coordinates
4. **Formatting**: Converts to standard GeoJSON structure

### Performance
- **Memory efficient**: Processes data in chunks
- **Network optimized**: Concurrent lat/lon downloads
- **Error resilient**: Continues processing with partial data

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-17 | Initial documentation |
|  |  | - Comprehensive usage guide |
|  |  | - Integration examples |
|  |  | - Troubleshooting section |

---

*Part of the iMatrix Tools Suite - See [main README](../README.md) for complete tool overview*