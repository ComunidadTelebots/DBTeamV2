#!/usr/bin/env python3
import os, re, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
modified = []
pattern = re.compile(r"<script[^>]*>.*?function\s+setTheme\s*\(.*?</script>", re.S|re.I)
for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        if not fn.endswith('.html'):
            continue
        path = os.path.join(dirpath, fn)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                txt = f.read()
        except Exception:
            continue
        matches = list(pattern.finditer(txt))
        if len(matches) > 1:
            # keep first match, remove others
            first = matches[0]
            new_txt = txt[:first.end()]
            # append remainder of original but without other matches
            rest = txt[first.end():]
            # remove any other matches in rest
            rest = pattern.sub('', rest)
            new_txt = txt[:first.end()] + rest
            # backup
            try:
                with open(path + '.bak', 'w', encoding='utf-8') as b:
                    b.write(txt)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_txt)
                modified.append(path)
            except Exception as e:
                print('Failed to write', path, e)

if modified:
    print('Modified files:')
    for p in modified:
        print(p)
else:
    print('No duplicates found.')
