#!/usr/bin/env python3
"""
Build heavily-reinforced 2026 calendar pairs.

Same discipline as build_verbatim.py: the FACTS are constants in this file, spliced
into answers. No generative model invents or paraphrases a date or a time.

Two rules enforced structurally, not by hope:
  1. every answer that carries a date or time opens with the year
  2. every muhurat clock time names its city
A self-check at the bottom fails the build if either is violated.

  python scripts/build_calendar.py
"""
from __future__ import annotations
import json, random, re, sys
from pathlib import Path
from corpus import ROOT
from branding import sign, assert_intact

random.seed(4242)
OUT = ROOT / "outputs" / "calendar_pairs.jsonl"
REPEAT = 15          # reinforcement multiplier

SYSTEM = ("You are an offline assistant fine-tuned on Shri Ganesha's shlokas, stotras, "
          "aartis, rituals and stories. Answer in the language the user writes in. "
          "Never invent a verse.")

# ---------------------------------------------------------------- the facts --
A = {
 "chaturthi": {
   "en": "In 2026, Ganesh Chaturthi falls on Monday, 14 September 2026. The Chaturthi tithi begins at 07:06 AM on 14 September and ends at 07:44 AM on 15 September.",
   "mr": "२०२६ मध्ये गणेश चतुर्थी सोमवार, १४ सप्टेंबर २०२६ रोजी आहे. चतुर्थी तिथी १४ सप्टेंबरला सकाळी ०७:०६ वाजता सुरू होते आणि १५ सप्टेंबरला सकाळी ०७:४४ वाजता संपते.",
   "hi": "२०२६ में गणेश चतुर्थी सोमवार, १४ सितंबर २०२६ को है. चतुर्थी तिथि १४ सितंबर को सुबह ०७:०६ बजे शुरू होकर १५ सितंबर को सुबह ०७:४४ बजे समाप्त होती है.",
 },
 "muhurat_mumbai": {
   "en": "In 2026, for Mumbai, the madhyahna sthapana muhurat is 11:20 AM to 01:48 PM on Monday 14 September — about 2 hours 27 minutes. This window is city-specific: the generic figure quoted in most almanacs is 11:02 AM to 01:31 PM, roughly 18 minutes earlier. Please confirm against a panchang set to your own city.",
   "mr": "२०२६ मध्ये मुंबईसाठी मध्याह्न स्थापना मुहूर्त सोमवार १४ सप्टेंबर रोजी सकाळी ११:२० ते दुपारी ०१:४८ असा आहे — सुमारे २ तास २७ मिनिटे. हा मुहूर्त शहरानुसार बदलतो: सर्वसाधारण पंचांगात ११:०२ ते ०१:३१ असा दिलेला असतो, जो सुमारे १८ मिनिटे आधीचा आहे. कृपया आपल्या शहराचे पंचांग पाहून खात्री करून घ्या.",
   "hi": "२०२६ में मुंबई के लिए मध्याह्न स्थापना मुहूर्त सोमवार १४ सितंबर को सुबह ११:२० से दोपहर ०१:४८ तक है — लगभग २ घंटे २७ मिनट. यह मुहूर्त शहर के अनुसार बदलता है: सामान्य पंचांग में ११:०२ से ०१:३१ दिया जाता है, जो लगभग १८ मिनट पहले है. कृपया अपने शहर के पंचांग से पुष्टि करें.",
 },
 "visarjan_main": {
   "en": "In 2026, Anant Chaturdashi — the main visarjan day, when the large Mumbai mandals immerse — is Friday, 25 September 2026.",
   "mr": "२०२६ मध्ये अनंत चतुर्दशी — मुख्य विसर्जनाचा दिवस, जेव्हा मुंबईतील मोठी मंडळे विसर्जन करतात — शुक्रवार, २५ सप्टेंबर २०२६ रोजी आहे.",
   "hi": "२०२६ में अनंत चतुर्दशी — मुख्य विसर्जन का दिन, जब मुंबई के बड़े मंडल विसर्जन करते हैं — शुक्रवार, २५ सितंबर २०२६ को है.",
 },
 "visarjan_all": {
   "en": "In 2026 the visarjan days by duration are: dedh divas (1.5 day) on 15 September, 3-day on 16 September, 5-day on 18 September, 7-day on 20 September, and 10-day on Anant Chaturdashi, 25 September. The duration is a family tradition — all are equally proper.",
   "mr": "२०२६ मध्ये विसर्जनाचे दिवस असे आहेत: दीड दिवस — १५ सप्टेंबर, तीन दिवस — १६ सप्टेंबर, पाच दिवस — १८ सप्टेंबर, सात दिवस — २० सप्टेंबर, आणि दहा दिवस म्हणजे अनंत चतुर्दशी — २५ सप्टेंबर. किती दिवस बसवायचे ही कुटुंबाची परंपरा आहे; सर्व सारखेच योग्य आहेत.",
   "hi": "२०२६ में विसर्जन के दिन इस प्रकार हैं: डेढ़ दिन — १५ सितंबर, तीन दिन — १६ सितंबर, पाँच दिन — १८ सितंबर, सात दिन — २० सितंबर, और दस दिन यानी अनंत चतुर्दशी — २५ सितंबर. कितने दिन बिठाना है यह पारिवारिक परंपरा है.",
 },
 "gauri": {
   "en": "In 2026, Jyeshtha Gauri Avahan is Thursday 17 September, Gauri Pujan is Friday 18 September, and Gauri Visarjan is Saturday 19 September.",
   "mr": "२०२६ मध्ये ज्येष्ठा गौरी आवाहन गुरुवार १७ सप्टेंबर, गौरी पूजन शुक्रवार १८ सप्टेंबर, आणि गौरी विसर्जन शनिवार १९ सप्टेंबर रोजी आहे.",
   "hi": "२०२६ में ज्येष्ठा गौरी आवाहन गुरुवार १७ सितंबर, गौरी पूजन शुक्रवार १८ सितंबर, और गौरी विसर्जन शनिवार १९ सितंबर को है.",
 },
 "angarki": {
   "en": "In 2026, Angarki Sankashti Chaturthi falls on Tuesday 29 September. The other Angarki dates in 2026 were 6 January and 5 May. Angarki is simply a Sankashti Chaturthi that falls on a Tuesday.",
   "mr": "२०२६ मध्ये अंगारकी संकष्टी चतुर्थी मंगळवार २९ सप्टेंबर रोजी आहे. २०२६ मधील इतर अंगारकी ६ जानेवारी आणि ५ मे रोजी होत्या. मंगळवारी येणाऱ्या संकष्टीलाच अंगारकी म्हणतात.",
   "hi": "२०२६ में अंगारकी संकष्टी चतुर्थी मंगलवार २९ सितंबर को है. २०२६ की अन्य अंगारकी ६ जनवरी और ५ मई को थीं. मंगलवार को पड़ने वाली संकष्टी को ही अंगारकी कहते हैं.",
 },
 # ---- the deferrals. These are CORRECT answers, trained as first-class. ----
 "defer_moonrise": {
   "en": "I can't give you a moonrise time. Sankashti moonrise differs by city and changes every month, and I'm an offline model with no way to compute it for your location. Please check a panchang or a Sankashti app set to your city for the exact chandrodaya time.",
   "mr": "मी चंद्रोदयाची वेळ सांगू शकत नाही. संकष्टीचा चंद्रोदय शहरानुसार आणि दर महिन्याला बदलतो, आणि मी ऑफलाइन मॉडेल असल्याने तो काढू शकत नाही. कृपया आपल्या शहराचे पंचांग किंवा संकष्टी अ‍ॅप पाहून नेमकी वेळ घ्या.",
   "hi": "मैं चंद्रोदय का समय नहीं बता सकता. संकष्टी का चंद्रोदय शहर के अनुसार और हर महीने बदलता है, और मैं ऑफलाइन मॉडल हूँ. कृपया अपने शहर का पंचांग या संकष्टी ऐप देखकर सही समय लें.",
 },
 "defer_otheryear": {
   "en": "My calendar information covers 2026 only. Tithi-based dates shift by roughly ten or eleven days each year, so I can't work it out for another year — please check a current panchang.",
   "mr": "माझ्याकडे फक्त २०२६ सालच्या तारखा आहेत. तिथीवर आधारित तारखा दरवर्षी साधारण दहा-अकरा दिवसांनी सरकतात, त्यामुळे मी दुसऱ्या वर्षाची तारीख काढू शकत नाही — कृपया चालू पंचांग पाहा.",
   "hi": "मेरे पास केवल २०२६ की तिथियाँ हैं. तिथि आधारित तारीखें हर साल लगभग दस-ग्यारह दिन खिसकती हैं, इसलिए मैं दूसरे वर्ष की तारीख नहीं बता सकता — कृपया चालू पंचांग देखें.",
 },
 "defer_queue": {
   "en": "I can't tell you current queue or darshan timings — I'm an offline model and those change daily through the festival. Please check the mandal's own announcement or their official social media for this year.",
   "mr": "सध्याची रांग किंवा दर्शनाची वेळ मी सांगू शकत नाही — मी ऑफलाइन मॉडेल आहे आणि उत्सवात या रोज बदलतात. कृपया मंडळाची अधिकृत घोषणा पाहा.",
   "hi": "मैं मौजूदा कतार या दर्शन का समय नहीं बता सकता — मैं ऑफलाइन मॉडल हूँ और उत्सव में ये रोज़ बदलते हैं. कृपया मंडल की आधिकारिक घोषणा देखें.",
 },
}

