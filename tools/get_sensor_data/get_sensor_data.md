Create a plan to make a new script to download user sensor data using the iMatrix API.
Use the reference script from tools/get_loc/get_loc.py to understand how to access the iMatrix API
The script should allow the user to enter the following items on the command line
1. Start time
2. End time
3. Device Serial Number
4. Sensor ID
Create the new script in the directory tools/get_sensor_data

API Reference document: https://api.imatrixsys.com/api-docs/swagger/#
If the user only enters the serial number use the api call: GET /products/{id} to get product information.
Example of returned data is:
{
  "id": 1349851161,
  "name": "NEO-1D Temperature Humidity Sensor with Display",
  "platformId": 899907174,
  "platformType": "ble",
  "organizationId": 1583546208,
  "shortName": "NEO-1D",
  "isPublished": true,
  "badge": "imatrix",
  "internalFlashSize": 1048576,
  "externalFlashSize": 0,
  "defaultFavorite1": 251656609,
  "defaultFavorite2": 872052224,
  "defaultFavorite3": null,
  "noControls": 0,
  "noSensors": 7,
  "imageUrl": "https://storage.googleapis.com/imatrix-files-prod/a8a82188-968c-4969-9542-5ebd935cf870.svg",
  "iconUrl": "https://storage.googleapis.com/imatrix-files-prod/6affa7c7-4c43-4b7a-b20d-b32fb59e9d7a.svg",
  "defaultImage": "https://storage.googleapis.com/imatrix-files-prod/6b70d448-a088-48a7-898e-b14893013caa.jpg",
  "controlSensorIds": [
    58108062,
    528597925,
    726966252,
    847839682,
    872052224,
    916775340,
    1719488477
  ],
  "batteryUse": 20,
  "rssiUse": 22,
  "operationalVoltage": {
    "id": 441776386,
    "name": "voltageProfile_3.3",
    "profile": {
      "level1": null,
      "level2": null,
      "level3": null,
      "level4": null,
      "level5": null,
      "level6": null,
      "level7": 3.3
    }
  },
  "sensor": {
    "name": "NEO-1D Temperature Humidity Sensor with Display",
    "productId": 1349851161,
    "platformId": 899907174,
    "iconUrl": "https://storage.googleapis.com/imatrix-files-prod/6affa7c7-4c43-4b7a-b20d-b32fb59e9d7a.svg"
  },
  "externalType": null
}

Then use the API call GET /sensors/{id} get sensor to get each of the details about each sensor. An example of the response to the get set API call is:
{
  "id": 58108062,
  "type": 1,
  "name": "Temperature",
  "units": "Deg. C",
  "unitsType": "IMX_TEMPERATURE",
  "dataType": "IMX_FLOAT",
  "defaultValue": null,
  "productId": 1349851161,
  "platformId": null,
  "states": 0,
  "mode": "scalar",
  "iconUrl": "https://storage.googleapis.com/imatrix-files/33df801b-2d99-433a-a00c-6b70b7269b46-Temperature.svg",
  "thresholdQualificationTime": null,
  "minAdvisoryEnabled": null,
  "minAdvisory": null,
  "minWarningEnabled": null,
  "minWarning": null,
  "minAlarmEnabled": null,
  "minAlarm": null,
  "maxAdvisoryEnabled": null,
  "maxAdvisory": null,
  "maxWarningEnabled": null,
  "maxWarning": null,
  "maxAlarmEnabled": null,
  "maxAlarm": null,
  "maxGraph": 455.35,
  "minGraph": -200,
  "calibrationMode": 0,
  "calibrateValue1": null,
  "calibrateValue2": null,
  "calibrateValue3": null,
  "calibrationRef1": null,
  "calibrationRef2": null,
  "calibrationRef3": null
}

once all the sensors details have been found list the names and let the user select sensor to use. Use the id from the sensor to retrieve the history data for that sensor


if the user does not enter the start or end date prompt the user to enter this data. the format accepted should be mS since 1970 or a date and time in the format: <mm>/<dd>/<yy> <hh>:<mm> 
if the user does not enter a time assume from midnight to midnight.

