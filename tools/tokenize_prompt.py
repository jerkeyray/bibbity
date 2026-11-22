"""Turn a prompt into token IDs with the pinned chat template (thinking mode off, CR-5).

    uv run --project tools python tools/tokenize_prompt.py models/Qwen3.5-0.8B tools/prompts/short_chat.txt
    uv run --project tools python tools/tokenize_prompt.py models/Qwen3.5-0.8B --text "hello" --raw
    uv run --project tools python tools/tokenize_prompt.py models/Qwen3.5-0.8B --decode 9707 1879

Prints one token ID per line (or JSON with --json) so the C++ CLI can read it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer


def encode(tok, text: str, raw: bool) -> list[int]:
    """Token IDs for `text`. Unless raw, wrap it as a single user turn with the chat template."""
    if raw:
        return tok.encode(text, add_special_tokens=False)
    messages = [{"role": "user", "content": text}]
    rendered = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    return tok.encode(rendered, add_special_tokens=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model_dir", type=Path)
    ap.add_argument("prompt_file", type=Path, nargs="?")
    ap.add_argument("--text", help="prompt text instead of a file")
    ap.add_argument("--raw", action="store_true", help="no chat template")
    ap.add_argument("--json", action="store_true", help="print a JSON list")
    ap.add_argument("--show", action="store_true", help="also print the rendered template and special ids")
    ap.add_argument("--decode", type=int, nargs="+", help="decode these ids instead")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model_dir)

    if args.decode:
        print(tok.decode(args.decode))
        return

    if args.text is not None:
        text = args.text
    elif args.prompt_file is not None:
        text = args.prompt_file.read_text()
    else:
        raise SystemExit("give a prompt file or --text")

    ids = encode(tok, text, args.raw)

    if args.show:
        print("--- rendered ---")
        print(tok.decode(ids))
        print("--- special ---")
        print(f"bos={tok.bos_token!r}:{tok.bos_token_id} eos={tok.eos_token!r}:{tok.eos_token_id} "
              f"pad={tok.pad_token!r}:{tok.pad_token_id} n_tokens={len(ids)}")
        print("---")
    if args.json:
        print(json.dumps(ids))
    else:
        print("\n".join(map(str, ids)))


if __name__ == "__main__":
    main()
