document.addEventListener('DOMContentLoaded', ()=>{
  const apiBaseInput = document.getElementById('apiBase')
  const apiTokenInput = document.getElementById('apiToken')
  const connectionStatus = document.getElementById('connectionStatus')
  const statusSummary = document.getElementById('statusSummary')
  const botStatsSummary = document.getElementById('botStatsSummary')
  const sessionSummary = document.getElementById('sessionSummary')
  const usersTable = document.getElementById('usersTable')
  const newUserInput = document.getElementById('newUser')
  const newPassInput = document.getElementById('newPass')
  const newIsAdmin = document.getElementById('newIsAdmin')
  const newIsTranslator = document.getElementById('newIsTranslator')
  const newIsPublisher = document.getElementById('newIsPublisher')
  const botsList = document.getElementById('botsList')
  const refreshAllBtn = document.getElementById('refreshAll')
  const refreshOverviewBtn = document.getElementById('refreshOverview')
  const refreshBotsBtn = document.getElementById('refreshBots')
  const createUserBtn = document.getElementById('createUser')
  const saveConnectionBtn = document.getElementById('saveConnection')
  const apiBaseList = document.getElementById('apiBaseList')

  const API_BASE_KEY = 'bot_api_base'

  function setConnection(text, ok){
    if(!connectionStatus) return
    connectionStatus.textContent = text
    connectionStatus.style.color = ok ? 'var(--success, #22c55e)' : 'var(--muted)'
  }

  function loadApiBaseHistory(){
    if(!apiBaseList) return
    apiBaseList.innerHTML = ''
    const defaults = ['http://127.0.0.1:8000','http://localhost:8000','http://0.0.0.0:8000','https://cas.chat']
    const hist = []
    defaults.forEach(v=>{ const o = document.createElement('option'); o.value=v; apiBaseList.appendChild(o) })
    try{
      const saved = JSON.parse(localStorage.getItem(API_BASE_KEY+'_history') || '[]')
      saved.forEach(v=>{ const o = document.createElement('option'); o.value=v; apiBaseList.appendChild(o) })
    }catch(e){}
  }

  function saveApiBaseHistory(val){
    if(!val) return
    let hist = []
    try{ hist = JSON.parse(localStorage.getItem(API_BASE_KEY+'_history') || '[]') }catch(e){ hist = [] }
    hist = [val, ...hist.filter(x=>x && x!==val)].slice(0,10)
    try{ localStorage.setItem(API_BASE_KEY+'_history', JSON.stringify(hist)) }catch(e){}
    loadApiBaseHistory()
  }

  function getApiBase(){
    const v = apiBaseInput && apiBaseInput.value ? apiBaseInput.value.trim() : ''
    if(v) return v.replace(/\/+$/, '')
    return 'http://127.0.0.1:8000'
  }

  function authHeaders(withJson=true){
    const h = withJson ? {'Content-Type':'application/json'} : {}
    let tok = ''
    try{ tok = (apiTokenInput && apiTokenInput.value ? apiTokenInput.value.trim() : '') || (localStorage.getItem('api_token') || '') }catch(e){ tok='' }
    if(tok) h['Authorization'] = 'Bearer ' + tok
    return h
  }

  async function request(path, opts={}){
    const base = getApiBase()
    const headers = Object.assign({}, authHeaders(opts.body !== undefined ? true : false), opts.headers||{})
    const res = await fetch(base + path, Object.assign({}, opts, { headers }))
    const text = await res.text()
    let data = null
    try{ data = text ? JSON.parse(text) : null }catch(e){ data = null }
    if(!res.ok){
      const detail = (data && (data.detail || data.error)) ? (data.detail || data.error) : (text || 'request failed')
      throw new Error(detail)
    }
    return data
  }

  function fmtDate(ts){ if(!ts) return '—'; try{ return new Date(ts*1000).toLocaleString() }catch(e){ return String(ts) }
  }
  function fmtUptime(sec){ if(!sec && sec!==0) return '—'; const d=Math.floor(sec/86400); const h=Math.floor((sec%86400)/3600); const m=Math.floor((sec%3600)/60); return `${d}d ${h}h ${m}m`; }

  function renderUsers(users){
    if(!usersTable) return
    usersTable.innerHTML = ''
    if(!users || !users.length){
      const tr = document.createElement('tr'); const td=document.createElement('td'); td.colSpan=6; td.style.textAlign='center'; td.style.color='var(--muted)'; td.textContent='Sin usuarios'; tr.appendChild(td); usersTable.appendChild(tr); return
    }
    users.forEach(u=>{
      const tr = document.createElement('tr')
      const tdUser = document.createElement('td'); tdUser.textContent = u.user || '(sin nombre)'; tr.appendChild(tdUser)
      const tdAdmin = document.createElement('td'); tdAdmin.textContent = u.is_admin ? 'Sí' : 'No'; tr.appendChild(tdAdmin)
      const tdTransAdmin = document.createElement('td'); tdTransAdmin.textContent = u.is_trans_admin ? 'Sí' : 'No'; tr.appendChild(tdTransAdmin)
      const tdTranslator = document.createElement('td'); tdTranslator.textContent = u.is_translator ? 'Sí' : 'No'; tr.appendChild(tdTranslator)
      const tdPublisher = document.createElement('td'); tdPublisher.textContent = u.is_publisher ? 'Sí' : 'No'; tr.appendChild(tdPublisher)
      const tdCreated = document.createElement('td'); tdCreated.textContent = fmtDate(u.created_at); tr.appendChild(tdCreated)
      const tdActions = document.createElement('td');
      const btnReset = document.createElement('button'); btnReset.className='secondary'; btnReset.textContent='Reset pass'; btnReset.addEventListener('click',()=>resetUser(u.user))
      const btnDelete = document.createElement('button'); btnDelete.className='ghost'; btnDelete.textContent='Eliminar'; btnDelete.style.marginLeft='6px'; btnDelete.addEventListener('click',()=>deleteUser(u.user))
      const btnEditTrans = document.createElement('button'); btnEditTrans.className='secondary'; btnEditTrans.textContent='Editar traducciones'; btnEditTrans.style.marginLeft='6px'; btnEditTrans.addEventListener('click',()=>editTransPerms(u.user))
      tdActions.appendChild(btnReset); tdActions.appendChild(btnDelete); tr.appendChild(tdActions)
      tdActions.appendChild(btnEditTrans)
      usersTable.appendChild(tr)
    })
  }

  async function editTransPerms(user){
    if(!user) return
    // Open modal editor
    try{
      const resp = await request('/admin/users/'+encodeURIComponent(user)+'/trans_perms', { method:'GET' })
      const current = resp.trans_perms || {}
      openTransModal(user, current)
    }catch(e){
      alert('No se pudo cargar permisos: '+e.message)
    }
  }

  function openTransModal(user, current){
    const overlay = document.createElement('div'); overlay.style.position='fixed'; overlay.style.left=0; overlay.style.top=0; overlay.style.right=0; overlay.style.bottom=0; overlay.style.background='rgba(0,0,0,0.6)'; overlay.style.zIndex=9999; overlay.style.display='flex'; overlay.style.alignItems='center'; overlay.style.justifyContent='center'
    const box = document.createElement('div'); box.style.background='#0f1724'; box.style.padding='18px'; box.style.borderRadius='8px'; box.style.width='720px'; box.style.maxHeight='80vh'; box.style.overflow='auto'; box.style.color='#fff'
    box.innerHTML = `<h3>Permisos de traducción para ${user}</h3>`
    const table = document.createElement('table'); table.style.width='100%'; table.style.marginTop='8px';
    const thead = document.createElement('thead'); thead.innerHTML = '<tr><th>Idioma</th><th>Web</th><th>Backend</th><th>Instalado</th><th></th></tr>'
    table.appendChild(thead)
    const tbody = document.createElement('tbody')
    Object.keys(current).sort().forEach(lang=>{
      const comps = current[lang]
      const tr = document.createElement('tr')
      const tdLang = document.createElement('td'); tdLang.textContent=lang; tr.appendChild(tdLang)
      const makeChk = (name, checked)=>{ const td=document.createElement('td'); const c=document.createElement('input'); c.type='checkbox'; c.checked=!!(checked); c.dataset.comp=name; td.appendChild(c); return td }
      tr.appendChild(makeChk('web', comps && comps.web))
      tr.appendChild(makeChk('backend', comps && comps.backend))
      tr.appendChild(makeChk('installed', comps && comps.installed))
      const tdRem = document.createElement('td'); const del=document.createElement('button'); del.textContent='Eliminar'; del.className='ghost'; del.onclick=()=>{ tr.remove() }; tdRem.appendChild(del); tr.appendChild(tdRem)
      tbody.appendChild(tr)
    })
    table.appendChild(tbody)
    const addRow = () => {
      const tr = document.createElement('tr')
      const tdLang = document.createElement('td'); const langInput = document.createElement('input'); langInput.placeholder='es'; langInput.style.width='80px'; tdLang.appendChild(langInput); tr.appendChild(tdLang)
      const makeChk = (name)=>{ const td=document.createElement('td'); const c=document.createElement('input'); c.type='checkbox'; c.dataset.comp=name; td.appendChild(c); return td }
      tr.appendChild(makeChk('web'))
      tr.appendChild(makeChk('backend'))
      tr.appendChild(makeChk('installed'))
      const tdRem = document.createElement('td'); const del=document.createElement('button'); del.textContent='Eliminar'; del.className='ghost'; del.onclick=()=>{ tr.remove() }; tdRem.appendChild(del); tr.appendChild(tdRem)
      tbody.appendChild(tr)
    }
    const addBtn = document.createElement('button'); addBtn.textContent='Añadir idioma'; addBtn.className='secondary'; addBtn.onclick=addRow
    const saveBtn = document.createElement('button'); saveBtn.textContent='Guardar'; saveBtn.className='btn'; saveBtn.style.marginLeft='8px'; saveBtn.onclick=async ()=>{
      const rows = Array.from(tbody.querySelectorAll('tr'))
      const out = {}
      for(const r of rows){
        const langCell = r.children[0]
        const lang = (langCell.querySelector('input') ? langCell.querySelector('input').value.trim() : langCell.textContent.trim())
        if(!lang) continue
        const comps = {}
        const chks = r.querySelectorAll('input[type=checkbox]')
        chks.forEach(c => { comps[c.dataset.comp]=!!c.checked })
        out[lang]=comps
      }
      try{
        await request('/admin/users/'+encodeURIComponent(user)+'/trans_perms', { method:'POST', body: JSON.stringify({ trans_perms: out }) })
        alert('Guardado')
        overlay.remove()
        await loadUsers()
      }catch(e){ alert('Error: '+e.message) }
    }
    const cancelBtn = document.createElement('button'); cancelBtn.textContent='Cancelar'; cancelBtn.className='ghost'; cancelBtn.style.marginLeft='8px'; cancelBtn.onclick=()=>overlay.remove()
    box.appendChild(table); box.appendChild(addBtn); box.appendChild(saveBtn); box.appendChild(cancelBtn)
    overlay.appendChild(box); document.body.appendChild(overlay)
  }

  function renderStatus(data){
    if(!statusSummary || !sessionSummary) return
    if(!data){ statusSummary.textContent='Sin datos'; sessionSummary.textContent='Sin datos'; return }
    const redisOk = data.redis && data.redis.ok
    const mem = data.redis ? data.redis.used_memory_human : null
    const uptime = fmtUptime(data.uptime)
    statusSummary.textContent = `Uptime ${uptime || '—'} | Redis ${redisOk ? 'OK' : 'Error'}${mem ? ' ('+mem+')' : ''} | Páginas ${data.pages ? data.pages.length : 0}`
    const counts = data.counts || {}
    sessionSummary.textContent = `Usuarios ${counts.users ?? '—'} | Sesiones ${counts.sessions ?? '—'} | Mensajes ${counts.messages ?? '—'} | Devices ${counts.devices ?? '—'}`
  }

  function renderBotStats(stats){
    if(!botStatsSummary) return
    if(!stats){ botStatsSummary.textContent='Sin datos'; return }
    const parts = []
    if(stats.messages_count!=null) parts.push(`Mensajes ${stats.messages_count}`)
    if(stats.tdlib_events_count!=null) parts.push(`TDLib ${stats.tdlib_events_count}`)
    if(stats.server_uptime!=null) parts.push(`Uptime ${fmtUptime(stats.server_uptime)}`)
    if(stats.processes && Array.isArray(stats.processes)){
      const running = stats.processes.filter(p=>p && p.running).map(p=>p.name || 'proc').join(', ')
      if(running) parts.push(`Procesos: ${running}`)
    }
    botStatsSummary.textContent = parts.join(' | ') || 'Sin datos'
  }

  function renderBots(accounts){
    if(!botsList) return
    botsList.innerHTML = ''
    const accs = accounts && accounts.accounts ? accounts.accounts : accounts
    if(!accs || !accs.length){
      const div = document.createElement('div'); div.className='mini-body'; div.style.color='var(--muted)'; div.textContent='Sin bots registrados'; botsList.appendChild(div); return
    }
    accs.forEach(acc=>{
      const card = document.createElement('div'); card.className='mini-card'
      const title = document.createElement('div'); title.className='mini-title'; title.textContent = acc.name || acc.id || 'Bot'
      const body = document.createElement('div'); body.className='mini-body'
      const id = document.createElement('div'); id.textContent = `ID: ${acc.id || '—'}`; body.appendChild(id)
      const token = document.createElement('div'); token.style.color='var(--muted)'; token.textContent = `Token: ${acc.token_masked || (acc.has_token ? 'oculto' : 'no')}`; body.appendChild(token)
      if(acc.getMe){
        const gm = acc.getMe
        const uname = gm.username ? '@'+gm.username : ''
        const line = document.createElement('div'); line.textContent = `getMe: ${gm.first_name || gm.title || ''} ${uname}`; body.appendChild(line)
      } else if(acc.getMe_error){
        const err = document.createElement('div'); err.style.color='var(--muted)'; err.textContent = `getMe error: ${acc.getMe_error}`; body.appendChild(err)
      }
      const actions = document.createElement('div'); actions.style.marginTop='8px';
      const del = document.createElement('button'); del.className='ghost'; del.textContent='Eliminar'; del.addEventListener('click',()=>deleteBot(acc.id))
      actions.appendChild(del)
      card.appendChild(title); card.appendChild(body); card.appendChild(actions);
      botsList.appendChild(card)
    })
  }

  async function createUser(){
    const user = newUserInput && newUserInput.value ? newUserInput.value.trim() : ''
    const pass = newPassInput && newPassInput.value ? newPassInput.value.trim() : ''
    if(!user || !pass){ alert('Usuario y contraseña requeridos'); return }
    await request('/admin/users', { method:'POST', body: JSON.stringify({ user, pass, is_admin: !!(newIsAdmin && newIsAdmin.checked), is_translator: !!(newIsTranslator && newIsTranslator.checked), is_publisher: !!(newIsPublisher && newIsPublisher.checked) }) })
    alert('Usuario creado')
    newPassInput.value=''
    await loadUsers()
  }

  async function resetUser(user){
    if(!user) return
    const pass = prompt('Nueva contraseña para '+user)
    if(!pass) return
    await request('/admin/users/reset', { method:'POST', body: JSON.stringify({ user, pass }) })
    alert('Contraseña reiniciada')
  }

  async function deleteUser(user){
    if(!user) return
    if(!confirm('¿Eliminar usuario '+user+'?')) return
    await request('/admin/users/'+encodeURIComponent(user), { method:'DELETE' })
    await loadUsers()
  }

  async function deleteBot(id){
    if(!id) return
    if(!confirm('¿Eliminar bot/dispositivo '+id+'?')) return
    await request('/devices/'+encodeURIComponent(id), { method:'DELETE' })
    await loadBots()
  }

  async function loadUsers(){
    try{
      const data = await request('/admin/users')
      renderUsers(data ? data.users : [])
      setConnection('API OK', true)
    }catch(e){
      renderUsers([])
      setConnection('Error usuarios: '+e.message, false)
    }
  }

  async function loadOverview(){
    try{
      const data = await request('/admin/overview')
      if(data){
        if(data.users) renderUsers(data.users)
        if(data.status) renderStatus(data.status)
        if(data.bot_stats) renderBotStats(data.bot_stats)
        if(data.bot_accounts) renderBots(data.bot_accounts)
        setConnection('API OK', true)
        return
      }
    }catch(e){
      setConnection('Fallo /admin/overview: '+e.message, false)
    }
    // fallback calls
    try{ const s = await request('/status', { method:'GET', headers: authHeaders(false) }); renderStatus(s) }catch(e){ renderStatus(null) }
    try{ const bs = await request('/bot/stats', { method:'GET' }); renderBotStats(bs) }catch(e){ renderBotStats(null) }
    try{ const ba = await request('/bot/accounts', { method:'GET' }); renderBots(ba) }catch(e){ renderBots([]) }
  }

  async function loadBots(){
    try{ const ba = await request('/bot/accounts', { method:'GET' }); renderBots(ba); setConnection('API OK', true) }catch(e){ renderBots([]); setConnection('Error bots: '+e.message, false) }
  }

  function saveConnection(){
    const base = apiBaseInput && apiBaseInput.value ? apiBaseInput.value.trim() : ''
    const tok = apiTokenInput && apiTokenInput.value ? apiTokenInput.value.trim() : ''
    if(base) localStorage.setItem(API_BASE_KEY, base)
    if(tok) localStorage.setItem('api_token', tok)
    if(base) saveApiBaseHistory(base)
    alert('Conexión guardada')
  }

  // init values
  try{ const saved = localStorage.getItem(API_BASE_KEY); if(saved && apiBaseInput) apiBaseInput.value = saved }catch(e){}
  try{ const tok = localStorage.getItem('api_token'); if(tok && apiTokenInput && !apiTokenInput.value) apiTokenInput.value = tok }catch(e){}
  loadApiBaseHistory()

  // wire events
  if(refreshAllBtn) refreshAllBtn.addEventListener('click', ()=>{ loadOverview(); loadUsers(); })
  if(refreshOverviewBtn) refreshOverviewBtn.addEventListener('click', loadOverview)
  if(refreshBotsBtn) refreshBotsBtn.addEventListener('click', loadBots)
  if(createUserBtn) createUserBtn.addEventListener('click', createUser)
  if(saveConnectionBtn) saveConnectionBtn.addEventListener('click', saveConnection)
  if(apiBaseInput) apiBaseInput.addEventListener('blur', ()=>{ const v = apiBaseInput.value && apiBaseInput.value.trim(); if(v){ localStorage.setItem(API_BASE_KEY, v); saveApiBaseHistory(v) } })

  // initial load
  loadOverview()
})
