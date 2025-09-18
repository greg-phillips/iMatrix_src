#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
link_sensor.py
Links a product to a predefined sensor in the iMatrix API.

This script authenticates with the iMatrix API and creates a link between
a product ID and a predefined sensor ID.

Usage:
    python3 link_sensor.py -u <username> -pid <product_id> -sid <sensor_id> [-p <password>]

Example:
    python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 2

Dependencies:
    python3 -m pip install requests urllib3
"""
import argparse
import requests
import sys
import json
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


def link_sensor_to_product(product_id, sensor_id, token, use_development=False):
    """
    Link a predefined sensor to a product using the iMatrix API.

    Args:
        product_id (str): The product ID to link
        sensor_id (int): The sensor ID to link
        token (str): Authentication token from login
        use_development (bool): Use development API instead of production

    Returns:
        bool: True if linking was successful or already linked, False otherwise
    """
    base_url = get_api_base_url(use_development)
    url = f"{base_url}/sensors/predefined/link"
    headers = {
        'accept': 'application/json',
        'x-auth-token': token,
        'Content-Type': 'application/json'
    }
    payload = {
        'id': sensor_id,
        'productId': int(product_id)
    }
    
    print(f"Linking sensor {sensor_id} to product {product_id}...")
    try:
        response = requests.put(url, headers=headers, data=json.dumps(payload), verify=False)
        
        if response.status_code == 200:
            print(f"✅ Successfully linked sensor {sensor_id} to product {product_id}")
            return True
        elif response.status_code == 201:
            print(f"✅ Successfully created link between sensor {sensor_id} and product {product_id}")
            return True
        elif response.status_code == 409:
            # Conflict - sensor already linked
            try:
                error_data = response.json()
                message = error_data.get('message', 'Sensor already linked')
                print(f"ℹ️  {message}")
            except:
                print(f"ℹ️  Sensor {sensor_id} already linked to product {product_id}")
            return True  # Consider this a success since the link exists
        else:
            print(f"❌ Failed to link sensor: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception during sensor linking: {e}")
        return False


def main():
    """
    Main function to handle command line arguments and orchestrate the sensor linking process.
    """
    parser = argparse.ArgumentParser(
        description="Link a product to a predefined sensor in the iMatrix API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Link sensor 2 to product 1235419592:
    python3 link_sensor.py -u user@example.com -pid 1235419592 -sid 2
    
  With password on command line (not recommended):
    python3 link_sensor.py -u user@example.com -p mypassword -pid 1235419592 -sid 2
        """
    )
    
    parser.add_argument('-u', '--username', required=True, 
                       help='iMatrix Cloud username (email)')
    parser.add_argument('-p', '--password', 
                       help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-pid', '--product-id', required=True, 
                       help='Product ID to link')
    parser.add_argument('-sid', '--sensor-id', required=True, type=int,
                       help='Sensor ID to link')
    parser.add_argument('-dev', '--dev', action='store_true',
                       help='Use development API endpoint instead of production')

    args = parser.parse_args()
    
    # Get password securely if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")
    
    # Extract arguments
    username = args.username
    product_id = args.product_id
    sensor_id = args.sensor_id

    environment = "development" if args.dev else "production"
    print(f"Starting sensor linking process (using {environment} API)...")
    print(f"Product ID: {product_id}")
    print(f"Sensor ID: {sensor_id}")

    # Authenticate
    token = login_to_imatrix(username, password, args.dev)

    # Link sensor to product
    success = link_sensor_to_product(product_id, sensor_id, token, args.dev)
    
    if success:
        print("✅ Sensor linking completed successfully.")
    else:
        print("❌ Sensor linking failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()