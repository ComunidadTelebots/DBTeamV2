import os
import json
from glob import glob

# Ruta al archivo central de strings base de la web
WEB_I18N_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../web/i18n/web/en.json'))

# Busca todas las cadenas en los archivos .html y .js de la web

def extract_strings_from_html_js():
    import re
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../web'))
    html_files = glob(os.path.join(root, '*.html'))
    js_files = glob(os.path.join(root, '*.js'))
    string_re = re.compile(r">\s*([^<\n][^<]+?)\s*<|\"([^\"]{3,})\"|'([^']{3,})'")
    found = set()
    for path in html_files + js_files:
        with open(path, encoding='utf-8') as f:
            text = f.read()
            for m in string_re.finditer(text):
                for g in m.groups():
                    if g and not g.strip().startswith(('http', 'btn', 'class', 'id', 'var', 'function', 'let', 'const', 'px', 'rem', 'px;', 'none', 'block', 'inline', 'hidden', 'visible', 'true', 'false', 'OK', 'DOWN', 'Running', 'Stopped', 'Unavailable', 'configured', 'missing')):
                        s = g.strip()
                        if 3 < len(s) < 120 and not s.startswith('<') and not s.endswith('>'):
                            found.add(s)
    return found

def sync_web_strings():
    # Cargar las actuales
    if os.path.exists(WEB_I18N_PATH):
        with open(WEB_I18N_PATH, encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}
    # Extraer nuevas
    found = extract_strings_from_html_js()
    # Añadir las nuevas que no estén
    added = 0
    for s in found:
        if s not in data.values() and s not in data.keys():
            key = s.replace(' ', '_').replace('.', '').replace(':', '').replace('>', '').replace('<', '').lower()[:40]
            if key not in data:
                data[key] = s
                added += 1
    if added:
        with open(WEB_I18N_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Añadidas {added} nuevas cadenas a {WEB_I18N_PATH}")
    else:
        print("No hay nuevas cadenas para añadir.")

if __name__ == "__main__":
    sync_web_strings()
