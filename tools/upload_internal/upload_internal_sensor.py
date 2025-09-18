#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_internal_sensor.py
Uploads internal sensor definitions to the iMatrix Cloud system.

This script authenticates with the iMatrix API and creates predefined internal
sensors used for device management. It reads the sensor definition from a JSON
file and posts it to the API.

Usage:
    python3 upload_internal_sensor.py -u <username> -f <json_file> [options]

Example:
    python3 upload_internal_sensor.py -u user@example.com -f sensor_def.json
    python3 upload_internal_sensor.py -u user@example.com -f sensor_def.json --validate-only

Dependencies:
    python3 -m pip install requests urllib3
"""
import argparse
import requests
import sys
import json
import urllib3
import getpass
import os
from datetime import datetime

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_api_base_url(use_development=False):
    """Get API base URL based on environment selection."""
    if use_development:
        return "https://api-dev.imatrixsys.com/api/v1"
    else:
        return "https://api.imatrixsys.com/api/v1"

# Required fields in sensor payload
REQUIRED_FIELDS = [
    'id', 'type', 'name', 'units', 'unitsType', 'dataType', 
    'mode', 'states', 'defaultValue'
]

# Valid data types
VALID_DATA_TYPES = [
    'IMX_INT8', 'IMX_UINT8', 'IMX_INT16', 'IMX_UINT16', 
    'IMX_INT32', 'IMX_UINT32', 'IMX_FLOAT', 'IMX_STRING'
]

# Valid units types
VALID_UNITS_TYPES = ['IMX_NATIVE', 'IMX_METRIC', 'IMX_IMPERIAL']

# Valid modes
VALID_MODES = ['scalar', 'array', 'binary']


def login_to_imatrix(email, password, use_development=False):
    """
    Authenticate with the iMatrix API and retrieve an authentication token.

    Args:
        email (str): User's email address for authentication
        password (str): User's password
        use_development (bool): Use development API instead of production

    Returns:
        str: Authentication token for subsequent API calls

    Raises:
        SystemExit: If login fails or token is not received
    """
    base_url = get_api_base_url(use_development)
    url = f"{base_url}/login"
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    payload = {
        'email': email,
        'password': password
    }
    print("Logging in to iMatrix API...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
        if response.status_code == 200:
            token = response.json().get('token')
            if token:
                print("✅ Login successful.")
                return token
            else:
                print("❌ Token not found in response.")
                sys.exit(1)
        else:
            print(f"❌ Login failed with status code {response.status_code}: {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error during login request: {e}")
        sys.exit(1)


def load_json_file(file_path):
    """
    Load and parse JSON sensor definition from file.
    
    Args:
        file_path (str): Path to JSON file
        
    Returns:
        dict: Parsed JSON data
        
    Raises:
        SystemExit: If file cannot be read or parsed
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    if not os.path.isfile(file_path):
        print(f"❌ Path is not a file: {file_path}")
        sys.exit(1)
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            print(f"✅ Loaded JSON file: {file_path}")
            return data
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)


def validate_sensor_payload(payload):
    """
    Validate the sensor payload for required fields and valid values.
    
    Args:
        payload (dict): Sensor definition payload
        
    Returns:
        tuple: (is_valid, error_messages)
    """
    errors = []
    
    # Check if payload is a dictionary
    if not isinstance(payload, dict):
        return False, ["Payload must be a JSON object"]
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"Missing required field: {field}")
    
    # Validate specific fields if present
    if 'id' in payload:
        if not isinstance(payload['id'], int) or payload['id'] <= 0:
            errors.append("'id' must be a positive integer")
    
    if 'type' in payload:
        if payload['type'] not in [1, 2]:  # 1=predefined, 2=custom
            errors.append("'type' must be 1 (predefined) or 2 (custom)")
    
    if 'dataType' in payload:
        if payload['dataType'] not in VALID_DATA_TYPES:
            errors.append(f"'dataType' must be one of: {', '.join(VALID_DATA_TYPES)}")
    
    if 'unitsType' in payload:
        if payload['unitsType'] not in VALID_UNITS_TYPES:
            errors.append(f"'unitsType' must be one of: {', '.join(VALID_UNITS_TYPES)}")
    
    if 'mode' in payload:
        if payload['mode'] not in VALID_MODES:
            errors.append(f"'mode' must be one of: {', '.join(VALID_MODES)}")
    
    if 'states' in payload:
        if not isinstance(payload['states'], int) or payload['states'] < 0:
            errors.append("'states' must be a non-negative integer")
    
    # Check threshold consistency
    threshold_fields = [
        ('minAdvisoryEnabled', 'minAdvisory'),
        ('minWarningEnabled', 'minWarning'),
        ('minAlarmEnabled', 'minAlarm'),
        ('maxAdvisoryEnabled', 'maxAdvisory'),
        ('maxWarningEnabled', 'maxWarning'),
        ('maxAlarmEnabled', 'maxAlarm')
    ]
    
    for enabled_field, value_field in threshold_fields:
        if payload.get(enabled_field, False) and value_field not in payload:
            errors.append(f"'{value_field}' is required when '{enabled_field}' is true")
    
    return len(errors) == 0, errors


