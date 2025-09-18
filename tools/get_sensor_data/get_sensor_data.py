#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_sensor_data.py
Downloads sensor data history from the iMatrix API with device discovery and
interactive sensor selection. Properly handles device serial numbers and product IDs
for correct API endpoint usage.

Usage:
    # Default interactive mode (complete workflow - devices, sensors, dates):
    python3 get_sensor_data.py -u <email>

    # Skip to sensor selection (with known device):
    python3 get_sensor_data.py -s <serial> -u <email>

    # Skip to date entry (with known device and sensor):
    python3 get_sensor_data.py -s <serial> -id <sensor_id> -u <email>

    # Direct mode (no interaction needed):
    python3 get_sensor_data.py -s <serial> -ts <start> -te <end> -id <sensor_id> -u <email>

    # Information modes:
    python3 get_sensor_data.py -s <serial> -u <email> --list-sensors
    python3 get_sensor_data.py -s <serial> -u <email> --product-info

Date Formats Supported:
    • Epoch milliseconds: 1736899200000
    • Date only: 01/15/25 (midnight to midnight)
    • Date and time: 01/15/25 14:30

Examples:
    # Default interactive mode (complete workflow - NEW DEFAULT)
    python3 get_sensor_data.py -u user@example.com

    # Skip to sensor selection (device known)
    python3 get_sensor_data.py -s 1234567890 -u user@example.com

    # Skip to date entry (device and sensor known)
    python3 get_sensor_data.py -s 1234567890 -id 509 -u user@example.com

    # Direct download with human dates
    python3 get_sensor_data.py -s 1234567890 -ts "01/15/25" -te "01/16/25" -id 509 -u user@example.com

    # Direct download with epoch timestamps (original)
    python3 get_sensor_data.py -s 1234567890 -ts 1736899200000 -te 1736985600000 -id 509 -u user@example.com

    # Information modes
    python3 get_sensor_data.py -s 1234567890 -u user@example.com --list-sensors
    python3 get_sensor_data.py -s 1234567890 -u user@example.com --product-info

Dependencies:
    python3 -m pip install requests urllib3
