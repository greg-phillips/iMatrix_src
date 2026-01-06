#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_loc.py - iMatrix Location Data Download Tool v2.0.0

Downloads latitude and longitude history from the iMatrix API for a given serial number and time range,
matches timestamps, and outputs a GeoJSON file suitable for Google Maps.

Usage:
    # Default interactive mode (complete workflow - devices, dates):
    python3 get_loc.py -u <email>

    # Skip to date entry (with known device):
    python3 get_loc.py -s <serial> -u <email>

    # Direct mode (no interaction needed):
    python3 get_loc.py -s <serial> -ts <start> -te <end> -u <email>

Date Formats Supported:
    • Press Enter for last 24 hours (default)
    • Negative number: -60 (last 60 minutes from now)
    • Epoch milliseconds: 1736899200000
    • Date only: 01/15/25 (midnight to midnight)
    • Date and time: 01/15/25 14:30

Dependencies:
    python3 -m pip install requests urllib3
"""
import argparse
import requests
import sys
import json
from collections import defaultdict
import urllib3
import getpass
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_api_base_url(use_development=False):
    """Get API base URL based on environment selection."""
    if use_development:
        return "https://api-dev.imatrixsys.com/api/v1"
    else:
        return "https://api.imatrixsys.com/api/v1"


def login_to_imatrix(email, password, use_development=False):
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


def get_user_devices(token: str, verbose: bool = False, use_development: bool = False) -> List[Dict]:
    """
    Fetch all devices/things for the authenticated user.

    Args:
        token: Authentication token
        verbose: Print verbose output
        use_development: Use development API instead of production

    Returns:
        List of device dictionaries

    Raises:
        SystemExit: If API request fails
    """
    base_url = get_api_base_url(use_development)
    url = f"{base_url}/things/?per_page=100"

    if verbose:
        print(f"📡 User Devices URL: {url}")

    print("🔍 Fetching your devices...")

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.get(url, timeout=30, verify=False, headers=headers)

        if response.status_code == 200:
            data = response.json()
            devices = data.get('list', [])
            total = data.get('total', len(devices))

            print(f"✅ Found {len(devices)} devices in your account" +
                  (f" (out of {total} total)" if total != len(devices) else ""))

            if len(devices) == 0:
                print("❌ No devices found in your account")
                print("   Please check that you have devices registered")
                sys.exit(1)

            # Sort devices by name for consistent display
            devices.sort(key=lambda d: d.get('name', '').lower())

            return devices

        elif response.status_code == 403:
            print("❌ Access denied to user devices")
            print("   Please check your account permissions")
            sys.exit(1)
        else:
            print(f"❌ Failed to fetch user devices")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            sys.exit(1)

    except requests.exceptions.Timeout:
        print("❌ Request timeout while fetching user devices")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while fetching user devices: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error while fetching user devices: {e}")
        sys.exit(1)


def get_device_by_serial(serial: str, devices: List[Dict]) -> Dict:
    """
    Find device in device list by serial number.

    Args:
        serial: Device serial number as string
        devices: List of device dictionaries

    Returns:
        Device dictionary if found

    Raises:
        SystemExit: If device not found
    """
    device = next((d for d in devices if str(d['sn']) == serial), None)

    if not device:
        print(f"❌ Device {serial} not found in your account")
        print(f"   Available devices: {', '.join(str(d['sn']) for d in devices[:5])}")
        if len(devices) > 5:
            print(f"   ... and {len(devices) - 5} more")
        sys.exit(1)

    return device


def display_device_list(devices: List[Dict]) -> None:
    """
    Display devices in 4-column format with selection numbers.

    Args:
        devices: List of device dictionaries
    """
    print(f"\n{'=' * 109}")
    print(f"{'USER DEVICES':^109}")
    print(f"{'(' + str(len(devices)) + ' found)':^109}")
    print(f"{'=' * 109}")

    # Header
    print(f"{'#':>3} {'Device Name':<64} {'Serial Number':<12} {'Product ID':<12} {'Version':<10}")
    print("-" * 109)

    # Device list
    for i, device in enumerate(devices, 1):
        name = device.get('name', 'Unknown')
        serial = device.get('sn', 0)
        product_id = device.get('productId', 0)
        version = device.get('currentVersion') or 'Unknown'

        # Truncate long names
        if len(name) > 64:
            name = name[:61] + "..."

        print(f"[{i:2}] {name:<64} {serial:<12} {product_id:<12} {version:<10}")


def select_device_interactive(devices: List[Dict]) -> str:
    """
    Interactive device selection from list.

    Args:
        devices: List of device dictionaries

    Returns:
        Selected device serial number as string

    Raises:
        SystemExit: If user cancels or invalid selection
    """
    display_device_list(devices)

    print("-" * 109)
    print(f"Select a device [1-{len(devices)}], or 'q' to quit:")

    while True:
        try:
            selection = input("Enter your choice: ").strip().lower()

            if selection == 'q' or selection == 'quit':
                print("👋 Cancelled by user")
                sys.exit(0)

            # Try to parse as integer
            choice = int(selection)

            if 1 <= choice <= len(devices):
                selected_device = devices[choice - 1]
                serial = str(selected_device['sn'])
                name = selected_device.get('name', f'Device {serial}')

                print(f"✅ Selected: {name} (Serial: {serial})")
                return serial
            else:
                print(f"❌ Please enter a number between 1 and {len(devices)}")

        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            sys.exit(0)


def print_device_details(device: Dict) -> None:
    """
    Display detailed information for a selected device.

    Args:
        device: Device information dictionary
    """
    print(f"\n📱 Device Details:")
    print(f"   Name:            {device.get('name', 'Unknown')}")
    print(f"   Serial Number:   {device.get('sn', 'Unknown')}")
    print(f"   MAC Address:     {device.get('mac', 'Unknown')}")
    print(f"   Product ID:      {device.get('productId', 'Unknown')}")
    print(f"   Group ID:        {device.get('groupId', 'Unknown')}")
    print(f"   Organization:    {device.get('organizationId', 'Unknown')}")
    print(f"   Version:         {device.get('currentVersion') or 'Unknown'}")

    # Format creation date
    created_at = device.get('createdAt')
    if created_at:
        created_dt = datetime.fromtimestamp(created_at / 1000.0)
        print(f"   Created:         {created_dt.isoformat()}Z")

    print()


def format_timestamp(epoch_ms: int) -> str:
    """
    Convert epoch milliseconds to ISO 8601 formatted string.

    Args:
        epoch_ms: Epoch time in milliseconds

    Returns:
        ISO 8601 formatted datetime string
    """
    try:
        dt = datetime.fromtimestamp(epoch_ms / 1000.0)
        return dt.isoformat() + 'Z'
    except Exception:
        return str(epoch_ms)


def parse_flexible_datetime(input_str: str, default_to_end_of_day: bool = False) -> datetime:
    """
    Parse date input in multiple formats.

    Args:
        input_str: User input string
        default_to_end_of_day: If True and no time specified, use 23:59:59

    Returns:
        datetime object

    Raises:
        ValueError: If format is not recognized
    """
    input_str = input_str.strip()

    # Try epoch milliseconds first
    if input_str.isdigit() and len(input_str) >= 10:
        try:
            if len(input_str) == 13:  # Milliseconds
                return datetime.fromtimestamp(int(input_str) / 1000.0)
            elif len(input_str) == 10:  # Seconds
                return datetime.fromtimestamp(int(input_str))
        except (ValueError, OSError):
            pass

    # Try mm/dd/yy format with optional time
    try:
        # Handle mm/dd/yy hh:mm format
        if ' ' in input_str:
            date_part, time_part = input_str.split(' ', 1)

            # Parse date part (mm/dd/yy)
            month, day, year = date_part.split('/')
            month = int(month)
            day = int(day)
            year = int(year)

            # Convert 2-digit year to 4-digit
            if year < 50:
                year += 2000  # 00-49 = 2000-2049
            elif year < 100:
                year += 1900  # 50-99 = 1950-1999

            # Parse time part (hh:mm)
            hour, minute = time_part.split(':')
            hour = int(hour)
            minute = int(minute)

            return datetime(year, month, day, hour, minute, 0)

        else:
            # Date only - mm/dd/yy format
            month, day, year = input_str.split('/')
            month = int(month)
            day = int(day)
            year = int(year)

            # Convert 2-digit year to 4-digit
            if year < 50:
                year += 2000  # 00-49 = 2000-2049
            elif year < 100:
                year += 1900  # 50-99 = 1950-1999

            if default_to_end_of_day:
                return datetime(year, month, day, 23, 59, 59)
            else:
                return datetime(year, month, day, 0, 0, 0)

    except (ValueError, IndexError):
        raise ValueError(f"Invalid date format: {input_str}")


def parse_date_input(date_str: str, default_to_end_of_day: bool = False) -> int:
    """
    Parse user date input in multiple formats to epoch milliseconds.

    Args:
        date_str: User input string
        default_to_end_of_day: If True and no time specified, use end of day

    Returns:
        Epoch milliseconds as integer

    Raises:
        ValueError: If format is not recognized
    """
    try:
        dt = parse_flexible_datetime(date_str, default_to_end_of_day)
        return int(dt.timestamp() * 1000)
    except ValueError as e:
        raise ValueError(f"Could not parse date '{date_str}': {e}")


def prompt_for_date_range() -> Tuple[int, int]:
    """
    Interactive prompt for start and end dates with flexible format support.

    Returns:
        Tuple of (start_ms, end_ms) as integers

    Raises:
        SystemExit: If user cancels or repeated invalid input
    """
    print("\n📅 Date/time range required for location data download")
    print("\nSupported formats:")
    print("  • Press Enter for last 24 hours (default)")
    print("  • Negative number: -60 (last 60 minutes from now)")
    print("  • Epoch milliseconds: 1736899200000")
    print("  • Date only: 01/15/25 (assumes midnight to midnight)")
    print("  • Date and time: 01/15/25 14:30")
    print("  • Enter 'q' to quit\n")

    # Get start date
    start_attempts = 0
    while start_attempts < 3:
        try:
            start_input = input("📅 Enter start date/time (or Enter for last 24h, or -N for last N minutes): ").strip()

            if start_input.lower() in ['q', 'quit']:
                print("👋 Cancelled by user")
                sys.exit(0)

            # Handle blank input - use last 24 hours
            if start_input == '':
                end_ms = int(datetime.now().timestamp() * 1000)
                start_ms = end_ms - (24 * 60 * 60 * 1000)  # 24 hours in ms
                print(f"✅ Using last 24 hours:")
                print(f"   Start: {format_timestamp(start_ms)}")
                print(f"   End:   {format_timestamp(end_ms)}")
                duration_hours = 24.0
                print(f"📊 Date range: {duration_hours:.1f} hours")
                return start_ms, end_ms

            # Handle negative number input - relative minutes from now
            if start_input.startswith('-'):
                try:
                    minutes = int(start_input)  # Will be negative
                    if minutes >= 0:
                        raise ValueError("Must be a negative number")
                    minutes = abs(minutes)
                    end_ms = int(datetime.now().timestamp() * 1000)
                    start_ms = end_ms - (minutes * 60 * 1000)  # minutes to ms
                    print(f"✅ Using last {minutes} minutes:")
                    print(f"   Start: {format_timestamp(start_ms)}")
                    print(f"   End:   {format_timestamp(end_ms)}")
                    duration_hours = minutes / 60.0
                    if duration_hours >= 1:
                        print(f"📊 Date range: {duration_hours:.1f} hours")
                    else:
                        print(f"📊 Date range: {minutes} minutes")
                    return start_ms, end_ms
                except ValueError:
                    raise ValueError(f"Invalid relative time: {start_input}. Use -N where N is minutes (e.g., -60)")

            start_ms = parse_date_input(start_input, default_to_end_of_day=False)
            start_formatted = format_timestamp(start_ms)
            print(f"✅ Start: {start_formatted}")
            break

        except ValueError as e:
            start_attempts += 1
            print(f"❌ {e}")
            if start_attempts < 3:
                print("Please try again with format: mm/dd/yy hh:mm or epoch milliseconds")
            else:
                print("Too many invalid attempts")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            sys.exit(0)

    # Get end date
    end_attempts = 0
    while end_attempts < 3:
        try:
            end_input = input("📅 Enter end date/time: ").strip()

            if end_input.lower() in ['q', 'quit']:
                print("👋 Cancelled by user")
                sys.exit(0)

            end_ms = parse_date_input(end_input, default_to_end_of_day=True)
            end_formatted = format_timestamp(end_ms)
            print(f"✅ End: {end_formatted}")
            break

        except ValueError as e:
            end_attempts += 1
            print(f"❌ {e}")
            if end_attempts < 3:
                print("Please try again with format: mm/dd/yy hh:mm or epoch milliseconds")
            else:
                print("Too many invalid attempts")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            sys.exit(0)

    # Validate date range
    if start_ms >= end_ms:
        print("❌ Start time must be before end time")
        sys.exit(1)

    # Show duration
    duration_hours = (end_ms - start_ms) / (1000 * 60 * 60)
    print(f"📊 Date range: {duration_hours:.1f} hours")

    return start_ms, end_ms


def get_timestamps_interactive(start_arg: Optional[str], end_arg: Optional[str]) -> Tuple[int, int]:
    """
    Get start and end timestamps, prompting user if not provided.

    Args:
        start_arg: Command-line start time (may be None)
        end_arg: Command-line end time (may be None)

    Returns:
        Tuple of (start_ms, end_ms) as integers

    Raises:
        SystemExit: If user cancels or validation fails
    """
    # If both provided, validate and return
    if start_arg and end_arg:
        try:
            start_ms = parse_date_input(start_arg, default_to_end_of_day=False)
            end_ms = parse_date_input(end_arg, default_to_end_of_day=True)

            if start_ms >= end_ms:
                print("❌ Start time must be before end time")
                sys.exit(1)

            print(f"✅ Start: {format_timestamp(start_ms)}")
            print(f"✅ End: {format_timestamp(end_ms)}")

            duration_hours = (end_ms - start_ms) / (1000 * 60 * 60)
            print(f"📊 Date range: {duration_hours:.1f} hours")

            return start_ms, end_ms
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)

    # If neither provided, prompt for both
    if not start_arg and not end_arg:
        return prompt_for_date_range()

    # If only one provided, prompt for the missing one
    if start_arg and not end_arg:
        try:
            start_ms = parse_date_input(start_arg, default_to_end_of_day=False)
            print(f"✅ Start: {format_timestamp(start_ms)}")

            # Prompt for end date
            end_input = input("📅 Enter end date/time: ").strip()
            if end_input.lower() in ['q', 'quit']:
                print("👋 Cancelled by user")
                sys.exit(0)

            end_ms = parse_date_input(end_input, default_to_end_of_day=True)
            print(f"✅ End: {format_timestamp(end_ms)}")

            if start_ms >= end_ms:
                print("❌ Start time must be before end time")
                sys.exit(1)

            return start_ms, end_ms

        except ValueError as e:
            print(f"❌ Error parsing date: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            sys.exit(0)

    if end_arg and not start_arg:
        try:
            end_ms = parse_date_input(end_arg, default_to_end_of_day=True)
            print(f"✅ End: {format_timestamp(end_ms)}")

            # Prompt for start date
            start_input = input("📅 Enter start date/time: ").strip()
            if start_input.lower() in ['q', 'quit']:
                print("👋 Cancelled by user")
                sys.exit(0)

            start_ms = parse_date_input(start_input, default_to_end_of_day=False)
            print(f"✅ Start: {format_timestamp(start_ms)}")

            if start_ms >= end_ms:
                print("❌ Start time must be before end time")
                sys.exit(1)

            return start_ms, end_ms

        except ValueError as e:
            print(f"❌ Error parsing date: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            sys.exit(0)


def generate_cli_command(serial: str, start_ms: int, end_ms: int, username: str,
                         use_dev: bool = False) -> str:
    """
    Generate CLI command to reproduce the current request.

    Args:
        serial: Device serial number
        start_ms: Start timestamp in milliseconds
        end_ms: End timestamp in milliseconds
        username: User email
        use_dev: Whether dev API was used

    Returns:
        CLI command string
    """
    cmd_parts = ['python3 get_loc.py']
    cmd_parts.append(f'-u {username}')
    cmd_parts.append(f'-s {serial}')
    cmd_parts.append(f'-ts {start_ms}')
    cmd_parts.append(f'-te {end_ms}')

    if use_dev:
        cmd_parts.append('-dev')

    return ' '.join(cmd_parts)


def print_reproducible_command(serial: str, start_ms: int, end_ms: int, username: str,
                               use_dev: bool = False) -> None:
    """
    Print the CLI command to reproduce this request.

    Args:
        serial: Device serial number
        start_ms: Start timestamp in milliseconds
        end_ms: End timestamp in milliseconds
        username: User email
        use_dev: Whether dev API was used
    """
    cmd = generate_cli_command(serial, start_ms, end_ms, username, use_dev)
    print(f"\n📋 To reproduce this request:")
    print(f"   {cmd}")


def fetch_sensor_history(serial, sensor_id, start, end, token, use_development=False):
    base_url = get_api_base_url(use_development)
    url = f"{base_url}/things/{serial}/sensor/{sensor_id}/history/{start}/{end}?group_by_time=1m"
    print(f"Fetching sensor {sensor_id} data from: {url}")
    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }
    try:
        response = requests.get(url, timeout=30, verify=False, headers=headers)
        if response.status_code == 200:
            print(f"✅ Received data for sensor {sensor_id}")
            return response.json()
        else:
            print(f"❌ Failed to fetch sensor {sensor_id} data: {response.status_code} - {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Exception fetching sensor {sensor_id} data: {e}")
        sys.exit(1)


def combine_lat_lon(lat_data, lon_data):
    print("Combining latitude and longitude data by timestamp...")
    lat_points = {pt['time']: pt['value'] for pt in lat_data}
    lon_points = {pt['time']: pt['value'] for pt in lon_data}
    all_times = sorted(set(lat_points.keys()) & set(lon_points.keys()))
    combined = [
        {
            "time": t,
            "latitude": lat_points[t],
            "longitude": lon_points[t]
        }
        for t in all_times
    ]
    print(f"Matched {len(combined)} lat/lon pairs.")
    return combined


def to_geojson(serial, start, combined_points):
    print("Generating GeoJSON output...")
    features = []
    for pt in combined_points:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [pt["longitude"], pt["latitude"]]
            },
            "properties": {
                "timestamp": pt["time"]
            }
        })
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    filename = f"{serial}-{start}.geojson"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)
    print(f"GeoJSON written to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Download and convert iMatrix location history to GeoJSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default interactive mode (complete workflow)
  %(prog)s -u user@example.com

  # Skip to date entry (device known)
  %(prog)s -s 1234567890 -u user@example.com

  # Direct download with human dates
  %(prog)s -s 1234567890 -ts "01/15/25" -te "01/16/25" -u user@example.com

  # Direct download with epoch timestamps
  %(prog)s -s 1234567890 -ts 1736899200000 -te 1736985600000 -u user@example.com

Date Formats:
  • Press Enter for last 24 hours (when prompted)
  • Negative number: -60 (last 60 minutes from now)
  • mm/dd/yy (e.g., 01/15/25)
  • mm/dd/yy hh:mm (e.g., 01/15/25 14:30)
  • Epoch milliseconds (e.g., 1736899200000)
        """
    )
    parser.add_argument('-s', '--serial',
                        help='Device serial number (optional - interactive device selection if omitted)')
    parser.add_argument('-ts', '--start',
                        help='Start time (optional - interactive prompt if omitted)')
    parser.add_argument('-te', '--end',
                        help='End time (optional - interactive prompt if omitted)')
    parser.add_argument('-u', '--username', required=True,
                        help='iMatrix Cloud username (email)')
    parser.add_argument('-p', '--password',
                        help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('-dev', '--dev', action='store_true',
                        help='Use development API endpoint instead of production')
    args = parser.parse_args()

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("🔑 Enter password: ")

    username = args.username

    # Login to API first (needed for all operations)
    environment = "development" if args.dev else "production"
    if args.verbose:
        print(f"Using {environment} API")
    token = login_to_imatrix(username, password, args.dev)

    # Step 1: Get device serial number
    devices = None
    selected_device = None

    if not args.serial:
        # No serial provided - start with device listing (DEFAULT MODE)
        devices = get_user_devices(token, args.verbose, args.dev)
        selected_serial = select_device_interactive(devices)

        # Find selected device details
        selected_device = get_device_by_serial(selected_serial, devices)
        print_device_details(selected_device)
    else:
        # Serial provided directly - validate it exists
        devices = get_user_devices(token, args.verbose, args.dev)
        selected_serial = args.serial
        selected_device = get_device_by_serial(selected_serial, devices)
        print_device_details(selected_device)

    # Step 2: Get timestamps (interactive prompting if not provided)
    start_ms, end_ms = get_timestamps_interactive(args.start, args.end)

    # Step 3: Download location data
    print(f"\n🚀 Starting location data download")
    print(f"   Serial: {selected_serial}")
    print(f"   Period: {format_timestamp(start_ms)} to {format_timestamp(end_ms)}")
    print(f"   Epoch:  {start_ms} to {end_ms}\n")

    lat_json = fetch_sensor_history(selected_serial, 2, start_ms, end_ms, token, args.dev)
    lon_json = fetch_sensor_history(selected_serial, 3, start_ms, end_ms, token, args.dev)

    # The API returns a dict: {<serial>: {<sensor_id>: { ... 'data': [ ... ] } } }
    try:
        lat_data = next(iter(lat_json.values()))["2"]["data"]
        lon_data = next(iter(lon_json.values()))["3"]["data"]
    except Exception as e:
        print(f"❌ Error parsing API response: {e}")
        print("   This device may not have GPS/location sensors")
        sys.exit(1)

    combined_points = combine_lat_lon(lat_data, lon_data)

    if not combined_points:
        print("⚠️  No matching location data found in the specified time range")
        print("   The device may not have reported location during this period")
    else:
        to_geojson(selected_serial, start_ms, combined_points)

        # Print summary
        print(f"\n📊 Location Data Summary:")
        print(f"   Device:       {selected_device.get('name', 'Unknown')} ({selected_serial})")
        print(f"   Time Range:   {format_timestamp(start_ms)} to {format_timestamp(end_ms)}")
        print(f"   Data Points:  {len(combined_points)}")

        if combined_points:
            first_pt = combined_points[0]
            last_pt = combined_points[-1]
            print(f"   First Point:  ({first_pt['latitude']:.6f}, {first_pt['longitude']:.6f}) @ {format_timestamp(first_pt['time'])}")
            print(f"   Last Point:   ({last_pt['latitude']:.6f}, {last_pt['longitude']:.6f}) @ {format_timestamp(last_pt['time'])}")

    # Print reproducible command
    print_reproducible_command(selected_serial, start_ms, end_ms, username, args.dev)

    print("\n✨ Done!")

if __name__ == "__main__":
    main()
