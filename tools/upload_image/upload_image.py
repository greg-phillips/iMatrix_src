#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_image.py
Uploads image files to the iMatrix Cloud storage system.

This script authenticates with the iMatrix API and uploads image files
for use as icons and product displays. It maintains a JSON registry of
all uploaded files with their URLs.

Usage:
    python3 upload_image.py -u <username> -f <image_file> [options]

Example:
    python3 upload_image.py -u user@example.com -f icon.png
    python3 upload_image.py -u user@example.com -f logo.jpg -p mypassword

Dependencies:
    python3 -m pip install requests urllib3
"""
import argparse
import requests
import sys
import json
import urllib3
import getpass
import os
import mimetypes
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

# Image registry file - saved in same directory as this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_FILE = os.path.join(SCRIPT_DIR, "image_uploads.json")

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Supported image types
SUPPORTED_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    '.ico': 'image/x-icon'
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


def validate_file(file_path):
    """
    Validate that the file exists, is readable, and is a supported image type.
    
    Args:
        file_path (str): Path to the file to validate
        
    Returns:
        tuple: (absolute_path, file_size, mime_type)
        
    Raises:
        SystemExit: If file validation fails
    """
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    # Get absolute path
    abs_path = os.path.abspath(file_path)
    
    # Check if it's a file (not directory)
    if not os.path.isfile(abs_path):
        print(f"❌ Path is not a file: {abs_path}")
        sys.exit(1)
    
    # Check file size
    file_size = os.path.getsize(abs_path)
    if file_size == 0:
        print(f"❌ File is empty: {abs_path}")
        sys.exit(1)
    if file_size > MAX_FILE_SIZE:
        print(f"❌ File too large: {file_size} bytes (max: {MAX_FILE_SIZE} bytes)")
        sys.exit(1)
    
    # Check file extension
    _, ext = os.path.splitext(abs_path.lower())
    if ext not in SUPPORTED_TYPES:
        print(f"❌ Unsupported file type: {ext}")
        print(f"   Supported types: {', '.join(SUPPORTED_TYPES.keys())}")
        sys.exit(1)
    
    # Get MIME type
    mime_type = SUPPORTED_TYPES[ext]
    
    print(f"✅ File validated: {os.path.basename(abs_path)} ({file_size} bytes, {mime_type})")
    return abs_path, file_size, mime_type


def upload_image_file(file_path, file_size, mime_type, token, use_development=False):
    """
    Upload an image file to the iMatrix API.

    Args:
        file_path (str): Absolute path to the file
        file_size (int): Size of the file in bytes
        mime_type (str): MIME type of the file
        token (str): Authentication token
        use_development (bool): Use development API instead of production

    Returns:
        str: URL of the uploaded file

    Raises:
        SystemExit: If upload fails
    """
    base_url = get_api_base_url(use_development)
    url = f"{base_url}/files"
    headers = {
        'accept': 'application/json',
        'x-auth-token': token
    }
    
    filename = os.path.basename(file_path)
    
    try:
        print(f"📤 Uploading {filename}...")
        
        # Open file in binary mode
        with open(file_path, 'rb') as f:
            # Prepare multipart form data
            files = {
                'file': (filename, f, mime_type)
            }
            
            # Show progress (simple version)
            start_time = time.time()
            response = requests.post(url, headers=headers, files=files, verify=False)
            elapsed = time.time() - start_time
            
        if response.status_code in [200, 201]:
            # Parse response to get URL
            response_data = response.json()
            
            # The API might return the URL in different formats
            # Try common response patterns
            file_url = None
            
            if isinstance(response_data, dict):
                # Check for common URL field names
                for field in ['url', 'fileUrl', 'file_url', 'location', 'path']:
                    if field in response_data:
                        file_url = response_data[field]
                        break
                
                # Sometimes the URL might be nested
                if not file_url and 'data' in response_data:
                    data = response_data['data']
                    if isinstance(data, dict):
                        for field in ['url', 'fileUrl', 'file_url']:
                            if field in data:
                                file_url = data[field]
                                break
            
            # If we still don't have a URL, try to construct it from the response
            if not file_url and isinstance(response_data, dict):
                # Sometimes APIs return just the filename or ID
                if 'filename' in response_data:
                    file_url = f"https://storage.googleapis.com/imatrix-files/{response_data['filename']}"
                elif 'id' in response_data:
                    file_url = f"https://storage.googleapis.com/imatrix-files/{response_data['id']}"
            
            if file_url:
                print(f"✅ Upload completed in {elapsed:.1f} seconds")
                return file_url
            else:
                print(f"⚠️  Upload succeeded but URL not found in response")
                print(f"Response: {json.dumps(response_data, indent=2)}")
                # Return a placeholder URL if we can't find it
                return f"https://storage.googleapis.com/imatrix-files/{filename}"
                
        else:
            print(f"❌ Upload failed with status {response.status_code}: {response.text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error during file upload: {e}")
        sys.exit(1)


def load_registry():
    """
    Load the existing image registry or create a new one.
    
    Returns:
        dict: Registry data structure
    """
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, 'r') as f:
                data = json.load(f)
                # Ensure the structure is correct
                if not isinstance(data, dict) or 'uploads' not in data:
                    print(f"⚠️  Invalid registry format, creating new registry")
                    return {'uploads': []}
                return data
        except Exception as e:
            print(f"⚠️  Error reading registry file: {e}")
            print("   Creating new registry")
            return {'uploads': []}
    else:
        return {'uploads': []}


def update_image_registry(filename, url, file_size):
    """
    Update the image registry JSON file with the new upload.
    
    Args:
        filename (str): Name of the uploaded file
        url (str): URL of the uploaded file
        file_size (int): Size of the file in bytes
    """
    # Load existing registry
    registry = load_registry()
    
    # Create new entry
    entry = {
        'filename': filename,
        'url': url,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'size': file_size
    }
    
    # Add to registry
    registry['uploads'].append(entry)
    
    # Save registry
    try:
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(registry, f, indent=2)
        print(f"✅ Registry updated: {os.path.basename(REGISTRY_FILE)}")
        print(f"   Location: {REGISTRY_FILE}")
    except Exception as e:
        print(f"❌ Error updating registry: {e}")
        # Don't exit - the upload was successful even if registry update failed


def main():
    """
    Main function to handle command line arguments and orchestrate image upload.
    """
    parser = argparse.ArgumentParser(
        description="Upload image files to the iMatrix Cloud storage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Upload an image:
    python3 upload_image.py -u user@example.com -f icon.png
    
  Upload with password provided:
    python3 upload_image.py -u user@example.com -p mypassword -f logo.jpg
    
Supported image types:
  .jpg, .jpeg, .png, .gif, .svg, .webp, .bmp, .ico
  
The uploaded file URL will be displayed and saved to image_uploads.json
        """
    )
    
    parser.add_argument('-u', '--username', required=True, 
                       help='iMatrix Cloud username (email)')
    parser.add_argument('-p', '--password', 
                       help='iMatrix Cloud password (optional, secure prompt if omitted)')
    parser.add_argument('-f', '--file', required=True,
                       help='Path to image file to upload')
    parser.add_argument('-dev', '--dev', action='store_true',
                       help='Use development API endpoint instead of production')

    args = parser.parse_args()
    
    # Get password securely if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")
    
    environment = "development" if args.dev else "production"
    print(f"\n🖼️  iMatrix Image Upload Tool (using {environment} API)")
    print("=" * 40)

    # Validate file
    file_path, file_size, mime_type = validate_file(args.file)

    # Authenticate
    token = login_to_imatrix(args.username, password, args.dev)

    # Upload file
    file_url = upload_image_file(file_path, file_size, mime_type, token, args.dev)
    
    # Update registry
    update_image_registry(os.path.basename(file_path), file_url, file_size)
    
    # Display results
    print("\n" + "=" * 40)
    print("✅ File uploaded successfully!")
    print(f"📎 Filename: {os.path.basename(file_path)}")
    print(f"🔗 URL: {file_url}")
    print("=" * 40)


if __name__ == "__main__":
    main()