#!/usr/bin/env python3
"""SFT paraphrase pipeline for LIBERO successful rollouts.

For each successful rollout we produce N paraphrased variations. Every variation
rewrites *everything* — initial instruction, tool function names, docstrings,
argument orders, thinking, non-code prose, and the generated code — while keeping
the code logically coherent with the (also paraphrased) API surface.

Architecture (per design decision): LLM rewrites a full variation as one JSON
object; a deterministic validator gates it on
  (1) ast.parse(code) succeeds,
  (2) every API-style call in the code resolves to a function declared in that
      variation's paraphrased api spec,
  (3) call arity is compatible with the declared signature,
  (4) any keyword argument used resolves to a declared parameter name,
  (5) no *original* API name leaks into the paraphrased code.
On failure we retry the LLM up to --max-retries times; only clean variations are kept.

Storage: variations are written to a separate, centralized tree
(--out-dir, default outputs/sft-paraphrase-<stamp>/). Source capx outputs are
read-only and untouched.

Usage:
  # pilot: one rollout, 2 variations
  python scripts/sft_paraphrase.py --limit 1 --n-variations 2 --out-dir outputs/sft-pilot

  # full run
  python scripts/sft_paraphrase.py --n-variations 10
"""
from __future__ import annotations

import argparse
import ast
import glob
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict

import requests  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Source session dirs holding successful rollouts.
SOURCE_ROOTS = [
    "outputs/libero-opus4_8-20260612-1810",
    "outputs/libero-gemini31-20260615-2220",
    "outputs/libero-gemini31-campaign-20260615-2314",
    "outputs/libero-gemini31-topup-20260616-1957",
    "outputs/libero-opus48-topup-20260616-1957",
    "outputs/libero-union-20260616-2237",
]



# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

@dataclass
class ApiFunc:
    name: str
    signature: str   # raw signature line, e.g. "goto_pose(position: np.ndarray, ...) -> None"
    doc: str


@dataclass
class Rollout:
    rollout_id: str
    task: str
    model: str
    source_dir: str
    instruction: str          # full pre-"APIs:" prompt text
    api_block: str            # raw "APIs:" block text
    api_funcs: list           # list[ApiFunc]
    code: str
    thinking: str
    response_prose: str


_API_FN_RE = re.compile(r"^([a-z_][a-zA-Z0-9_]*)\(", re.M)


def parse_api_block(block: str) -> list:
    """Parse the 'APIs:' block into structured ApiFunc entries."""
    body = block.split("APIs:", 1)[1] if "APIs:" in block else block
    # Find each top-level function entry (name( at column 0).
    matches = list(_API_FN_RE.finditer(body))
    funcs = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[start:end]
        # signature = up to first newline; doc = remainder after "Doc:"
        sig_line = chunk.splitlines()[0].strip()
        doc = ""
        if "Doc:" in chunk:
            doc = chunk.split("Doc:", 1)[1].strip("\n")
            # dedent common leading whitespace
            lines = [ln for ln in doc.splitlines()]
            doc = "\n".join(ln.strip() for ln in lines).strip()
        funcs.append(ApiFunc(name=m.group(1), signature=sig_line, doc=doc))
    return funcs


