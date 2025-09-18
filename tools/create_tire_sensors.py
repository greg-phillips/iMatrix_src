#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_tire_sensors.py
Creates predefined tire sensors in the iMatrix API.

This script authenticates with the iMatrix API and creates predefined sensors
for tire monitoring systems. It can process sensors from a data file or 
create individual sensors via command line.

Usage:
    python3 create_tire_sensors.py -u <username> -f <data_file> [options]

Example:
    python3 create_tire_sensors.py -u user@example.com -f tire_sensors_data.txt
    python3 create_tire_sensors.py -u user@example.com -f tire_sensors_data.txt --dry-run
    python3 create_tire_sensors.py -u user@example.com -f tire_sensors_data.txt --start-id 200 --end-id 250

Dependencies:
    python3 -m pip install requests urllib3
"""
import argparse
import requests
import sys
import json
import urllib3
import getpass
import re
import time
from datetime import datetime

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_api_base_url(use_development=False):
    """Get API base URL based on environment selection."""
    if use_development:
        return "https://api-dev.imatrixsys.com/api/v1"
    else:
        return "https://api.imatrixsys.com/api/v1"

# Sensor type mappings
SENSOR_MAPPINGS = {
    "pressure": {"units": "Pa", "dataType": "IMX_FLOAT", "minGraph": 0, "maxGraph": 1000000},
    "temperature": {"units": "°C", "dataType": "IMX_FLOAT", "minGraph": -40, "maxGraph": 150},
    "load": {"units": "kg", "dataType": "IMX_FLOAT", "minGraph": 0, "maxGraph": 5000},
    "toe": {"units": "°", "dataType": "IMX_FLOAT", "minGraph": -10, "maxGraph": 10},
    "camber": {"units": "°", "dataType": "IMX_FLOAT", "minGraph": -10, "maxGraph": 10},
    "wear": {"units": "%", "dataType": "IMX_FLOAT", "minGraph": 0, "maxGraph": 100},
    "lug_nut": {"units": "%", "dataType": "IMX_FLOAT", "minGraph": 0, "maxGraph": 100}
}

# Position mappings
POSITION_MAPPINGS = {
    "LO": "Left Outer",
    "LI": "Left Inner",
    "RI": "Right Inner",
    "RO": "Right Outer"
}


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


def parse_sensor_line(line):
    """
    Parse X-macro line to extract sensor information.
    
    Args:
        line (str): X-macro line like X(TIRE_A1_LO_PRESSURE, 200, "Tire_A1_LO_Pressure_Pascal")
        
    Returns:
        dict: Parsed sensor info with id, name, type, axle, position
        None: If line cannot be parsed
    """
    # Pattern to match X(TIRE_A#_POS_TYPE, ID, "Description")
    pattern = r'X\(TIRE_A(\d+)_([A-Z]+)_([A-Z_]+),\s*(\d+),\s*"([^"]+)"\)'
    match = re.match(pattern, line.strip())
    
    if not match:
        return None
    
    axle_num = match.group(1)
    position_code = match.group(2)
    sensor_type = match.group(3).lower()
    sensor_id = int(match.group(4))
    description = match.group(5)
    
    # Get position name
    position = POSITION_MAPPINGS.get(position_code, position_code)
    
    # Format sensor name
    sensor_name = f"Tire A{axle_num} {position} {sensor_type.replace('_', ' ').title()}"
    
    return {
        'id': sensor_id,
        'name': sensor_name,
        'type': sensor_type,
        'axle': axle_num,
        'position': position_code,
        'position_name': position,
        'description': description
    }


def create_sensor_payload(sensor_info, icon_base_url=None):
    """
    Create API payload for a sensor.
    
    Args:
        sensor_info (dict): Parsed sensor information
        icon_base_url (str): Base URL for icon files
        
    Returns:
        dict: API payload for creating sensor
    """
    # Get sensor type mapping
    sensor_mapping = SENSOR_MAPPINGS.get(sensor_info['type'], SENSOR_MAPPINGS['pressure'])
    
    # Default icon URL if not provided
    if not icon_base_url:
        icon_base_url = "https://storage.googleapis.com/imatrix-files/"
    
    # Map sensor types to icon names
    icon_mapping = {
        'pressure': '59cb3544-78d1-45e1-94ec-6d9762c90258.svg',
        'temperature': '59cb3544-78d1-45e1-94ec-6d9762c90259.svg',
        'load': '59cb3544-78d1-45e1-94ec-6d9762c90260.svg',
        'toe': '59cb3544-78d1-45e1-94ec-6d9762c90261.svg',
        'camber': '59cb3544-78d1-45e1-94ec-6d9762c90262.svg',
        'wear': '59cb3544-78d1-45e1-94ec-6d9762c90263.svg',
        'lug_nut': '59cb3544-78d1-45e1-94ec-6d9762c90264.svg'
    }
    
    icon_file = icon_mapping.get(sensor_info['type'], icon_mapping['pressure'])
    icon_url = f"{icon_base_url}{icon_file}"
    
    payload = {
        "id": sensor_info['id'],
        "type": 1,  # Predefined sensor type
        "name": sensor_info['name'],
        "units": sensor_mapping['units'],
        "unitsType": "IMX_NATIVE",
        "dataType": sensor_mapping['dataType'],
        "defaultValue": 0,
        "mode": "scalar",
        "states": 0,
        "iconUrl": icon_url,
        "thresholdQualificationTime": 0,
        "minAdvisoryEnabled": false,
        "minAdvisory": 0,
        "minWarningEnabled": false,
        "minWarning": 0,
        "minAlarmEnabled": false,
        "minAlarm": 0,
        "maxAdvisoryEnabled": false,
        "maxAdvisory": 0,
        "maxWarningEnabled": false,
        "maxWarning": 0,
        "maxAlarmEnabled": false,
        "maxAlarm": 0,
        "maxGraph": sensor_mapping['maxGraph'],
        "minGraph": sensor_mapping['minGraph'],
        "calibrationMode": 0,
        "calibrateValue1": 0,
        "calibrateValue2": 0,
        "calibrateValue3": 0,
        "calibrationRef1": 0,
        "calibrationRef2": 0,
        "calibrationRef3": 0
    }
    
    return payload


def create_sensor(sensor_info, token, icon_base_url=None, dry_run=False, use_development=False):
    """
    Create a single sensor in the iMatrix API.

    Args:
        sensor_info (dict): Parsed sensor information
        token (str): Authentication token
        icon_base_url (str): Base URL for icon files
        dry_run (bool): If True, only print what would be done
        use_development (bool): Use development API instead of production

    Returns:
        tuple: (success: bool, message: str)
    """
    payload = create_sensor_payload(sensor_info, icon_base_url)

    if dry_run:
        print(f"[DRY RUN] Would create sensor: {sensor_info['name']} (ID: {sensor_info['id']})")
        return True, "Dry run"

    base_url = get_api_base_url(use_development)
    url = f"{base_url}/sensors/predefined"
    headers = {
        'accept': 'application/json',
        'x-auth-token': token,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
        
        if response.status_code in [200, 201]:
            return True, f"Created sensor {sensor_info['id']}: {sensor_info['name']}"
        elif response.status_code == 409:
            return True, f"Sensor {sensor_info['id']} already exists"
        else:
            error_msg = f"Failed with status {response.status_code}: {response.text}"
            return False, error_msg
    except Exception as e:
        return False, f"Exception: {str(e)}"


def process_sensors_file(filename, token, start_id=None, end_id=None, icon_base_url=None, dry_run=False, use_development=False):
    """
    Process sensors from a data file.
    
    Args:
        filename (str): Path to sensor data file
        token (str): Authentication token
        start_id (int): Optional starting sensor ID
        end_id (int): Optional ending sensor ID
        icon_base_url (str): Base URL for icon files
        dry_run (bool): If True, only print what would be done
        use_development (bool): Use development API instead of production

    Returns:
        dict: Summary of results
    """
    sensors = []
    
    # Read and parse file
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('/*'):
                    continue
                    
                sensor_info = parse_sensor_line(line)
                if sensor_info:
                    # Apply ID filters if specified
                    if start_id and sensor_info['id'] < start_id:
                        continue
                    if end_id and sensor_info['id'] > end_id:
                        continue
                    sensors.append(sensor_info)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)
    
    if not sensors:
        print("No sensors found to process.")
        return {'total': 0, 'created': 0, 'skipped': 0, 'failed': 0}
    
    # Process sensors
    print(f"\nCreating Tire Sensors")
    print("=" * 50)
    print(f"Total sensors: {len(sensors)}")
    print("Processing...\n")
    
    created = 0
    skipped = 0
    failed = 0
    failed_sensors = []
    
    start_time = time.time()
    
    for i, sensor in enumerate(sensors):
        # Progress bar
        progress = (i + 1) / len(sensors)
        bar_length = 40
        filled = int(bar_length * progress)
        bar = "■" * filled + "□" * (bar_length - filled)
        
        sys.stdout.write(f"\r[{bar}] {int(progress*100)}% | {i+1}/{len(sensors)} | "
                        f"Created: {created} | Skipped: {skipped} | Failed: {failed}")
        sys.stdout.flush()
        
        # Create sensor
        success, message = create_sensor(sensor, token, icon_base_url, dry_run, use_development)
        
        if success:
            if "already exists" in message:
                skipped += 1
            else:
                created += 1
        else:
            failed += 1
            failed_sensors.append({
                'sensor': sensor,
                'error': message
            })
        
        # Rate limiting - small delay between requests
        if not dry_run:
            time.sleep(0.5)
    
    elapsed = time.time() - start_time
    
    # Final summary
    print(f"\n\nSummary:")
    print(f"✅ Successfully created {created} sensors")
    print(f"ℹ️  Skipped {skipped} existing sensors")
    print(f"❌ Failed {failed} sensors")
    print(f"\nTime elapsed: {int(elapsed//60)}m {int(elapsed%60)}s")
    
    # Save failed sensors if any
    if failed_sensors and not dry_run:
        failed_file = "failed_sensors.json"
        with open(failed_file, 'w') as f:
            json.dump(failed_sensors, f, indent=2)
        print(f"\nFailed sensors saved to: {failed_file}")
    
    return {
        'total': len(sensors),
        'created': created,
        'skipped': skipped,
        'failed': failed
    }


def main():
    """
    Main function to handle command line arguments and orchestrate sensor creation.
    """
    parser = argparse.ArgumentParser(
        description="Create predefined tire sensors in the iMatrix API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Create all sensors from file:
    python3 create_tire_sensors.py -u user@example.com -f tire_sensors_data.txt
    
  Dry run to preview:
    python3 create_tire_sensors.py -u user@example.com -f tire_sensors_data.txt --dry-run
    
  Create specific range:
    python3 create_tire_sensors.py -u user@example.com -f tire_sensors_data.txt --start-id 200 --end-id 250
    
  With custom icon URL:
    python3 create_tire_sensors.py -u user@example.com -f tire_sensors_data.txt --icon-base-url "https://example.com/icons/"
        """
    )
    
    parser.add_argument('-u', '--username', required=True, 
                       help='iMatrix Cloud username (email)')
    parser.add_argument('-p', '--password', 
                       help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-f', '--file', required=True,
                       help='Sensor data file to process')
    parser.add_argument('--start-id', type=int,
                       help='Start processing from this sensor ID')
    parser.add_argument('--end-id', type=int,
                       help='Stop processing at this sensor ID')
    parser.add_argument('--icon-base-url',
                       help='Base URL for sensor icon files')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview what would be done without making changes')
    parser.add_argument('-dev', '--dev', action='store_true',
                       help='Use development API endpoint instead of production')

    args = parser.parse_args()
    
    # Get password securely if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")
    
    environment = "development" if args.dev else "production"
    print(f"Starting tire sensor creation process (using {environment} API)...")
    print(f"Data file: {args.file}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")

    # Authenticate
    token = login_to_imatrix(args.username, password, args.dev)
    
    # Process sensors
    results = process_sensors_file(
        args.file,
        token,
        start_id=args.start_id,
        end_id=args.end_id,
        icon_base_url=args.icon_base_url,
        dry_run=args.dry_run,
        use_development=args.dev
    )
    
    if results['failed'] > 0 and not args.dry_run:
        print("\n⚠️  Some sensors failed to create. Check failed_sensors.json for details.")
        sys.exit(1)
    else:
        print("\n✅ Sensor creation completed successfully.")


if __name__ == "__main__":
    main()