# ------------------------------------------------------------- the questions --
Q = {
 "chaturthi": {
   "en": ["When is Ganesh Chaturthi in 2026?", "What date is Ganesh Chaturthi 2026?",
          "Ganpati 2026 kab hai?", "Which day does Ganesh Chaturthi fall on this year?",
          "When does Ganeshotsav start in 2026?"],
   "mr": ["२०२६ मध्ये गणेश चतुर्थी कधी आहे?", "गणपती कधी बसणार?", "यंदा गणेश चतुर्थी कोणत्या तारखेला आहे?",
          "गणेशोत्सव कधी सुरू होतो?", "चतुर्थी तिथी किती वाजता सुरू होते?"],
   "hi": ["२०२६ में गणेश चतुर्थी कब है?", "गणपति कब बैठेंगे?", "इस साल गणेश चतुर्थी किस तारीख को है?"],
 },
 "muhurat_mumbai": {
   "en": ["What is the sthapana muhurat for Ganesh Chaturthi 2026 in Mumbai?",
          "What time should I install Ganpati in Mumbai?", "Mumbai muhurat timing for Ganpati sthapana?",
          "When is the madhyahna muhurat?", "What time is the puja muhurat this year?"],
   "mr": ["मुंबईत गणपती स्थापनेचा मुहूर्त किती वाजता आहे?", "स्थापनेचा मुहूर्त काय आहे?",
          "मध्याह्न मुहूर्त किती वाजता?", "गणपती किती वाजता बसवावा?"],
   "hi": ["मुंबई में गणपति स्थापना का मुहूर्त क्या है?", "स्थापना का समय क्या है?",
          "मध्याह्न मुहूर्त कितने बजे है?"],
 },
 "visarjan_main": {
   "en": ["When is Anant Chaturdashi 2026?", "When is the main Ganpati visarjan in 2026?",
          "What date do the big Mumbai mandals immerse?"],
   "mr": ["अनंत चतुर्दशी कधी आहे?", "मुख्य विसर्जन कधी आहे?", "मोठी मंडळे कधी विसर्जन करतात?"],
   "hi": ["अनंत चतुर्दशी कब है?", "मुख्य विसर्जन कब है?"],
 },
 "visarjan_all": {
   "en": ["What are all the visarjan dates in 2026?", "When is the 5-day visarjan?",
          "When is dedh divas visarjan 2026?", "I'm keeping Ganpati for 7 days — which date is visarjan?"],
   "mr": ["२०२६ मधील विसर्जनाच्या सर्व तारखा सांग.", "दीड दिवसाचे विसर्जन कधी?",
          "पाच दिवसांचा गणपती कधी विसर्जित करायचा?", "सात दिवसांचे विसर्जन कोणत्या तारखेला?"],
   "hi": ["२०२६ में विसर्जन की सभी तारीखें बताइए.", "डेढ़ दिन का विसर्जन कब है?",
          "पाँच दिन का विसर्जन कब है?"],
 },
 "gauri": {
   "en": ["When is Gauri Avahan in 2026?", "What are the Jyeshtha Gauri dates this year?",
          "When is Gauri Pujan 2026?"],
   "mr": ["२०२६ मध्ये गौरी आवाहन कधी आहे?", "ज्येष्ठा गौरीच्या तारखा सांग.", "गौरी पूजन कधी आहे?"],
   "hi": ["२०२६ में गौरी आवाहन कब है?", "ज्येष्ठा गौरी की तिथियाँ बताइए."],
 },
 "angarki": {
   "en": ["When is Angarki Chaturthi in 2026?", "What is Angarki?", "Angarki Sankashti 2026 date?"],
   "mr": ["२०२६ मध्ये अंगारकी कधी आहे?", "अंगारकी म्हणजे काय?", "अंगारकी संकष्टी कधी येते?"],
   "hi": ["२०२६ में अंगारकी कब है?", "अंगारकी क्या है?"],
 },
 "defer_moonrise": {
   "en": ["What time is moonrise for Sankashti in Mumbai?", "When is chandrodaya tomorrow for Sankashti?",
          "What time can I break my Sankashti fast?"],
   "mr": ["संकष्टीला चंद्रोदय किती वाजता आहे?", "उपवास किती वाजता सोडायचा?", "चंद्र कधी दिसेल?"],
   "hi": ["संकष्टी को चंद्रोदय कितने बजे है?", "व्रत कब खोलें?"],
 },
 "defer_otheryear": {
   "en": ["When is Ganesh Chaturthi in 2027?", "What date is Ganpati next year?",
          "When is Anant Chaturdashi in 2028?"],
   "mr": ["२०२७ मध्ये गणेश चतुर्थी कधी आहे?", "पुढच्या वर्षी गणपती कधी बसणार?"],
   "hi": ["२०२७ में गणेश चतुर्थी कब है?", "अगले साल गणपति कब हैं?"],
 },
 "defer_queue": {
   "en": ["How long is the Lalbaugcha Raja queue right now?", "What are Siddhivinayak darshan timings today?",
          "How much time for Mumbaicha Raja darshan?"],
   "mr": ["लालबागच्या राजाची रांग किती वेळ आहे?", "सिद्धिविनायकाची दर्शन वेळ काय आहे?"],
   "hi": ["लालबाग के राजा की कतार कितनी लंबी है?", "सिद्धिविनायक दर्शन का समय क्या है?"],
 },
}