Add a command line option to list all the devices/things in a users account. Use the API call: GET/things/ to get user things

An example of the returned data is as follows:

{
  "list": [
    {
      "sn": 863095613,
      "name": "1st Floor Micro Gateway",
      "mac": "00:06:8b:01:04:3c",
      "image": "https://storage.googleapis.com/imatrix-files-prod/1e64fba0-7bf0-44f2-a860-b7843465c70b.jpg",
      "organizationId": 298726404,
      "productId": 984993858,
      "groupId": 1082477619,
      "createdAt": 1690828577000,
      "favorite1": 355762848,
      "favorite2": 3974806334,
      "favorite3": 2763270826,
      "isFavorite": false,
      "currentVersion": "1.034.001"
    },
    {
      "sn": 81541896,
      "name": "AGSoil-1",
      "mac": "00:06:8b:01:1b:9d",
      "image": "https://storage.googleapis.com/imatrix-files/159e7293-b9a8-4480-9c04-1a62ef4f115a.jpg",
      "organizationId": 298726404,
      "productId": 3829380261,
      "groupId": 1082477619,
      "createdAt": 1689808170000,
      "favorite1": 2719317351,
      "favorite2": 109753869,
      "favorite3": 2840021870,
      "isFavorite": false,
      "currentVersion": "1.020.000"
    },
    {
      "sn": 815828186,
      "name": "AQM-1 #1",
      "mac": "00:06:8b:01:05:57",
      "image": "https://storage.googleapis.com/imatrix-files/65057ee2-b92b-49c5-95f7-c8549a32243a-NEO-05.jpg",
      "organizationId": 298726404,
      "productId": 548556236,
      "groupId": 1082477619,
      "createdAt": 1667343138000,
      "favorite1": 493239876,
      "favorite2": 324179680,
      "favorite3": 2899002727,
      "isFavorite": false,
      "currentVersion": "1.020.000"
    },
    {
      "sn": 456047521,
      "name": "Failed Gateway 0456047521",
      "mac": "00:06:8b:01:03:5e",
      "image": "https://storage.googleapis.com/imatrix-files-prod/1e64fba0-7bf0-44f2-a860-b7843465c70b.jpg",
      "organizationId": 298726404,
      "productId": 984993858,
      "groupId": 1769104624,
      "createdAt": 1687897541000,
      "favorite1": 355762848,
      "favorite2": 3974806334,
      "favorite3": 130129941,
      "isFavorite": false,
      "currentVersion": "1.022.033"
    },
    {
      "sn": 915867336,
      "name": "Failed Gateway 0915867336",
      "mac": "00:06:8b:01:04:5b",
      "image": "https://storage.googleapis.com/imatrix-files-prod/1e64fba0-7bf0-44f2-a860-b7843465c70b.jpg",
      "organizationId": 298726404,
      "productId": 984993858,
      "groupId": 1769104624,
      "createdAt": 1690558964000,
      "favorite1": 355762848,
      "favorite2": 3974806334,
      "favorite3": 130129941,
      "isFavorite": false,
      "currentVersion": "1.022.038"
    },
    {
      "sn": 592978988,
      "name": "Greg's Desk NEO-1D",
      "mac": "00:06:8b:01:11:eb",
      "image": "https://storage.googleapis.com/imatrix-files-prod/6b70d448-a088-48a7-898e-b14893013caa.jpg",
      "organizationId": 298726404,
      "productId": 1349851161,
      "groupId": 1082477619,
      "createdAt": 1749149336000,
      "favorite1": 58108062,
      "favorite2": 872052224,
      "favorite3": null,
      "isFavorite": false,
      "currentVersion": "1.023.000"
    },
    {
      "sn": 955154708,
      "name": "Home Office",
      "mac": "00:06:8b:01:01:db",
      "image": "https://storage.googleapis.com/imatrix-files-prod/aa13b1ee-9c3d-473f-9768-d746358039d0.jpg",
      "organizationId": 298726404,
      "productId": 1472614291,
      "groupId": 1082477619,
      "createdAt": 1667342550000,
      "favorite1": 883739317,
      "favorite2": 313619845,
      "favorite3": 516671690,
      "isFavorite": false,
      "currentVersion": "1.023.000"
    },
    {
      "sn": 600988347,
      "name": "Home Office Desk - offline",
      "mac": "00:06:8b:01:11:e8",
      "image": "https://storage.googleapis.com/imatrix-files-prod/7c031082-9a63-4aee-8e3b-bffbd9d51735.jpg",
      "organizationId": 298726404,
      "productId": 1349851161,
      "groupId": 1082477619,
      "createdAt": 1709759848000,
      "favorite1": 58108062,
      "favorite2": 872052224,
      "favorite3": null,
      "isFavorite": false,
      "currentVersion": "1.021.001"
    },
    {
      "sn": 296540475,
      "name": "Kitchen",
      "mac": "00:06:8b:01:0f:40",
      "image": "https://storage.googleapis.com/imatrix-files-prod/6b70d448-a088-48a7-898e-b14893013caa.jpg",
      "organizationId": 298726404,
      "productId": 1349851161,
      "groupId": 1082477619,
      "createdAt": 1709346933000,
      "favorite1": 58108062,
      "favorite2": 872052224,
      "favorite3": null,
      "isFavorite": false,
      "currentVersion": "1.023.000"
    },
    {
      "sn": 174959126,
      "name": "Kitchen  Refrigerator Door",
      "mac": "00:06:8b:01:15:06",
      "image": "https://storage.googleapis.com/imatrix-files-prod/ff11e59a-bd34-48db-a4ed-ebcaf6b9dee9.jpg",
      "organizationId": 298726404,
      "productId": 1272203777,
      "groupId": 1082477619,
      "createdAt": 1720465112000,
      "favorite1": 870568750,
      "favorite2": 357403979,
      "favorite3": 4153769548,
      "isFavorite": false,
      "currentVersion": "1.020.001"
    }
  ],
  "total": 30
}

