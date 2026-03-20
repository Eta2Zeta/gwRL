cmake_minimum_required(VERSION 3.20)

project(gw_simplified_china LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(gw_simplified
    src/action_catalog.cpp
    src/action_encoder.cpp
    src/game_state.cpp
    src/main.cpp
    src/snapshot_writer.cpp
    src/simulator.cpp
    src/setup_loader.cpp
    src/simple_json.cpp
    src/state_encoder.cpp
    src/training.cpp
)

target_include_directories(gw_simplified PRIVATE include)
