#!/usr/bin/env python3
"""Shared corpus loader + validator. Every other script imports this."""
from __future__ import annotations
import sys, unicodedata
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"

ALLOWED_LICENSES = {"public-domain", "original"}
ALLOWED_CLASSES = {"verbatim", "prose"}
LANGS = ("mr", "hi", "en", "sa")

# Marathi-dominant mix, per the project decision. Change here, rebuild, retrain.
LANG_MIX = {"mr": 0.45, "en": 0.25, "hi": 0.20, "sa": 0.10}


class Unit(dict):
    @property
    def id(self): return self["id"]
    @property
    def cls(self): return self["class"]
    @property
    def verified(self): return bool(self.get("verified", False))
    @property
    def complete(self): return bool(self.get("complete", True))
    @property
    def weight(self): return int(self.get("weight", 1))

    def devanagari(self) -> str | None:
        t = self.get("text") or {}
        d = t.get("devanagari")
        return d.strip() if d else None

    def can_emit_verbatim(self) -> bool:
        """The gate. Unverified or incomplete canon never becomes a recall target."""
        return self.cls == "verbatim" and self.verified and self.complete and bool(self.devanagari())


def load_all() -> list[Unit]:
    units, seen = [], set()
    for p in sorted(CORPUS.rglob("*.yaml")):
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise SystemExit(f"{p}: not a YAML mapping")
        raw["_path"] = str(p.relative_to(ROOT))
        u = Unit(raw)
        if u.id in seen:
            raise SystemExit(f"{p}: duplicate id {u.id!r}")
        seen.add(u.id)
        units.append(u)
    return units


def validate(units: list[Unit]) -> list[str]:
    errs = []
    for u in units:
        p = u["_path"]
        for f in ("id", "class", "kind", "license", "title"):
            if f not in u:
                errs.append(f"{p}: missing required field {f!r}")
        if u.get("license") not in ALLOWED_LICENSES:
            errs.append(f"{p}: license {u.get('license')!r} not in {ALLOWED_LICENSES} "
                        f"(copyrighted material must not enter the corpus)")
        if u.get("class") not in ALLOWED_CLASSES:
            errs.append(f"{p}: class {u.get('class')!r} invalid")
        if u.get("class") == "verbatim":
            if not u.devanagari():
                errs.append(f"{p}: verbatim unit has no text.devanagari")
            else:
                d = u.devanagari()
                if d != unicodedata.normalize("NFC", d):
                    errs.append(f"{p}: devanagari is not NFC-normalised — normalise before training")
        if u.get("class") == "prose" and not u.get("facts"):
            errs.append(f"{p}: prose unit has no facts[] to ground generation")
    return errs


def report(units: list[Unit]) -> str:
    ver = [u for u in units if u.cls == "verbatim"]
    pro = [u for u in units if u.cls == "prose"]
    gated = [u for u in ver if not u.can_emit_verbatim()]
    lines = [
        f"units: {len(units)}  (verbatim {len(ver)}, prose {len(pro)})",
        f"verbatim cleared for recall training: {len(ver) - len(gated)}/{len(ver)}",
    ]
    if gated:
        lines.append("GATED (verified:false or complete:false) — no recall pairs will be emitted:")
        for u in gated:
            why = []
            if not u.verified: why.append("unverified")
            if not u.complete: why.append("incomplete")
            lines.append(f"  - {u.id}  ({', '.join(why)})")
    return "\n".join(lines)


if __name__ == "__main__":
    units = load_all()
    errs = validate(units)
    print(report(units))
    if errs:
        print("\nERRORS:", file=sys.stderr)
        for e in errs: print("  " + e, file=sys.stderr)
        sys.exit(1)
    print("\nschema OK")
