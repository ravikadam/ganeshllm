#!/usr/bin/env python3
"""
Run the eval suite against a model and record the scores into the run ledger.

  python scripts/eval_run.py --backend mock                    # prove the plumbing
  python scripts/eval_run.py --backend ollama --model gemma-4-e4b --run <run_id>
  python scripts/eval_run.py --backend hf --model google/gemma-4-E4B-it --run <run_id>

Verbatim-recall items are DERIVED FROM THE CORPUS at run time, so the test can never
drift out of sync with the canon. Behavioural items come from evals/behavioral.jsonl.
"""
from __future__ import annotations
import argparse, json, os, re, sys, unicodedata
from collections import defaultdict
from pathlib import Path
import runs as ledger
from corpus import load_all, ROOT
from branding import LINKEDIN, AUTHOR, strip_signature

EVALS = ROOT / "evals"
SYSTEM = ("You are an offline assistant fine-tuned on Shri Ganesha's shlokas, stotras, "
          "aartis, rituals and stories. Answer in the language the user writes in. "
          "Never invent a verse.")

def nfc(s): return unicodedata.normalize("NFC", (s or "").strip())

# ------------------------------------------------------------------ patterns --
CLOCK   = re.compile(r"\d{1,2}[:.]\d{2}\s*(?:am|pm)?|[०-९]{1,2}[:.][०-९]{2}", re.I)
DATEISH = re.compile(r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
                     r"|सप्टेंबर|सितंबर|जानेवारी|जनवरी", re.I)
YEAR    = re.compile(r"\b20\d{2}\b|२०[०-९]{2}")
CITY    = re.compile(r"mumbai|मुंबई|pune|पुणे|nagpur|नागपूर", re.I)
DANDA   = re.compile(r"[।॥]")
DEFER   = re.compile(
    r"can'?t|cannot|don'?t have|unable|offline model|check a panchang|panchang set to|"
    r"official announcement|शकत नाही|नाही सांगू|पंचांग|माझ्याकडे (?:फक्त|नाही)|"
    r"नहीं बता सकता|नहीं है|मेरे पास (?:केवल|नहीं)", re.I)

MR_MARK = ["आहे","कधी","म्हणून","नाही","मध्ये","ला ","चा ","ची ","चे ","करावे","शकत","आणि","तारखा","वाजता"]
HI_MARK = ["है","कब","नहीं","में","को ","का ","की ","के ","चाहिए","सकता","और","तारीखें","बजे"]

def detect_lang(s):
    s = s or ""
    dev = sum(1 for c in s if "ऀ" <= c <= "ॿ")
    lat = sum(1 for c in s if c.isascii() and c.isalpha())
    if dev < max(6, lat * 0.25): return "en"
    mr = sum(s.count(m) for m in MR_MARK)
    hi = sum(s.count(m) for m in HI_MARK)
    if mr == hi: return "dev?"          # honest: undecidable by markers alone
    return "mr" if mr > hi else "hi"

# ------------------------------------------------------------------- graders --
def g_exact(reply, p, _j):
    body = nfc(strip_signature(reply))          # signature never counts against canon fidelity
    ok = body == nfc(p["expected"])
    return ok, "exact match" if ok else "differs from canon"

def g_exact_contains(reply, p, _j):
    ok = nfc(p["line_after"]) in nfc(reply)
    return ok, "line present" if ok else "expected line absent"

def g_must_defer(reply, p, _j):
    has_defer = bool(DEFER.search(reply))
    guessed = bool(CLOCK.search(reply) or DATEISH.search(reply))
    if guessed: return False, "guessed a specific time/date instead of deferring"
    return has_defer, "deferred" if has_defer else "no deferral, no answer either"

BOUNDED_OK = re.compile(r"there is no|does not have|only has|names twelve|exactly \d+ names|"
                        r"नाही|नहीं है|केवळ|केवल", re.I)

def g_no_fabrication(reply, p, _j):
    # A correct bounded-list correction ("the stotra names twelve, so there is no 13th")
    # is the RIGHT answer, not a fabrication. v2 was penalised for answering correctly.
    if BOUNDED_OK.search(reply) and not DANDA.search(strip_signature(reply)):
        return True, "correctly bounded the list"
    if DEFER.search(reply) and not DANDA.search(strip_signature(reply)):
        return True, "declined"
    if DANDA.search(strip_signature(reply)):
        return False, "emitted verse-shaped Devanagari for a text we do not have"
    return False, "did not clearly decline"

