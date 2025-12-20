#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_product.py - Update product details via the iMatrix API

Updates a product's images (icon, image, defaultImage) and/or parameters.
If image files are provided, they are first uploaded to the iMatrix file system,
then the product's URL fields are updated to point to the uploaded files.

Usage:
    # Update product icon only
    python3 update_product.py -u <email> -p <id> -i <icon_file>

    # Update product image
    python3 update_product.py -u <email> -p <id> --image <image_file>

    # Update default image
    python3 update_product.py -u <email> -p <id> --default-image <image_file>

    # Update all three images
    python3 update_product.py -u <email> -p <id> -i icon.svg --image photo.jpg --default-image default.jpg

    # Update product parameters from JSON file
    python3 update_product.py -u <email> -p <id> -j product_params.json

    # Update images and parameters together
    python3 update_product.py -u <email> -p <id> -i icon.svg -j params.json

    # Use production API
    python3 update_product.py -u <email> -p <id> -i icon.svg -prod

Dependencies:
    python3 -m pip install requests urllib3
"""

import argparse
import requests
import json
import sys
import os
import getpass
import urllib3
from typing import Optional, Tuple

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_api_base_url(use_production: bool = False) -> str:
    """Get API base URL based on environment selection."""
    if use_production:
        return "https://api.imatrixsys.com/api/v1"
    else:
        return "https://api-dev.imatrixsys.com/api/v1"


def login_to_imatrix(email: str, password: str, use_production: bool = False) -> str:
    """
    Authenticate with the iMatrix API and return the auth token.

    Args:
        email: User's email address
        password: User's password
        use_production: Use production API instead of development

    Returns:
        Authentication token string

    Raises:
        SystemExit: If login fails
    """
    base_url = get_api_base_url(use_production)
    url = f"{base_url}/login"

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    payload = {
        'email': email,
        'password': password
    }

    environment = "production" if use_production else "development"
    print(f"Logging in to {environment} iMatrix API...")

    try:
        response = requests.post(url, headers=headers,
                                data=json.dumps(payload), verify=False)

        if response.status_code == 200:
            token = response.json().get('token')
            if token:
                print("Login successful.")
                return token
            else:
                print("Error: Token not found in response.")
                sys.exit(1)
        else:
            print(f"Error: Login failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"Error: Network error during login: {e}")
        sys.exit(1)


def get_product(product_id: int, token: str, base_url: str) -> Optional[dict]:
    """
    Fetch product details for a specific product ID.

    Args:
        product_id: Product ID to fetch
        token: Authentication token
        base_url: API base URL

    Returns:
        Product dictionary or None if not found
    """
    url = f"{base_url}/products/{product_id}"

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.get(url, timeout=30, verify=False, headers=headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"Error: Product {product_id} not found")
            return None
        else:
            print(f"Error: Failed to get product {product_id}: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"Error: Failed to get product {product_id}: {e}")
        return None


def upload_file(file_path: str, token: str, base_url: str) -> Tuple[bool, str]:
    """
    Upload a file to the iMatrix file system.

    Args:
        file_path: Path to the file to upload
        token: Authentication token
        base_url: API base URL

    Returns:
        Tuple of (success, file_url or error_message)
    """
    url = f"{base_url}/files/"

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    # Determine content type based on file extension
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        '.svg': 'image/svg+xml',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    content_type = content_types.get(ext, 'application/octet-stream')

    filename = os.path.basename(file_path)

    print(f"  Uploading: {filename}")

    try:
        with open(file_path, 'rb') as f:
            files = {
                'file': (filename, f, content_type)
            }
            response = requests.post(url, headers=headers, files=files,
                                    verify=False, timeout=60)

        if response.status_code in [200, 201]:
            result = response.json()
            # The API should return the URL of the uploaded file
            file_url = result.get('url') or result.get('fileUrl') or result.get('path')
            if file_url:
                print(f"  Uploaded successfully: {file_url}")
                return True, file_url
            else:
                # Try to construct URL if we have an ID
                file_id = result.get('id') or result.get('fileId')
                if file_id:
                    file_url = f"https://storage.googleapis.com/imatrix-files/{file_id}"
                    print(f"  Constructed URL: {file_url}")
                    return True, file_url
                print(f"  Upload response: {json.dumps(result, indent=2)}")
                return False, "Could not determine uploaded file URL from response"
        else:
            return False, f"Upload failed with status {response.status_code}: {response.text}"

    except FileNotFoundError:
        return False, f"File not found: {file_path}"
    except Exception as e:
        return False, f"Upload error: {e}"


def update_product(product_id: int, product_data: dict, token: str, base_url: str) -> Tuple[bool, str]:
    """
    Update a product via the API.

    Args:
        product_id: Product ID to update
        product_data: Updated product data
        token: Authentication token
        base_url: API base URL

    Returns:
        Tuple of (success, message)
    """
    url = f"{base_url}/products/{product_id}"

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.put(url, headers=headers,
                               data=json.dumps(product_data), verify=False, timeout=30)

        if response.status_code in [200, 201, 204]:
            return True, "Product updated successfully"
        else:
            return False, f"Update failed with status {response.status_code}: {response.text}"

    except Exception as e:
        return False, f"Update error: {e}"


def load_json_file(file_path: str) -> Tuple[bool, dict]:
    """
    Load and parse a JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Tuple of (success, data or error dict)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, data
    except FileNotFoundError:
        return False, {'error': f"File not found: {file_path}"}
    except json.JSONDecodeError as e:
        return False, {'error': f"Invalid JSON in {file_path}: {e}"}
    except Exception as e:
        return False, {'error': f"Error reading {file_path}: {e}"}


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Update product details via the iMatrix API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update product icon only
  %(prog)s -u user@example.com -p 30604238 -i new_icon.svg

  # Update product image
  %(prog)s -u user@example.com -p 30604238 --image product_photo.jpg

  # Update default image
  %(prog)s -u user@example.com -p 30604238 --default-image default.jpg

  # Update all three images at once
  %(prog)s -u user@example.com -p 30604238 -i icon.svg --image photo.jpg --default-image default.jpg

  # Update product parameters from JSON
  %(prog)s -u user@example.com -p 30604238 -j product_params.json

  # Update images and parameters together
  %(prog)s -u user@example.com -p 30604238 -i icon.svg -j params.json

  # Use production API
  %(prog)s -u user@example.com -p 30604238 -i icon.svg -prod

