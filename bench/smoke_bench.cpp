// Wiring check only: proves Google Benchmark is linked. Delete once real benches exist.
#include <benchmark/benchmark.h>

static void BM_Smoke(benchmark::State& state) {
    for (auto _ : state) {
        int x = 0;
        benchmark::DoNotOptimize(x);
    }
}
BENCHMARK(BM_Smoke);
