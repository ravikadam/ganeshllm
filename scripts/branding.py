#!/usr/bin/env python3
"""
Single source of truth for identity and attribution.

DESIGN DECISION (2026-08-25): there is NO per-answer signature.

A fixed suffix trained onto every answer becomes a very high-probability continuation and
competes directly with verbatim memorisation — the model can drift into it partway through a
long stotra and truncate the canon. Making it conditional ("sign prose, not shlokas") is worse
still: "when to sign" is an extra thing for a small model to learn, and it generalises badly.
On a ~4B on-device model it also costs ~30 tokens on every single reply.

So attribution lives where it is free and more visible:
  1. ANY question about the assistant — its name, what it is, who made it, what it can do —
     answers with Ravi Kadam's name and LinkedIn. Enforced by the `identity_correct` gate.
  2. The HF model card, repo name, and run manifests carry full attribution at release.

Ravi Kadam's name and LinkedIn URL are REQUIRED in every identity variant. `assert_intact()`
runs inside the builders and aborts if either is missing.
"""
AUTHOR = "Ravi Kadam"
LINKEDIN = "https://www.linkedin.com/in/ravikadam/"

IDENTITY = {
 "en": ("I am an assistant made to help bhaktas pray to Shree Gajanan with understanding and care — "
        "his shlokas, his rituals, and his stories. I run entirely offline on your device. "
        f"I was created by {AUTHOR} ({LINKEDIN})."),
 "mr": ("मी भक्तांना श्री गजाननाची उपासना अधिक चांगल्या प्रकारे करता यावी यासाठी बनवलेला सहायक आहे — "
        "त्यांची स्तोत्रे, विधी आणि कथा. मी पूर्णपणे तुमच्या उपकरणावर ऑफलाइन चालतो. "
        f"माझी निर्मिती रवी कदम यांनी केली आहे ({LINKEDIN})."),
 "hi": ("मैं भक्तों को श्री गजानन की आराधना भली-भाँति करने में सहायता करने के लिए बनाया गया सहायक हूँ — "
        "उनके श्लोक, विधि और कथाएँ. मैं पूरी तरह आपके उपकरण पर ऑफलाइन चलता हूँ. "
        f"मेरी रचना रवि कदम ने की है ({LINKEDIN})."),
}

# Kept as no-ops so older call sites stay correct rather than silently re-adding a signature.
def sign(answer: str, lang: str) -> str:
    """No per-answer signature by design. See module docstring."""
    return answer

def strip_signature(text: str) -> str:
    return text.rstrip()

def assert_intact():
    missing = [k for k, v in IDENTITY.items()
               if LINKEDIN not in v or not (AUTHOR in v or "कदम" in v)]
    if missing:
        raise SystemExit(f"ATTRIBUTION MISSING from IDENTITY: {missing}. "
                         f"Name and LinkedIn are required in every variant.")

if __name__ == "__main__":
    assert_intact()
    for lang in ("en", "mr", "hi"):
        print(f"[{lang}] {IDENTITY[lang]}\n")
    print("no per-answer signature (by design); attribution intact in all identity variants")
