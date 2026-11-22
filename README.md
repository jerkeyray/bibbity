# bibbity

A tiny inference engine for [Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B), built by hand in C++ for the CPU of an Apple Silicon Mac. No magic, just matmuls (and a little recurrence).

Build, test, bench and the Python tooling: [docs/setup.md](docs/setup.md).

## Layout

```
src/        engine: runtime, loader, ops, layers, model, state, sample, sched
tests/      *_test.cpp → bibbity_tests (unit, golden, property, allocation)
bench/      *_bench.cpp → bibbity_bench (micro, e2e)
tools/      Python (uv): inspect_weights, tokenize_prompt, golden_dump, prompts/
scripts/    machine_profile.sh, leaks.sh
docs/       setup, machine profile, design/, notes/logs/ (learning log)
models/     downloaded checkpoint (gitignored)
golden/     reference dumps (gitignored)
temp_docs/  private working notes (gitignored)
```
