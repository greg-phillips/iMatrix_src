#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_predefined_icons.py - iMatrix Predefined Sensor Icon Downloader

Downloads all predefined sensor definitions from the iMatrix API (IDs 1-999),
retrieves their icons, and generates a static HTML page displaying all sensors
with their icons in a responsive grid layout.

Usage:
    # Default (development API)
    python3 get_predefined_icons.py -u <email>

    # Production API
    python3 get_predefined_icons.py -u <email> -prod

    # With password on command line
    python3 get_predefined_icons.py -u <email> -p <password>

    # Verbose mode
    python3 get_predefined_icons.py -u <email> -v

Dependencies:
    python3 -m pip install requests urllib3
"""

import argparse
import requests
import sys
import json
import os
import getpass
import urllib3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# iMatrix Color Palette
COLORS = {
    'primary_dark': '#005C8C',
    'primary': '#0085B4',
    'light_blue': '#A8D2E3',
    'lighter_blue': '#D8E9F0',
    'near_white': '#F5F9FC',
    'text_dark': '#121212',
}

# Placeholder SVG for missing/failed icons
PLACEHOLDER_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="#D8E9F0" stroke="#A8D2E3" stroke-width="2"/>
  <text x="50" y="45" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#005C8C">No Icon</text>
  <text x="50" y="62" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#0085B4">Available</text>
</svg>'''


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
                print(f"Response: {response.json()}")
                sys.exit(1)
        else:
            print(f"Error: Login failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"Error: Network error during login: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Unexpected error during login: {e}")
        sys.exit(1)


def get_sensor(sensor_id: int, token: str, use_production: bool = False,
               verbose: bool = False) -> Optional[Dict]:
    """
    Fetch sensor details for a specific sensor ID.

    Args:
        sensor_id: Sensor ID to fetch
        token: Authentication token
        use_production: Use production API
        verbose: Print verbose output

    Returns:
        Sensor details dictionary or None if not found
    """
    base_url = get_api_base_url(use_production)
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
            if verbose:
                print(f"  Sensor {sensor_id} not found")
            return None
        else:
            if verbose:
                print(f"  Error fetching sensor {sensor_id}: {response.status_code}")
            return None

    except Exception as e:
        if verbose:
            print(f"  Error fetching sensor {sensor_id}: {e}")
        return None


def download_icon(icon_url: str, sensor_id: int, icons_dir: str,
                  verbose: bool = False) -> Tuple[bool, str]:
    """
    Download an icon from the given URL.

    Args:
        icon_url: URL to download icon from
        sensor_id: Sensor ID for filename
        icons_dir: Directory to save icons
        verbose: Print verbose output

    Returns:
        Tuple of (success, local_filename or error message)
    """
    if not icon_url or icon_url.strip() == '':
        return False, "No icon URL provided"

    try:
        # Parse URL to get file extension
        parsed = urlparse(icon_url)
        path = parsed.path.lower()

        if path.endswith('.svg'):
            ext = 'svg'
        elif path.endswith('.png'):
            ext = 'png'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            ext = 'jpg'
        elif path.endswith('.gif'):
            ext = 'gif'
        else:
            # Default to svg for unknown types
            ext = 'svg'

        local_filename = f"sensor_{sensor_id}.{ext}"
        local_path = os.path.join(icons_dir, local_filename)

        # Download the icon
        response = requests.get(icon_url, timeout=30, verify=False)

        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)

            if verbose:
                print(f"  Downloaded icon for sensor {sensor_id}")

            return True, local_filename
        else:
            return False, f"HTTP {response.status_code}"

    except Exception as e:
        return False, str(e)


def enumerate_sensors(token: str, icons_dir: str, use_production: bool = False,
                      verbose: bool = False) -> List[Dict]:
    """
    Enumerate all sensors from ID 1 to 999 and save JSON data for each.

    Args:
        token: Authentication token
        icons_dir: Directory to save sensor JSON files
        use_production: Use production API
        verbose: Print verbose output

    Returns:
        List of sensor dictionaries
    """
    sensors = []
    total = 999

    # Create icons directory if it doesn't exist
    os.makedirs(icons_dir, exist_ok=True)

    print(f"\nEnumerating sensors 1-{total}...")

    for sensor_id in range(1, total + 1):
        # Progress bar
        progress = int((sensor_id / total) * 50)
        bar = "=" * progress + "-" * (50 - progress)
        percent = int((sensor_id / total) * 100)
        print(f"\r  [{bar}] {percent}% ({sensor_id}/{total})", end="", flush=True)

        sensor = get_sensor(sensor_id, token, use_production, verbose)

        if sensor:
            # Convert 0/1 to false/true for boolean fields
            bool_fields = [
                'minAdvisoryEnabled', 'minWarningEnabled', 'minAlarmEnabled',
                'maxAdvisoryEnabled', 'maxWarningEnabled', 'maxAlarmEnabled'
            ]
            for field in bool_fields:
                if field in sensor:
                    if sensor[field] == 0:
                        sensor[field] = False
                    elif sensor[field] == 1:
                        sensor[field] = True

            sensors.append(sensor)

            # Save sensor JSON to file
            json_filename = os.path.join(icons_dir, f"sensor_{sensor_id}.json")
            try:
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(sensor, f, indent=2)
                if verbose:
                    print(f"\n  Saved sensor_{sensor_id}.json")
            except Exception as e:
                print(f"\n  Warning: Failed to save sensor_{sensor_id}.json: {e}")

    print()  # New line after progress bar
    print(f"Found {len(sensors)} sensors.")

    return sensors


def download_all_icons(sensors: List[Dict], icons_dir: str,
                       verbose: bool = False) -> Tuple[int, int, List[Dict]]:
    """
    Download icons for all sensors.

    Args:
        sensors: List of sensor dictionaries
        icons_dir: Directory to save icons
        verbose: Print verbose output

    Returns:
        Tuple of (success_count, failure_count, updated_sensors)
    """
    # Create icons directory
    os.makedirs(icons_dir, exist_ok=True)

    # Create placeholder icon
    placeholder_path = os.path.join(icons_dir, "placeholder.svg")
    with open(placeholder_path, 'w') as f:
        f.write(PLACEHOLDER_SVG)

    success_count = 0
    failure_count = 0
    updated_sensors = []

    print(f"\nDownloading icons for {len(sensors)} sensors...")

    for i, sensor in enumerate(sensors, 1):
        sensor_id = sensor.get('id', 0)
        icon_url = sensor.get('iconUrl', '')

        # Progress
        progress = int((i / len(sensors)) * 50)
        bar = "=" * progress + "-" * (50 - progress)
        percent = int((i / len(sensors)) * 100)
        print(f"\r  [{bar}] {percent}% ({i}/{len(sensors)})", end="", flush=True)

        if icon_url and icon_url.strip():
            success, result = download_icon(icon_url, sensor_id, icons_dir, verbose)
            if success:
                sensor['local_icon'] = f"icons/{result}"
                success_count += 1
            else:
                print(f"\n  Warning: Failed to download icon for sensor {sensor_id}: {result}")
                sensor['local_icon'] = "icons/placeholder.svg"
                failure_count += 1
        else:
            sensor['local_icon'] = "icons/placeholder.svg"
            failure_count += 1

        updated_sensors.append(sensor)

    print()  # New line after progress bar
    print(f"Downloaded {success_count} icons, {failure_count} using placeholder.")

    return success_count, failure_count, updated_sensors


def generate_html(sensors: List[Dict], logo_path: str, output_file: str) -> str:
    """
    Generate the HTML page with sensor icons.

    Args:
        sensors: List of sensor dictionaries with local_icon paths
        logo_path: Path to iMatrix logo
        output_file: Output HTML filename

    Returns:
        Full path to generated HTML file
    """
    # Sort sensors by ID
    sorted_sensors = sorted(sensors, key=lambda s: s.get('id', 0))

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iMatrix Internal Sensor Icons</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: Arial, sans-serif;
            background-color: {COLORS['near_white']};
            color: {COLORS['text_dark']};
            min-height: 100vh;
        }}

        header {{
            background-color: {COLORS['primary_dark']};
            color: white;
            padding: 20px 40px;
            display: flex;
            align-items: center;
            gap: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        header img {{
            height: 60px;
            width: auto;
        }}

        header h1 {{
            font-size: 24px;
            font-weight: normal;
        }}

        .stats {{
            background-color: {COLORS['lighter_blue']};
            padding: 10px 40px;
            font-size: 14px;
            color: {COLORS['primary_dark']};
            border-bottom: 1px solid {COLORS['light_blue']};
        }}

        .container {{
            padding: 30px 40px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 20px;
        }}

        .sensor-card {{
            background-color: white;
            border: 1px solid {COLORS['light_blue']};
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            transition: box-shadow 0.2s, transform 0.2s;
        }}

        .sensor-card:hover {{
            box-shadow: 0 4px 12px rgba(0, 92, 140, 0.15);
            transform: translateY(-2px);
        }}

        .sensor-card img {{
            width: 100px;
            height: 100px;
            object-fit: contain;
            margin-bottom: 10px;
        }}

        .sensor-card .label {{
            font-size: 8pt;
            color: {COLORS['text_dark']};
            word-wrap: break-word;
            line-height: 1.3;
        }}

        footer {{
            background-color: {COLORS['primary_dark']};
            color: white;
            text-align: center;
            padding: 15px;
            font-size: 12px;
            margin-top: 40px;
        }}

        /* Popup tooltip styles */
        .popup {{
            display: none;
            position: fixed;
            background-color: white;
            border: 2px solid {COLORS['primary']};
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 8px 24px rgba(0, 92, 140, 0.25);
            z-index: 1000;
            max-width: 400px;
            max-height: 80vh;
            overflow-y: auto;
            font-size: 12px;
        }}

        .popup.visible {{
            display: block;
        }}

        .popup h3 {{
            color: {COLORS['primary_dark']};
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid {COLORS['light_blue']};
            font-size: 14px;
        }}

        .popup table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .popup td {{
            padding: 4px 8px;
            vertical-align: top;
        }}

        .popup td:first-child {{
            font-weight: bold;
            color: {COLORS['primary_dark']};
            white-space: nowrap;
            width: 40%;
        }}

        .popup td:last-child {{
            color: {COLORS['text_dark']};
            word-break: break-word;
        }}

        .popup tr:nth-child(even) {{
            background-color: {COLORS['near_white']};
        }}

        .popup .close-btn {{
            position: absolute;
            top: 8px;
            right: 10px;
            cursor: pointer;
            font-size: 18px;
            color: {COLORS['primary']};
        }}

        .popup .close-btn:hover {{
            color: {COLORS['primary_dark']};
        }}
    </style>
</head>
<body>
    <header>
        <img src="{logo_path}" alt="iMatrix Logo">
        <h1>iMatrix Internal Sensor Icons</h1>
    </header>

    <div class="stats">
        Total Sensors: {len(sorted_sensors)} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>

    <div class="container">
        <div class="grid">
'''

    # Generate sensor cards
    for sensor in sorted_sensors:
        sensor_id = sensor.get('id', 0)
        sensor_name = sensor.get('name', 'Unknown')
        local_icon = sensor.get('local_icon', 'icons/placeholder.svg')

        # Escape HTML in name
        safe_name = sensor_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Prepare sensor data as JSON for the popup (escape for HTML attribute)
        sensor_json = json.dumps(sensor).replace('"', '&quot;')

        html_content += f'''            <div class="sensor-card" data-sensor="{sensor_json}">
                <img src="{local_icon}" alt="{safe_name}" onerror="this.src='icons/placeholder.svg'">
                <div class="label">{sensor_id}:{safe_name}</div>
            </div>
'''

    html_content += '''        </div>
    </div>

    <!-- Popup for sensor details -->
    <div id="sensor-popup" class="popup">
        <span class="close-btn" onclick="hidePopup()">&times;</span>
        <h3 id="popup-title">Sensor Details</h3>
        <table id="popup-content"></table>
    </div>

    <footer>
        iMatrix Systems - Predefined Sensor Icons
    </footer>

    <script>
        let hoverTimer = null;
        let currentCard = null;
        const popup = document.getElementById('sensor-popup');
        const popupTitle = document.getElementById('popup-title');
        const popupContent = document.getElementById('popup-content');

        // Field display names (friendly names for API fields)
        const fieldNames = {
            'id': 'Sensor ID',
            'productId': 'Product ID',
            'platformId': 'Platform ID',
            'name': 'Name',
            'type': 'Type',
            'units': 'Units',
            'unitsType': 'Units Type',
            'dataType': 'Data Type',
            'mode': 'Mode',
            'defaultValue': 'Default Value',
            'iconUrl': 'Icon URL',
            'thresholdQualificationTime': 'Threshold Qualification Time',
            'minAdvisoryEnabled': 'Min Advisory Enabled',
            'minAdvisory': 'Min Advisory',
            'minWarningEnabled': 'Min Warning Enabled',
            'minWarning': 'Min Warning',
            'minAlarmEnabled': 'Min Alarm Enabled',
            'minAlarm': 'Min Alarm',
            'maxAdvisoryEnabled': 'Max Advisory Enabled',
            'maxAdvisory': 'Max Advisory',
            'maxWarningEnabled': 'Max Warning Enabled',
            'maxWarning': 'Max Warning',
            'maxAlarmEnabled': 'Max Alarm Enabled',
            'maxAlarm': 'Max Alarm',
            'maxGraph': 'Max Graph',
            'minGraph': 'Min Graph',
            'calibrationRef1': 'Calibration Ref 1',
            'calibrationRef2': 'Calibration Ref 2',
            'calibrationRef3': 'Calibration Ref 3',
            'local_icon': 'Local Icon Path'
        };

        // Format value for display
        function formatValue(value) {
            if (value === null || value === undefined) return '<em>null</em>';
            if (value === '') return '<em>empty</em>';
            if (typeof value === 'boolean') return value ? 'Yes' : 'No';
            if (Array.isArray(value)) return value.join(', ');
            if (typeof value === 'object') return JSON.stringify(value);
            return String(value);
        }

        // Show popup with sensor details
        function showPopup(card, event) {
            const sensorData = JSON.parse(card.dataset.sensor.replace(/&quot;/g, '"'));

            popupTitle.textContent = sensorData.name || 'Sensor Details';

            // Build table rows
            let rows = '';
            for (const [key, value] of Object.entries(sensorData)) {
                const displayName = fieldNames[key] || key;
                const displayValue = formatValue(value);
                rows += `<tr><td>${displayName}</td><td>${displayValue}</td></tr>`;
            }
            popupContent.innerHTML = rows;

            // Position popup near the card but ensure it stays in viewport
            const rect = card.getBoundingClientRect();
            let left = rect.right + 10;
            let top = rect.top;

            // Check if popup would go off right edge
            if (left + 400 > window.innerWidth) {
                left = rect.left - 410;
            }
            // If still off screen, center it
            if (left < 10) {
                left = Math.max(10, (window.innerWidth - 400) / 2);
            }

            // Check if popup would go off bottom
            if (top + 300 > window.innerHeight) {
                top = Math.max(10, window.innerHeight - 350);
            }

            popup.style.left = left + 'px';
            popup.style.top = top + 'px';
            popup.classList.add('visible');
        }

        // Hide popup
        function hidePopup() {
            popup.classList.remove('visible');
            if (hoverTimer) {
                clearTimeout(hoverTimer);
                hoverTimer = null;
            }
            currentCard = null;
        }

        // Add event listeners to all sensor cards
        document.querySelectorAll('.sensor-card').forEach(card => {
            card.addEventListener('mouseenter', function(e) {
                currentCard = this;
                hoverTimer = setTimeout(() => {
                    showPopup(this, e);
                }, 2000); // 2 second delay
            });

            card.addEventListener('mouseleave', function() {
                if (hoverTimer) {
                    clearTimeout(hoverTimer);
                    hoverTimer = null;
                }
                // Don't hide if mouse moved to popup
                setTimeout(() => {
                    if (!popup.matches(':hover') && currentCard === this) {
                        hidePopup();
                    }
                }, 100);
            });
        });

        // Hide popup when clicking outside
        document.addEventListener('click', function(e) {
            if (!popup.contains(e.target) && !e.target.closest('.sensor-card')) {
                hidePopup();
            }
        });

        // Keep popup visible when hovering over it
        popup.addEventListener('mouseenter', function() {
            if (hoverTimer) {
                clearTimeout(hoverTimer);
                hoverTimer = null;
            }
        });

        popup.addEventListener('mouseleave', function() {
            hidePopup();
        });
    </script>
</body>
</html>
'''

    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return os.path.abspath(output_file)


def save_metadata(sensors: List[Dict], output_file: str) -> None:
    """
    Save sensor metadata to a JSON file.

    Args:
        sensors: List of sensor dictionaries
        output_file: Output JSON filename
    """
    metadata = {
        'generated': datetime.now().isoformat(),
        'total_sensors': len(sensors),
        'sensors': []
    }

    for sensor in sorted(sensors, key=lambda s: s.get('id', 0)):
        metadata['sensors'].append({
            'id': sensor.get('id'),
            'name': sensor.get('name'),
            'units': sensor.get('units'),
            'type': sensor.get('type'),
            'dataType': sensor.get('dataType'),
            'iconUrl': sensor.get('iconUrl'),
            'local_icon': sensor.get('local_icon')
        })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to: {output_file}")


def main():
    """Main function to orchestrate the icon download and HTML generation."""

    parser = argparse.ArgumentParser(
        description="Download iMatrix predefined sensor icons and generate HTML page",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default (development API)
  %(prog)s -u user@example.com

  # Production API
  %(prog)s -u user@example.com -prod

  # Verbose mode
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
                       help='Enable verbose output')

    args = parser.parse_args()

    # Get script directory for relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(script_dir, 'icons')
    logo_path = 'iMatrix_logo.jpg'
    output_html = os.path.join(script_dir, 'imatrix_predefined.html')
    output_json = os.path.join(script_dir, 'sensor_metadata.json')

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")

    print("=" * 60)
    print("iMatrix Predefined Sensor Icon Downloader")
    print("=" * 60)

    # Login
    token = login_to_imatrix(args.username, password, args.production)

    # Enumerate sensors and save JSON files
    sensors = enumerate_sensors(token, icons_dir, args.production, args.verbose)

    if not sensors:
        print("No sensors found. Exiting.")
        sys.exit(1)

    # Download icons
    success, failures, updated_sensors = download_all_icons(
        sensors, icons_dir, args.verbose
    )

    # Save metadata
    save_metadata(updated_sensors, output_json)

    # Generate HTML
    print("\nGenerating HTML page...")
    html_path = generate_html(updated_sensors, logo_path, output_html)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total sensors found:    {len(sensors)}")
    print(f"JSON files saved:       {len(sensors)} (icons/sensor_<id>.json)")
    print(f"Icons downloaded:       {success}")
    print(f"Using placeholder:      {failures}")
    print(f"HTML output:            {html_path}")
    print(f"Linux URL:              file://{html_path}")
    print(f"Windows URL:            file:///U:/{html_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
