#!/usr/bin/env python3
"""
Expand `class: prose` corpus units into instruction pairs via an API model.

Grounding discipline: the model is given ONLY the unit's facts/steps/variants/sensitivities
and told it may use nothing else. Every generated answer is then checked against the unit's
`must_contain` before it is kept. Prose is generated; canon is never generated (see
build_verbatim.py).

  python scripts/gen_prose.py --per-unit 40
  python scripts/gen_prose.py --per-unit 4 --limit 2      # cheap smoke test
"""
from __future__ import annotations
import argparse, asyncio, json, os, random, sys
from pathlib import Path
from corpus import load_all, ROOT, LANG_MIX
from branding import IDENTITY
import re

OUT = ROOT / "outputs" / "prose_pairs.jsonl"

# Prose units cover rituals, stories and how-to. They must NEVER state a date or a clock
# time — those come only from build_calendar.py, which splices verified constants. A date
# appearing in generated prose is unverifiable by construction, so it is dropped.
# (This rule was added after the generator confidently produced "Anant Chaturdashi is
# 27 September 2026", which is wrong — the verified date is 25 September.)
# Questions about WHEN something falls belong to build_calendar.py alone. Letting the
# prose generator answer them produced a direct contradiction: the calendar builder taught
# "In 2026, Ganesh Chaturthi falls on Monday 14 September" while prose taught "it depends
# on the panchang" for the same question.
DATE_Q = re.compile(r"\bwhen is\b|\bwhat date\b|\bwhich day\b|कधी आहे|कधी येते|कधी बसणार|"
                    r"कब है|कब आ|किस तारीख|तारीख|तारखा|मुहूर्त|muhurat|what time", re.I)
DATE_LEAK = re.compile(
    r"\d{1,2}\s*(?:st|nd|rd|th)?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}"
    r"|\d{1,2}\s*(?:सप्टेंबर|सितंबर|ऑगस्ट|अगस्त|सप्टें)"
    r"|(?:सप्टेंबर|सितंबर)\s*\d{1,2}"
    r"|[०-९]{1,2}\s*(?:सप्टेंबर|सितंबर)"
    r"|\d{1,2}[:.]\d{2}", re.I)
SYSTEM = ("You are an offline assistant fine-tuned on Shri Ganesha's shlokas, stotras, "
          "aartis, rituals and stories. Answer in the language the user writes in. "
          "Never invent a verse.")
LANGNAME = {"mr": "Marathi", "hi": "Hindi", "en": "English", "sa": "Sanskrit"}
DROPPED = []

def load_key():
    for envf in (ROOT / ".env", ROOT.parent / "runtrain" / ".env"):
        if envf.exists():
            for line in envf.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("No OPENAI_API_KEY (looked in ganeshllm/.env and runtrain/.env)")

def ground(u) -> str:
    b = [f"TITLE: {(u.get('title') or {}).get('en', u['id'])}"]
    if u.get("facts"):   b.append("FACTS:\n" + "\n".join(f"- {f}" for f in u["facts"]))
    if u.get("steps"):
        b.append("STEPS:\n" + "\n".join(
            f"- {s.get('name_en','')} ({s.get('name_mr','')}): {s.get('detail_en','')}"
            for s in u["steps"]))
    if u.get("variants"): b.append("VARIANTS (must be acknowledged, never flattened):\n"
                                   + "\n".join(f"- {v}" for v in u["variants"]))
    if u.get("sensitivities"): b.append("SENSITIVITIES (must be honoured):\n"
                                        + "\n".join(f"- {s}" for s in u["sensitivities"]))
    return "\n\n".join(b)

MODES = [
 "a direct factual question a first-time householder would ask",
 "a practical 'how do I ...' question",
 "a worried question from someone who thinks they have done something wrong",
 "a question about what varies between families",
 "a short follow-up exchange: question, answer, then one natural follow-up (4 messages)",
 "a question from someone in a small city flat with little space or few materials",
]

