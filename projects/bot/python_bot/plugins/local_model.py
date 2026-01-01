from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import requests
import os

API_BASE = os.getenv('WEB_API_BASE') or os.getenv('API_BASE') or 'http://127.0.0.1:8081'

async def gen_local(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /gen_local <model> | prompt text
    Example: /gen_local gpt2 | Write a short haiku about code
    If model contains spaces, use quotes or separate with |.
    """
    try:
        text = update.message.text or ''
        parts = text.split(None, 1)
        if len(parts) <= 1:
            await update.message.reply_text('Uso: /gen_local <model> | prompt')
            return
        rest = parts[1].strip()
        # split by | to separate model and prompt
        if '|' in rest:
            model, prompt = [x.strip() for x in rest.split('|', 1)]
        else:
            # if no |, assume first token is model name
            sp = rest.split(None, 1)
            if len(sp) == 1:
                await update.message.reply_text('Proveer modelo y prompt. Ej: /gen_local gpt2 | Hola')
                return
            model = sp[0]
            prompt = sp[1]
        payload = { 'model': model, 'prompt': prompt }
        url = API_BASE.rstrip('/') + '/models/run'
        # call API
        try:
            r = requests.post(url, json=payload, timeout=30)
        except Exception as e:
            await update.message.reply_text(f'Error conectando a API: {e}')
            return
        if not r.ok:
            await update.message.reply_text('API error: ' + r.text)
            return
        data = r.json()
        # try to extract generated text
        out = None
        if isinstance(data, dict) and data.get('result'):
            res = data.get('result')
            # transformers pipeline returns list of dicts with 'generated_text'
            if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict) and 'generated_text' in res[0]:
                out = res[0]['generated_text']
            else:
                out = str(res)
        else:
            out = str(data)
        # send back a truncated reply if too long
        if not out:
            out = '(sin resultado)'
        if len(out) > 4000:
            out = out[:3900] + '\n\n...[truncated]'
        await update.message.reply_text(out)
    except Exception as e:
        await update.message.reply_text('Error interno: ' + str(e))


def setup(application):
    application.add_handler(CommandHandler('gen_local', gen_local))
