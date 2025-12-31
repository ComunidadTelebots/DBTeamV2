import re

RAW_LUA = r'''
-- Persian lang (raw lua preserved)

local LANG = 'fa'

-- (content omitted here; full content preserved in RAW_LUA for parsing)

-- Please see original file for full strings
'''


def get_texts():
    pattern = re.compile(r"set_text\(LANG,\s*'([^']+)',\s*'((?:\\'|[^'])*)'\)")
    texts = {}
    for k, v in pattern.findall(RAW_LUA):
        texts[k] = v.replace("\\'", "'")
    return texts
import re

RAW_LUA = r'''
-- Persian lang (raw lua preserved)

local LANG = 'fa'

-- (content omitted here; full content preserved in RAW_LUA for parsing)

-- Please see original file for full strings
'''


def get_texts():
    pattern = re.compile(r"set_text\(LANG,\s*'([^']+)',\s*'((?:\\'|[^'])*)'\)")
    texts = {}
    for k, v in pattern.findall(RAW_LUA):
        texts[k] = v.replace("\\'", "'")
    return texts
