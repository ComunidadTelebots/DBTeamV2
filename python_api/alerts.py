import os
import requests
import smtplib
from email.message import EmailMessage

def send_telegram(text: str):
    token = os.environ.get('BOT_TOKEN')
    chat = os.environ.get('ADMIN_TELEGRAM_CHAT')
    if not token or not chat:
        return False
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        requests.post(url, json={'chat_id': chat, 'text': text})
        return True
    except Exception:
        return False


def send_email(subject: str, body: str):
    host = os.environ.get('SMTP_HOST')
    port = int(os.environ.get('SMTP_PORT', '587'))
    user = os.environ.get('SMTP_USER')
    pwd = os.environ.get('SMTP_PASS')
    to = os.environ.get('ADMIN_EMAIL')
    if not host or not to:
        return False
    msg = EmailMessage()
    msg['From'] = user or f'no-reply@{host}'
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            if user and pwd:
                s.login(user, pwd)
            s.send_message(msg)
        return True
    except Exception:
        return False


def notify_admin(title: str, text: str):
    # prefer telegram, fallback to email
    sent = False
    try:
        sent = send_telegram(f"{title}\n\n{text}") or sent
    except Exception:
        pass
    try:
        sent = send_email(title, text) or sent
    except Exception:
        pass
    return sent
