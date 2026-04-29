cmake_minimum_required(VERSION 3.20)
project(luo_gate VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(luo_gate_core
    src/app.cpp
    src/security.cpp
    src/ui.cpp
)

target_include_directories(luo_gate_core PUBLIC include)

add_executable(luo_gate_app
    src/main.cpp
)

target_link_libraries(luo_gate_app PRIVATE luo_gate_core)

add_executable(luo_gate_tests
    tests/app_tests.cpp
)

target_link_libraries(luo_gate_tests PRIVATE luo_gate_core)

enable_testing()
add_test(NAME luo_gate_tests COMMAND luo_gate_tests)
