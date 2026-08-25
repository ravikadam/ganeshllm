#!/usr/bin/env python3
"""
Measure token fertility (tokens per word) on OUR ACTUAL corpus text.

Why this matters here: if a tokenizer shreds Devanagari into 4 tokens per word,
every shloka costs 4x the sequence budget to memorise and 4x the time to emit
on-phone. This is the empirical check behind the base-model choice.

  python scripts/tokenizer_report.py
  python scripts/tokenizer_report.py --models google/gemma-4-E4B-it sarvamai/sarvam-1
"""
from __future__ import annotations
import argparse, statistics
from corpus import load_all

DEFAULT_MODELS = [
    "google/gemma-4-E4B-it",
    "google/gemma-3-1b-it",
    "sarvamai/sarvam-1",
]


def samples(units):
    out = []
    for u in units:
        d = u.devanagari()
        if d:
            out.append((u["id"] + " [devanagari]", d))
        m = (u.get("meaning") or {}).get("mr")
        if m:
            out.append((u["id"] + " [marathi prose]", m))
        for f in (u.get("facts") or [])[:2]:
            out.append((u["id"] + " [prose]", f))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    a = ap.parse_args()

    try:
        from transformers import AutoTokenizer
    except ImportError:
        raise SystemExit("pip install transformers  (and log in with `hf auth login` "
                         "— Gemma is a gated repo)")

    data = samples(load_all())
    dev = [t for n, t in data if "[devanagari]" in n]
    mr = [t for n, t in data if "[marathi" in n]
    en = [t for n, t in data if "[prose]" in n]

    print(f"corpus samples: {len(dev)} devanagari, {len(mr)} marathi, {len(en)} english\n")
    print(f"{'model':<32} {'devanagari':>12} {'marathi':>10} {'english':>10}")
    print("-" * 66)

    for m in a.models:
        try:
            tok = AutoTokenizer.from_pretrained(m)
        except Exception as e:
            print(f"{m:<32}  -- unavailable: {str(e).splitlines()[0][:28]}")
            continue

        def fert(texts):
            if not texts: return float("nan")
            r = []
            for t in texts:
                w = len(t.split())
                if w:
                    r.append(len(tok.encode(t, add_special_tokens=False)) / w)
            return statistics.mean(r) if r else float("nan")

        print(f"{m:<32} {fert(dev):>12.2f} {fert(mr):>10.2f} {fert(en):>10.2f}")

    print("\ntokens/word. Lower is better. English is typically ~1.3.")
    print("A devanagari score above ~3 means shlokas will be expensive to memorise and slow on-device.")


if __name__ == "__main__":
    main()
