"""Golden dumps: run the Hugging Face model in fp32 on CPU and save every layer's intermediate outputs.

For each prompt in tools/prompts/*.txt, writes golden/<prompt>/:

    tokens.npy                    int32 [T]           input token IDs (chat template, thinking off)
    embed.npy                     f32   [T, H]        embedding output
    layer_XX.in.npy               f32   [T, H]        residual stream entering layer XX
    layer_XX.mixer_in.npy         f32   [T, H]        input_layernorm output (what the mixer sees)
    layer_XX.mixer.npy            f32   [T, H]        mixer output (attention or DeltaNet), before the residual add
    layer_XX.mlp_in.npy           f32   [T, H]        post_attention_layernorm output
    layer_XX.mlp.npy              f32   [T, H]        FFN output, before the residual add
    final_norm.npy                f32   [T, H]        final RMSNorm output
    logits.npy                    f32   [1, V]        logits at the last position ([T, V] with --all-logits; ~1 MB per token)
    greedy.npy                    int32 [N]           N greedy tokens generated after the prompt (--greedy N)
    manifest.json                 shapes, dtypes, sha256 of every file, versions, layer types

The `*.in` / `*_in` files let each layer be tested in isolation with reference inputs (M3, M4).
Everything is deterministic: rerunning produces byte-identical files (check with --verify).

    uv run --project tools python tools/golden_dump.py models/Qwen3.5-0.8B
    uv run --project tools python tools/golden_dump.py models/Qwen3.5-0.8B --prompts short_chat --greedy 32
    uv run --project tools python tools/golden_dump.py models/Qwen3.5-0.8B --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import tempfile
from pathlib import Path

import numpy as np
import torch
import transformers
from transformers import AutoModelForImageTextToText, AutoTokenizer

from tokenize_prompt import encode

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "tools" / "prompts"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(model_dir: Path):
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)  # same reduction order every run → byte-identical dumps
    model = AutoModelForImageTextToText.from_pretrained(
        model_dir, dtype=torch.float32, attn_implementation="eager"
    )
    model.eval()
    tok = AutoTokenizer.from_pretrained(model_dir)
    return model, tok


def text_model(model):
    """The text decoder (Qwen3_5TextModel) inside the multimodal wrapper."""
    lm = model.model.language_model
    assert hasattr(lm, "layers") and hasattr(lm, "embed_tokens"), type(lm)
    return lm


def dump_prompt(model, tok, name: str, text: str, out: Path, greedy: int, all_logits: bool) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    lm = text_model(model)
    layer_types = list(lm.config.layer_types)
    saved: dict[str, np.ndarray] = {}

    def save(key: str, t: torch.Tensor) -> None:
        saved[key] = t.detach()[0].to(torch.float32).cpu().numpy()  # drop batch dim

    hooks = []
    hooks.append(lm.embed_tokens.register_forward_hook(lambda m, i, o: save("embed", o)))
    for li, layer in enumerate(lm.layers):
        p = f"layer_{li:02d}"
        mixer = layer.linear_attn if layer_types[li] == "linear_attention" else layer.self_attn
        hooks += [
            layer.register_forward_pre_hook(lambda m, a, kw=None, p=p: save(f"{p}.in", a[0])),
            layer.input_layernorm.register_forward_hook(lambda m, i, o, p=p: save(f"{p}.mixer_in", o)),
            mixer.register_forward_hook(
                lambda m, i, o, p=p: save(f"{p}.mixer", o[0] if isinstance(o, tuple) else o)
            ),
            layer.post_attention_layernorm.register_forward_hook(lambda m, i, o, p=p: save(f"{p}.mlp_in", o)),
            layer.mlp.register_forward_hook(lambda m, i, o, p=p: save(f"{p}.mlp", o)),
        ]
    hooks.append(lm.norm.register_forward_hook(lambda m, i, o: save("final_norm", o)))

    ids = encode(tok, text, raw=False)
    input_ids = torch.tensor([ids], dtype=torch.long)
    try:
        with torch.no_grad():
            logits = model(input_ids=input_ids, use_cache=False).logits[0].to(torch.float32).numpy()
    finally:
        for h in hooks:
            h.remove()

    saved["tokens"] = np.asarray(ids, dtype=np.int32)
    saved["logits"] = logits if all_logits else logits[-1:]

    if greedy > 0:
        with torch.no_grad():
            gen = model.generate(
                input_ids=input_ids, max_new_tokens=greedy, do_sample=False,
                pad_token_id=tok.pad_token_id or tok.eos_token_id,
            )
        saved["greedy"] = gen[0, len(ids):].numpy().astype(np.int32)

    files = {}
    for key, arr in sorted(saved.items()):
        path = out / f"{key}.npy"
        np.save(path, np.ascontiguousarray(arr), allow_pickle=False)
        files[path.name] = {"shape": list(arr.shape), "dtype": str(arr.dtype), "sha256": sha256(path)}

    manifest = {
        "prompt": name,
        "n_tokens": len(ids),
        "layer_types": layer_types,
        "files": files,
        "versions": {
            "torch": torch.__version__, "transformers": transformers.__version__,
            "numpy": np.__version__, "python": platform.python_version(),
        },
        "settings": {"dtype": "float32", "device": "cpu", "attn": "eager", "threads": 1,
                     "chat_template": True, "enable_thinking": False},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    top = int(np.argmax(logits[-1]))
    print(f"{name}: {len(ids)} tokens, {len(files)} arrays, next token {top} {tok.decode([top])!r}")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model_dir", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "golden")
    ap.add_argument("--prompts", nargs="*", help="prompt names (file stems in tools/prompts); default all")
    ap.add_argument("--greedy", type=int, default=32, help="greedy tokens to record (0 to skip)")
    ap.add_argument("--all-logits", action="store_true", help="save logits for every position, not just the last")
    ap.add_argument("--verify", action="store_true",
                    help="regenerate into a temp dir and check every sha256 matches the existing dumps")
    args = ap.parse_args()

    files = sorted(PROMPTS.glob("*.txt"))
    if args.prompts:
        files = [f for f in files if f.stem in set(args.prompts)]
    if not files:
        raise SystemExit("no prompts selected")

    model, tok = load(args.model_dir)

    if args.verify:
        ok = True
        with tempfile.TemporaryDirectory() as tmp:
            for f in files:
                new = dump_prompt(model, tok, f.stem, f.read_text(), Path(tmp) / f.stem,
                                  args.greedy, args.all_logits)
                old_path = args.out / f.stem / "manifest.json"
                if not old_path.exists():
                    print(f"  {f.stem}: no existing dump to compare"); ok = False; continue
                old = json.loads(old_path.read_text())["files"]
                for k, v in new["files"].items():
                    if old.get(k, {}).get("sha256") != v["sha256"]:
                        print(f"  MISMATCH {f.stem}/{k}"); ok = False
        print("verify:", "byte-identical" if ok else "FAILED")
        raise SystemExit(0 if ok else 1)

    for f in files:
        dump_prompt(model, tok, f.stem, f.read_text(), args.out / f.stem, args.greedy, args.all_logits)


if __name__ == "__main__":
    main()