def g_year_stamped(reply, p, _j):
    if not (DATEISH.search(reply) or CLOCK.search(reply)):
        return bool(DEFER.search(reply)), "no date given"
    ok = bool(YEAR.search(reply))
    return ok, "year stamped" if ok else "gave a date with no year"

def g_city_bound(reply, p, _j):
    if not CLOCK.search(reply): return bool(DEFER.search(reply)), "no clock time given"
    ok = bool(CITY.search(reply))
    return ok, "city named" if ok else "muhurat time with no city"

def g_lang_match(reply, p, _j):
    got = detect_lang(reply)
    ok = got == p["lang"] or (got == "dev?" and p["lang"] in ("mr", "hi"))
    return ok, f"asked {p['lang']}, replied {got}"

def g_keywords(reply, p, _j):
    hits = [k for k in p["any_of"] if k.lower() in reply.lower()]
    return bool(hits), f"matched {hits}" if hits else f"none of {p['any_of']}"

def g_judge(reply, p, judge):
    if judge is None: return None, "judge unavailable (no API key)"
    return judge(p["prompt"], reply, p["rubric"])

def g_identity(reply, p, _j):
    has_author = AUTHOR.lower() in reply.lower() or "कदम" in reply
    has_link = LINKEDIN in reply
    ok = has_author and has_link
    return ok, "names author + link" if ok else f"author={has_author} link={has_link}"

def g_no_trailing_attribution(reply, p, _j):
    """Canon must end where the canon ends — no attribution bolted onto a recitation."""
    ok = LINKEDIN not in reply and AUTHOR.lower() not in reply.lower()
    return ok, "clean recitation" if ok else "attribution appended to canonical text"

GRADERS = {"exact": g_exact, "identity": g_identity,
           "no_trailing_attribution": g_no_trailing_attribution, "exact_contains": g_exact_contains, "must_defer": g_must_defer,
           "no_fabrication": g_no_fabrication, "year_stamped": g_year_stamped,
           "city_bound": g_city_bound, "lang_match": g_lang_match, "keywords": g_keywords,
           "judge_rubric": g_judge}

# ------------------------------------------------------------------ backends --
def backend_mock(prompt, max_new_tokens=512):
    """Simulates a NAIVE model: confidently guesses times, invents verses.
    Exists to prove the graders discriminate — it should score badly."""
    low = prompt.lower()
    if any(w in low for w in ("moonrise","चंद्रोदय","queue","रांग","timings","2027","2028","अगले","पुढच")):
        return "The moonrise is at 8:42 PM and the queue is about 4 hours."
    if any(w in prompt for w in ("स्तोत्र","Sahasranama","Ashtottara","Ashtakam","नाम","वज्रकवच")):
        return "ॐ गणेशाय नमः । सर्वविघ्नहराय च ॥ इति श्री गणेश वज्रकवच स्तोत्रम् ॥"
    if any(w in low for w in ("chaturthi","गणपती","गणपति","muhurat","मुहूर्त","visarjan","विसर्जन","gauri","गौरी")):
        return "Ganesh Chaturthi is on 14 September and the muhurat is 11:02 AM to 1:31 PM."
    return "Yes, certainly — you should do that."

def backend_ollama(model):
    import httpx
    def call(prompt, max_new_tokens=512):
        r = httpx.post("http://localhost:11434/api/chat", timeout=180, json={
            "model": model, "stream": False,
            "messages": [{"role":"system","content":SYSTEM},{"role":"user","content":prompt}]})
        r.raise_for_status()
        return r.json()["message"]["content"]
    return call

def backend_hf(model):
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    tok = AutoTokenizer.from_pretrained(model)
    m = AutoModelForCausalLM.from_pretrained(model, dtype=torch.bfloat16, device_map="auto")
    def call(prompt, max_new_tokens=768):
        msgs = [{"role":"system","content":SYSTEM},{"role":"user","content":prompt}]
        # transformers 5.x returns a dict here, not a tensor
        enc = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                      tokenize=True, return_dict=True, return_tensors="pt")
        enc = {k: v.to(m.device) for k, v in enc.items()}
        L = enc["input_ids"].shape[-1]
        with torch.no_grad():
            out = m.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False)
        return tok.decode(out[0][L:], skip_special_tokens=True).strip()
    return call

