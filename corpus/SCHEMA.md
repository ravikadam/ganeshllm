# Corpus schema

The corpus is the **single source of truth**. Every training pair is derived from it.
Nothing is scraped at inference time — this is a fine-tuning project, not RAG.

Two classes of unit, handled very differently:

| class | examples | how answers are produced |
|---|---|---|
| **verbatim** | shlokas, stotras, aartis, namavali | Answer text is **copied byte-exact from the YAML**. An LLM never rewrites it. It only proposes *question* phrasings. |
| **prose** | rituals, stories, places, practical | Answer is LLM-generated, but **grounded** in the YAML `facts` block and checked against `must_contain`. |

## Common fields

```yaml
id: vakratunda-mahakaya        # kebab-case, unique, stable — used in eval reports
class: verbatim                # verbatim | prose
kind: shloka                   # shloka | stotra | aarti | namavali | vidhi | story | place | howto
verified: false                # MUST be true before this unit emits verbatim-recall pairs
verified_by: ""                # who checked the Devanagari against a printed/authoritative source
license: public-domain         # public-domain | original  (nothing else is allowed in)
source: "Traditional; widely attested in Puranic mangalacharana"
weight: 10                     # repetition multiplier at build time (verbatim canon gets 8-12)
```

## `verbatim` units

```yaml
title:
  sa: वक्रतुण्ड महाकाय
  mr: वक्रतुंड महाकाय
  hi: वक्रतुंड महाकाय
  en: Vakratunda Mahakaya
text:
  devanagari: |            # THE canonical string. Byte-exact. Never machine-edited.
    वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ ।
  iast: |                  # Roman transliteration (IAST)
    vakratuṇḍa mahākāya sūryakoṭi samaprabha |
  roman_simple: |          # phonetic Roman for people who don't read Devanagari
    Vakratunda Mahakaya Suryakoti Samaprabha |
meaning:
  en: "..."                # our own original translation — never copied from a modern book
  mr: "..."
  hi: "..."
usage:
  when: "Recited before beginning any new work, and at the start of any puja."
  count: "Commonly 1, 3, or 11 times."
notes_en: "Free-form context: attribution debate, regional variants, etc."
```

## `prose` units

```yaml
title: { mr: ..., hi: ..., en: ... }
facts:                       # the grounding. Generator may ONLY use these + notes.
  - "Pranapratishtha is performed once, on the day the idol is installed."
  - "..."
steps:                       # ordered, for vidhi units
  - name_mr: "संकल्प"
    name_en: "Sankalpa"
    detail_en: "..."
must_contain:                # build-time assertion on generated answers (substring, any-language)
  - "सुपारी"
variants:                    # where traditions legitimately differ — the model must say so
  - "Some families install for 1.5 days, others 5, 7, or 10."
sensitivities:               # things the model must hedge or defer to family/guruji on
  - "Muhurat timing varies by panchang; tell the user to check their local panchang."
```

## Rules

1. `license` must be `public-domain` or `original`. Modern copyrighted translations/commentary do not enter this repo.
2. A `verbatim` unit with `verified: false` is **excluded from verbatim-recall training pairs** by `build_dataset.py`. It can still contribute contextual pairs ("when is this recited?").
3. Where traditions differ, record the difference in `variants` — the model should answer "commonly X; some families do Y", never invent a single false orthodoxy.
4. `sensitivities` become explicit hedges in generated answers.