def extract_rollout(trial_dir: str, root: str) -> Rollout | None:
    code_f = os.path.join(trial_dir, "code.py")
    prompt_f = os.path.join(trial_dir, "prompts_and_responses", "initial_prompt.txt")
    resp_f = os.path.join(trial_dir, "all_responses.json")
    if not (os.path.exists(code_f) and os.path.exists(prompt_f)):
        return None
    prompt = open(prompt_f, encoding="utf-8", errors="replace").read()
    if "APIs:" not in prompt:
        return None
    instruction, api_block = prompt.split("APIs:", 1)
    api_block = "APIs:" + api_block
    code = open(code_f, encoding="utf-8", errors="replace").read()
    # strip leading "# Code block N" marker lines
    code = re.sub(r"^# Code block \d+\n", "", code)

    thinking, prose = "", ""
    if os.path.exists(resp_f):
        try:
            d = json.load(open(resp_f))
            t0 = d[0] if isinstance(d, list) and d else d
            thinking = t0.get("reasoning") or ""
        except Exception:
            pass
    raw_f = os.path.join(trial_dir, "raw_response.sh")
    if os.path.exists(raw_f):
        raw = open(raw_f, encoding="utf-8", errors="replace").read()
        # non-code prose = text outside ```...``` fences
        prose = re.sub(r"```.*?```", "", raw, flags=re.S).strip()

    depth = len(root.rstrip("/").split("/"))
    parts = trial_dir.split("/")
    model_seg = parts[depth]
    model = ("gemini-3.1-pro" if "gemini" in model_seg else
             "opus-4.8" if ("opus" in model_seg or "anthropic" in model_seg) else
             "gpt-5.5" if "gpt" in model_seg else "other")
    task_dir = os.path.basename(os.path.dirname(trial_dir))
    rid = hashlib.md5(trial_dir.encode()).hexdigest()[:10]
    return Rollout(
        rollout_id=f"{task_dir}__{model}__{rid}",
        task=task_dir, model=model, source_dir=trial_dir,
        instruction=instruction.strip(), api_block=api_block.strip(),
        api_funcs=parse_api_block(api_block), code=code.strip(),
        thinking=thinking.strip(), response_prose=prose.strip(),
    )


def discover_rollouts(roots: list) -> list:
    out = []
    seen = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for tr in sorted(glob.glob(os.path.join(root, "*", "*", "trial_*_taskcompleted_1"))):
            if not os.path.isdir(tr):
                continue
            r = extract_rollout(tr, root)
            if r and r.rollout_id not in seen:
                seen.add(r.rollout_id)
                out.append(r)
    return out


# ---------------------------------------------------------------------------
# Validation: cheap parse gate + independent LLM coherence judge
# ---------------------------------------------------------------------------

@dataclass
class ValResult:
    ok: bool
    errors: list = field(default_factory=list)


def parse_gate(variation: dict) -> ValResult:
    """Free, zero-false-positive structural checks: required keys present and the
    code is syntactically valid Python. Everything semantic is left to the LLM judge."""
    api = variation.get("api")
    code = variation.get("code")
    if not isinstance(api, list) or not api:
        return ValResult(False, ["missing/empty 'api'"])
    if not isinstance(code, str) or not code.strip():
        return ValResult(False, ["missing/empty 'code'"])
    try:
        ast.parse(code)
    except SyntaxError as e:
        return ValResult(False, [f"code is not valid Python: {e}"])
    return ValResult(True, [])


JUDGE_SYSTEM = (
    "You are a strict validator for paraphrased code-as-policy training data. You are given a "
    "paraphrased API definition and a paraphrased Python program. Judge ONLY coherence between "
    "them — not style. Return a JSON object {\"coherent\": bool, \"reasons\": [str]}.\n\n"
    "Mark coherent=false if ANY of these hold:\n"
    "- the code calls a function that is NOT defined in the given api (excluding Python builtins, "
    "numpy/np, and helper functions the code defines itself);\n"
    "- a call passes arguments inconsistent with that function's declared parameters (wrong count, "
    "or a keyword that isn't a declared parameter), in a way that would change behavior or error;\n"
    "- any ORIGINAL (pre-paraphrase) API name appears in the code or api (the orig_name fields tell "
    "you what those were);\n"
    "- the program's behavior is not clearly preserved relative to a faithful paraphrase.\n"
    "Otherwise coherent=true. Be precise; cite the offending call(s) in reasons."
)


