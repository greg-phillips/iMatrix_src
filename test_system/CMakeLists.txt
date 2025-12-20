##
# @file CMakeLists.txt
# @brief CMake build configuration for CAN test program
#
# This CMakeLists.txt builds the can_test.c standalone program for testing
# CAN bus functionality on the iMX6 embedded target. It links against pre-built
# libraries from the Fleet-Connect-1 build.
#
# @date 2025-12-15
# @author Claude Code
#
# Prerequisites:
#   Fleet-Connect-1 must be built first to generate the required libraries.
#
# Usage:
#   mkdir build && cd build
#   CC=/opt/qconnect_sdk_musl/bin/arm-linux-gcc \
#   CXX=/opt/qconnect_sdk_musl/bin/arm-linux-g++ \
#   cmake -DCMAKE_SYSROOT=/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot ..
#   make
##

cmake_minimum_required(VERSION 3.10.0)

project(CAN_Test)

# Application name
set(APP_NAME can_test)

# Paths to required directories (relative to test_system/)
set(IMATRIX_DIR ../iMatrix)
set(FC1_BUILD_DIR ../Fleet-Connect-1/build)
set(QUAKE_LIBS ../../../qfc/arm_musl/libs)

# Resolve paths
get_filename_component(IMATRIX_DIR_FULL ${IMATRIX_DIR} ABSOLUTE)
get_filename_component(FC1_BUILD_DIR_FULL ${FC1_BUILD_DIR} ABSOLUTE)
get_filename_component(QUAKE_LIBS_FULL_PATH ${QUAKE_LIBS} ABSOLUTE)

# Pre-built library paths
set(IMATRIX_LIB ${FC1_BUILD_DIR_FULL}/CMakeFiles/iMatrix.dir/libimatrix.a)
set(MBEDTLS_LIB ${FC1_BUILD_DIR_FULL}/CMakeFiles/mbedtls.dir/library/libmbedtls.a)
set(MBEDX509_LIB ${FC1_BUILD_DIR_FULL}/CMakeFiles/mbedtls.dir/library/libmbedx509.a)
set(MBEDCRYPTO_LIB ${FC1_BUILD_DIR_FULL}/CMakeFiles/mbedtls.dir/library/libmbedcrypto.a)

# Verify pre-built libraries exist
if(NOT EXISTS ${IMATRIX_LIB})
    message(FATAL_ERROR "Pre-built iMatrix library not found: ${IMATRIX_LIB}\n"
                        "Please build Fleet-Connect-1 first.")
endif()
if(NOT EXISTS ${MBEDTLS_LIB})
    message(FATAL_ERROR "Pre-built mbedtls library not found: ${MBEDTLS_LIB}\n"
                        "Please build Fleet-Connect-1 first.")
endif()

message(STATUS "QUAKE_LIBS resolved to: ${QUAKE_LIBS_FULL_PATH}")
if(EXISTS ${QUAKE_LIBS_FULL_PATH})
    message(STATUS "Directory exists: ${QUAKE_LIBS_FULL_PATH}")
else()
    message(WARNING "Directory does not exist: ${QUAKE_LIBS_FULL_PATH}")
endif()

# Add link directories
link_directories(${QUAKE_LIBS_FULL_PATH})

# Application sources
set(APP_SOURCES
    can_test.c
)

# Add compiler flags for platform compatibility
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DLINUX_PLATFORM")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DCAN_PLATFORM")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DIMX_FLASH=")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DCCMSRAM=")

# Force include stdbool.h for bool/true/false support
# (HostTypes.h expects bool to be defined)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -include stdbool.h")

# Define TRUE/FALSE macros (HostTypes.h has these commented out for C mode)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DTRUE=true -DFALSE=false")

# Warning flags
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-unused-function")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-unused-parameter")

# Debug flags
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -g3")

# Create executable
add_executable(${APP_NAME} ${APP_SOURCES})

# Include directories
# The can_test.c uses:
#   #include "HostTypes.h"           -> found in iMatrix/quake/
#   #include "drivers/CanEvents.h"   -> found in iMatrix/quake/drivers/
target_include_directories(${APP_NAME} PRIVATE
    ${IMATRIX_DIR_FULL}/quake
    ${IMATRIX_DIR_FULL}
    ${CMAKE_SYSROOT}/usr/include
)

# Add linker map for debugging
if(${CMAKE_VERSION} VERSION_GREATER_EQUAL "3.13.0")
    target_link_options(${APP_NAME} PRIVATE -Wl,-Map=${APP_NAME}.map)
endif()

# Link libraries - use pre-built static libraries
# Order matters: imatrix depends on mbedtls, mbedx509, mbedcrypto
target_link_libraries(${APP_NAME} PRIVATE
    ${IMATRIX_LIB}
    ${MBEDTLS_LIB}
    ${MBEDX509_LIB}
    ${MBEDCRYPTO_LIB}
    pthread
    c
    m
    rt
    i2c
    qfc
    nl-3
    nl-route-3
    bluetooth
)

# Print build summary
message(STATUS "========================================")
message(STATUS "CAN Test Build Configuration")
message(STATUS "========================================")
message(STATUS "  Application:     ${APP_NAME}")
message(STATUS "  iMatrix Lib:     ${IMATRIX_LIB}")
message(STATUS "  mbedtls Lib:     ${MBEDTLS_LIB}")
message(STATUS "  QUAKE_LIBS:      ${QUAKE_LIBS_FULL_PATH}")
message(STATUS "========================================")
