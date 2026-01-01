document.addEventListener('DOMContentLoaded', function(){
  const apiBaseEl = document.getElementById('apiBaseChat')
  const apiKeyEl = document.getElementById('apiKeyChat')
  const chatSelector = document.getElementById('chatSelector')
  const refreshChatsBtn = document.getElementById('refreshChats')
  const chatIdInput = document.getElementById('chatIdInput')
  const messagesEl = document.getElementById('messages')
  const composeEl = document.getElementById('compose')
  const sendBtn = document.getElementById('sendMessage')
  const clearBtn = document.getElementById('clearChat')
  const sendAsEl = document.getElementById('sendAsChat')
  const deviceSelect = document.getElementById('deviceSelectChat')

  let pollTimer = null

  // Spinner / cache helpers (safe to inject even if app.js already did)
  if(!document.getElementById('inlineSpinnerStyles')){
    const s = document.createElement('style')
    s.id = 'inlineSpinnerStyles'
    s.textContent = `
      .inline-spinner{display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,0.18);border-top-color:rgba(255,255,255,0.9);border-radius:50%;animation:spin 0.8s linear infinite;margin-right:8px}
      @keyframes spin{to{transform:rotate(360deg)}}
      .spinner-block{display:inline-flex;align-items:center}
    `
    document.head.appendChild(s)
  }
  const DEVICES_CACHE_KEY = 'devicesCache_v1'
  const CACHE_TTL = 60 * 1000
  function createSpinner(){ const sp = document.createElement('span'); sp.className='inline-spinner'; return sp }
  function getCachedDevices(){ try{ const raw = localStorage.getItem(DEVICES_CACHE_KEY); if(!raw) return null; const obj = JSON.parse(raw); if(!obj.ts || (Date.now() - obj.ts) > CACHE_TTL) return null; return obj.data }catch(e){ return null } }
  function setCachedDevices(data){ try{ localStorage.setItem(DEVICES_CACHE_KEY, JSON.stringify({ ts: Date.now(), data })) }catch(e){} }

  function headers(){ const h = {'Content-Type':'application/json'}; const k = (apiKeyEl && apiKeyEl.value)?apiKeyEl.value.trim():''; if(k) h['Authorization']='Bearer '+k; return h }

  async function fetchDevices(){
    const base = apiBaseEl.value.trim(); if(!base) return
    deviceSelect.innerHTML = '<option value="">(usar BOT_TOKEN)</option>'
    const cached = getCachedDevices()
    if(cached){
      cached.forEach(d=>{ const opt = document.createElement('option'); opt.value = d.id; opt.textContent = (d.name? d.name+' ('+d.id+')':d.id); deviceSelect.appendChild(opt) })
      // background refresh
      ;(async ()=>{
        try{
          const res = await fetch(base.replace(/\/$/, '') + '/devices', { headers: headers() })
          if(!res.ok) return
          const list = await res.json()
          setCachedDevices(list)
          // update ui if changed
          try{ if(JSON.stringify(list) !== JSON.stringify(cached)){
            deviceSelect.innerHTML = '<option value="">(usar BOT_TOKEN)</option>'
            list.forEach(d=>{ const opt = document.createElement('option'); opt.value = d.id; opt.textContent = (d.name? d.name+' ('+d.id+')':d.id); deviceSelect.appendChild(opt) })
          } }catch(e){}
        }catch(e){}
      })()
      return
    }
    try{
      const res = await fetch(base.replace(/\/$/, '') + '/devices', { headers: headers() })
      if(!res.ok) return
      const list = await res.json()
      setCachedDevices(list)
      deviceSelect.innerHTML = '<option value="">(usar BOT_TOKEN)</option>'
      list.forEach(d=>{ const opt = document.createElement('option'); opt.value = d.id; opt.textContent = d.name+' ('+d.id+')'; deviceSelect.appendChild(opt) })
    }catch(e){}
  }

  async function refreshChats(){
    // get messages, extract distinct chat ids
    const base = apiBaseEl.value.trim(); if(!base) return
    try{
      const res = await fetch(base.replace(/\/$/, '') + '/messages', { headers: headers() })
      if(!res.ok) return
      const arr = await res.json()
      const ids = [...new Set(arr.map(i=> (i && i.chat_id) ? i.chat_id : (i && i.from && i.from.id ? i.from.id : null)).filter(Boolean))]
      chatSelector.innerHTML = ''
      ids.forEach(id => { const o = document.createElement('option'); o.value = id; o.textContent = id; chatSelector.appendChild(o) })
    }catch(e){}
  }

  function renderMessages(arr, filterId){
    messagesEl.innerHTML = ''
    const list = (arr || []).filter(m=>{ if(!filterId) return true; return String(m.chat_id|| (m.to && m.to.id) || (m.from && m.from.id)) === String(filterId) })
    list.slice(-200).forEach(m=>{
      const d = document.createElement('div'); d.className = 'msg ' + (m.from && m.from.is_bot ? 'other' : 'me')
      d.innerHTML = `<div style="font-size:0.85rem;color:var(--muted)">${m.date ? new Date(m.date*1000).toLocaleTimeString():''} ${m.from && m.from.username ? m.from.username : ''}</div><div>${escapeHtml(m.text||m.content||JSON.stringify(m))}</div>`
      messagesEl.appendChild(d)
    })
    messagesEl.scrollTop = messagesEl.scrollHeight
  }

  function escapeHtml(s){ if(s==null) return ''; return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])) }

  async function poll(){
    const base = apiBaseEl.value.trim(); if(!base) return
    try{
      const res = await fetch(base.replace(/\/$/, '') + '/messages', { headers: headers() })
      if(!res.ok) return
      const arr = await res.json()
      renderMessages(arr, chatIdInput.value.trim() || chatSelector.value || null)
    }catch(e){ /* ignore */ }
  }

  // Render resources into the chat page dropdown
  async function renderChatResources(){
    const container = document.getElementById('chatResources')
    if(!container) return
    container.innerHTML = ''
    const base = apiBaseEl.value.trim()
    const endpoint = base || ''
    const apiDiv = document.createElement('div')
    apiDiv.style.marginBottom = '8px'
    apiDiv.innerHTML = `<div style="font-size:0.85rem;color:var(--muted)">API base:</div><div style="font-weight:600;word-break:break-all">${escapeHtml(endpoint)}</div>`
    container.appendChild(apiDiv)

    // devices (with spinner)
    const devHeader = document.createElement('div')
    devHeader.style.fontSize='0.85rem'; devHeader.style.color='var(--muted)'; devHeader.textContent='Dispositivos:'
    container.appendChild(devHeader)
    const devList = document.createElement('div')
    devList.style.display='flex'; devList.style.flexWrap='wrap'; devList.style.gap='6px'; devList.style.marginTop='6px'
    container.appendChild(devList)
    // show spinner while resolving cache/network
    const loader = document.createElement('div'); loader.className='spinner-block'; loader.appendChild(createSpinner()); const lt = document.createElement('div'); lt.style.color='var(--muted)'; lt.textContent='Cargando dispositivos...'; loader.appendChild(lt); devList.appendChild(loader)
    try{
      const cached = getCachedDevices()
      if(cached && cached.length>0){
        // populate from cache immediately
        devList.removeChild(loader)
        cached.slice(0,8).forEach(d=>{
          const b = document.createElement('button')
          b.className='secondary'
          b.textContent = (d.name? d.name+' ('+ (d.id||'') +')' : (d.id||'unnamed'))
          b.addEventListener('click', ()=>{ deviceSelect.value = d.id || ''; deviceSelect.dispatchEvent(new Event('change')) })
          devList.appendChild(b)
        })
        // background refresh
        ;(async ()=>{
          try{ const res = await fetch(base.replace(/\/$/, '') + '/devices', { headers: headers() }); if(res.ok){ const list = await res.json(); setCachedDevices(list); if(JSON.stringify(list)!==JSON.stringify(cached)){ devList.innerHTML=''; list.slice(0,8).forEach(d=>{ const b=document.createElement('button'); b.className='secondary'; b.textContent=(d.name? d.name+' ('+(d.id||'')+')':(d.id||'unnamed')); b.addEventListener('click', ()=>{ deviceSelect.value=d.id||''; deviceSelect.dispatchEvent(new Event('change')) }); devList.appendChild(b) }) } } }catch(e){}
        })()
      } else {
        const res = await fetch(base.replace(/\/$/, '') + '/devices', { headers: headers() })
        devList.removeChild(loader)
        if(res.ok){
          const list = await res.json()
          if(list.length===0){ const p = document.createElement('div'); p.style.color='var(--muted)'; p.textContent='(no hay dispositivos)'; devList.appendChild(p) }
          list.slice(0,8).forEach(d=>{
            const b = document.createElement('button')
            b.className='secondary'
            b.textContent = (d.name? d.name+' ('+ (d.id||'') +')' : (d.id||'unnamed'))
            b.addEventListener('click', ()=>{ deviceSelect.value = d.id || ''; deviceSelect.dispatchEvent(new Event('change')) })
            devList.appendChild(b)
          })
          setCachedDevices(list)
        } else {
          const p = document.createElement('div'); p.style.color='var(--muted)'; p.textContent='(no disponible)'; devList.appendChild(p)
        }
      }
    }catch(e){ try{ devList.removeChild(loader) }catch(_){} const p = document.createElement('div'); p.style.color='var(--muted)'; p.textContent='(error al cargar)'; devList.appendChild(p) }

    // pages
    const pagesHeader = document.createElement('div')
    pagesHeader.style.fontSize='0.85rem'; pagesHeader.style.color='var(--muted)'; pagesHeader.style.marginTop='10px'; pagesHeader.textContent='Páginas:'
    container.appendChild(pagesHeader)
    const pagesWrap = document.createElement('div')
    pagesWrap.style.display='flex'; pagesWrap.style.flexWrap='wrap'; pagesWrap.style.gap='6px'; pagesWrap.style.marginTop='6px'
    // try dynamic pages list
    let pages = []
    try{ const r = await fetch('pages.json'); if(r.ok) pages = await r.json() }catch(e){}
    if(!pages || !Array.isArray(pages) || pages.length===0) pages = [ { href:'index.html', label:'Inicio' }, { href:'chat.html', label:'Chat' }, { href:'monitor.html', label:'Monitor' }, { href:'wsl_install.html', label:'WSL' } ]
    pages.forEach(p=>{
      const a = document.createElement('a'); a.href = p.href; a.textContent = p.label; a.className='secondary'; a.style.display='inline-block'; a.style.padding='6px 8px'; a.target='_blank'
      // prefetch
      try{ if(!document.querySelector('link[rel="prefetch"][href="'+p.href+'"]')){ const l=document.createElement('link'); l.rel='prefetch'; l.href=p.href; document.head.appendChild(l) } }catch(e){}
      pagesWrap.appendChild(a)
    })
    container.appendChild(pagesWrap)

    // quick actions
    const act = document.createElement('div'); act.style.marginTop='10px'; act.innerHTML = '<button id="openChatBtnInline" class="secondary">Abrir chat</button> <button id="openMonBtnInline" class="secondary">Abrir monitor</button> <button id="dlSettingsInline" class="secondary">Descargar settings</button>'
    container.appendChild(act)
    document.getElementById('openChatBtnInline')?.addEventListener('click', ()=>{ window.location.href='chat.html' })
    document.getElementById('openMonBtnInline')?.addEventListener('click', ()=>{ window.location.href='monitor.html' })
    document.getElementById('dlSettingsInline')?.addEventListener('click', ()=>{ document.getElementById('downloadSettings')?.click() })
  }

  // Toggle inline resources panel
  const toggleBtn = document.getElementById('toggleChatResources')
  toggleBtn && toggleBtn.addEventListener('click', async ()=>{
    const box = document.getElementById('chatResources')
    if(!box) { console.warn('chatResources container not found'); return }
    try{
      if(box.style.display === 'none' || box.style.display === ''){
        box.style.display = 'block'
        box.innerHTML = '<div style="color:var(--muted)">Cargando recursos...</div>'
        await renderChatResources()
      } else {
        box.style.display = 'none'
      }
    }catch(err){
      console.error('Error renderChatResources', err)
      box.style.display = 'block'
      box.innerHTML = '<div style="color:var(--muted)">Error cargando recursos</div>'
    }
  })

  refreshChatsBtn.addEventListener('click', ()=>refreshChats())

  chatSelector.addEventListener('change', ()=>{ chatIdInput.value = chatSelector.value; poll() })

  sendBtn.addEventListener('click', async ()=>{
    const base = apiBaseEl.value.trim(); if(!base) { alert('Introduce API base'); return }
    const chatId = chatIdInput.value.trim(); if(!chatId){ alert('Introduce chat id'); return }
    const text = composeEl.value.trim(); if(!text){ alert('Escribe un mensaje'); return }
    const sendAs = sendAsEl.value
    const headersObj = headers()
    let url = ''
    let body = {}
    if(sendAs === 'user'){
      url = base.replace(/\/$/, '') + '/send_user'
      body = { chat_id: chatId, text: text }
      if(deviceSelect && deviceSelect.value) body.device_id = deviceSelect.value
    } else {
      url = base.replace(/\/$/, '') + '/send'
      body = { chat_id: chatId, text: text }
      if(deviceSelect && deviceSelect.value) body.device_id = deviceSelect.value
    }
    try{
      const res = await fetch(url, { method:'POST', headers: headersObj, body: JSON.stringify(body) })
      if(!res.ok){ alert('Error: '+res.status+' '+await res.text()); return }
      composeEl.value = ''
      // immediate poll to show message
      poll()
    }catch(e){ alert('Error: '+e.toString()) }
  })

  if (clearBtn && typeof clearBtn.addEventListener === 'function') {
    clearBtn.addEventListener('click', ()=>{ messagesEl.innerHTML = ''; composeEl.value = '' })
  } else {
    console.warn('clearBtn missing or not an element:', clearBtn)
  }

  // start polling
  (async ()=>{ await fetchDevices(); await refreshChats(); poll(); pollTimer = setInterval(poll, 1500) })()

  // Settings panel handlers
  try{
    const btnSettings = document.getElementById('btnSettings');
    const settingsPanel = document.getElementById('settingsPanel');
    const closeSettings = document.getElementById('closeSettings');
    const saveRolesBtn = document.getElementById('saveRolesBtn');
    const clearRolesBtn = document.getElementById('clearRolesBtn');
    if(btnSettings && settingsPanel){ btnSettings.addEventListener('click', ()=>{
        // open modal: remove hidden + aria-hidden, remove inert, focus first tab
        settingsPanel.classList.remove('hidden');
        settingsPanel.setAttribute('aria-hidden','false');
        settingsPanel.removeAttribute('inert');
        try{ loadSettingsUI(); }catch(_){}
        try{ const t = document.getElementById('tabRoles'); if(t) t.focus(); }catch(_){}
      }); }
    if(closeSettings && settingsPanel){ closeSettings.addEventListener('click', ()=>{
        // if a descendant is focused, move focus to the opener before hiding
        try{
          const active = document.activeElement;
          if(active && settingsPanel.contains(active)){
            try{ active.blur(); }catch(_){}
            try{ btnSettings && btnSettings.focus(); }catch(_){}
          }
        }catch(_){}
        settingsPanel.classList.add('hidden');
        settingsPanel.setAttribute('aria-hidden','true');
        // mark inert so assistive tech sees it as non-interactive
        try{ settingsPanel.setAttribute('inert',''); }catch(_){}
      }); }
    if(saveRolesBtn){ saveRolesBtn.addEventListener('click', saveRoles); }
    if(clearRolesBtn){ clearRolesBtn.addEventListener('click', clearRoles); }
  }catch(e){}

  // Bot verification and import helpers
  async function verifyBotToken(token, device_id, name){
    const base = apiBaseEl.value.trim(); if(!base) throw new Error('API base not set')
    const url = base.replace(/\/$/, '') + '/bot/verify'
    const body = { token: token }
    if(device_id) body.id = device_id
    if(name) body.name = name
    const res = await fetch(url, { method:'POST', headers: headers(), body: JSON.stringify(body) })
    if(!res.ok){ const t = await res.text(); throw new Error('verify failed: '+t) }
    return await res.json()
  }

  async function importBotData(){
    const base = apiBaseEl.value.trim(); if(!base) throw new Error('API base not set')
    const url = base.replace(/\/$/, '') + '/bot/data'
    const res = await fetch(url, { headers: headers() })
    if(!res.ok){ const t = await res.text(); throw new Error('import failed: '+t) }
    return await res.json()
  }

  // Wire optional verify form if present in the page
  try{
    const verifyForm = document.getElementById('verifyTokenForm')
    if(verifyForm){
      verifyForm.addEventListener('submit', async (ev)=>{
        ev.preventDefault()
        const tokEl = document.getElementById('verifyTokenInput')
        const idEl = document.getElementById('verifyDeviceId')
        const nameEl = document.getElementById('verifyDeviceName')
        const token = tokEl ? tokEl.value.trim() : ''
        if(!token){ alert('Introduce el token del bot'); return }
        try{
          const sp = createSpinner(); tokEl.parentNode && tokEl.parentNode.appendChild(sp)
          const v = await verifyBotToken(token, idEl && idEl.value.trim(), nameEl && nameEl.value.trim())
          alert('Bot verificado y device registrado: ' + (v.device && v.device.id ? v.device.id : 'ok'))
          // then import data and show counts
          try{
            const data = await importBotData()
            console.log('Imported bot data', data)
            alert('Importado: ' + (data.infohashes ? data.infohashes.length : 0) + ' infohashes, ' + Object.keys(data.allowed_senders || {}).length + ' chats con allowed_senders')
          }catch(e){ console.error('import error', e); alert('Import failed: '+e.message) }
        }catch(e){ alert('Verify error: '+e.message) }
        try{ tokEl.parentNode && tokEl.parentNode.removeChild(tokEl.parentNode.querySelector('.inline-spinner')) }catch(_){}
      })
    }
      const importBtn = document.getElementById('importDataBtn')
      if(importBtn){ importBtn.addEventListener('click', async ()=>{
        try{
          const data = await importBotData()
          console.log('Imported bot data', data)
          alert('Importado: ' + (data.infohashes ? data.infohashes.length : 0) + ' infohashes, ' + Object.keys(data.allowed_senders || {}).length + ' chats con allowed_senders')
        }catch(e){ alert('Import failed: '+(e.message||e)) }
      }) }
  }catch(e){}

  function loadSettingsUI(){
    try{
      const owner = localStorage.getItem('bot_owner') || '';
      const admins = localStorage.getItem('bot_admins') || '';
      const ownerEl = document.getElementById('ownerInput'); if(ownerEl) ownerEl.value = owner;
      const adminsEl = document.getElementById('adminsInput'); if(adminsEl) adminsEl.value = admins;
      const features = [
        'Creación de estructura de torrents y descarga de covers (scripts/create_torrent_structure.py)',
        'Extracción de metadatos e infohash desde .torrent (bencode fallback)',
        'Integración en el bot: procesado de .torrent y almacenamiento de infohash',
        'Persistencia de infohashes en storage (`projects/bot/python_bot/storage.py`)',
        'Comandos `/allow_send` y `/disallow_send` y control por chat',
        'Guardado de Bot token como device en servidor (`/devices/add`)',
        'Enlaces en la web: botón "Abrir bot" y link a `telegram.html` en navegación',
        'Enforcement de permisos (envío privado si no autorizado)'
      ];
      const list = document.getElementById('featuresList'); if(list){ list.innerHTML = ''; features.forEach(f=>{ const d = document.createElement('div'); d.style.marginBottom='6px'; d.textContent = '• ' + f; list.appendChild(d); }); }
    }catch(e){}
  }

  function saveRoles(){
    try{
      const owner = (document.getElementById('ownerInput')||{}).value || '';
      const admins = (document.getElementById('adminsInput')||{}).value || '';
      localStorage.setItem('bot_owner', owner.trim());
      localStorage.setItem('bot_admins', admins.trim());
      alert('Roles guardados en localStorage');
    }catch(e){ alert('Error guardando roles') }
  }

  function clearRoles(){
    try{ localStorage.removeItem('bot_owner'); localStorage.removeItem('bot_admins'); loadSettingsUI(); alert('Roles borrados'); }catch(e){ alert('Error borrando roles') }
  }

  // Tabs and explain content logic
  try{
    const tabRoles = document.getElementById('tabRoles');
    const tabExplain = document.getElementById('tabExplain');
    const rolesContent = document.getElementById('rolesContent');
    const explainContent = document.getElementById('explainContent');
    const explainList = document.getElementById('explainList');
    const restoreChatBtn = document.getElementById('restoreChatBtn');
    const chatWrap = document.querySelector('.chat-wrap');
    function showRolesTab(){ if(tabRoles) tabRoles.classList.remove('ghost'); if(tabExplain) tabExplain.classList.add('ghost'); if(rolesContent) rolesContent.style.display='block'; if(explainContent) explainContent.style.display='none'; if(chatWrap) chatWrap.style.display='flex'; }
    function showExplainTab(){ if(tabExplain) tabExplain.classList.remove('ghost'); if(tabRoles) tabRoles.classList.add('ghost'); if(rolesContent) rolesContent.style.display='none'; if(explainContent) explainContent.style.display='block'; if(chatWrap) chatWrap.style.display='none'; }
    if(tabRoles) tabRoles.addEventListener('click', showRolesTab);
    if(tabExplain) tabExplain.addEventListener('click', ()=>{
      try{
        // Find the modal element at click time to avoid block-scope issues
        const sp = document.getElementById('settingsPanel');
        if(sp){
          if(sp.classList.contains('hidden')){
            sp.classList.remove('hidden');
            sp.setAttribute('aria-hidden','false');
            try{ if(typeof loadSettingsUI !== 'undefined') loadSettingsUI(); }catch(_){}
          }
        }
        loadExplanation();
        showExplainTab();
      }catch(e){
        console.error('Error opening Explicación tab', e)
        try{ alert('Error al abrir Explicación: '+(e && e.message?e.message:e)) }catch(_){}
      }
    });
    if(restoreChatBtn) restoreChatBtn.addEventListener('click', ()=>{ if(chatWrap) chatWrap.style.display='flex'; showRolesTab(); });

    function loadExplanation(){
      if(!explainList) return;
      explainList.innerHTML = '';
      const cmdsEl = document.getElementById('commandsList');
      if(cmdsEl){
        cmdsEl.innerHTML = '';
        const cmds = [
          {cmd: '/start', desc: 'Inicia la interacción con el bot y muestra ayuda básica.'},
          {cmd: '/help', desc: 'Muestra ayuda y una lista de comandos disponibles.'},
          {cmd: '/allow_send <chat_id>', desc: 'Permite que el origen envíe contenido a este chat.'},
          {cmd: '/disallow_send <chat_id>', desc: 'Revoca permiso para que el origen envíe al chat.'},
          {cmd: '/list_infohashes', desc: 'Muestra infohashes registrados por el bot.'},
          {cmd: '/my_id', desc: 'Devuelve tu user id (útil para configurar roles).'}
        ];
        cmds.forEach(c=>{ const row = document.createElement('div'); row.style.marginBottom='8px'; row.innerHTML = `<code style="font-weight:700">${c.cmd}</code><div class="site-brand-sub" style="margin-top:4px">${c.desc}</div>`; cmdsEl.appendChild(row); });
      }
      const items = [
        {title: 'Estructura de torrents', desc: 'Crea carpetas, metadata y descarga cover desde OpenLibrary/TMDb.'},
        {title: 'Extracción de metadatos', desc: 'Se obtiene infohash y lista de archivos desde el .torrent (bencode fallback).'},
        {title: 'Integración bot', desc: 'Al recibir .torrent el bot crea la estructura y guarda infohash en storage.'},
        {title: 'Persistencia', desc: 'Infohashes y permisos se guardan en storage (Redis o fallback en memoria).'},
        {title: 'Permisos', desc: 'Comandos `/allow_send` y `/disallow_send` controlan quién puede recibir envíos.'},
        {title: 'Seguridad', desc: 'Tokens de bot pueden guardarse como devices en el servidor (encriptados).'}
      ];
      items.forEach(it=>{ const d = document.createElement('div'); d.style.marginBottom='10px'; d.innerHTML = `<strong>${it.title}</strong><div class="site-brand-sub" style="margin-top:4px">${it.desc}</div>`; explainList.appendChild(d); });
    }
  }catch(e){}

})
