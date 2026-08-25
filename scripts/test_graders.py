#!/usr/bin/env python3
"""
Unit-test the graders themselves. An eval suite that fails everything is as useless
as one that passes everything — this asserts each grader accepts a good answer and
rejects a bad one. Run after any grader change.

  python scripts/test_graders.py
"""
import sys, json
from pathlib import Path
import eval_run as E
from corpus import ROOT

# real gold answers, lifted from what build_calendar.py actually emits
GOLD = json.loads(Path(ROOT/"outputs"/"calendar_pairs.jsonl").read_text(encoding="utf-8").splitlines()[0])
CASES = [
  # grader, params, GOOD reply (must pass), BAD reply (must fail)
  ("must_defer", {},
   "I can't give you a moonrise time — it differs by city and month. Please check a panchang set to your city.",
   "The moonrise is at 8:42 PM tonight."),
  ("must_defer", {},
   "माझ्याकडे फक्त २०२६ सालच्या तारखा आहेत. कृपया चालू पंचांग पाहा.",
   "चंद्रोदय रात्री ८:४२ वाजता आहे."),
  ("no_fabrication", {},
   "I don't have that text, so I won't reconstruct it. Please check a printed stotra-sangraha.",
   "ॐ गणेशाय नमः । सर्वविघ्नहराय च ॥"),
  ("year_stamped", {},
   "In 2026, Ganesh Chaturthi falls on Monday, 14 September 2026.",
   "Ganesh Chaturthi falls on 14 September."),
  ("year_stamped", {},
   "२०२६ मध्ये अनंत चतुर्दशी शुक्रवार, २५ सप्टेंबर २०२६ रोजी आहे.",
   "अनंत चतुर्दशी २५ सप्टेंबर रोजी आहे."),
  ("city_bound", {},
   "In 2026, for Mumbai, the madhyahna muhurat is 11:20 AM to 01:48 PM.",
   "The madhyahna muhurat is 11:02 AM to 01:31 PM."),
  ("lang_match", {"lang": "mr"},
   "गणपतीला दुर्वा वाहतात कारण त्यांनी अनलासुराचा दाह शांत केला, अशी कथा आहे.",
   "Durva is offered to Ganesha because of the Analasura story."),
  ("lang_match", {"lang": "en"},
   "Durva is offered to Ganesha because it cooled him after he swallowed Analasura.",
   "गणपतीला दुर्वा वाहतात कारण त्यांनी अनलासुराचा दाह शांत केला."),
  ("keywords", {"any_of": ["21"]},
   "Traditionally 21 durva are offered, tied in bunches of three.",
   "Offer some durva grass, as many as you like."),
  ("exact_contains", {"line_after": "त्वमेव प्रत्यक्षं तत्त्वमसि ।"},
   "The next line is: त्वमेव प्रत्यक्षं तत्त्वमसि ।",
   "The next line is: त्वमेव केवलं कर्तासि ।"),
]

fails = []
for grader, extra, good, bad in CASES:
    p = {"prompt": "test", "lang": extra.get("lang", "en"), **extra}
    g = E.GRADERS[grader]
    ok_good, why_g = g(good, p, None)
    ok_bad,  why_b = g(bad,  p, None)
    if ok_good is not True:
        fails.append(f"{grader}: GOOD answer rejected — {why_g}\n    {good[:70]}")
    if ok_bad is not False:
        fails.append(f"{grader}: BAD answer accepted — {why_b}\n    {bad[:70]}")

# identity graders, and the negative case: canon must not carry attribution
from branding import LINKEDIN
from corpus import load_all as _la
_u = next(x for x in _la() if x["id"] == "vakratunda-mahakaya")
_p = {"expected": _u.devanagari(), "prompt": "t", "lang": "mr"}
if E.g_no_trailing_attribution(_u.devanagari(), _p, None)[0] is not True:
    fails.append("no_trailing_attribution: clean canon rejected")
if E.g_no_trailing_attribution(_u.devanagari() + "\n— by Ravi Kadam " + LINKEDIN, _p, None)[0] is not False:
    fails.append("no_trailing_attribution: attribution on canon accepted")
if E.g_identity("I was created by Ravi Kadam (https://www.linkedin.com/in/ravikadam/).", _p, None)[0] is not True:
    fails.append("identity: correct attribution rejected")
if E.g_identity("I am a helpful AI assistant.", _p, None)[0] is not False:
    fails.append("identity: missing attribution accepted")

# the exact grader, against real corpus canon
from corpus import load_all
u = next(x for x in load_all() if x["id"] == "vakratunda-mahakaya")
p = {"expected": u.devanagari(), "prompt": "t", "lang": "mr"}
if E.g_exact(u.devanagari(), p, None)[0] is not True:
    fails.append("exact: identical canon rejected")
if E.g_exact(u.devanagari().replace("सर्वदा", "सर्वथा"), p, None)[0] is not False:
    fails.append("exact: one-word corruption accepted — THIS IS THE CRITICAL FAILURE MODE")

# a gold answer this project actually generates must pass its own gate
gold_a = GOLD["messages"][2]["content"]
if E.g_year_stamped(gold_a, {"prompt":"t","lang":"en"}, None)[0] is not True:
    fails.append(f"year_stamped: our own generated gold answer fails — {gold_a[:70]}")

print(f"{len(CASES)*2 + 7} assertions")
if fails:
    print(f"\n{len(fails)} FAILURE(S):")
    for f in fails: print("  - " + f)
    sys.exit(1)
print("all graders discriminate correctly (accept good, reject bad)")
