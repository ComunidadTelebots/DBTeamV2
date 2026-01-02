import os
import json
from transformers import pipeline

BASE_PATH = os.path.join(os.path.dirname(__file__), 'en.py')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'generated_gpt2')

# List of language codes to translate to (ISO 639-1)
LANGUAGES = [
    'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ar', 'hi', 'tr', 'ko', 'pl', 'nl', 'sv', 'fi', 'no', 'da', 'cs', 'el', 'he', 'id', 'ms', 'th', 'vi', 'uk', 'ro', 'hu', 'bg', 'fa', 'sr', 'sk', 'hr', 'lt', 'lv', 'et', 'sl', 'mt', 'ga', 'cy', 'eu', 'gl', 'ca', 'sq', 'mk', 'bs', 'is', 'az', 'ka', 'be', 'uz', 'kk', 'mn', 'hy', 'lo', 'my', 'km', 'si', 'ta', 'te', 'kn', 'ml', 'gu', 'mr', 'pa', 'bn', 'ur', 'ne', 'sw', 'zu', 'xh', 'af', 'yo', 'ig', 'am', 'om', 'so', 'rw', 'ny', 'sn', 'st', 'tn', 'ts', 'ss', 've', 'nr', 'tw', 'ak', 'ee', 'ff', 'ha', 'kr', 'lb', 'lg', 'ln', 'lu', 'nd', 'rn', 'sg', 'sh', 'ti', 'yi', 'jv', 'su', 'ceb', 'haw', 'hmn', 'jw', 'tl', 'fil', 'ilo', 'war', 'bikol', 'pam', 'pag', 'hil', 'hiligaynon', 'mag', 'mdh', 'msb', 'tao', 'tsg', 'yue', 'zh-TW', 'zh-HK'
]

# Extract LANG dict from en.py
lang_dict = {}
with open(BASE_PATH, 'r', encoding='utf-8') as f:
    code = f.read()
    ns = {}
    exec(code, ns)
    lang_dict = ns.get('LANG', {})

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load translation pipeline (Helsinki-NLP models for many languages)
def get_translator(lang):
    if lang == 'en':
        return None
    model_name = f"Helsinki-NLP/opus-mt-en-{lang}"
    try:
        return pipeline('translation_en_to_'+lang, model=model_name)
    except Exception:
        return None

for lang in LANGUAGES:
    print(f'Translating to {lang}...')
    translator = get_translator(lang)
    translated = {}
    for k, v in lang_dict.items():
        if not translator:
            translated[k] = v
            continue
        try:
            t = translator(v)
            translated[k] = t[0]['translation_text'] if t and isinstance(t, list) else v
        except Exception as e:
            translated[k] = v
    # Write to Python file
    out_path = os.path.join(OUTPUT_DIR, f'{lang}.py')
    with open(out_path, 'w', encoding='utf-8') as out:
        out.write(f"""# Auto-generated translation with GPT2/OpusMT
LANG = {json.dumps(translated, ensure_ascii=False, indent=2)}
""")
print('Done!')
