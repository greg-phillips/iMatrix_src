#!/usr/bin/env python3
"""
Convert Excel sensor list to C header file with #define statements.

This script reads an Excel file with sensor ID and name columns
and generates a C header file with #define statements using the blank.h template.

Usage: python3 convert_sensor_list.py <input_excel_file>

The output file name is automatically generated based on the input filename.
For example: "Sensor List.xlsx" -> "sensor_list_defines.h"
"""

import pandas as pd
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

def sanitize_name(name):
    """
    Convert sensor name to valid C identifier in ALL UPPERCASE.
    
    Args:
        name (str): Original sensor name from Excel
        
    Returns:
        str: Sanitized C identifier in uppercase
    """
    if not isinstance(name, str):
        return "UNKNOWN_SENSOR"
    
    # Convert to uppercase first
    name = name.upper().strip()
    
    # Replace spaces and special characters with underscores
    # Keep only alphanumeric and underscores
    name = re.sub(r'[^A-Z0-9_]', '_', name)
    
    # Replace multiple consecutive underscores with single underscore
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    # Ensure it doesn't start with a digit
    if name and name[0].isdigit():
        name = 'SENSOR_' + name
    
    # If empty after sanitization, use default
    if not name:
        name = 'UNKNOWN_SENSOR'
    
    return name

def sanitize_filename(filename):
    """
    Convert input filename to valid output filename.
    
    Args:
        filename (str): Original filename without extension
        
    Returns:
        str: Sanitized filename for output header
    """
    # Convert to lowercase
    name = filename.lower().strip()
    
    # Replace spaces and special characters with underscores
    name = re.sub(r'[^a-z0-9_]', '_', name)
    
    # Replace multiple consecutive underscores with single underscore
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    # Add suffix
    return f"{name}_defines.h"

def generate_header_guard(filename):
    """
    Generate header guard macro from filename.
    
    Args:
        filename (str): Header filename
        
    Returns:
        str: Header guard macro in uppercase
    """
    # Remove extension and convert to uppercase
    base = Path(filename).stem.upper()
    
    # Replace special characters with underscores
    guard = re.sub(r'[^A-Z0-9_]', '_', base)
    
    # Replace multiple underscores
    guard = re.sub(r'_+', '_', guard)
    
    return f"{guard}_H_"

def read_sensor_list(file_path):
    """
    Read Excel file and extract sensor data.
    
    Args:
        file_path (Path): Path to the Excel file
        
    Returns:
        list: List of tuples (sensor_id, sanitized_name)
    """
    try:
        # Read Excel file
        df = pd.read_excel(file_path, header=None, names=['sensor_id', 'name'])
        
        # Remove rows with NaN values
        df = df.dropna()
        
        sensor_data = []
        skipped_rows = 0
        
        for index, row in df.iterrows():
            try:
                # Skip header rows or invalid sensor IDs
                sensor_id_raw = row['sensor_id']
                if isinstance(sensor_id_raw, str) and (sensor_id_raw.startswith('#') or 'id' in sensor_id_raw.lower()):
                    skipped_rows += 1
                    continue
                    
                sensor_id = int(sensor_id_raw)
                name = sanitize_name(row['name'])
                sensor_data.append((sensor_id, name))
                
            except (ValueError, TypeError) as e:
                skipped_rows += 1
                continue
        
        if skipped_rows > 0:
            print(f"Info: Skipped {skipped_rows} header/invalid rows")
        
        # Sort by identifier name for alphabetical output
        sensor_data.sort(key=lambda x: x[1])
        
        return sensor_data
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []

