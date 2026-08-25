# LinkedIn post — DRAFT, HOLD UNTIL THE MODEL IS ACTUALLY PUBLISHED

**Do not post yet.** Every placeholder in `<angle brackets>` must be filled with a real,
verified value first. The post tells people to install and use the model — it cannot go out
before the model exists on Hugging Face and has passed the release gates.

Blocking checklist:
- [ ] Model trained and `runs.py gate <run_id>` passes
- [ ] `.litertlm` built and confirmed loading in Edge Gallery on a real phone
- [ ] HF repo public, model card carries name + LinkedIn (primary attribution surface)
- [ ] Personally recited at least one aarti and one stotra from the model and checked it word by word

---

## Post

गणपती बाप्पा मोरया 🙏

This Ganeshotsav I wanted to try something: can a language model small enough to run *entirely
offline on a phone* be genuinely useful to someone doing puja at home?

No internet. No API. No RAG. Just a small model that has actually learned the shlokas, the
stotras, the aartis, and the vidhi — and can answer in Marathi, Hindi or English.

So I fine-tuned one. It's free, it's open, and it runs on your phone with aeroplane mode on.

**What it does**
• Recites the aartis and stotras — Sukhkarta Dukhharta, Sankatnashan Ganesh Stotra, Atharvashirsha
• Explains the vidhi — pranapratishtha, shodashopachara, the 21 durva, uttarpuja, visarjan
• Tells the stories — why the elephant head, why one tusk, why no tulsi
• Answers in the language you type in

**What it deliberately does NOT do**
It will not guess a muhurat time for your city, and it will not invent a shloka it doesn't know.
It says "I don't know, check your panchang" instead. For a devotional tool I think that matters
more than sounding confident — a wrong Sanskrit line is not a small bug.

**How to try it — takes about 5 minutes**

*Android:*
1. Install **Google AI Edge Gallery** from the Play Store (it's Google's official app for
   running models on-device)
2. Open it → **Import from Hugging Face URL**
3. Paste: `<HF_REPO_URL>`
4. Wait for the download (~<SIZE> GB — use WiFi), then open the chat and ask it anything

*iPhone / iPad:*
1. Install **Google AI Edge Gallery** from the App Store (needs iOS 17 or later)
2. Same steps — import from the Hugging Face URL above

Once it's downloaded, turn on aeroplane mode and try it. That's the part I find genuinely
lovely — it keeps working.

**A caveat, honestly stated**
This is a small model. It will make mistakes. Please treat it as a helpful companion, not as a
guruji or a panchang — for muhurat, family vidhi, and anything disputed, ask your elders and
your priest. If you catch it reciting something incorrectly, tell me and I'll fix it.

Built with Gemma 4 E4B. Model, dataset method and eval suite: `<HF_REPO_URL>`

Would love to hear how it goes if you try it. 🙏

#Ganeshotsav #GaneshChaturthi #OnDeviceAI #Gemma #SmallLanguageModels #Marathi #OpenSource

---

## Notes for filling placeholders

- `<HF_REPO_URL>` — e.g. `https://huggingface.co/ravikadam/ganesh-gemma4-e4b-LiteRT`.
  Edge Gallery's HF import accepts a **model card URL** for a `.litertlm` repo.
  A `.task` file cannot be imported by URL — that is local-"+"-import only (learned in runtrain).
- `<SIZE>` — check the actual `.litertlm` size. Base Gemma 4 E4B litertlm is 3.66 GB, so expect
  roughly that. Say the number honestly; people on mobile data will care.
- Verified install facts as of 2026-08-26: Android via Google Play (`com.google.ai.edge.gallery`),
  iOS via App Store (requires iOS 17.0+). Both are free and official Google apps.
- Consider posting 2-3 days before 14 September so people have it installed before Chaturthi.
