import os
import json
import re
from googletrans import Translator
def preprocess_string(s):
    # Si la cadena es solo una variable, no traducir
    if re.fullmatch(r'\$[a-zA-Z0-9_]+', s.strip()):
        return s, [], [], [], True
    # Proteger variables tipo $user, $id, $num, etc.
    var_pattern = re.compile(r'(\$[a-zA-Z0-9_]+)')
    vars_found = var_pattern.findall(s)
    for i, var in enumerate(vars_found):
        s = s.replace(var, f'__VAR{i}__')
    # Proteger etiquetas HTML
    html_pattern = re.compile(r'<[^>]+>')
    htmls_found = html_pattern.findall(s)
    for i, tag in enumerate(htmls_found):
        s = s.replace(tag, f'__HTML{i}__')
    # Proteger backticks y markdown
    s = s.replace('`', '__BACKTICK__')
    # Proteger comandos tipo #comando
    cmd_pattern = re.compile(r'(#[a-zA-Z0-9_]+)')
    cmds_found = cmd_pattern.findall(s)
    for i, cmd in enumerate(cmds_found):
        s = s.replace(cmd, f'__CMD{i}__')
    # Solo enviar a traducir el texto entre comillas si existe
    match = re.match(r'^[^\"]*\"([^"]+)\"[^\"]*$', s)
    if match:
        s = match.group(1)
    return s, vars_found, htmls_found, cmds_found, False

def postprocess_string(s, vars_found, htmls_found, cmds_found):
    for i, var in enumerate(vars_found):
        s = s.replace(f'__VAR{i}__', var)
    for i, tag in enumerate(htmls_found):
        s = s.replace(f'__HTML{i}__', tag)
    for i, cmd in enumerate(cmds_found):
        s = s.replace(f'__CMD{i}__', cmd)
    s = s.replace('__BACKTICK__', '`')
    return s

# Path to base language file (English)
BASE_PATH = os.path.join(os.path.dirname(__file__), 'en.py')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'generated')

# List of language codes to translate to (Google Translate supported)
LANGUAGES = [
    'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh-cn', 'ja', 'ar', 'hi', 'tr', 'ko', 'pl', 'nl', 'sv', 'fi', 'no', 'da', 'cs', 'el', 'he', 'id', 'ms', 'th', 'vi', 'uk', 'ro', 'hu', 'bg', 'fa', 'sr', 'sk', 'hr', 'lt', 'lv', 'et', 'sl', 'mt', 'ga', 'cy', 'eu', 'gl', 'ca', 'sq', 'mk', 'bs', 'is', 'az', 'ka', 'be', 'uz', 'kk', 'mn', 'hy', 'lo', 'my', 'km', 'si', 'ta', 'te', 'kn', 'ml', 'gu', 'mr', 'pa', 'bn', 'ur', 'ne', 'sw', 'zu', 'xh', 'af', 'yo', 'ig', 'am', 'om', 'so', 'rw', 'ny', 'sn', 'st', 'tn', 'ts', 'ss', 've', 'nr', 'tw', 'ak', 'ee', 'ff', 'ha', 'kr', 'lb', 'lg', 'ln', 'lu', 'nd', 'rn', 'sg', 'sh', 'ti', 'yi', 'jv', 'su', 'ceb', 'haw', 'hmn', 'jw', 'tl', 'fil', 'ilo', 'war', 'bikol', 'pam', 'pag', 'hil', 'hiligaynon', 'mag', 'mdh', 'msb', 'tao', 'tsg', 'yue', 'zh-TW', 'zh-HK'
]

# Extract LANG dict from en.py
lang_dict = {}
with open(BASE_PATH, 'r', encoding='utf-8') as f:
    code = f.read()
    ns = {}
    exec(code, ns)
    lang_dict = ns.get('LANG', {})

os.makedirs(OUTPUT_DIR, exist_ok=True)
translator = Translator()

""")
for lang in LANGUAGES:
    print(f'Translating to {lang}...')
    translated = {}
    for k, v in lang_dict.items():
        # Preprocesar string
        pre_v, vars_found, htmls_found, cmds_found, skip_translate = preprocess_string(v)
        if skip_translate:
            translated[k] = v
            continue
        try:
            t = translator.translate(pre_v, dest=lang)
            # Restaurar variables y formatos
            translated[k] = postprocess_string(t.text, vars_found, htmls_found, cmds_found)
        except Exception as e:
            translated[k] = v
    # Write to Python file
    out_path = os.path.join(OUTPUT_DIR, f'{lang}.py')
    with open(out_path, 'w', encoding='utf-8') as out:
        out.write(f"""# Auto-generated translation
LANG = {json.dumps(translated, ensure_ascii=False, indent=2)}
""")
print('Done!')
