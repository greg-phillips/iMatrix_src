#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@file upload_sine_wave.py
@brief Upload sine wave time series data to iMatrix Cloud API

This script generates a sine wave pattern with special marker values and uploads
the time series data to the iMatrix Cloud API. The pattern consists of:
- 60 samples of sine wave (0-100 range) at 1-minute intervals
- 4 marker values (101, 102, 103, 104) after each cycle
- Entire sequence repeated 5 times

Usage:
    python3 upload_sine_wave.py -U <email> -P <password> -s <serial_number> -T <start_time_ms> [-S <sensor_id>]

Options:
    -U, --username       User email for login (required)
    -P, --password       Password (required)
    -s, --serial         Device serial number (required)
    -T, --start-time     Start time in milliseconds since epoch (required)
    -S, --sensor-id      Sensor ID for the data (default: 126)
    --dry-run           Generate data without uploading
    -dev, --dev         Use development API endpoint instead of production

Example:
    python3 upload_sine_wave.py -U user@example.com -P mypassword -s 1000000001 -T 1735689600000
"""

import argparse
import requests
import getpass
import sys
import json
import math
import urllib3
from datetime import datetime, timedelta

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants
SAMPLES_PER_HOUR = 60  # One sample per minute
MARKER_VALUES = [101, 102, 103, 104]
REPEAT_CYCLES = 5
SAMPLE_INTERVAL_MS = 60000  # 1 minute in milliseconds


def login_to_imatrix(email, password, use_production=False):
    """
    Authenticate with the iMatrix API and retrieve an authentication token.
    
    Args:
        email (str): User's email address for authentication
        password (str): User's password
        use_production (bool): Use production API instead of development
        
    Returns:
        str: Authentication token for subsequent API calls
        
    Raises:
        SystemExit: If login fails or token is not received
    """
    url = 'https://api.imatrixsys.com/api/v1/login' if use_production else 'https://api-dev.imatrixsys.com/api/v1/login'
    
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    payload = {
        'email': email,
        'password': password
    }
    
    print(f"🔐 Logging in to {'production' if use_production else 'development'} API...")
    
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


def generate_sine_wave_data(start_time_ms, sensor_id):
    """
    Generate sine wave time series data with marker values.
    
    Creates a pattern of:
    - 60 sine wave samples (0-100 range) at 1-minute intervals
    - 4 marker values (101, 102, 103, 104)
    - Repeated 5 times
    
    Args:
        start_time_ms (int): Start timestamp in milliseconds since epoch
        sensor_id (int): Sensor ID for the data points
        
    Returns:
        list: List of dictionaries containing time series data points
    """
    data_points = []
    current_time_ms = start_time_ms
    
    print(f"📊 Generating sine wave data starting at {datetime.fromtimestamp(start_time_ms/1000).isoformat()}")
    
    for cycle in range(REPEAT_CYCLES):
        print(f"  Cycle {cycle + 1}/{REPEAT_CYCLES}...")
        
        # Generate sine wave samples
        for i in range(SAMPLES_PER_HOUR):
            # Calculate sine value: 50 + 50 * sin(2π * t/60)
            # This gives us a range from 0 to 100
            angle = 2 * math.pi * i / SAMPLES_PER_HOUR
            value = 50 + 50 * math.sin(angle)
            
            data_points.append({
                "time": current_time_ms,
                "value": round(value, 2)
            })
            current_time_ms += SAMPLE_INTERVAL_MS
        
        # Add marker values
        for marker_value in MARKER_VALUES:
            data_points.append({
                "time": current_time_ms,
                "value": marker_value
            })
            current_time_ms += SAMPLE_INTERVAL_MS
    
    print(f"✅ Generated {len(data_points)} data points")
    print(f"   Time range: {datetime.fromtimestamp(start_time_ms/1000).isoformat()} to "
          f"{datetime.fromtimestamp((current_time_ms-SAMPLE_INTERVAL_MS)/1000).isoformat()}")
    
    return data_points


def upload_time_series_data(token, serial_number, sensor_id, data_points, use_production=False, dry_run=False, show_json=False):
    """
    Upload time series data to iMatrix API.
    
    Args:
        token (str): Authentication token
        serial_number (str): Device serial number
        sensor_id (int): Sensor ID
        data_points (list): List of time series data points
        use_production (bool): Use production API instead of development
        dry_run (bool): If True, only display data without uploading
        show_json (bool): If True, display the full JSON payload
        
    Returns:
        bool: True if upload successful or dry run, False otherwise
    """
    if dry_run and not show_json:
        print("\n🔍 DRY RUN MODE - Data preview:")
        print(f"   Device SN: {serial_number}")
        print(f"   Sensor ID: {sensor_id}")
        print(f"   First 5 points:")
        for point in data_points[:5]:
            dt = datetime.fromtimestamp(point['time']/1000)
            print(f"     {dt.isoformat()}: {point['value']}")
        print(f"   ... ({len(data_points)-10} more points)")
        print(f"   Last 5 points:")
        for point in data_points[-5:]:
            dt = datetime.fromtimestamp(point['time']/1000)
            print(f"     {dt.isoformat()}: {point['value']}")
        return True
    
    # If show_json is requested, display the full JSON payload
    if show_json:
        print("\n📋 JSON PAYLOAD:")
        full_payload = {
            "data": {
                serial_number: {
                    str(sensor_id): data_points
                }
            }
        }
        print(json.dumps(full_payload, indent=2))
        
        if dry_run:
            print("\n✅ JSON displayed (dry-run mode, not uploaded)")
            return True
        else:
            print("\n📤 Proceeding to upload this data...")
    
    base_url = 'https://api.imatrixsys.com' if use_production else 'https://api-dev.imatrixsys.com'
    post_url = f"{base_url}/api/v1/things/points"
    
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-auth-token': token
    }
    
    # Batch upload in chunks to avoid overwhelming the API
    batch_size = 100
    total_batches = (len(data_points) + batch_size - 1) // batch_size
    
    print(f"\n📤 Uploading {len(data_points)} data points in {total_batches} batches...")
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(data_points))
        batch_points = data_points[start_idx:end_idx]
        
        payload = {
            "data": {
                serial_number: {
                    str(sensor_id): batch_points
                }
            }
        }
        
        try:
            print(f"   Batch {batch_num + 1}/{total_batches}: Uploading points {start_idx + 1}-{end_idx}...", end="")
            response = requests.post(post_url, headers=headers, json=payload, verify=False)
            
            if response.status_code == 200:
                print(" ✅")
            else:
                print(f" ❌")
                print(f"   Failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f" ❌")
            print(f"   Exception: {e}")
            return False
    
    print("✅ All data uploaded successfully!")
    return True


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Upload sine wave time series data to iMatrix Cloud API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -U user@example.com -P mypassword -s 1000000001 -T 1735689600000
  %(prog)s -U user@example.com -P mypassword -s 1000000001 -T 1735689600000 --dry-run
  %(prog)s -U user@example.com -P mypassword -s 1000000001 -T 1735689600000 --dry-run --show-json
  %(prog)s -U user@example.com -P mypassword -s 2000000001 -T 1735689600000 -S 126 --pro
        """
    )
    
    parser.add_argument('-U', '--username', required=True, 
                       help='iMatrix Cloud username (email) [REQUIRED]')
    parser.add_argument('-P', '--password', required=True,
                       help='iMatrix Cloud password [REQUIRED]')
    parser.add_argument('-s', '--serial', required=True,
                       help='Device serial number [REQUIRED]')
    parser.add_argument('-T', '--start-time', type=int, required=True,
                       help='Start time in milliseconds since epoch [REQUIRED]')
    parser.add_argument('-S', '--sensor-id', type=int, default=126,
                       help='Sensor ID for the data (default: 126)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Generate and display data without uploading')
    parser.add_argument('--show-json', action='store_true',
                       help='Display the full JSON payload that will be sent')
    parser.add_argument('-dev', '--dev', action='store_true',
                       help='Use development API endpoint instead of production')
    
    args = parser.parse_args()
    
    # Validate start time
    try:
        start_dt = datetime.fromtimestamp(args.start_time / 1000)
        print(f"📅 Start time: {start_dt.isoformat()}")
    except Exception as e:
        print(f"❌ Invalid start time: {e}")
        sys.exit(1)
    
    # Password is now mandatory from command line
    password = args.password
    
    # Generate sine wave data
    data_points = generate_sine_wave_data(args.start_time, args.sensor_id)
    
    # Login and upload (unless dry run without JSON display)
    if not args.dry_run or args.show_json:
        if not args.dry_run:
            token = login_to_imatrix(args.username, password, not args.dev)
        else:
            token = None
        upload_time_series_data(token, args.serial, args.sensor_id,
                              data_points, not args.dev, args.dry_run, args.show_json)
    else:
        upload_time_series_data(None, args.serial, args.sensor_id,
                              data_points, not args.dev, args.dry_run, args.show_json)
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()