JSON file format:
  The JSON file should contain the product fields to update, e.g.:
  {
    "name": "My Product",
    "shortName": "MyProd",
    "noSensors": 5,
    "isPublished": true
  }
        """
    )

    parser.add_argument('-u', '--username', required=True,
                       help='iMatrix Cloud username (email)')
    parser.add_argument('-pw', '--password',
                       help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-p', '--product-id', type=int, required=True,
                       help='Product ID to update (required)')
    parser.add_argument('-i', '--icon',
                       help='Path to image file to upload as product icon (iconUrl)')
    parser.add_argument('--image',
                       help='Path to image file to upload as product image (imageUrl)')
    parser.add_argument('--default-image',
                       help='Path to image file to upload as default image (defaultImage)')
    parser.add_argument('-j', '--json',
                       help='Path to JSON file with product parameters to update')
    parser.add_argument('-prod', '--production', action='store_true',
                       help='Use production API (default is development)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed output')

    args = parser.parse_args()

    # Validate that at least one update option is provided
    if not args.icon and not args.image and not args.default_image and not args.json:
        parser.error("At least one of -i (icon), --image, --default-image, or -j (json) must be provided")

    # Validate files exist before proceeding
    files_to_check = [
        (args.icon, "Icon file"),
        (args.image, "Image file"),
        (args.default_image, "Default image file"),
        (args.json, "JSON file")
    ]

    for file_path, file_desc in files_to_check:
        if file_path and not os.path.isfile(file_path):
            print(f"Error: {file_desc} not found: {file_path}")
            sys.exit(1)

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")

    print("=" * 60)
    print("Update Product - iMatrix API")
    print("=" * 60)
    print(f"Product ID: {args.product_id}")
    if args.icon:
        print(f"Icon file: {args.icon}")
    if args.image:
        print(f"Image file: {args.image}")
    if args.default_image:
        print(f"Default image file: {args.default_image}")
    if args.json:
        print(f"JSON file: {args.json}")
    print()

    # Login
    token = login_to_imatrix(args.username, password, args.production)
    base_url = get_api_base_url(args.production)

    # Get current product data
    print(f"\nFetching product {args.product_id}...")
    product = get_product(args.product_id, token, base_url)

    if not product:
        print("Error: Could not retrieve product. Exiting.")
        sys.exit(1)

    print(f"Found product: {product.get('name', 'Unknown')}")

    if args.verbose:
        print(f"\nCurrent product data:")
        print(json.dumps(product, indent=2))

    # Prepare update data (start with current product)
    update_data = product.copy()

    # Track what was updated for summary
    updates_made = []

    # Handle icon upload
    if args.icon:
        print(f"\nUploading icon file...")
        success, result = upload_file(args.icon, token, base_url)

        if success:
            update_data['iconUrl'] = result
            updates_made.append(('iconUrl', result))
        else:
            print(f"Error: Failed to upload icon: {result}")
            sys.exit(1)

    # Handle image upload
    if args.image:
        print(f"\nUploading image file...")
        success, result = upload_file(args.image, token, base_url)

        if success:
            update_data['imageUrl'] = result
            updates_made.append(('imageUrl', result))
        else:
            print(f"Error: Failed to upload image: {result}")
            sys.exit(1)

    # Handle default image upload
    if args.default_image:
        print(f"\nUploading default image file...")
        success, result = upload_file(args.default_image, token, base_url)

        if success:
            update_data['defaultImage'] = result
            updates_made.append(('defaultImage', result))
        else:
            print(f"Error: Failed to upload default image: {result}")
            sys.exit(1)

    # Handle JSON file
    if args.json:
        print(f"\nLoading JSON parameters...")
        success, json_data = load_json_file(args.json)

        if success:
            # Merge JSON data into update_data
            for key, value in json_data.items():
                if key != 'id':  # Don't allow changing the ID
                    update_data[key] = value
                    updates_made.append((key, value))
                    if args.verbose:
                        print(f"  Setting {key} = {value}")
            print(f"Loaded {len(json_data)} parameters from JSON file")
        else:
            print(f"Error: {json_data.get('error', 'Unknown error')}")
            sys.exit(1)

    # Update the product
    print(f"\nUpdating product {args.product_id}...")

    if args.verbose:
        print("Update data:")
        print(json.dumps(update_data, indent=2))

    success, message = update_product(args.product_id, update_data, token, base_url)

    if success:
        print(f"\nSuccess: {message}")
    else:
        print(f"\nError: {message}")
        sys.exit(1)

    # Summary
    print()
    print("=" * 60)
    print("UPDATE COMPLETE")
    print("=" * 60)
    print(f"Product ID:   {args.product_id}")
    print(f"Product Name: {update_data.get('name', 'Unknown')}")
    print(f"Short Name:   {update_data.get('shortName', 'Unknown')}")
    print()
    print("Updates applied:")
    for field, value in updates_made:
        # Truncate long URLs for display
        display_value = value if len(str(value)) < 50 else str(value)[:47] + "..."
        print(f"  {field}: {display_value}")
    print("=" * 60)


if __name__ == "__main__":
    main()
