#include <benchmark/benchmark.h>

#include <cstddef>
#include <cstdint>
#include <vector>

namespace {

void BM_ReadBandwidth(benchmark::State& state) {
    const auto n_bytes = static_cast<std::size_t>(state.range(0));
    const std::size_t n = n_bytes / sizeof(float);

    std::vector<float> buf(n, 1.0f);

    for (auto _ : state) {
        float sum = 0.0f;
        for (std::size_t i = 0; i < n; ++i) {
            sum += buf[i];
        }
        benchmark::DoNotOptimize(sum);
    }

    state.SetBytesProcessed(state.iterations() * static_cast<std::int64_t>(n_bytes));
}

}  // namespace

BENCHMARK(BM_ReadBandwidth)->Arg(std::int64_t{1} << 30)->Unit(benchmark::kMillisecond);