def judge_variation(args, variation: dict) -> ValResult:
    """Independent LLM judge of code<->API coherence (different model from the generator)."""
    api = variation.get("api", [])
    payload_obj = {"api": api, "code": variation.get("code", "")}
    prompt = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": [{"type": "text", "text":
            "Validate this paraphrased sample. Return only the JSON verdict.\n\n"
            + json.dumps(payload_obj, indent=1)}]},
    ]
    try:
        content = _post_to(args.judge_model, args.judge_server_url, args.judge_effort, prompt,
                           max_tokens=2000)
        verdict = parse_json_response(content)
    except Exception as e:
        # On judge failure, don't silently accept — surface as a retryable error.
        return ValResult(False, [f"judge call failed: {e}"])
    if not isinstance(verdict, dict) or "coherent" not in verdict:
        return ValResult(False, ["judge returned malformed verdict"])
    if verdict.get("coherent"):
        return ValResult(True, [])
    return ValResult(False, list(verdict.get("reasons", []) or ["judge: not coherent"]))


# ---------------------------------------------------------------------------
# Paraphrase prompt + LLM
# ---------------------------------------------------------------------------

STYLE_HINTS = [
    "verbose descriptive snake_case names; reorder some parameters",
    "terse short names; keep most parameter orders",
    "domain/robotics-flavored names (e.g. eef, manip); reorder parameters",
    "action-verb-first function names; rename and reorder some parameters",
    "formal API-style names with noun phrases; reorder parameters",
    "compact lowercase names with abbreviations; minor reorders",
    "explicit intent-revealing long names; reorder parameters",
    "neutral plain names different from originals; reorder some parameters",
    "camel-ish-but-pythonic distinct names; reorder parameters",
    "alternative vocabulary (grip/arm/scene) names; reorder parameters",
]