Create a 4 column list of the Names of the names and let the user select the device. Use the device serial number as though it was provided on the commandline

The default operation with no command line optios is to list all devices/things the let user select device, then list all sensors and let user select sensor, then prompt for start and end time

review all scripts the default url should use: api.imatrixsys.com if the option -dev is used on the command line then use the base url api-dev.imatrixsys.com
Update all scripts to be consisent in this use

the script get_sensor_data.py incorrectly uses the serial number of the device when requesting information about the product. it should use the productId from the JSON

the script get_sensor_data.py failed review issue, review api documentation for correct format. Ask any quesions needed for assistance. if the request fails print the requesting URL and payload
greg@Greg-P1-Laptop:~/iMatrix/iMatrix_Client/tools/get_sensor_data$ python3 get_sensor_data.py -u greg.phillips.tahoe@gmail.com -p SierraSnow100!
🔐 Logging in to iMatrix API...
✅ Login successful.
🔍 Fetching your devices...
✅ Found 10 devices in your account

================================================================================
                                  USER DEVICES
                                   (10 found)
================================================================================
  # Device Name                         Serial Number Product ID   Version
--------------------------------------------------------------------------------
[ 1] 1st Floor Micro Gateway             863095613    984993858    1.034.001
[ 2] AGSoil-1                            81541896     3829380261   1.020.000
[ 3] AQM-1 #1                            815828186    548556236    1.020.000
[ 4] Failed Gateway 0456047521           456047521    984993858    1.022.033
[ 5] Failed Gateway 0915867336           915867336    984993858    1.022.038
[ 6] Greg's Desk NEO-1D                  592978988    1349851161   1.023.000
[ 7] Home Office                         955154708    1472614291   1.023.000
[ 8] Home Office Desk - offline          600988347    1349851161   1.021.001
[ 9] Kitchen                             296540475    1349851161   1.023.000
[10] Kitchen  Refrigerator Door          174959126    1272203777   1.020.001
--------------------------------------------------------------------------------
Select a device [1-10], or 'q' to quit:
Enter your choice: 6
✅ Selected: Greg's Desk NEO-1D (Serial: 592978988)

