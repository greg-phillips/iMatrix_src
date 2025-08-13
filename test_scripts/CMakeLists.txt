cmake_minimum_required(VERSION 3.10.0)

project(iMatrix_Test_Scripts)

# Application name
set(APP_NAME test_scripts)

# Paths to required directories
set(IMATRIX_DIR ../iMatrix)

# Add compiler flags following Fleet-Connect-1 pattern
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DLINUX_PLATFORM")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DIMX_FLASH=")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DCCMSRAM=")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DMEMORY_TEST_BUILD")
# Don't use -fcommon, we need to fix the multiple definitions properly

# Simplified flags without external dependencies
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -g3 -Wall -O2")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-unused-function")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-unused-parameter")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-implicit-function-declaration")

# Set storage path for tests
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DIMATRIX_STORAGE_PATH=\\\"/usr/qk/etc/sv/${APP_NAME}\\\"")

# Core iMatrix source files (minimal set for memory testing)
set(IMATRIX_CORE_SOURCES
    ${IMATRIX_DIR}/storage.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_core.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_tsd_evt.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_external.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_stats.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_tiered.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_disk.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_recovery.c
    ${IMATRIX_DIR}/cs_ctrl/memory_manager_utils.c
    ${IMATRIX_DIR}/IMX_Platform/LINUX_Platform/imx_linux_platform.c
    ${IMATRIX_DIR}/time/ck_time.c
)

# Common source files for all tests
set(COMMON_TEST_SOURCES
    memory_test_init.c
    imatrix_stubs.c
    memory_test_disk_sim.c
    memory_test_csb_csd.c
)

# Use existing stub source file instead of generating it

# Include directories
set(INCLUDE_DIRS
    .
    ${IMATRIX_DIR}
    ${IMATRIX_DIR}/IMX_Platform/LINUX_Platform
    ../mbedtls/include
)

# Create individual test executables
add_executable(simple_memory_test 
    simple_memory_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(tiered_storage_test 
    tiered_storage_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(performance_test 
    performance_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(diagnostic_test 
    diagnostic_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(spillover_test 
    spillover_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(module_link_test 
    module_link_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(minimal_test 
    minimal_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(ultra_minimal_test 
    ultra_minimal_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(size_check_test 
    size_check_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(bare_minimal_test 
    bare_minimal_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(real_world_test 
    real_world_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(test_disk_init 
    test_disk_init.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(test_disk_batching 
    test_disk_batching.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(comprehensive_memory_test 
    comprehensive_memory_test.c 
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

add_executable(test_shutdown 
    test_shutdown.c 
    test_shutdown_helpers.c
    ${IMATRIX_CORE_SOURCES}
    ${COMMON_TEST_SOURCES}
)

# Commented out until these test files are created
# add_executable(bucket_test 
#     bucket_test.c 
#     ${IMATRIX_CORE_SOURCES}
#     ${STUB_SOURCE}
# )
# 
# add_executable(multi_bucket_test 
#     multi_bucket_test.c 
#     ${IMATRIX_CORE_SOURCES}
#     ${STUB_SOURCE}
# )
# 
# add_executable(large_test 
#     large_test.c 
#     ${IMATRIX_CORE_SOURCES}
#     ${STUB_SOURCE}
# )

# Set include directories for all targets
target_include_directories(simple_memory_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(tiered_storage_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(performance_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(diagnostic_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(spillover_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(module_link_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(minimal_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(ultra_minimal_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(size_check_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(bare_minimal_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(real_world_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(test_disk_init PRIVATE ${INCLUDE_DIRS})
target_include_directories(test_disk_batching PRIVATE ${INCLUDE_DIRS})
target_include_directories(comprehensive_memory_test PRIVATE ${INCLUDE_DIRS})
target_include_directories(test_shutdown PRIVATE ${INCLUDE_DIRS})
# target_include_directories(bucket_test PRIVATE ${INCLUDE_DIRS})
# target_include_directories(multi_bucket_test PRIVATE ${INCLUDE_DIRS})
# target_include_directories(large_test PRIVATE ${INCLUDE_DIRS})

# Link libraries (minimal set)
target_link_libraries(simple_memory_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(tiered_storage_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(performance_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(diagnostic_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(spillover_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(module_link_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(minimal_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(ultra_minimal_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(size_check_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(bare_minimal_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(real_world_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(test_disk_init PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(test_disk_batching PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(comprehensive_memory_test PRIVATE
    c
    pthread
    m
    rt
)

target_link_libraries(test_shutdown PRIVATE
    c
    pthread
    m
    rt
)

# Test Verify
add_executable(test_verify
    test_verify.c
    ${MEMORY_SOURCES}
    ${MEMORY_TEST_SOURCES}
)
target_link_libraries(test_verify PRIVATE ${REQUIRED_LIBRARIES})

# target_link_libraries(bucket_test PRIVATE
#     c
#     pthread
#     m
#     rt
# )
# 
# target_link_libraries(multi_bucket_test PRIVATE
#     c
#     pthread
#     m
#     rt
# )
# 
# target_link_libraries(large_test PRIVATE
#     c
#     pthread
#     m
#     rt
# )

# Custom targets for running tests
add_custom_target(run_simple
    COMMAND simple_memory_test
    DEPENDS simple_memory_test
    COMMENT "Running simple test"
)

add_custom_target(run_tiered
    COMMAND tiered_storage_test
    DEPENDS tiered_storage_test
    COMMENT "Running tiered storage test"
)

add_custom_target(run_performance
    COMMAND performance_test
    DEPENDS performance_test
    COMMENT "Running performance test"
)

add_custom_target(run_diagnostic
    COMMAND diagnostic_test
    DEPENDS diagnostic_test
    COMMENT "Running diagnostic tests"
)

add_custom_target(run_spillover
    COMMAND spillover_test
    DEPENDS spillover_test
    COMMENT "Running spillover test"
)

add_custom_target(run_module_link
    COMMAND module_link_test
    DEPENDS module_link_test
    COMMENT "Running module link test"
)

add_custom_target(run_real_world
    COMMAND real_world_test
    DEPENDS real_world_test
    COMMENT "Running real-world usage test"
)

add_custom_target(run_shutdown
    COMMAND test_shutdown
    DEPENDS test_shutdown
    COMMENT "Running shutdown functionality tests"
)

add_custom_target(run_all_tests
    COMMAND simple_memory_test
    COMMAND tiered_storage_test
    COMMAND performance_test
    DEPENDS simple_memory_test tiered_storage_test performance_test
    COMMENT "Running all tests"
)

# Install targets
install(TARGETS simple_memory_test tiered_storage_test performance_test diagnostic_test spillover_test module_link_test real_world_test test_disk_batching comprehensive_memory_test test_shutdown
    RUNTIME DESTINATION bin
    PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE
)