def create_sensor(payload, token, dry_run=False, use_development=False):
    """
    Create a sensor in the iMatrix API.

    Args:
        payload (dict): Sensor definition payload
        token (str): Authentication token
        dry_run (bool): If True, validate only without creating
        use_development (bool): Use development API instead of production

    Returns:
        tuple: (success: bool, message: str, response_data: dict or None)
    """
    # Validate payload first
    is_valid, errors = validate_sensor_payload(payload)
    if not is_valid:
        error_msg = "Validation errors:\n" + "\n".join(f"  - {e}" for e in errors)
        return False, error_msg, None

    if dry_run:
        return True, "Validation passed (dry run mode)", None

    base_url = get_api_base_url(use_development)
    url = f"{base_url}/sensors/predefined"
    headers = {
        'accept': 'application/json',
        'x-auth-token': token,
        'Content-Type': 'application/json'
    }
    
    sensor_id = payload.get('id', 'unknown')
    sensor_name = payload.get('name', 'unknown')
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
        
        if response.status_code in [200, 201]:
            try:
                response_data = response.json()
            except:
                response_data = None
            return True, f"Created sensor {sensor_id}: {sensor_name}", response_data
        elif response.status_code == 409:
            return True, f"Sensor {sensor_id} already exists", None
        else:
            error_msg = f"Failed with status {response.status_code}: {response.text}"
            return False, error_msg, None
    except Exception as e:
        return False, f"Exception: {str(e)}", None


def format_sensor_summary(payload):
    """
    Format a summary of the sensor for display.
    
    Args:
        payload (dict): Sensor definition
        
    Returns:
        str: Formatted summary
    """
    summary = []
    summary.append(f"  ID: {payload.get('id', 'N/A')}")
    summary.append(f"  Name: {payload.get('name', 'N/A')}")
    summary.append(f"  Units: {payload.get('units', 'N/A')}")
    summary.append(f"  Data Type: {payload.get('dataType', 'N/A')}")
    summary.append(f"  Mode: {payload.get('mode', 'N/A')}")
    
    if payload.get('iconUrl'):
        summary.append(f"  Icon URL: {payload.get('iconUrl')}")
    
    if payload.get('minGraph') is not None or payload.get('maxGraph') is not None:
        summary.append(f"  Graph Range: {payload.get('minGraph', 'N/A')} to {payload.get('maxGraph', 'N/A')}")
    
    return "\n".join(summary)


def main():
    """
    Main function to handle command line arguments and orchestrate sensor creation.
    """
    parser = argparse.ArgumentParser(
        description="Upload internal sensor definitions to the iMatrix API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Upload sensor definition:
    python3 upload_internal_sensor.py -u user@example.com -f sensor_def.json
    
  Validate only (no upload):
    python3 upload_internal_sensor.py -u user@example.com -f sensor_def.json --validate-only
    
  With password provided:
    python3 upload_internal_sensor.py -u user@example.com -p mypassword -f sensor_def.json
    
Sample JSON file format:
{
  "id": 100,
  "type": 1,
  "name": "System Temperature",
  "units": "°C",
  "unitsType": "IMX_METRIC",
  "dataType": "IMX_FLOAT",
  "defaultValue": 0,
  "mode": "scalar",
  "states": 0,
  "iconUrl": "https://example.com/temp-icon.svg",
  "minGraph": -40,
  "maxGraph": 125,
  "maxWarningEnabled": true,
  "maxWarning": 85,
  "maxAlarmEnabled": true,
  "maxAlarm": 95
}
        """
    )
    
    parser.add_argument('-u', '--username', required=True, 
                       help='iMatrix Cloud username (email)')
    parser.add_argument('-p', '--password', 
                       help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-f', '--file', required=True,
                       help='JSON file containing sensor definition')
    parser.add_argument('--validate-only', action='store_true',
                       help='Validate the JSON payload without uploading')
    parser.add_argument('-dev', '--dev', action='store_true',
                       help='Use development API endpoint instead of production')

    args = parser.parse_args()
    
    environment = "development" if args.dev else "production"
    print(f"\n📊 iMatrix Internal Sensor Upload Tool (using {environment} API)")
    print("=" * 50)
    
    # Load sensor definition
    payload = load_json_file(args.file)
    
    # Display sensor summary
    print("\nSensor Definition:")
    print(format_sensor_summary(payload))
    print()
    
    # Validate only mode
    if args.validate_only:
        is_valid, errors = validate_sensor_payload(payload)
        if is_valid:
            print("✅ Validation passed - sensor definition is valid")
            sys.exit(0)
        else:
            print("❌ Validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
    
    # Get password securely if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")
    
    # Authenticate
    token = login_to_imatrix(args.username, password, args.dev)

    # Create sensor
    print("\nCreating sensor...")
    success, message, response_data = create_sensor(payload, token, dry_run=False, use_development=args.dev)
    
    # Display results
    print("\n" + "=" * 50)
    if success:
        print(f"✅ {message}")
        if response_data:
            print("\nAPI Response:")
            print(json.dumps(response_data, indent=2))
    else:
        print(f"❌ {message}")
        sys.exit(1)
    
    print("=" * 50)


if __name__ == "__main__":
    main()