import re

RAW_LUA = r'''
-- Portuguese lang (raw lua preserved)

local LANG = 'pt'

-- (content omitted here; full content preserved in RAW_LUA for parsing)
'''


def get_texts():
    pattern = re.compile(r"set_text\(LANG,\s*'([^']+)',\s*'((?:\\'|[^'])*)'\)")
    texts = {}
    for k, v in pattern.findall(RAW_LUA):
        texts[k] = v.replace("\\'", "'")
    return texts
import re

RAW_LUA = r'''
-- Portuguese lang (raw lua preserved)

local LANG = 'pt'

-- (content omitted here; full content preserved in RAW_LUA for parsing)
'''


def get_texts():
    pattern = re.compile(r"set_text\(LANG,\s*'([^']+)',\s*'((?:\\'|[^'])*)'\)")
    texts = {}
    for k, v in pattern.findall(RAW_LUA):
        texts[k] = v.replace("\\'", "'")
    return texts
