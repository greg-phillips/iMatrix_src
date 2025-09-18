#!/bin/bash
# -*- coding: utf-8 -*-
"""
link_hm_wrecker_sensors.sh
Links all Horizon Motors wrecker predefined sensors to a product in the iMatrix API.

This script reads the sensor definitions from hm_wrecker_config.c and uses
link_sensor.py to upload each sensor mapping to the iMatrix API.

Usage:
    ./link_hm_wrecker_sensors.sh <product_id>

Example:
    ./link_hm_wrecker_sensors.sh 1235419592
"""

# Check if product ID is provided
if [ $# -eq 0 ]; then
    echo "Error: Product ID required"
    echo "Usage: $0 <product_id>"
    exit 1
fi

# Configuration
PRODUCT_ID="$1"
USERNAME="superadmin@imatrixsys.com"
PASSWORD="passw0rd123"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINK_SENSOR_PY="$SCRIPT_DIR/link_sensor.py"

# Check if link_sensor.py exists
if [ ! -f "$LINK_SENSOR_PY" ]; then
    echo "Error: link_sensor.py not found at $LINK_SENSOR_PY"
    exit 1
fi

# Define the sensor mappings based on hm_wrecker_config.c and internal_sensors_def.h
# Format: "sensor_id:sensor_name"
declare -a HM_WRECKER_SENSORS=(
    "2:GPS_LATITUDE"
    "3:GPS_LONGITUDE"
    "4:GPS_ALTITUDE"
    "19:WIFI_RF_CHANNEL"
    "20:WIFI_RF_RSSI"
    "21:WIFI_RF_NOISE"
    "25:BATTERY_LEVEL"
    "26:SOFTWARE_VERSION"
    "28:BOOT_COUNT"
    "29:4G_RF_RSSI"
    "34:4G_CARRIER"
    "36:IMEI"
    "37:SIM_CARD_STATE"
    "38:SIM_CARD_IMSI"
    "39:SIM_CARD_ICCID"
    "40:4G_NETWORK_TYPE"
    "41:GEOFENCE_ENTER"
    "117:GEOFENCE_EXIT"
    "118:GEOFENCE_ENTER_BUFFER"
    "119:GEOFENCE_EXIT_BUFFER"
    "120:GEOFENCE_IN"
    "42:HOST_CONTROLLER"
    "43:4G_BER"
    "142:VEHICLE_SPEED"
    "48:DIRECTION"
    "49:IDLE_STATE"
    "50:VEHICLE_STOPPED"
    "51:HARD_BRAKE"
    "52:HARD_ACCELERATION"
    "53:HARD_TURN"
    "54:HARD_BUMP"
    "55:HARD_POTHOLE"
    "116:HARD_IMPACT"
    "63:DAILY_HOURS_OF_OPERATION"
    "64:ODOMETER"
    "93:IGNITION_STATUS"
    "144:COMM_LINK_TYPE"
    "145:CANBUS_STATUS"
    "122:CAN_0_SPEED"
    "146:CAN_1_SPEED"
    "123:BATTERY_VOLTAGE"
    "124:BATTERY_CURRENT"
    "143:POWER_USED"
)

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "HM Wrecker Sensor Linking Script"
echo "=========================================="
echo "Product ID: $PRODUCT_ID"
echo "Username: $USERNAME"
echo "Total sensors to link: ${#HM_WRECKER_SENSORS[@]}"
echo "=========================================="
echo ""

# Counter variables
SUCCESS_COUNT=0
FAIL_COUNT=0
ALREADY_LINKED_COUNT=0

# Loop through each sensor and link it
for sensor_entry in "${HM_WRECKER_SENSORS[@]}"; do
    # Split the entry into sensor_id and sensor_name
    IFS=':' read -r sensor_id sensor_name <<< "$sensor_entry"
    
    echo -n "Linking sensor $sensor_id ($sensor_name)... "
    
    # Run the link_sensor.py script and capture output
    output=$(python3 "$LINK_SENSOR_PY" \
        -u "$USERNAME" \
        -p "$PASSWORD" \
        -pid "$PRODUCT_ID" \
        -sid "$sensor_id" 2>&1)
    
    exit_code=$?
    
    # Check if the command was successful
    if [ $exit_code -eq 0 ]; then
        # Check if it was already linked
        if echo "$output" | grep -q "already linked"; then
            echo -e "${YELLOW}ALREADY LINKED${NC}"
            ((ALREADY_LINKED_COUNT++))
        else
            echo -e "${GREEN}SUCCESS${NC}"
            ((SUCCESS_COUNT++))
        fi
    else
        echo -e "${RED}FAILED${NC}"
        echo "  Error: $output"
        ((FAIL_COUNT++))
    fi
    
    # Small delay to avoid overwhelming the API
    sleep 0.5
done

echo ""
echo "=========================================="
echo "Summary:"
echo -e "  Newly Linked: ${GREEN}$SUCCESS_COUNT${NC}"
echo -e "  Already Linked: ${YELLOW}$ALREADY_LINKED_COUNT${NC}"
echo -e "  Failed: ${RED}$FAIL_COUNT${NC}"
echo -e "  Total Processed: $((SUCCESS_COUNT + ALREADY_LINKED_COUNT + FAIL_COUNT))"
echo "=========================================="

# Exit with error code if any failures
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}Some sensors failed to link. Please check the errors above.${NC}"
    exit 1
else
    echo -e "${GREEN}All sensors processed successfully!${NC}"
    exit 0
fi