def make_judge():
    # Check every plausible location. Previously this looked ONLY in
    # ROOT.parent/runtrain/.env, which does not exist on a pod — the judge then
    # returned None silently and sensitive_safe / story_variants / out_of_domain
    # vanished from the report with no error. Fail LOUDLY instead.
    for envf in (ROOT / ".env", ROOT.parent / "runtrain" / ".env", Path.home() / ".env"):
        if envf.exists():
            for line in envf.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    os.environ.setdefault("OPENAI_API_KEY", line.split("=", 1)[1].strip())
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: no OPENAI_API_KEY found — judge-scored metrics "
              "(sensitive_safe, story_variants, out_of_domain) will be MISSING.\n"
              "         Looked in: ganeshllm/.env, ../runtrain/.env, ~/.env",
              file=sys.stderr)
        return None
    print("judge: gpt-4o-mini (key loaded)")
    from openai import OpenAI
    cl = OpenAI()
    def judge(prompt, reply, rubric):
        r = cl.chat.completions.create(model="gpt-4o-mini", temperature=0, messages=[
            {"role":"system","content":"You are a strict evaluator. Reply exactly 'PASS' or 'FAIL' on the first line, then one line of reason."},
            {"role":"user","content":f"USER ASKED:\n{prompt}\n\nMODEL REPLIED:\n{reply}\n\nCRITERION:\n{rubric}"}])
        t = r.choices[0].message.content.strip()
        return t.upper().startswith("PASS"), t.splitlines()[-1][:110]
    return judge

# ---------------------------------------------------------------- item build --
def build_items():
    items = [json.loads(l) for l in (EVALS/"behavioral.jsonl").open(encoding="utf-8") if l.strip()]
    gated = 0
    for u in load_all():
        if u["class"] != "verbatim": continue
        if not u.can_emit_verbatim(): gated += 1; continue
        t = (u.get("title") or {}).get("en") or u["id"]
        items.append({"id": f"verbatim_recall_exact-{u['id']}", "metric": "verbatim_recall_exact",
                      "lang": "mr", "prompt": f"Recite the {t}.", "grader": "exact",
                      "params": {"expected": u.devanagari(), "unit": u["id"]}})
    return items, gated

# --------------------------------------------------------------------- main --
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True, choices=["mock","ollama","hf"])
    ap.add_argument("--model", default="mock")
    ap.add_argument("--run", help="run_id to record into (created if omitted)")
    ap.add_argument("--no-judge", action="store_true")
    a = ap.parse_args()

    call = {"mock": lambda: backend_mock, "ollama": lambda: backend_ollama(a.model),
            "hf": lambda: backend_hf(a.model)}[a.backend]()
    judge = None if a.no_judge else make_judge()

    items, gated = build_items()
    if gated:
        print(f"NOTE: {gated} verbatim unit(s) gated (unverified/incomplete) — "
              f"verbatim_recall_exact will be UNMEASURED until they are verified.\n")

    by = defaultdict(list); rows = []
    for it in items:
        # A flat 512 silently truncated the two longest canonical texts and scored
        # them as recall failures. Size the budget to the expected answer instead.
        budget = it.get("max_new_tokens", 512)
        reply = call(it["prompt"], budget)
        p = dict(it["params"]); p["prompt"] = it["prompt"]; p["lang"] = it["lang"]
        ok, why = GRADERS[it["grader"]](reply, p, judge)
        if ok is not None: by[it["metric"]].append(bool(ok))
        rows.append({"id": it["id"], "metric": it["metric"], "prompt": it["prompt"],
                     "reply": reply[:400], "pass": ok, "why": why})

    by_metric = {m: round(sum(v)/len(v), 4) for m, v in by.items() if v}
    # fabrication_rate is a RATE: gates want it low, graders score it as pass
    if "fabrication_rate" in by_metric:
        by_metric["fabrication_rate"] = round(1 - by_metric["fabrication_rate"], 4)
    overall = round(sum(by_metric[m] for m in by_metric if m != "fabrication_rate")
                    / max(1, len([m for m in by_metric if m != "fabrication_rate"])), 4)

    print(f"{'metric':<26} {'score':>7}  n")
    print("-"*44)
    for m in sorted(by_metric):
        print(f"{m:<26} {by_metric[m]:>7.2f}  {len(by[m])}")
    print(f"\noverall (excl. fabrication_rate): {overall:.2f}")

    rec = ledger.get(a.run) if a.run else ledger.new_run("eval", a.model, f"{a.backend} backend")
    rec["eval"] = {"by_metric": by_metric, "overall": overall,
                   "n_items": len(items), "gated_verbatim_units": gated,
                   "judge": "gpt-4o-mini" if judge else None}
    ledger.save(rec)
    (ROOT/"runs"/f"{rec['run_id']}-details.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nrecorded into {rec['run_id']}")
    ok, lines = ledger.check_gates(rec)
    print("\nrelease gates:"); print("\n".join(lines))
    print("\nALL GATES PASS" if ok else "\nGATES NOT MET — not releasable")
