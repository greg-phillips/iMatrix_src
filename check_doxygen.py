#!/usr/bin/env python3
"""Check for functions without Doxygen documentation in imx_platform.h"""

import re

def check_doxygen_docs(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Pattern to match function declarations
    func_pattern = re.compile(r'^\s*(imx_result_t|void|int|bool)\s+(imx_\w+)\s*\(')
    typedef_func_pattern = re.compile(r'^\s*typedef\s+.*\(\s*\*\s*(\w+)\s*\)\s*\(')
    
    missing_docs = []
    
    for i, line in enumerate(lines):
        # Check if this line is a function declaration
        func_match = func_pattern.match(line)
        typedef_match = typedef_func_pattern.match(line)
        
        if func_match or typedef_match:
            # Look backwards for a Doxygen comment
            has_doxygen = False
            
            # Check up to 10 lines back for the end of a Doxygen comment
            for j in range(1, min(i + 1, 11)):
                if '*/' in lines[i - j]:
                    # Found end of comment, now check if it's a Doxygen comment
                    # Look further back for the start
                    for k in range(j, min(i + 1, 20)):
                        if '/**' in lines[i - k]:
                            has_doxygen = True
                            break
                    break
            
            if not has_doxygen:
                if func_match:
                    func_name = func_match.group(2)
                else:
                    func_name = typedef_match.group(1)
                missing_docs.append({
                    'line': i + 1,
                    'function': func_name,
                    'declaration': line.strip()
                })
    
    return missing_docs

# Check the file
missing = check_doxygen_docs('/home/greg/iMatrix_src/iMatrix/imx_platform.h')

if missing:
    print(f"Found {len(missing)} functions without proper Doxygen documentation:\n")
    for item in missing:
        print(f"Line {item['line']}: {item['function']}")
        print(f"  Declaration: {item['declaration']}")
        print()
else:
    print("All functions have proper Doxygen documentation!")