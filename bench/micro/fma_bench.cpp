#include <arm_neon.h>
#include <benchmark/benchmark.h>
#include <pthread/qos.h>

#include <cstdint>

namespace {

// Inner repeats per benchmark iteration, so the benchmark loop's own overhead is negligible.
constexpr int kRepeat = 1024;

// One vfmaq_f32 = 4 lanes x (multiply + add) = 8 flops.
constexpr std::int64_t kFlopsPerFma = 8;

// Peak FMA throughput: C independent chains of acc = acc + b * c, all in registers.
// No memory loads. C is a template parameter because register count is fixed at compile time.
// Speed rises with C until there are enough chains to cover FMA latency x FMA units, then flattens.
template <int C>
void BM_Fma(benchmark::State& state) {
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);

    float32x4_t acc[C];
    for (int i = 0; i < C; ++i) {
        acc[i] = vdupq_n_f32(static_cast<float>(i));
    }

    // a + 1.0 * 1e-6 grows slowly and never overflows. DoNotOptimize hides the values,
    // so the compiler can't fold the chain into a precomputed result.
    float32x4_t b = vdupq_n_f32(1.0f);
    float32x4_t c = vdupq_n_f32(1e-6f);
    benchmark::DoNotOptimize(b);
    benchmark::DoNotOptimize(c);

    for (auto _ : state) {
        for (int k = 0; k < kRepeat; ++k) {
            for (int i = 0; i < C; ++i) {
                acc[i] = vfmaq_f32(acc[i], b, c);
            }
        }
    }

    float32x4_t total = acc[0];
    for (int i = 1; i < C; ++i) {
        total = vaddq_f32(total, acc[i]);
    }
    benchmark::DoNotOptimize(vaddvq_f32(total));

    // Google Benchmark (1.9.1) sums every thread's time, so scale by threads() for a machine rate.
    const std::int64_t flops = state.iterations() * kRepeat * C * kFlopsPerFma * state.threads();
    state.counters["FLOPS"] =
        benchmark::Counter(static_cast<double>(flops), benchmark::Counter::kIsRate);
}

}  // namespace

BENCHMARK_TEMPLATE(BM_Fma, 1);
BENCHMARK_TEMPLATE(BM_Fma, 2);
BENCHMARK_TEMPLATE(BM_Fma, 4);
BENCHMARK_TEMPLATE(BM_Fma, 8);
BENCHMARK_TEMPLATE(BM_Fma, 12);
BENCHMARK_TEMPLATE(BM_Fma, 16);
BENCHMARK_TEMPLATE(BM_Fma, 24);
BENCHMARK_TEMPLATE(BM_Fma, 32);

// Thread sweep at 16 chains (the single-core peak). Each thread runs its own chains.
// 4 = the P-cores, 10 = every core.
BENCHMARK_TEMPLATE(BM_Fma, 16)
    ->Name("BM_Fma16_MT")
    ->Threads(1)
    ->Threads(2)
    ->Threads(3)
    ->Threads(4)
    ->Threads(6)
    ->Threads(8)
    ->Threads(10)
    ->UseRealTime();
