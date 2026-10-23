cmake_minimum_required(VERSION 3.20)

project(gw_simplified_china LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(gw_engine STATIC
    src/action_encoder.cpp
    src/campaign_runtime.cpp
    src/campaign_benchmarks.cpp
    src/campaign_audit.cpp
    src/campaign_env.cpp
    src/campaign_objective.cpp
    src/campaign_setup.cpp
    src/campaign_state.cpp
    src/catalog.cpp
    src/movement.cpp
    src/economy.cpp
    src/economy_lendlease.cpp
    src/land_combat.cpp
    src/air.cpp
    src/naval.cpp
    src/naval_movement.cpp
    src/naval_combat.cpp
    src/naval_operations.cpp
    src/politics.cpp
    src/politics_influence.cpp
    src/politics_warlords.cpp
    src/debug_tools.cpp
    src/game_state.cpp
    src/japan_training_env.cpp
    src/snapshot_writer.cpp
    src/simulator.cpp
    src/setup_loader.cpp
    src/simple_json.cpp
    src/state_encoder.cpp
)

target_include_directories(gw_engine PUBLIC include)
target_compile_definitions(gw_engine PRIVATE GWRL_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")

add_executable(gw_simplified src/main.cpp)
target_link_libraries(gw_simplified PRIVATE gw_engine)

add_executable(campaign_benchmark tools/campaign_benchmark.cpp)
target_link_libraries(campaign_benchmark PRIVATE gw_engine)
target_compile_definitions(campaign_benchmark PRIVATE GWRL_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")

add_executable(campaign_trace tools/campaign_trace.cpp)
target_link_libraries(campaign_trace PRIVATE gw_engine)
target_compile_definitions(campaign_trace PRIVATE GWRL_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")

include(CTest)
if(BUILD_TESTING)
    add_executable(combat_regression_tests
        tests/combat_regression_tests.cpp
    )
    target_link_libraries(combat_regression_tests PRIVATE gw_engine)
    add_test(NAME combat_regression COMMAND combat_regression_tests)
    set_tests_properties(combat_regression PROPERTIES TIMEOUT 10)
    foreach(test_name campaign_state campaign_runtime campaign_setup campaign_env campaign_reward campaign_integration catalog politics politics_influence politics_warlords movement economy land_combat land_truce air air_logistics air_integration air_mission naval_movement naval_combat naval_operations json_integrity prototype_boundary)
        add_executable(${test_name}_tests tests/${test_name}_tests.cpp)
        target_link_libraries(${test_name}_tests PRIVATE gw_engine)
        target_compile_definitions(${test_name}_tests PRIVATE GWRL_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
        add_test(NAME ${test_name} COMMAND ${test_name}_tests)
        set_tests_properties(${test_name} PROPERTIES TIMEOUT 30)
    endforeach()
endif()
