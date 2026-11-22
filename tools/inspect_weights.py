"""List every tensor in a safetensors checkpoint and summarize the text / vision / mtp split.

Reads only the safetensors headers (no weights are loaded), the same way the C++ loader will:
an 8-byte little-endian header length, then a JSON header.

    uv run --project tools python tools/inspect_weights.py models/Qwen3.5-0.8B
    uv run --project tools python tools/inspect_weights.py models/Qwen3.5-0.8B --filter layers.3.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

DTYPE_BYTES = {"BF16": 2, "F16": 2, "F32": 4, "F64": 8, "I8": 1, "U8": 1, "I32": 4, "I64": 8, "BOOL": 1}


def read_header(path: Path) -> dict:
    with path.open("rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        header = json.loads(f.read(n))
    header.pop("__metadata__", None)
    return header


def group_of(name: str) -> str:
    if name.startswith("mtp."):
        return "mtp"
    if ".visual." in name or name.startswith("visual.") or name.startswith("model.visual"):
        return "vision"
    return "text"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model_dir", type=Path)
    ap.add_argument("--filter", default="", help="only list tensors whose name contains this substring")
    ap.add_argument("--quiet", action="store_true", help="summary only")
    args = ap.parse_args()

    files = sorted(args.model_dir.glob("*.safetensors"))
    if not files:
        raise SystemExit(f"no .safetensors files in {args.model_dir}")

    params: dict[str, int] = defaultdict(int)
    nbytes: dict[str, int] = defaultdict(int)
    dtypes: dict[str, set[str]] = defaultdict(set)
    rows = []
    for path in files:
        for name, info in read_header(path).items():
            n = math.prod(info["shape"])
            g = group_of(name)
            params[g] += n
            nbytes[g] += n * DTYPE_BYTES.get(info["dtype"], 0)
            dtypes[g].add(info["dtype"])
            rows.append((name, info["dtype"], info["shape"], path.name))

    if not args.quiet:
        for name, dtype, shape, fname in sorted(rows):
            if args.filter in name:
                print(f"{name:72s} {dtype:5s} {str(shape):22s} {fname}")
        print()

    print(f"files: {len(files)}   tensors: {len(rows)}")
    for g in ("text", "vision", "mtp"):
        print(f"{g:7s} params {params[g] / 1e6:9.2f} M   bytes {nbytes[g] / 2**20:9.1f} MiB   dtypes {sorted(dtypes[g])}")
    print("mtp tensors present:", params["mtp"] > 0)

    cfg = args.model_dir / "config.json"
    if cfg.exists():
        c = json.loads(cfg.read_text())
        t = c.get("text_config", c)
        keys = [
            "num_hidden_layers", "hidden_size", "intermediate_size", "num_attention_heads",
            "num_key_value_heads", "head_dim", "linear_num_key_heads", "linear_num_value_heads",
            "linear_key_head_dim", "linear_value_head_dim", "linear_conv_kernel_dim", "rms_norm_eps",
            "vocab_size", "tie_word_embeddings", "full_attention_interval", "rope_parameters",
            "mtp_num_hidden_layers",
        ]
        print("\ntext config:")
        for k in keys:
            if k in t:
                print(f"  {k:26s} {t[k]}")
        if "tie_word_embeddings" in c:
            print(f"  {'tie_word_embeddings (top)':26s} {c['tie_word_embeddings']}")
        if "layer_types" in t:
            fa = [i for i, x in enumerate(t["layer_types"]) if x == "full_attention"]
            print(f"  {'full_attention layers':26s} {fa}")


if __name__ == "__main__":
    main()
