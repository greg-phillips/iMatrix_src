#!/bin/bash
#
# Build Expect for ARM Cross-Compilation
#
# This script cross-compiles Tcl and Expect for the ARM target platform
# used by Fleet-Connect-1 devices.
#
# Author: Claude Code
# Date: 2025-12-31
#
# Usage: ./build_expect.sh
#
# Prerequisites:
#   - ARM toolchain at /opt/qconnect_sdk_musl/
#   - Tcl source in external_tools/tcl8.6.13/
#   - Expect source in external_tools/expect/
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMATRIX_CLIENT_DIR="$(dirname "$SCRIPT_DIR")"
EXTERNAL_TOOLS_DIR="${IMATRIX_CLIENT_DIR}/external_tools"

# Toolchain settings
TOOLCHAIN_DIR="/opt/qconnect_sdk_musl"
CROSS_COMPILE="${TOOLCHAIN_DIR}/bin/arm-linux-"
SYSROOT="${TOOLCHAIN_DIR}/arm-buildroot-linux-musleabihf/sysroot"

# Source directories
TCL_SRC="${EXTERNAL_TOOLS_DIR}/tcl8.6.13"
EXPECT_SRC="${EXTERNAL_TOOLS_DIR}/expect"

# Build directories
BUILD_DIR="${EXTERNAL_TOOLS_DIR}/build"
TCL_BUILD="${BUILD_DIR}/tcl-build"
EXPECT_BUILD="${BUILD_DIR}/expect-build"

# Install prefix (staged install)
INSTALL_PREFIX="${BUILD_DIR}/install"

# Export cross-compile environment
export CC="${CROSS_COMPILE}gcc"
export CXX="${CROSS_COMPILE}g++"
export AR="${CROSS_COMPILE}ar"
export RANLIB="${CROSS_COMPILE}ranlib"
export STRIP="${CROSS_COMPILE}strip"
export LD="${CROSS_COMPILE}ld"

export CFLAGS="--sysroot=${SYSROOT} -O2 -fPIC"
export CPPFLAGS="--sysroot=${SYSROOT}"
export LDFLAGS="--sysroot=${SYSROOT} -Wl,-rpath,/usr/local/lib"

echo "============================================="
echo "Building Expect for ARM"
echo "============================================="
echo ""
echo "Toolchain: ${TOOLCHAIN_DIR}"
echo "CC: ${CC}"
echo "Sysroot: ${SYSROOT}"
echo "Install prefix: ${INSTALL_PREFIX}"
echo ""

# Verify toolchain
if [ ! -x "${CC}" ]; then
    echo "ERROR: Cross compiler not found: ${CC}"
    exit 1
fi

# Create directories
echo "Creating build directories..."
rm -rf "${BUILD_DIR}"
mkdir -p "${TCL_BUILD}" "${EXPECT_BUILD}" "${INSTALL_PREFIX}"

# ============================================
# Build Tcl
# ============================================
echo ""
echo "============================================="
echo "Step 1: Building Tcl 8.6.13"
echo "============================================="

cd "${TCL_BUILD}"

# For cross-compilation, we need to tell Tcl about the build system
# and disable features that require running target binaries
# Configure Tcl for shared library build
# Disable packages that fail with cross-compilation
"${TCL_SRC}/unix/configure" \
    --host=arm-linux \
    --build=x86_64-linux-gnu \
    --prefix="${INSTALL_PREFIX}" \
    --enable-shared \
    --disable-threads \
    ac_cv_func_strtod=yes \
    tcl_cv_strtod_buggy=ok \
    tcl_cv_strtod_unbroken=ok \
    tcl_cv_strstr_unbroken=ok \
    ac_cv_func_memcmp_working=yes \
    2>&1 | tee configure.log

echo "Building Tcl..."
make -j4 2>&1 | tee build.log

echo "Installing Tcl..."
make install 2>&1 | tee install.log

