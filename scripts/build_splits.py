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

verbatim = load("verbatim_pairs.jsonl")
calendar = load("calendar_pairs.jsonl")
prose    = load("prose_pairs.jsonl")

random.shuffle(prose)
n_val = max(20, int(len(prose) * 0.08))
valid, prose_train = prose[:n_val], prose[n_val:]

train = verbatim + calendar + prose_train
random.shuffle(train)

for name, rows in (("train", train), ("valid", valid)):
    (OUT / f"{name}.jsonl").write_text(
        "\n".join(json.dumps({"messages": r["messages"]}, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")

print(f"train {len(train):>5}  (verbatim {len(verbatim)}, calendar {len(calendar)}, prose {len(prose_train)})")
print(f"valid {len(valid):>5}  (prose only — canon is graded by exact match, not loss)")
print(f"wrote {OUT/'train.jsonl'} and {OUT/'valid.jsonl'}")