📱 Device Details:
   Name:            Greg's Desk NEO-1D
   Serial Number:   592978988
   MAC Address:     00:06:8b:01:11:eb
   Product ID:      1349851161
   Group ID:        1082477619
   Organization:    298726404
   Version:         1.023.000
   Created:         2025-06-05T11:48:56Z

Proceeding to sensor discovery...
🔍 Discovering sensors for device: 592978988
🔍 Fetching product information for product ID: 1349851161
✅ Retrieved product information
📊 Found 7 sensors, fetching details...
✅ Successfully discovered 7 sensors

📊 Available sensors (7 found):
--------------------------------------------------------------------------------
[1] Temperature (ID: 58108062)
    Units: Deg. C | Type: IMX_FLOAT
[2] Battery Voltage (ID: 528597925)
    Units: Volts | Type: IMX_FLOAT
[3] Dew Point (ID: 726966252)
    Units: Deg. C | Type: IMX_FLOAT
[4] Air VPD (ID: 847839682)
    Units: kPa | Type: IMX_FLOAT
[5] Humidity (ID: 872052224)
    Units: %RH | Type: IMX_FLOAT
[6] Heat Index (ID: 916775340)
    Units: Deg. C | Type: IMX_FLOAT
[7] Wet Bulb (ID: 1719488477)
    Units: Deg. C | Type: IMX_FLOAT
--------------------------------------------------------------------------------
Select a sensor to download [1-7], or 'q' to quit:
Enter your choice: 1
✅ Selected: Temperature (ID: 58108062)

📅 Date/time range required for data download

Supported formats:
  • Epoch milliseconds: 1736899200000
  • Date only: 01/15/25 (assumes midnight to midnight)
  • Date and time: 01/15/25 14:30
  • Enter 'q' to quit

📅 Enter start date/time: 9/16/25
✅ Start: 2025-09-16T00:00:00Z
📅 Enter end date/time: 9/17/25
✅ End: 2025-09-17T23:59:59Z
📊 Date range: 48.0 hours

🚀 Starting sensor data download
   Serial: None
   Sensor: Temperature (ID: 58108062)
   Period: 2025-09-16T00:00:00Z to 2025-09-17T23:59:59Z

📊 Fetching Sensor 58108062 (ID: 58108062) data...
❌ Failed to fetch sensor 58108062 data
   Status code: 400
   Response: {"message":"Given parameter sn is invalid. Value (\"None\") cannot be parsed into number."}
greg@Greg-P1-Laptop:~/iMatrix/iMatrix_Client/tools/get_sensor_data$

---

## Additional Features Implemented (2025-12-08)

The following features have been added beyond the original requirements:

### Multi-Sensor Download
- Download multiple sensors in a single request using multiple `-id` flags:
  ```bash
  python3 get_sensor_data.py -s 592978988 -id 509 -id 514 -id 522 -ts "01/15/25" -te "01/16/25" -u user@example.com
  ```
- Interactive [D] Direct entry option for comma-separated sensor IDs: `509, 514, 522`
- Combined JSON output containing all sensor data in single file
- Filename format: `{serial}_{id1}_{id2}_{id3}_{date}.json`

### Last 24 Hours Default
- Press Enter at date prompt to use last 24 hours as default time range
- No need to calculate timestamps for quick data access

### Reproducible Command Output
- After every download, displays the full CLI command to reproduce the request:
  ```
  📋 To reproduce this request:
     python3 get_sensor_data.py -u user@example.com -s 592978988 -id 509 -ts 1736899200000 -te 1736985599000 -o json
  ```

### Enhanced Output
- Multi-sensor combined JSON structure with metadata and sensors array
- Per-sensor statistics in combined output
- Summary display for all downloaded sensors