def read_template():
    """
    Read the blank.h template file.
    
    Returns:
        str: Template content
    """
    # Template path: /Fleet-Connect-1/tools/ -> /iMatrix/iMatrix_Client/iMatrix/templates/
    # Go up from tools directory to iMatrix_Client, then to iMatrix/templates
    script_dir = Path(__file__).resolve().parent  # /Fleet-Connect-1/tools/
    imatrix_client_dir = script_dir.parent.parent  # /iMatrix/iMatrix_Client/
    template_path = imatrix_client_dir / 'iMatrix' / 'templates' / 'blank.h'
    
    try:
        with open(template_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading template file {template_path}: {e}")
        return ""

def generate_header_file(sensor_data, template_content, output_path, input_filename):
    """
    Generate C header file using template and sensor data.
    
    Args:
        sensor_data (list): List of (sensor_id, name) tuples
        template_content (str): Template file content
        output_path (Path): Output file path
        input_filename (str): Original input filename for documentation
    """
    current_date = datetime.now()
    header_guard = generate_header_guard(output_path.name)
    
    # Replace template placeholders
    content = template_content.replace('{{YEAR}}', '2025')
    content = content.replace('{{DATE_LONG}}', current_date.strftime('%B %d, %Y'))
    content = content.replace('{{CURRENT_DATE}}', current_date.strftime('%Y-%m-%d'))
    
    # Fix header guards properly
    content = content.replace('#ifndef _H', f'#ifndef {header_guard}')
    content = content.replace('#define _H', f'#define {header_guard}')
    content = content.replace('#endif // _H', f'#endif // {header_guard}')
    
    # Replace file name in comment
    content = content.replace('/** @file .h', f'/** @file {output_path.name}')
    
    # Update the brief description
    content = content.replace('Describe the purpose of this file', 
                            f'Sensor ID definitions generated from {input_filename}')
    content = content.replace('A more extensive description that may\ntake multiple lines of text.',
                            f'This file contains sensor ID definitions automatically\ngenerated from the Excel sensor list: {input_filename}')
    
    # Generate #define statements with proper alignment
    if sensor_data:
        max_name_length = max(len(name) for _, name in sensor_data)
        
        defines = []
        defines.append(f'/* Generated sensor definitions from {input_filename} */')
        defines.append(f'/* Generated on: {current_date.strftime("%Y-%m-%d %H:%M:%S")} */')
        defines.append(f'/* Total sensors: {len(sensor_data)} */')
        defines.append('')
        
        for sensor_id, name in sensor_data:
            # Pad name to align sensor IDs
            padded_name = name.ljust(max_name_length)
            defines.append(f'#define {padded_name} {sensor_id}')
        
        defines_content = '\n'.join(defines)
    else:
        defines_content = '/* No sensor data found */'
    
    # Insert defines into the Constants section
    constants_marker = '/******************************************************\n *                  Constants\n ******************************************************/\n'
    
    if constants_marker in content:
        # Insert defines after Constants section
        content = content.replace(constants_marker, constants_marker + '\n' + defines_content + '\n')
    else:
        print("Warning: Constants section not found in template")
    
    # Write output file
    try:
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"Successfully generated: {output_path}")
        print(f"Generated {len(sensor_data)} sensor definitions")
    except Exception as e:
        print(f"Error writing output file: {e}")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Convert Excel sensor list to C header file with #define statements',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ../hm_truck/Sensor\ List.xlsx
  %(prog)s /path/to/Vehicle_Sensors.xlsx
  
Output file will be automatically generated in the same directory as input file.
For example: "Sensor List.xlsx" -> "sensor_list_defines.h"
        """
    )
    
    parser.add_argument('input_file', 
                       help='Path to Excel file containing sensor list')
    
    args = parser.parse_args()
    
    # Set up file paths
    input_path = Path(args.input_file).resolve()
    
    # Validate input file
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1
    
    if not input_path.suffix.lower() in ['.xlsx', '.xls']:
        print(f"Error: Input file must be an Excel file (.xlsx or .xls): {input_path}")
        return 1
    
    # Generate output filename
    output_filename = sanitize_filename(input_path.stem)
    output_path = input_path.parent / output_filename
    
    print(f"Input file: {input_path}")
    print(f"Output file: {output_path}")
    
    # Read sensor data
    print(f"Reading Excel file...")
    sensor_data = read_sensor_list(input_path)
    
    if not sensor_data:
        print("No valid sensor data found in Excel file")
        return 1
    
    print(f"Found {len(sensor_data)} sensors")
    
    # Read template
    template_content = read_template()
    if not template_content:
        print("Failed to read template file")
        return 1
    
    # Generate header file
    generate_header_file(sensor_data, template_content, output_path, input_path.name)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())