#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@file upload_tsd.py
@brief Logs into the iMatrix Cloud API using command-line credentials and validates gateway and controller serial numbers.

This script authenticates against either the development or production iMatrix API, using
username/password credentials passed as command-line options. It also verifies that the
provided gateway and controller serial numbers are registered iMatrix devices. It additionally
accepts a CSV data file and checks for a valid header format.

Usage:
    python3 upload_tsd.py -U <email> [-P <password>] -G <gateway_serial> -C <controller_serial> -D <data_file> [-dev]

Options:
    -U, --username   User email for login (required)
    -P, --password   Password (optional, will prompt if not provided)
    -G, --gateway    Gateway serial number (numeric, max 10 digits, required)
    -C, --controller Controller serial number (numeric, max 10 digits, required)
    -D, --data       Path to data CSV file with sensor readings (required)
    -dev, --dev      Use development API endpoint instead of production

On successful login and validation, confirms device identity and file format.
"""

import argparse
import requests
import getpass
import sys
import json
import os
import csv
import urllib3
import sqlite3
import json

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def validate_serial(serial_str, label):
    if not serial_str.isdigit() or len(serial_str) > 10:
        print(f"❌ Invalid {label} serial number: must be numeric and at most 10 digits.")
        sys.exit(1)
    return serial_str

def validate_data_file(file_path):
    if not os.path.isfile(file_path):
        file_path_csv = file_path + ".csv"
        if os.path.isfile(file_path_csv):
            file_path = file_path_csv
        else:
            print(f"❌ Data file not found: {file_path}")
            sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)
            normalized_header = [col.strip().lower() for col in header]
            expected_header = ['timestamp', 'sensor_id', 'description', 'value']
            if normalized_header[:4] != expected_header:
                print("❌ Invalid CSV header format. Expected: timestamp,sensor_id,description,value")
                sys.exit(1)
            else:
                print(f"ߓ Data file loaded: {file_path}")
                return file_path
    except Exception as e:
        print(f"❌ Error reading data file: {e}")
    

def login_to_imatrix(email, password, use_production=False):
    url = 'https://api.imatrixsys.com/api/v1/login' if use_production else 'https://api-dev.imatrixsys.com/api/v1/login'

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    payload = {
        'email': email,
        'password': password
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
        if response.status_code == 200:
            token = response.json().get('token')
            if token:
                print("\n✅ Login successful.")
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

def validate_device(serial_number, label, token, use_production):
    base_url = 'https://api.imatrixsys.com' if use_production else 'https://api-dev.imatrixsys.com'
    url = f"{base_url}/api/v1/things/sn/{serial_number}"
    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            device = response.json()
            print(f"✅ {label} Device: {device['name']} (SN: {device['sn']})")
        else:
            print(f"❌ {label} device not found (SN: {serial_number})")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error validating {label} device: {e}")
        sys.exit(1)

from datetime import datetime

# Mapping table from Mersino Sensor ID to iMatrix Sensor ID
MERSINO_TO_IMATRIX = {
    9: 1514568775, 12: 41780623, 13: 1956385987, 14: 2062087966,
    15: 1518779154, 17: 2000830037, 19: 522106864, 52: 1955342161,
    53: 854793471, 56: 41817641, 57: 1008864098, 59: 1462674559,
    100: 565205552, 111: 266263402, 119: 1180447011, 136: 1958346967,
    137: 1390212605, 138: 984397266, 139: 1964429760, 143: 313104271,
    144: 1035073150, 205: 213404821, 207: 186370547, 208: 1347556348
}

# Database file for deduplication tracking
DB_FILE = "upload_tracker.db"

def is_duplicate(cursor, sensor_id, timestamp_ms):
    cursor.execute("SELECT 1 FROM uploads WHERE sensor_id = ? AND timestamp_ms = ?", (sensor_id, timestamp_ms))
    return cursor.fetchone() is not None

def record_upload(cursor, sensor_id, timestamp_ms):
    cursor.execute("INSERT OR IGNORE INTO uploads (sensor_id, timestamp_ms) VALUES (?, ?)", (sensor_id, timestamp_ms))

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            sensor_id INTEGER NOT NULL,
            timestamp_ms INTEGER NOT NULL,
            PRIMARY KEY(sensor_id, timestamp_ms)
        )
    """)
    conn.commit()
    return conn, cursor

