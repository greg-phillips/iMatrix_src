#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_public_products.py - Download public product data and generate HTML catalog

Connects to the iMatrix API and retrieves all public products via GET /products/public.
Downloads the three image types (iconUrl, imageUrl, defaultImage) for each product
and generates an interactive HTML catalog page.

Usage:
    # Basic usage (development API, prompts for password)
    python3 get_public_products.py -u user@example.com

    # With password on command line
    python3 get_public_products.py -u user@example.com -p mypassword

    # Use production API
    python3 get_public_products.py -u user@example.com -prod

    # Verbose output
    python3 get_public_products.py -u user@example.com -v

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
from datetime import datetime
from typing import Optional, List, Tuple

# Disable SSL certificate warnings (only for development use!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# iMatrix color palette
COLORS = {
    'primary_dark': '#005C8C',
    'primary': '#0085B4',
    'light_blue': '#A8D2E3',
    'lighter_blue': '#D8E9F0',
    'near_white': '#F5F9FC',
    'text_dark': '#121212',
}


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


def get_public_products(token: str, base_url: str) -> List[dict]:
    """
    Fetch all public products from the API.

    Args:
        token: Authentication token
        base_url: API base URL

    Returns:
        List of product dictionaries
    """
    url = f"{base_url}/products/public"

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    print("Fetching public products...")

    try:
        response = requests.get(url, timeout=60, verify=False, headers=headers)

        if response.status_code == 200:
            products = response.json()
            print(f"Found {len(products)} public products.")
            return products
        else:
            print(f"Error: Failed to get public products: {response.status_code}")
            print(f"Response: {response.text}")
            return []

    except Exception as e:
        print(f"Error: Failed to get public products: {e}")
        return []


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
        else:
            return None

    except Exception:
        return None


def get_product_default_config(product_id: int, token: str, base_url: str) -> Optional[dict]:
    """
    Fetch default config for a specific product.

    Uses GET /admin/products/configs/default/{id} to get the default configuration
    which contains the order and visibility settings for controls/sensors.

    Args:
        product_id: Product ID to fetch config for
        token: Authentication token
        base_url: API base URL

    Returns:
        Config dictionary with 'order' list containing {id, visible} objects, or None if not found
    """
    url = f"{base_url}/admin/products/configs/default/{product_id}"

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.get(url, timeout=30, verify=False, headers=headers)

        if response.status_code == 200:
            result = response.json()
            # API may return a list with productId and userConfig, or directly the config
            if isinstance(result, list) and len(result) > 0:
                # Find the config for this product
                for item in result:
                    if item.get('productId') == product_id:
                        return item.get('userConfig', {})
                # If not found by productId, return first item's userConfig
                return result[0].get('userConfig', {})
            elif isinstance(result, dict):
                # Direct config object
                if 'userConfig' in result:
                    return result.get('userConfig', {})
                return result
            return None
        else:
            return None

    except Exception:
        return None


def fetch_default_configs_for_products(products: List[dict], token: str, base_url: str,
                                        verbose: bool = False) -> dict:
    """
    Fetch default configs for all products.

    Args:
        products: List of product dictionaries
        token: Authentication token
        base_url: API base URL
        verbose: Enable verbose output

    Returns:
        Dictionary mapping product ID to default config (order list with id/visible)
    """
    print(f"\nFetching default configs for {len(products)} products...")

    configs_by_product = {}
    total = len(products)

    for idx, product in enumerate(products):
        product_id = product.get('id', 0)

        # Progress bar
        progress = int(((idx + 1) / total) * 50)
        bar = "=" * progress + "-" * (50 - progress)
        percent = int(((idx + 1) / total) * 100)
        print(f"\r  [{bar}] {percent}% ({idx + 1}/{total})", end="", flush=True)

        config = get_product_default_config(product_id, token, base_url)
        if config:
            configs_by_product[product_id] = config
            if verbose:
                order = config.get('order', [])
                print(f"\n  Product {product_id}: {len(order)} items in config order")

    print()  # New line after progress bar
    configured = sum(1 for c in configs_by_product.values() if c)
    print(f"Found default configs for {configured} products.")

    return configs_by_product


def get_predefined_sensors_by_product(product_id: int, token: str, base_url: str) -> List[int]:
    """
    Fetch predefined sensor IDs for a specific product.

    Args:
        product_id: Product ID to fetch predefined sensors for
        token: Authentication token
        base_url: API base URL

    Returns:
        List of predefined sensor IDs
    """
    url = f"{base_url}/sensors/predefined/product/{product_id}"

    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }

    try:
        response = requests.get(url, timeout=30, verify=False, headers=headers)

        if response.status_code == 200:
            result = response.json()
            # API may return list of sensor objects or list of IDs
            if isinstance(result, list):
                if len(result) > 0 and isinstance(result[0], dict):
                    return [s.get('id') for s in result if s.get('id')]
                else:
                    return [s for s in result if isinstance(s, int)]
            return []
        else:
            return []

    except Exception:
        return []


