#!/usr/bin/env bash
# Prints the build guide's machine-profile table (section 3) from sysctl.
# Usage: scripts/machine_profile.sh > /tmp/profile.md   (then paste into docs/machine-profile.md)
set -euo pipefail

s() { sysctl -n "$1" 2>/dev/null || echo "n/a"; }
yn() { case "$(s "$1")" in 1) echo yes ;; 0) echo no ;; *) echo "n/a" ;; esac; }
kib() { local v; v=$(s "$1"); [[ "$v" =~ ^[0-9]+$ ]] && echo "$((v / 1024)) KiB" || echo "$v"; }

mem=$(s hw.memsize)
cat <<TABLE
| Field | Command | Value |
| --- | --- | --- |
| Chip | \`sysctl -n machdep.cpu.brand_string\` | $(s machdep.cpu.brand_string) |
| RAM | \`sysctl hw.memsize\` | $((mem / 1024 / 1024 / 1024)) GiB |
| P-cores / E-cores | \`sysctl hw.perflevel0.physicalcpu hw.perflevel1.physicalcpu\` | $(s hw.perflevel0.physicalcpu) / $(s hw.perflevel1.physicalcpu) |
| Cache line | \`sysctl hw.cachelinesize\` | $(s hw.cachelinesize) bytes |
| P-core L1d / L2 | \`sysctl hw.perflevel0.l1dcachesize hw.perflevel0.l2cachesize\` | $(kib hw.perflevel0.l1dcachesize) / $(kib hw.perflevel0.l2cachesize) |
| E-core L1d / L2 | \`sysctl hw.perflevel1.l1dcachesize hw.perflevel1.l2cachesize\` | $(kib hw.perflevel1.l1dcachesize) / $(kib hw.perflevel1.l2cachesize) |
| Page size | \`pagesize\` | $(($(pagesize) / 1024)) KiB |
| BF16 | \`sysctl hw.optional.arm.FEAT_BF16\` | $(yn hw.optional.arm.FEAT_BF16) |
| Int8 dot product | \`sysctl hw.optional.arm.FEAT_DotProd\` | $(yn hw.optional.arm.FEAT_DotProd) |
| Int8 matrix multiply | \`sysctl hw.optional.arm.FEAT_I8MM\` | $(yn hw.optional.arm.FEAT_I8MM) |
| FP16 arithmetic | \`sysctl hw.optional.arm.FEAT_FP16\` | $(yn hw.optional.arm.FEAT_FP16) |
| SME / SME2 | \`sysctl hw.optional.arm.FEAT_SME hw.optional.arm.FEAT_SME2\` | $(yn hw.optional.arm.FEAT_SME) / $(yn hw.optional.arm.FEAT_SME2) |
| OS | \`sw_vers\` | macOS $(sw_vers -productVersion) ($(sw_vers -buildVersion)) |
| Compiler | \`clang++ --version\` | $(clang++ --version | head -1) |
TABLE
