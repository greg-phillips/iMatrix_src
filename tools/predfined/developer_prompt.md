# Developer Prompt: iMatrix Predefined Sensor Tools

**Date**: 2025-12-13
**Version**: 1.3.0

This document provides complete specifications for implementing Python scripts that interact with the iMatrix API to manage predefined sensor definitions and products.

---

## Project Overview

Create four Python command-line tools for managing iMatrix predefined sensors and products:

1. **get_predefined_icons.py** - Downloads all predefined sensor definitions and generates an HTML catalog
2. **get_public_products.py** - Downloads all public products and generates an HTML catalog
3. **update_sensor.py** - Updates individual sensor definitions via the API
4. **update_product.py** - Updates individual product details via the API

---

## Environment & Dependencies

### Python Version
- Python 3.7+

### Required Packages
```bash
python3 -m pip install requests urllib3
```

### Standard Library Modules Used
- `argparse` - Command line argument parsing
- `json` - JSON encoding/decoding
- `os` - File system operations
- `sys` - System exit codes
- `getpass` - Secure password input
- `glob` - File pattern matching (get_predefined_icons.py only)
- `datetime` - Timestamps

---

## iMatrix API Reference

### Base URLs

| Environment | URL |
|-------------|-----|
| Development (default) | `https://api-dev.imatrixsys.com/api/v1` |
| Production | `https://api.imatrixsys.com/api/v1` |

### SSL Certificates
Disable SSL verification for development API:
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# Use verify=False in requests
```

### Authentication

#### Login Endpoint
```
POST /login
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  "password": "password123"
}

