#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_sensor.py - Update sensor details via the iMatrix API

Updates a sensor's icon and/or parameters. If an image file is provided,
it is first uploaded to the iMatrix file system, then the sensor's iconUrl
is updated to point to the uploaded file.

Usage:
    # Update sensor icon
    python3 update_sensor.py -u <email> -s <sensor_id> -i <image_file>

    # Update sensor parameters from JSON
    python3 update_sensor.py -u <email> -s <sensor_id> -j <json_file>

    # Update both icon and parameters
    python3 update_sensor.py -u <email> -s <sensor_id> -i <image_file> -j <json_file>

    # Use production API
    python3 update_sensor.py -u <email> -s <sensor_id> -i <image_file> -prod

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


def get_sensor(sensor_id: int, token: str, base_url: str) -> Optional[dict]:
    """
    Fetch sensor details for a specific sensor ID.

    Args:
        sensor_id: Sensor ID to fetch
        token: Authentication token
        base_url: API base URL

    Returns:
        Sensor dictionary or None if not found
    """
    url = f"{base_url}/sensors/{sensor_id}"

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.get(url, timeout=30, verify=False, headers=headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"Error: Sensor {sensor_id} not found")
            return None
        else:
            print(f"Error: Failed to get sensor {sensor_id}: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"Error: Failed to get sensor {sensor_id}: {e}")
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

    print(f"Uploading file: {filename}")

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
                print(f"File uploaded successfully: {file_url}")
                return True, file_url
            else:
                # If URL not in expected fields, check the full response
                print(f"Upload response: {json.dumps(result, indent=2)}")
                # Try to construct URL if we have an ID
                file_id = result.get('id') or result.get('fileId')
                if file_id:
                    file_url = f"https://storage.googleapis.com/imatrix-files/{file_id}"
                    print(f"Constructed file URL: {file_url}")
                    return True, file_url
                return False, "Could not determine uploaded file URL from response"
        else:
            return False, f"Upload failed with status {response.status_code}: {response.text}"

    except FileNotFoundError:
        return False, f"File not found: {file_path}"
    except Exception as e:
        return False, f"Upload error: {e}"


def update_sensor(sensor_id: int, sensor_data: dict, token: str, base_url: str) -> Tuple[bool, str]:
    """
    Update a sensor via the API.

    Args:
        sensor_id: Sensor ID to update
        sensor_data: Updated sensor data
        token: Authentication token
        base_url: API base URL

    Returns:
        Tuple of (success, message)
    """
    url = f"{base_url}/sensors/{sensor_id}"

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.put(url, headers=headers,
                               data=json.dumps(sensor_data), verify=False, timeout=30)

        if response.status_code in [200, 201, 204]:
            return True, "Sensor updated successfully"
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
        description="Update sensor details via the iMatrix API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update sensor icon only
  %(prog)s -u user@example.com -s 42 -i new_icon.svg

  # Update sensor parameters from JSON
  %(prog)s -u user@example.com -s 42 -j sensor_params.json

  # Update both icon and parameters
  %(prog)s -u user@example.com -s 42 -i new_icon.svg -j sensor_params.json

  # Use production API
  %(prog)s -u user@example.com -s 42 -i new_icon.svg -prod

JSON file format:
  The JSON file should contain the sensor fields to update, e.g.:
  {
    "name": "My Sensor",
    "units": "Celsius",
    "minWarning": 10,
    "maxWarning": 50
  }
        """
    )

    parser.add_argument('-u', '--username', required=True,
                       help='iMatrix Cloud username (email)')
    parser.add_argument('-p', '--password',
                       help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-s', '--sensor-id', type=int, required=True,
                       help='Sensor ID to update (required)')
    parser.add_argument('-i', '--image',
                       help='Path to image file to upload as sensor icon')
    parser.add_argument('-j', '--json',
                       help='Path to JSON file with sensor parameters to update')
    parser.add_argument('-prod', '--production', action='store_true',
                       help='Use production API (default is development)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed output')

    args = parser.parse_args()

    # Validate that at least one of -i or -j is provided
    if not args.image and not args.json:
        parser.error("At least one of -i (image) or -j (json) must be provided")

    # Validate files exist before proceeding
    if args.image and not os.path.isfile(args.image):
        print(f"Error: Image file not found: {args.image}")
        sys.exit(1)

    if args.json and not os.path.isfile(args.json):
        print(f"Error: JSON file not found: {args.json}")
        sys.exit(1)

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")

    print("=" * 60)
    print("Update Sensor - iMatrix API")
    print("=" * 60)
    print(f"Sensor ID: {args.sensor_id}")
    if args.image:
        print(f"Image file: {args.image}")
    if args.json:
        print(f"JSON file: {args.json}")
    print()

    # Login
    token = login_to_imatrix(args.username, password, args.production)
    base_url = get_api_base_url(args.production)

    # Get current sensor data
    print(f"\nFetching sensor {args.sensor_id}...")
    sensor = get_sensor(args.sensor_id, token, base_url)

    if not sensor:
        print("Error: Could not retrieve sensor. Exiting.")
        sys.exit(1)

    print(f"Found sensor: {sensor.get('name', 'Unknown')}")

    if args.verbose:
        print(f"Current sensor data:")
        print(json.dumps(sensor, indent=2))

    # Prepare update data (start with current sensor)
    update_data = sensor.copy()

    # Handle image upload
    if args.image:
        print(f"\nUploading image file...")
        success, result = upload_file(args.image, token, base_url)

        if success:
            update_data['iconUrl'] = result
            print(f"Icon URL set to: {result}")
        else:
            print(f"Error: Failed to upload image: {result}")
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
                    if args.verbose:
                        print(f"  Setting {key} = {value}")
            print(f"Loaded {len(json_data)} parameters from JSON file")
        else:
            print(f"Error: {json_data.get('error', 'Unknown error')}")
            sys.exit(1)

    # Update the sensor
    print(f"\nUpdating sensor {args.sensor_id}...")

    if args.verbose:
        print("Update data:")
        print(json.dumps(update_data, indent=2))

    success, message = update_sensor(args.sensor_id, update_data, token, base_url)

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
    print(f"Sensor ID:    {args.sensor_id}")
    print(f"Sensor Name:  {update_data.get('name', 'Unknown')}")
    if args.image:
        print(f"New Icon URL: {update_data.get('iconUrl', 'N/A')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
