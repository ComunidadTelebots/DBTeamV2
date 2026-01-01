(() => {
  const apiBase = '';
  let ws = null;
  let selectedChat = null;
  let isConnected = false;
  let botToken = null;

  function el(tag, cls){ const e = document.createElement(tag); if(cls) e.className = cls; return e }

  async function connect() {
    try{
      const res = await fetch('/tdlib/connect', { method: 'POST', headers: Object.assign({'Content-Type':'application/json'}, getAuthHeaders()), body: JSON.stringify({dummy:true}) });
      const j = await res.json();
      console.log('tdlib connect', j);
      isConnected = true;
      document.getElementById('btnConnect').textContent = 'Desconectar';
      try{ document.getElementById('loginPanel').style.display = 'none'; }catch(e){}
      try{ setLocked(false); }catch(e){}
      startWS();
      loadChats();
    }catch(e){ showToast('Error connecting: '+(e && e.message? e.message : e),'error'); }
  }

  async function disconnect(){
    try{
      await fetch('/tdlib/disconnect', { method: 'POST' , headers: getAuthHeaders() });
    }catch(e){}
    try{ if(ws) ws.close(); }catch(e){}
    isConnected = false;
    document.getElementById('btnConnect').textContent = 'Conectar';
    try{ document.getElementById('loginPanel').style.display = 'block'; }catch(e){}
    try{ setLocked(true); }catch(e){}
  }

  function startWS(){
    if(ws) try{ ws.close() }catch(e){}
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/tdlib/ws`);
    ws.onopen = ()=> console.log('ws open');
    ws.onmessage = (ev)=> {
      try{
        const d = JSON.parse(ev.data);
        console.log('ws event', d);
        appendEvent(d);
      }catch(e){
        try{ appendEvent(ev.data) }catch(_){ console.log(ev.data) }
      }
    };
    ws.onclose = ()=> console.log('ws closed');
  }

  async function loadChats(){
    const elList = document.getElementById('chatList');
    elList.innerHTML = 'Cargando...';
    try{
      const res = await fetch('/tdlib/chats', { headers: getAuthHeaders() });
      if(!res.ok){ elList.innerHTML = 'No conectado'; return }
      const data = await res.json();
      elList.innerHTML = '';
      if(!data || data.length===0){ elList.innerHTML = '<div class="site-brand-sub">No hay chats (dummy)</div>'; return }
      data.forEach(c=>{
        const item = el('div','chat-item');
        item.textContent = c.title || c.id || 'chat';
        item.addEventListener('click', ()=> selectChat(c));
        elList.appendChild(item);
      });
    }catch(e){ elList.innerHTML = 'Error'; }
  }

  async function loadMessages(){
    try{
      const res = await fetch('/tdlib/messages', { headers: getAuthHeaders() });
      if(!res.ok) return;
      const data = await res.json();
      const area = document.getElementById('messages');
      area.innerHTML = '';
      if(!data || data.length===0){ area.innerHTML = '<div class="site-brand-sub">No hay mensajes</div>'; return }
      data.reverse().forEach(ev=>{
        try{ appendEvent(typeof ev === 'string' ? JSON.parse(ev) : ev) }catch(e){ appendEvent(ev) }
      });
    }catch(e){ console.log('loadMessages error', e) }
  }

  // auto-refresh recent messages every 4s
  setInterval(()=>{ try{ loadMessages() }catch(e){} }, 4000);


  function selectChat(c){
    selectedChat = c;
    document.getElementById('chatTitle').textContent = c.title || ('Chat '+(c.id||''));
    document.getElementById('messages').textContent = '';
    loadMessages();
  }

  async function sendMessage(){
    const t = document.getElementById('msgText').value.trim();
    if(!t) return;
    if(!selectedChat){ alert('Selecciona un chat'); return }
    try{
      // include uploaded attachment if present
      const attachUrl = window._lastUploadedUrl || null;
      const body = { chat_id:selectedChat.id||selectedChat.peer_id||0, text:t };
      if(attachUrl) body.attachment_url = attachUrl;
      // choose send method
      const via = document.getElementById('sendVia').value;
      if(via === 'bot'){
        // send via server-side endpoint to avoid exposing Bot token in browser
        const res = await fetch('/bot/send',{method:'POST',headers: Object.assign({'Content-Type':'application/json'}, getAuthHeaders()),body:JSON.stringify(Object.assign(body, { attachment_url: attachUrl }))});
        if(res.ok){ document.getElementById('msgText').value=''; showToast('Enviado via servidor (Bot API)','success'); }
        else{ const txt = await res.text(); showToast('Error: '+txt,'error') }
      }else{
        const res = await fetch('/tdlib/send',{method:'POST',headers: Object.assign({'Content-Type':'application/json'}, getAuthHeaders()),body:JSON.stringify(body)});
        if(res.ok){ document.getElementById('msgText').value=''; showToast('Enviado (simulado)','success'); }
        else{ const txt = await res.text(); showToast('Error: '+txt,'error') }
      }
    }catch(e){ alert('Error: '+e) }
  }

  // upload helper
  async function uploadFile(file){
    const fd = new FormData();
    fd.append('file', file);
    try{
      const res = await fetch('/tdlib/upload', { method: 'POST', body: fd, headers: getAuthHeaders() });
      if(!res.ok){ const t = await res.text(); showToast('Upload failed: '+t,'error'); return null }
      const j = await res.json();
      // store last uploaded URL globally for sendMessage
      window._lastUploadedUrl = j.url;
      showToast('Archivo subido: '+j.url,'success');
      return j.url;
    }catch(e){ alert('Upload error: '+e); return null }
  }

  function appendEvent(ev){
    // if a chat is selected, ignore events from other chats
    if(ev && ev.type==='message' && selectedChat && (ev.chat_id != (selectedChat.id||selectedChat.peer_id))){
      return;
    }
    const area = document.getElementById('messages');
    const container = document.createElement('div');
    container.className = 'msg-row';
    container.dataset.eventId = ev && ev.id ? ev.id : '';
    // determine if message is from 'me'
    const isMe = ev && (ev.from_me === true || ev.from === 'me' || ev.sender === 'me');
    container.classList.add(isMe ? 'me' : 'other');

    if(typeof ev === 'string'){
      const bubble = document.createElement('div'); bubble.className = 'msg-bubble other'; bubble.textContent = ev;
      container.appendChild(bubble);
    } else if(ev && ev.type === 'message'){
      // left avatar for 'other'
      if(!isMe){
        const av = document.createElement('div'); av.className = 'msg-avatar'; container.appendChild(av);
      }
      const bubble = document.createElement('div'); bubble.className = 'msg-bubble '+(isMe? 'me' : 'other');
      // content
      const textNode = document.createElement('div'); textNode.innerHTML = ev.text || '';
      bubble.appendChild(textNode);
      // attachment preview
      if(ev.attachment_url){
        const url = ev.attachment_url;
        const isImg = url.match(/\.(jpg|jpeg|png|gif|webp)(\?|$)/i);
        if(isImg){
          const img = document.createElement('img'); img.src = url; img.style.maxWidth='280px'; img.style.borderRadius='8px'; img.style.display='block'; img.style.marginTop='8px'; bubble.appendChild(img);
        } else {
          const a = document.createElement('a'); a.href = url; a.target='_blank'; a.textContent = 'Adjunto: ' + url; a.style.display='block'; a.style.marginTop='8px'; bubble.appendChild(a);
        }
      }
      const meta = document.createElement('div'); meta.className = 'msg-meta'; meta.textContent = new Date((ev.ts||Date.now())*1000).toLocaleString(); bubble.appendChild(meta);
      // actions for own messages
      if(isMe){
        const actions = document.createElement('div'); actions.style.marginTop='6px';
        const editBtn = document.createElement('button'); editBtn.className='msg-edit btn ghost'; editBtn.textContent='Editar';
        const delBtn = document.createElement('button'); delBtn.className='msg-delete btn ghost'; delBtn.textContent='Borrar';
        actions.appendChild(editBtn); actions.appendChild(delBtn);
        bubble.appendChild(actions);
      }
      // append bubble and optional spacer for me
      container.appendChild(bubble);
    } else {
      // edited/deleted/other events
      const bubble = document.createElement('div'); bubble.className='msg-bubble other';
      if(ev && ev.type === 'edited'){
        bubble.textContent = `(edit) ${ev.id}: ${ev.text}`;
      } else if(ev && ev.type === 'deleted'){
        bubble.textContent = `(deleted) ${ev.id}`;
      } else {
        bubble.textContent = JSON.stringify(ev);
      }
      container.appendChild(bubble);
    }

    area.appendChild(container);
    area.scrollTop = area.scrollHeight;

    // attach handlers
    const editBtn = container.querySelector('.msg-edit'); if(editBtn) editBtn.addEventListener('click', ()=> onEditClick(container));
    const delBtn = container.querySelector('.msg-delete'); if(delBtn) delBtn.addEventListener('click', ()=> onDeleteClick(container));
  }

  function onEditClick(node){
    const id = node.dataset.eventId;
    if(!id){ alert('No editable id'); return }
    const text = prompt('Nuevo texto:', node.innerText || '');
    if(text===null) return;
    fetch('/tdlib/message/edit', { method:'POST', headers: Object.assign({'Content-Type':'application/json'}, getAuthHeaders()), body: JSON.stringify({ id: id, text: text }) })
      .then(r=>r.json()).then(j=>{ if(j.status==='ok') loadMessages(); else alert('Edit error'); }).catch(e=>alert('Edit failed: '+e));
  }

  function onDeleteClick(node){
    const id = node.dataset.eventId;
    if(!id){ alert('No id'); return }
    if(!confirm('Borrar este mensaje?')) return;
    fetch('/tdlib/message/delete', { method:'POST', headers: Object.assign({'Content-Type':'application/json'}, getAuthHeaders()), body: JSON.stringify({ id: id }) })
      .then(r=>r.json()).then(j=>{ if(j.status==='ok') node.remove(); else alert('Delete error'); }).catch(e=>alert('Delete failed: '+e));
  }

  function getAuthHeaders(){
    const h = {};
    try{
      const k = localStorage.getItem('td_api_key');
      if(k){ h['Authorization'] = 'Bearer '+k; }
    }catch(e){}
    return h;
  }

  // Auth UI helpers
  async function startAuth(){
    // support overlay (`authPhoneFull`) or normal panel (`authPhone`) and include selected prefix
    const phoneEl = document.getElementById('authPhone') || document.getElementById('authPhoneFull');
    const prefixEl = document.getElementById('countryPrefix') || document.getElementById('countryPrefixFull');
    const phoneRaw = (phoneEl && (phoneEl.value||'').trim()) || '';
    const prefix = (prefixEl && prefixEl.value) || '';
    const phone = prefix ? (prefix + phoneRaw.replace(/^\+/,'')) : phoneRaw;
    if(!phone){
      showFieldError(phoneEl, 'Introduce un número de teléfono');
      try{ phoneEl.focus(); }catch(e){}
      return
    }
    try{
      const res = await fetch('/tdlib/auth/start', { method: 'POST', headers: Object.assign({'Content-Type':'application/json'}, getAuthHeaders()), body: JSON.stringify({ phone: phone }) });
      if(!res.ok){ const t = await res.text(); showToast('Error: '+t,'error'); return }
      try{ document.getElementById('authStatus').textContent = 'Estado: código enviado'; }catch(e){}
      try{ document.getElementById('authStatusFull').textContent = 'Estado: código enviado'; }catch(e){}
      // if server marked that a password will be required, show pwd field
      try{ const j = await res.json(); if(j && j.require_password){ showPasswordFields(true); } }catch(e){}
    }catch(e){ alert('Error iniciando auth: '+e) }
  }

  async function checkAuth(){
    const codeEl = document.getElementById('authCode') || document.getElementById('authCodeFull');
    const code = (codeEl && (codeEl.value||'').trim()) || '';
    if(!code){ showFieldError(codeEl, 'Introduce el código'); try{ codeEl.focus(); }catch(e){}; return }
    // optional password
    const pwdEl = document.getElementById('authPwd') || document.getElementById('authPwdFull');
    const pwd = (pwdEl && pwdEl.value) ? pwdEl.value : null;
    try{
      const body = pwd ? { code: code, password: pwd } : { code: code };
      const res = await fetch('/tdlib/auth/check', { method: 'POST', headers: Object.assign({'Content-Type':'application/json'}, getAuthHeaders()), body: JSON.stringify(body) });
      if(res.ok){ const j = await res.json(); if(j && j.status === 'password_required'){ showPasswordFields(true); showFieldError(pwdEl, 'Se requiere contraseña'); showToast('Se requiere contraseña','error'); try{ pwdEl && pwdEl.focus(); }catch(e){}; return; } try{ document.getElementById('authStatus').textContent = 'Estado: conectado (session '+(j.session_id||'')+')'; }catch(e){} try{ document.getElementById('authStatusFull').textContent = 'Estado: conectado (session '+(j.session_id||'')+')'; }catch(e){} try{ localStorage.setItem('td_session_id', j.session_id||''); }catch(e){}; showToast('Login OK','success'); try{ await connect(); }catch(e){} }
      else{
        // try parse structured response
        try{
          const body = await res.json();
          if(body && body.status === 'password_mismatch'){
            showPasswordFields(true);
            showFieldError(pwdEl, 'no coincide');
            try{ pwdEl && pwdEl.focus(); }catch(e){}
            return;
          }
          const t = body && body.message ? body.message : JSON.stringify(body);
          showToast('Error: '+t,'error');
        }catch(_){ const t = await res.text(); alert('Error: '+t) }
      }
    }catch(e){ alert('Error verificando código: '+e) }
  }

  // poll auth status and update UI
  async function pollAuthStatus(){
    try{
      const res = await fetch('/tdlib/auth/status', { headers: getAuthHeaders() });
      if(!res.ok) return;
      const j = await res.json();
      const st = j.status || 'none';
      let text = 'Estado: '+st;
      if(j.phone) text += ' ('+j.phone+')';
      try{ document.getElementById('authStatus').textContent = text; }catch(e){}
      try{ document.getElementById('authStatusFull').textContent = text; }catch(e){}
      // show password field if backend indicates it
      try{ if(j && j.require_password){ showPasswordFields(true); } }catch(e){}
      // if auth is ready, auto-connect and hide login panel
      if(st === 'ready' && !isConnected){
        try{ document.getElementById('authStatus').textContent = text + ' — conectando...'; }catch(e){}
        try{ document.getElementById('authStatusFull').textContent = text + ' — conectando...'; }catch(e){}
        try{ localStorage.setItem('td_session_id', j.session_id||''); }catch(e){}
        try{ await connect(); }catch(e){}
      }
    }catch(e){ /* ignore */ }
  }

  function setLocked(locked){
    const over = document.getElementById('writeLockedOverlay');
    const full = document.getElementById('fullLockOverlay');
    try{
      // toggle right-panel overlay
      if(over){ if(locked) over.classList.remove('hidden'); else over.classList.add('hidden'); }
      // toggle full-page overlay
      if(full){ if(locked) full.classList.remove('hidden'); else full.classList.add('hidden'); }
      // disable page scroll when locked
      try{ document.body.style.overflow = locked ? 'hidden' : ''; }catch(e){}
      // hide composer entirely and disable buttons when locked
      try{
        const comp = document.querySelector('.composer');
        if(comp){ if(locked) comp.classList.add('hidden'); else comp.classList.remove('hidden'); }
      }catch(e){}
      try{
        const send = document.getElementById('sendMsg'); if(send) send.disabled = !!locked;
        const attach = document.getElementById('attachBtn'); if(attach) attach.disabled = !!locked;
        const attachFile = document.getElementById('attachFile'); if(attachFile) attachFile.disabled = !!locked;
      }catch(e){}
    }catch(e){}
  }

  function showPasswordFields(show){
    try{ const p = document.getElementById('authPwd'); if(p) p.style.display = show ? '' : 'none'; }catch(e){}
    try{ const p2 = document.getElementById('authPwdFull'); if(p2) p2.style.display = show ? '' : 'none'; }catch(e){}
    try{ const cb = document.getElementById('authUsePwd'); if(cb) cb.checked = !!show; }catch(e){}
    try{ const cb2 = document.getElementById('authUsePwdFull'); if(cb2) cb2.checked = !!show; }catch(e){}
  }

  // show a red error state for an input element and message
  function showFieldError(el, msg){
    try{
      if(!el) return;
      el.classList.add('field-error');
      // remove any existing message
      clearFieldError(el);
      const msgEl = document.createElement('div'); msgEl.className = 'field-error-msg'; msgEl.textContent = msg;
      msgEl.dataset._for = el.id || '';
      el.parentNode && el.parentNode.insertBefore(msgEl, el.nextSibling);
    }catch(e){}
  }

  function clearFieldError(el){
    try{
      if(!el) return;
      el.classList.remove('field-error');
      const next = el.nextSibling;
      if(next && next.classList && next.classList.contains && next.classList.contains('field-error-msg')){
        next.remove();
      }
    }catch(e){}
  }

  // Toast helpers
  function _ensureToastContainer(){
    let c = document.getElementById('toastContainer');
    if(!c){ c = document.createElement('div'); c.id = 'toastContainer'; c.className = 'toast-container'; document.body.appendChild(c); }
    return c;
  }

  function showToast(msg, type='info', timeout=4000){
    try{
      const c = _ensureToastContainer();
      const t = document.createElement('div'); t.className = 'toast '+(type||'info'); t.textContent = msg;
      c.appendChild(t);
      setTimeout(()=>{ try{ t.remove() }catch(e){} }, timeout);
      return t;
    }catch(e){ console.log('toast err', e) }
  }

  function clearToasts(){ try{ const c = document.getElementById('toastContainer'); if(c) c.innerHTML = ''; }catch(e){} }

  // Expose global handler for Telegram login widget
  window.onTelegramAuth = async function(user){
    try{
      // send user object to server /auth for verification
      const res = await fetch('/auth', { method: 'POST', headers: Object.assign({'Content-Type':'application/json'}, getAuthHeaders()), body: JSON.stringify(user) });
      if(!res.ok){ const t = await res.text(); showToast('Telegram auth failed: '+t,'error'); return }
      const j = await res.json();
      if(j && j.token){
        try{ localStorage.setItem('td_api_key', j.token); }catch(e){}
        showToast('Conectado vía Telegram','success');
        try{ await connect(); }catch(e){ /* ignore connect errors */ }
      } else {
        showToast('Autenticación Telegram: respuesta inválida','error');
      }
    }catch(e){ showToast('Error autenticando con Telegram: '+(e && e.message? e.message : e),'error') }
  }

  function initUI(){
    setInterval(()=>{ try{ pollAuthStatus() }catch(e){} }, 3000);

    // wire up connect toggle and api key save
    // populate saved api key
    try{ const kEl = document.getElementById('apiKey'); if(kEl) kEl.value = localStorage.getItem('td_api_key')||'' }catch(e){}
    try{ const saveKeyBtn = document.getElementById('saveKey'); if(saveKeyBtn) saveKeyBtn.addEventListener('click', ()=>{
      const vEl = document.getElementById('apiKey'); const v = vEl ? vEl.value.trim() : '';
      if(!v){ localStorage.removeItem('td_api_key'); showToast('API key removed','info'); } else { localStorage.setItem('td_api_key', v); showToast('API key saved','success'); }
    }); }catch(e){}

    // auth buttons
    try{ const aStart = document.getElementById('authStart'); if(aStart) aStart.addEventListener('click', startAuth); }catch(e){}
    try{ const aCheck = document.getElementById('authCheck'); if(aCheck) aCheck.addEventListener('click', checkAuth); }catch(e){}
    // overlay auth buttons
    try{ const aStartF = document.getElementById('authStartFull'); if(aStartF) aStartF.addEventListener('click', startAuth); }catch(e){}
    try{ const aCheckF = document.getElementById('authCheckFull'); if(aCheckF) aCheckF.addEventListener('click', checkAuth); }catch(e){}

    // clear field error when user types in phone inputs
    try{ const phone = document.getElementById('authPhone'); if(phone) phone.addEventListener('input', ()=> clearFieldError(phone)); }catch(e){}
    try{ const phoneF = document.getElementById('authPhoneFull'); if(phoneF) phoneF.addEventListener('input', ()=> clearFieldError(phoneF)); }catch(e){}

    // populate bot token from session/local storage
    try{
      const t = localStorage.getItem('td_bot_token') || sessionStorage.getItem('td_bot_token') || '';
      const botEl = document.getElementById('botToken'); if(botEl) botEl.value = t;
      if(t){ botToken = t; const rem = document.getElementById('rememberBot'); if(rem) rem.checked = !!localStorage.getItem('td_bot_token'); }
    }catch(e){}

    try{ const botTokenEl = document.getElementById('botToken'); if(botTokenEl) botTokenEl.addEventListener('change', (ev)=>{
      const v = ev.target.value.trim(); botToken = v || null;
      try{ const remember = document.getElementById('rememberBot'); if(remember && remember.checked){ if(v) localStorage.setItem('td_bot_token', v); else localStorage.removeItem('td_bot_token'); }
        else{ if(v) sessionStorage.setItem('td_bot_token', v); else sessionStorage.removeItem('td_bot_token'); } }catch(e){}
    }); }catch(e){}

    try{ const rememberEl = document.getElementById('rememberBot'); if(rememberEl) rememberEl.addEventListener('change', (ev)=>{
      const v = document.getElementById('botToken') ? document.getElementById('botToken').value.trim() : '';
      if(ev.target.checked){ if(v) localStorage.setItem('td_bot_token', v); sessionStorage.removeItem('td_bot_token'); }
      else{ if(v) sessionStorage.setItem('td_bot_token', v); localStorage.removeItem('td_bot_token'); }
    }); }catch(e){}

    // save bot token to server as a device (encrypted server-side)
    try{ const saveBotBtn = document.getElementById('saveBotServer'); if(saveBotBtn) saveBotBtn.addEventListener('click', async ()=>{
      const tokenEl = document.getElementById('botToken'); const token = tokenEl ? tokenEl.value.trim() : '';
      if(!token){ alert('Introduce un Bot token antes de guardar'); return }
      let id = null; try{ id = crypto.randomUUID(); }catch(e){ id = 'browser-'+Math.random().toString(36).slice(2,10); }
      const name = 'browser-saved-bot'; const payload = { id: id, token: token, name: name };
      try{
        const res = await fetch('/devices/add', { method: 'POST', headers: Object.assign({'Content-Type':'application/json'}, getAuthHeaders()), body: JSON.stringify(payload) });
        if(!res.ok){ const t = await res.text(); alert('Error guardando token en servidor: '+t); return }
        alert('Token guardado en servidor como device id: '+id);
        try{ localStorage.setItem('td_bot_device_id', id); }catch(e){}
      }catch(e){ alert('Error guardando token: '+e) }
    }); }catch(e){}

    try{ const btnConnect = document.getElementById('btnConnect'); if(btnConnect) btnConnect.addEventListener('click', ()=>{ if(isConnected) disconnect(); else connect(); }); }catch(e){}
    try{ const btnRefresh = document.getElementById('btnRefresh'); if(btnRefresh) btnRefresh.addEventListener('click', loadChats); }catch(e){}
    try{ const btnSend = document.getElementById('sendMsg'); if(btnSend) btnSend.addEventListener('click', sendMessage); }catch(e){}
    try{ const attachBtn = document.getElementById('attachBtn'); if(attachBtn) attachBtn.addEventListener('click', ()=>{ const f = document.getElementById('attachFile'); if(f) f.click(); }); }catch(e){}
    try{ const attachFile = document.getElementById('attachFile'); if(attachFile) attachFile.addEventListener('change', async (ev)=>{
      const f = ev.target.files && ev.target.files[0]; if(!f) return; showAttachmentPreview(f);
      const url = await uploadFile(f); if(url){ updateAttachmentPreviewWithUrl(url); }
    }); }catch(e){}

    // focus login inputs when overlay button clicked
    try{ const focusLogin = document.getElementById('focusLogin'); if(focusLogin) focusLogin.addEventListener('click', ()=>{ const el = document.getElementById('authPhoneFull') || document.getElementById('authPhone'); if(el) el.focus(); window.scrollTo({top:0,behavior:'smooth'}); }); }catch(e){}
    try{ const focusLoginFull = document.getElementById('focusLoginFull'); if(focusLoginFull) focusLoginFull.addEventListener('click', ()=>{ const el = document.getElementById('authPhoneFull') || document.getElementById('authPhone'); if(el) el.focus(); window.scrollTo({top:0,behavior:'smooth'}); }); }catch(e){}

    // global click delegation fallback for auth buttons (in case direct listeners fail)
    try{
      document.addEventListener('click', function(ev){
        const t = ev.target;
        if(!t) return;
        const btn = t.closest && t.closest('button') ? t.closest('button') : t;
        if(!btn || !btn.id) return;
        if(btn.id === 'authStart' || btn.id === 'authStartFull'){
          console.log('authStart delegated');
          ev.preventDefault(); startAuth();
        }
        if(btn.id === 'authCheck' || btn.id === 'authCheckFull'){
          console.log('authCheck delegated');
          ev.preventDefault(); checkAuth();
        }
      });
    }catch(e){}
  }
    
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initUI); else initUI();

  // initialize locked state (hidden after connected)
  try{ setLocked(!isConnected); }catch(e){}

  function showAttachmentPreview(file){
    clearAttachmentPreview();
    const container = document.getElementById('attachPreview');
    if(!container) return;
    const wrapper = document.createElement('div');
    wrapper.id = 'attach-preview-item';
    wrapper.style.display = 'flex';
    wrapper.style.alignItems = 'center';
    wrapper.style.gap = '8px';

    if(file.type && file.type.startsWith('image/')){
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      img.style.maxWidth = '120px';
      img.style.maxHeight = '80px';
      img.style.borderRadius = '6px';
      img.onload = ()=> { try{ URL.revokeObjectURL(img.src) }catch(e){} };
      wrapper.appendChild(img);
    }else{
      const ico = document.createElement('div');
      ico.textContent = '📎';
      ico.style.fontSize = '20px';
      wrapper.appendChild(ico);
      const nm = document.createElement('div');
      nm.textContent = file.name;
      wrapper.appendChild(nm);
    }

    const status = document.createElement('div');
    status.id = 'attach-status';
    status.textContent = 'Subiendo...';
    status.style.fontSize = '0.8rem';
    status.className = 'site-brand-sub';
    wrapper.appendChild(status);

    const remove = document.createElement('button');
    remove.className = 'btn ghost';
    remove.textContent = 'Quitar';
    remove.addEventListener('click', ()=> clearAttachmentPreview());
    wrapper.appendChild(remove);

    container.appendChild(wrapper);
  }

  function updateAttachmentPreviewWithUrl(url){
    const status = document.getElementById('attach-status');
    if(status) status.textContent = 'Subido';
    // store URL for send
    window._lastUploadedUrl = url;
    // add link
    const wrapper = document.getElementById('attach-preview-item');
    if(wrapper){
      const link = document.createElement('a');
      link.href = url;
      link.target = '_blank';
      link.textContent = 'Ver archivo';
      link.style.marginLeft = '6px';
      wrapper.appendChild(link);
    }
  }

  function clearAttachmentPreview(){
    window._lastUploadedUrl = null;
    const container = document.getElementById('attachPreview');
    if(!container) return;
    container.innerHTML = '';
  }
})();