"""

import argparse
import requests
import sys
import json
import csv
import urllib3
import getpass
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_api_base_url(use_development=False):
    """Get API base URL based on environment selection."""
    if use_development:
        return "https://api-dev.imatrixsys.com/api/v1"
    else:
        return "https://api.imatrixsys.com/api/v1"

# Known sensor definitions (ID 509-537)
SENSOR_DEFINITIONS = {
    509: {"name": "MPGe", "units": "mpge"},
    510: {"name": "Trip UTC Start Time", "units": "Time"},
    511: {"name": "Trip UTC End Time", "units": "Time"},
    512: {"name": "Trip idle time", "units": "Seconds"},
    513: {"name": "Trip Wh/km", "units": "Wh/km"},
    514: {"name": "Trip MPGe", "units": "mpge"},
    515: {"name": "Trip l/100km", "units": "l/100km"},
    516: {"name": "Trip CO2 Emissions", "units": "kg"},
    517: {"name": "Trip Power", "units": "kWh"},
    518: {"name": "Trip Energy Recovered", "units": "kWH"},
    519: {"name": "Trip Charge", "units": "kWH"},
    520: {"name": "Trip Average Charge Rate", "units": "kW"},
    521: {"name": "Trip Peak Charge Rate", "units": "kW"},
    522: {"name": "Trip Average Speed", "units": "km"},
    523: {"name": "Trip Maximum Speed", "units": "km"},
    524: {"name": "Trip number hard accelerations", "units": "Qty"},
    525: {"name": "Trip number hard braking", "units": "Qty"},
    526: {"name": "Trip number hard turns", "units": "Qty"},
    527: {"name": "Maximum deceleration", "units": "g"},
    528: {"name": "Trip fault Codes", "units": "Code"},
    529: {"name": "Peak power", "units": "kW"},
    530: {"name": "Range gained per minute", "units": "km/min"},
    531: {"name": "Peak Regerative Power", "units": "kW"},
    532: {"name": "Peak Brake Pedal", "units": "%"},
    533: {"name": "Peak Accel Pedal", "units": "%"},
    534: {"name": "DTC OBD2 Codes", "units": "Code"},
    535: {"name": "DTC J1939 Codes", "units": "Code"},
    536: {"name": "DTC HM Truck Codes", "units": "Code"},
    537: {"name": "DTC Echassie Codes", "units": "Code"},
}


def login_to_imatrix(email: str, password: str) -> str:
    """
    Authenticate with the iMatrix API and return the auth token.

    Args:
        email: User's email address
        password: User's password

    Returns:
        Authentication token string

    Raises:
        SystemExit: If login fails
    """
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    payload = {
        'email': email,
        'password': password
    }

    print("🔐 Logging in to iMatrix API...")

    try:
        response = requests.post(LOGIN_URL, headers=headers,
                                data=json.dumps(payload), verify=False)

        if response.status_code == 200:
            token = response.json().get('token')
            if token:
                print("✅ Login successful.")
                return token
            else:
                print("❌ Token not found in response.")
                print(f"Response: {response.json()}")
                sys.exit(1)
        else:
            print(f"❌ Login failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error during login: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during login: {e}")
        sys.exit(1)


def get_user_devices(token: str, verbose: bool = False) -> List[Dict]:
    """
    Fetch all devices/things for the authenticated user.

    Args:
        token: Authentication token
        verbose: Print verbose output

    Returns:
        List of device dictionaries

    Raises:
        SystemExit: If API request fails
    """
    url = USER_DEVICES_URL

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

            print(f"✅ Found {len(devices)} devices in your account")

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


def get_product_info(product_id: int, token: str, verbose: bool = False) -> Dict:
    """
    Fetch product information for a product ID.

    Args:
        product_id: Product ID (integer)
        token: Authentication token
        verbose: Print verbose output

    Returns:
        Product information dictionary

    Raises:
        SystemExit: If API request fails
    """
    url = PRODUCT_INFO_URL.format(id=product_id)

    if verbose:
        print(f"📡 Product Info URL: {url}")

    print(f"🔍 Fetching product information for product ID: {product_id}")

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.get(url, timeout=30, verify=False, headers=headers)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved product information")
            return data
        elif response.status_code == 404:
            print(f"❌ Product {product_id} not found")
            print("   Please check the product ID and try again")
            sys.exit(1)
        else:
            print(f"❌ Failed to fetch product information")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            sys.exit(1)

    except requests.exceptions.Timeout:
        print(f"❌ Request timeout while fetching product information")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while fetching product information: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error while fetching product information: {e}")
        sys.exit(1)


def get_sensor_details(sensor_id: int, token: str, verbose: bool = False) -> Dict:
    """
    Fetch detailed information for a specific sensor ID.

    Args:
        sensor_id: Sensor ID to fetch details for
        token: Authentication token
        verbose: Print verbose output

    Returns:
        Sensor details dictionary

    Raises:
        SystemExit: If API request fails
    """
    url = SENSOR_DETAILS_URL.format(id=sensor_id)

    if verbose:
        print(f"📡 Sensor Details URL: {url}")

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.get(url, timeout=30, verify=False, headers=headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            if verbose:
                print(f"⚠️  Sensor {sensor_id} details not found")
            return {}
        else:
            if verbose:
                print(f"⚠️  Failed to fetch sensor {sensor_id} details: {response.status_code}")
            return {}

    except Exception as e:
        if verbose:
            print(f"⚠️  Error fetching sensor {sensor_id} details: {e}")
        return {}


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


def discover_device_sensors(serial: str, token: str, verbose: bool = False, devices: List[Dict] = None) -> List[Dict]:
    """
    Discover all sensors available for a device.

    Args:
        serial: Device serial number
        token: Authentication token
        verbose: Print verbose output
        devices: Optional pre-fetched device list (avoids duplicate API call)

    Returns:
        List of sensor information dictionaries

    Raises:
        SystemExit: If discovery fails
    """
    print(f"🔍 Discovering sensors for device: {serial}")

    # Get device list if not provided
    if devices is None:
        devices = get_user_devices(token, verbose)

    # Find the device and get its productId
    device = get_device_by_serial(serial, devices)
    product_id = device.get('productId')

    if not product_id:
        print(f"❌ Device {serial} has no associated product ID")
        sys.exit(1)

    if verbose:
        print(f"   Device product ID: {product_id}")

    # Get product information using correct productId
    product_data = get_product_info(product_id, token, verbose)

    # Extract sensor IDs from product data
    sensor_ids = product_data.get('controlSensorIds', [])

    if not sensor_ids:
        print(f"❌ No sensors found for device {serial}")
        sys.exit(1)

    print(f"📊 Found {len(sensor_ids)} sensors, fetching details...")

    # Fetch details for each sensor
    sensors = []
    for i, sensor_id in enumerate(sensor_ids, 1):
        if verbose:
            print(f"   Fetching sensor {i}/{len(sensor_ids)}: {sensor_id}")

        sensor_details = get_sensor_details(sensor_id, token, verbose)

        if sensor_details:
            # Enhance with index for menu selection
            sensor_details['menu_index'] = len(sensors) + 1
            sensors.append(sensor_details)
        else:
            if verbose:
                print(f"   ⚠️  Skipping sensor {sensor_id} (no details available)")

    if not sensors:
        print(f"❌ Could not retrieve details for any sensors on device {serial}")
        sys.exit(1)

    print(f"✅ Successfully discovered {len(sensors)} sensors")
    return sensors


def print_product_info(product_data: Dict) -> None:
    """
    Display formatted product information.

    Args:
        product_data: Product information dictionary
    """
    print("\n" + "="*80)
    print("📱 DEVICE INFORMATION")
    print("="*80)

    print(f"Device Name:        {product_data.get('name', 'Unknown')}")
    print(f"Short Name:         {product_data.get('shortName', 'Unknown')}")
    print(f"Product ID:         {product_data.get('id', 'Unknown')}")
    print(f"Platform Type:      {product_data.get('platformType', 'Unknown')}")
    print(f"Platform ID:        {product_data.get('platformId', 'Unknown')}")
    print(f"Organization ID:    {product_data.get('organizationId', 'Unknown')}")
    print(f"Number of Sensors:  {product_data.get('noSensors', 0)}")
    print(f"Number of Controls: {product_data.get('noControls', 0)}")
    print(f"Published:          {'Yes' if product_data.get('isPublished') else 'No'}")

    if product_data.get('batteryUse'):
        print(f"Battery Usage:      {product_data.get('batteryUse')}%")

    if product_data.get('rssiUse'):
        print(f"RSSI Usage:         {product_data.get('rssiUse')} dBm")

    print("="*80)


def print_sensor_list(sensors: List[Dict]) -> None:
    """
    Display formatted list of available sensors.

    Args:
        sensors: List of sensor information dictionaries
    """
    print(f"\n📊 Available sensors ({len(sensors)} found):")
    print("-" * 80)

    for sensor in sensors:
        sensor_id = sensor.get('id', 'Unknown')
        name = sensor.get('name', 'Unknown')
        units = sensor.get('units', 'Unknown')
        data_type = sensor.get('dataType', 'Unknown')
        menu_index = sensor.get('menu_index', 0)

        print(f"[{menu_index}] {name} (ID: {sensor_id})")
        print(f"    Units: {units} | Type: {data_type}")


def display_sensor_menu(sensors: List[Dict]) -> int:
    """
    Display interactive menu for sensor selection.

    Args:
        sensors: List of sensor information dictionaries

    Returns:
        Selected sensor ID

    Raises:
        SystemExit: If user cancels or invalid selection
    """
    print_sensor_list(sensors)

    print("-" * 80)
    print(f"Select a sensor to download [1-{len(sensors)}], or 'q' to quit:")

    while True:
        try:
            selection = input("Enter your choice: ").strip().lower()

            if selection == 'q' or selection == 'quit':
                print("👋 Cancelled by user")
                sys.exit(0)

            # Try to parse as integer
            choice = int(selection)

            if 1 <= choice <= len(sensors):
                selected_sensor = sensors[choice - 1]
                sensor_id = selected_sensor['id']
                sensor_name = selected_sensor.get('name', f'Sensor {sensor_id}')

                print(f"✅ Selected: {sensor_name} (ID: {sensor_id})")
                return sensor_id
            else:
                print(f"❌ Please enter a number between 1 and {len(sensors)}")

        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            sys.exit(0)


def display_device_list(devices: List[Dict]) -> None:
    """
    Display devices in 4-column format with selection numbers.

    Args:
        devices: List of device dictionaries
    """
    print(f"\n{'=' * 80}")
    print(f"{'USER DEVICES':^80}")
    print(f"{'(' + str(len(devices)) + ' found)':^80}")
    print(f"{'=' * 80}")

    # Header
    print(f"{'#':>3} {'Device Name':<35} {'Serial Number':<12} {'Product ID':<12} {'Version':<10}")
    print("-" * 80)

    # Device list
    for i, device in enumerate(devices, 1):
        name = device.get('name', 'Unknown')
        serial = device.get('sn', 0)
        product_id = device.get('productId', 0)
        version = device.get('currentVersion', 'Unknown')

        # Truncate long names
        if len(name) > 34:
            name = name[:31] + "..."

        print(f"[{i:2}] {name:<35} {serial:<12} {product_id:<12} {version:<10}")


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

    print("-" * 80)
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
    print(f"   Version:         {device.get('currentVersion', 'Unknown')}")

    # Format creation date
    created_at = device.get('createdAt')
    if created_at:
        created_dt = datetime.fromtimestamp(created_at / 1000.0)
        print(f"   Created:         {created_dt.isoformat()}Z")

    print()


def validate_timestamps(start_ms: str, end_ms: str) -> Tuple[int, int]:
    """
    Validate and convert timestamp strings to integers.

    Args:
        start_ms: Start time in epoch milliseconds
        end_ms: End time in epoch milliseconds

    Returns:
        Tuple of (start_ms, end_ms) as integers

    Raises:
        SystemExit: If timestamps are invalid
    """
    try:
        start = int(start_ms)
        end = int(end_ms)

        if start < 0 or end < 0:
            print("❌ Timestamps must be positive integers")
            sys.exit(1)

        if start >= end:
            print("❌ Start time must be before end time")
            sys.exit(1)

        # Check if timestamps are reasonable (not in seconds by mistake)
        current_ms = int(datetime.now().timestamp() * 1000)
        if end > current_ms * 10:  # Way in the future
            print("⚠️  Warning: End time appears to be far in the future")

        if start < 1000000000000:  # Likely in seconds, not milliseconds
            print("⚠️  Warning: Timestamps appear to be in seconds, not milliseconds")
            print("    Consider multiplying by 1000")

        return start, end

    except ValueError:
        print(f"❌ Invalid timestamp format. Must be epoch milliseconds.")
        print(f"   Start: {start_ms}, End: {end_ms}")
        sys.exit(1)


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
    print("\n📅 Date/time range required for data download")
    print("\nSupported formats:")
    print("  • Epoch milliseconds: 1736899200000")
    print("  • Date only: 01/15/25 (assumes midnight to midnight)")
    print("  • Date and time: 01/15/25 14:30")
    print("  • Enter 'q' to quit\n")

    # Get start date
    start_attempts = 0
    while start_attempts < 3:
        try:
            start_input = input("📅 Enter start date/time: ").strip()

            if start_input.lower() in ['q', 'quit']:
                print("👋 Cancelled by user")
                sys.exit(0)

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
    # If both provided, use existing validation
    if start_arg and end_arg:
        return validate_timestamps(start_arg, end_arg)

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
            print(f"❌ Error parsing start date: {e}")
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
            print(f"❌ Error parsing end date: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            sys.exit(0)


def fetch_sensor_history(serial: str, sensor_id: int, start: int, end: int,
                        token: str, verbose: bool = False) -> Dict:
    """
    Fetch sensor history data from the iMatrix API.

    Args:
        serial: Device serial number
        sensor_id: Sensor ID to fetch
        start: Start time in epoch milliseconds
        end: End time in epoch milliseconds
        token: Authentication token
        verbose: Print verbose output

    Returns:
        API response as dictionary

    Raises:
        SystemExit: If API request fails
    """
    url = API_URL.format(serial=serial, sensor_id=sensor_id,
                        start=start, end=end)

    if verbose:
        print(f"📡 API URL: {url}")

    sensor_info = SENSOR_DEFINITIONS.get(sensor_id, {"name": f"Sensor {sensor_id}", "units": "unknown"})
    print(f"📊 Fetching {sensor_info['name']} (ID: {sensor_id}) data...")

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.get(url, timeout=30, verify=False, headers=headers)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Received data for sensor {sensor_id}")
            return data
        elif response.status_code == 404:
            print(f"❌ No data found for sensor {sensor_id} in the specified time range")
            return {}
        else:
            print(f"❌ Failed to fetch sensor {sensor_id} data")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            sys.exit(1)

    except requests.exceptions.Timeout:
        print(f"❌ Request timeout while fetching sensor {sensor_id} data")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while fetching sensor {sensor_id} data: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error while fetching sensor {sensor_id} data: {e}")
        sys.exit(1)


def parse_sensor_data(api_response: Dict, sensor_id: int) -> List[Dict]:
    """
    Parse sensor data from API response.

    Args:
        api_response: Raw API response dictionary
        sensor_id: Sensor ID being parsed

    Returns:
        List of data points with time, value, and formatted_time
    """
    if not api_response:
        return []

    try:
        # API returns: {<serial>: {<sensor_id>: { ... 'data': [ ... ] } } }
        # Get the first (and usually only) serial key
        serial_data = next(iter(api_response.values()))
        sensor_data = serial_data.get(str(sensor_id), {})
        raw_data = sensor_data.get('data', [])

        # Enhance each data point with formatted timestamp
        parsed_data = []
        for point in raw_data:
            enhanced_point = {
                'time': point['time'],
                'value': point['value'],
                'formatted_time': format_timestamp(point['time'])
            }
            parsed_data.append(enhanced_point)

        return parsed_data

    except Exception as e:
        print(f"⚠️  Warning: Error parsing API response: {e}")
        return []


def calculate_statistics(data: List[Dict]) -> Dict[str, Any]:
    """
    Calculate statistics for the sensor data.

    Args:
        data: List of data points

    Returns:
        Dictionary with min, max, average, count, and time range
    """
    if not data:
        return {
            'min': None,
            'max': None,
            'average': None,
            'count': 0,
            'first_time': None,
            'last_time': None,
            'duration_hours': 0
        }

    values = [point['value'] for point in data if point['value'] is not None]

    if not values:
        return {
            'min': None,
            'max': None,
            'average': None,
            'count': len(data),
            'first_time': format_timestamp(data[0]['time']),
            'last_time': format_timestamp(data[-1]['time']),
            'duration_hours': 0
        }

    first_time = data[0]['time']
    last_time = data[-1]['time']
    duration_ms = last_time - first_time
    duration_hours = duration_ms / (1000 * 60 * 60)

    return {
        'min': min(values),
        'max': max(values),
        'average': sum(values) / len(values),
        'count': len(data),
        'first_time': format_timestamp(first_time),
        'last_time': format_timestamp(last_time),
        'duration_hours': round(duration_hours, 2)
    }


def generate_filename(serial: str, sensor_id: int, start: int,
                     custom_name: Optional[str] = None) -> str:
    """
    Generate a descriptive filename for the output.

    Args:
        serial: Device serial number
        sensor_id: Sensor ID
        start: Start timestamp
        custom_name: Optional custom filename base

    Returns:
        Base filename (without extension)
    """
    if custom_name:
        return custom_name

    # Format: serial_sensorID_YYYYMMDD
    dt = datetime.fromtimestamp(start / 1000.0)
    date_str = dt.strftime('%Y%m%d')

    sensor_info = SENSOR_DEFINITIONS.get(sensor_id, {"name": f"sensor{sensor_id}"})
    sensor_name = sensor_info['name'].replace(' ', '_').replace('/', '_')

    return f"{serial}_{sensor_name}_{date_str}"


def save_as_json(data: List[Dict], filename: str, metadata: Dict,
                 statistics: Dict) -> None:
    """
    Save sensor data as JSON file.

    Args:
        data: Sensor data points
        filename: Output filename (without extension)
        metadata: Metadata about the request
        statistics: Calculated statistics
    """
    output = {
        'metadata': metadata,
        'statistics': statistics,
        'data': data
    }

    json_filename = f"{filename}.json"

    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        print(f"💾 JSON data saved to: {json_filename}")
    except Exception as e:
        print(f"❌ Error saving JSON file: {e}")
        sys.exit(1)


def save_as_csv(data: List[Dict], filename: str, metadata: Dict,
                statistics: Dict) -> None:
    """
    Save sensor data as CSV file.

    Args:
        data: Sensor data points
        filename: Output filename (without extension)
        metadata: Metadata about the request
        statistics: Calculated statistics
    """
    csv_filename = f"{filename}.csv"

    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            # Write metadata header
            f.write(f"# Sensor Data Export\n")
            f.write(f"# Serial: {metadata['serial']}\n")
            f.write(f"# Sensor: {metadata['sensor_name']} (ID: {metadata['sensor_id']})\n")
            f.write(f"# Units: {metadata['sensor_units']}\n")
            f.write(f"# Start: {metadata['start_time']}\n")
            f.write(f"# End: {metadata['end_time']}\n")
            f.write(f"# Data Points: {statistics['count']}\n")
            if statistics['min'] is not None:
                f.write(f"# Min Value: {statistics['min']}\n")
                f.write(f"# Max Value: {statistics['max']}\n")
                f.write(f"# Average: {statistics['average']:.2f}\n")
            f.write(f"#\n")

            # Write data
            if data:
                fieldnames = ['timestamp_ms', 'value', 'formatted_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for point in data:
                    writer.writerow({
                        'timestamp_ms': point['time'],
                        'value': point['value'],
                        'formatted_time': point['formatted_time']
                    })
            else:
                f.write("# No data points found\n")

        print(f"💾 CSV data saved to: {csv_filename}")

    except Exception as e:
        print(f"❌ Error saving CSV file: {e}")
        sys.exit(1)


def print_summary(data: List[Dict], statistics: Dict, metadata: Dict) -> None:
    """
    Print a summary of the downloaded data to console.

    Args:
        data: Sensor data points
        statistics: Calculated statistics
        metadata: Request metadata
    """
    print("\n" + "="*60)
    print("📈 SENSOR DATA SUMMARY")
    print("="*60)

    print(f"Device Serial:  {metadata['serial']}")
    print(f"Sensor:         {metadata['sensor_name']} (ID: {metadata['sensor_id']})")
    print(f"Units:          {metadata['sensor_units']}")
    print(f"Time Range:     {metadata['start_time']}")
    print(f"                {metadata['end_time']}")
    print(f"Duration:       {statistics['duration_hours']} hours")
    print("-"*60)

    print(f"Data Points:    {statistics['count']}")

    if statistics['min'] is not None:
        print(f"Min Value:      {statistics['min']}")
        print(f"Max Value:      {statistics['max']}")
        print(f"Average:        {statistics['average']:.2f}")

    if data and len(data) > 0:
        print(f"\nFirst Reading:  {data[0]['value']} @ {data[0]['formatted_time']}")
        print(f"Last Reading:   {data[-1]['value']} @ {data[-1]['formatted_time']}")

    print("="*60 + "\n")


def main():
    """Main function to orchestrate the sensor data download."""

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Download sensor data from iMatrix API with device discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default interactive mode (complete workflow)
  %(prog)s -u user@example.com

  # Skip to sensor selection (device known)
  %(prog)s -s 1234567890 -u user@example.com

  # Skip to date entry (device and sensor known)
  %(prog)s -s 1234567890 -id 509 -u user@example.com

  # Direct download with human dates
  %(prog)s -s 1234567890 -ts "01/15/25" -te "01/16/25" -id 509 -u user@example.com

  # Information modes
  %(prog)s -s 1234567890 -u user@example.com --list-sensors
  %(prog)s -s 1234567890 -u user@example.com --product-info
        """
    )

    parser.add_argument('-s', '--serial',
                       help='Device serial number (optional - interactive device selection if omitted)')
    parser.add_argument('-ts', '--start',
                       help='Start time (epoch milliseconds) - required for data download')
    parser.add_argument('-te', '--end',
                       help='End time (epoch milliseconds) - required for data download')
    parser.add_argument('-id', '--sensor-id', type=int,
                       help='Sensor ID to download (optional - interactive selection if omitted)')

    # Discovery mode flags
    parser.add_argument('--list-devices', action='store_true',
                       help='List all user devices and select interactively')
    parser.add_argument('--list-sensors', action='store_true',
                       help='List available sensors without downloading data')
    parser.add_argument('--product-info', action='store_true',
                       help='Show product information only')
    parser.add_argument('-u', '--username', required=True,
                       help='iMatrix Cloud username (email)')
    parser.add_argument('-p', '--password',
                       help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-o', '--output', choices=['json', 'csv', 'both'],
                       default='json',
                       help='Output format (default: json)')
    parser.add_argument('-f', '--filename',
                       help='Output filename (without extension)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('-dev', '--dev', action='store_true',
                       help='Use development API endpoint instead of production')

    args = parser.parse_args()

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("🔑 Enter password: ")

    # Login to API first (needed for all operations)
    environment = "development" if args.dev else "production"
    if args.verbose:
        print(f"Using {environment} API")
    token = login_to_imatrix(args.username, password)

    # Step 1: Get device information and serial number
    devices = None
    selected_device = None

    if not args.serial:
        # No serial provided - start with device listing (DEFAULT MODE)
        devices = get_user_devices(token, args.verbose)
        selected_serial = select_device_interactive(devices)

        # Find selected device details
        selected_device = get_device_by_serial(selected_serial, devices)
        print_device_details(selected_device)
        print("Proceeding to sensor discovery...")
    else:
        # Serial provided directly - need to get device info
        devices = get_user_devices(token, args.verbose)
        selected_serial = args.serial
        selected_device = get_device_by_serial(selected_serial, devices)

    # Handle info-only modes that require product information
    if args.product_info:
        product_id = selected_device.get('productId')
        if not product_id:
            print(f"❌ Device {selected_serial} has no associated product ID")
            sys.exit(1)

        product_data = get_product_info(product_id, token, args.verbose)
        print_product_info(product_data)
        print("\n✨ Done!")
        return

    # Step 2: Determine sensor ID
    if not args.sensor_id:
        # No sensor ID provided - discover sensors on selected device
        sensors = discover_device_sensors(selected_serial, token, args.verbose, devices)

        if args.list_sensors:
            # Just list sensors and exit
            product_id = selected_device.get('productId')
            if product_id:
                product_data = get_product_info(product_id, token, args.verbose)
                print_product_info(product_data)
            print_sensor_list(sensors)
            print("\n✨ Done!")
            return

        # Interactive sensor selection
        selected_sensor_id = display_sensor_menu(sensors)

        # Find the selected sensor details
        selected_sensor = None
        for sensor in sensors:
            if sensor['id'] == selected_sensor_id:
                selected_sensor = sensor
                break
    else:
        # Sensor ID provided directly
        selected_sensor_id = args.sensor_id
        selected_sensor = {
            'id': selected_sensor_id,
            'name': SENSOR_DEFINITIONS.get(selected_sensor_id, {}).get('name', f'Sensor {selected_sensor_id}'),
            'units': SENSOR_DEFINITIONS.get(selected_sensor_id, {}).get('units', 'unknown')
        }

    # Get timestamps (interactive prompting if not provided)
    start_ms, end_ms = get_timestamps_interactive(args.start, args.end)

    # Get sensor information
    sensor_name = selected_sensor.get('name', f'Sensor {selected_sensor_id}')
    sensor_units = selected_sensor.get('units', 'unknown')

    print(f"\n🚀 Starting sensor data download")
    print(f"   Serial: {selected_serial}")
    print(f"   Sensor: {sensor_name} (ID: {selected_sensor_id})")
    print(f"   Period: {format_timestamp(start_ms)} to {format_timestamp(end_ms)}\n")

    # Fetch sensor data
    api_response = fetch_sensor_history(selected_serial, selected_sensor_id,
                                       start_ms, end_ms, token, args.verbose)

    # Parse the data
    sensor_data = parse_sensor_data(api_response, selected_sensor_id)

    if not sensor_data:
        print("⚠️  No data points found in the specified time range")
        # Still create empty output files if requested

    # Calculate statistics
    stats = calculate_statistics(sensor_data)

    # Prepare metadata
    metadata = {
        'serial': args.serial,
        'sensor_id': selected_sensor_id,
        'sensor_name': sensor_name,
        'sensor_units': sensor_units,
        'start_time': format_timestamp(start_ms),
        'end_time': format_timestamp(end_ms),
        'download_time': datetime.now().isoformat() + 'Z',
        'data_points': stats['count']
    }

    # Print summary
    print_summary(sensor_data, stats, metadata)

    # Generate filename
    base_filename = generate_filename(args.serial, args.sensor_id,
                                     start_ms, args.filename)

    # Save output files
    if args.output in ['json', 'both']:
        save_as_json(sensor_data, base_filename, metadata, stats)

    if args.output in ['csv', 'both']:
        save_as_csv(sensor_data, base_filename, metadata, stats)

    print("\n✨ Done!")


if __name__ == "__main__":
    main()