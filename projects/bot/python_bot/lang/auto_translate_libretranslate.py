
import os
import json
import re
import requests

BASE_PATH = os.path.join(os.path.dirname(__file__), 'en.py')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'generated_libretranslate')
API_URL = 'https://libretranslate.de/translate'

# Solo traducir a amárico para la prueba
LANGUAGES = ['am']

# Preprocesamiento avanzado
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
    match = re.match(r'^[^\"]*\"([^\"]+)\"[^\"]*$', s)
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

# Extraer LANG dict de en.py
lang_dict = {}
with open(BASE_PATH, 'r', encoding='utf-8') as f:
    code = f.read()
    ns = {}
    exec(code, ns)
    lang_dict = ns.get('LANG', {})

os.makedirs(OUTPUT_DIR, exist_ok=True)

def translate(text, target_lang):
    resp = requests.post(API_URL, data={
        'q': text,
        'source': 'en',
        'target': target_lang,
        'format': 'text'
    })
    if resp.ok:
        return resp.json().get('translatedText', text)
    return text

for lang in LANGUAGES:
    print(f'Traduciendo a {lang}...')
    translated = {}
    for k, v in lang_dict.items():
        pre_v, vars_found, htmls_found, cmds_found, skip_translate = preprocess_string(v)
        if skip_translate:
            translated[k] = v
            continue
        try:
            t = translate(pre_v, lang)
            translated[k] = postprocess_string(t, vars_found, htmls_found, cmds_found)
        except Exception:
            translated[k] = v
    out_path = os.path.join(OUTPUT_DIR, f'{lang}.py')
    with open(out_path, 'w', encoding='utf-8') as out:
        out.write(f"""# Auto-generated translation with LibreTranslate\nLANG = {json.dumps(translated, ensure_ascii=False, indent=2)}\n""")
    # Mostrar resultado aquí
    print(f"\n--- Traducción a {lang} ---\n")
    for k, v in list(translated.items())[:10]:
        print(f'{k}: {v}')
    print(f"... Total: {len(translated)} claves ...\n")
print('¡Listo!')
