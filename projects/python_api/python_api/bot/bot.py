import asyncio
import os
import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import redis.asyncio as aioredis

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        entry = { 'chat_id': msg.chat.id, 'from_id': msg.from_user.id, 'text': msg.text or '', 'date': msg.date.timestamp(), 'id': msg.message_id }
        r = context.bot_data.get('redis')
        if r:
            await r.lpush('web:messages', json.dumps(entry))
            await r.ltrim('web:messages', 0, 99)
        LOG.info('Stored incoming message from %s', msg.from_user.id)
    except Exception as e:
        LOG.exception('on_message error: %s', e)

async def outbox_worker(app):
    r = app.bot_data.get('redis')
    if not r:
        LOG.error('No redis client for outbox')
        return
    while True:
        try:
            item = await r.lpop('web:outbox')
            if not item:
                await asyncio.sleep(0.5)
                continue
            obj = json.loads(item)
            chat_id = obj.get('chat_id')
            text = obj.get('text')
            if chat_id and text:
                await app.bot.send_message(chat_id=int(chat_id), text=text)
        except Exception as e:
            LOG.exception('outbox_worker error: %s', e)
            await asyncio.sleep(1)

async def main():
    if not BOT_TOKEN:
        LOG.error('BOT_TOKEN not set')
        return
    r = aioredis.from_url(REDIS_URL)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    # attach redis to bot data for handlers
    app.bot_data['redis'] = r
    # message handler
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_message))
    # start background outbox worker
    asyncio.create_task(outbox_worker(app))
    LOG.info('Starting bot polling')
    await app.run_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOG.info('Bot stopped')