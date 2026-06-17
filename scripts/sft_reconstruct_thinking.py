#!/usr/bin/env python3
"""Reconstruct a natural chain-of-thought for a rollout from its prompt + code.

The captured Bedrock/OpenRouter "thinking" is a post-hoc summary — often a stub,
sometimes a giant degenerate loop. For SFT we'd rather have a clean first-person
planning trace that plausibly *leads to* the actual code. This step regenerates
that from (instruction + API + final code), independent of the captured thinking.

Pilot usage:
  python scripts/sft_reconstruct_thinking.py --limit 3 --out outputs/sft-think-recon
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scripts.sft_paraphrase as P  # reuse discovery / extraction  # noqa: E402

RECON_SYSTEM = (
    "You reconstruct the INTERNAL REASONING a robot-control coding agent would have produced "
    "BEFORE writing a given program. You are given the task instruction, the available API, and "
    "the FINAL Python program the agent wrote. Write the first-person chain-of-thought that "
    "naturally leads to that exact program.\n\n"
    "RULES:\n"
    "- Write as forward-looking planning ('I need to...', 'First I'll...', 'The grasp pose might "
    "be unreliable, so I'll...'), NOT as a retrospective description of finished code.\n"
    "- Ground it in the ACTUAL decisions visible in the code: which API calls are used and why, "
    "fallbacks/retries, the chosen offsets/constants, the order of operations, error handling.\n"
    "- Refer to the real API function names from the provided API (do not invent functions).\n"
    "- Explain the WHY (perception may fail, need an approach offset, must open gripper first, "
    "etc.) — the reasoning a thoughtful agent would have, not a line-by-line narration.\n"
    "- Do NOT include code or code fences. Prose only. 1-4 short paragraphs.\n"
    "- Output ONLY the reasoning text, no preamble."
)


def build_prompt(r) -> list:
    api_json = [{"name": f.name, "signature": f.signature, "doc": f.doc} for f in r.api_funcs]
    user = (
        f"=== TASK INSTRUCTION ===\n{r.instruction}\n\n"
        f"=== AVAILABLE API (name/signature/doc) ===\n{json.dumps(api_json, indent=1)}\n\n"
        f"=== FINAL PROGRAM THE AGENT WROTE ===\n{r.code}\n\n"
        f"Write the chain-of-thought that leads to this program."
    )
    return [{"role": "system", "content": RECON_SYSTEM},
            {"role": "user", "content": [{"type": "text", "text": user}]}]


def post(model, url, effort, prompt, max_tokens):
    payload = {"model": model, "messages": prompt, "max_tokens": max_tokens,
               "reasoning_effort": effort}
    resp = requests.post(url, headers={"Content-Type": "application/json"},
                         data=json.dumps(payload), timeout=600)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs/sft-think-recon")
    ap.add_argument("--model", default="openrouter/anthropic/claude-opus-4")
    ap.add_argument("--server-url", default="http://127.0.0.1:8112/chat/completions")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    rollouts = P.discover_rollouts(P.SOURCE_ROOTS)
    if args.only:
        rollouts = [r for r in rollouts if args.only in r.rollout_id]
    if args.limit:
        rollouts = rollouts[:args.limit]
    # skip already-done
    todo = [r for r in rollouts
            if not os.path.exists(os.path.join(args.out, f"{r.rollout_id}.json"))]
    print(f"reconstructing thinking for {len(todo)}/{len(rollouts)} rollouts "
          f"({len(rollouts)-len(todo)} cached) with {args.workers} workers")

    def work(r):
        try:
            recon = post(args.model, args.server_url, args.effort, build_prompt(r), args.max_tokens)
        except Exception as e:
            return r, None, str(e)
        rec = {"rollout_id": r.rollout_id, "task": r.task, "model": r.model,
               "captured_thinking": r.thinking, "captured_len": len(r.thinking or ""),
               "reconstructed_thinking": recon, "recon_len": len(recon)}
        json.dump(rec, open(os.path.join(args.out, f"{r.rollout_id}.json"), "w"), indent=1)
        return r, rec, None

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(work, r): r for r in todo}
        for fut in as_completed(futs):
            r, rec, err = fut.result()
            done += 1
            if err:
                print(f"[{done}/{len(todo)}] {r.rollout_id}: ERROR {err[:120]}")
            else:
                print(f"[{done}/{len(todo)}] {r.rollout_id}: {rec['captured_len']} "
                      f"-> {rec['recon_len']} chars")
    print("DONE")


if __name__ == "__main__":
    main()
