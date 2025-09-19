# New Energy and Trip Sensors Implementation

**Date:** January 17, 2025
**Task:** Add 29 new sensors for energy management and trip metrics

## Summary

Successfully created JSON sensor definition files and updated the iMatrix internal sensor definitions to support enhanced energy reporting, trip metrics, and diagnostics.

## Files Created

### JSON Sensor Definition Files (29 files)

All files created in `/home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/tools/`:

| File | ID | Sensor Name | Units |
|------|-----|-------------|-------|
| sensor_509.json | 509 | MPGe | mpge |
| sensor_510.json | 510 | Trip UTC Start Time | Time |
| sensor_511.json | 511 | Trip UTC End Time | Time |
| sensor_512.json | 512 | Trip idle time | Seconds |
| sensor_513.json | 513 | Trip Wh/km | Wh/km |
| sensor_514.json | 514 | Trip MPGe | mpge |
| sensor_515.json | 515 | Trip l/100km | l/100km |
| sensor_516.json | 516 | Trip CO2 Emissions | kg |
| sensor_517.json | 517 | Trip Power | kWh |
| sensor_518.json | 518 | Trip Energy Recovered | kWH |
| sensor_519.json | 519 | Trip Charge | kWH |
| sensor_520.json | 520 | Trip Average Charge Rate | kW |
| sensor_521.json | 521 | Trip Peak Charge Rate | kW |
| sensor_522.json | 522 | Trip Average Speed | km |
| sensor_523.json | 523 | Trip Maximum Speed | km |
| sensor_524.json | 524 | Trip number hard accelerations | Qty |
| sensor_525.json | 525 | Trip number hard braking | Qty |
| sensor_526.json | 526 | Trip number hard turns | Qty |
| sensor_527.json | 527 | Maximum deceleration | g |
| sensor_528.json | 528 | Trip fault Codes | Code |
| sensor_529.json | 529 | Peak power | kW |
| sensor_530.json | 530 | Range gained per minute | km/min |
| sensor_531.json | 531 | Peak Regerative Power | kW |
| sensor_532.json | 532 | Peak Brake Pedal | % |
| sensor_533.json | 533 | Peak Accel Pedal | % |
| sensor_534.json | 534 | DTC OBD2 Codes | Code |
| sensor_535.json | 535 | DTC J1939 Codes | Code |
| sensor_536.json | 536 | DTC HM Truck Codes | Code |
| sensor_537.json | 537 | DTC Echassie Codes | Code |

## Files Modified

### internal_sensors_def.h

Updated `/home/greg/iMatrix/iMatrix_Client/iMatrix/internal_sensors_def.h` with 29 new X-macro entries:

```c
X(MPGE,509,"MPGe")
X(TRIP_END_START_TIME,510,"Trip UTC Start Time")
X(TRIP_END_TIME,511,"Trip UTC End Time")
X(TRIP_IDLE_TIME,512,"Trip idle time")
X(TRIP_KW_KM,513,"Trip Wh/km")
X(TRIP_MPGE,514,"Trip MPGe")
X(TRIP_L_100KW,515,"Trip l/100km")
X(TRIP_CO2,516,"Trip CO2 Emissions")
X(TRIP_POWER,517,"Trip Power")
X(TRIP_ENERGY_RECOVERED_KWHR,518,"Trip Energy Recovered")
X(TRIP_CHARGE,519,"Trip Charge")
X(TRIP_AVG_CHARGE_RATE,520,"Trip Average Charge Rate")
X(TRIP_PEAK_CHARGE_RATE,521,"Trip Peak Charge Rate")
X(TRIP_SPEED_AVG,522,"Trip Average Speed")
X(TRIP_SPEED_MAX,523,"Trip Maximum Speed")
X(TRIP_NO_HARD_ACCELS,524,"Trip number hard accelerations")
X(TRIP_NO_HARD_BRAKES,525,"Trip number hard braking")
X(TRIP_NO_HARD_TURNS,526,"Trip number hard turns")
X(TRIP_BRAKE_MAX,527,"Maximum deceleration")
X(TRIP_FALT_CODES,528,"Trip fault Codes")
X(PEAK_POWER,529,"Peak power")
X(RANGE_GAINED_PER_MIN,530,"Range gained per minute")
X(PEAK_REGEN,531,"Peak Regerative Power")
X(PEAK_BRAKE_PEDAL,532,"Peak Brake Pedal")
X(PEAK_ACCEL_PEDAL,533,"Peak Accel Pedal")
X(DTC_OBD3,534,"DTC OBD2 Codes")
X(DTC_J1939,535,"DTC J1939 Codes")
X(DTC_HM_TRUCK,536,"DTC HM Truck Codes")
X(DTC_HM_ECHASSIE,537,"DTC Echassie Codes")
```

## Upload Instructions

To upload these sensors to the iMatrix cloud platform:

```bash
cd /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/tools/

# Upload individual sensor
python3 upload_internal_sensor.py -u <username> -f sensor_509.json

# Upload all new sensors (509-537)
for i in {509..537}; do
    echo "Uploading sensor $i..."
    python3 upload_internal_sensor.py -u <username> -f sensor_${i}.json
    sleep 1  # Add delay to avoid rate limiting
done
```

## Sensor Categories

### Energy Efficiency Metrics
- MPGe (509, 514)
- Wh/km (513)
- l/100km (515)
- CO2 Emissions (516)

### Trip Timing and Statistics
- Start/End Time (510, 511)
- Idle Time (512)
- Distance (504 - existing)
- Average/Max Speed (522, 523)

### Power and Charging
- Trip Power (517)
- Peak Power (529)
- Trip Charge (519)
- Average/Peak Charge Rate (520, 521)
- Range gained per minute (530)

### Regeneration
- Energy Recovered (518)
- Peak Regenerative Power (531)

### Driving Behavior
- Hard Accelerations (524)
- Hard Braking (525)
- Hard Turns (526)
- Maximum Deceleration (527)
- Peak Brake/Accel Pedal (532, 533)

### Diagnostics
- Trip Fault Codes (528)
- DTC OBD2 Codes (534)
- DTC J1939 Codes (535)
- DTC HM Truck Codes (536)
- DTC Echassie Codes (537)

## Integration with Energy Reporting

These sensors support the enhanced energy reporting system implemented in:
- `energy_manager.c/h` - 100ms power tracking
- `energy_display.c/h` - Formatted report display
- CLI commands (`e t`, `e r`, `e c`, `e j`)

## Verification

All JSON files have been:
- Created with correct structure matching sensor_508.json template
- Validated as proper JSON format
- Given unique IDs from 509-537
- Assigned appropriate names and units from the specification

The internal_sensors_def.h file has been updated with all 29 new sensor definitions in the correct X-macro format.

## Next Steps

1. Upload sensors to iMatrix cloud using the upload script
2. Update Fleet-Connect-1 code to populate these sensors with actual values
3. Configure thresholds and alerts as needed for each sensor
4. Test sensor data flow from device to cloud platform

## Notes

- All sensors use IMX_NATIVE units type for maximum flexibility
- IMX_FLOAT data type selected for numeric values
- Default values set to 0
- Thresholds and alerts disabled by default (can be configured later)
- Same icon URL used for consistency (can be customized per sensor if needed)