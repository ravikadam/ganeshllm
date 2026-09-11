#!/usr/bin/env python3
"""Judge a LiteRT generation sample. Presence of the canon is NOT enough.

The int4 build emitted the correct opening 'सुखकर्ता दुखहर्ता' and then collapsed
into a loop with Burmese characters spliced in. A gate that greps for the canon
would have called that a PASS and published it. Check for collapse too.
"""
import re, sys, unicodedata
from collections import Counter

CANON = re.compile(r"सुखकर्ता\s*दुखहर्ता|वक्रतुंड\s*महाकाय|गजाननं\s*भूतगणादि")

def blocks(t):
    """Which writing systems appear, ignoring Latin/common/punctuation."""
    c = Counter()
    for ch in t:
        if ch.isspace() or not ch.isalpha(): continue
        try: name = unicodedata.name(ch).split()[0]
        except ValueError: continue
        c[name] += 1
    return c

def repetition(t, n=24, k=4):
    """Longest n-gram repeated k+ times -> runaway loop."""
    s = re.sub(r"\s+", " ", t)
    if len(s) < n * 2: return 0
    c = Counter(s[i:i+n] for i in range(len(s)-n))
    return c.most_common(1)[0][1] if c else 0

def check(text, want_canon=True):
    fails = []
    if want_canon and not CANON.search(text):
        fails.append("canon absent")
    rep = repetition(text)
    if rep >= 4:
        fails.append(f"degenerate loop: a 24-char span repeats {rep}x")
    b = blocks(text)
    stray = {k: v for k, v in b.items()
             if k not in ("DEVANAGARI", "LATIN") and v >= 3}
    if stray:
        fails.append(f"foreign scripts spliced in: {stray}")
    if len(text.strip()) < 40:
        fails.append("output too short")
    return fails

if __name__ == "__main__":
    t = open(sys.argv[1], encoding="utf-8").read()
    want = "--no-canon" not in sys.argv
    f = check(t, want)
    print("FAIL: " + "; ".join(f) if f else "PASS: coherent and on-canon")
    sys.exit(1 if f else 0)
