#!/usr/bin/env python3
"""Build the LIBERO successful-trajectory collection index (COLLECTION.md).

Scans every output session dir for trial_*_taskcompleted_1 folders, groups by
environment and model, and emits a tracked markdown index under docs/.
Trajectory data itself stays under gitignored outputs/.
"""
import glob
import os
import re
from collections import defaultdict

# All session dirs that hold collected rollouts (campaigns + comparison + topups + manual).
ROOTS = [
    "outputs/libero-opus4_8-20260612-1810",          # Opus 4.8 original 130-task sweep
    "outputs/libero-gemini31-20260615-2220",         # Gemini 7-task comparison (no reasoning capture)
    "outputs/libero-gemini31-campaign-20260615-2314",# Gemini 130-task sweep
    "outputs/libero-gemini31-topup-20260616-1957",   # Gemini topup
    "outputs/libero-opus48-topup-20260616-1957",     # Opus topup
    "outputs/libero-union-20260616-2237",            # manual union top-up
]


def canon(parent: str) -> str:
    p = re.sub(r"__topup_\d+$", "", parent)
    p = re.sub(r"__G_b\d+$|__O_b\d+$", "", p)
    p = re.sub(r"_resume_\d+$", "", p)
    p = re.sub(r"__(S1|S2).*$", "", p)
    p = re.sub(r"_(S1|S2)$", "", p)
    return p.replace("libero_", "").replace("__", "_")


def model_of(seg: str) -> str:
    if "gemini" in seg:
        return "gemini-3.1-pro"
    if "opus" in seg or "anthropic" in seg:
        return "opus-4.8"
    if "gpt" in seg:
        return "gpt-5.5"
    return "other"


MODELS = ("gemini-3.1-pro", "opus-4.8", "gpt-5.5")


def suite(lab: str) -> str:
    if lab.startswith("object"):
        return "libero_object"
    if lab.startswith("spatial"):
        return "libero_spatial"
    if lab.startswith("goal"):
        return "libero_goal"
    if lab.startswith("10_"):
        return "libero_10"
    if lab.startswith("90_"):
        return "libero_90"
    return "?"


def tid(lab: str) -> int:
    m = re.search(r"(\d+)$", lab)
    return int(m.group(1)) if m else 0


data = defaultdict(lambda: defaultdict(list))
dropped_malformed = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    depth = len(root.rstrip("/").split("/"))
    for tr in glob.glob(os.path.join(root, "*", "*", "trial_*_taskcompleted_1")):
        if not os.path.isdir(tr):
            continue
        seg = tr.split("/")[depth]
        lab = canon(os.path.basename(os.path.dirname(tr)))
        if lab and lab != "_":
            data[lab][model_of(seg)].append(tr)
        else:
            dropped_malformed.append(tr)

tasks = sorted(data, key=lambda l: (suite(l), tid(l)))
L = []
def w(s=""):
    L.append(s)

g = sum(len(data[t].get("gemini-3.1-pro", [])) for t in tasks)
o = sum(len(data[t].get("opus-4.8", [])) for t in tasks)
gpt = sum(len(data[t].get("gpt-5.5", [])) for t in tasks)
def env_union(t):
    return max(len(data[t].get(m, [])) for m in MODELS)
u = sum(env_union(t) for t in tasks)
n10 = sum(1 for t in tasks if env_union(t) >= 10)
raw = g + o + gpt

w("# LIBERO Successful-Trajectory Collection")
w()
w("Inventory of every successful rollout (`taskcompleted_1`) collected across the")
w("Gemini 3.1 Pro and Opus 4.8 S2 LIBERO campaigns, the 7-task comparison run, and")
w("the trajectory-collection top-ups (2026-06-12 through 2026-06-16).")
w()
w("**The trajectory data lives under `outputs/` (gitignored — videos + per-turn")
w("JSON, several GB). This file is the tracked index.** Each trajectory directory")
w("contains `code.py`, `all_responses.json` (campaign/topup runs include Gemini/Opus")
w("reasoning summaries), `summary.txt`, and `video_combined.mp4`.")
w()
w("## Totals")
w()
w(f"- **{raw} raw successful trajectories** (Gemini {g} + Opus {o} + GPT-5.5 {gpt})")
w(f"- **{len(tasks)} distinct environments** with at least one success (of 130 S2 tasks)")
w(f"- **{u} trajectories** when deduped to best-model-per-environment")
w(f"- **{n10} environments reached >=10** successes; {len(tasks) - n10} are partial (1-9)")
if dropped_malformed:
    w(f"- ({len(dropped_malformed)} additional success dir(s) with a malformed/empty task label "
      f"excluded: `{dropped_malformed[0]}`)")
w(f"- GPT-5.5's {gpt} trajectories are leftovers from a prior 90_19 Bedrock comparison probe.")
w()
w("> Note: raw counts include multiple sources for the same env (e.g. the 7-task")
w("> comparison run and the full campaign both ran goal_1, 90_19, etc.), so the per-env")
w("> tables below sum every successful rollout for that env across all sessions.")
w()
w("## By suite")
w()
w("| Suite | Envs | Gemini | Opus | GPT-5.5 | Union |")
w("|---|--:|--:|--:|--:|--:|")
bs = defaultdict(lambda: [0, 0, 0, 0, 0])
for t in tasks:
    gg = len(data[t].get("gemini-3.1-pro", []))
    oo = len(data[t].get("opus-4.8", []))
    pp = len(data[t].get("gpt-5.5", []))
    s = suite(t)
    bs[s][0] += 1
    bs[s][1] += gg
    bs[s][2] += oo
    bs[s][3] += pp
    bs[s][4] += env_union(t)
for s in ["libero_object", "libero_spatial", "libero_goal", "libero_10", "libero_90"]:
    b = bs[s]
    w(f"| {s} | {b[0]} | {b[1]} | {b[2]} | {b[3]} | {b[4]} |")
w(f"| **Total** | **{len(tasks)}** | **{g}** | **{o}** | **{gpt}** | **{u}** |")
w()
w("## Per-environment counts")
w()
w("| Env | Suite | Gemini | Opus | GPT-5.5 | Union | >=10? |")
w("|---|---|--:|--:|--:|--:|:--:|")
for t in tasks:
    gg = len(data[t].get("gemini-3.1-pro", []))
    oo = len(data[t].get("opus-4.8", []))
    pp = len(data[t].get("gpt-5.5", []))
    uu = env_union(t)
    w(f"| {t} | {suite(t)} | {gg} | {oo} | {pp} | {uu} | {'yes' if uu >= 10 else ''} |")
w()
w("## Trajectory paths")
w()
w("Every successful trajectory directory, grouped by environment and model")
w("(paths relative to repo root, under gitignored `outputs/`).")
w()
for t in tasks:
    w(f"### {t} ({suite(t)})")
    for m in MODELS:
        ps = sorted(data[t].get(m, []))
        if not ps:
            continue
        w(f"- **{m}** ({len(ps)}):")
        for p in ps:
            w(f"  - `{p}`")
    w()

out = "docs/libero-trajectory-collection.md"
with open(out, "w") as f:
    f.write("\n".join(L) + "\n")
print(f"wrote {out}: {len(L)} lines | raw={raw} (G{g}+O{o}+GPT{gpt}) envs={len(tasks)} "
      f"union={u} ten={n10} dropped={len(dropped_malformed)}")
