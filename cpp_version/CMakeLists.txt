cmake_minimum_required(VERSION 3.10)
project(UltimateDoomCPP)

set(CMAKE_CXX_STANDARD 17)

# Procura pela Raylib (Precisa estar instalada ou no PATH)
find_package(raylib REQUIRED)

add_executable(UltimateDoomCPP main.cpp)

target_link_libraries(UltimateDoomCPP raylib)
