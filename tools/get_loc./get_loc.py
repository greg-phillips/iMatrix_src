#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_loc.py
Downloads latitude and longitude history from the iMatrix API for a given serial number and time range,
matches timestamps, and outputs a GeoJSON file suitable for Google Maps.

python3 -m pip install requests urllib3
"""
import argparse
import requests
import sys
import json
from collections import defaultdict
import urllib3
import getpass

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
    parser = argparse.ArgumentParser(description="Download and convert iMatrix location history to GeoJSON.")
    parser.add_argument('-s', '--serial', required=True, help='Device serial number')
    parser.add_argument('-ts', '--start', required=True, help='Start time (epoch ms)')
    parser.add_argument('-te', '--end', required=True, help='End time (epoch ms)')
    parser.add_argument('-u', '--username', required=True, help='iMatrix Cloud username (email)')
    parser.add_argument('-p', '--password', help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-dev', '--dev', action='store_true', help='Use development API endpoint instead of production')
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")

    serial = args.serial
    start = args.start
    end = args.end
    username = args.username

    environment = "development" if args.dev else "production"
    print(f"Starting download for serial: {serial}, from {start} to {end} (using {environment} API)")
    token = login_to_imatrix(username, password, args.dev)
    lat_json = fetch_sensor_history(serial, 2, start, end, token, args.dev)
    lon_json = fetch_sensor_history(serial, 3, start, end, token, args.dev)

    # The API returns a dict: {<serial>: {<sensor_id>: { ... 'data': [ ... ] } } }
    try:
        lat_data = next(iter(lat_json.values()))["2"]["data"]
        lon_data = next(iter(lon_json.values()))["3"]["data"]
    except Exception as e:
        print(f"❌ Error parsing API response: {e}")
        sys.exit(1)

    combined_points = combine_lat_lon(lat_data, lon_data)
    to_geojson(serial, start, combined_points)
    print("Done.")

if __name__ == "__main__":
    main()