def post_payload(token, payload, use_production):
    base_url = 'https://api.imatrixsys.com' if use_production else 'https://api-dev.imatrixsys.com'
    post_url = f"{base_url}/api/v1/things/points"
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-auth-token': token
    }
    try:
        response = requests.post(post_url, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            print("✅ Payload uploaded successfully.")
        else:
            print(f"❌ Failed to upload payload: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception during payload upload: {e}")


def main():
    parser = argparse.ArgumentParser(description="Login to iMatrix Cloud API and validate devices.")
    
    parser.add_argument('-R', '--repeat', action='store_true', help='Enable repeat mode using upload_tsd.json as time anchor')
    parser.add_argument('--lat', type=float, help='Latitude of the device location')
    parser.add_argument('--lon', type=float, help='Longitude of the device location')
    parser.add_argument('--alt', type=float, help='Altitude of the device location')
    parser.add_argument('-U', '--username', required=True, help='iMatrix Cloud username (email)')
    parser.add_argument('-P', '--password', help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-G', '--gateway', required=True, help='Gateway serial number (numeric, max 10 digits)')
    parser.add_argument('-C', '--controller', required=True, help='Controller serial number (numeric, max 10 digits)')
    parser.add_argument('-D', '--data', required=True, help='Path to raw data file (CSV with header)')
    parser.add_argument('-dev', '--dev', action='store_true', help='Use development API endpoint instead of production')

    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")

    gateway_serial = validate_serial(args.gateway, "Gateway")
    controller_serial = validate_serial(args.controller, "Controller")
    data_file = validate_data_file(args.data)

    # If repeat mode is enabled, load the anchor time from upload_tsd.json
    anchor_timestamp = None
    if args.repeat:
        repeat_file = 'upload_tsd.json'
        if not os.path.isfile(repeat_file):
            print("❌ Repeat mode enabled but 'upload_tsd.json' not found.")
            sys.exit(1)
        try:
            with open(repeat_file, 'r') as rf:
                repeat_data = json.load(rf)
                anchor_timestamp = repeat_data.get('last_event')
                if not isinstance(anchor_timestamp, int):
                    raise ValueError("Invalid timestamp in upload_tsd.json")
                print(f"ߔ Repeat mode active. Using anchor timestamp: {anchor_timestamp}")
        except Exception as e:
            print(f"❌ Failed to load repeat timestamp: {e}")
            sys.exit(1)

    token = login_to_imatrix(args.username, password, not args.dev)

    validate_device(gateway_serial, "Gateway", token, not args.dev)
    validate_device(controller_serial, "Controller", token, not args.dev)

    conn, cursor = setup_database()

    # Process up to 100 entries and emit 'GPS Update' messages every minute
    print("ߓ Processing all data rows:")
    try:
        with open(data_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            last_timestamp = None
            processed = 0
            offset = None
            for row in reader:
                try:
                    raw_timestamp = row['timestamp'].strip()
                    dt = datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00'))
                    timestamp_ms = int(dt.timestamp() * 1000)
                    if args.repeat:
                        if offset is None:
                            offset = timestamp_ms
                        timestamp_ms = anchor_timestamp + (timestamp_ms - offset)
                        if timestamp_ms > int(datetime.utcnow().timestamp() * 1000):
                            print("⏹️  Terminating repeat mode: simulated time has caught up with real time.")
                            break

                    if last_timestamp is not None:
                        time_diff = timestamp_ms - last_timestamp
                        while time_diff >= 60000:
                            print(f"ߓ GPS Update at {dt.isoformat()} | Location: ({args.lat}, {args.lon}, {args.alt})")
                            gps_payload = {
                                "data": {
                                    args.controller: {
                                        "2": [ {"time": timestamp_ms, "value": args.lat or 0.0} ],
                                        "3": [ {"time": timestamp_ms, "value": args.lon or 0.0} ],
                                        "4": [ {"time": timestamp_ms, "value": args.alt or 0.0} ],
                                        "142": [ {"time": timestamp_ms, "value": 0.0} ]
                                    }
                                }
                            }
                            if timestamp_ms - last_gps_sent >= 600000:
                                post_payload(token, gps_payload, not args.dev)
                                last_gps_sent = timestamp_ms
                            time_diff -= 60000
                    last_timestamp = timestamp_ms
                    if 'last_gps_sent' not in locals():
                        last_gps_sent = timestamp_ms

                    sensor_id = int(row['sensor_id'])
                    value_str = row['value'].strip()
                    if value_str.startswith('0x') or value_str.startswith('0X'):
                        value = float(int(value_str, 16))
                    else:
                        value = float(value_str)

                    if sensor_id in MERSINO_TO_IMATRIX:
                        imatrix_id = MERSINO_TO_IMATRIX[sensor_id]

                        if is_duplicate(cursor, imatrix_id, timestamp_ms):
                            print(f"{processed + 1:03}: ߕ {raw_timestamp} -> {timestamp_ms} | ID: {sensor_id}->{imatrix_id} | Value: {value_str} [Skipped: Duplicate]")
                        else:
                            payload = {
                                "data": {
                                    args.controller: {
                                        str(imatrix_id): [
                                            {
                                                "time": timestamp_ms,
                                                "value": value
                                            }
                                        ]
                                    }
                                }
                            }
                            print(f"{processed + 1:03}: ߕ {raw_timestamp} -> {timestamp_ms} | ID: {sensor_id}->{imatrix_id} | Value: {value} [Posted]")
                            post_payload(token, payload, not args.dev)
                            record_upload(cursor, imatrix_id, timestamp_ms)
                            conn.commit()
                        processed += 1
                        if args.repeat:
                            with open('upload_tsd.json', 'w') as rf:
                                json.dump({"last_event": timestamp_ms}, rf)
                    else:
                        print(f"⚠️  Skipping: {sensor_id}")
                except Exception as e:
                    print(f"❌ Error processing row {processed + 1}: {e} | Data: {row}")
    except Exception as e:
        print(f"❌ Error reading data file: {e}")

if __name__ == "__main__":
    main()