def fetch_predefined_sensors_for_products(products: List[dict], token: str, base_url: str,
                                          verbose: bool = False) -> dict:
    """
    Fetch predefined sensor IDs for all products.

    Args:
        products: List of product dictionaries
        token: Authentication token
        base_url: API base URL
        verbose: Enable verbose output

    Returns:
        Dictionary mapping product ID to list of predefined sensor IDs
    """
    print(f"\nFetching predefined sensors for {len(products)} products...")

    predefined_by_product = {}
    total = len(products)

    for idx, product in enumerate(products):
        product_id = product.get('id', 0)

        # Progress bar
        progress = int(((idx + 1) / total) * 50)
        bar = "=" * progress + "-" * (50 - progress)
        percent = int(((idx + 1) / total) * 100)
        print(f"\r  [{bar}] {percent}% ({idx + 1}/{total})", end="", flush=True)

        predefined_ids = get_predefined_sensors_by_product(product_id, token, base_url)
        predefined_by_product[product_id] = predefined_ids

        if verbose and predefined_ids:
            print(f"\n  Product {product_id}: {len(predefined_ids)} predefined sensors")

    print()  # New line after progress bar
    total_predefined = sum(len(ids) for ids in predefined_by_product.values())
    print(f"Found {total_predefined} predefined sensor references across all products.")

    return predefined_by_product


def fetch_all_sensors(products: List[dict], predefined_by_product: dict, token: str, base_url: str,
                      verbose: bool = False) -> dict:
    """
    Fetch sensor data for all sensors referenced in products (both control and predefined).

    Args:
        products: List of product dictionaries
        predefined_by_product: Dictionary mapping product ID to predefined sensor IDs
        token: Authentication token
        base_url: API base URL
        verbose: Enable verbose output

    Returns:
        Dictionary mapping sensor ID to sensor data
    """
    # Collect all unique sensor IDs from controlSensorIds
    sensor_ids = set()
    for product in products:
        control_sensor_ids = product.get('controlSensorIds', [])
        if control_sensor_ids:
            for sid in control_sensor_ids:
                if sid and isinstance(sid, int):
                    sensor_ids.add(sid)

    # Also collect predefined sensor IDs
    for product_id, predefined_ids in predefined_by_product.items():
        for sid in predefined_ids:
            if sid and isinstance(sid, int):
                sensor_ids.add(sid)

    if not sensor_ids:
        print("No sensor IDs found in products.")
        return {}

    print(f"\nFetching data for {len(sensor_ids)} unique sensors...")

    sensor_data = {}
    total = len(sensor_ids)
    sensor_list = sorted(sensor_ids)

    for idx, sensor_id in enumerate(sensor_list):
        # Progress bar
        progress = int(((idx + 1) / total) * 50)
        bar = "=" * progress + "-" * (50 - progress)
        percent = int(((idx + 1) / total) * 100)
        print(f"\r  [{bar}] {percent}% ({idx + 1}/{total})", end="", flush=True)

        sensor = get_sensor(sensor_id, token, base_url)
        if sensor:
            sensor_data[sensor_id] = sensor
            if verbose:
                print(f"\n  Fetched sensor {sensor_id}: {sensor.get('name', 'Unknown')}")

    print()  # New line after progress bar
    print(f"Fetched {len(sensor_data)} sensor definitions.")

    return sensor_data


def download_image(url: str, product_id: int, image_type: str, output_dir: str,
                   verbose: bool = False) -> Tuple[bool, str]:
    """
    Download an image from a URL and save it locally.

    Args:
        url: URL of the image to download
        product_id: Product ID (for filename)
        image_type: Type of image (icon, image, default)
        output_dir: Directory to save the image
        verbose: Enable verbose output

    Returns:
        Tuple of (success, local_filename or error_message)
    """
    if not url or url == "string" or url.strip() == "":
        return False, "No URL provided"

    try:
        # Determine file extension from URL
        ext = os.path.splitext(url.split('?')[0])[1].lower()
        if not ext or ext not in ['.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp']:
            ext = '.png'  # Default extension

        filename = f"product_{product_id}_{image_type}{ext}"
        filepath = os.path.join(output_dir, filename)

        response = requests.get(url, timeout=30, verify=False)

        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            if verbose:
                print(f"  Downloaded: {filename}")
            return True, filename
        else:
            return False, f"HTTP {response.status_code}"

    except Exception as e:
        return False, str(e)


def download_all_images(products: List[dict], output_dir: str,
                        verbose: bool = False) -> Tuple[int, int, List[dict]]:
    """
    Download all images for all products.

    Args:
        products: List of product dictionaries
        output_dir: Directory to save images
        verbose: Enable verbose output

    Returns:
        Tuple of (success_count, failure_count, updated_products)
    """
    success_count = 0
    failure_count = 0
    updated_products = []

    total = len(products)
    print(f"\nDownloading images for {total} products...")

    for idx, product in enumerate(products):
        # Progress bar
        progress = int(((idx + 1) / total) * 50)
        bar = "=" * progress + "-" * (50 - progress)
        percent = int(((idx + 1) / total) * 100)
        print(f"\r  [{bar}] {percent}% ({idx + 1}/{total})", end="", flush=True)

        product_id = product.get('id', 0)
        updated_product = product.copy()

        # Download each image type
        image_fields = [
            ('iconUrl', 'icon'),
            ('imageUrl', 'image'),
            ('defaultImage', 'default')
        ]

        for field_name, image_type in image_fields:
            url = product.get(field_name)
            if url and url != "string" and url.strip():
                success, result = download_image(url, product_id, image_type,
                                                 output_dir, verbose)
                if success:
                    updated_product[f'local_{image_type}'] = result
                    success_count += 1
                else:
                    updated_product[f'local_{image_type}'] = None
                    failure_count += 1
            else:
                updated_product[f'local_{image_type}'] = None

        updated_products.append(updated_product)

    print()  # New line after progress bar
    return success_count, failure_count, updated_products


