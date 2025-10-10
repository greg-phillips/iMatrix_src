# Memory Manager v2 - Sensor Storage System
# CMake build configuration for embedded IoT sensor data storage

cmake_minimum_required(VERSION 3.10)
project(SensorStorage VERSION 2.0.0 LANGUAGES C)

# Build configuration
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Build options
option(SS_ENABLE_TIMING_DEBUG "Enable timing debug features" OFF)
option(SS_ENABLE_TESTS "Build unit tests" ON)
option(SS_PLATFORM_STM32 "Build for STM32 platform" OFF)
option(SS_PLATFORM_LINUX "Build for Linux platform" ON)

# Compiler flags
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -Werror")
set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -g -O0 -DDEBUG")
set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -O2 -DNDEBUG")

# Platform-specific settings
if(SS_PLATFORM_STM32)
    add_definitions(-DSS_PLATFORM_STM32=1)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -mcpu=cortex-m4 -mthumb")
elseif(SS_PLATFORM_LINUX)
    add_definitions(-DSS_PLATFORM_LINUX=1)
    find_package(Threads REQUIRED)
endif()

# Debug timing features
if(SS_ENABLE_TIMING_DEBUG)
    add_definitions(-DSS_DEBUG_TIMING=1)
endif()

# Include directories
include_directories(
    src/sensor_storage/api
    src/sensor_storage/core
    src/sensor_storage/utils
    src/sensor_storage/platform
)

# Core library sources
set(SENSOR_STORAGE_CORE_SOURCES
    src/sensor_storage/core/ss_sector.c
    src/sensor_storage/utils/ss_crc.c
    src/sensor_storage/utils/ss_mutex.c
)

# Platform-specific sources
if(SS_PLATFORM_LINUX)
    list(APPEND SENSOR_STORAGE_CORE_SOURCES
        src/sensor_storage/platform/ss_linux.c
    )
endif()

if(SS_PLATFORM_STM32)
    list(APPEND SENSOR_STORAGE_CORE_SOURCES
        src/sensor_storage/platform/ss_stm32.c
    )
endif()

# Main library
add_library(sensor_storage STATIC ${SENSOR_STORAGE_CORE_SOURCES})

# Platform-specific linking
if(SS_PLATFORM_LINUX)
    target_link_libraries(sensor_storage Threads::Threads)
endif()

# API implementation (when complete)
# add_library(sensor_storage_api STATIC
#     src/sensor_storage/api/sensor_storage.c
# )
# target_link_libraries(sensor_storage_api sensor_storage)

# Unit tests
if(SS_ENABLE_TESTS)
    enable_testing()

    # Test framework (simple built-in for now)
    add_library(test_framework STATIC
        tests/framework/simple_test.c
    )

    # Individual test programs
    set(TEST_PROGRAMS
        test_crc
        test_mutex
        test_sector
        test_pool
    )

    foreach(test_name ${TEST_PROGRAMS})
        add_executable(${test_name} tests/unit/${test_name}.c)
        target_link_libraries(${test_name} sensor_storage test_framework)
        add_test(NAME ${test_name} COMMAND ${test_name})
    endforeach()
endif()

# Installation
install(TARGETS sensor_storage
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(FILES src/sensor_storage/api/sensor_storage.h
    DESTINATION include
)

# Documentation target
find_program(DOXYGEN_EXECUTABLE doxygen)
if(DOXYGEN_EXECUTABLE)
    add_custom_target(docs
        COMMAND ${DOXYGEN_EXECUTABLE} Doxyfile
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Generating API documentation with Doxygen"
    )
endif()

# Summary
message(STATUS "Sensor Storage System Configuration:")
message(STATUS "  Version: ${PROJECT_VERSION}")
message(STATUS "  Platform STM32: ${SS_PLATFORM_STM32}")
message(STATUS "  Platform Linux: ${SS_PLATFORM_LINUX}")
message(STATUS "  Timing Debug: ${SS_ENABLE_TIMING_DEBUG}")
message(STATUS "  Build Tests: ${SS_ENABLE_TESTS}")
message(STATUS "  Build Type: ${CMAKE_BUILD_TYPE}")