# Verify Tcl was built correctly
if [ ! -f "${INSTALL_PREFIX}/lib/libtcl8.6.so" ] && [ ! -f "${INSTALL_PREFIX}/lib/libtcl8.6.a" ]; then
    echo "ERROR: Tcl library not found after build"
    echo "Checking what was built..."
    ls -la "${INSTALL_PREFIX}/lib/" 2>/dev/null || ls -la "${TCL_BUILD}/"*.so "${TCL_BUILD}/"*.a 2>/dev/null
    exit 1
fi

echo "Tcl build complete!"
if [ -f "${INSTALL_PREFIX}/lib/libtcl8.6.so" ]; then
    file "${INSTALL_PREFIX}/lib/libtcl8.6.so"
else
    file "${INSTALL_PREFIX}/lib/libtcl8.6.a"
fi

# ============================================
# Patch Expect for cross-compilation
# ============================================
echo ""
echo "============================================="
echo "Step 2: Patching Expect for cross-compilation"
echo "============================================="

# Expect's configure script has runtime checks that fail during cross-compilation
# We patch these to assume sensible defaults for Linux ARM (termios, POSIX signals, etc.)
PATCH_SCRIPT="${EXTERNAL_TOOLS_DIR}/patch_expect_v5.py"

if [ ! -f "$PATCH_SCRIPT" ]; then
    echo "ERROR: Patch script not found: $PATCH_SCRIPT"
    exit 1
fi

# Backup and patch the configure script
if [ -f "${EXPECT_SRC}/configure.orig" ]; then
    cp "${EXPECT_SRC}/configure.orig" "${EXPECT_SRC}/configure"
else
    cp "${EXPECT_SRC}/configure" "${EXPECT_SRC}/configure.orig"
fi

python3 "$PATCH_SCRIPT" "${EXPECT_SRC}/configure" "${EXPECT_SRC}/configure.patched"
mv "${EXPECT_SRC}/configure.patched" "${EXPECT_SRC}/configure"
chmod +x "${EXPECT_SRC}/configure"

echo "Expect configure patched for cross-compilation"

# ============================================
# Build Expect
# ============================================
echo ""
echo "============================================="
echo "Step 3: Building Expect"
echo "============================================="

cd "${EXPECT_BUILD}"

# Expect needs to find Tcl
export TCL_LIBRARY="${INSTALL_PREFIX}/lib"

# Configure Expect for shared library build
"${EXPECT_SRC}/configure" \
    --host=arm-linux \
    --build=x86_64-linux-gnu \
    --prefix="${INSTALL_PREFIX}" \
    --with-tcl="${TCL_BUILD}" \
    --with-tclinclude="${TCL_SRC}/generic" \
    --enable-shared \
    2>&1 | tee configure.log

echo "Building Expect..."
make -j4 2>&1 | tee build.log

echo "Installing Expect..."
# Note: Full make install may fail because it tries to run ARM binaries.
# We manually copy the essential files instead.
make SCRIPTS="" install-binaries install-libraries 2>&1 | tee install.log || true

# Manual install if automated install failed
if [ ! -f "${INSTALL_PREFIX}/bin/expect" ]; then
    echo "Automated install incomplete, performing manual install..."
    mkdir -p "${INSTALL_PREFIX}/bin"
    mkdir -p "${INSTALL_PREFIX}/lib/expect5.45.3"
    cp expect "${INSTALL_PREFIX}/bin/"
    cp libexpect5.45.3.so "${INSTALL_PREFIX}/lib/expect5.45.3/"
    cp pkgIndex.tcl "${INSTALL_PREFIX}/lib/expect5.45.3/"
fi

# Verify Expect was built correctly
if [ ! -f "${INSTALL_PREFIX}/bin/expect" ]; then
    echo "ERROR: Expect binary not found after build"
    exit 1
fi

echo "Expect build complete!"
file "${INSTALL_PREFIX}/bin/expect"

# ============================================
# Create deployment package
# ============================================
echo ""
echo "============================================="
echo "Step 4: Creating deployment package"
echo "============================================="

DEPLOY_DIR="${BUILD_DIR}/deploy"
mkdir -p "${DEPLOY_DIR}/bin"
mkdir -p "${DEPLOY_DIR}/lib/tcl8.6"

