document.addEventListener('DOMContentLoaded', function(){
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
