cmake_minimum_required(VERSION 3.25)
project(bibbity LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
# Apple clang 21 resolves -mcpu=native to apple-m4 on the M5, so name the chip explicitly.
# Override with -DBIBBITY_MCPU=...
set(BIBBITY_MCPU "apple-m5" CACHE STRING "Value passed to -mcpu for optimized builds")
set(BIBBITY_SANITIZE "" CACHE STRING "Sanitizers: '', 'address,undefined', or 'thread'")
option(BIBBITY_VEC_REPORT "Emit loop-vectorizer remarks" OFF)
option(BIBBITY_BUILD_TESTS "Build tests" ON)
option(BIBBITY_BUILD_BENCH "Build benchmarks" ON)

# ---------------------------------------------------------------------------
# Common flags (applied through an interface target, not globally, so that
# FetchContent dependencies are not affected by -Werror etc.)
# ---------------------------------------------------------------------------
add_library(bibbity_flags INTERFACE)
target_compile_options(bibbity_flags INTERFACE
  -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wno-sign-conversion
  $<$<NOT:$<CONFIG:Debug>>:-mcpu=${BIBBITY_MCPU}>
)
if(BIBBITY_VEC_REPORT)
  target_compile_options(bibbity_flags INTERFACE
    -Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize)
endif()

# Sanitizers apply to everything (including gtest) so instrumentation is consistent.
if(BIBBITY_SANITIZE)
  add_compile_options(-fsanitize=${BIBBITY_SANITIZE} -fno-omit-frame-pointer -fno-sanitize-recover=all)
  add_link_options(-fsanitize=${BIBBITY_SANITIZE})
endif()

# ---------------------------------------------------------------------------
# Dependencies (pinned)
# ---------------------------------------------------------------------------
include(FetchContent)
set(FETCHCONTENT_QUIET ON)

if(BIBBITY_BUILD_TESTS)
  FetchContent_Declare(googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz
    URL_HASH SHA256=7b42b4d6ed48810c5362c265a17faebe90dc2373c885e5216439d37927f02926
    DOWNLOAD_EXTRACT_TIMESTAMP ON)
  set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
  set(BUILD_GMOCK OFF CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(googletest)
endif()

if(BIBBITY_BUILD_BENCH)
  FetchContent_Declare(benchmark
    URL https://github.com/google/benchmark/archive/refs/tags/v1.9.1.tar.gz
    URL_HASH SHA256=32131c08ee31eeff2c8968d7e874f3cb648034377dfc32a4c377fa8796d84981
    DOWNLOAD_EXTRACT_TIMESTAMP ON)
  set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
  set(BENCHMARK_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)
  set(BENCHMARK_ENABLE_WERROR OFF CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(benchmark)
endif()

# ---------------------------------------------------------------------------
# Engine: every .cpp under src/ except main.cpp goes into bibbity_core.
# While src/ is empty, bibbity_core is an INTERFACE library.
# ---------------------------------------------------------------------------
file(GLOB_RECURSE BIBBITY_SOURCES CONFIGURE_DEPENDS ${PROJECT_SOURCE_DIR}/src/*.cpp)
list(FILTER BIBBITY_SOURCES EXCLUDE REGEX ".*/src/main\\.cpp$")

if(BIBBITY_SOURCES)
  add_library(bibbity_core STATIC ${BIBBITY_SOURCES})
  target_include_directories(bibbity_core PUBLIC ${PROJECT_SOURCE_DIR}/src)
  target_link_libraries(bibbity_core PUBLIC bibbity_flags "-framework Accelerate")
else()
  add_library(bibbity_core INTERFACE)
  target_include_directories(bibbity_core INTERFACE ${PROJECT_SOURCE_DIR}/src)
  target_link_libraries(bibbity_core INTERFACE bibbity_flags "-framework Accelerate")
endif()

if(EXISTS ${PROJECT_SOURCE_DIR}/src/main.cpp)
  add_executable(bibbity ${PROJECT_SOURCE_DIR}/src/main.cpp)
  target_link_libraries(bibbity PRIVATE bibbity_core)
endif()

# ---------------------------------------------------------------------------
# Tests: every tests/**/*_test.cpp into one gtest binary.
# ---------------------------------------------------------------------------
if(BIBBITY_BUILD_TESTS)
  enable_testing()
  include(GoogleTest)
  file(GLOB_RECURSE BIBBITY_TEST_SOURCES CONFIGURE_DEPENDS ${PROJECT_SOURCE_DIR}/tests/*_test.cpp)
  add_executable(bibbity_tests ${BIBBITY_TEST_SOURCES})
  target_link_libraries(bibbity_tests PRIVATE bibbity_core GTest::gtest_main)
  target_compile_definitions(bibbity_tests PRIVATE
    BIBBITY_SOURCE_DIR="${PROJECT_SOURCE_DIR}")
  gtest_discover_tests(bibbity_tests
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    DISCOVERY_MODE PRE_TEST)
endif()

# ---------------------------------------------------------------------------
# Benchmarks: every bench/**/*_bench.cpp into one Google Benchmark binary.
# ---------------------------------------------------------------------------
if(BIBBITY_BUILD_BENCH)
  file(GLOB_RECURSE BIBBITY_BENCH_SOURCES CONFIGURE_DEPENDS ${PROJECT_SOURCE_DIR}/bench/*_bench.cpp)
  add_executable(bibbity_bench ${BIBBITY_BENCH_SOURCES})
  target_link_libraries(bibbity_bench PRIVATE bibbity_core benchmark::benchmark_main)
  # Apple clang's machine outliner pulls repeated instruction runs out into OUTLINED_FUNCTION_*
  # helpers, even at -O3. Inside a hot loop that adds a call/return per pass (seen in the FMA bench).
  target_compile_options(bibbity_bench PRIVATE $<$<NOT:$<CONFIG:Debug>>:-mno-outline>)
  set_target_properties(bibbity_bench PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bench)
endif()
