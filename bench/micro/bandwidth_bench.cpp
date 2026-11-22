#include <arm_neon.h>
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

// 16 sums as 4 explicit NEON registers (4 floats each): 4 independent fadd.4s chains.
// Written with intrinsics because the compiler won't reliably vectorize a float[16]
// accumulator array: it kept 16 scalar sums instead and ran at the 8-sum speed.
void BM_ReadBandwidth16(benchmark::State& state) {
    const auto n_bytes = static_cast<std::size_t>(state.range(0));
    const std::size_t n = n_bytes / sizeof(float);

    std::vector<float> buf(n, 1.0f);
    const float* p = buf.data();

    for (auto _ : state) {
        float32x4_t a0 = vdupq_n_f32(0.0f);
        float32x4_t a1 = vdupq_n_f32(0.0f);
        float32x4_t a2 = vdupq_n_f32(0.0f);
        float32x4_t a3 = vdupq_n_f32(0.0f);
        for (std::size_t i = 0; i < n; i += 16) {
            a0 = vaddq_f32(a0, vld1q_f32(p + i));
            a1 = vaddq_f32(a1, vld1q_f32(p + i + 4));
            a2 = vaddq_f32(a2, vld1q_f32(p + i + 8));
            a3 = vaddq_f32(a3, vld1q_f32(p + i + 12));
        }
        const float32x4_t total = vaddq_f32(vaddq_f32(a0, a1), vaddq_f32(a2, a3));
        benchmark::DoNotOptimize(vaddvq_f32(total));
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

BENCHMARK(BM_ReadBandwidth16)
    ->Arg(64 << 10)
    ->Arg(std::int64_t{1} << 30)
    ->Unit(benchmark::kMicrosecond);