# Copy binaries
cp "${INSTALL_PREFIX}/bin/expect" "${DEPLOY_DIR}/bin/"
cp "${INSTALL_PREFIX}/bin/tclsh8.6" "${DEPLOY_DIR}/bin/"

# Strip binaries to reduce size
"${STRIP}" "${DEPLOY_DIR}/bin/expect" 2>/dev/null || true
"${STRIP}" "${DEPLOY_DIR}/bin/tclsh8.6" 2>/dev/null || true

# Copy shared libraries (make writable for stripping)
if [ -f "${INSTALL_PREFIX}/lib/libtcl8.6.so" ]; then
    cp "${INSTALL_PREFIX}/lib/libtcl8.6.so" "${DEPLOY_DIR}/lib/"
    chmod +w "${DEPLOY_DIR}/lib/libtcl8.6.so"
    "${STRIP}" "${DEPLOY_DIR}/lib/libtcl8.6.so" 2>/dev/null || true
fi

# Copy expect shared library if it exists
for explib in "${INSTALL_PREFIX}/lib/libexpect"*.so; do
    if [ -f "$explib" ]; then
        cp "$explib" "${DEPLOY_DIR}/lib/"
        "${STRIP}" "${DEPLOY_DIR}/lib/$(basename $explib)" 2>/dev/null || true
    fi
done

# Copy minimal Tcl library files (required for initialization)
cp "${INSTALL_PREFIX}/lib/tcl8.6/init.tcl" "${DEPLOY_DIR}/lib/tcl8.6/"
cp "${INSTALL_PREFIX}/lib/tcl8.6/auto.tcl" "${DEPLOY_DIR}/lib/tcl8.6/"
cp "${INSTALL_PREFIX}/lib/tcl8.6/package.tcl" "${DEPLOY_DIR}/lib/tcl8.6/"
cp "${INSTALL_PREFIX}/lib/tcl8.6/tm.tcl" "${DEPLOY_DIR}/lib/tcl8.6/"
cp "${INSTALL_PREFIX}/lib/tcl8.6/tclIndex" "${DEPLOY_DIR}/lib/tcl8.6/" 2>/dev/null || true

# Copy expect package files if they exist
for expdir in "${INSTALL_PREFIX}/lib/expect"*; do
    if [ -d "$expdir" ]; then
        expbase=$(basename "$expdir")
        mkdir -p "${DEPLOY_DIR}/lib/${expbase}"
        cp -r "$expdir"/* "${DEPLOY_DIR}/lib/${expbase}/" 2>/dev/null || true
    fi
done

# Create wrapper script for expect that sets up paths
cat > "${DEPLOY_DIR}/bin/expect-wrapper" << 'WRAPPER_EOF'
#!/bin/sh
# Expect wrapper script for FC-1
# Sets up library paths for expect to work correctly
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB_DIR="$(dirname "$SCRIPT_DIR")/lib"
export LD_LIBRARY_PATH="${LIB_DIR}:${LIB_DIR}/expect5.45.3:${LD_LIBRARY_PATH}"
export TCL_LIBRARY="${LIB_DIR}/tcl8.6"
exec "${SCRIPT_DIR}/expect" "$@"
WRAPPER_EOF
chmod +x "${DEPLOY_DIR}/bin/expect-wrapper"

# Create tarball for deployment
cd "${BUILD_DIR}"
tar czf expect-arm.tar.gz -C deploy .

echo ""
echo "============================================="
echo "Build Complete!"
echo "============================================="
echo ""
echo "Deployment package: ${BUILD_DIR}/expect-arm.tar.gz"
echo ""
echo "Package contents:"
tar tvf "${BUILD_DIR}/expect-arm.tar.gz"
echo ""
echo "Package size:"
ls -lh "${BUILD_DIR}/expect-arm.tar.gz"
echo ""
echo "To deploy to target:"
echo "  scp ${BUILD_DIR}/expect-arm.tar.gz root@192.168.7.1:/tmp/"
echo "  ssh -p 22222 root@192.168.7.1 'mkdir -p /usr/local && cd /usr/local && tar xzf /tmp/expect-arm.tar.gz'"
echo ""
