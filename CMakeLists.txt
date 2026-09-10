cmake_minimum_required(VERSION 3.20)

project(gw_simplified_china LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(gw_simplified
    src/action_encoder.cpp
    src/debug_tools.cpp
    src/game_state.cpp
    src/japan_training_env.cpp
    src/main.cpp
    src/snapshot_writer.cpp
    src/simulator.cpp
    src/setup_loader.cpp
    src/simple_json.cpp
    src/state_encoder.cpp
)

target_include_directories(gw_simplified PRIVATE include)

include(CTest)
if(BUILD_TESTING)
    add_executable(combat_regression_tests
        tests/combat_regression_tests.cpp
        src/game_state.cpp
    )
    target_include_directories(combat_regression_tests PRIVATE include)
    add_test(NAME combat_regression COMMAND combat_regression_tests)
    set_tests_properties(combat_regression PROPERTIES TIMEOUT 10)
endif()
