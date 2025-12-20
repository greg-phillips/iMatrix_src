#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_defaults.py - Fix default sensor icon URLs and normalize boolean fields via API

Connects to the iMatrix API and for each sensor (IDs 1-999):
1. Replaces the default placeholder icon URL with the correct Sensor General icon
2. Converts boolean fields from 0/1 to false/true
3. Updates the sensor via the API

Usage:
    python3 fix_defaults.py -u <email>

    # With password on command line
    python3 fix_defaults.py -u <email> -p <password>

    # Production API
    python3 fix_defaults.py -u <email> -prod

    # Dry run (show changes without updating)
    python3 fix_defaults.py -u <email> --dry-run

    # Verbose mode
    python3 fix_defaults.py -u <email> -v

Dependencies:
    python3 -m pip install requests urllib3
"""

import argparse
import requests
import json
import sys
import getpass
import urllib3

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Icon URL to replace (the default placeholder)
OLD_ICON_URL = "https://storage.googleapis.com/imatrix-files/59cb3544-78d1-45e1-94ec-6d9762c90258.svg"

# Replacement icon URL (Sensor General)
NEW_ICON_URL = "https://storage.googleapis.com/imatrix-files/a3e5d012-93f4-4c35-9827-b52a8afaac93-Sensor%20General.svg"

# Boolean fields that should be converted from 0/1 to false/true
BOOL_FIELDS = [
    'minAdvisoryEnabled',
    'minWarningEnabled',
    'minAlarmEnabled',
    'maxAdvisoryEnabled',
    'maxWarningEnabled',
    'maxAlarmEnabled'
]


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


def get_sensor(sensor_id: int, token: str, base_url: str) -> dict:
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
        else:
            return None

    except Exception:
        return None


def update_sensor(sensor_id: int, sensor_data: dict, token: str, base_url: str) -> bool:
    """
    Update a sensor via the API.

    Args:
        sensor_id: Sensor ID to update
        sensor_data: Updated sensor data
        token: Authentication token
        base_url: API base URL

    Returns:
        True if successful, False otherwise
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
            return True
        else:
            return False

    except Exception:
        return False


def check_and_fix_sensor(sensor: dict) -> tuple:
    """
    Check if a sensor needs fixing and return the fixed version.

    Args:
        sensor: Sensor dictionary to check

    Returns:
        Tuple of (needs_update, fixed_sensor, changes) where:
        - needs_update: Boolean indicating if changes are needed
        - fixed_sensor: The fixed sensor dictionary
        - changes: List of change descriptions
    """
    changes = []
    fixed_sensor = sensor.copy()

    # Check and fix icon URL
    if fixed_sensor.get('iconUrl') == OLD_ICON_URL:
        fixed_sensor['iconUrl'] = NEW_ICON_URL
        changes.append("iconUrl: default -> Sensor General")

    # Convert boolean fields from 0/1 to false/true
    for field in BOOL_FIELDS:
        if field in fixed_sensor:
            if fixed_sensor[field] == 0:
                fixed_sensor[field] = False
                changes.append(f"{field}: 0 -> false")
            elif fixed_sensor[field] == 1:
                fixed_sensor[field] = True
                changes.append(f"{field}: 1 -> true")

    return len(changes) > 0, fixed_sensor, changes


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fix default sensor icon URLs and normalize boolean fields via iMatrix API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default (development API)
  %(prog)s -u user@example.com

  # Production API
  %(prog)s -u user@example.com -prod

  # Dry run (preview changes)
  %(prog)s -u user@example.com --dry-run

  # Verbose output
  %(prog)s -u user@example.com -v
        """
    )

    parser.add_argument('-u', '--username', required=True,
                       help='iMatrix Cloud username (email)')
    parser.add_argument('-p', '--password',
                       help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-prod', '--production', action='store_true',
                       help='Use production API (default is development)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed output for each sensor')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without updating API')

    args = parser.parse_args()

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")

    print("=" * 60)
    print("Fix Defaults - Sensor API Updater")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN - no changes will be made to the API")

    print()

    # Login
    token = login_to_imatrix(args.username, password, args.production)
    base_url = get_api_base_url(args.production)

    # Statistics
    stats = {
        'total_sensors': 0,
        'sensors_updated': 0,
        'icon_urls_fixed': 0,
        'booleans_converted': 0,
        'update_errors': 0
    }

    total = 999
    print(f"\nScanning sensors 1-{total}...")

    for sensor_id in range(1, total + 1):
        # Progress bar
        progress = int((sensor_id / total) * 50)
        bar = "=" * progress + "-" * (50 - progress)
        percent = int((sensor_id / total) * 100)
        print(f"\r  [{bar}] {percent}% ({sensor_id}/{total})", end="", flush=True)

        # Get sensor
        sensor = get_sensor(sensor_id, token, base_url)

        if sensor:
            stats['total_sensors'] += 1

            # Check if fixes are needed
            needs_update, fixed_sensor, changes = check_and_fix_sensor(sensor)

            if needs_update:
                # Count changes
                for change in changes:
                    if 'iconUrl' in change:
                        stats['icon_urls_fixed'] += 1
                    else:
                        stats['booleans_converted'] += 1

                if args.verbose:
                    print(f"\n  Sensor {sensor_id} ({sensor.get('name', 'Unknown')}):")
                    for change in changes:
                        print(f"    - {change}")

                # Update via API (unless dry run)
                if not args.dry_run:
                    success = update_sensor(sensor_id, fixed_sensor, token, base_url)
                    if success:
                        stats['sensors_updated'] += 1
                        if args.verbose:
                            print(f"    Updated successfully")
                    else:
                        stats['update_errors'] += 1
                        print(f"\n  Error: Failed to update sensor {sensor_id}")
                else:
                    stats['sensors_updated'] += 1  # Count as "would be updated"

    print()  # New line after progress bar

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total sensors found:    {stats['total_sensors']}")
    print(f"Sensors {'to update' if args.dry_run else 'updated'}:      {stats['sensors_updated']}")
    print(f"Icon URLs fixed:        {stats['icon_urls_fixed']}")
    print(f"Booleans converted:     {stats['booleans_converted']}")
    if stats['update_errors'] > 0:
        print(f"Update errors:          {stats['update_errors']}")
    print("=" * 60)

    if args.dry_run and stats['sensors_updated'] > 0:
        print("\nRun without --dry-run to apply changes to the API.")


if __name__ == "__main__":
    main()
