# Sensor Linking Tools

This directory contains tools for linking predefined sensors to products in the iMatrix API.

## Tools

### link_sensor.py
A Python script that links a single sensor to a product using the iMatrix API.

**Usage:**
```bash
python3 link_sensor.py -u <username> -pid <product_id> -sid <sensor_id> [-p <password>]
```

**Example:**
```bash
python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 2
```

**Arguments:**
- `-u, --username`: iMatrix Cloud username (email) - Required
- `-p, --password`: iMatrix Cloud password (optional, prompts if not provided)
- `-pid, --product-id`: Product ID to link - Required
- `-sid, --sensor-id`: Sensor ID to link - Required

### link_hm_wrecker_sensors.sh
A bash script that links all Horizon Motors wrecker predefined sensors to a product.

**Usage:**
```bash
./link_hm_wrecker_sensors.sh <product_id>
```

**Example:**
```bash
./link_hm_wrecker_sensors.sh 1235419592
```

This script will:
1. Link all 41 predefined sensors from the HM wrecker configuration
2. Use the hardcoded credentials (superadmin@imatrixsys.com / passw0rd123)
3. Show progress for each sensor
4. Provide a summary at the end

## Sensor Mappings

The HM wrecker configuration includes the following sensors:

### GPS and Location Sensors
- 2: GPS_LATITUDE
- 3: GPS_LONGITUDE
- 4: GPS_ALTITUDE
- 48: DIRECTION

### Network and Connectivity
- 19: WIFI_RF_CHANNEL
- 20: WIFI_RF_RSSI
- 21: WIFI_RF_NOISE
- 29: 4G_RF_RSSI
- 34: 4G_CARRIER
- 36: IMEI
- 37: SIM_CARD_STATE
- 38: SIM_CARD_IMSI
- 39: SIM_CARD_ICCID
- 40: 4G_NETWORK_TYPE
- 43: 4G_BER
- 144: COMM_LINK_TYPE

### System and Device
- 25: BATTERY_LEVEL
- 26: SOFTWARE_VERSION
- 28: BOOT_COUNT
- 42: HOST_CONTROLLER

### Vehicle Dynamics
- 142: VEHICLE_SPEED
- 49: IDLE_STATE
- 50: VEHICLE_STOPPED
- 51: HARD_BRAKE
- 52: HARD_ACCELERATION
- 53: HARD_TURN
- 54: HARD_BUMP
- 55: HARD_POTHOLE
- 116: HARD_IMPACT

### Electric Vehicle Specific
- 63: DAILY_HOURS_OF_OPERATION
- 64: ODOMETER
- 93: IGNITION_STATUS
- 123: BATTERY_VOLTAGE
- 124: BATTERY_CURRENT
- 143: POWER_USED

### CAN Bus
- 145: CANBUS_STATUS
- 122: CAN_0_SPEED
- 146: CAN_1_SPEED

### Geofencing
- 41: GEOFENCE_ENTER
- 117: GEOFENCE_EXIT
- 118: GEOFENCE_ENTER_BUFFER
- 119: GEOFENCE_EXIT_BUFFER
- 120: GEOFENCE_IN

## API Details

The scripts use the following iMatrix API endpoint:
- **URL**: https://api-dev.imatrixsys.com/api/v1/sensors/predefined/link
- **Method**: PUT
- **Authentication**: Token-based (obtained via login)

## Requirements

- Python 3.x
- requests library (`pip install requests`)
- urllib3 library (`pip install urllib3`)
- Bash shell (for the batch script)

## Notes

1. The scripts disable SSL certificate verification for development use
2. A small delay (0.5s) is added between API calls to avoid overwhelming the server
3. The batch script provides colored output for easy status identification
4. All sensor IDs are based on the definitions in `internal_sensors_def.h`