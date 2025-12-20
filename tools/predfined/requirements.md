We are building a python tool to download details about the imatrix assests using the API. For reference on how this works refer to the code in this file: ~/iMatrix/iMatrix_Client/tools/get_sensor_data/get_sensor_data.py.
Refer to this URL for details on all API Calls: https://api-dev.imatrixsys.com/api-docs/swagger/#/
The user will pass the user name and password on the command line in the same way the example script works. You will use this to login and get a token that is used for future api calls.
Using the API request GET/sensors/{id} - get sensor you will loop thru all sensor ids from 1 to 999, ignoring any that are not found. 
The for each sensor returned is the following json format:

{
  "id": 0,
  "productId": 0,
  "platformId": 0,
  "name": "string",
  "type": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8
  ],
  "units": "string",
  "unitsType": [
    "IMX_NATIVE",
    "IMX_TEMPERATURE",
    "IMX_MASS",
    "IMX_LENGTH",
    "IMX_VOLUME",
    "IMX_NO_UNIT_TYPES"
  ],
  "dataType": [
    "IMX_UINT32",
    "IMX_INT32",
    "IMX_FLOAT",
    "IMX_VARIABLE_LENGTH",
    "IMX_NO_DATA_TYPES"
  ],
  "mode": "string",
  "defaultValue": 0,
  "iconUrl": "string",
  "thresholdQualificationTime": 0,
  "minAdvisoryEnabled": true,
  "minAdvisory": 0,
  "minWarningEnabled": true,
  "minWarning": 0,
  "minAlarmEnabled": true,
  "minAlarm": 0,
  "maxAdvisoryEnabled": true,
  "maxAdvisory": 0,
  "maxWarningEnabled": true,
  "maxWarning": 0,
  "maxAlarmEnabled": true,
  "maxAlarm": 0,
  "maxGraph": 0,
  "minGraph": 0,
  "calibrationRef1": 0,
  "calibrationRef2": 0,
  "calibrationRef3": 0
}

	There is no sensor with id = {id}
The iconUrl is a link to an image, usually in SVG or PNG format. Download this  icon image to a subdirectory called “icons”.
Build a local static HTML page with the heading “iMatrix Internal Sensor icons.” The iMatrix Logo will be displayed to the left. The icon is in the file iMatrix_logo.jpg.
Create a table for all of the downloaded icons.
Each table entry has a header and the icon. The icon size is scaled to100x100 pixels.
The header will have the name of the icon.
Show progress as the program processes each icon and creates the page.
Provide the file url as final output.
style the page using the imatrix color palette colors of
#005C8C
#0085B4
#A8D2E3
#D8E9F0
#F5F9FC
#121212


  1. Should the HTML page show ALL sensors or just those with valid/non-empty iconUrl?
  Show All - any missing should show error icon
  2. What should happen if the sensor doesn't have an iconUrl or the iconUrl is empty?
  refer to 1
  3. Should the table be sorted in any particular way (by sensor ID, alphabetically by name)?
  sort by id
  4. Does the iMatrix_logo.jpg already exist in this directory or does it need to be fetched?
  file exists
  5. Should this use the development API or production API (or have a flag like the reference script)?
  use flag, default to development
  6. What should the output HTML filename be?
  imatrix_predefined.html
  7. Should we store metadata about the sensors (like id, name, units) along with the icons?
  yes
  8. How should we handle rate limiting when making 999 API calls?
  no rate limit
  9. Should there be error handling for failed icon downloads?
  output a message and contine processing

  additional 
  the head will contain the <id>:<name> in 8 point font

For the following fields if the values returned are 0 or 1 replace with false or true

  "minAdvisoryEnabled"
  "minWarningEnabled"
  "minAlarmEnabled"
  "maxAdvisoryEnabled"
  "maxWarningEnabled"
  "maxAlarmEnabled"

  write a another script to provide the user with the ability to update the details of a sensor.
  the script will accept 3 parameters
  1. -s sensor id. The sensor id to use for the operation
  2. -i <filename>. The path/filename of the image to replace the icon
  3. -j <filename>. The path/filename of a JSON file with all parameters for a sensor to update.

  The  sensor id is mandatory. 
  The image and or JSON file must be provided.

If the user provides an image file then it must first be uploaded to the iMatrix File system using the  API POST ​/files​/ - upload file.
The script uses the the API call PUT ​/sensors​/{id} - to update sensor.
Ask any questions.

