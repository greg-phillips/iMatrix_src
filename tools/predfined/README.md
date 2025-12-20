# iMatrix Predefined Sensor Tools

**Date**: 2025-12-13
**Version**: 1.3.0
**Author**: Sierra Telecom

Tools for managing iMatrix predefined sensor definitions and products, including downloading sensor icons, updating sensor parameters, downloading public products, and updating product details via the iMatrix API.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Scripts](#scripts)
   - [get_predefined_icons.py](#get_predefined_iconspy)
   - [get_public_products.py](#get_public_productspy)
   - [update_sensor.py](#update_sensorpy)
   - [update_product.py](#update_productpy)
4. [API Reference](#api-reference)
5. [File Structure](#file-structure)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The iMatrix platform uses predefined sensors (IDs 1-999) that define standard sensor types across all products. These tools allow administrators to:

- **Download** all predefined sensor definitions and their icons
- **Generate** an HTML catalog of all sensor icons
- **Download** all public products and their images
- **Generate** an HTML catalog of all products with icons, images, and default images
- **Update** individual sensor definitions (icon, name, thresholds, etc.)
- **Update** product details (images, parameters, etc.)

---

## Prerequisites

### Python Version
- Python 3.7 or higher

### Dependencies

Install required packages:

```bash
python3 -m pip install requests urllib3
```

### Authentication

All scripts require iMatrix Cloud credentials:
- **Username**: Your iMatrix account email address
- **Password**: Your iMatrix account password

### API Environments

| Environment | API Base URL |
|-------------|--------------|
| Development (default) | `https://api-dev.imatrixsys.com/api/v1` |
| Production | `https://api.imatrixsys.com/api/v1` |

Use the `-prod` flag to target the production API.

---

## Scripts

### get_predefined_icons.py

Downloads all predefined sensor definitions (IDs 1-999) from the iMatrix API, saves their icons, and generates an interactive HTML catalog.

#### Features

- Enumerates all sensors from ID 1 to 999
- Downloads sensor icon images (SVG, PNG, JPG, GIF)
- Saves individual JSON files for each sensor
- Generates a responsive HTML page with all icons
- Interactive hover popup showing all sensor settings (2-second delay)
- Uses iMatrix brand color palette

#### Usage

```bash
# Basic usage (development API, prompts for password)
python3 get_predefined_icons.py -u user@example.com

# With password on command line
python3 get_predefined_icons.py -u user@example.com -p mypassword

# Use production API
python3 get_predefined_icons.py -u user@example.com -prod

# Verbose output
python3 get_predefined_icons.py -u user@example.com -v
```

#### Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `-u, --username` | Yes | iMatrix Cloud username (email) |
| `-p, --password` | No | Password (secure prompt if omitted) |
| `-prod, --production` | No | Use production API instead of development |
| `-v, --verbose` | No | Enable verbose output |

#### Output Files

| File | Description |
|------|-------------|
| `imatrix_predefined.html` | HTML page with all sensor icons |
| `sensor_metadata.json` | Combined metadata for all sensors |
| `icons/sensor_<id>.json` | Individual JSON file for each sensor |
| `icons/sensor_<id>.svg` | Downloaded icon for each sensor |
| `icons/placeholder.svg` | Placeholder for missing icons |

#### HTML Page Features

- **Header**: iMatrix logo and title
- **Grid Layout**: Responsive multi-column grid of sensor icons
- **Icon Cards**: Each card shows:
  - Sensor icon (100x100 pixels)
  - Label: `<id>:<name>` in 8pt font
- **Hover Popup**: After hovering 2 seconds, displays all sensor settings:
  - Sensor ID, Product ID, Platform ID
  - Name, Units, Data Type
  - Min/Max thresholds and warnings
  - Calibration references
  - Icon URL

#### Data Transformations

The following fields are converted from `0`/`1` to `false`/`true`:
- `minAdvisoryEnabled`
- `minWarningEnabled`
- `minAlarmEnabled`
- `maxAdvisoryEnabled`
- `maxWarningEnabled`
- `maxAlarmEnabled`

#### Example Output

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

### get_public_products.py

Downloads all public products from the iMatrix API, saves their images (icon, image, defaultImage), and generates an interactive HTML catalog.

#### Features

- Fetches all public products via `GET /products/public`
- Downloads three image types for each product (iconUrl, imageUrl, defaultImage)
- Saves individual JSON files for each product
- Fetches predefined sensors for each product via `GET /sensors/predefined/product/{productId}`
- Fetches default configs for each product via `GET /admin/products/configs/default/{id}`
- Generates a responsive HTML page with all products
- Interactive hover popup showing all product settings (2-second delay)
- Uses iMatrix brand color palette

#### New Features (v1.3.0)

- **Config-based sensor ordering**: Sensors are displayed in the exact order defined in the product's default configuration
- **Config match indicator**:
  - Green checkmark (✓) when all sensors match the default config
  - Red X (✗) when there's a mismatch (hover to see details)
- **Visible attribute**: Sensor popup shows visibility status (Visible/Hidden) from the config
- **Separate sensor displays**: Product sensors and predefined sensors shown in separate sections (no duplicates)
- **Favorites system**: Star/unstar products for quick filtering

#### Usage

```bash
# Basic usage (development API, prompts for password)
python3 get_public_products.py -u user@example.com

# With password on command line
python3 get_public_products.py -u user@example.com -p mypassword

# Use production API
python3 get_public_products.py -u user@example.com -prod

# Verbose output
python3 get_public_products.py -u user@example.com -v
```

#### Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `-u, --username` | Yes | iMatrix Cloud username (email) |
| `-p, --password` | No | Password (secure prompt if omitted) |
| `-prod, --production` | No | Use production API instead of development |
| `-v, --verbose` | No | Enable verbose output |

#### Output Files

| File | Description |
|------|-------------|
| `imatrix_public_products.html` | HTML page with all product cards |
| `product_metadata.json` | Combined metadata for all products |
| `products/product_<id>.json` | Individual JSON file for each product |
| `products/product_<id>_icon.{ext}` | Downloaded icon for each product |
| `products/product_<id>_image.{ext}` | Downloaded image for each product |
| `products/product_<id>_default.{ext}` | Downloaded default image for each product |
| `products/placeholder.svg` | Placeholder for missing images |

#### HTML Page Features

- **Header**: iMatrix logo and title
- **Stats Bar**: Total products, generation timestamp, favorites toggle
- **Grid Layout**: Responsive multi-column grid of product cards
- **Product Cards**: Each card shows:
  - Product icon (60x60 pixels in header)
  - Product name and ID
  - Config match indicator (green ✓ or red ✗) in top-right corner
  - Favorite star button
  - Three images side-by-side: Icon, Image, Default
  - Sensors section (first 5 with +N more indicator, excludes predefined)
  - Predefined Sensors section (first 5 with +N more indicator)
  - Sensor and control counts
  - Platform type badges (ble, wifi, etc.)
  - Organization badges (imatrix, agrowtronics, etc.)
- **Sensor Popup**: Click +N to see all sensors with:
  - Sensor icon, name, and ID
  - Visibility indicator (Visible/Hidden badge)
  - Sensors sorted by config order
- **Config Match Tooltip**: Hover over red X to see mismatch details
- **Hover Popup**: After hovering 2 seconds, displays all product settings
- **Favorites Filter**: Toggle to show only favorited products

#### Product Response Fields

```json
{
  "id": 12345,
  "organizationId": 1,
  "platformId": 1,
  "platformType": ["ble", "wifi"],
  "name": "Product Name",
  "shortName": "ProdName",
  "isPublished": true,
  "noControls": 2,
  "noSensors": 5,
  "imageUrl": "https://storage.googleapis.com/imatrix-files/...",
  "iconUrl": "https://storage.googleapis.com/imatrix-files/...",
  "defaultImage": "https://storage.googleapis.com/imatrix-files/...",
  "badge": ["imatrix"],
  "defaultFavorite1": 0,
  "defaultFavorite2": 0,
  "defaultFavorite3": 0,
  "controlSensorIds": [],
  "rssiUse": 0,
  "batteryUse": 0
}
```

#### Example Output

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

Fetching predefined sensors for 45 products...
  [==================================================] 100% (45/45)
Found predefined sensors for 38 products.

Fetching default configs for 45 products...
  [==================================================] 100% (45/45)
Found default configs for 42 products.

Fetching sensor details for 156 unique sensors...
  [==================================================] 100% (156/156)
Fetched details for 156 sensors.

Metadata saved to: /path/to/product_metadata.json

Generating HTML page...

============================================================
SUMMARY
============================================================
Total products found:    45
JSON files saved:        45 (products/product_<id>.json)
Images downloaded:       120
Images failed/missing:   15
Sensors fetched:         156
Predefined sensors:      89 refs across products
Default configs:         42 products with order/visibility
HTML output:             /path/to/imatrix_public_products.html
Linux URL:               file:///path/to/imatrix_public_products.html
Windows URL:             file:///U://path/to/imatrix_public_products.html
============================================================
```

---

### update_sensor.py

Updates a single sensor's icon and/or parameters via the iMatrix API.

#### Features

- Upload new icon image to iMatrix file storage
- Update any sensor parameter from a JSON file
- Supports all image formats (SVG, PNG, JPG, GIF, WebP)
- Merges JSON parameters with existing sensor data

#### Usage

```bash
# Update sensor icon only
python3 update_sensor.py -u user@example.com -s 42 -i new_icon.svg

# Update sensor parameters from JSON file
python3 update_sensor.py -u user@example.com -s 42 -j sensor_params.json

# Update both icon and parameters
python3 update_sensor.py -u user@example.com -s 42 -i new_icon.svg -j sensor_params.json

# Use production API
python3 update_sensor.py -u user@example.com -s 42 -i new_icon.svg -prod

# Verbose output (shows all data)
python3 update_sensor.py -u user@example.com -s 42 -j params.json -v
```

#### Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `-u, --username` | Yes | iMatrix Cloud username (email) |
| `-p, --password` | No | Password (secure prompt if omitted) |
| `-s, --sensor-id` | Yes | Sensor ID to update |
| `-i, --image` | No* | Path to image file for new icon |
| `-j, --json` | No* | Path to JSON file with parameters |
| `-prod, --production` | No | Use production API |
| `-v, --verbose` | No | Show detailed output |

*At least one of `-i` or `-j` must be provided.

#### JSON File Format

The JSON file should contain only the fields you want to update:

```json
{
  "name": "Temperature Sensor",
  "units": "Celsius",
  "defaultValue": 25,
  "minWarning": 0,
  "maxWarning": 100,
  "minWarningEnabled": true,
  "maxWarningEnabled": true
}
```

#### Supported Sensor Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Sensor display name |
| `units` | string | Unit of measurement |
| `unitsType` | string | Unit type category |
| `dataType` | string | Data type (IMX_UINT32, IMX_FLOAT, etc.) |
| `mode` | string | Sensor mode |
| `defaultValue` | number | Default value |
| `iconUrl` | string | URL to sensor icon (set automatically with -i) |
| `thresholdQualificationTime` | number | Time before threshold triggers |
| `minAdvisory` | number | Minimum advisory threshold |
| `minAdvisoryEnabled` | boolean | Enable minimum advisory |
| `minWarning` | number | Minimum warning threshold |
| `minWarningEnabled` | boolean | Enable minimum warning |
| `minAlarm` | number | Minimum alarm threshold |
| `minAlarmEnabled` | boolean | Enable minimum alarm |
| `maxAdvisory` | number | Maximum advisory threshold |
| `maxAdvisoryEnabled` | boolean | Enable maximum advisory |
| `maxWarning` | number | Maximum warning threshold |
| `maxWarningEnabled` | boolean | Enable maximum warning |
| `maxAlarm` | number | Maximum alarm threshold |
| `maxAlarmEnabled` | boolean | Enable maximum alarm |
| `minGraph` | number | Minimum graph scale |
| `maxGraph` | number | Maximum graph scale |
| `calibrationRef1` | number | Calibration reference 1 |
| `calibrationRef2` | number | Calibration reference 2 |
| `calibrationRef3` | number | Calibration reference 3 |

#### Workflow

1. **Login**: Authenticate with iMatrix API
2. **Fetch**: Get current sensor data via `GET /sensors/{id}`
3. **Upload Image** (if `-i` provided):
   - Upload file via `POST /files/`
   - Set returned URL as `iconUrl`
4. **Merge JSON** (if `-j` provided):
   - Load JSON file
   - Merge parameters into sensor data
5. **Update**: Send updated sensor via `PUT /sensors/{id}`

#### Example Output

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

---

### update_product.py

Updates a product's images (icon, image, defaultImage) and/or parameters via the iMatrix API.

#### Features

- Upload new icon image to iMatrix file storage (iconUrl)
- Upload new product image to iMatrix file storage (imageUrl)
- Upload new default image to iMatrix file storage (defaultImage)
- Update any product parameter from a JSON file
- Supports all image formats (SVG, PNG, JPG, GIF, WebP)
- Merges JSON parameters with existing product data

#### Usage

```bash
# Update product icon only
python3 update_product.py -u user@example.com -p 30604238 -i new_icon.svg

# Update product image
python3 update_product.py -u user@example.com -p 30604238 --image product_photo.jpg

# Update default image
python3 update_product.py -u user@example.com -p 30604238 --default-image default.jpg

# Update all three images at once
python3 update_product.py -u user@example.com -p 30604238 -i icon.svg --image photo.jpg --default-image default.jpg

# Update product parameters from JSON file
python3 update_product.py -u user@example.com -p 30604238 -j product_params.json

# Update images and parameters together
python3 update_product.py -u user@example.com -p 30604238 -i icon.svg -j params.json

# Use production API
python3 update_product.py -u user@example.com -p 30604238 -i icon.svg -prod

# Verbose output (shows all data)
python3 update_product.py -u user@example.com -p 30604238 -j params.json -v
```

#### Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `-u, --username` | Yes | iMatrix Cloud username (email) |
| `-pw, --password` | No | Password (secure prompt if omitted) |
| `-p, --product-id` | Yes | Product ID to update |
| `-i, --icon` | No* | Path to image file for product icon (iconUrl) |
| `--image` | No* | Path to image file for product image (imageUrl) |
| `--default-image` | No* | Path to image file for default image (defaultImage) |
| `-j, --json` | No* | Path to JSON file with parameters |
| `-prod, --production` | No | Use production API |
| `-v, --verbose` | No | Show detailed output |

*At least one of `-i`, `--image`, `--default-image`, or `-j` must be provided.

#### JSON File Format

The JSON file should contain only the fields you want to update:

```json
{
  "name": "My Product",
  "shortName": "MyProd",
  "noSensors": 5,
  "isPublished": true,
  "description": "Product description"
}
```

#### Product Image Fields

| Field | Flag | Description |
|-------|------|-------------|
| `iconUrl` | `-i, --icon` | Small icon representing the product |
| `imageUrl` | `--image` | Main product image |
| `defaultImage` | `--default-image` | Default image for product |

#### Workflow

1. **Login**: Authenticate with iMatrix API
2. **Fetch**: Get current product data via `GET /products/{id}`
3. **Upload Images** (for each image flag provided):
   - Upload file via `POST /files/`
   - Set returned URL to corresponding field
4. **Merge JSON** (if `-j` provided):
   - Load JSON file
   - Merge parameters into product data
5. **Update**: Send updated product via `PUT /products/{id}`

#### Example Output

```
============================================================
Update Product - iMatrix API
============================================================
Product ID: 30604238
Icon file: product_icon.svg
JSON file: product_params.json

Logging in to development iMatrix API...
Login successful.

Fetching product 30604238...
Found product: My Product

Uploading icon file...
  Uploading: product_icon.svg
  Uploaded successfully: https://storage.googleapis.com/imatrix-files/abc123.svg

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
  name: My Product
  shortName: MyProd
============================================================
```

---

## API Reference

### Endpoints Used

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Authenticate and get token |
| GET | `/sensors/{id}` | Get sensor details |
| PUT | `/sensors/{id}` | Update sensor |
| GET | `/sensors/predefined/product/{productId}` | Get predefined sensor IDs for a product |
| GET | `/products/public` | Get all public products |
| GET | `/products/{id}` | Get product details |
| PUT | `/products/{id}` | Update product |
| GET | `/admin/products/configs/default/{id}` | Get default config (order/visibility) for a product |
| POST | `/files/` | Upload file to storage |

### Default Config Response Format

The `/admin/products/configs/default/{id}` endpoint returns:

```json
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
```

The `order` array defines:
- **Sensor display order**: Sensors are shown in this exact sequence
- **Visibility**: Whether each sensor is visible or hidden in the UI

### Authentication

All API calls (except login) require the `x-auth-token` header:

```
x-auth-token: <token_from_login>
```

### Sensor Response Format

```json
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
  "iconUrl": "https://storage.googleapis.com/imatrix-files/...",
  "thresholdQualificationTime": 0,
  "minAdvisoryEnabled": false,
  "minAdvisory": 0,
  "minWarningEnabled": true,
  "minWarning": 0,
  "minAlarmEnabled": false,
  "minAlarm": 0,
  "maxAdvisoryEnabled": false,
  "maxAdvisory": 0,
  "maxWarningEnabled": true,
  "maxWarning": 100,
  "maxAlarmEnabled": false,
  "maxAlarm": 0,
  "maxGraph": 100,
  "minGraph": 0,
  "calibrationRef1": 0,
  "calibrationRef2": 0,
  "calibrationRef3": 0
}
```

---

## File Structure

After running `get_predefined_icons.py`:

```
tools/predfined/
├── get_predefined_icons.py    # Download sensors and catalog
├── get_public_products.py     # Download products and catalog
├── update_sensor.py           # Update individual sensors
├── update_product.py          # Update individual products
├── iMatrix_logo.jpg           # iMatrix logo for HTML pages
├── requirements.md            # Requirements document
├── README.md                  # This file
├── imatrix_predefined.html    # Generated sensor HTML catalog
├── imatrix_public_products.html # Generated product HTML catalog
├── sensor_metadata.json       # Combined sensor metadata
├── product_metadata.json      # Combined product metadata
├── icons/                     # Downloaded sensor icons and JSON
│   ├── placeholder.svg        # Placeholder for missing icons
│   ├── sensor_1.json          # Sensor 1 definition
│   ├── sensor_1.svg           # Sensor 1 icon
│   └── ...
└── products/                  # Downloaded product images and JSON
    ├── placeholder.svg        # Placeholder for missing images
    ├── product_123.json       # Product 123 definition
    ├── product_123_icon.svg   # Product 123 icon
    ├── product_123_image.jpg  # Product 123 image
    ├── product_123_default.jpg # Product 123 default image
    └── ...
```

---

## Troubleshooting

### Login Failed

```
Error: Login failed with status code 401
```

**Solution**: Verify your username and password are correct.

### Sensor Not Found

```
Error: Sensor 42 not found
```

**Solution**: The sensor ID doesn't exist. Use `get_predefined_icons.py` to see all available sensors.

### Product Not Found

```
Error: Product 30604238 not found
```

**Solution**: The product ID doesn't exist. Verify the product ID in the iMatrix Cloud dashboard.

### No Public Products Found

```
No public products found. Exiting.
```

**Solution**: There are no published products in the system, or you may not have permission to view them. Contact your administrator.

### SSL Certificate Warnings

The scripts disable SSL verification for development use. This is expected behavior for the development API.

### File Upload Failed

```
Error: Failed to upload image: Upload failed with status 403
```

**Solution**: Verify you have permission to upload files. Contact your administrator.

### Missing Icons

Some sensors may not have icons defined. These will use the placeholder icon in the HTML catalog.

### Rate Limiting

If you experience connection issues when running `get_predefined_icons.py`, the API may be rate limiting. Wait a few minutes and try again.

---

## iMatrix Color Palette

The HTML page uses the official iMatrix color palette:

| Color | Hex Code | Usage |
|-------|----------|-------|
| Primary Dark | #005C8C | Header, footer, accent |
| Primary | #0085B4 | Links, borders |
| Light Blue | #A8D2E3 | Card borders |
| Lighter Blue | #D8E9F0 | Backgrounds, hover |
| Near White | #F5F9FC | Page background |
| Text Dark | #121212 | Text |

---

## License

Copyright Sierra Telecom. All rights reserved.
