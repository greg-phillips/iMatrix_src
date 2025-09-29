# CMake generated Testfile for 
# Source directory: /home/greg/iMatrix/iMatrix_Client/memory_manager_v2
# Build directory: /home/greg/iMatrix/iMatrix_Client/memory_manager_v2
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(basic_operations "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/test_harness" "--suite=basic" "--platform=LINUX")
set_tests_properties(basic_operations PROPERTIES  _BACKTRACE_TRIPLES "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;128;add_test;/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;0;")
add_test(platform_specific "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/test_harness" "--suite=platform" "--platform=LINUX")
set_tests_properties(platform_specific PROPERTIES  _BACKTRACE_TRIPLES "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;133;add_test;/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;0;")
add_test(stress_testing "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/test_harness" "--suite=stress" "--platform=LINUX")
set_tests_properties(stress_testing PROPERTIES  _BACKTRACE_TRIPLES "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;138;add_test;/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;0;")
add_test(corner_cases "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/test_harness" "--suite=corners" "--platform=LINUX")
set_tests_properties(corner_cases PROPERTIES  _BACKTRACE_TRIPLES "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;143;add_test;/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;0;")
add_test(comprehensive "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/test_harness" "--suite=all" "--platform=LINUX" "--verbose")
set_tests_properties(comprehensive PROPERTIES  _BACKTRACE_TRIPLES "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;148;add_test;/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;0;")
add_test(memory_validation "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/test_harness" "--suite=memory" "--platform=LINUX")
set_tests_properties(memory_validation PROPERTIES  _BACKTRACE_TRIPLES "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;153;add_test;/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;0;")
add_test(performance_benchmark "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/test_harness" "--suite=performance" "--platform=LINUX")
set_tests_properties(performance_benchmark PROPERTIES  _BACKTRACE_TRIPLES "/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;158;add_test;/home/greg/iMatrix/iMatrix_Client/memory_manager_v2/CMakeLists.txt;0;")