Response (200 OK):
{
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### Using the Token
All subsequent API calls require the header:
```
x-auth-token: <token>
```

### Sensor Endpoints

#### Get Sensor
```
GET /sensors/{id}
Headers:
  accept: application/json
  x-auth-token: <token>

Response (200 OK):
{
  "id": 42,
  "productId": 1,
  "platformId": 1,
  "name": "Temperature",
  "type": 1,
  "units": "Celsius",
  "unitsType": "IMX_TEMPERATURE",
  "dataType": "IMX_FLOAT",
  "mode": "read",
  "defaultValue": 0,
  "iconUrl": "https://storage.googleapis.com/imatrix-files/xxx.svg",
  "thresholdQualificationTime": 0,
  "minAdvisoryEnabled": 0,
  "minAdvisory": 0,
  "minWarningEnabled": 1,
  "minWarning": 0,
  "minAlarmEnabled": 0,
  "minAlarm": 0,
  "maxAdvisoryEnabled": 0,
  "maxAdvisory": 0,
  "maxWarningEnabled": 1,
  "maxWarning": 100,
  "maxAlarmEnabled": 0,
  "maxAlarm": 0,
  "maxGraph": 100,
  "minGraph": 0,
  "calibrationRef1": 0,
  "calibrationRef2": 0,
  "calibrationRef3": 0
}

Response (404 Not Found):
Sensor does not exist
```

#### Update Sensor
```
PUT /sensors/{id}
Headers:
  accept: application/json
  Content-Type: application/json
  x-auth-token: <token>

Request Body:
{
  // Full sensor object with updated fields
}

Response (200 OK):
Updated sensor object
```

#### Upload File
```
POST /files/
Headers:
  accept: application/json
  x-auth-token: <token>
Content-Type: multipart/form-data

Form Data:
  file: (binary file content)

Response (200/201):
{
  "url": "https://storage.googleapis.com/imatrix-files/uuid-filename.ext"
  // or "fileUrl" or "path" depending on API version
  // or "id"/"fileId" which can be used to construct URL
}
```

### Product Endpoints

#### Get Public Products
```
GET /products/public
Headers:
  accept: application/json
  x-auth-token: <token>

Response (200 OK):
[
  {
    "id": 12345,
    "organizationId": 1,
    "platformId": 1,
    "platformType": ["ble", "wifi"],
    "name": "Product Name",
    "shortName": "ProdName",
    "isPublished": true,
    "internalFlashSize": 0,
    "externalFlashSize": 0,
    "badge": ["imatrix", "agrowtronics"],
    "defaultFavorite1": 0,
    "defaultFavorite2": 0,
    "defaultFavorite3": 0,
    "noControls": 2,
    "noSensors": 5,
    "imageUrl": "https://storage.googleapis.com/imatrix-files/xxx.jpg",
    "iconUrl": "https://storage.googleapis.com/imatrix-files/xxx.svg",
    "defaultImage": "https://storage.googleapis.com/imatrix-files/xxx.jpg",
    "controlSensorIds": [],
    "rssiUse": 0,
    "batteryUse": 0,
    "operationalVoltage": {
      "id": 0,
      "name": "string",
      "profile": []
    },
    "externalType": ["appliance", null]
  }
]
```

#### Get Product
```
GET /products/{id}
Headers:
  accept: application/json
  x-auth-token: <token>

Response (200 OK):
{
  "id": 30604238,
  "name": "My Product",
  "shortName": "MyProd",
  "iconUrl": "https://storage.googleapis.com/imatrix-files/xxx.svg",
  "imageUrl": "https://storage.googleapis.com/imatrix-files/xxx.jpg",
  "defaultImage": "https://storage.googleapis.com/imatrix-files/xxx.jpg",
  "noSensors": 5,
  "isPublished": true,
  "description": "Product description",
  // ... other product fields
}

Response (404 Not Found):
Product does not exist
```

#### Update Product
```
PUT /products/{id}
Headers:
  accept: application/json
  Content-Type: application/json
  x-auth-token: <token>

Request Body:
{
  // Full product object with updated fields
}

Response (200 OK):
Updated product object
```

#### Get Predefined Sensors by Product
```
GET /sensors/predefined/product/{productId}
Headers:
  accept: application/json
  x-auth-token: <token>

Response (200 OK):
[1, 2, 3, 42, 56]  // Array of predefined sensor IDs

Response (404 Not Found):
Product does not exist or has no predefined sensors
```

#### Get Default Product Config
```
GET /admin/products/configs/default/{id}
Headers:
  accept: application/json
  x-auth-token: <token>

Response (200 OK):
[
  {
    "productId": 12345,
    "userConfig": {
      "order": [
        {"id": 1, "visible": true},
        {"id": 2, "visible": false},
        {"id": 3, "visible": true}
      ]
    }
  }
]

Response (404 Not Found):
Product does not exist or has no default config
```

The `order` array in the config defines:
- **Display order**: Sensors/controls are shown in this exact sequence
- **Visibility**: Whether each sensor is visible (`true`) or hidden (`false`) in the UI

---

## Script 1: get_predefined_icons.py

### Purpose
Enumerate all predefined sensors (IDs 1-999), download their icons, save JSON definitions, and generate an interactive HTML catalog page.

### Command Line Arguments

| Argument | Short | Required | Default | Description |
|----------|-------|----------|---------|-------------|
| `--username` | `-u` | Yes | - | iMatrix account email |
| `--password` | `-p` | No | Prompt | iMatrix account password |
| `--production` | `-prod` | No | False | Use production API |
| `--verbose` | `-v` | No | False | Verbose output |

### Program Flow

1. **Parse Arguments**
   - Validate required arguments
   - Prompt for password if not provided using `getpass.getpass()`

2. **Login to API**
   - POST to `/login` with credentials
   - Extract and store token from response
   - Exit with error if login fails

3. **Create Output Directory**
   - Create `icons/` subdirectory if it doesn't exist

4. **Enumerate Sensors (IDs 1-999)**
   - Display progress bar during enumeration
   - For each ID, GET `/sensors/{id}`
   - Skip 404 responses (sensor doesn't exist)
   - For valid sensors:
     - **Convert boolean fields**: The following fields return `0` or `1` from the API but should be stored as `false` or `true`:
       - `minAdvisoryEnabled`
       - `minWarningEnabled`
       - `minAlarmEnabled`
       - `maxAdvisoryEnabled`
       - `maxWarningEnabled`
       - `maxAlarmEnabled`
     - Save sensor JSON to `icons/sensor_{id}.json`
     - Add to sensors list

5. **Download Icons**
   - Create placeholder SVG for missing icons
   - For each sensor:
     - Extract `iconUrl` field
     - Download image file
     - Save as `icons/sensor_{id}.{ext}` (preserve original extension)
     - If download fails or no URL, use placeholder
     - Track success/failure counts

6. **Save Metadata**
   - Write combined `sensor_metadata.json` with all sensors

7. **Generate HTML Page**
   - Create `imatrix_predefined.html` with:
     - iMatrix logo in header (use `iMatrix_logo.jpg`)
     - Title: "iMatrix Internal Sensor Icons"
     - Statistics bar showing total sensors and generation date
     - Responsive CSS grid layout
     - Sensor cards with:
       - Icon image (100x100 pixels)
       - Label: `{id}:{name}` in 8pt font
     - **Hover popup feature**:
       - After 2-second hover delay, show popup
       - Display all sensor fields in formatted table
       - Smart positioning (stay within viewport)
       - Close button and click-outside-to-dismiss
     - Footer with company info

8. **Print Summary**
   - Total sensors found
   - JSON files saved
   - Icons downloaded vs using placeholder
   - Output file paths (both Linux and Windows format)

### Progress Bar Format
```
  [==========================------------------------] 52% (520/999)
```

### Placeholder SVG
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="#D8E9F0" stroke="#A8D2E3" stroke-width="2"/>
  <text x="50" y="45" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#005C8C">No Icon</text>
  <text x="50" y="62" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#0085B4">Available</text>
</svg>
```

### iMatrix Color Palette (for HTML styling)
```python
COLORS = {
    'primary_dark': '#005C8C',
    'primary': '#0085B4',
    'light_blue': '#A8D2E3',
    'lighter_blue': '#D8E9F0',
    'near_white': '#F5F9FC',
    'text_dark': '#121212',
}
```

### HTML Hover Popup JavaScript Requirements

The popup should:
- Appear after exactly 2 seconds of hovering on a sensor card
- Display all sensor fields with friendly names (e.g., `minWarningEnabled` → `Min Warning Enabled`)
- Format values appropriately:
  - `null`/`undefined` → `<em>null</em>`
  - Empty string → `<em>empty</em>`
  - Boolean → `Yes` / `No`
  - Arrays → comma-separated values
- Position intelligently:
  - Prefer right side of card
  - If would overflow right edge, show on left
  - If would overflow bottom, adjust upward
- Remain visible while mouse is over the popup itself
- Close when:
  - Mouse leaves both card and popup
  - User clicks the X button
  - User clicks outside the popup

### Output Files

| File | Description |
|------|-------------|
| `imatrix_predefined.html` | Interactive HTML catalog |
| `sensor_metadata.json` | Combined JSON with all sensors |
| `icons/sensor_{id}.json` | Individual sensor JSON files |
| `icons/sensor_{id}.{ext}` | Downloaded icon images |
| `icons/placeholder.svg` | Placeholder for missing icons |

### Example Usage
```bash
python3 get_predefined_icons.py -u admin@company.com
python3 get_predefined_icons.py -u admin@company.com -p secret123 -prod
python3 get_predefined_icons.py -u admin@company.com -v
```

### Example Output
```
============================================================
iMatrix Predefined Sensor Icon Downloader
============================================================
Logging in to development iMatrix API...
Login successful.

Enumerating sensors 1-999...
  [==================================================] 100% (999/999)
Found 156 sensors.

Downloading icons for 156 sensors...
  [==================================================] 100% (156/156)
Downloaded 142 icons, 14 using placeholder.

Metadata saved to: /path/to/sensor_metadata.json

Generating HTML page...

============================================================
SUMMARY
============================================================
Total sensors found:    156
JSON files saved:       156 (icons/sensor_<id>.json)
Icons downloaded:       142
Using placeholder:      14
HTML output:            /path/to/imatrix_predefined.html
Linux URL:              file:///path/to/imatrix_predefined.html
Windows URL:            file:///U://path/to/imatrix_predefined.html
============================================================
```

---

## Script 2: get_public_products.py

### Purpose
Download all public products via the API, download their images, fetch predefined sensors and default configs, and generate an interactive HTML catalog page with config-based sensor ordering and match indicators.

### Command Line Arguments

| Argument | Short | Required | Default | Description |
|----------|-------|----------|---------|-------------|
| `--username` | `-u` | Yes | - | iMatrix account email |
| `--password` | `-p` | No | Prompt | iMatrix account password |
| `--production` | `-prod` | No | False | Use production API |
| `--verbose` | `-v` | No | False | Verbose output |

### Program Flow

1. **Parse Arguments**
   - Validate required arguments
   - Prompt for password if not provided using `getpass.getpass()`

2. **Login to API**
   - POST to `/login` with credentials
   - Extract and store token from response
   - Exit with error if login fails

3. **Create Output Directory**
   - Create `products/` subdirectory if it doesn't exist

4. **Fetch Public Products**
   - GET `/products/public`
   - Returns array of all public product objects
   - Save each product JSON to `products/product_{id}.json`

5. **Download Images**
   - Create placeholder SVG for missing images
   - For each product, download three image types:
     - `iconUrl` → `products/product_{id}_icon.{ext}`
     - `imageUrl` → `products/product_{id}_image.{ext}`
     - `defaultImage` → `products/product_{id}_default.{ext}`
   - Track success/failure counts

6. **Fetch Predefined Sensors**
   - For each product, GET `/sensors/predefined/product/{productId}`
   - Store mapping of product ID → predefined sensor IDs
   - Display progress bar during fetch

7. **Fetch Default Configs**
   - For each product, GET `/admin/products/configs/default/{id}`
   - Extract `userConfig.order` array containing `{id, visible}` objects
   - Store mapping of product ID → config data
   - Display progress bar during fetch

8. **Fetch Sensor Details**
   - Collect all unique sensor IDs (from controlSensorIds + predefined)
   - GET `/sensors/{id}` for each unique sensor
   - Store sensor data (name, iconUrl) for display

9. **Save Metadata**
   - Write combined `product_metadata.json` with all products

10. **Generate HTML Page**
    - Create `imatrix_public_products.html` with:
      - iMatrix logo in header (use `iMatrix_logo.jpg`)
      - Title: "iMatrix Public Products"
      - Statistics bar showing total products, generation date, favorites toggle
      - Responsive CSS grid layout
      - Product cards with:
        - Icon in card header (60x60 pixels)
        - Product name and ID
        - **Config match indicator** (green ✓ or red ✗) in top-right corner
        - Favorite star button
        - Three images side-by-side (Icon, Image, Default)
        - **Sensors section** (sorted by config order, excludes predefined, first 5 + overflow)
        - **Predefined Sensors section** (sorted by config order, first 5 + overflow)
        - Sensor and control counts
        - Platform type badges (ble, wifi, etc.)
        - Organization badges
      - **Sensor popup** (click +N indicator):
        - Shows all sensors with icon, name, ID
        - Shows **visibility indicator** (Visible/Hidden badge from config)
        - Sensors sorted by config order
      - **Config match tooltip** (hover on red X):
        - Shows sensor IDs missing from config
        - Shows extra IDs in config not in product
      - **Hover popup feature**:
        - After 2-second hover delay, show popup
        - Display all product fields in formatted table
        - Smart positioning (stay within viewport)
        - Close button and click-outside-to-dismiss
      - **Favorites system**:
        - Star/unstar products
        - Filter toggle to show only favorites
        - Persisted in localStorage

11. **Print Summary**
    - Total products found
    - JSON files saved
    - Images downloaded vs failed/missing
    - Sensors fetched
    - Predefined sensor references
    - Default configs found
    - Output file paths (both Linux and Windows format)

### Config Match Logic

The config match indicator compares:
- **Full product sensors** = `controlSensorIds` + predefined sensor IDs
- **Config order IDs** = IDs from `userConfig.order` array

Match (green ✓): All product sensors are in config AND all config IDs are in product sensors
Mismatch (red ✗): Any difference between the two sets

### Sensor Display Logic

- **Sensors section**: Shows `controlSensorIds` MINUS predefined sensor IDs (no duplicates)
- **Predefined Sensors section**: Shows only predefined sensor IDs
- Both sections sorted by config order (sensors not in config appear at end)

### Product Image Fields

| Field | Filename Pattern | Description |
|-------|------------------|-------------|
| `iconUrl` | `product_{id}_icon.{ext}` | Small product icon |
| `imageUrl` | `product_{id}_image.{ext}` | Main product image |
| `defaultImage` | `product_{id}_default.{ext}` | Default product image |

### HTML Card Layout

Each product card should display:
```
┌─────────────────────────────────────┐
│  [Icon]  Product Name               │
│          ID: 12345                  │
│          ShortName                  │
├─────────────────────────────────────┤
│   Icon    │   Image   │   Default   │
│  [img]    │   [img]   │    [img]    │
├─────────────────────────────────────┤
│  Sensors: 5    Controls: 2          │
│  [ble] [wifi]                       │
│  [imatrix]                          │
└─────────────────────────────────────┘
```

### Output Files

| File | Description |
|------|-------------|
| `imatrix_public_products.html` | Interactive HTML catalog |
| `product_metadata.json` | Combined JSON with all products |
| `products/product_{id}.json` | Individual product JSON files |
| `products/product_{id}_icon.{ext}` | Downloaded icons |
| `products/product_{id}_image.{ext}` | Downloaded images |
| `products/product_{id}_default.{ext}` | Downloaded default images |
| `products/placeholder.svg` | Placeholder for missing images |

### Example Usage
```bash
python3 get_public_products.py -u admin@company.com
python3 get_public_products.py -u admin@company.com -p secret123 -prod
python3 get_public_products.py -u admin@company.com -v
```

### Example Output
```
============================================================
iMatrix Public Products Downloader
============================================================
Logging in to development iMatrix API...
Login successful.
Fetching public products...
Found 45 public products.

Saving product JSON files...
Saved 45 JSON files to products/

Downloading images for 45 products...
  [==================================================] 100% (45/45)
Downloaded 120 images, 15 failed/missing.

Metadata saved to: /path/to/product_metadata.json

Generating HTML page...

============================================================
SUMMARY
============================================================
Total products found:    45
JSON files saved:        45 (products/product_<id>.json)
Images downloaded:       120
Images failed/missing:   15
HTML output:             /path/to/imatrix_public_products.html
Linux URL:               file:///path/to/imatrix_public_products.html
Windows URL:             file:///U://path/to/imatrix_public_products.html
============================================================
```

---

## Script 3: update_sensor.py

### Purpose
Update a single sensor's icon and/or parameters via the iMatrix API. Supports uploading new icon images and applying parameter changes from a JSON file.

*Note: Shares common functions with other scripts (see Code Structure Recommendations).*

### Command Line Arguments

| Argument | Short | Required | Default | Description |
|----------|-------|----------|---------|-------------|
| `--username` | `-u` | Yes | - | iMatrix account email |
| `--password` | `-p` | No | Prompt | iMatrix account password |
| `--sensor-id` | `-s` | Yes | - | Sensor ID to update |
| `--image` | `-i` | No* | - | Path to image file for icon |
| `--json` | `-j` | No* | - | Path to JSON file with parameters |
| `--production` | `-prod` | No | False | Use production API |
| `--verbose` | `-v` | No | False | Verbose output |

*At least one of `--image` or `--json` must be provided.

### Validation Rules

1. **Sensor ID is mandatory** - exit with error if not provided
2. **At least one update source required** - exit with error if neither `-i` nor `-j` provided
3. **File existence check** - verify image and/or JSON files exist before API calls
4. **Sensor must exist** - verify sensor exists before attempting update

### Program Flow

1. **Parse and Validate Arguments**
   - Check required arguments
   - Validate at least one of `-i` or `-j` is provided
   - Verify files exist on disk
   - Prompt for password if not provided

2. **Login to API**
   - POST to `/login` with credentials
   - Store token for subsequent calls

3. **Fetch Current Sensor**
   - GET `/sensors/{id}`
   - Exit with error if sensor not found
   - Store current sensor data as base for update

4. **Process Image File (if provided)**
   - Determine content type from file extension:
     ```python
     content_types = {
         '.svg': 'image/svg+xml',
         '.png': 'image/png',
         '.jpg': 'image/jpeg',
         '.jpeg': 'image/jpeg',
         '.gif': 'image/gif',
         '.webp': 'image/webp'
     }
     ```
   - Upload file to `POST /files/`
   - Extract URL from response (check `url`, `fileUrl`, `path`, or construct from `id`)
   - Set `iconUrl` in update data

5. **Process JSON File (if provided)**
   - Load and parse JSON file
   - Merge all fields into update data (except `id` which should not be changed)
   - In verbose mode, print each field being set

6. **Update Sensor**
   - PUT `/sensors/{id}` with complete sensor data
   - Handle success/failure responses

7. **Print Summary**
   - Sensor ID and name
   - New icon URL (if image was uploaded)
   - Success/failure status

### Supported Image Formats
- SVG (`.svg`)
- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- GIF (`.gif`)
- WebP (`.webp`)

### JSON File Format
The JSON file should contain only the fields to update:
```json
{
  "name": "Updated Sensor Name",
  "units": "New Units",
  "minWarning": 10,
  "maxWarning": 90,
  "minWarningEnabled": true,
  "maxWarningEnabled": true
}
```

### Example Usage
```bash
# Update icon only
python3 update_sensor.py -u admin@company.com -s 42 -i new_icon.svg

# Update parameters only
python3 update_sensor.py -u admin@company.com -s 42 -j params.json

# Update both
python3 update_sensor.py -u admin@company.com -s 42 -i icon.svg -j params.json

# Production API with verbose output
python3 update_sensor.py -u admin@company.com -s 42 -i icon.svg -prod -v
```

### Example Output
```
============================================================
Update Sensor - iMatrix API
============================================================
Sensor ID: 42
Image file: temperature_icon.svg
JSON file: temp_params.json

Logging in to development iMatrix API...
Login successful.

Fetching sensor 42...
Found sensor: Temperature

Uploading image file...
Uploading file: temperature_icon.svg
File uploaded successfully: https://storage.googleapis.com/imatrix-files/abc123.svg
Icon URL set to: https://storage.googleapis.com/imatrix-files/abc123.svg

Loading JSON parameters...
Loaded 5 parameters from JSON file

Updating sensor 42...

Success: Sensor updated successfully

============================================================
UPDATE COMPLETE
============================================================
Sensor ID:    42
Sensor Name:  Temperature
New Icon URL: https://storage.googleapis.com/imatrix-files/abc123.svg
============================================================
```

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Login failed | Print error, exit code 1 |
| Sensor not found | Print error, exit code 1 |
| File not found | Print error, exit code 1 |
| Invalid JSON | Print parse error, exit code 1 |
| Upload failed | Print error, exit code 1 |
| Update failed | Print API error, exit code 1 |

---

## Script 4: update_product.py

### Purpose
Update a product's images (icon, image, defaultImage) and/or parameters via the iMatrix API. Supports uploading multiple image types and applying parameter changes from a JSON file.

*Note: Shares common functions with other scripts (see Code Structure Recommendations).*

### Command Line Arguments

| Argument | Short | Required | Default | Description |
|----------|-------|----------|---------|-------------|
| `--username` | `-u` | Yes | - | iMatrix account email |
| `--password` | `-pw` | No | Prompt | iMatrix account password |
| `--product-id` | `-p` | Yes | - | Product ID to update |
| `--icon` | `-i` | No* | - | Path to image file for icon (iconUrl) |
| `--image` | | No* | - | Path to image file for product image (imageUrl) |
| `--default-image` | | No* | - | Path to image file for default image (defaultImage) |
| `--json` | `-j` | No* | - | Path to JSON file with parameters |
| `--production` | `-prod` | No | False | Use production API |
| `--verbose` | `-v` | No | False | Verbose output |

*At least one of `--icon`, `--image`, `--default-image`, or `--json` must be provided.

### Product Image Fields

The product has three distinct image URL fields:

| Field | CLI Flag | Description |
|-------|----------|-------------|
| `iconUrl` | `-i, --icon` | Small icon representing the product |
| `imageUrl` | `--image` | Main product image |
| `defaultImage` | `--default-image` | Default image for the product |

### Validation Rules

1. **Product ID is mandatory** - exit with error if not provided
2. **At least one update source required** - exit with error if none of `-i`, `--image`, `--default-image`, or `-j` provided
3. **File existence check** - verify all image and JSON files exist before API calls
4. **Product must exist** - verify product exists before attempting update

### Program Flow

1. **Parse and Validate Arguments**
   - Check required arguments
   - Validate at least one update source is provided
   - Verify all specified files exist on disk
   - Prompt for password if not provided

2. **Login to API**
   - POST to `/login` with credentials
   - Store token for subsequent calls

3. **Fetch Current Product**
   - GET `/products/{id}`
   - Exit with error if product not found
   - Store current product data as base for update

4. **Process Icon File (if provided with `-i`)**
   - Upload file to `POST /files/`
   - Set returned URL to `iconUrl` field

5. **Process Image File (if provided with `--image`)**
   - Upload file to `POST /files/`
   - Set returned URL to `imageUrl` field

6. **Process Default Image File (if provided with `--default-image`)**
   - Upload file to `POST /files/`
   - Set returned URL to `defaultImage` field

7. **Process JSON File (if provided with `-j`)**
   - Load and parse JSON file
   - Merge all fields into update data (except `id` which should not be changed)
   - In verbose mode, print each field being set

8. **Update Product**
   - PUT `/products/{id}` with complete product data
   - Handle success/failure responses

9. **Print Summary**
   - Product ID and name
   - List of all updates applied (truncate long URLs)
   - Success/failure status

### JSON File Format
The JSON file should contain only the fields to update:
```json
{
  "name": "Updated Product Name",
  "shortName": "NewShort",
  "noSensors": 10,
  "isPublished": true,
  "description": "New description"
}
```

### Example Usage
```bash
# Update product icon only
python3 update_product.py -u admin@company.com -p 30604238 -i new_icon.svg

# Update product image
python3 update_product.py -u admin@company.com -p 30604238 --image product_photo.jpg

# Update default image
python3 update_product.py -u admin@company.com -p 30604238 --default-image default.jpg

# Update all three images at once
python3 update_product.py -u admin@company.com -p 30604238 -i icon.svg --image photo.jpg --default-image default.jpg

# Update parameters only
python3 update_product.py -u admin@company.com -p 30604238 -j params.json

# Update images and parameters together
python3 update_product.py -u admin@company.com -p 30604238 -i icon.svg -j params.json

# Production API with verbose output
python3 update_product.py -u admin@company.com -p 30604238 --image photo.jpg -prod -v
```

### Example Output
```
============================================================
Update Product - iMatrix API
============================================================
Product ID: 30604238
Icon file: product_icon.svg
Image file: product_photo.jpg
JSON file: product_params.json

Logging in to development iMatrix API...
Login successful.

Fetching product 30604238...
Found product: My Product

Uploading icon file...
  Uploading: product_icon.svg
  Uploaded successfully: https://storage.googleapis.com/imatrix-files/abc123.svg

Uploading image file...
  Uploading: product_photo.jpg
  Uploaded successfully: https://storage.googleapis.com/imatrix-files/def456.jpg

Loading JSON parameters...
Loaded 3 parameters from JSON file

Updating product 30604238...

Success: Product updated successfully

============================================================
UPDATE COMPLETE
============================================================
Product ID:   30604238
Product Name: My Product
Short Name:   MyProd

Updates applied:
  iconUrl: https://storage.googleapis.com/imatrix-files/...
  imageUrl: https://storage.googleapis.com/imatrix-files/...
  name: My Product
  shortName: MyProd
============================================================
```

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Login failed | Print error, exit code 1 |
| Product not found | Print error, exit code 1 |
| File not found | Print error, exit code 1 |
| Invalid JSON | Print parse error, exit code 1 |
| Upload failed | Print error, exit code 1 |
| Update failed | Print API error, exit code 1 |

---

## Code Structure Recommendations

### Common Functions (all scripts)

```python
def get_api_base_url(use_production: bool = False) -> str:
    """Return API base URL based on environment."""

def login_to_imatrix(email: str, password: str, use_production: bool = False) -> str:
    """Authenticate and return token. Exit on failure."""

def get_sensor(sensor_id: int, token: str, base_url: str) -> Optional[dict]:
    """Fetch sensor by ID. Return None if not found."""

def update_sensor(sensor_id: int, sensor_data: dict, token: str, base_url: str) -> Tuple[bool, str]:
    """Update sensor. Return (success, message)."""

def get_product(product_id: int, token: str, base_url: str) -> Optional[dict]:
    """Fetch product by ID. Return None if not found."""

def update_product(product_id: int, product_data: dict, token: str, base_url: str) -> Tuple[bool, str]:
    """Update product. Return (success, message)."""

def upload_file(file_path: str, token: str, base_url: str) -> Tuple[bool, str]:
    """Upload file to iMatrix. Return (success, url or error)."""

def load_json_file(file_path: str) -> Tuple[bool, dict]:
    """Load JSON file. Return (success, data or error_dict)."""
```

### get_predefined_icons.py Specific

```python
def enumerate_sensors(token: str, icons_dir: str, use_production: bool, verbose: bool) -> List[dict]:
    """Enumerate sensors 1-999, save JSON files, return list."""

def download_icon(icon_url: str, sensor_id: int, icons_dir: str, verbose: bool) -> Tuple[bool, str]:
    """Download icon image. Return (success, local_filename or error)."""

def download_all_icons(sensors: List[dict], icons_dir: str, verbose: bool) -> Tuple[int, int, List[dict]]:
    """Download all icons. Return (success_count, failure_count, updated_sensors)."""

def generate_html(sensors: List[dict], logo_path: str, output_file: str) -> str:
    """Generate HTML catalog. Return full path to file."""

def save_metadata(sensors: List[dict], output_file: str) -> None:
    """Save combined sensor metadata to JSON."""
```

### get_public_products.py Specific

```python
def get_public_products(token: str, base_url: str) -> List[dict]:
    """Fetch all public products. Return list of products."""

def download_image(url: str, product_id: int, image_type: str, output_dir: str, verbose: bool) -> Tuple[bool, str]:
    """Download single image. Return (success, local_filename or error)."""

def download_all_images(products: List[dict], output_dir: str, verbose: bool) -> Tuple[int, int, List[dict]]:
    """Download all images. Return (success_count, failure_count, updated_products)."""

def generate_html(products: List[dict], logo_path: str, output_file: str) -> str:
    """Generate HTML catalog. Return full path to file."""

def save_metadata(products: List[dict], output_file: str) -> None:
    """Save combined product metadata to JSON."""

def save_product_json(product: dict, output_dir: str) -> None:
    """Save individual product JSON file."""
```

### update_sensor.py Specific

Uses common functions: `get_api_base_url`, `login_to_imatrix`, `get_sensor`, `update_sensor`, `upload_file`, `load_json_file`

### update_product.py Specific

Uses common functions: `get_api_base_url`, `login_to_imatrix`, `get_product`, `update_product`, `upload_file`, `load_json_file`

---

## Testing Checklist

### get_predefined_icons.py

- [ ] Login with valid credentials succeeds
- [ ] Login with invalid credentials shows error and exits
- [ ] Progress bar displays correctly during enumeration
- [ ] Sensors are saved to individual JSON files
- [ ] Boolean fields are converted from 0/1 to false/true
- [ ] Icons are downloaded with correct extensions
- [ ] Missing icons use placeholder
- [ ] HTML page displays correctly in browser
- [ ] Hover popup appears after 2 seconds
- [ ] Hover popup shows all sensor fields
- [ ] Hover popup positions correctly (doesn't overflow viewport)
- [ ] Summary shows correct counts
- [ ] Both Linux and Windows URLs are displayed

### get_public_products.py

- [ ] Login with valid credentials succeeds
- [ ] Login with invalid credentials shows error and exits
- [ ] Products are fetched via GET /products/public
- [ ] Individual JSON files saved to products/ directory
- [ ] Icon images downloaded with correct filenames
- [ ] Image images downloaded with correct filenames
- [ ] Default images downloaded with correct filenames
- [ ] Missing images use placeholder
- [ ] Progress bar displays correctly during download
- [ ] HTML page displays correctly in browser
- [ ] Product cards show all three images
- [ ] Platform badges display correctly
- [ ] Organization badges display correctly
- [ ] Hover popup appears after 2 seconds
- [ ] Hover popup shows all product fields
- [ ] Summary shows correct counts
- [ ] Both Linux and Windows URLs are displayed

### update_sensor.py

- [ ] Error if no `-i` or `-j` provided
- [ ] Error if sensor ID doesn't exist
- [ ] Error if image file doesn't exist
- [ ] Error if JSON file doesn't exist
- [ ] Error if JSON file is invalid
- [ ] Image upload succeeds and URL is set
- [ ] JSON parameters are merged correctly
- [ ] Sensor update succeeds
- [ ] Verbose mode shows detailed output
- [ ] Production API flag works correctly

### update_product.py

- [ ] Error if no `-i`, `--image`, `--default-image`, or `-j` provided
- [ ] Error if product ID doesn't exist
- [ ] Error if any image file doesn't exist
- [ ] Error if JSON file doesn't exist
- [ ] Error if JSON file is invalid
- [ ] Icon upload succeeds and iconUrl is set
- [ ] Image upload succeeds and imageUrl is set
- [ ] Default image upload succeeds and defaultImage is set
- [ ] All three images can be uploaded at once
- [ ] JSON parameters are merged correctly
- [ ] Product update succeeds
- [ ] Verbose mode shows detailed output
- [ ] Production API flag works correctly
- [ ] Update summary shows all changes applied

---

## Reference Files

### Existing File: iMatrix_logo.jpg
Located in the same directory as the scripts. Used in the HTML header.

### API Documentation
Full API documentation available at:
- Development: https://api-dev.imatrixsys.com/api-docs/swagger/
- Production: https://api.imatrixsys.com/api-docs/swagger/

---

## Notes for Developers

1. **SSL Verification**: Disabled for development API. Do not disable in production environments.

2. **Rate Limiting**: The API may rate limit requests. The scripts do not implement delays between requests, but this could be added if issues occur.

3. **Error Messages**: Always provide clear, actionable error messages that help users understand what went wrong.

4. **Exit Codes**: Use `sys.exit(1)` for errors, `sys.exit(0)` or no explicit exit for success.

5. **Progress Feedback**: Long operations (enumeration, downloads) should show progress to the user.

6. **File Paths**: Use `os.path` functions for cross-platform compatibility.

7. **Encoding**: Always specify `encoding='utf-8'` when opening text files.

8. **Timeouts**: Use reasonable timeouts (30 seconds) for API requests to prevent hanging.
