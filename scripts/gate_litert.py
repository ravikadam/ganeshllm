#!/usr/bin/env python3
"""PASS/FAIL gate for a .litertlm run log.

Three gates have now been wrong in three different directions:
  1. [ऀ-ॿ]{12,}   demanded 12 CONSECUTIVE Devanagari chars. Devanagari is
                  written with spaces, so it failed on the real aarti too —
                  it would have WITHHELD a working model.
  2. canon prefix  matched 'सुखकर्ता दुखहर्ता' anywhere. A broken export that
                  emits the first two words and then loops passed it — it
                  would have PUSHED a broken model.
  3. this one      requires the canon to CONTINUE correctly, and rejects
                  degenerate repetition.

Run: gate_litert.py <logfile>   -> exits 0 on PASS, 1 on FAIL.
"""
import re, sys

# Enough of each text that a model must actually know it, not just start it.
CANON = [
    r'सुखकर्ता\s*दुखहर्ता\s*वार्ता\s*विघ्नाची',
    r'वक्रतुंड\s*महाकाय\s*सूर्यकोटि\s*समप्रभ',
    r'गजाननं\s*भूतगणादि\s*सेवितं',
]

def degenerate(text, n_sizes=(3, 4, 5), limit=5):
    """A phrase repeated `limit`+ times is a decode loop, not a recitation."""
    w = text.split()
    for n in n_sizes:
        grams = [" ".join(w[i:i+n]) for i in range(max(0, len(w) - n))]
        if not grams:
            continue
        counts = {}
        for g in grams:
            counts[g] = counts.get(g, 0) + 1
        top, c = max(counts.items(), key=lambda kv: kv[1])
        if c >= limit:
            return f"{n}-gram repeated {c}x: {top[:50]!r}"
    return None

def check(text):
    hit = next((p for p in CANON if re.search(p, text)), None)
    if not hit:
        return False, "no canonical text recited (or it stops after the opening words)"
    loop = degenerate(text)
    if loop:
        return False, f"canon found but output is degenerate — {loop}"
    return True, "canon recited and continues; no repetition loop"

if __name__ == "__main__":
    t = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    ok, why = check(t)
    print(("PASS — " if ok else "FAIL — ") + why)
    sys.exit(0 if ok else 1)
