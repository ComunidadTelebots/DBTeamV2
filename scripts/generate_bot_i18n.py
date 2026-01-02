#!/usr/bin/env python3
"""
Generate bot i18n files from `web/i18n/bot/en.json` to multiple target languages
using Hugging Face translation models. The script protects placeholders like
`$users`, `$id`, Markdown/code spans and HTML tags from being translated.

Usage:
  python -m pip install transformers sentencepiece
  python scripts/generate_bot_i18n.py --langs de fr it ja ru zh

If a model isn't available for a language, the script will skip it and print a warning.
"""
import json
import re
import sys
from pathlib import Path
from typing import Dict, Tuple

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
except Exception as e:
    print("Missing transformers. Install with: python -m pip install transformers sentencepiece")
    raise

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "i18n" / "bot" / "en.json"
OUT_DIR = ROOT / "web" / "i18n" / "bot"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Map simple language codes to well-known Helsinki-NLP models where available.
MODEL_MAP = {
    "de": "Helsinki-NLP/opus-mt-en-de",
    "fr": "Helsinki-NLP/opus-mt-en-fr",
    "it": "Helsinki-NLP/opus-mt-en-it",
    "ja": "Helsinki-NLP/opus-mt-en-jap",
    "ru": "Helsinki-NLP/opus-mt-en-ru",
    "zh": "Helsinki-NLP/opus-mt-en-zh",
    # fallback: mbart doesn't require one model per language but needs lang codes
}

# Protect placeholders and inline code from translation
PLACEHOLDER_RE = re.compile(r"(\$[A-Za-z0-9_]+|`[^`]*`|<[^>]+>)")


def protect_text(text: str) -> Tuple[str, Dict[str, str]]:
    placeholders = {}

    def repl(m):
        key = f"__PH{len(placeholders)}__"
        placeholders[key] = m.group(0)
        return key

    protected = PLACEHOLDER_RE.sub(repl, text)
    return protected, placeholders


def restore_text(text: str, placeholders: Dict[str, str]) -> str:
    for k, v in placeholders.items():
        text = text.replace(k, v)
    return text


def translate_text(translator, text: str) -> str:
    if not text.strip():
        return text
    res = translator(text, max_length=512)
    if isinstance(res, list):
        return res[0]["translation_text"]
    return res


def main(langs):
    src = json.loads(SRC.read_text(encoding="utf-8"))

    for lang in langs:
        print(f"\nProcessing language: {lang}")
        model_name = MODEL_MAP.get(lang)
        if not model_name:
            print(f"No model mapped for '{lang}', skipping. You can extend MODEL_MAP in the script.")
            continue

        try:
            print(f"Loading model {model_name}...")
            translator = pipeline("translation", model=model_name)
        except Exception as e:
            print(f"Failed loading model {model_name}: {e}\nSkipping {lang}.")
            continue

        out = {}
        for k, v in src.items():
            # Only translate string values; copy others as-is
            if not isinstance(v, str):
                out[k] = v
                continue

            protected, placeholders = protect_text(v)
            try:
                translated = translate_text(translator, protected)
            except Exception as e:
                print(f"Translation error for key {k}: {e}")
                translated = v

            restored = restore_text(translated, placeholders)
            out[k] = restored

        out_path = OUT_DIR / f"{lang}.json"
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")

    print("\nDone. Review generated files in web/i18n/bot/ and adjust translations if needed.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--langs", nargs="*", default=["de", "fr", "it", "ja", "ru", "zh"], help="Target language codes")
    args = parser.parse_args()
    main(args.langs)
