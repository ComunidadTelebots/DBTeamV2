"""Moderation plugin that uses `moderation.classifier` to score messages.

It does not perform automatic bans by default. Instead it pushes
suggestions to Redis (`moderation:actions`) so admins can review.
"""

patterns = []

def setup(bot):
    print("Plugin 'moderation' loaded.")


def run(msg, matches):
    try:
        # Minimal message shape adaptation
        group_id = getattr(msg, 'chat_id', None) or msg.get('chat_id') or msg.get('to', {}).get('id')
        user = getattr(msg, 'from', None) or msg.get('from') or {}
        text = None
        if isinstance(msg, dict):
            text = msg.get('text')
            media_type = msg.get('media_type')
        else:
            text = getattr(msg, 'text', None)
            media_type = getattr(msg, 'media_type', None)

        if not group_id or not user:
            return None

        from python_bot.moderation.classifier import classify_message, push_action_suggestion

        info = classify_message(int(group_id), user, {'text': text or '', 'media_type': media_type})
        suggestion = info.get('suggestion')
        if suggestion:
            # push for admin review
            push_action_suggestion(int(group_id), int(user.get('id') or 0), suggestion, info)
            # Return a short notice so admins in chat see it; this is configurable
            return f"Usuario {user.get('id')} marcado: {suggestion} (score {info.get('total')}). Admins revisen." 
    except Exception as e:
        print('moderation.run error:', e)
    return None
