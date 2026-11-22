# Setup

## Toolchain

| Tool | Why | Install |
| --- | --- | --- |
| Apple clang (CLT or Xcode) | compiler | `xcode-select --install` |
| Full Xcode | Instruments, `xctrace` (M7 onward) | App Store |
| CMake ≥ 3.25 | build | `brew install cmake` |
| Ninja | generator used by all presets | `brew install ninja` |
| uv | Python tooling env | https://docs.astral.sh/uv/ |

GoogleTest v1.15.2 and Google Benchmark v1.9.1 are fetched and pinned (URL + SHA256) by CMake; nothing is vendored.

## Build, test, bench (ER-1)

```bash
cmake --workflow --preset debug      # -O0 -g, ASan + UBSan; configure + build + test
cmake --workflow --preset release    # -O3 -mcpu=apple-m5; configure + build + test
cmake --workflow --preset tsan       # ThreadSanitizer build + test
cmake --preset profile && cmake --build --preset profile   # release + -g for Instruments
./build/release/bench/bibbity_bench  # all benchmarks (--benchmark_filter=... to narrow)
scripts/leaks.sh                     # tests under `leaks --atExit` (release build)
```

- Tests: any `tests/**/*_test.cpp` is compiled into `bibbity_tests` and discovered by ctest. `BIBBITY_SOURCE_DIR` is defined for locating `golden/` and fixtures.
- Benches: any `bench/**/*_bench.cpp` is compiled into `bibbity_bench`.
- Engine: every `src/**/*.cpp` except `main.cpp` goes into `bibbity_core`; the `bibbity` CLI builds once `src/main.cpp` exists.
- Vectorization remarks: `cmake --preset release -DBIBBITY_VEC_REPORT=ON`.
- Different target CPU: `-DBIBBITY_MCPU=...`.

### Toolchain updates

After the Command Line Tools update, delete `build/` (or configure with `--fresh`). Old build dirs keep the old clang's sanitizer runtime path, and ASan binaries then fail with `Library not loaded: libclang_rt.asan_osx_dynamic.dylib`. (Clang 17 on macOS 27.2 also had ASan hanging and TSan crashing; clang 21 fixed both.)

## Python tooling

```bash
uv sync --project tools
uv run --project tools hf download Qwen/Qwen3.5-0.8B --local-dir models/Qwen3.5-0.8B
uv run --project tools python tools/inspect_weights.py models/Qwen3.5-0.8B --quiet
uv run --project tools python tools/tokenize_prompt.py models/Qwen3.5-0.8B tools/prompts/short_chat.txt --show
uv run --project tools python tools/golden_dump.py models/Qwen3.5-0.8B           # writes golden/
uv run --project tools python tools/golden_dump.py models/Qwen3.5-0.8B --verify  # byte-identical check
```

- The reference always runs on CPU in fp32 (never MPS), single-threaded, eager attention, so dumps are reproducible.
- Golden prompts live in `tools/prompts/*.txt` (short chat, code, and a ~650-token long prompt). Chat template with `enable_thinking=False` (CR-5).
- Note: for multi-token inputs HF runs DeltaNet in its *chunked* form; the engine's M4 version is recurrent. Expect fp32-level differences, not bitwise equality.
- Logits are saved for the last position only by default; `--all-logits` saves every position (~1 MB per token, so ~630 MB for the long prompt).
- Current dumps: `golden/{short_chat,code,long_context}` = 24 / 36 / 634 tokens, 335 MB total, about 25 s to generate.
- `models/` and `golden/` are gitignored.

## Measuring

- Plugged in, Low Power Mode off, under `caffeinate -i`. Label results burst or sustained.
- `sudo powermetrics --samplers cpu_power,thermal` on long runs; `sudo purge` for cold-start numbers.
- Record every result in the results table (ER-4, ER-5).
