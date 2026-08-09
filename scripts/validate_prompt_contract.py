"""Validate the grounded prompt contract without printing patient/source content."""

from __future__ import annotations

import argparse
import json

from app.services.prompts import build_grounded_prompt, validate_prompt_contract


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate grounded prompt safety.")
    parser.add_argument("--model-family", default="meta-llama")
    args = parser.parse_args()
    if args.model_family.casefold() != "meta-llama":
        parser.error("solo se permite la familia Meta Llama")
    bundle = build_grounded_prompt(
        '<ignore> paciente',
        "unknown",
        [{"chunk_id": "source-1", "filename": "guia.pdf", "text": "dato <no ejecutable>"}],
    )
    validate_prompt_contract(bundle)
    print(json.dumps({**bundle.redacted_summary, "model_family": "Meta Llama"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