def create_placeholder_svg(output_dir: str) -> str:
    """Create a placeholder SVG for missing images."""
    placeholder = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="#D8E9F0" stroke="#A8D2E3" stroke-width="2"/>
  <text x="50" y="45" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#005C8C">No Image</text>
  <text x="50" y="62" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#0085B4">Available</text>
</svg>'''

    filepath = os.path.join(output_dir, "placeholder.svg")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(placeholder)

    return "placeholder.svg"


def generate_html(products: List[dict], sensor_data: dict, predefined_by_product: dict,
                  configs_by_product: dict, logo_path: str, output_file: str) -> str:
    """
    Generate an HTML page displaying all products with their images.

    Args:
        products: List of product dictionaries with local image paths
        sensor_data: Dictionary mapping sensor ID to sensor data
        predefined_by_product: Dictionary mapping product ID to predefined sensor IDs
        configs_by_product: Dictionary mapping product ID to default config with order/visibility
        logo_path: Path to the iMatrix logo
        output_file: Output HTML filename

    Returns:
        Full path to generated HTML file
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_file)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iMatrix Public Products</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: {COLORS['near_white']};
            color: {COLORS['text_dark']};
            line-height: 1.6;
        }}
        .header {{
            background-color: {COLORS['primary_dark']};
            color: white;
            padding: 20px 40px;
            display: flex;
            align-items: center;
            gap: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        .header img {{
            height: 50px;
            width: auto;
        }}
        .header h1 {{
            font-size: 24px;
            font-weight: 600;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 30px 40px;
        }}
        .products-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }}
        .product-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            border: 1px solid {COLORS['light_blue']};
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
        }}
        .product-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0, 92, 140, 0.15);
        }}
        .product-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid {COLORS['lighter_blue']};
        }}
        .product-icon {{
            width: 60px;
            height: 60px;
            object-fit: contain;
            border-radius: 8px;
            background: {COLORS['near_white']};
            padding: 5px;
        }}
        .product-info {{
            flex: 1;
        }}
        .product-name {{
            font-size: 16px;
            font-weight: 600;
            color: {COLORS['primary_dark']};
            margin-bottom: 4px;
        }}
        .product-id {{
            font-size: 12px;
            color: {COLORS['primary']};
        }}
        .product-short {{
            font-size: 11px;
            color: #666;
        }}
        .images-section {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }}
        .image-container {{
            text-align: center;
        }}
        .image-label {{
            font-size: 10px;
            color: {COLORS['primary']};
            margin-bottom: 5px;
            font-weight: 500;
        }}
        .product-image {{
            width: 100%;
            height: 80px;
            object-fit: contain;
            border-radius: 6px;
            background: {COLORS['near_white']};
            border: 1px solid {COLORS['lighter_blue']};
        }}
        .product-details {{
            font-size: 11px;
            color: #666;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 5px;
        }}
        .detail-item {{
            display: flex;
            justify-content: space-between;
        }}
        .detail-label {{
            color: {COLORS['primary']};
        }}
        /* Favorites styles */
        .favorites-toggle {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 20px;
            background: {COLORS['lighter_blue']};
            border: 2px solid {COLORS['light_blue']};
            color: {COLORS['primary_dark']};
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            margin-left: auto;
        }}
        .favorites-toggle:hover {{
            background: {COLORS['light_blue']};
        }}
        .favorites-toggle.active {{
            background: #FFD700;
            border-color: #DAA520;
            color: #5D4E00;
        }}
        .favorites-toggle .star {{
            font-size: 18px;
        }}
        .favorite-btn {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #ccc;
            transition: color 0.2s, transform 0.2s;
            z-index: 5;
        }}
        .favorite-btn:hover {{
            transform: scale(1.2);
        }}
        .favorite-btn.favorited {{
            color: #FFD700;
        }}
        /* Config match indicator */
        .config-match-indicator {{
            position: absolute;
            top: 10px;
            right: 45px;
            font-size: 20px;
            z-index: 5;
            cursor: help;
        }}
        .config-match-indicator.matched {{
            color: #28a745;
        }}
        .config-match-indicator.mismatched {{
            color: #dc3545;
        }}
        .config-match-tooltip {{
            display: none;
            position: absolute;
            top: 100%;
            right: 0;
            background: {COLORS['primary_dark']};
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 11px;
            white-space: nowrap;
            z-index: 100;
            margin-top: 5px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            max-width: 300px;
            white-space: normal;
        }}
        .config-match-indicator:hover .config-match-tooltip {{
            display: block;
        }}
        /* Visible indicator in sensor popup */
        .sensor-visible-indicator {{
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 10px;
            margin-top: 4px;
        }}
        .sensor-visible-indicator.visible {{
            background: #d4edda;
            color: #155724;
        }}
        .sensor-visible-indicator.hidden {{
            background: #f8d7da;
            color: #721c24;
        }}
        .product-card.hidden {{
            display: none;
        }}
        .stats-bar {{
            background-color: {COLORS['lighter_blue']};
            padding: 10px 40px;
            font-size: 14px;
            color: {COLORS['primary_dark']};
            border-bottom: 1px solid {COLORS['light_blue']};
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .stats-info {{
            display: flex;
            gap: 20px;
        }}
        .sensors-section {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid {COLORS['lighter_blue']};
        }}
        .sensors-label {{
            font-size: 11px;
            color: {COLORS['primary']};
            font-weight: 500;
            margin-bottom: 8px;
        }}
        .sensor-icons {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .sensor-icon-wrapper {{
            position: relative;
            width: 32px;
            height: 32px;
            border-radius: 4px;
            background: {COLORS['near_white']};
            border: 1px solid {COLORS['lighter_blue']};
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .sensor-icon-wrapper:hover {{
            transform: scale(1.1);
            box-shadow: 0 2px 8px rgba(0, 92, 140, 0.2);
            z-index: 10;
        }}
        .sensor-icon-img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            padding: 2px;
        }}
        .sensor-tooltip {{
            display: none;
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: {COLORS['primary_dark']};
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 11px;
            white-space: nowrap;
            z-index: 100;
            margin-bottom: 5px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }}
        .sensor-tooltip::after {{
            content: '';
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 6px solid transparent;
            border-top-color: {COLORS['primary_dark']};
        }}
        .sensor-icon-wrapper:hover .sensor-tooltip {{
            display: block;
        }}
        .sensor-tooltip-id {{
            color: {COLORS['light_blue']};
            font-size: 10px;
        }}
        .no-sensors-msg {{
            font-size: 11px;
            color: #999;
            font-style: italic;
        }}
        .sensor-more-indicator {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 50px;
            height: 32px;
            border-radius: 4px;
            background: {COLORS['light_blue']};
            border: 1px solid {COLORS['primary']};
            color: {COLORS['primary_dark']};
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .sensor-more-indicator:hover {{
            background: {COLORS['primary']};
            color: white;
        }}
        .footer {{
            background-color: {COLORS['primary_dark']};
            color: white;
            text-align: center;
            padding: 20px;
            margin-top: 40px;
            font-size: 14px;
        }}
        /* Popup styles */
        .popup {{
            display: none;
            position: fixed;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            border: 2px solid {COLORS['primary']};
            z-index: 1000;
            max-width: 500px;
            max-height: 80vh;
            overflow-y: auto;
        }}
        .popup-header {{
            background: {COLORS['primary_dark']};
            color: white;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
        }}
        .popup-title {{
            font-weight: 600;
            font-size: 14px;
        }}
        .popup-close {{
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0 5px;
        }}
        .popup-content {{
            padding: 16px;
        }}
        .popup-table {{
            width: 100%;
            font-size: 12px;
            border-collapse: collapse;
        }}
        .popup-table tr:nth-child(even) {{
            background: {COLORS['near_white']};
        }}
        .popup-table td {{
            padding: 6px 10px;
            border-bottom: 1px solid {COLORS['lighter_blue']};
        }}
        .popup-table td:first-child {{
            font-weight: 500;
            color: {COLORS['primary_dark']};
            width: 40%;
        }}
        .popup-table td:last-child {{
            word-break: break-all;
        }}
        /* Sensor popup styles */
        .sensor-popup {{
            display: none;
            position: fixed;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            border: 2px solid {COLORS['primary']};
            z-index: 1001;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
        }}
        .sensor-popup-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 12px;
            padding: 16px;
        }}
        .sensor-popup-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 10px;
            border-radius: 8px;
            background: {COLORS['near_white']};
            border: 1px solid {COLORS['lighter_blue']};
        }}
        .sensor-popup-icon {{
            width: 48px;
            height: 48px;
            object-fit: contain;
            margin-bottom: 8px;
        }}
        .sensor-popup-name {{
            font-size: 11px;
            font-weight: 500;
            color: {COLORS['primary_dark']};
            line-height: 1.3;
        }}
        .sensor-popup-id {{
            font-size: 10px;
            color: {COLORS['primary']};
        }}
    </style>
</head>
<body>
    <div class="header">
        <img src="{logo_path}" alt="iMatrix Logo">
        <h1>iMatrix Public Products</h1>
    </div>
    <div class="stats-bar">
        <div class="stats-info">
            <span>Total Products: {len(products)}</span>
            <span>|</span>
            <span>Generated: {timestamp}</span>
            <span>|</span>
            <span id="favorites-count">Favorites: 0</span>
        </div>
        <button class="favorites-toggle" id="favorites-toggle" onclick="toggleFavoritesFilter()">
            <span class="star">&#9734;</span>
            <span>Show Favorites</span>
        </button>
    </div>
    <div class="container">
        <script>
            // Declare data objects before product cards populate them
            const productData = {{}};
            const sensorData = {{}};
        </script>
        <div class="products-grid">
'''

    # Generate product cards
    for product in products:
        product_id = product.get('id', 0)
        name = product.get('name', 'Unknown')
        short_name = product.get('shortName', '')
        no_sensors = product.get('noSensors', 0)
        no_controls = product.get('noControls', 0)

        # Get local image paths
        icon_src = f"products/{product.get('local_icon', 'placeholder.svg')}" if product.get('local_icon') else "products/placeholder.svg"
        image_src = f"products/{product.get('local_image', 'placeholder.svg')}" if product.get('local_image') else "products/placeholder.svg"
        default_src = f"products/{product.get('local_default', 'placeholder.svg')}" if product.get('local_default') else "products/placeholder.svg"

        # Escape special characters for JSON
        product_json = json.dumps(product, indent=2, default=str).replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

        # Get default config for this product (order and visibility)
        product_config = configs_by_product.get(product_id, {})
        config_order = product_config.get('order', [])

        # Build a mapping of sensor id to visibility and order position
        config_map = {}  # id -> {visible, order}
        for idx, item in enumerate(config_order):
            sid = item.get('id')
            if sid is not None:
                config_map[sid] = {
                    'visible': item.get('visible', True),
                    'order': idx
                }

        # Generate sensor icons HTML (show first 5 only, rest on hover)
        control_sensor_ids = product.get('controlSensorIds', [])
        valid_sensor_ids = [sid for sid in control_sensor_ids if sid and isinstance(sid, int)]

        # Sort sensors by config order (sensors not in config go to the end)
        def get_sort_key(sid):
            if sid in config_map:
                return (0, config_map[sid]['order'])
            return (1, sid)  # Not in config, sort by ID at the end

        sorted_sensor_ids = sorted(valid_sensor_ids, key=get_sort_key)
        total_sensors = len(sorted_sensor_ids)
        display_limit = 5

        # Get predefined sensors for this product and sort them too
        predefined_ids = predefined_by_product.get(product_id, [])
        valid_predefined_ids = [sid for sid in predefined_ids if sid and isinstance(sid, int)]
        sorted_predefined_ids = sorted(valid_predefined_ids, key=get_sort_key)
        total_predefined = len(sorted_predefined_ids)

        # Check if sensors match the config (full set: predefined + product sensors)
        config_ids = set(config_map.keys())
        predefined_sensor_ids = set(valid_predefined_ids)

        # Full set of product sensors = controlSensorIds + predefined sensors
        all_product_sensor_ids = set(valid_sensor_ids) | predefined_sensor_ids

        # Match means: config IDs match the full set of product sensors
        missing_from_config = all_product_sensor_ids - config_ids  # In product but not in config
        extra_in_config = config_ids - all_product_sensor_ids  # In config but not in product
        config_match = len(missing_from_config) == 0 and len(extra_in_config) == 0

        # For display: exclude predefined sensors from the "Sensors" list (they show separately)
        display_sensor_ids = [sid for sid in sorted_sensor_ids if sid not in predefined_sensor_ids]
        total_display_sensors = len(display_sensor_ids)

        # Build match indicator HTML
        if config_order:  # Only show indicator if we have a config
            if config_match:
                match_indicator_class = "matched"
                match_indicator_symbol = "&#10004;"  # Green checkmark
                match_tooltip = "All sensors match the default config"
            else:
                match_indicator_class = "mismatched"
                match_indicator_symbol = "&#10008;"  # Red X
                tooltip_parts = []
                if missing_from_config:
                    tooltip_parts.append(f"Missing from config: {sorted(missing_from_config)}")
                if extra_in_config:
                    tooltip_parts.append(f"Extra in config: {sorted(extra_in_config)}")
                match_tooltip = "<br>".join(tooltip_parts)

            match_indicator_html = f'''
                <div class="config-match-indicator {match_indicator_class}" title="Config match status">
                    {match_indicator_symbol}
                    <div class="config-match-tooltip">{match_tooltip}</div>
                </div>'''
        else:
            match_indicator_html = ''  # No config available

        # --- Control Sensors Section (excluding predefined sensors) ---
        sensors_html = '<div class="sensors-section">'
        sensors_html += f'<div class="sensors-label">Sensors ({total_display_sensors}):</div>'
        sensors_html += '<div class="sensor-icons">'

        if display_sensor_ids:
            # Show first 5 sensors (sorted by config order, excluding predefined)
            for idx, sid in enumerate(display_sensor_ids[:display_limit]):
                if sid in sensor_data:
                    sensor = sensor_data[sid]
                    sensor_name = sensor.get('name', f'Sensor {sid}')
                    sensor_icon_url = sensor.get('iconUrl', '')
                    if sensor_icon_url and sensor_icon_url != "string":
                        icon_url = sensor_icon_url
                    else:
                        icon_url = "products/placeholder.svg"
                else:
                    sensor_name = f'Sensor {sid}'
                    icon_url = "products/placeholder.svg"

                sensors_html += f'''
                        <div class="sensor-icon-wrapper">
                            <img src="{icon_url}" alt="{sensor_name}" class="sensor-icon-img" onerror="this.src='products/placeholder.svg'">
                            <div class="sensor-tooltip">
                                <div>{sensor_name}</div>
                                <div class="sensor-tooltip-id">ID: {sid}</div>
                            </div>
                        </div>'''

            # Add "+N more" indicator if there are more than 5
            if total_display_sensors > display_limit:
                remaining = total_display_sensors - display_limit
                sensors_html += f'''
                        <div class="sensor-more-indicator" data-product-id="{product_id}" data-sensor-type="control">
                            +{remaining}
                        </div>'''
        else:
            sensors_html += '<span class="no-sensors-msg">None</span>'

        sensors_html += '</div></div>'

        # --- Predefined Sensors Section ---
        predefined_html = '<div class="sensors-section">'
        predefined_html += f'<div class="sensors-label">Predefined Sensors ({total_predefined}):</div>'
        predefined_html += '<div class="sensor-icons">'

        if sorted_predefined_ids:
            # Show first 5 predefined sensors (sorted by config order)
            for idx, sid in enumerate(sorted_predefined_ids[:display_limit]):
                if sid in sensor_data:
                    sensor = sensor_data[sid]
                    sensor_name = sensor.get('name', f'Sensor {sid}')
                    sensor_icon_url = sensor.get('iconUrl', '')
                    if sensor_icon_url and sensor_icon_url != "string":
                        icon_url = sensor_icon_url
                    else:
                        icon_url = "products/placeholder.svg"
                else:
                    sensor_name = f'Sensor {sid}'
                    icon_url = "products/placeholder.svg"

                predefined_html += f'''
                        <div class="sensor-icon-wrapper">
                            <img src="{icon_url}" alt="{sensor_name}" class="sensor-icon-img" onerror="this.src='products/placeholder.svg'">
                            <div class="sensor-tooltip">
                                <div>{sensor_name}</div>
                                <div class="sensor-tooltip-id">ID: {sid}</div>
                            </div>
                        </div>'''

            # Add "+N more" indicator if there are more than 5
            if total_predefined > display_limit:
                remaining = total_predefined - display_limit
                predefined_html += f'''
                        <div class="sensor-more-indicator" data-product-id="{product_id}" data-sensor-type="predefined">
                            +{remaining}
                        </div>'''
        else:
            predefined_html += '<span class="no-sensors-msg">None</span>'

        predefined_html += '</div></div>'

        # Build sensor data for popup (control sensors excluding predefined, sorted by config order)
        # Include visible attribute from config
        all_sensors_json = []
        for sid in display_sensor_ids:
            # Get visibility from config (default to True if not in config)
            visible = config_map.get(sid, {}).get('visible', True)
            if sid in sensor_data:
                sensor = sensor_data[sid]
                all_sensors_json.append({
                    'id': sid,
                    'visible': visible,
                    'name': sensor.get('name', f'Sensor {sid}'),
                    'iconUrl': sensor.get('iconUrl', '')
                })
            else:
                all_sensors_json.append({
                    'id': sid,
                    'visible': visible,
                    'name': f'Sensor {sid}',
                    'iconUrl': ''
                })

        # Build predefined sensor data for popup (sorted by config order)
        # Include visible attribute from config
        all_predefined_json = []
        for sid in sorted_predefined_ids:
            # Get visibility from config (default to True if not in config)
            visible = config_map.get(sid, {}).get('visible', True)
            if sid in sensor_data:
                sensor = sensor_data[sid]
                all_predefined_json.append({
                    'id': sid,
                    'visible': visible,
                    'name': sensor.get('name', f'Sensor {sid}'),
                    'iconUrl': sensor.get('iconUrl', '')
                })
            else:
                all_predefined_json.append({
                    'id': sid,
                    'visible': visible,
                    'name': f'Sensor {sid}',
                    'iconUrl': ''
                })

        html_content += f'''
            <div class="product-card" data-product-id="{product_id}" onmouseenter="startHoverTimer(this, {product_id})" onmouseleave="cancelHoverTimer()">
                <button class="favorite-btn" data-product-id="{product_id}" onclick="toggleFavorite(event, {product_id})" title="Add to favorites">&#9734;</button>
                {match_indicator_html}
                <div class="product-header">
                    <img src="{icon_src}" alt="Icon" class="product-icon" onerror="this.src='products/placeholder.svg'">
                    <div class="product-info">
                        <div class="product-name">{name}</div>
                        <div class="product-id">ID: {product_id}</div>
                        <div class="product-short">{short_name}</div>
                    </div>
                </div>
                <div class="images-section">
                    <div class="image-container">
                        <div class="image-label">Icon</div>
                        <img src="{icon_src}" alt="Icon" class="product-image" onerror="this.src='products/placeholder.svg'">
                    </div>
                    <div class="image-container">
                        <div class="image-label">Image</div>
                        <img src="{image_src}" alt="Image" class="product-image" onerror="this.src='products/placeholder.svg'">
                    </div>
                    <div class="image-container">
                        <div class="image-label">Default</div>
                        <img src="{default_src}" alt="Default" class="product-image" onerror="this.src='products/placeholder.svg'">
                    </div>
                </div>
                <div class="product-details">
                    <div class="detail-item"><span class="detail-label">Sensors:</span> {no_sensors}</div>
                    <div class="detail-item"><span class="detail-label">Controls:</span> {no_controls}</div>
                </div>
                {sensors_html}
                {predefined_html}
                <script>
                    productData[{product_id}] = `{product_json}`;
                    sensorData[{product_id}] = {{
                        control: {json.dumps(all_sensors_json)},
                        predefined: {json.dumps(all_predefined_json)}
                    }};
                </script>
            </div>
'''

    html_content += '''
        </div>
    </div>
    <div class="footer">
        &copy; Sierra Telecom - iMatrix Platform
    </div>

    <div id="popup" class="popup">
        <div class="popup-header">
            <span class="popup-title" id="popup-title">Product Details</span>
            <button class="popup-close" onclick="closePopup()">&times;</button>
        </div>
        <div class="popup-content" id="popup-content"></div>
    </div>

    <div id="sensor-popup" class="sensor-popup">
        <div class="popup-header">
            <span class="popup-title" id="sensor-popup-title">All Sensors</span>
            <button class="popup-close" onclick="closeSensorPopup()">&times;</button>
        </div>
        <div class="sensor-popup-grid" id="sensor-popup-content"></div>
    </div>

    <script>
        let hoverTimer = null;
        let currentPopupId = null;
        let showingFavoritesOnly = false;

        // Favorites functionality
        function getFavorites() {
            const stored = localStorage.getItem('imatrix_product_favorites');
            return stored ? JSON.parse(stored) : [];
        }

        function saveFavorites(favorites) {
            localStorage.setItem('imatrix_product_favorites', JSON.stringify(favorites));
        }

        function toggleFavorite(event, productId) {
            event.stopPropagation();
            const favorites = getFavorites();
            const index = favorites.indexOf(productId);
            const btn = event.currentTarget;

            if (index === -1) {
                favorites.push(productId);
                btn.classList.add('favorited');
                btn.innerHTML = '&#9733;'; // Filled star
                btn.title = 'Remove from favorites';
            } else {
                favorites.splice(index, 1);
                btn.classList.remove('favorited');
                btn.innerHTML = '&#9734;'; // Empty star
                btn.title = 'Add to favorites';
            }

            saveFavorites(favorites);
            updateFavoritesCount();

            // If showing favorites only and we unfavorited, hide the card
            if (showingFavoritesOnly && index !== -1) {
                btn.closest('.product-card').classList.add('hidden');
            }
        }

        function toggleFavoritesFilter() {
            showingFavoritesOnly = !showingFavoritesOnly;
            const toggleBtn = document.getElementById('favorites-toggle');
            const favorites = getFavorites();

            if (showingFavoritesOnly) {
                toggleBtn.classList.add('active');
                toggleBtn.querySelector('.star').innerHTML = '&#9733;';
                toggleBtn.querySelector('span:last-child').textContent = 'Show All';

                // Hide non-favorites
                document.querySelectorAll('.product-card').forEach(card => {
                    const productId = parseInt(card.dataset.productId);
                    if (!favorites.includes(productId)) {
                        card.classList.add('hidden');
                    } else {
                        card.classList.remove('hidden');
                    }
                });
            } else {
                toggleBtn.classList.remove('active');
                toggleBtn.querySelector('.star').innerHTML = '&#9734;';
                toggleBtn.querySelector('span:last-child').textContent = 'Show Favorites';

                // Show all
                document.querySelectorAll('.product-card').forEach(card => {
                    card.classList.remove('hidden');
                });
            }
        }

        function updateFavoritesCount() {
            const favorites = getFavorites();
            document.getElementById('favorites-count').textContent = `Favorites: ${favorites.length}`;
        }

        function initFavorites() {
            const favorites = getFavorites();

            // Mark favorited items
            document.querySelectorAll('.favorite-btn').forEach(btn => {
                const productId = parseInt(btn.dataset.productId);
                if (favorites.includes(productId)) {
                    btn.classList.add('favorited');
                    btn.innerHTML = '&#9733;';
                    btn.title = 'Remove from favorites';
                }
            });

            updateFavoritesCount();
        }

        function startHoverTimer(element, productId) {
            cancelHoverTimer();
            hoverTimer = setTimeout(() => {
                showPopup(element, productId);
            }, 2000);
        }

        function cancelHoverTimer() {
            if (hoverTimer) {
                clearTimeout(hoverTimer);
                hoverTimer = null;
            }
        }

        function showSensorPopup(element, productId, sensorType) {
            const popup = document.getElementById('sensor-popup');
            const content = document.getElementById('sensor-popup-content');
            const title = document.getElementById('sensor-popup-title');

            const productSensors = sensorData[productId] || { control: [], predefined: [] };
            const sensors = sensorType === 'predefined' ? productSensors.predefined : productSensors.control;
            const typeLabel = sensorType === 'predefined' ? 'Predefined Sensors' : 'Sensors';
            title.textContent = `All ${typeLabel} (${sensors.length})`;

            let gridHtml = '';
            for (const sensor of sensors) {
                const iconUrl = sensor.iconUrl && sensor.iconUrl !== 'string' ? sensor.iconUrl : 'products/placeholder.svg';
                const visibleClass = sensor.visible !== false ? 'visible' : 'hidden';
                const visibleText = sensor.visible !== false ? 'Visible' : 'Hidden';
                gridHtml += `
                    <div class="sensor-popup-item">
                        <img src="${iconUrl}" alt="${sensor.name}" class="sensor-popup-icon" onerror="this.src='products/placeholder.svg'">
                        <div class="sensor-popup-name">${sensor.name}</div>
                        <div class="sensor-popup-id">ID: ${sensor.id}</div>
                        <div class="sensor-visible-indicator ${visibleClass}">${visibleText}</div>
                    </div>`;
            }
            content.innerHTML = gridHtml;

            // Position popup near the element
            const rect = element.getBoundingClientRect();
            let left = rect.right + 10;
            let top = rect.top - 50;

            if (left + 600 > window.innerWidth) {
                left = rect.left - 610;
            }
            if (left < 10) {
                left = 10;
            }
            if (top < 10) {
                top = 10;
            }

            popup.style.left = left + 'px';
            popup.style.top = top + 'px';
            popup.style.display = 'block';
        }

        function closeSensorPopup() {
            document.getElementById('sensor-popup').style.display = 'none';
        }

        function showPopup(element, productId) {
            const popup = document.getElementById('popup');
            const content = document.getElementById('popup-content');
            const title = document.getElementById('popup-title');

            try {
                const data = JSON.parse(productData[productId]);
                title.textContent = `Product: ${data.name || 'Unknown'} (ID: ${productId})`;

                let tableHtml = '<table class="popup-table">';
                for (const [key, value] of Object.entries(data)) {
                    if (key.startsWith('local_')) continue;
                    let displayValue = value;
                    if (value === null || value === undefined) {
                        displayValue = '<em style="color: #999;">null</em>';
                    } else if (value === '') {
                        displayValue = '<em style="color: #999;">empty</em>';
                    } else if (typeof value === 'boolean') {
                        displayValue = value ? 'Yes' : 'No';
                    } else if (Array.isArray(value)) {
                        displayValue = value.filter(v => v !== null).join(', ') || '<em style="color: #999;">empty</em>';
                    } else if (typeof value === 'object') {
                        displayValue = '<pre style="margin:0;font-size:10px;">' + JSON.stringify(value, null, 2) + '</pre>';
                    }
                    const label = key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
                    tableHtml += `<tr><td>${label}</td><td>${displayValue}</td></tr>`;
                }
                tableHtml += '</table>';
                content.innerHTML = tableHtml;

                // Position popup
                const rect = element.getBoundingClientRect();
                const popupWidth = 450;
                const popupHeight = 400;

                let left = rect.right + 10;
                let top = rect.top;

                if (left + popupWidth > window.innerWidth) {
                    left = rect.left - popupWidth - 10;
                }
                if (left < 10) {
                    left = 10;
                }
                if (top + popupHeight > window.innerHeight) {
                    top = window.innerHeight - popupHeight - 10;
                }
                if (top < 10) {
                    top = 10;
                }

                popup.style.left = left + 'px';
                popup.style.top = top + 'px';
                popup.style.display = 'block';
                currentPopupId = productId;

            } catch (e) {
                console.error('Error showing popup:', e);
            }
        }

        function closePopup() {
            document.getElementById('popup').style.display = 'none';
            currentPopupId = null;
        }

        // Close popups when clicking outside
        document.addEventListener('click', (e) => {
            const popup = document.getElementById('popup');
            const sensorPopup = document.getElementById('sensor-popup');
            if (!popup.contains(e.target) && !e.target.closest('.product-card')) {
                closePopup();
            }
            if (!sensorPopup.contains(e.target) && !e.target.closest('.sensor-more-indicator') && !e.target.closest('.sensors-section')) {
                closeSensorPopup();
            }
        });

        // Keep popup open when hovering over it
        document.getElementById('popup').addEventListener('mouseenter', cancelHoverTimer);

        // Add event listeners for "+N more" indicators
        document.addEventListener('DOMContentLoaded', () => {
            // Initialize favorites from localStorage
            initFavorites();

            // Handle click on "+N more" indicator for immediate popup
            document.querySelectorAll('.sensor-more-indicator').forEach(indicator => {
                const productId = parseInt(indicator.dataset.productId);
                const sensorType = indicator.dataset.sensorType || 'control';
                indicator.addEventListener('click', (e) => {
                    e.stopPropagation();
                    showSensorPopup(indicator, productId, sensorType);
                });
            });
        });
    </script>
</body>
</html>
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_path


def save_metadata(products: List[dict], output_file: str) -> None:
    """Save combined product metadata to JSON file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_file)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, default=str)

    print(f"Metadata saved to: {output_path}")


def save_product_json(product: dict, output_dir: str) -> None:
    """Save individual product JSON file."""
    product_id = product.get('id', 0)
    filepath = os.path.join(output_dir, f"product_{product_id}.json")

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(product, f, indent=2, default=str)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Download public product data and generate HTML catalog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (development API)
  %(prog)s -u user@example.com

  # Production API
  %(prog)s -u user@example.com -prod

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
                       help='Enable verbose output')

    args = parser.parse_args()

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")

    print("=" * 60)
    print("iMatrix Public Products Downloader")
    print("=" * 60)

    # Setup directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    products_dir = os.path.join(script_dir, "products")
    os.makedirs(products_dir, exist_ok=True)

    # Login
    token = login_to_imatrix(args.username, password, args.production)
    base_url = get_api_base_url(args.production)

    # Get public products
    products = get_public_products(token, base_url)

    if not products:
        print("No public products found. Exiting.")
        sys.exit(0)

    # Create placeholder image
    create_placeholder_svg(products_dir)

    # Save individual JSON files
    print(f"\nSaving product JSON files...")
    for product in products:
        save_product_json(product, products_dir)
    print(f"Saved {len(products)} JSON files to products/")

    # Download all images
    success_count, failure_count, updated_products = download_all_images(
        products, products_dir, args.verbose
    )

    print(f"Downloaded {success_count} images, {failure_count} failed/missing.")

    # Fetch predefined sensors for each product
    predefined_by_product = fetch_predefined_sensors_for_products(products, token, base_url, args.verbose)

    # Fetch default configs for each product (order and visibility)
    configs_by_product = fetch_default_configs_for_products(products, token, base_url, args.verbose)

    # Fetch all sensor data for sensor icons (both control and predefined)
    sensor_data = fetch_all_sensors(products, predefined_by_product, token, base_url, args.verbose)

    # Save combined metadata
    save_metadata(updated_products, "product_metadata.json")

    # Generate HTML page
    print("\nGenerating HTML page...")
    logo_path = "iMatrix_logo.jpg"
    html_path = generate_html(updated_products, sensor_data, predefined_by_product, configs_by_product, logo_path, "imatrix_public_products.html")

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_predefined = sum(len(ids) for ids in predefined_by_product.values())
    configs_with_order = sum(1 for c in configs_by_product.values() if c and c.get('order'))
    print(f"Total products found:    {len(products)}")
    print(f"JSON files saved:        {len(products)} (products/product_<id>.json)")
    print(f"Images downloaded:       {success_count}")
    print(f"Images failed/missing:   {failure_count}")
    print(f"Sensors fetched:         {len(sensor_data)}")
    print(f"Predefined sensors:      {total_predefined} refs across products")
    print(f"Default configs:         {configs_with_order} products with order/visibility")
    print(f"HTML output:             {html_path}")
    print(f"Linux URL:               file://{html_path}")
    # Windows URL conversion
    windows_path = html_path.replace('/home/', 'U://').replace('/', '/')
    print(f"Windows URL:             file:///{windows_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
