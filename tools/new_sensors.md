Create a plan to create JSON files to be used with the script Fleet-Connect-1/tools/upload_internal_sensor.py
For the format of the file reference the file Fleet-Connect-1/tools/sensor_508.json
Start wiht the next id of 509, increment by 1 for each succesive element.

The format of the list is:
<INTERNAL_NAME>, "<Name>", "<units>"

in the new JSON file use the "<Name>" for the "name" field in the JSON structure
in the new JSON file use the "<units>" for the "units" field in the JSON structure
All other values should be the defaults used in the example.
After creating the files add new entries to the end of the file iMatrix/internal_sensors_def.h
Example of a entry in that file is: X(OUT_OF_RANGE_SENSOR_DATA_VALUE,508,"Out of Range Sensor Data Value")

For each new record use the INTERNAL_NAME for the first entry in the macro defintions. use the id for the second entry and use the "<Name>" for the third entry.


List of required new sensors.

MPGE, "MPGe", "mpge"
TRIP_END_START_TIME, "Trip UTC Start Time", "Time"
TRIP_END_TIME, "Trip UTC End Time", "Time"
TRIP_IDLE_TIME, "Trip idle time", "Seconds"
TRIP_KW_KM, "Trip Wh/km", "Wh/km"
TRIP_MPGE, "Trip MPGe", "mpge"
TRIP_L_100KW, "Trip l/100km", "l/100km"

TRIP_CO2, "Trip CO2 Emissions", "kg"
TRIP_POWER, "Trip Power", "kWh"
TRIP_ENERGY_RECOVERED_KWHR, "Trip Energy Recovered", "kWH"
TRIP_CHARGE, "Trip Charge", "kWH"
TRIP_AVG_CHARGE_RATE, "Trip Average Charge Rate", "kW"
TRIP_PEAK_CHARGE_RATE, "Trip Peak Charge Rate", "kW"
TRIP_SPEED_AVG, "Trip Average Speed", "km"
TRIP_SPEED_MAX, "Trip Maximum Speed", "km"
TRIP_NO_HARD_ACCELS, "Trip number hard accelerations", "Qty"
TRIP_NO_HARD_BRAKES, "Trip number hard braking", "Qty"
TRIP_NO_HARD_TURNS, "Trip number hard turns", "Qty"
TRIP_BRAKE_MAX, "Maximum deceleration", "g"
TRIP_FALT_CODES, "Trip fault Codes", "Code"

PEAK_POWER, "Peak power", "kW"
RANGE_GAINED_PER_MIN, "Range gained per minute", "km/min"
PEAK_REGEN, "Peak Regerative Power", "kW"
PEAK_BRAKE_PEDAL, "Peak Brake Pedal", "%"
PEAK_ACCEL_PEDAL, "Peak Accel Pedal", "%"
DTC_OBD3, "DTC OBD2 Codes", "Code"
DTC_J1939, "DTC J1939 Codes", "Code"
DTC_HM_TRUCK, "DTC HM Truck Codes", "Code"
DTC_HM_ECHASSIE, "DTC Echassie Codes", "Code"
