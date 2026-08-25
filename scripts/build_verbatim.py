#!/usr/bin/env python3
"""
Deterministically build training pairs for VERBATIM units.

The whole point: the canonical Devanagari is spliced byte-exact from the YAML.
No generative model ever writes, rewrites, or 'improves' a shloka. Only the
QUESTION side is varied, from hand-written templates in four languages.

  python scripts/build_verbatim.py            # writes outputs/verbatim_pairs.jsonl
  python scripts/build_verbatim.py --allow-unverified   # dry-run preview only
"""
from __future__ import annotations
import argparse, json, random
from pathlib import Path
from corpus import load_all, ROOT
from branding import sign, assert_intact

random.seed(1729)
OUT = ROOT / "outputs" / "verbatim_pairs.jsonl"

# --- question templates. {t} = title in that language. -----------------------
Q_RECALL = {
    "mr": ["{t} म्हणून दाखव.", "मला {t} पूर्ण म्हण.", "{t} चे संपूर्ण पाठ सांग.",
           "{t} कसं आहे?", "{t} लिहून दे."],
    "hi": ["{t} पूरा सुनाइए.", "मुझे {t} सुनाओ.", "{t} का पूरा पाठ बताइए.",
           "{t} लिखकर दीजिए."],
    "en": ["Recite the {t}.", "Give me the full text of {t}.", "What is the {t}?",
           "Write out {t} for me.", "Can you say the {t}?"],
    "sa": ["{t} पठ।", "{t} इति किम्?"],
}
Q_MEANING = {
    "mr": ["{t} चा अर्थ काय?", "{t} म्हणजे काय?", "{t} चा मराठीत अर्थ सांग."],
    "hi": ["{t} का अर्थ क्या है?", "{t} का मतलब समझाइए."],
    "en": ["What does {t} mean?", "Explain the meaning of {t}.", "Translate {t} into English."],
}
Q_USAGE = {
    "mr": ["{t} कधी म्हणतात?", "{t} केव्हा आणि किती वेळा म्हणावे?"],
    "hi": ["{t} कब पढ़ा जाता है?", "{t} कितनी बार पढ़ना चाहिए?"],
    "en": ["When is {t} recited?", "How many times should {t} be recited?", "When do people say {t}?"],
}
Q_ROMAN = {
    "mr": ["{t} रोमन लिपीत दे.", "{t} इंग्रजी अक्षरात लिहून दे."],
    "hi": ["{t} रोमन लिपि में दीजिए."],
    "en": ["Give {t} in Roman transliteration.", "I can't read Devanagari — write {t} in English letters."],
}
Q_IDENTIFY = {
    "mr": ["'{line}' ही ओळ कोणत्या स्तोत्रातली आहे?"],
    "hi": ["'{line}' यह पंक्ति किस स्तोत्र की है?"],
    "en": ["Which stotra begins '{line}'?", "Where is the line '{line}' from?"],
}

SYSTEM = ("You are an offline assistant fine-tuned on Shri Ganesha's shlokas, stotras, "
          "aartis, rituals and stories. Answer in the language the user writes in. "
          "Never invent a verse.")


def title_for(u, lang):
    t = u.get("title") or {}
    return t.get(lang) or t.get("mr") or t.get("en") or u.id


def pair(q, a):
    return {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": q},
                         {"role": "assistant", "content": a}]}


def build(units, allow_unverified=False):
    pairs, skipped = [], []
    for u in units:
        if u["class"] != "verbatim":
            continue
        if not u.can_emit_verbatim() and not allow_unverified:
            skipped.append(u.id)
            continue

        dev = u.devanagari()
        text = u.get("text") or {}
        meaning = u.get("meaning") or {}
        usage = u.get("usage") or {}

        for _rep in range(u.weight):          # weight = how hard we drill this canon
            for lang, tmpls in Q_RECALL.items():
                q = random.choice(tmpls).format(t=title_for(u, lang))
                pairs.append(pair(q, sign(dev, lang)))   # canon byte-exact ABOVE the signature line

            for lang, tmpls in Q_MEANING.items():
                if meaning.get(lang):
                    q = random.choice(tmpls).format(t=title_for(u, lang))
                    pairs.append(pair(q, sign(meaning[lang].strip(), lang)))

            if usage.get("when"):
                for lang, tmpls in Q_USAGE.items():
                    q = random.choice(tmpls).format(t=title_for(u, lang))
                    a = usage["when"].strip()
                    if usage.get("count"):
                        a += " " + usage["count"].strip()
                    pairs.append(pair(q, sign(a, lang)))

            if text.get("roman_simple"):
                for lang, tmpls in Q_ROMAN.items():
                    q = random.choice(tmpls).format(t=title_for(u, lang))
                    pairs.append(pair(q, sign(text["roman_simple"].strip(), lang)))

            first = dev.splitlines()[0].strip()
            for lang, tmpls in Q_IDENTIFY.items():
                q = random.choice(tmpls).format(line=first)
                pairs.append(pair(q, sign(f"{title_for(u, lang)}.", lang)))

    return pairs, skipped


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-unverified", action="store_true",
                    help="preview only — DO NOT train on the result")
    a = ap.parse_args()

    assert_intact()
    units = load_all()
    pairs, skipped = build(units, a.allow_unverified)

    if skipped:
        print(f"gated {len(skipped)} unverified/incomplete verbatim unit(s): {', '.join(skipped)}")
    print(f"built {len(pairs)} verbatim pairs")

    if a.allow_unverified:
        print("\n--- PREVIEW ONLY, not written to disk ---")
        for p in pairs[:3]:
            print(f"  Q: {p['messages'][1]['content']}")
            print(f"  A: {p['messages'][2]['content'].splitlines()[0]} ...")
    else:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in pairs) + "\n",
                       encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}")
