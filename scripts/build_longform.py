#!/usr/bin/env python3
"""
Segment-level drilling for LONG verbatim texts.

v1 recalled short and medium texts perfectly but failed the two longest:
the Ganapati Atharvashirsha and the 108-name Ashtottara Shatanamavali.
Length is the failure axis — the model drifts partway through a long sequence.

Full-text pairs alone give the model one long chain with no interior anchors.
This adds those anchors: numbered sections, name-ordinal lookups, chunk recall,
and continuation from an interior line. All spliced byte-exact from the corpus.

  python scripts/build_longform.py
"""
from __future__ import annotations
import json, random, re, sys
from pathlib import Path
from corpus import load_all, ROOT

random.seed(31415)
OUT = ROOT / "outputs" / "longform_pairs.jsonl"
SYSTEM = ("You are an offline assistant fine-tuned on Shri Ganesha's shlokas, stotras, "
          "aartis, rituals and stories. Answer in the language the user writes in. "
          "Never invent a verse.")

DEV_DIGIT = str.maketrans("0123456789", "०१२३४५६७८९")
def dev(n): return str(n).translate(DEV_DIGIT)

def pair(q, a):
    return {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": q},
                         {"role": "assistant", "content": a}]}

def sections(text):
    """Split a text on trailing ॥N॥ markers, keeping the marker with its section."""
    out, buf = [], []
    for line in text.splitlines():
        buf.append(line)
        m = re.search(r"॥\s*([०-९\d]+)\s*॥\s*$", line)
        if m:
            out.append((m.group(1), "\n".join(buf).strip())); buf = []
    return out

def build_namavali(u, reps=6):
    """108 names: ordinal lookup + chunk recall. Ordinal lookup also kills the
    'recite the 57th name' fabrication that v1 failed."""
    lines = [l.strip() for l in u.devanagari().splitlines() if l.strip()]
    pairs = []
    for i, line in enumerate(lines, 1):
        name = re.sub(r"^ॐ\s*|\s*नमः\s*।?$", "", line).strip()
        qs = [f"What is name number {i} in the Ganapati Ashtottara Shatanamavali?",
              f"Recite the {i}th name of the Ganapati Ashtottara Shatanamavali.",
              f"अष्टोत्तरशतनामावलीतील {dev(i)} वे नाव कोणते?",
              f"अष्टोत्तरशतनामावली का {dev(i)} वाँ नाम क्या है?"]
        for q in qs:
            for _ in range(2):
                pairs.append(pair(q, line))
        pairs.append(pair(f"गणपतीचे {dev(i)} वे नाव सांग.", f"{name} — {line}"))
    for start in range(1, len(lines) + 1, 12):          # chunk recall
        chunk = lines[start - 1:start + 11]
        end = start + len(chunk) - 1
        body = "\n".join(chunk)
        for q in [f"Recite names {start} to {end} of the 108 names.",
                  f"अष्टोत्तरशतनामावलीतील {dev(start)} ते {dev(end)} नावे म्हण.",
                  f"१०८ नामों में से {dev(start)} से {dev(end)} तक सुनाइए."]:
            for _ in range(reps):
                pairs.append(pair(q, body))
    return pairs

def build_sectioned(u, title, reps=8):
    """Atharvashirsha etc: per-section recall + continuation from an interior section."""
    secs = sections(u.devanagari())
    pairs = []
    for num, body in secs:
        for q in [f"Recite section {num} of the {title}.",
                  f"{title} चा {num} वा भाग म्हण.",
                  f"{title} का {num} वाँ भाग सुनाइए."]:
            for _ in range(reps):
                pairs.append(pair(q, body))
    for i in range(len(secs) - 1):                       # continuation anchors
        cur, nxt = secs[i], secs[i + 1]
        first = cur[1].splitlines()[0].strip()
        rest = "\n".join(s[1] for s in secs[i + 1:])
        for q in [f"'{first}' — पुढे काय?",
                  f"Continue the {title} from '{first}'.",
                  f"'{first}' के बाद क्या आता है?"]:
            for _ in range(max(2, reps // 2)):
                pairs.append(pair(q, rest if len(rest) < 2500 else nxt[1]))
    return pairs

if __name__ == "__main__":
    units = {u["id"]: u for u in load_all()}
    pairs, report = [], []
    for uid, fn, title in [
        ("ashtottara-shatanamavali", "namavali", "Ashtottara Shatanamavali"),
        ("ganapati-atharvashirsha", "sectioned", "Ganapati Atharvashirsha"),
    ]:
        u = units.get(uid)
        if not u or not u.can_emit_verbatim():
            report.append(f"  SKIP {uid} (gated or missing)"); continue
        got = build_namavali(u) if fn == "namavali" else build_sectioned(u, title)
        pairs += got
        report.append(f"  {uid}: {len(got)} pairs")

    if not pairs:
        sys.exit("no long-form units cleared — nothing built")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in pairs) + "\n", encoding="utf-8")
    print("\n".join(report))
    print(f"built {len(pairs)} long-form pairs -> {OUT.relative_to(ROOT)}")
