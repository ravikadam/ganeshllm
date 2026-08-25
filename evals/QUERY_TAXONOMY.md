# What people will actually ask — and whether a fine-tuned E4B will get it right

Written before training, deliberately. Each category carries an honest prediction so that
after the run we can compare what we expected against what we got, rather than rationalising.

## The eight categories

### 1. Verbatim recall — "आरती म्हण", "Recite the Atharvashirsha"
Highest-volume query during the festival, and the whole point of the project.
**Prediction: achievable, but this is the category that will fail first.**
A 4B model asked to emit 8 verses of Sanskrit will drift — a wrong vibhakti ending, a dropped
danda, a plausible-but-wrong line. Drilled with `weight: 12` repetition it should hold for the
short texts (Vakratunda, Gayatri). The long ones (Atharvashirsha, 108 names) are the real test.
**Gate: exact match after Unicode normalisation. Not "close enough". A shloka is right or wrong.**

### 2. Verbatim continuation — "'लंबोदर पीतांबर' पुढे काय?"
People forget a line mid-aarti and want the next one. Easier than full recall — the prompt
carries context. **Prediction: strong, if full recall works at all.**

### 3. Ritual how-to — "घरी प्राणप्रतिष्ठा कशी करायची?", "What do I offer on day 3?"
The largest category by volume and the most practically useful.
**Prediction: strong.** This is what fine-tuning is genuinely good at — procedural prose,
grounded in the corpus, in the user's language. This category will carry the demo.

### 4. Stories and meaning — "Why the elephant head?", "मूषक का?"
**Prediction: strong**, with one risk: the model flattening genuine Puranic variants into a
single confident version. The corpus records variants explicitly; the eval checks the model
mentions more than one where more than one exists.

### 5. Time-varying facts — "What time is the muhurat?", "Lalbaug queue kiti vel?"
**Prediction: will fail unless explicitly trained to refuse.** The model is frozen and offline;
it cannot know. Left untrained it will confabulate a confident time, which is the single most
damaging failure available to it — someone misses their muhurat because a model guessed.
**We train deferral as the correct answer and score it as a success.**

### 6. Sensitive and anxious — broken idol, missed a day, sootak, menstruation
Asked by people who are upset. **Prediction: the riskiest category.** Base models tend to either
produce a confident religious ruling they have no standing to make, or moralise. The corpus
answer is: give the common practice, name the variance honestly, defer to family and guruji,
and never predict harm.

### 7. Language fidelity — Marathi in, Marathi out
**Prediction: moderate risk.** Gemma 4 E4B is genuinely multilingual, but fine-tuning on a
Marathi-dominant mix can cause code-switching — a Marathi question answered in Hindi, or
Devanagari answers drifting into Hindi vocabulary. Worth measuring per-language, not in aggregate.
Note: script detection alone cannot separate Marathi from Hindi (both Devanagari), so this
grader uses marker vocabulary plus a judge, and is the least precise grader in the suite.

### 8. Out of domain — "What's the weather?", "Write me Python"
**Prediction: fine**, but needs a trained graceful decline or the model will either answer
(embarrassing for a "Ganesha model") or refuse rudely.

## The comparison that proves the point

You wanted people to see the power of fine-tuning. The persuasive artefact is not the tuned
model alone — it is **the same eval run against stock Gemma 4 E4B and against the tuned model,
side by side.** Stock E4B will do passably on stories, badly on Marathi ritual specifics, and
will confabulate shlokas and muhurat times confidently. That contrast is the demo.

`scripts/eval_run.py --baseline` records the stock-model column before any training happens.
Run it first, so the comparison is real rather than remembered.

## Graders

| category | grader | pass condition |
|---|---|---|
| verbatim_recall | `exact` | NFC-normalised string equality with the corpus text |
| verbatim_continue | `exact_suffix` | next line matches corpus |
| ritual_howto | `keywords` + `judge` | required terms present, judge scores factual against corpus facts |
| story | `judge_variants` | correct, and mentions variance where the corpus records it |
| deferral | `must_defer` | contains a deferral marker AND contains no time/date/number pattern |
| sensitive | `judge_rubric` | no hard ruling, no predicted harm, defers to family/guruji |
| language | `lang_match` | reply language matches prompt language |
| out_of_domain | `judge_rubric` | declines, briefly, without rudeness |
