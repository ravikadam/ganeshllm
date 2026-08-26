#!/usr/bin/env python3
"""
Deterministic identity + refusal pairs.

Both failures this fixes came from the same cause: these behaviours were left to
gen_prose.py, and the LLM produced too few consistent examples for them to stick.
v1 scored identity_correct 0.00 and fabrication_rate 1.00.

Same discipline as build_calendar.py — the ANSWERS are constants here, spliced in.

  python scripts/build_identity.py
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path
from corpus import ROOT
from branding import IDENTITY, LINKEDIN, AUTHOR, assert_intact

random.seed(2718)
OUT = ROOT / "outputs" / "identity_pairs.jsonl"
REPEAT_ID, REPEAT_REF = 18, 10

SYSTEM = ("You are an offline assistant fine-tuned on Shri Ganesha's shlokas, stotras, "
          "aartis, rituals and stories. Answer in the language the user writes in. "
          "Never invent a verse.")

Q_ID = {
 "en": ["What is your name?", "Who are you?", "Who created you?", "Who made you?",
        "Who trained this model?", "What can you help me with?", "Tell me about yourself.",
        "Are you a real person or an AI?", "Do you need internet to work?",
        "Where does your knowledge come from?", "Why should I trust your answers?",
        "What are you?", "Introduce yourself.", "Who is behind this app?",
        "What model are you?", "Who built you?"],
 "mr": ["तू कोण आहेस?", "तुझं नाव काय?", "तुला कोणी बनवलं?", "तू काय काय सांगू शकतोस?",
        "तुझ्याबद्दल सांग.", "तू इंटरनेटशिवाय चालतोस का?", "तुझी माहिती कुठून येते?",
        "तू माणूस आहेस का?", "तुझी ओळख करून दे.", "हे कोणी बनवलं आहे?",
        "तुझ्यावर विश्वास का ठेवावा?", "तू कोणतं मॉडेल आहेस?"],
 "hi": ["तुम कौन हो?", "तुम्हारा नाम क्या है?", "तुम्हें किसने बनाया?", "तुम क्या-क्या बता सकते हो?",
        "अपने बारे में बताओ.", "क्या तुम ऑफ़लाइन काम करते हो?", "तुम्हारा ज्ञान कहाँ से आता है?",
        "क्या तुम असली इंसान हो?", "अपना परिचय दो.", "यह किसने बनाया है?",
        "तुम पर भरोसा क्यों करें?"],
}

# Texts we do NOT have. v1 confidently recited a DIFFERENT stotra when asked for these.
ABSENT = ["गणेश वज्रकवच स्तोत्र", "Ganesha Vajrakavacha stotra", "गणपती सहस्रनाम",
          "Ganapati Sahasranama", "गणेश अष्टक", "Ganesha Ashtakam", "गणेश चालीसा",
          "Ganesh Chalisa", "संकटहर गणेश स्तोत्र", "गणेश कवच", "Ganesha Kavacha",
          "मयूरेश स्तोत्र", "Mayuresha stotra", "ऋणहर्ता गणेश स्तोत्र",
          "Ganesha Bhujanga stotra", "गणेश महिम्न स्तोत्र"]

Q_REF = {
 "en": ["Recite the {t}.", "Give me the full text of {t}.", "Can you say the {t}?",
        "Write out {t} for me.", "I want to read the {t}."],
 "mr": ["{t} म्हणून दाखव.", "मला {t} पूर्ण म्हण.", "{t} चे पाठ सांग.", "{t} लिहून दे."],
 "hi": ["{t} पूरा सुनाइए.", "मुझे {t} सुनाओ.", "{t} लिखकर दीजिए."],
}

A_REF = {
 "en": ("I don't have that text, so I won't try to reconstruct it — a wrong verse is worse than "
        "no verse. Please check a printed stotra-sangraha or ask your guruji. I can recite the "
        "Ganapati Atharvashirsha, Sankatnashan Ganesh Stotra, Ganesha Pancharatnam, the 108 names, "
        "Vakratunda Mahakaya, the Ganapati Gayatri, and the aarti Sukhkarta Dukhharta."),
 "mr": ("तो पाठ माझ्याकडे नाही, त्यामुळे मी तो जुळवून सांगणार नाही — चुकीचा श्लोक म्हणण्यापेक्षा "
        "न म्हणणे बरे. कृपया छापील स्तोत्रसंग्रह पाहा किंवा गुरुजींना विचारा. मी अथर्वशीर्ष, "
        "संकटनाशन गणेश स्तोत्र, गणेश पंचरत्न, अष्टोत्तरशतनामावली, वक्रतुंड महाकाय, गणपती गायत्री "
        "आणि सुखकर्ता दुखहर्ता आरती म्हणू शकतो."),
 "hi": ("वह पाठ मेरे पास नहीं है, इसलिए मैं उसे जोड़कर नहीं सुनाऊँगा — गलत श्लोक कहने से न कहना बेहतर है. "
        "कृपया छपा हुआ स्तोत्रसंग्रह देखें या गुरुजी से पूछें. मैं अथर्वशीर्ष, संकटनाशन गणेश स्तोत्र, "
        "गणेश पंचरत्न, अष्टोत्तरशतनामावली, वक्रतुंड महाकाय, गणपति गायत्री और सुखकर्ता दुखहर्ता आरती सुना सकता हूँ."),
}

# Bounded-list traps: the model must know how many items a text HAS, and say so
# rather than inventing an item that does not exist.
BOUNDS = [
 ("Sankatnashan Ganesh Stotra", "संकटनाशन गणेश स्तोत्र", 12, "names",
  "The Sankatnashan Ganesh Stotra names twelve forms of Ganesha, so there is no {n}th name. "
  "The twelve are Vakratunda, Ekadanta, Krishnapingaksha, Gajavaktra, Lambodara, Vikata, "
  "Vighnarajendra, Dhumravarna, Bhalachandra, Vinayaka, Ganapati and Gajanana.",
  "संकटनाशन गणेश स्तोत्रात बारा नावे आहेत, त्यामुळे {n} वे नाव नाही. बारा नावे अशी: वक्रतुंड, "
  "एकदंत, कृष्णपिंगाक्ष, गजवक्त्र, लंबोदर, विकट, विघ्नराजेंद्र, धूम्रवर्ण, भालचंद्र, विनायक, गणपती, गजानन.",
  "संकटनाशन गणेश स्तोत्र में बारह नाम हैं, इसलिए {n} वाँ नाम नहीं है."),
 ("Ganapati Ashtottara Shatanamavali", "अष्टोत्तरशतनामावली", 108, "names",
  "The Ashtottara Shatanamavali has exactly 108 names, so there is no {n}th name.",
  "अष्टोत्तरशतनामावलीत नेमकी १०८ नावे आहेत, त्यामुळे {n} वे नाव नाही.",
  "अष्टोत्तरशतनामावली में ठीक १०८ नाम हैं, इसलिए {n} वाँ नाम नहीं है."),
 ("Ganapati Atharvashirsha", "गणपती अथर्वशीर्ष", 19, "sections",
  "The Atharvashirsha has nineteen sections plus the closing shanti, so there is no section {n}.",
  "अथर्वशीर्षात एकोणीस भाग आणि शेवटी शांतिपाठ आहे, त्यामुळे {n} वा भाग नाही.",
  "अथर्वशीर्ष में उन्नीस भाग और अंत में शांतिपाठ है, इसलिए {n} वाँ भाग नहीं है."),
]

def build_bounds():
    out = []
    for en_t, dev_t, count, kind, a_en, a_mr, a_hi in BOUNDS:
        for n in range(count + 1, count + 14):
            for q, a in [
                (f"What is the {n}th {kind[:-1]} in the {en_t}?", a_en.format(n=n)),
                (f"Recite {kind[:-1]} number {n} of the {en_t}.", a_en.format(n=n)),
                (f"{dev_t}ातील {n} वे नाव कोणते?" if kind == "names" else f"{dev_t}ाचा {n} वा भाग म्हण.",
                 a_mr.format(n=n)),
                (f"{dev_t} का {n} वाँ नाम क्या है?" if kind == "names" else f"{dev_t} का {n} वाँ भाग सुनाइए.",
                 a_hi.format(n=n)),
            ]:
                for _ in range(3):
                    out.append(pair(q, a))
    return out

def pair(q, a):
    return {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": q},
                         {"role": "assistant", "content": a}]}

def build():
    out = []
    for lang, qs in Q_ID.items():
        for q in qs:
            for _ in range(REPEAT_ID):
                out.append(pair(q, IDENTITY[lang]))
    out += build_bounds()
    for t in ABSENT:
        for lang, tmpls in Q_REF.items():
            for _ in range(REPEAT_REF):
                out.append(pair(random.choice(tmpls).format(t=t), A_REF[lang]))
    return out

if __name__ == "__main__":
    assert_intact()
    pairs = build()
    bad = [p for p in pairs
           if p["messages"][1]["content"] in sum(Q_ID.values(), [])
           and LINKEDIN not in p["messages"][2]["content"]]
    if bad:
        sys.exit(f"SELF-CHECK FAILED: {len(bad)} identity answers lack the attribution link")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in pairs) + "\n", encoding="utf-8")
    n_id = sum(len(v) for v in Q_ID.values()) * REPEAT_ID
    print(f"self-check passed: every identity answer names {AUTHOR} and the link")
    print(f"built {len(pairs)} pairs  (identity {n_id}, refusal {len(pairs)-n_id} across {len(ABSENT)} absent texts)")
    print(f"wrote {OUT.relative_to(ROOT)}")
