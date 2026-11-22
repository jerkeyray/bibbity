# Machine profile

The ceilings every number in bibbity is judged against (PR-1). Static fields come from `scripts/machine_profile.sh` (generated 2026-11-21); measured fields are filled at M0.

| Field | Command | Value |
| --- | --- | --- |
| Chip | `sysctl -n machdep.cpu.brand_string` | Apple M5 |
| RAM | `sysctl hw.memsize` | 16 GiB |
| P-cores / E-cores | `sysctl hw.perflevel0.physicalcpu hw.perflevel1.physicalcpu` | 4 / 6 |
| Cache line | `sysctl hw.cachelinesize` | 128 bytes |
| P-core L1d / L2 | `sysctl hw.perflevel0.l1dcachesize hw.perflevel0.l2cachesize` | 128 KiB / 16384 KiB |
| E-core L1d / L2 | `sysctl hw.perflevel1.l1dcachesize hw.perflevel1.l2cachesize` | 64 KiB / 6144 KiB |
| Page size | `pagesize` | 16 KiB |
| BF16 | `sysctl hw.optional.arm.FEAT_BF16` | yes |
| Int8 dot product | `sysctl hw.optional.arm.FEAT_DotProd` | yes |
| Int8 matrix multiply | `sysctl hw.optional.arm.FEAT_I8MM` | yes |
| FP16 arithmetic | `sysctl hw.optional.arm.FEAT_FP16` | yes |
| SME / SME2 | `sysctl hw.optional.arm.FEAT_SME hw.optional.arm.FEAT_SME2` | yes / yes |
| OS | `sw_vers` | macOS 27.2.1 (26B131) |
| Compiler | `clang++ --version` | Apple clang version 17.0.0 (clang-1700.6.3.2) |

## Measured (M0)

| Field | Source | Value |
| --- | --- | --- |
| Spec memory bandwidth | Apple | 153 GB/s |
| Measured bandwidth: 1 thread / P-cores / all cores | M0 bandwidth bench |  |
| Measured NEON fp32 peak: 1 P-core / all P-cores | M0 FMA bench |  |
| Ridge point (peak FLOP/s ÷ bandwidth) | computed |  |
| L1 / L2 / SLC cliffs from bandwidth-vs-size | M0 sweep |  |

## Notes

- P-core L2 is 16 MiB shared across the P-cluster; E-core L2 is 6 MiB.