PROMPT = """You are generating training data for a small offline assistant about Shri Ganesha.

Below is the ONLY source material you may use. Do not add facts from your own knowledge.
If the material does not cover something, do not invent it.

{ground}

Write {n} DISTINCT question-answer pairs in {lang}, in the style of: {mode}

Rules:
- Answers must be warm, plain, and short (2-5 sentences unless steps are needed).
- Where the material lists VARIANTS, the answer must acknowledge that practice varies.
- Where the material lists SENSITIVITIES, the answer must honour them exactly.
- Never predict misfortune. Never give one family's practice as the only correct one.
- Never invent or quote a Sanskrit verse.
- NEVER state a calendar date or a clock time. If the question asks when something falls,
  say it depends on the panchang for that year and do not name a date.
- Do NOT append any signature or attribution to the answer.
- Questions must be phrased the way a real person types, not like a textbook heading.

Return STRICT JSON: {{"pairs":[{{"q":"...","a":"..."}}]}}
For multi-turn mode use {{"turns":[{{"role":"user","content":"..."}},{{"role":"assistant","content":"..."}},...]}} inside the list instead."""

async def gen_one(cl, u, lang, mode, n, model):
    try:
        r = await cl.chat.completions.create(
            model=model, temperature=0.9, response_format={"type": "json_object"},
            messages=[{"role": "user", "content": PROMPT.format(
                ground=ground(u), n=n, lang=LANGNAME[lang], mode=mode)}])
        data = json.loads(r.choices[0].message.content)
    except Exception as e:
        print(f"  ! {u['id']}/{lang}: {str(e)[:70]}"); return []

    out, must = [], [m for m in (u.get("must_contain") or [])]
    for item in data.get("pairs", []):
        if "turns" in item:
            msgs = [{"role": "system", "content": SYSTEM}] + item["turns"]
        elif item.get("q") and item.get("a"):
            msgs = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": item["q"]},
                    {"role": "assistant", "content": item["a"]}]
        else:
            continue
        blob = " ".join(m["content"] for m in msgs if m["role"] == "assistant")
        if must and not any(t in blob for t in must):
            continue                      # failed the grounding check — drop it
        if DATE_LEAK.search(blob):
            DROPPED.append((u["id"], "date in answer: " + blob[:60]))
            continue                      # a date in generated prose is unverifiable — drop
        qblob = " ".join(m["content"] for m in msgs if m["role"] == "user")
        if DATE_Q.search(qblob):
            DROPPED.append((u["id"], "date question: " + qblob[:60]))
            continue                      # build_calendar.py owns date questions entirely
        out.append({"messages": msgs, "_unit": u["id"], "_lang": lang})
    return out

async def main(a):
    load_key()
    from openai import AsyncOpenAI
    cl = AsyncOpenAI()
    units = [u for u in load_all() if u["class"] == "prose" and u.get("kind") != "calendar"]
    if a.limit: units = units[:a.limit]

    tasks = []
    for u in units:
        for lang, share in LANG_MIX.items():
            if lang == "sa": continue                 # prose is not generated in Sanskrit
            n_lang = max(1, round(a.per_unit * share / 0.9))
            for mode in random.sample(MODES, k=min(3, len(MODES))):
                tasks.append(gen_one(cl, u, lang, mode, max(1, n_lang // 3), a.model))

    print(f"{len(units)} prose units x {len(LANG_MIX)-1} languages -> {len(tasks)} requests")
    res = await asyncio.gather(*tasks)
    pairs = [p for r in res for p in r]

    seen, uniq = set(), []
    for p in pairs:
        q = next(m["content"] for m in p["messages"] if m["role"] == "user").strip().lower()
        if q in seen: continue
        seen.add(q); uniq.append(p)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(json.dumps({"messages": p["messages"]}, ensure_ascii=False)
                             for p in uniq) + "\n", encoding="utf-8")
    from collections import Counter
    print(f"\ngenerated {len(pairs)} -> {len(uniq)} unique")
    if DROPPED:
        print(f"  dropped {len(DROPPED)} for leaking an unverifiable date/time, e.g.:")
        for uid, snip in DROPPED[:3]:
            print(f"    [{uid}] {snip}...")
    print("  by lang:", dict(Counter(p['_lang'] for p in uniq)))
    print(f"wrote {OUT.relative_to(ROOT)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-unit", type=int, default=40)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="gpt-4o-mini")
    asyncio.run(main(ap.parse_args()))
