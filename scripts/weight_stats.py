#!/usr/bin/env python3
"""Compare weight distributions of a stock checkpoint vs a merged fine-tune.

Hypothesis under test: our LoRA (scale 2.0, 3 epochs, loss 0.064) pushes merged
weights into heavy tails, and int4 cannot represent them — one outlier can empty
whole quantisation bins. int8 has enough headroom, which is why int8 worked and
int4 collapsed on every base we tried, QAT included.

Reports, per tensor, the ratio of max|w| to the 99.9th percentile. A large ratio
means a few extreme values dominate the range the quantiser must cover.
"""
import sys, glob, json
import numpy as np
from safetensors import safe_open

def stats(d, limit=40):
    files = sorted(glob.glob(f"{d}/*.safetensors"))
    if not files: return None
    out = []
    seen = 0
    for fp in files:
        with safe_open(fp, framework="pt") as f:
            for k in f.keys():
                if "language_model" not in k or not k.endswith(".weight"): continue
                t = f.get_tensor(k).float().abs().numpy().ravel()
                if t.size < 1024: continue
                p999 = np.percentile(t, 99.9)
                out.append((k, float(t.max()), float(p999),
                            float(t.max()/max(p999, 1e-9)), float(t.std())))
                seen += 1
                if seen >= limit: return out
    return out

def summarise(name, rows):
    if not rows: print(f"{name}: no tensors read"); return None
    r = np.array([x[3] for x in rows])
    print(f"\n{name}  ({len(rows)} tensors)")
    print(f"  max|w| / p99.9   mean {r.mean():7.2f}   median {np.median(r):7.2f}   worst {r.max():7.2f}")
    worst = sorted(rows, key=lambda x: -x[3])[:3]
    for k, mx, p, ratio, sd in worst:
        print(f"    {ratio:7.1f}x  max={mx:8.4f} p99.9={p:8.4f}  {k[-58:]}")
    return r.mean()

if __name__ == "__main__":
    a = summarise("STOCK  " + sys.argv[1], stats(sys.argv[1]))
    b = summarise("MERGED " + sys.argv[2], stats(sys.argv[2]))
    if a and b:
        print(f"\nmerged/stock outlier ratio: {b/a:.2f}x")
        print("  >1.5x supports the hypothesis; ~1.0x refutes it and the cause is elsewhere.")
