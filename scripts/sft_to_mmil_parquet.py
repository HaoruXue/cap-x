#!/usr/bin/env python3
"""Convert SFT paraphrase variations -> MMIL parquet for the one-model pipeline.

Each VALID paraphrase variation becomes one training example (one MMIL document):

    system    : the paraphrased API definition (that variation's tool surface)
    user      : the paraphrased instruction
    assistant : reasoning = paraphrased thinking, content = paraphrased code

Faithful pass-through — fields are emitted exactly as they appear in the
variation (bare code, reasoning as-is); nothing is reformatted.

Built with the canonical one-model builders (no format drift), so it must run
with one-model's venv:

    /k8s-nfs/personal/haoru/one/ws0/one-model/.venv/bin/python \\
        scripts/sft_to_mmil_parquet.py \\
        --variations-dir outputs/sft-paraphrase/variations \\
        --out outputs/sft-mmil/capx_sft_paraphrase.parquet \\
        --task-tag capx_sft_paraphrase

Output schema (MMIL): columns `datum` (compact-JSON document) + `tasks` (list[str]).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

# Import the canonical one-model converter helpers.
_OM_CONV = "/k8s-nfs/personal/haoru/one/ws0/one-model/one_model/external/one-model-internal"
sys.path.insert(0, _OM_CONV)
import pyarrow as pa  # noqa: E402
from one_model_internal.converters import _common  # noqa: E402

SCHEMA = pa.schema([("datum", pa.string()), ("tasks", pa.list_(pa.string()))])


def api_to_text(api: list) -> str:
    """Render a variation's paraphrased API spec as a readable tool definition,
    mirroring the structure of the original prompt's 'APIs:' block."""
    lines = ["APIs:", ""]
    for f in api:
        name = f.get("name", "")
        params = f.get("params", []) or []
        sig = ", ".join(p.get("name", "") for p in params)
        ret = f.get("returns", "")
        head = f"{name}({sig})" + (f" -> {ret}" if ret else "")
        lines.append(head)
        doc = (f.get("doc") or "").strip()
        if doc:
            lines.append("  Doc:")
            for dl in doc.splitlines():
                lines.append("    " + dl)
        lines.append("")
    return "\n".join(lines).rstrip()


def variation_to_messages(variation_data: dict) -> list:
    """Build the agentic message list for one variation (faithful pass-through)."""
    api_text = api_to_text(variation_data.get("api", []))
    instruction = (variation_data.get("instruction") or "").strip()
    thinking = (variation_data.get("thinking") or "").strip() or None
    code = variation_data.get("code") or ""
    prose = (variation_data.get("response") or "").strip()
    # Assistant content is the code, faithfully. If the variation carried any
    # non-code prose (rare), keep it ahead of the code so nothing is dropped.
    answer = f"{prose}\n\n{code}" if prose else code
    return [
        {"role": "system", "content": api_text},
        {"role": "user", "content": instruction},
        {"role": "assistant", "reasoning": thinking, "tool_calls": None, "content": answer},
    ]


def iter_examples(variations_dir: str):
    """Yield (meta, variation_data) for every VALID variation across all rollout files."""
    files = sorted(glob.glob(os.path.join(variations_dir, "*.json")))
    for f in files:
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for v in d.get("variations", []):
            if v.get("status") != "ok" or "data" not in v:
                continue
            meta = {"rollout_id": d["rollout_id"], "task": d["task"],
                    "source_model": d["model"], "variation_index": v["variation_index"]}
            yield meta, v["data"]


def row_to_record(row: dict) -> dict:
    """row = {'data': variation_data, 'task_tag': str}. Returns an MMIL parquet record."""
    msgs = variation_to_messages(row["data"])
    doc = _common.build_agentic_trajectory_document(messages=msgs)
    return {"datum": _common.compact_json_dumps(doc), "tasks": [row["task_tag"]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variations-dir", default="outputs/sft-paraphrase/variations")
    ap.add_argument("--out", default="outputs/sft-mmil/capx_sft_paraphrase.parquet")
    ap.add_argument("--task-tag", default="capx_sft_paraphrase")
    ap.add_argument("--limit", type=int, default=0, help="cap examples (0 = all); for piloting")
    ap.add_argument("--meta-out", default="", help="optional jsonl sidecar of per-row metadata")
    # S3 push (one-model far-research-internal bucket). Name auto-appends '_mmil'.
    ap.add_argument("--push-s3", action="store_true", help="push the built table to S3 (PERMANENT)")
    ap.add_argument("--s3-name", default="capx_sft_paraphrase", help="dataset name (without _mmil)")
    ap.add_argument("--s3-version", default="", help="version YYYYMMDD (required with --push-s3)")
    ap.add_argument("--s3-split", default="train")
    ap.add_argument("--s3-on-exists", default="refuse", choices=["refuse", "skip", "force"])
    args = ap.parse_args()

    rows, metas = [], []
    for meta, data in iter_examples(args.variations_dir):
        rows.append({"data": data, "task_tag": args.task_tag})
        metas.append(meta)
        if args.limit and len(rows) >= args.limit:
            break
    print(f"collected {len(rows)} valid variations from {args.variations_dir}")
    if not rows:
        print("nothing to write"); return

    table = _common.build_parquet_table(rows, row_to_record, SCHEMA, num_workers=1)
    from pathlib import Path
    out = _common.write_parquet_shard_local(table, Path(args.out))
    print(f"wrote {table.num_rows} rows -> {out}")
    if args.meta_out:
        with open(args.meta_out, "w") as mf:
            for m in metas:
                mf.write(json.dumps(m) + "\n")
        print(f"wrote metadata sidecar -> {args.meta_out}")

    if args.push_s3:
        if not args.s3_version:
            raise SystemExit("--push-s3 requires --s3-version YYYYMMDD")
        print(f"pushing to S3 (PERMANENT): bucket={_common.PARQUET_BUCKET} "
              f"name={args.s3_name}_mmil version={args.s3_version} split={args.s3_split} "
              f"on_exists={args.s3_on_exists}")
        url = _common.write_parquet_shard_to_s3(
            table, args.s3_name, args.s3_version, args.s3_split,
            on_exists=args.s3_on_exists)
        print(f"S3 -> {url}" if url else "S3 push skipped (key existed, on_exists=skip)")


if __name__ == "__main__":
    main()
