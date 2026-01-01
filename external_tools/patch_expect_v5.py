#!/usr/bin/env python3
"""
Patch Expect's configure script for cross-compilation v5.

Properly handles terminal structure checks for Linux ARM (termios=yes).
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

    # Pattern 2: setpgrp check - assume void (System V style)
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

    # Pattern 3: Warning blocks
    pattern3 = (
        r'\{ echo "\$as_me:\$LINENO: WARNING: Expect can\'t be cross compiled" >&5\s*\n'
        r'echo "\$as_me: WARNING: Expect can\'t be cross compiled" >&2;\}'
    )
    replacement3 = (
        '{ echo "$as_me:$LINENO: NOTE: Cross-compiling with defaults" >&5\n'
        'echo "$as_me: NOTE: Cross-compiling with defaults" >&2;}'
    )

    matches3 = len(re.findall(pattern3, content))
    if matches3:
        content = re.sub(pattern3, replacement3, content)
        print(f"Patched {matches3} warning blocks")
        changes += matches3

    # Pattern 4: Fix termios check to return YES and set PTY_TYPE
    # This one needs special handling since we want it to say yes and define things
    pattern4 = (
        r'(# now check for the new style ttys \(not yet posix\)\s*\n'
        r'\s*echo "\$as_me:\$LINENO: checking for struct termios" >&5\s*\n'
        r'echo \$ECHO_N "checking for struct termios\.\.\. \$ECHO_C" >&6\s*\n'
        r'\s*)if test "\$cross_compiling" = yes; then\s*\n'
        r'\s*echo "\$as_me:\$LINENO: result: no" >&5\s*\n'
        r'echo "\$\{ECHO_T\}no \(cross-compile, assumed\)" >&6\s*\n'
        r'\s*\n'
        r'else'
    )

    replacement4 = r'''\1if test "$cross_compiling" = yes; then
  # Cross-compile: assume termios (POSIX) is available on Linux ARM
cat >>confdefs.h <<\_ACEOF
#define HAVE_TERMIOS 1
_ACEOF
  PTY_TYPE=termios
  echo "$as_me:$LINENO: result: yes" >&5
echo "${ECHO_T}yes (cross-compile, assumed termios)" >&6

else'''

    matches4 = len(re.findall(pattern4, content))
    if matches4:
        content = re.sub(pattern4, replacement4, content)
        print(f"Patched {matches4} termios check blocks")
        changes += matches4

    # Pattern 5: Fix TCGETS/TCGETA check to return YES
    pattern5 = (
        r'(echo "\$as_me:\$LINENO: checking if TCGETS or TCGETA in termios\.h" >&5\s*\n'
        r'echo \$ECHO_N "checking if TCGETS or TCGETA in termios\.h\.\.\. \$ECHO_C" >&6\s*\n)'
        r'if test "\$cross_compiling" = yes; then\s*\n'
        r'\s*echo "\$as_me:\$LINENO: result: no" >&5\s*\n'
        r'echo "\$\{ECHO_T\}no \(cross-compile, assumed\)" >&6'
    )

    replacement5 = r'''\1if test "$cross_compiling" = yes; then
  # Cross-compile: TCGETS is available on Linux
cat >>confdefs.h <<\_ACEOF
#define HAVE_TCGETS 1
_ACEOF
  echo "$as_me:$LINENO: result: yes" >&5
echo "${ECHO_T}yes (cross-compile, assumed)"'''

    matches5 = len(re.findall(pattern5, content))
    if matches5:
        content = re.sub(pattern5, replacement5, content)
        print(f"Patched {matches5} TCGETS check blocks")
        changes += matches5

    # Pattern 6: Fix TIOCGWINSZ check to return YES
    pattern6 = (
        r'(echo "\$as_me:\$LINENO: checking if TIOCGWINSZ in termios\.h" >&5\s*\n'
        r'echo \$ECHO_N "checking if TIOCGWINSZ in termios\.h\.\.\. \$ECHO_C" >&6\s*\n)'
        r'if test "\$cross_compiling" = yes; then\s*\n'
        r'\s*echo "\$as_me:\$LINENO: result: no" >&5\s*\n'
        r'echo "\$\{ECHO_T\}no \(cross-compile, assumed\)" >&6'
    )

    replacement6 = r'''\1if test "$cross_compiling" = yes; then
  # Cross-compile: TIOCGWINSZ is in sys/ioctl.h on Linux
  echo "$as_me:$LINENO: result: no (in sys/ioctl.h)" >&5
echo "${ECHO_T}no (cross-compile, in sys/ioctl.h)"'''

    matches6 = len(re.findall(pattern6, content))
    if matches6:
        content = re.sub(pattern6, replacement6, content)
        print(f"Patched {matches6} TIOCGWINSZ check blocks")
        changes += matches6

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
