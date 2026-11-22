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

void BM_ReadBandwidth4(benchmark::State& state) {
    const auto n_bytes = static_cast<std::size_t>(state.range(0));
    const std::size_t n = n_bytes / sizeof(float);

    std::vector<float> buf(n, 1.0f);

    for (auto _ : state) {
        float s0 = 0.0f, s1 = 0.0f, s2 = 0.0f, s3 = 0.0f;
        for (std::size_t i = 0; i < n; i += 4) {
            s0 += buf[i];
            s1 += buf[i + 1];
            s2 += buf[i + 2];
            s3 += buf[i + 3];
        }
        benchmark::DoNotOptimize(s0 + s1 + s2 + s3);
    }

    state.SetBytesProcessed(state.iterations() * static_cast<std::int64_t>(n_bytes));
}

void BM_ReadBandwidth8(benchmark::State& state) {
    const auto n_bytes = static_cast<std::size_t>(state.range(0));
    const std::size_t n = n_bytes / sizeof(float);

    std::vector<float> buf(n, 1.0f);

    for (auto _ : state) {
        float s0 = 0.0f, s1 = 0.0f, s2 = 0.0f, s3 = 0.0f;
        float s4 = 0.0f, s5 = 0.0f, s6 = 0.0f, s7 = 0.0f;
        for (std::size_t i = 0; i < n; i += 8) {
            s0 += buf[i];
            s1 += buf[i + 1];
            s2 += buf[i + 2];
            s3 += buf[i + 3];
            s4 += buf[i + 4];
            s5 += buf[i + 5];
            s6 += buf[i + 6];
            s7 += buf[i + 7];
        }
        benchmark::DoNotOptimize(s0 + s1 + s2 + s3 + s4 + s5 + s6 + s7);
    }

    state.SetBytesProcessed(state.iterations() * static_cast<std::int64_t>(n_bytes));
}

}  // namespace

BENCHMARK(BM_ReadBandwidth)
    ->Arg(64 << 10)
    ->Arg(std::int64_t{1} << 30)
    ->Unit(benchmark::kMicrosecond);

BENCHMARK(BM_ReadBandwidth4)
    ->Arg(64 << 10)
    ->Arg(std::int64_t{1} << 30)
    ->Unit(benchmark::kMicrosecond);

BENCHMARK(BM_ReadBandwidth8)
    ->Arg(64 << 10)
    ->Arg(std::int64_t{1} << 30)
    ->Unit(benchmark::kMicrosecond);
