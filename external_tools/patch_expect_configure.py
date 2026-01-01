#!/usr/bin/env python3
"""
Patch Expect's configure script for cross-compilation.

This replaces the cross-compilation error blocks with code that assumes
reasonable defaults for a modern Linux ARM target.
"""

import re
import sys

def patch_configure(input_file, output_file):
    with open(input_file, 'r') as f:
        content = f.read()

    # Pattern to match the cross-compile error block
    # The block looks like:
    # if test "$cross_compiling" = yes; then
    #   { { echo "...error: Expect can't be cross compiled" ...
    #      { (exit 1); exit 1; }; }
    #
    # else
    #   <actual test code>
    # fi

    # Replace error blocks with just "no" result (assume modern Linux defaults)
    # For WNOHANG _POSIX_SOURCE check - assume no (WNOHANG is available)
    error_pattern = r'if test "\$cross_compiling" = yes; then\s*\n\s*\{ \{ echo "\$as_me:\$LINENO: error: Expect can\'t be cross compiled"[^\}]+\{ \(exit 1\); exit 1; \}; \}'

    # Simple replacement - change error to assume "no" result
    replacement = '''if test "$cross_compiling" = yes; then
  echo "$as_me:$LINENO: result: no (cross-compile assumed)" >&5
echo "${ECHO_T}no" >&6'''

    # Count and replace all error patterns
    count = len(re.findall(error_pattern, content))
    if count > 0:
        content = re.sub(error_pattern, replacement, content)
        print(f"Replaced {count} error blocks")

    # Also handle warning blocks (lines 14419-14420)
    warning_pattern = r'\{ echo "\$as_me:\$LINENO: WARNING: Expect can\'t be cross compiled"[^\}]+\}'
    warning_replacement = '{ echo "$as_me:$LINENO: NOTE: Cross-compiling with assumed defaults" >&5\necho "$as_me: NOTE: Cross-compiling with assumed defaults" >&2;}'

    warn_count = len(re.findall(warning_pattern, content))
    if warn_count > 0:
        content = re.sub(warning_pattern, warning_replacement, content)
        print(f"Replaced {warn_count} warning blocks")

    with open(output_file, 'w') as f:
        f.write(content)

    print(f"Patched configure written to {output_file}")
    return count + warn_count

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_configure> <output_configure>")
        sys.exit(1)

    changes = patch_configure(sys.argv[1], sys.argv[2])
    if changes == 0:
        print("Warning: No patterns matched!")
        sys.exit(1)
