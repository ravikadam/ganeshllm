#!/usr/bin/env python3
"""
Audit the built training set for the failure modes we have actually hit.

Every check here exists because something went wrong once:
  - contradiction: limitations.yaml once said "never state dates" while the calendar
    unit stated them. Contradictory training data -> inconsistent model.
  - ratio: v2 regressed on deferral because 405 confident-date pairs swamped 45
    other-year refusals. Ratio, not presence, is what decides which behaviour wins.
  - leakage: a valid example that also appears in train tells you nothing.
  - date leaks in prose: gen_prose once invented "Anant Chaturdashi 27 September".

  python scripts/audit_dataset.py
"""
from __future__ import annotations
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
from corpus import ROOT

def load(p): return [json.loads(l) for l in Path(p).open(encoding="utf-8") if l.strip()]
def user(r):  return next(m["content"] for m in r["messages"] if m["role"] == "user")
def asst(r):  return " ".join(m["content"] for m in r["messages"] if m["role"] == "assistant")

DATEISH = re.compile(r"\b\d{1,2}\s*(?:sep|september)|सप्टेंबर|सितंबर", re.I)
YEAR    = re.compile(r"\b20\d{2}\b|२०[०-९]{2}")
DEFER   = re.compile(r"can'?t|cannot|don'?t have|offline|panchang|शकत नाही|पंचांग|नहीं बता", re.I)
OTHERYR = re.compile(r"20(2[789]|3\d)|२०२[७८९]")

def main():
    train = load(ROOT / "data/train.jsonl")
    valid = load(ROOT / "data/valid.jsonl")
    issues, notes = [], []

    # 1 leakage
    tq = {user(r).strip().lower() for r in train}
    leaked = [r for r in valid if user(r).strip().lower() in tq]
    (issues if leaked else notes).append(f"valid/train overlap: {len(leaked)}/{len(valid)}")

    # 2 exact duplicate pairs
    seen = Counter((user(r).strip(), asst(r).strip()) for r in train)
    dupes = sum(v - 1 for v in seen.values() if v > 1)
    notes.append(f"duplicate (q,a) pairs: {dupes} ({dupes/len(train)*100:.0f}% of train) "
                 f"— intentional for canon drilling")

    # 3 contradiction: same question, different answers
    byq = defaultdict(set)
    for r in train: byq[user(r).strip()].add(asst(r).strip())
    conflict = {q: v for q, v in byq.items() if len(v) > 1}
    if conflict:
        issues.append(f"CONTRADICTIONS: {len(conflict)} questions have >1 distinct answer")
        for q in list(conflict)[:3]:
            issues.append(f"    {q[:60]!r} -> {len(conflict[q])} different answers")

    # 4 THE v2 REGRESSION: confident dates vs other-year refusals
    conf = [r for r in train if DATEISH.search(asst(r)) and not DEFER.search(asst(r))]
    refu = [r for r in train if OTHERYR.search(user(r)) and DEFER.search(asst(r))]
    ratio = len(conf) / max(1, len(refu))
    line = (f"confident-date pairs {len(conf)} vs other-year refusals {len(refu)} "
            f"= {ratio:.0f}:1")
    (issues if ratio > 4 else notes).append(
        line + ("  <-- caused the v2 deferral regression" if ratio > 4 else ""))

    # 5 unstamped dates
    unstamped = [r for r in train if DATEISH.search(asst(r)) and not YEAR.search(asst(r))
                 and not DEFER.search(asst(r))]
    (issues if unstamped else notes).append(f"dated answers missing a year stamp: {len(unstamped)}")

    # 6 locality invention (the BMC tank failure)
    loc = re.compile(r"तलाव|talav|tank", re.I)
    loc_conf = [r for r in train if loc.search(user(r)) and not DEFER.search(asst(r))]
    loc_ref  = [r for r in train if loc.search(user(r)) and DEFER.search(asst(r))]
    (issues if len(loc_ref) < 20 else notes).append(
        f"locality (tank/talav) pairs: {len(loc_ref)} refusals vs {len(loc_conf)} confident")

    # 7 language balance
    def lang(s):
        d = sum(1 for c in s if "ऀ" <= c <= "ॿ")
        return "devanagari" if d > len(s) * 0.3 else "latin"
    notes.append("question script mix: " + str(dict(Counter(lang(user(r)) for r in train))))

    print(f"train {len(train)}  valid {len(valid)}\n")
    print("ISSUES")
    print("\n".join("  ! " + i for i in issues) if issues else "  (none)")
    print("\nNOTES")
    print("\n".join("  - " + n for n in notes))
    return 1 if issues else 0

if __name__ == "__main__":
    sys.exit(main())
