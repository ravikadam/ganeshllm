#!/usr/bin/env python3
"""
Combine the built pair files into MLX-LM train/valid splits.

Validation holds out PROSE pairs only. Verbatim recall is graded by exact match in the
eval suite, not by held-out loss — holding out canon would just mean training on less of it,
and a low val loss on a shloka tells you nothing that `verbatim_recall_exact` doesn't say better.

  python scripts/build_splits.py
"""
import json, random
from pathlib import Path
from corpus import ROOT

random.seed(1729)
OUT = ROOT / "data"; OUT.mkdir(exist_ok=True)

def load(name):
    p = ROOT / "outputs" / name
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()] if p.exists() else []

# pick up every built pair file so new builders are never silently left out
buckets = {p.stem: load(p.name) for p in sorted((ROOT / "outputs").glob("*.jsonl"))}
prose    = buckets.pop("prose_pairs", [])
other    = [r for name, rows in buckets.items() for r in rows]
verbatim = buckets.get("verbatim_pairs", [])
calendar = buckets.get("calendar_pairs", [])

random.shuffle(prose)
n_val = max(20, int(len(prose) * 0.08))
valid, prose_train = prose[:n_val], prose[n_val:]

train = other + prose_train
random.shuffle(train)

for name, rows in (("train", train), ("valid", valid)):
    (OUT / f"{name}.jsonl").write_text(
        "\n".join(json.dumps({"messages": r["messages"]}, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")

print(f"train {len(train):>5}")
for k, v in sorted(buckets.items()): print(f"    {k:<22}{len(v):>6}")
print(f"    {'prose_pairs (train part)':<22}{len(prose_train):>6}")
print(f"valid {len(valid):>5}  (prose only — canon is graded by exact match, not loss)")
print(f"wrote {OUT/'train.jsonl'} and {OUT/'valid.jsonl'}")
