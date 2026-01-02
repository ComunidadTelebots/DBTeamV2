document.addEventListener('DOMContentLoaded', () => {
  const sendBtn = document.getElementById('sendMessage');
  const sendAs = document.getElementById('sendAsChat');
  const apiBaseInput = document.getElementById('apiBaseChat');
  const apiKeyInput = document.getElementById('apiKeyChat');
  const compose = document.getElementById('compose');
  const messages = document.getElementById('messages');
  const chatIdInput = document.getElementById('chatIdInput');

  function appendMessage(text, cls = 'other'){
    const d = document.createElement('div');
    d.className = 'msg ' + (cls === 'me' ? 'me' : 'other');
    d.textContent = text;
    messages.appendChild(d);
    messages.scrollTop = messages.scrollHeight;
  }

  async function sendToAi(prompt){
    const base = apiBaseInput.value.trim() || '/';
    const url = base.replace(/\/$/, '') + '/ai/chat';
    const body = { prompt: prompt, chat_id: chatIdInput.value || null };
    const headers = { 'Content-Type': 'application/json' };
    const key = apiKeyInput.value.trim();
    if (key) headers['Authorization'] = 'Bearer ' + key;

    try{
      const resp = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
      if (!resp.ok) {
        const t = await resp.text();
        appendMessage('IA error: ' + resp.status + ' ' + t);
        return;
      }
      const data = await resp.json();
      // Expecting { reply: '...' } or plain text fallback
      const reply = data && (data.reply || data.result || data.text) ? (data.reply || data.result || data.text) : JSON.stringify(data);
      appendMessage(reply, 'other');
    }catch(err){
      appendMessage('IA request failed: ' + err.message);
    }
  }

  sendBtn.addEventListener('click', async (e) => {
    const text = compose.value.trim();
    if (!text) return;
    const mode = sendAs.value;
    appendMessage(text, 'me');
    compose.value = '';

    if (mode === 'ai'){
      await sendToAi(text);
    } else {
      // allow existing chat.js behavior to handle send for user/bot
      // If chat.js exposes a send function on window, call it; otherwise no-op
      if (window.sendChatMessage) {
        window.sendChatMessage(text, mode);
      } else {
        // fallback: post to API /messages (minimal)
        const base = apiBaseInput.value.trim() || '/';
        const url = base.replace(/\/$/, '') + '/messages/send';
        const headers = { 'Content-Type': 'application/json' };
        const key = apiKeyInput.value.trim();
        if (key) headers['Authorization'] = 'Bearer ' + key;
        try{
          await fetch(url, { method: 'POST', headers, body: JSON.stringify({ chat_id: chatIdInput.value || null, text, as: mode }) });
        }catch(err){
          appendMessage('Send failed: ' + err.message);
        }
      }
    }
  });
});