def pair(q, a):
    return {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": q},
                         {"role": "assistant", "content": a}]}

# Only these carry LOCAL-SUNRISE-derived times, so only these must name a city.
# Tithi begin/end times are a single astronomical instant and read identically
# across India on IST — they are correctly city-independent.
CITY_BOUND = {"muhurat_mumbai"}

def build():
    pairs = []
    for key, qs in Q.items():
        for lang, tmpls in qs.items():
            ans = A[key][lang]
            for _ in range(REPEAT):
                p = pair(random.choice(tmpls), sign(ans, lang))
                p["_key"] = key
                pairs.append(p)
    return pairs

# ------------------------------------------------------------- self-checks --
YEAR_LEAD = re.compile(r"(In 2026|२०२६ मध्ये|२०२६ में)")
CLOCKISH  = re.compile(r"\d{1,2}:\d{2}|[०-९]{1,2}:[०-९]{2}")
CITYISH   = re.compile(r"Mumbai|मुंबई")

def selfcheck(pairs):
    bad = []
    for p in pairs:
        a = p["messages"][2]["content"]
        if p["_key"].startswith("defer_"):   # deferrals carry no dates, by design
            continue
        if not YEAR_LEAD.search(a):
            bad.append(("no year stamp", a[:60]))
        if p["_key"] in CITY_BOUND and not CITYISH.search(a):
            bad.append(("muhurat time without city", a[:60]))
    return bad

if __name__ == "__main__":
    assert_intact()
    pairs = build()
    bad = selfcheck(pairs)
    if bad:
        print(f"SELF-CHECK FAILED ({len(bad)} violations):", file=sys.stderr)
        for why, snip in bad[:10]:
            print(f"  {why}: {snip}...", file=sys.stderr)
        sys.exit(1)
    OUT.parent.mkdir(exist_ok=True)
    clean = [{"messages": p["messages"]} for p in pairs]
    OUT.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in clean) + "\n", encoding="utf-8")
    facts = len(Q); langs = sum(len(v) for v in Q.values())
    print("self-check passed: every dated answer is year-stamped, every muhurat names its city")
    print(f"built {len(pairs)} calendar pairs  ({facts} fact groups x {langs} lang-variants x {REPEAT} reps)")
    print(f"wrote {OUT.relative_to(ROOT)}")