Write another script like update_sensor.py that instead of updating a sensor updates a product. Use the API GET ​/products​/{id} - to get product details
The returned JSON is in the following format:
{
  "id": 0,
  "organizationId": 0,
  "platformId": 0,
  "platformType": [
    "ble",
    "wifi"
  ],
  "name": "string",
  "shortName": "string",
  "isPublished": true,
  "internalFlashSize": 0,
  "externalFlashSize": 0,
  "badge": [
    "imatrix",
    "agrowtronics"
  ],
  "defaultFavorite1": 0,
  "defaultFavorite2": 0,
  "defaultFavorite3": 0,
  "noControls": 0,
  "noSensors": 0,
  "imageUrl": "string",
  "iconUrl": "string",
  "controlSensorIds": [],
  "rssiUse": 0,
  "batteryUse": 0,
  "operationalVoltage": {
    "id": 0,
    "name": "string",
    "profile": [
      "{1: 2.65, 2: 2.8, 3: 2.85, 4: 2.87, 5: 2.9, 6: 2,95, 7: 3.0}"
    ]
  },
  "externalType": [
    "appliance",
    null
  ]
}

provide command line options to upload images and update the following:

  "imageUrl"
  "iconUrl"
  "defaultImage"

Use the API PUT ​/products​/{id} - to update product

Ask any questions
────────────────

Write another script like get_predefined_icons.py that instead of getting sensor data it gets product data.
Use the API GET ​/products​/public - to get all public products data.
Create a new static web page the same way however include the three graphic items associated with each product
  "imageUrl"
  "iconUrl"
  "defaultImage"

  Example output from the API GET ​/products​/public is:
  [
  {
    "id": 0,
    "organizationId": 0,
    "platformId": 0,
    "platformType": [
      "ble",
      "wifi"
    ],
    "name": "string",
    "shortName": "string",
    "isPublished": true,
    "internalFlashSize": 0,
    "externalFlashSize": 0,
    "badge": [
      "imatrix",
      "agrowtronics"
    ],
    "defaultFavorite1": 0,
    "defaultFavorite2": 0,
    "defaultFavorite3": 0,
    "noControls": 0,
    "noSensors": 0,
    "imageUrl": "string",
    "iconUrl": "string",
    "controlSensorIds": [],
    "rssiUse": 0,
    "batteryUse": 0,
    "operationalVoltage": {
      "id": 0,
      "name": "string",
      "profile": [
        "{1: 2.65, 2: 2.8, 3: 2.85, 4: 2.87, 5: 2.9, 6: 2,95, 7: 3.0}"
      ]
    },
    "externalType": [
      "appliance",
      null
    ]
  }
]


Add the 2 seconds hover over funciton to the page generated by the get_public_products.py script.

Add a hover over the sensor list that will show the sensor names and icons for all the sensors associated with the products 
due to space only show the first 10 control / sensor icons in the table. show all of the when the hove over action is taken 

use the iMatrix API GET ​/sensors​/predefined​/product​/{productId} - to get predefined sensor ids by product. Show a separate row for the icons and list of predefined sensors.
Limit the display of controls, sensors and predefined sensors to 5 items with the +N button for over flow. clicking on the + overflow button will show all sensors in a pop up.

Use the iMatrix API GET ​/admin​/products​/configs​/default​/{id} - to get default configs. This configuration determines the order and visibility of the controls and sensros. Use the order to sort the display controls and sensors 
for the entries. Show a red cross in the right corner of any products that the list of sensors does not match the list in the reply to the API request. Show a green check if all the controls and sensors are matched. in the pop up of the controls sensor list add the attribute "visible" after the id and show the value from the response.
The format of the response from the API call is:
[
  {
    "productId": 0,
    "userConfig": {
      "order": [
        {
          "id": 0,
          "visible": true
        }
      ]
    }
  }
]

A a feature that if the configuration does not match all the defined controls and sensors and the user hovers over the red X it will pop up a list of the confilcts.

The list of sensors should not include the predefined sensors. update

After the product pop has been show, close this if the user scrolls with the moust or the slider.

The configuration contains both predefined and product sensors. The list must match the full set. The display of the list of "sensors" should not include the entries in the predfiend list

The list of sensors in the table for the product and in the pop up list must be in the order defined in the configuratioon from the API call GET ​/admin​/products​/configs​/default​/{id}