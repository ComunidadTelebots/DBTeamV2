document.addEventListener('DOMContentLoaded', function(){
  // Apply saved theme (owner_color) to this page immediately
  try{
    const owner = localStorage.getItem('owner_color') || null;
    if(owner){
      document.documentElement.style.setProperty('--owner-color', owner);
      document.documentElement.style.setProperty('--accent', owner);
      document.documentElement.style.setProperty('--bubble-me-bg', `linear-gradient(180deg, ${owner}, #1e6ed8)`);
    }
  }catch(e){}
  const apiBaseEl = document.getElementById('apiBase')
  const verifyForm = document.getElementById('verifyTokenForm')
  const verifyTokenInput = document.getElementById('verifyTokenInput')
  const importBtn = document.getElementById('importDataBtn')
  const infohashesList = document.getElementById('infohashesList')
  const allowedSendersList = document.getElementById('allowedSendersList')
  const importSummary = document.getElementById('importSummary')
  const botSummary = document.getElementById('botSummary')
  const botPhoto = document.getElementById('botPhoto')
  const botName = document.getElementById('botName')
  const botExtra = document.getElementById('botExtra')
  const botStats = document.getElementById('botStats')
  const devicesList = document.getElementById('devicesList')
  const configuredBotsList = document.getElementById('configuredBotsList')
  const apiStatusList = document.getElementById('apiStatusList')
  const svcStartBtn = document.getElementById('svcStartBtn')
  const svcStopBtn = document.getElementById('svcStopBtn')
  const svcRestartBtn = document.getElementById('svcRestartBtn')
  const localModelInput = document.getElementById('localModelInput')
  const installModelBtn = document.getElementById('installModelBtn')
  const refreshModelsBtn = document.getElementById('refreshModelsBtn')
  const localModelsList = document.getElementById('localModelsList')
  const modelPromptInput = document.getElementById('modelPromptInput')
  const runModelBtn = document.getElementById('runModelBtn')
  const addCfgBotBtn = document.getElementById('addCfgBotBtn')
  const refreshBotsBtn = document.getElementById('refreshBotsBtn')
  const cfgBotName = document.getElementById('cfgBotName')
  const cfgBotApiBase = document.getElementById('cfgBotApiBase')
  const cfgBotToken = document.getElementById('cfgBotToken')
  const ownerInput = document.getElementById('ownerInput')
  const adminsInput = document.getElementById('adminsInput')
  const saveRolesBtn = document.getElementById('saveRolesBtn')
  const clearRolesBtn = document.getElementById('clearRolesBtn')
  const commandsList = document.getElementById('commandsList')
  const listFilesBtn = document.getElementById('listFilesBtn')
  const filesLimit = document.getElementById('filesLimit')
  const uploadedFilesList = document.getElementById('uploadedFilesList')

  function headers(){ const h = {'Content-Type':'application/json'}; return h }
  function getApiBase(){
    const v = (apiBaseEl && apiBaseEl.value) ? apiBaseEl.value.trim() : ''
    if(v) return v.replace(/\/$/, '')
    // fallback to localhost API for convenience
    return 'http://127.0.0.1:8000'
  }

  // Persist and autocomplete API base
  const API_BASE_KEY = 'bot_api_base'
  const API_BASE_HISTORY_KEY = 'bot_api_base_history'
  function loadApiBaseHistory(){
    const list = document.getElementById('apiBaseList')
    if(!list) return
    list.innerHTML = ''
    const defaults = ['http://127.0.0.1:8000','http://localhost:8000','http://0.0.0.0:8000','https://cas.chat']
    let hist = []
    try{ hist = JSON.parse(localStorage.getItem(API_BASE_HISTORY_KEY) || '[]') }catch(e){ hist = [] }
    const combined = Array.from(new Set([...(hist || []), ...defaults]))
    combined.forEach(v=>{ const o = document.createElement('option'); o.value = v; list.appendChild(o) })
  }
  function saveApiBaseToHistory(val){
    if(!val) return
    let hist = []
    try{ hist = JSON.parse(localStorage.getItem(API_BASE_HISTORY_KEY) || '[]') }catch(e){ hist = [] }
    hist = hist.filter(x=>x && x !== val)
    hist.unshift(val)
    hist = hist.slice(0,10)
    try{ localStorage.setItem(API_BASE_HISTORY_KEY, JSON.stringify(hist)) }catch(e){}
    loadApiBaseHistory()
  }
  // initialize apiBase input from localStorage
  try{ const saved = localStorage.getItem(API_BASE_KEY); if(saved && apiBaseEl) apiBaseEl.value = saved }catch(e){}
  loadApiBaseHistory()
  if(apiBaseEl){ apiBaseEl.addEventListener('blur', ()=>{ try{ const v = apiBaseEl.value && apiBaseEl.value.trim(); if(v){ localStorage.setItem(API_BASE_KEY, v); saveApiBaseToHistory(v) } }catch(e){} }) }

  // Attempt to load env tokens provided by the local server for convenience
  (async function(){
    try{
      const r = await fetch('env_tokens.json')
      if(r.ok){
        const env = await r.json()
        // prefill verify token input if empty
        try{ if(env.BOT_TOKEN && verifyTokenInput && !verifyTokenInput.value) verifyTokenInput.value = env.BOT_TOKEN }catch(e){}
        // prefill configured bot token input if empty
        try{ if(env.BOT_TOKEN && cfgBotToken && !cfgBotToken.value) cfgBotToken.value = env.BOT_TOKEN }catch(e){}
        // if API_BASE present and apiBase input empty, fill it
        try{ if(env.API_BASE && apiBaseEl && !apiBaseEl.value) apiBaseEl.value = env.API_BASE }catch(e){}
      }
    }catch(e){ /* ignore */ }
  })()

  async function verifyBotToken(token){
    const base = getApiBase()
    const res = await fetch(base + '/bot/verify', { method:'POST', headers: headers(), body: JSON.stringify({ token: token }) })
    if(!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  function renderBotSummary(getMe, photo_url, extraCounts){
    try{
      if(photo_url){ botPhoto.src = photo_url; botPhoto.style.display = 'block' } else { botPhoto.style.display = 'none' }
      if(getMe){
        const name = getMe.first_name || getMe.username || getMe.title || '(sin nombre)'
        const uname = getMe.username ? '@'+getMe.username : ''
        botName.textContent = name + (uname ? ' '+uname : '')
        botExtra.textContent = 'ID: ' + (getMe.id || '-')
      } else {
        botName.textContent = '(no verificado)'
        botExtra.textContent = 'ID: -'
      }
      if(extraCounts){
        botStats.textContent = `Chats activos: ${extraCounts.chats || 0} · Infohashes: ${extraCounts.infohashes || 0}`
      }
    }catch(e){ /* ignore */ }
  }

  async function importBotData(){
    const base = getApiBase()
    const res = await fetch(base + '/bot/data', { headers: headers() })
    if(!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  async function fetchDevices(){
    const base = getApiBase()
    try{ const res = await fetch(base + '/devices', { headers: headers() }); if(!res.ok) return []; return await res.json() }catch(e){ return [] }
  }

  // --- Services status monitoring ---
  // We'll check the API /status and show semaphore indicators for important services.
  function makeIndicator(name, status){
    const row = document.createElement('div'); row.style.display='flex'; row.style.alignItems='center'; row.style.justifyContent='space-between'; row.style.marginBottom='8px'
    const left = document.createElement('div'); left.style.display='flex'; left.style.alignItems='center'; left.style.gap='10px'
    const dot = document.createElement('div'); dot.style.width='14px'; dot.style.height='14px'; dot.style.borderRadius='10px';
    if(status === 'ok') dot.style.background='green'; else if(status === 'warn') dot.style.background='orange'; else dot.style.background='red'
    const label = document.createElement('div'); label.textContent = name
    left.appendChild(dot); left.appendChild(label)
    const right = document.createElement('div'); right.style.color='var(--muted)'
    right.textContent = status
    row.appendChild(left); row.appendChild(right)
    return row
  }

  async function refreshApiStatus(){
    apiStatusList && (apiStatusList.innerHTML = '')
    const base = getApiBase()
    // check /status
    try{
      const r = await fetch(base + '/status')
      if(r.ok){
        const js = await r.json()
        apiStatusList.appendChild(makeIndicator('Web API', 'ok'))
        // processes: show python_bot state
        try{
          const proc = (js.processes || []).find(p=>p.name === 'python_bot')
          if(proc){ apiStatusList.appendChild(makeIndicator('Python Bot (python_bot)', proc.running ? 'ok' : 'red')) }
        }catch(e){}
        // redis
        try{ apiStatusList.appendChild(makeIndicator('Redis', js.redis && js.redis.ok ? 'ok' : 'red')) }catch(e){}
        // tor
        try{ apiStatusList.appendChild(makeIndicator('Tor (SOCKS5)', js.tor && js.tor.socks_ok ? 'ok' : 'red')) }catch(e){}
      } else {
        apiStatusList.appendChild(makeIndicator('Web API', 'red'))
      }
    }catch(e){ if(apiStatusList) apiStatusList.appendChild(makeIndicator('Web API', 'red')) }
  }

  // control buttons: start/stop/restart python_bot via /processes endpoints
  async function callProcessAction(action, name){
    const base = getApiBase()
    const url = base + (action === 'restart' ? '/processes/restart' : (action === 'start' ? '/processes/start' : '/processes/stop'))
    try{
      const res = await fetch(url, { method: 'POST', headers: headers(), body: JSON.stringify({ name: name }) })
      if(!res.ok){ const t = await res.text(); throw new Error(t || res.statusText) }
      return await res.json()
    }catch(e){ throw e }
  }

  svcStartBtn && svcStartBtn.addEventListener('click', async ()=>{
    try{ svcStartBtn.disabled = true; const r = await callProcessAction('start','python_bot'); alert('Start: '+JSON.stringify(r)); await refreshApiStatus(); }catch(e){ alert('Error start: '+(e.message||e)) } finally{ svcStartBtn.disabled = false }
  })
  svcStopBtn && svcStopBtn.addEventListener('click', async ()=>{
    if(!confirm('Detener python_bot?')) return
    try{ svcStopBtn.disabled = true; const r = await callProcessAction('stop','python_bot'); alert('Stop: '+JSON.stringify(r)); await refreshApiStatus(); }catch(e){ alert('Error stop: '+(e.message||e)) } finally{ svcStopBtn.disabled = false }
  })
  svcRestartBtn && svcRestartBtn.addEventListener('click', async ()=>{
    try{ svcRestartBtn.disabled = true; const r = await callProcessAction('restart','python_bot'); alert('Restart: '+JSON.stringify(r)); await refreshApiStatus(); }catch(e){ alert('Error restart: '+(e.message||e)) } finally{ svcRestartBtn.disabled = false }
  })

  // poll status periodically
  setInterval(refreshApiStatus, 5000)
  // initial
  try{ refreshApiStatus() }catch(e){}
  // models
  async function fetchLocalModels(){
    try{
      const base = getApiBase()
      const r = await fetch(base + '/models/list')
      if(!r.ok) throw new Error('no models')
      const js = await r.json()
      const arr = js.models || []
      localModelsList.innerHTML = ''
      if(arr.length === 0){ localModelsList.textContent='(no hay modelos instalados)'; return }
      arr.forEach(m=>{
        const row = document.createElement('div'); row.style.display='flex'; row.style.justifyContent='space-between'; row.style.alignItems='center'; row.style.marginBottom='6px'
        const name = document.createElement('div'); name.textContent = m; name.style.flex='1'
        const runBtn = document.createElement('button'); runBtn.className='btn ghost'; runBtn.textContent='Run'; runBtn.addEventListener('click', async ()=>{
          try{
            const prompt = modelPromptInput.value && modelPromptInput.value.trim()
            if(!prompt){ alert('Introduce prompt de prueba'); return }
            const res = await fetch(getApiBase() + '/models/run', { method:'POST', headers: headers(), body: JSON.stringify({ model: m, prompt: prompt }) })
            if(!res.ok){ const t = await res.text(); throw new Error(t||res.statusText) }
            const out = await res.json(); alert('Result: '+JSON.stringify(out.result||out))
          }catch(e){ alert('Error: '+(e.message||e)) }
        })
        row.appendChild(name); row.appendChild(runBtn); localModelsList.appendChild(row)
      })
    }catch(e){ localModelsList.textContent='(no disponible)'; }
  }

  installModelBtn && installModelBtn.addEventListener('click', async ()=>{
    const m = localModelInput && localModelInput.value && localModelInput.value.trim()
    if(!m){ alert('Introduce nombre de modelo'); return }
    try{
      installModelBtn.disabled = true
      const res = await fetch(getApiBase() + '/models/install', { method:'POST', headers: headers(), body: JSON.stringify({ model: m }) })
      if(!res.ok){ const t = await res.text(); throw new Error(t||res.statusText) }
      alert('Instalación iniciada: '+m)
      localModelInput.value = ''
      await fetchLocalModels()
    }catch(e){ alert('Error instalando: '+(e.message||e)) } finally{ installModelBtn.disabled = false }
  })

  refreshModelsBtn && refreshModelsBtn.addEventListener('click', ()=>{ fetchLocalModels() })
  runModelBtn && runModelBtn.addEventListener('click', async ()=>{
    const model = (localModelsList.firstChild && localModelsList.firstChild.textContent) || (localModelInput && localModelInput.value && localModelInput.value.trim())
    const prompt = modelPromptInput && modelPromptInput.value && modelPromptInput.value.trim()
    if(!model || !prompt){ alert('Modelo y prompt requeridos'); return }
    try{
      runModelBtn.disabled = true
      const res = await fetch(getApiBase() + '/models/run', { method:'POST', headers: headers(), body: JSON.stringify({ model: model, prompt: prompt }) })
      if(!res.ok){ const t = await res.text(); throw new Error(t||res.statusText) }
      const out = await res.json()
      alert('Result: '+JSON.stringify(out.result||out))
    }catch(e){ alert('Error ejecutando: '+(e.message||e)) } finally{ runModelBtn.disabled = false }
  })

  // initial models fetch
  try{ fetchLocalModels() }catch(e){}

  async function listBotFiles(token, limit){
    const base = getApiBase()
    const res = await fetch(base + '/bot/files', { method: 'POST', headers: headers(), body: JSON.stringify({ token: token, limit: limit || 50 }) })
    if(!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  function renderUploadedFiles(files){
    uploadedFilesList.innerHTML = ''
    if(!files || files.length===0){ uploadedFilesList.textContent='(no hay archivos detectados)'; return }
    files.forEach(f=>{
      const box = document.createElement('div')
      box.style.display='flex'; box.style.gap='8px'; box.style.marginBottom='8px'; box.style.alignItems='center'
      const thumb = document.createElement('div')
      if(f.type === 'photo' && f.file_url){ const img = document.createElement('img'); img.src = f.file_url; img.style.width='64px'; img.style.height='64px'; img.style.objectFit='cover'; img.style.borderRadius='6px'; thumb.appendChild(img) }
      else { const ic = document.createElement('div'); ic.textContent = f.type || 'file'; ic.style.width='64px'; ic.style.height='64px'; ic.style.display='flex'; ic.style.alignItems='center'; ic.style.justifyContent='center'; ic.style.background='var(--muted)'; ic.style.color='white'; ic.style.borderRadius='6px'; thumb.appendChild(ic) }
      box.appendChild(thumb)
      const meta = document.createElement('div')
      const title = document.createElement('div'); title.style.fontWeight='700'; title.textContent = f.file_name || (f.file_id||'file')
      const sub = document.createElement('div'); sub.style.color='var(--muted)'; sub.style.fontSize='0.9rem'; sub.textContent = `chat: ${f.chat_id} · ${f.type || ''}`
      meta.appendChild(title); meta.appendChild(sub)
      if(f.file_url){ const a = document.createElement('a'); a.href = f.file_url; a.target='_blank'; a.textContent='Abrir'; a.style.marginLeft='8px'; meta.appendChild(a) }
      box.appendChild(meta)
      uploadedFilesList.appendChild(box)
    })
  }

  function renderCommands(){
    const cmds = [
      {cmd:'/start', desc:'Inicia interacción con el bot'},
      {cmd:'/help', desc:'Muestra ayuda'},
      {cmd:'/allow_send <chat_id>', desc:'Permite al origen enviar a este chat'},
      {cmd:'/disallow_send <chat_id>', desc:'Revoca permiso'},
      {cmd:'/list_infohashes', desc:'Lista infohashes conocidos'},
      {cmd:'/my_id', desc:'Muestra tu user id'}
    ]
    commandsList.innerHTML = ''
    cmds.forEach(c=>{ const d=document.createElement('div'); d.style.marginBottom='8px'; d.innerHTML = `<strong>${c.cmd}</strong><div style="color:var(--muted);font-size:0.95rem">${c.desc}</div>`; commandsList.appendChild(d) })
  }

  function showInfohashes(arr){ infohashesList.innerHTML = ''; if(!arr || arr.length===0){ infohashesList.textContent = '(no hay infohashes)'; return } arr.forEach(h=>{ const d=document.createElement('div'); d.textContent = h; d.style.padding='4px 0'; infohashesList.appendChild(d) }) }
  function showAllowedSenders(obj){ allowedSendersList.innerHTML=''; const keys = Object.keys(obj||{}); if(keys.length===0){ allowedSendersList.textContent='(no hay allowed_senders)'; return } keys.forEach(chatid=>{ const box = document.createElement('div'); box.style.marginBottom='8px'; const title = document.createElement('div'); title.style.fontWeight='700'; title.textContent = 'Chat: '+chatid; box.appendChild(title); const v = obj[chatid] || []; const list = document.createElement('div'); list.style.color='var(--muted)'; list.textContent = v.join(', '); box.appendChild(list); allowedSendersList.appendChild(box) }) }

  async function refreshAll(){
    try{
      const data = await importBotData();
      showInfohashes(data.infohashes || [])
      showAllowedSenders(data.allowed_senders || {})
      const chatsCount = Object.keys(data.allowed_senders||{}).length
      importSummary.textContent = `Infohashes: ${ (data.infohashes||[]).length }, chats con allowed_senders: ${ chatsCount }`
      // update bot summary stats if present
      try{ renderBotSummary(null, null, { chats: chatsCount, infohashes: (data.infohashes||[]).length }) }catch(e){}
    }catch(e){ importSummary.textContent = 'Import error: '+(e.message||e) }
    const devices = await fetchDevices()
    devicesList.innerHTML = ''
    if(!devices || devices.length===0){ devicesList.textContent='(no hay dispositivos)'; return }
    devices.forEach(d=>{
      const row = document.createElement('div'); row.style.display='flex'; row.style.alignItems='center'; row.style.justifyContent='space-between'; row.style.marginBottom='8px'
      const label = document.createElement('div'); label.textContent = (d.name? d.name+' ('+d.id+')': d.id); label.style.flex='1'
      const btns = document.createElement('div')
      const revoke = document.createElement('button'); revoke.className='btn ghost'; revoke.textContent='Revocar'; revoke.style.marginLeft='8px'
      revoke.addEventListener('click', async ()=>{
        if(!confirm('Revocar dispositivo '+d.id+'?')) return
        try{
          const base = getApiBase()
          const res = await fetch(base + '/devices/' + encodeURIComponent(d.id), { method: 'DELETE', headers: headers() })
          if(!res.ok){ const t = await res.text(); alert('Error revocando: '+t); return }
          alert('Dispositivo revocado')
          await refreshAll()
        }catch(e){ alert('Error revocando: '+(e.message||e)) }
      })
      btns.appendChild(revoke)
      row.appendChild(label)
      row.appendChild(btns)
      devicesList.appendChild(row)
    })
  }

  // --- Configured bots management ---
  const CONFIGURED_BOTS_KEY = 'configured_bots'
  function loadConfiguredBots(){
    try{ return JSON.parse(localStorage.getItem(CONFIGURED_BOTS_KEY) || '[]') }catch(e){ return [] }
  }
  function saveConfiguredBots(arr){ try{ localStorage.setItem(CONFIGURED_BOTS_KEY, JSON.stringify(arr||[])) }catch(e){} }

  function renderConfiguredBots(){
    const arr = loadConfiguredBots()
    configuredBotsList.innerHTML = ''
    if(!arr || arr.length===0){ configuredBotsList.textContent='(no hay bots configurados)'; return }
    arr.forEach((b, idx)=>{
      const row = document.createElement('div'); row.style.display='flex'; row.style.alignItems='center'; row.style.justifyContent='space-between'; row.style.marginBottom='8px'
      const info = document.createElement('div'); info.style.flex='1'
      const title = document.createElement('div'); title.style.fontWeight='700'; title.textContent = (b.name||'(sin nombre)') + ' — ' + (b.apiBase||'')
      const subtitle = document.createElement('div'); subtitle.style.color='var(--muted)'; subtitle.style.fontSize='0.9rem'; subtitle.textContent = (b.token? 'Token: yes' : 'Token: no')
      info.appendChild(title); info.appendChild(subtitle)
      const actions = document.createElement('div')
      const statsBtn = document.createElement('button'); statsBtn.className='btn ghost'; statsBtn.textContent='Ver stats'; statsBtn.addEventListener('click', ()=>fetchAndShowBotStats(b))
      const delBtn = document.createElement('button'); delBtn.className='btn'; delBtn.style.marginLeft='8px'; delBtn.textContent='Eliminar'; delBtn.addEventListener('click', ()=>{ if(!confirm('Eliminar bot configurado?')) return; arr.splice(idx,1); saveConfiguredBots(arr); renderConfiguredBots() })
      actions.appendChild(statsBtn); actions.appendChild(delBtn)
      row.appendChild(info); row.appendChild(actions)
      configuredBotsList.appendChild(row)
    })
  }

  async function fetchAndShowBotStats(b){
    const base = (b.apiBase||'').replace(/\/$/, '')
    if(!base){ alert('api base inválida'); return }
    try{
      // try /bot/verify (POST) if token provided, else /bot/data
      let verifyRes = null
      try{
        if(b.token){
          const r = await fetch(base + '/bot/verify', { method:'POST', headers: headers(), body: JSON.stringify({ token: b.token }) })
          if(r.ok) verifyRes = await r.json()
        }
      }catch(e){ /* ignore */ }
      let dataRes = null
      try{ const r2 = await fetch(base + '/bot/data', { headers: headers() }); if(r2.ok) dataRes = await r2.json() }catch(e){}

      // Build a simple modal-like alert with stats
      let out = ''
      if(verifyRes && verifyRes.getMe){ out += `Bot: ${verifyRes.getMe.first_name||verifyRes.getMe.username||''} (@${verifyRes.getMe.username||''})\n` }
      if(dataRes){ out += `Infohashes: ${ (dataRes.infohashes||[]).length }\nAllowed senders chats: ${ Object.keys(dataRes.allowed_senders||{}).length }\n` }
      if(!out) out = 'No se pudo obtener información desde la API.'
      alert(out)
    }catch(e){ alert('Error al obtener stats: '+(e.message||e)) }
  }

  addCfgBotBtn && addCfgBotBtn.addEventListener('click', ()=>{
    const name = cfgBotName.value && cfgBotName.value.trim()
    const base = cfgBotApiBase.value && cfgBotApiBase.value.trim()
    const token = cfgBotToken.value && cfgBotToken.value.trim()
    if(!base){ alert('Introduce API base'); return }
    const arr = loadConfiguredBots()
    arr.push({ name: name||'', apiBase: base, token: token||'' })
    saveConfiguredBots(arr)
    cfgBotName.value=''; cfgBotApiBase.value=''; cfgBotToken.value=''
    renderConfiguredBots()
  })

  refreshBotsBtn && refreshBotsBtn.addEventListener('click', ()=>{ renderConfiguredBots() })

  // initial render for configured bots
  // If no configured bots in localStorage, load defaults from file
  (async function(){
    try{
      const arr = loadConfiguredBots()
      if(!arr || arr.length===0){
        const base = getApiBase()
        try{
          const r = await fetch(base + '/default_configured_bots.json')
          if(r.ok){
            const defaults = await r.json()
            if(defaults && defaults.length){ saveConfiguredBots(defaults); }
          }
        }catch(e){
          // try fetching from same directory
          try{ const r2 = await fetch('default_configured_bots.json'); if(r2.ok){ const defs = await r2.json(); if(defs && defs.length) saveConfiguredBots(defs) } }catch(_){}
      }
    }catch(e){}
    renderConfiguredBots()
  })()

  verifyForm && verifyForm.addEventListener('submit', async (ev)=>{ ev.preventDefault(); const token = verifyTokenInput.value.trim(); if(!token){ alert('Introduce token'); return } try{ const res = await verifyBotToken(token); const devId = (res.device && res.device.id?res.device.id:'ok'); alert('Verificado: '+devId); // render bot summary from verify response
    try{ const gm = res.getMe || null; const photo = res.photo_url || null; const chats = res.allowed_senders ? Object.keys(res.allowed_senders).length : 0; const infohs = res.infohashes ? (res.infohashes.length) : 0; renderBotSummary(gm, photo, { chats: chats, infohashes: infohs }); }catch(e){}
    await refreshAll(); }catch(e){ alert('Verify failed: '+(e.message||e)) } })
  importBtn && importBtn.addEventListener('click', async ()=>{ try{ await refreshAll(); alert('Import completo'); }catch(e){ alert('Import failed: '+(e.message||e)) } })

  listFilesBtn && listFilesBtn.addEventListener('click', async ()=>{
    const token = verifyTokenInput.value.trim()
    if(!token){ alert('Introduce token del bot en el formulario'); return }
    const limit = parseInt(filesLimit && filesLimit.value) || 50
    try{
      const res = await listBotFiles(token, limit)
      renderUploadedFiles(res.files || [])
    }catch(e){ alert('Error listando archivos: '+(e.message||e)) }
  })

  saveRolesBtn && saveRolesBtn.addEventListener('click', ()=>{ try{ localStorage.setItem('bot_owner', ownerInput.value.trim()); localStorage.setItem('bot_admins', adminsInput.value.trim()); alert('Roles guardados'); }catch(e){ alert('Error guardando roles') } })
  clearRolesBtn && clearRolesBtn.addEventListener('click', ()=>{ localStorage.removeItem('bot_owner'); localStorage.removeItem('bot_admins'); ownerInput.value=''; adminsInput.value=''; alert('Roles borrados') })

  // load saved roles
  try{ ownerInput.value = localStorage.getItem('bot_owner') || ''; adminsInput.value = localStorage.getItem('bot_admins') || '' }catch(e){}

  renderCommands()
  // initial attempt to refresh if API base present
  try{ if(apiBaseEl && apiBaseEl.value && apiBaseEl.value.trim() !== '') refreshAll() }catch(e){}

})
