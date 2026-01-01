#!/usr/bin/env python3
"""
Patch Expect's configure script for cross-compilation v4.

Handles multiple types of cross-compile error blocks and provides default values.
"""

import re

def patch_configure(input_path, output_path):
    with open(input_path, 'r') as f:
        content = f.read()

    changes = 0

    # Pattern 1: "Expect can't be cross compiled" error blocks
    pattern1 = (
        r'if test "\$cross_compiling" = yes; then\s*\n'
        r'\s*\{ \{ echo "\$as_me:\$LINENO: error: Expect can\'t be cross compiled" >&5\s*\n'
        r'echo "\$as_me: error: Expect can\'t be cross compiled" >&2;\}\s*\n'
        r'\s*\{ \(exit 1\); exit 1; \}; \}\s*\n'
        r'\s*\n'
        r'else'
    )
    replacement1 = '''if test "$cross_compiling" = yes; then
  echo "$as_me:$LINENO: result: no" >&5
echo "${ECHO_T}no (cross-compile, assumed)" >&6

else'''

    matches1 = len(re.findall(pattern1, content))
    if matches1:
        content = re.sub(pattern1, replacement1, content)
        print(f"Patched {matches1} 'Expect can't be cross compiled' blocks")
        changes += matches1

    # Pattern 2: "cannot check setpgrp when cross compiling" - assume void (System V style)
    pattern2 = (
        r'if test "\$cross_compiling" = yes; then\s*\n'
        r'\s*\{ \{ echo "\$as_me:\$LINENO: error: cannot check setpgrp when cross compiling" >&5\s*\n'
        r'echo "\$as_me: error: cannot check setpgrp when cross compiling" >&2;\}\s*\n'
        r'\s*\{ \(exit 1\); exit 1; \}; \}\s*\n'
        r'else'
    )
    replacement2 = '''if test "$cross_compiling" = yes; then
  ac_cv_func_setpgrp_void=yes
else'''

    matches2 = len(re.findall(pattern2, content))
    if matches2:
        content = re.sub(pattern2, replacement2, content)
        print(f"Patched {matches2} 'cannot check setpgrp' blocks")
        changes += matches2

    # Pattern 3: Generic "when cross compiling" errors - comment out and continue
    pattern3 = (
        r'if test "\$cross_compiling" = yes; then\s*\n'
        r'\s*\{ \{ echo "\$as_me:\$LINENO: error: ([^"]+)" >&5\s*\n'
        r'echo "\$as_me: error: \1" >&2;\}\s*\n'
        r'\s*\{ \(exit 1\); exit 1; \}; \}\s*\n'
        r'else'
    )

    def replacement3(m):
        return '''if test "$cross_compiling" = yes; then
  echo "$as_me:$LINENO: result: assuming defaults for: ''' + m.group(1) + '''" >&5
echo "${ECHO_T}assuming defaults" >&6

else'''

    matches3_before = len(re.findall(pattern3, content))
    if matches3_before:
        content = re.sub(pattern3, replacement3, content)
        print(f"Patched {matches3_before} generic cross-compile error blocks")
        changes += matches3_before

    # Pattern 4: Warning blocks (lines with WARNING: Expect can't be cross compiled)
    pattern4 = (
        r'\{ echo "\$as_me:\$LINENO: WARNING: Expect can\'t be cross compiled" >&5\s*\n'
        r'echo "\$as_me: WARNING: Expect can\'t be cross compiled" >&2;\}'
    )
    replacement4 = (
        '{ echo "$as_me:$LINENO: NOTE: Cross-compiling with defaults" >&5\n'
        'echo "$as_me: NOTE: Cross-compiling with defaults" >&2;}'
    )

    matches4 = len(re.findall(pattern4, content))
    if matches4:
        content = re.sub(pattern4, replacement4, content)
        print(f"Patched {matches4} warning blocks")
        changes += matches4

    with open(output_path, 'w') as f:
        f.write(content)

    print(f"Written patched configure to {output_path}")
    return changes

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input> <output>")
        sys.exit(1)

    changes = patch_configure(sys.argv[1], sys.argv[2])
    print(f"Total changes: {changes}")
