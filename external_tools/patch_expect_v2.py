#!/usr/bin/env python3
"""
Patch Expect's configure script for cross-compilation v2.

Replaces the error blocks with code that assumes no (default) for each test.
"""

import sys

def patch_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    patched_lines = []
    i = 0
    changes = 0

    while i < len(lines):
        line = lines[i]

        # Check for error block start
        if "error: Expect can't be cross compiled" in line:
            # Find the { (exit 1); exit 1; }; } line and replace the block
            # Go back to find the if test "$cross_compiling" line
            # and replace through the exit 1 line

            # Remove the previous line (echo $as_me: error: ...) if we added it
            if patched_lines and "error: Expect can't be cross compiled" in patched_lines[-1]:
                patched_lines.pop()

            # Also remove the { { echo ... line before that
            if patched_lines and '{ { echo "$as_me:$LINENO: error' in patched_lines[-1]:
                patched_lines.pop()

            # Add a comment and skip the error echo line
            patched_lines.append('  # Cross-compile: assuming no (patched)\n')
            patched_lines.append('  echo "$as_me:$LINENO: result: no (cross-compile assumed)" >&5\n')
            patched_lines.append('  echo "${ECHO_T}no" >&6\n')

            # Skip this line
            i += 1

            # Look for and skip the exit 1 line
            while i < len(lines) and '{ (exit 1); exit 1; };' not in lines[i]:
                i += 1
            if i < len(lines):
                i += 1  # Skip the exit line

            # Skip empty line after
            if i < len(lines) and lines[i].strip() == '':
                i += 1

            # Skip the "else" line since we're now assuming the cross-compile path works
            if i < len(lines) and lines[i].strip() == 'else':
                # We need to skip the else block content and jump to the end of the if
                i += 1
                # Skip until we find the matching fi or the result handling
                depth = 0
                while i < len(lines):
                    if 'cat >conftest' in lines[i]:
                        # Skip the test code block
                        while i < len(lines) and 'fi' not in lines[i]:
                            i += 1
                        break
                    i += 1

            changes += 1
        else:
            patched_lines.append(line)
            i += 1

    with open(filepath, 'w') as f:
        f.writelines(patched_lines)

    return changes

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <configure_file>")
        sys.exit(1)

    changes = patch_file(sys.argv[1])
    print(f"Made {changes} patches")
