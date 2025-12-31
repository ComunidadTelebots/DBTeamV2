"""Compatibility layer: port of bot/methods.lua to Python.

Functions here reuse `python_bot.methods` helpers and provide names
compatible with the original Lua code so existing call sites can be
updated gradually.
"""
from python_bot import methods as pmethods
from python_bot.utils import getChatId

def send_msg(chat_id, text, parse=None):
    return pmethods.send_msg(chat_id, text, parse)

def reply_msg(chat_id, text, msg_id, parse=None):
    return pmethods.reply_msg(chat_id, text, msg_id, parse)

def forward_msg(chat_id, from_chat_id, message_id):
    return pmethods.forward_msg(chat_id, from_chat_id, message_id)

def send_document(chat_id, document, caption=None):
    return pmethods.send_document(chat_id, document, caption)

def send_photo(chat_id, photo, caption=None):
    return pmethods.send_document(chat_id, photo, caption)

def getChatId(chat_id):
    # return structure similar to Lua: { 'ID': '...', 'type': 'group'/'channel' }
    return getChatId(chat_id)

def send_to_api_send(chat_id, text):
    return pmethods.send_to_api_send(chat_id, text)
