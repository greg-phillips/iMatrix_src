# Sensor Linking Tools

## Overview

The `link_sensor` directory contains tools for linking predefined sensors to iMatrix products. These tools are essential for configuring devices to use specific sensor definitions and enabling proper data collection.

## Tools

### link_sensor.py

**Purpose:** Link individual predefined sensors to iMatrix products

**Features:**
- Links sensor definitions to specific product IDs
- Validates sensor and product IDs before linking
- Secure authentication with password prompt
- Error handling for invalid links and API failures
- Confirmation of successful linking operations

### link_sensors.sh

**Purpose:** Batch link energy sensors (IDs 508-537) to a specific product

**Features:**
- Automated batch linking for sensor range 508-537
- Uses hardcoded credentials and product ID (modify as needed)
- Sequential processing with status updates
- Designed for energy sensor deployment automation

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

### Individual Sensor Linking

#### Basic Command Structure
```bash
python3 link_sensor.py -u <email> -pid <product_id> -sid <sensor_id>
```

#### Required Arguments
- `-u, --username`: iMatrix Cloud username (email)
- `-pid, --product-id`: Target product ID (integer)
- `-sid, --sensor-id`: Sensor ID to link (integer)

#### Optional Arguments
- `-p, --password`: Password (secure prompt if omitted)

### Batch Sensor Linking

#### Run the Batch Script
```bash
./link_sensors.sh
```

**Note:** Edit the script to update credentials and product ID before running.

## Examples

### Link Single Sensor
```bash
# Link MPGe sensor (509) to a product
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 509
```

### Link Energy Sensors to Product
```bash
# Link trip start time sensor
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 510

# Link regenerative power sensor
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 531
```

### Batch Link All Energy Sensors
```bash
# Edit link_sensors.sh first to update credentials/product ID
./link_sensors.sh
```

### Link Common Sensors
```bash
# Link latitude sensor
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 2

# Link longitude sensor
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 3

# Link battery state of charge
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 503
```

## API Integration

### Endpoints Used
- **Authentication**: `POST /login`
- **Sensor Linking**: `POST /sensors/predefined/link`

### Request Format
```json
{
  "productId": 1235419592,
  "sensorId": 509
}
```

### Response Handling
- **Success**: 200 OK with confirmation
- **Duplicate**: 409 if link already exists
- **Not Found**: 404 if sensor or product doesn't exist
- **Access Denied**: 403 if insufficient permissions

## Sensor Categories

### Energy and Trip Sensors (509-537)
These sensors support the Fleet-Connect-1 energy management system:

| Sensor ID | Name | Purpose |
|-----------|------|---------|
| 509 | MPGe | Fuel economy calculation |
| 510-511 | Trip Start/End Time | Trip duration tracking |
| 512 | Trip Idle Time | Efficiency analysis |
| 513-515 | Consumption Metrics | Energy efficiency |
| 518 | Energy Recovered | Regeneration tracking |
| 520-521 | Charge Rates | Charging performance |
| 524-526 | Driving Behavior | Safety metrics |
| 531 | Peak Regenerative Power | Performance tracking |

### System Sensors (500-508)
Core system sensors for basic functionality:

| Sensor ID | Name | Purpose |
|-----------|------|---------|
| 500 | Cumulative Throughput | Data usage tracking |
| 501 | Charge Rate | Charging status |
| 502 | Estimated Range | Range calculation |
| 503 | Battery State of Health | Battery monitoring |
| 504 | Trip Distance | Distance tracking |
| 505 | Charging Status | Charge state |
| 506 | Trip Meter | Trip management |

### Location Sensors (2-3)
Basic location tracking:

| Sensor ID | Name | Units |
|-----------|------|-------|
| 2 | Latitude | degrees |
| 3 | Longitude | degrees |

## Batch Processing

### Custom Batch Scripts

Create custom batch linking scripts for specific product deployments:

```bash
#!/bin/bash

USERNAME="user@example.com"
PRODUCT_ID="1235419592"

# Energy sensors for electric vehicles
ENERGY_SENSORS=(509 513 514 518 520 521 531)

echo "Linking energy sensors to product $PRODUCT_ID..."

for SENSOR_ID in "${ENERGY_SENSORS[@]}"; do
    echo "Linking sensor $SENSOR_ID..."
    python3 link_sensor.py -u "$USERNAME" -pid "$PRODUCT_ID" -sid "$SENSOR_ID"
    sleep 1  # Avoid rate limiting
done

echo "Energy sensor linking complete!"
```

### Verification Script

Verify sensor links are working:

```bash
#!/bin/bash

# Use get_sensor_data.py to verify linked sensors
python3 ../get_sensor_data/get_sensor_data.py -s 1234567890 -u user@example.com --list-sensors
```

## Troubleshooting

### Common Issues

#### Product ID Not Found
- Verify the product ID exists in iMatrix Cloud
- Check that you have access to the product
- Ensure the product is published and active

#### Sensor ID Not Found
- Verify the sensor ID exists (use upload_internal_sensor.py if needed)
- Check sensor definitions in iMatrix Cloud
- Ensure sensor is published and available

#### Link Already Exists
- The sensor is already linked to the product
- This is not an error - the link is functional
- Use list commands to verify existing links

#### Access Denied
- Check account permissions for product modification
- Verify you're the product owner or have appropriate rights
- Contact administrator for permission issues

### Debug Mode

For detailed error information:
```bash
# Run with verbose Python output
python3 -v link_sensor.py -u user@example.com -pid 1235419592 -sid 509
```

## Security Considerations

### Credentials
- Never commit passwords to version control
- Use environment variables for automation:
  ```bash
  export IMATRIX_USERNAME="user@example.com"
  export IMATRIX_PASSWORD="securepassword"
  ```

### API Access
- Links affect device functionality
- Test with development API first
- Verify links before deploying to production devices

## Related Tools

### Prerequisite Tools
- **[upload_internal_sensor.py](../upload_internal/)**: Create sensor definitions before linking
- **[get_sensor_data.py](../get_sensor_data/)**: Verify sensors work after linking

### Workflow Integration
1. **Create Sensors**: Use `upload_internal_sensor.py` to define new sensors
2. **Link Sensors**: Use `link_sensor.py` to associate with products
3. **Verify Links**: Use `get_sensor_data.py` to test sensor access
4. **Deploy**: Update device firmware with new sensor configurations

## Advanced Usage

### Product-Specific Configurations

#### Fleet-Connect-1 Energy Setup
```bash
# Core energy sensors
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 509  # MPGe
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 518  # Energy Recovered
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 531  # Peak Regen Power
```

#### GPS Tracking Setup
```bash
# Location sensors
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 2    # Latitude
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 3    # Longitude
```

#### Battery Monitoring Setup
```bash
# Battery sensors
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 501  # Charge Rate
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 503  # State of Health
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 505  # Charging Status
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-17 | Initial documentation |
|  |  | - Comprehensive usage guide |
|  |  | - Sensor category reference |
|  |  | - Batch processing examples |
|  |  | - Troubleshooting guide |

---

*Part of the iMatrix Tools Suite - See [main README](../README.md) for complete tool overview*