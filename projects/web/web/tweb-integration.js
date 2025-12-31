// Helpers to integrate tweb frontend with DBTeamV2 backend endpoints.
// Usage: include this after tweb's JS and after web/telegram.js

(function(){
  function apiFetch(path, opts){
    opts = opts || {};
    opts.headers = opts.headers || {};
    if(localStorage.getItem('td_api_key')){
      opts.headers['Authorization'] = 'Bearer ' + localStorage.getItem('td_api_key');
    }
    return fetch(path, opts).then(r => r.json().then(b => ({ status: r.status, body: b }))); 
  }

  // Send a message through the REST send endpoint used by web/telegram.js
  async function sendMessage(chatId, text){
    const payload = { chat_id: String(chatId), text };
    const res = await apiFetch('/tdlib/sendMessage', { method: 'POST', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } });
    return res;
  }

  // Upload a file via existing upload endpoint. Returns file id/url on success.
  async function uploadFile(file){
    const form = new FormData();
    form.append('file', file);
    const opts = { method: 'POST', body: form }; // auth header added in apiFetch wrapper not usable here
    const token = localStorage.getItem('td_api_key');
    const headers = token ? { 'Authorization': 'Bearer ' + token } : undefined;
    const res = await fetch('/tdlib/upload', Object.assign({ headers }, opts));
    try{ return await res.json(); }catch(e){ return { status: res.status } }
  }

  // Wire tweb composer send button to our sendMessage helper.
  // Replace selectors below if tweb markup differs.
  function wireComposer(){
    const composer = document.querySelector('.composer');
    if(!composer) return;
    const input = composer.querySelector('textarea, input[type=text]');
    const sendBtn = composer.querySelector('.send-btn, button[type=submit]');
    if(!input || !sendBtn) return;
    sendBtn.addEventListener('click', async (e)=>{
      e.preventDefault();
      const chatId = composer.getAttribute('data-chat-id') || document.querySelector('.chat-item.active')?.getAttribute('data-chat-id');
      if(!chatId) return;
      const text = input.value.trim();
      if(!text) return;
      const res = await sendMessage(chatId, text);
      if(res.status === 200){
        input.value = '';
        if(window.showToast) showToast('Mensaje enviado');
      }else{
        if(window.showToast) showToast('Error al enviar: '+(res.body?.message||res.status));
      }
    });
  }

  function init(){
    document.addEventListener('DOMContentLoaded', ()=>{
      wireComposer();
      // Re-wire when tweb dynamically replaces DOM
      const obs = new MutationObserver((m)=>{ wireComposer(); });
      obs.observe(document.body, { childList:true, subtree:true });
    });
  }

  // Expose helpers for manual use
  window.twebIntegration = { sendMessage, uploadFile, apiFetch };
  init();
})();
