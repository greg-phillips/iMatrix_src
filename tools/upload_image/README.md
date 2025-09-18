# Image Upload Tools

## Overview

The `upload_image` directory contains tools for uploading and managing image files in the iMatrix Cloud storage system. These tools handle icons, product images, and other visual assets used throughout the iMatrix platform.

## Tools

### upload_image.py

**Purpose:** Upload image files to iMatrix Cloud storage with registry management

**Features:**
- Supports multiple image formats (PNG, JPG, GIF, SVG, WebP)
- File size validation (max 10MB)
- MIME type detection and validation
- JSON registry tracking of all uploads
- Secure authentication with password prompt
- Progress reporting for large uploads
- URL generation for uploaded images

## Installation

### Prerequisites
- Python 3.6 or higher
- pip package manager

### Dependencies
```bash
python3 -m pip install requests urllib3
```

## Usage

### Basic Command Structure
```bash
python3 upload_image.py -u <email> -f <image_file>
```

### Required Arguments
- `-u, --username`: iMatrix Cloud username (email)
- `-f, --file`: Image file to upload

### Optional Arguments
- `-p, --password`: Password (secure prompt if omitted)
- `--description`: Image description for registry
- `--category`: Image category (icon, product, background)
- `--pro`: Use production API (default: development)

## Examples

### Upload Device Icon
```bash
python3 upload_image.py -u user@example.com -f device_icon.png
```

### Upload Product Image with Description
```bash
python3 upload_image.py -u user@example.com -f product.jpg --description "HM Truck Product Image"
```

### Upload SVG Icon with Category
```bash
python3 upload_image.py -u user@example.com -f sensor_icon.svg --category icon
```

### Batch Upload Multiple Images
```bash
#!/bin/bash
USERNAME="user@example.com"

for image in *.png; do
    echo "Uploading $image..."
    python3 upload_image.py -u "$USERNAME" -f "$image" --category icon
    sleep 1  # Avoid rate limiting
done
```

## Supported File Formats

### Image Types
- **PNG**: `.png` - Recommended for icons and graphics
- **JPEG**: `.jpg`, `.jpeg` - Best for photos and complex images
- **GIF**: `.gif` - Supports animation
- **SVG**: `.svg` - Vector graphics, scalable
- **WebP**: `.webp` - Modern format with compression

### File Size Limits
- **Maximum size**: 10MB per file
- **Recommended size**: Under 1MB for web usage
- **Icon dimensions**: 64x64 to 512x512 pixels
- **Product images**: 800x600 to 1920x1080 pixels

## Registry Management

### Image Registry File
The tool maintains a JSON registry at `upload_image/image_uploads.json`:

```json
{
  "uploads": [
    {
      "filename": "device_icon.png",
      "url": "https://storage.googleapis.com/imatrix-files/uuid.png",
      "upload_time": "2025-01-17T10:30:00Z",
      "file_size": 15234,
      "mime_type": "image/png",
      "description": "Device icon for HM Truck",
      "category": "icon"
    }
  ],
  "total_uploads": 1,
  "last_updated": "2025-01-17T10:30:00Z"
}
```

### Registry Features
- **Upload tracking**: Complete history of all uploads
- **URL management**: Direct links to uploaded images
- **Metadata storage**: File info, descriptions, categories
- **Search capability**: Find images by name or category
- **Size tracking**: Monitor storage usage

## API Integration

### Endpoints Used
- **Authentication**: `POST /login`
- **File Upload**: `POST /files`

### Upload Process
1. **File validation**: Check format, size, and type
2. **Authentication**: Login and get API token
3. **Upload**: POST file as multipart/form-data
4. **Registry update**: Add entry with URL and metadata
5. **Confirmation**: Display upload URL and details

### Response Format
```json
{
  "url": "https://storage.googleapis.com/imatrix-files/uuid.png",
  "fileId": "12345",
  "uploadTime": "2025-01-17T10:30:00Z"
}
```

## Image Usage in iMatrix

### Icon URLs
Uploaded images can be used in:
- **Sensor definitions**: Icon URLs for sensor display
- **Product configurations**: Product images and icons
- **Dashboard displays**: Custom graphics and logos
- **Device interfaces**: Status indicators and branding

### URL Integration
```json
{
  "id": 509,
  "name": "MPGe",
  "iconUrl": "https://storage.googleapis.com/imatrix-files/mpge-icon.svg"
}
```

## Troubleshooting

### Common Issues

#### File Format Not Supported
- Check file extension is in supported list
- Verify file is not corrupted
- Use standard image editing software to convert format

#### File Too Large
- **Resize images**: Use image editing software
- **Compress**: Reduce quality for JPEGs
- **Convert format**: PNG to JPEG for photos
- **Optimize**: Remove metadata and unnecessary data

#### Upload Failed
- **Check connection**: Verify internet connectivity
- **API status**: Ensure iMatrix API is accessible
- **Authentication**: Verify credentials are correct
- **File permissions**: Ensure file is readable

#### Registry Issues
- **Permission denied**: Check write permissions in upload_image directory
- **Corrupted registry**: Delete image_uploads.json to reset
- **Missing entries**: Registry may be out of sync

### Debug Mode

#### Verbose Upload
```bash
# See detailed upload information
python3 upload_image.py -u user@example.com -f image.png --verbose
```

#### Test File Validation
```bash
# Check file without uploading
python3 upload_image.py -u user@example.com -f image.png --validate-only
```

## Best Practices

### Image Optimization
- **Icons**: Use PNG or SVG formats
- **Photos**: Use JPEG with 80-90% quality
- **Graphics**: Use PNG for transparency
- **Vector graphics**: Use SVG for scalability

### File Organization
```
images/
├── icons/          # Small PNG/SVG icons
├── products/       # Product photos and images
├── backgrounds/    # Background images and textures
└── logos/          # Company and brand logos
```

### Naming Conventions
- **Icons**: `{sensor_name}_icon.png`
- **Products**: `{product_name}_image.jpg`
- **Logos**: `{company}_logo.svg`
- **Use descriptive names**: Avoid generic names like "image1.png"

## Related Tools

### Integration Tools
- **[upload_internal_sensor.py](../upload_internal/)**: Use uploaded icons in sensor definitions
- **[create_tire_sensors.py](../create_tire_sensors.py)**: Bulk sensor creation with icon assignment

### Workflow Integration
1. **Prepare Images**: Optimize and organize image files
2. **Upload**: Use `upload_image.py` to get URLs
3. **Registry**: Check `image_uploads.json` for URLs
4. **Configure**: Use URLs in sensor definitions or product configs
5. **Deploy**: Update devices with new image references

## Advanced Usage

### Automated Image Processing
```bash
#!/bin/bash

# Batch upload with automatic categorization
for icon in icons/*.png; do
    python3 upload_image.py -u user@example.com -f "$icon" --category icon
done

for product in products/*.jpg; do
    python3 upload_image.py -u user@example.com -f "$product" --category product
done
```

### Registry Management
```python
#!/usr/bin/env python3
import json

# Read registry
with open('image_uploads.json', 'r') as f:
    registry = json.load(f)

# Find images by category
icons = [img for img in registry['uploads'] if img.get('category') == 'icon']
print(f"Found {len(icons)} icon uploads")

# Get URLs for specific images
for img in icons:
    print(f"{img['filename']}: {img['url']}")
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-17 | Initial documentation |
|  |  | - Complete usage guide |
|  |  | - Registry management documentation |
|  |  | - Integration workflow examples |
|  |  | - Troubleshooting guide |

---

*Part of the iMatrix Tools Suite - See [main README](../README.md) for complete tool overview*