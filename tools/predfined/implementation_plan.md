# Implementation Plan: iMatrix Predefined Sensor Tools

**Date**: 2025-12-13
**Last Updated**: 2025-12-13
**Author**: Claude Code
**Status**: Completed
**Version**: 1.3.0

## Scripts

| Script | Output File | Status |
|--------|-------------|--------|
| `get_predefined_icons.py` | `imatrix_predefined.html` | Completed |
| `get_public_products.py` | `imatrix_public_products.html` | Completed |
| `update_sensor.py` | N/A | Completed |
| `update_product.py` | N/A | Completed |

---

## Version 1.3.0 Features (get_public_products.py)

### New API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /sensors/predefined/product/{productId}` | Fetch predefined sensor IDs for each product |
| `GET /admin/products/configs/default/{id}` | Fetch default config with sensor order and visibility |

### New HTML Features

1. **Config-based Sensor Ordering**
   - Sensors displayed in exact order from product's default config
   - Sensors not in config appear at end, sorted by ID

2. **Config Match Indicator**
   - Green checkmark (✓) when sensors match config exactly
   - Red X (✗) when mismatch detected
   - Hover tooltip shows mismatch details (missing/extra sensor IDs)

3. **Visibility Attribute in Popup**
   - Each sensor shows "Visible" or "Hidden" badge
   - Color-coded: green for visible, red for hidden

4. **Separate Sensor Displays**
   - "Sensors" section excludes predefined sensors
   - "Predefined Sensors" section shows only predefined
   - Config match checks full set (sensors + predefined)

5. **Favorites System**
   - Star button to favorite/unfavorite products
   - Filter toggle to show only favorites
   - Persisted in localStorage

---

## Summary of Requirements (Original)

| Requirement | Detail |
|-------------|--------|
| API Default | Development (`-dev` flag defaults to dev, add `-prod` for production) |
| Sensor Range | IDs 1-999 |
| Missing Icons | Show placeholder/error icon |
| Table Sort | By sensor ID |
| Metadata | Store id, name, units |
| Rate Limiting | None |
| Error Handling | Log message, continue processing |
| Layout | Multi-column responsive grid |
| Icon Size | 100x100 pixels |
| Header Format | `<id>:<name>` in 8pt font |
| Colors | iMatrix palette (#005C8C, #0085B4, #A8D2E3, #D8E9F0, #F5F9FC, #121212) |

---

## iMatrix Color Palette

- **Primary Dark**: #005C8C
- **Primary**: #0085B4
- **Light Blue**: #A8D2E3
- **Lighter Blue**: #D8E9F0
- **Near White**: #F5F9FC
- **Text/Dark**: #121212

---

## Implementation Steps

### 1. Create Script Structure
- Command-line argument parsing (username, password, -dev/-prod flags)
- Login function (reuse pattern from `get_sensor_data.py`)
- Disable SSL warnings for development

### 2. Sensor Enumeration Loop
- Iterate sensor IDs 1-999
- GET `/api/v1/sensors/{id}` for each
- Skip 404s (sensor doesn't exist)
- Collect valid sensors with metadata (id, name, units, iconUrl)
- Show progress bar during iteration

### 3. Icon Downloading
- Create `icons/` subdirectory if not exists
- Download each iconUrl (SVG or PNG)
- Save with filename `sensor_{id}.{ext}`
- Create inline SVG placeholder for empty/failed downloads
- Track failures for reporting

### 4. HTML Generation
- Header with iMatrix logo (left) and title "iMatrix Internal Sensor Icons"
- Multi-column responsive CSS grid (auto-fit columns)
- Each cell contains:
  - Icon image (100x100 pixels, scaled)
  - Header text: `{id}:{name}` in 8pt font
- Apply iMatrix color palette to styling
- Sort sensors by ID before rendering

### 5. Output
- Save as `imatrix_predefined.html`
- Print file URL (`file:///path/to/imatrix_predefined.html`)
- Summary statistics (total sensors found, icons downloaded, failures)

---

## File Structure After Execution

```
tools/predfined/
├── get_predefined_icons.py    # New script
├── iMatrix_logo.jpg           # Existing
├── requirements.md            # Existing
├── implementation_plan.md     # This file
├── imatrix_predefined.html    # Generated output
└── icons/                     # Created subdirectory
    ├── sensor_1.svg
    ├── sensor_2.png
    └── ...
```

---

## Dependencies

```
python3 -m pip install requests urllib3
```

---

## Usage

```bash
# Default (development API)
python3 get_predefined_icons.py -u <email>

# Production API
python3 get_predefined_icons.py -u <email> -prod

# With password on command line
python3 get_predefined_icons.py -u <email> -p <password>

# Verbose mode
python3 get_predefined_icons.py -u <email> -v
```
