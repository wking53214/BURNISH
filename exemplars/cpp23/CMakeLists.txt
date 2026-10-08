cmake_minimum_required(VERSION 3.20)
project(defect_ids LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(defect_ids INTERFACE)
target_include_directories(defect_ids INTERFACE include)
target_compile_options(defect_ids INTERFACE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror)

enable_testing()
add_executable(test_defect_ids tests/test_defect_ids.cpp)
target_link_libraries(test_defect_ids PRIVATE defect_ids)
add_test(NAME vectors COMMAND test_defect_ids ${CMAKE_CURRENT_SOURCE_DIR}/../vectors.txt)
