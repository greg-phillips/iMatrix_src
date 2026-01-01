#!/usr/bin/env python3
"""
Patch Expect's configure script for cross-compilation v3.

Replaces cross_compiling=yes error blocks with code that assumes 'no'.
"""

import re

def patch_configure(input_path, output_path):
    with open(input_path, 'r') as f:
        content = f.read()

    # Pattern: Complete error block for cross-compilation
    # if test "$cross_compiling" = yes; then
    #   { { echo "$as_me:$LINENO: error: Expect can't be cross compiled" >&5
    # echo "$as_me: error: Expect can't be cross compiled" >&2;}
    #    { (exit 1); exit 1; }; }
    #
    # else

    pattern = (
        r'if test "\$cross_compiling" = yes; then\s*\n'
        r'\s*\{ \{ echo "\$as_me:\$LINENO: error: Expect can\'t be cross compiled" >&5\s*\n'
        r'echo "\$as_me: error: Expect can\'t be cross compiled" >&2;\}\s*\n'
        r'\s*\{ \(exit 1\); exit 1; \}; \}\s*\n'
        r'\s*\n'
        r'else'
    )

    replacement = '''if test "$cross_compiling" = yes; then
  echo "$as_me:$LINENO: result: no" >&5
echo "${ECHO_T}no (cross-compile, assumed)" >&6

else'''

    # Count matches
    matches = re.findall(pattern, content)
    print(f"Found {len(matches)} cross-compile error blocks")

    # Replace all occurrences
    patched = re.sub(pattern, replacement, content)

    # Also handle the warning blocks (these just print warnings, don't exit)
    warning_pattern = (
        r'\{ echo "\$as_me:\$LINENO: WARNING: Expect can\'t be cross compiled" >&5\s*\n'
        r'echo "\$as_me: WARNING: Expect can\'t be cross compiled" >&2;\}'
    )
    warning_replacement = (
        '{ echo "$as_me:$LINENO: NOTE: Cross-compiling with defaults" >&5\n'
        'echo "$as_me: NOTE: Cross-compiling with defaults" >&2;}'
    )

    warnings = re.findall(warning_pattern, patched)
    print(f"Found {len(warnings)} warning blocks")
    patched = re.sub(warning_pattern, warning_replacement, patched)

    with open(output_path, 'w') as f:
        f.write(patched)

    print(f"Written patched configure to {output_path}")
    return len(matches) + len(warnings)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input> <output>")
        sys.exit(1)

    changes = patch_configure(sys.argv[1], sys.argv[2])
    if changes == 0:
        print("ERROR: No patterns matched!")
        sys.exit(1)
    print(f"Total changes: {changes}")
