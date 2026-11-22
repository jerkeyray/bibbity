#!/usr/bin/env bash
# Runs the test suite under macOS `leaks` (ER-2). Uses the release build: leaks
# does not work on ASan-instrumented binaries.
set -euo pipefail
cd "$(dirname "$0")/.."
cmake --preset release >/dev/null
cmake --build --preset release --target bibbity_tests
MallocStackLogging=1 leaks --atExit -- ./build/release/bibbity_tests "$@"
