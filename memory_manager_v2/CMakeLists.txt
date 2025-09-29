cmake_minimum_required(VERSION 3.10)
project(MemoryManagerV2)

# Set C standard
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Platform selection (default to LINUX for WSL development)
if(NOT DEFINED TARGET_PLATFORM)
    set(TARGET_PLATFORM "LINUX" CACHE STRING "Target platform: LINUX or WICED")
endif()

# Storage backend selection (default to MOCK for testing)
if(NOT DEFINED STORAGE_BACKEND)
    set(STORAGE_BACKEND "MOCK" CACHE STRING "Storage backend: MOCK or IMATRIX")
endif()

# Platform-specific configuration
if(TARGET_PLATFORM STREQUAL "LINUX")
    message(STATUS "Configuring for LINUX platform")
    add_definitions(-DLINUX_PLATFORM)
    add_definitions(-DTEST_ENVIRONMENT)
    set(PLATFORM_SOURCES src/platform/linux_platform.c)
    set(MEMORY_LIMIT 2048)  # 2KB memory limit to force disk overflow
    set(DISK_SUPPORT ON)
elseif(TARGET_PLATFORM STREQUAL "WICED")
    message(STATUS "Configuring for WICED platform simulation")
    add_definitions(-DWICED_PLATFORM)
    add_definitions(-DTEST_ENVIRONMENT)
    set(PLATFORM_SOURCES src/platform/wiced_platform.c)
    set(MEMORY_LIMIT 12288)  # 12KB memory limit simulation
    set(DISK_SUPPORT OFF)
else()
    message(FATAL_ERROR "Unknown platform: ${TARGET_PLATFORM}. Use LINUX or WICED")
endif()

# Build configuration
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -Werror")
set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -g -O0 -DDEBUG")
set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -O3 -DNDEBUG")

# Add memory sanitizers for development
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fsanitize=address -fstack-protector-all")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fsanitize=address")
endif()

# Include directories
include_directories(include)
include_directories(../iMatrix)  # Access to real iMatrix headers
include_directories(../iMatrix/cs_ctrl)
include_directories(../iMatrix/cli)
include_directories(../iMatrix/time)

# Storage backend configuration
if(STORAGE_BACKEND STREQUAL "IMATRIX")
    message(STATUS "Configuring for iMatrix storage backend")
    add_definitions(-DIMATRIX_STORAGE)
    set(STORAGE_SOURCES src/core/imatrix_storage.c)
else()
    message(STATUS "Configuring for mock storage backend")
    add_definitions(-DMOCK_STORAGE)
    set(STORAGE_SOURCES src/core/mock_sectors.c)
endif()

# Source files
set(CORE_SOURCES
    src/core/unified_state.c
    ${STORAGE_SOURCES}
    src/core/write_operations.c
    src/core/read_operations.c
    src/core/erase_operations.c
    src/core/validation.c
    src/core/initialization.c
    src/core/persistent_state.c
)

# Add disk operations for LINUX platform
if(TARGET_PLATFORM STREQUAL "LINUX")
    list(APPEND CORE_SOURCES src/core/disk_operations.c)
endif()

set(INTERFACE_SOURCES
    src/interfaces/legacy_interface.c
    src/interfaces/statistics_interface.c
)

set(TEST_FRAMEWORK_SOURCES
    test_harness/src/test_framework.c
    test_harness/src/platform_simulation.c
    test_harness/src/mock_functions.c
    test_harness/src/test_runner.c
)

set(TEST_SOURCES
    test_harness/tests/test_basic_operations.c
    test_harness/tests/test_state_management.c
    test_harness/tests/test_platform_specific.c
    test_harness/tests/test_stress_scenarios.c
    test_harness/tests/test_corner_cases.c
)

# Create main library
add_library(memory_manager_v2 STATIC
    ${CORE_SOURCES}
    ${PLATFORM_SOURCES}
    ${INTERFACE_SOURCES}
)

# Create simple test harness for now
add_executable(test_harness
    simple_test.c
)

# Link test harness with main library
target_link_libraries(test_harness memory_manager_v2)

# Add platform-specific libraries
if(TARGET_PLATFORM STREQUAL "LINUX")
    # Linux-specific libraries (threading, file I/O)
    target_link_libraries(test_harness pthread)
endif()

# Test targets
enable_testing()

# Basic functionality tests
add_test(NAME basic_operations
    COMMAND test_harness --suite=basic --platform=${TARGET_PLATFORM}
)

# Platform-specific tests
add_test(NAME platform_specific
    COMMAND test_harness --suite=platform --platform=${TARGET_PLATFORM}
)

# Stress tests
add_test(NAME stress_testing
    COMMAND test_harness --suite=stress --platform=${TARGET_PLATFORM}
)

# Corner case tests
add_test(NAME corner_cases
    COMMAND test_harness --suite=corners --platform=${TARGET_PLATFORM}
)

# Comprehensive test suite
add_test(NAME comprehensive
    COMMAND test_harness --suite=all --platform=${TARGET_PLATFORM} --verbose
)

# Memory validation tests
add_test(NAME memory_validation
    COMMAND test_harness --suite=memory --platform=${TARGET_PLATFORM}
)

# Performance benchmarks
add_test(NAME performance_benchmark
    COMMAND test_harness --suite=performance --platform=${TARGET_PLATFORM}
)

# Custom test targets
add_custom_target(test_verbose
    COMMAND test_harness --suite=all --platform=${TARGET_PLATFORM} --verbose --detailed
    DEPENDS test_harness
)

add_custom_target(test_quick
    COMMAND test_harness --suite=basic --platform=${TARGET_PLATFORM}
    DEPENDS test_harness
)

add_custom_target(test_platform_linux
    COMMAND ${CMAKE_COMMAND} -DTARGET_PLATFORM=LINUX ${CMAKE_SOURCE_DIR} && make && make test
)

add_custom_target(test_platform_wiced
    COMMAND ${CMAKE_COMMAND} -DTARGET_PLATFORM=WICED ${CMAKE_SOURCE_DIR} && make && make test
)

# Documentation generation
find_program(DOXYGEN_EXECUTABLE doxygen)
if(DOXYGEN_EXECUTABLE)
    add_custom_target(docs
        COMMAND doxygen docs/Doxyfile
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Generating documentation with Doxygen"
    )
endif()

# Installation (for integration with main iMatrix system)
install(TARGETS memory_manager_v2
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(DIRECTORY include/
    DESTINATION include/memory_manager_v2
    FILES_MATCHING PATTERN "*.h"
)

# Print configuration summary
message(STATUS "=== Memory Manager v2 Configuration ===")
message(STATUS "Platform: ${TARGET_PLATFORM}")
message(STATUS "Storage Backend: ${STORAGE_BACKEND}")
message(STATUS "Memory Limit: ${MEMORY_LIMIT} bytes")
message(STATUS "Disk Support: ${DISK_SUPPORT}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C Flags: ${CMAKE_C_FLAGS}")
message(STATUS "=======================================")