def build_paraphrase_prompt(r: Rollout, var_idx: int, prev_errors: list) -> list:
    style = STYLE_HINTS[var_idx % len(STYLE_HINTS)]
    api_json = [{"name": f.name, "signature": f.signature, "doc": f.doc} for f in r.api_funcs]
    retry_note = ""
    if prev_errors:
        retry_note = ("\n\nYour previous attempt FAILED validation with these errors — fix them:\n- "
                      + "\n- ".join(prev_errors[:8]))
    system = (
        "You produce paraphrased training data for code-as-policy robot control. "
        "You rewrite an instruction, a tool/API definition, a chain-of-thought, optional prose, "
        "and a Python program into a SEMANTICALLY IDENTICAL but SURFACE-DIFFERENT variation. "
        "The rewritten code MUST remain logically coherent with the rewritten API: it may only call "
        "functions you declare in `api`, with arguments consistent with your declared parameters.\n\n"
        "HARD RULES:\n"
        "1. Rename every API function and parameter to NEW names (do not reuse any original name).\n"
        "2. You MAY reorder parameters. WHENEVER you rename OR reorder a function's parameters, the "
        "code MUST call that function using KEYWORD arguments (e.g. f(target=..., orient=...)), so the "
        "call is unambiguous.\n"
        "3. The code's logic/behavior must be preserved exactly — same control flow, same numeric "
        "constants, same object-name strings, same outcome. Only identifiers and surface syntax change.\n"
        "4. Reword the instruction, all docstrings, the thinking, and prose with fresh wording. Keep the "
        "robot goal and meaning identical. Do NOT mention any original API name anywhere.\n"
        "5. Output ONE JSON object only, no markdown fences."
    )
    user = (
        f"Variation style for this sample: {style}.\n\n"
        f"Return a JSON object with keys exactly: api, instruction, thinking, response, code.\n"
        f"- api: list of objects {{orig_name, name, params:[{{orig,name,default?}}], returns, doc}} — "
        f"one per original function, declaring your new names + (possibly reordered) params + reworded doc.\n"
        f"- instruction: paraphrased instruction text (the part before the API list).\n"
        f"- thinking: paraphrased chain-of-thought.\n"
        f"- response: paraphrased non-code prose (use \"\" if none).\n"
        f"- code: paraphrased Python program using ONLY your new api names; keyword args where reordered.\n\n"
        f"=== ORIGINAL INSTRUCTION ===\n{r.instruction}\n\n"
        f"=== ORIGINAL API (name/signature/doc) ===\n{json.dumps(api_json, indent=1)}\n\n"
        f"=== ORIGINAL THINKING ===\n{r.thinking or '(none)'}\n\n"
        f"=== ORIGINAL PROSE ===\n{r.response_prose or '(none)'}\n\n"
        f"=== ORIGINAL CODE ===\n{r.code}\n"
        f"{retry_note}"
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": [{"type": "text", "text": user}]}]


def parse_json_response(text: str) -> dict | None:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n", "", t)
        t = re.sub(r"\n```\s*$", "", t)
    try:
        return json.loads(t)
    except Exception:
        # try to grab the outermost {...}
        i, j = t.find("{"), t.rfind("}")
        if 0 <= i < j:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                return None
    return None


def _post_to(model: str, server_url: str, effort: str, prompt: list, max_tokens: int) -> str:
    """POST directly to a proxy so reasoning_effort is honored (query_model's
    openrouter branch drops it)."""
    payload = {"model": model, "messages": prompt, "max_tokens": max_tokens,
               "reasoning_effort": effort}
    resp = requests.post(server_url, headers={"Content-Type": "application/json"},
                         data=json.dumps(payload), timeout=600)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_variation(args, r: Rollout, var_idx: int) -> dict:
    errs = []
    for attempt in range(1, args.max_retries + 2):
        prompt = build_paraphrase_prompt(r, var_idx, errs)
        try:
            content = _post_to(args.model, args.server_url, args.reasoning_effort,
                               prompt, args.max_tokens)
            var = parse_json_response(content)
        except Exception as e:
            errs = [f"generator call/parse exception: {e}"]
            continue
        if var is None:
            errs = ["generator response was not valid JSON"]
            continue
        # 1) free structural gate
        pg = parse_gate(var)
        if not pg.ok:
            errs = pg.errors
            continue
        # 2) independent LLM coherence judge
        jr = judge_variation(args, var)
        if jr.ok:
            return {"variation_index": var_idx, "status": "ok", "attempts": attempt,
                    "data": var}
        errs = jr.errors
    return {"variation_index": var_idx, "status": "failed", "attempts": args.max_retries + 1,
            "errors": errs}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="outputs/sft-paraphrase")
    ap.add_argument("--model", default="openrouter/anthropic/claude-opus-4")
    ap.add_argument("--server-url", default="http://127.0.0.1:8112/chat/completions")
    ap.add_argument("--n-variations", type=int, default=10)
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--reasoning-effort", default="low")
    ap.add_argument("--max-tokens", type=int, default=12000)
    # Independent validator: Sonnet 4.6 (different model from the Opus generator),
    # served by the same Bedrock proxy.
    ap.add_argument("--judge-model", default="openrouter/anthropic/claude-sonnet-4")
    ap.add_argument("--judge-server-url", default="http://127.0.0.1:8112/chat/completions")
    ap.add_argument("--judge-effort", default="low")
    ap.add_argument("--workers", type=int, default=12, help="concurrent variation tasks")
    ap.add_argument("--limit", type=int, default=0, help="cap number of rollouts (0 = all)")
    ap.add_argument("--only", default="", help="substring filter on rollout_id")
    ap.add_argument("--min-thinking-chars", type=int, default=0,
                    help="drop source rollouts whose thinking is shorter than this "
                         "(0 = keep all). Use 0 with --thinking-dir since reconstructed "
                         "traces replace captured thinking.")
    ap.add_argument("--thinking-dir", default="outputs/sft-think-recon",
                    help="dir of reconstructed-thinking JSONs (<rollout_id>.json with "
                         "'reconstructed_thinking'); overrides captured thinking. Empty = use captured.")
    args = ap.parse_args()

    os.environ.setdefault("OPENROUTER_SERVER_URL", args.server_url)
    os.makedirs(os.path.join(args.out_dir, "variations"), exist_ok=True)
    manifest_f = os.path.join(args.out_dir, "manifest.jsonl")

    rollouts = discover_rollouts(SOURCE_ROOTS)
    n_all = len(rollouts)
    # Replace captured thinking with reconstructed traces (approach A).
    n_recon = 0
    if args.thinking_dir:
        for r in rollouts:
            tf = os.path.join(args.thinking_dir, f"{r.rollout_id}.json")
            if os.path.exists(tf):
                try:
                    rec = json.load(open(tf)).get("reconstructed_thinking", "").strip()
                    if rec:
                        r.thinking = rec
                        n_recon += 1
                except Exception:
                    pass
    if args.min_thinking_chars > 0:
        rollouts = [r for r in rollouts if len((r.thinking or "").strip()) >= args.min_thinking_chars]
    n_thinking = len(rollouts)
    print(f"reconstructed-thinking applied to {n_recon}/{n_all} rollouts")
    if args.only:
        rollouts = [r for r in rollouts if args.only in r.rollout_id]
    if args.limit:
        rollouts = rollouts[:args.limit]
    print(f"discovered {n_all} rollouts; {n_thinking} have thinking >= {args.min_thinking_chars} chars; "
          f"processing {len(rollouts)}; generating {args.n_variations} variations each")

    # Flatten to (rollout, var_idx) units and run them across a shared pool, so
    # all --workers stay busy regardless of per-rollout variation count. Results
    # are collected per rollout and written when that rollout's variations finish.
    pending = []  # (rollout, var_idx)
    skipped = 0
    by_rollout = {}
    for r in rollouts:
        out_f = os.path.join(args.out_dir, "variations", f"{r.rollout_id}.json")
        if os.path.exists(out_f):
            skipped += 1
            continue
        by_rollout[r.rollout_id] = {"r": r, "results": [], "need": args.n_variations}
        for vi in range(args.n_variations):
            pending.append((r, vi))
    print(f"{skipped} rollouts already done; {len(by_rollout)} to process "
          f"({len(pending)} variation tasks) with {args.workers} workers")

    def write_rollout(rid):
        slot = by_rollout[rid]
        r = slot["r"]
        variations = sorted(slot["results"], key=lambda v: v["variation_index"])
        ok = sum(v["status"] == "ok" for v in variations)
        record = {"rollout_id": r.rollout_id, "task": r.task, "model": r.model,
                  "source_dir": r.source_dir,
                  "source": {"instruction": r.instruction, "api_block": r.api_block,
                             "code": r.code, "thinking": r.thinking,
                             "response_prose": r.response_prose},
                  "variations": variations}
        out_f = os.path.join(args.out_dir, "variations", f"{r.rollout_id}.json")
        json.dump(record, open(out_f, "w"), indent=1)
        with open(manifest_f, "a") as mf:
            mf.write(json.dumps({"rollout_id": r.rollout_id, "task": r.task,
                                 "model": r.model, "n_ok": ok,
                                 "n_requested": args.n_variations}) + "\n")
        return ok

    done_vars = 0
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(generate_variation, args, r, vi): (r.rollout_id, vi)
                for (r, vi) in pending}
        for fut in as_completed(futs):
            rid, vi = futs[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {"variation_index": vi, "status": "failed", "attempts": 0,
                       "errors": [f"worker exception: {e}"]}
            with lock:
                done_vars += 1
                slot = by_rollout[rid]
                slot["results"].append(res)
                progress = done_vars
                finished = len(slot["results"]) == slot["need"]
                if finished:
                    ok = write_rollout(rid)
            if finished:
                print(f"[{progress}/{len(pending)}] rollout {rid} complete: "
                      f"{ok}/{args.n_variations} valid")
    print("DONE")


if __name__ == "__main__":
    main()
