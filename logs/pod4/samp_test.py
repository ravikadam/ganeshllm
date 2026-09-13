#!/usr/bin/env python3
"""Recite under the model's baked defaults AND Edge Gallery-like sampling.
usage: samp_test.py model.litertlm"""
import sys, json, re
import litert_lm as L

VAK = "वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ ।\nनिर्विघ्नं कुरु मे देव सर्वकार्येषु सर्वदा ॥"
SUK = "सुखकर्ता दुखहर्ता, वार्ता विघ्नांची ।"
PROMPTS = [("वक्रतुंड महाकाय श्लोक सांग.", VAK), ("Recite the Vakratunda Mahakaya.", VAK),
           ("सुखकर्ता दुखहर्ता आरती म्हण.", SUK), ("गणपतीची मूर्ती का विसर्जित करतात?", None)]
SAMPLERS = [("file-default", None),
            ("gallery-like t1.0 k40 s1", L.SamplerConfig(top_k=40, top_p=0.95, temperature=1.0, seed=1)),
            ("gallery-like t1.0 k40 s2", L.SamplerConfig(top_k=40, top_p=0.95, temperature=1.0, seed=2))]

def text(r):
    c = r.get("content", r) if isinstance(r, dict) else r
    if isinstance(c, list): return "".join(x.get("text", "") for x in c if isinstance(x, dict))
    return str(c)

eng = L.Engine(sys.argv[1])
bad = 0
for name, sc in SAMPLERS:
    for p, ref in PROMPTS:
        with eng.create_conversation(sampler_config=sc) as conv:
            out = text(conv.send_message(p, max_output_tokens=700))
        norm = lambda s: re.sub(r"[\s'\"]", "", s)
        ok = "-"
        if ref == VAK:
            o = norm(out); ok = "EXACT" if o == norm(VAK) else ("PREFIX+JUNK" if o.startswith(norm(VAK)) else "WRONG")
        elif ref == SUK:
            ok = "OPENS-OK" if norm(SUK) in norm(out) else "WRONG"
        bad += ok in ("WRONG", "PREFIX+JUNK")
        print(f"### [{name}] {p} -> {ok} ({len(out)} chars)\n{out[:900]!r}\n", flush=True)
print("BAD", bad)
