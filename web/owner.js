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
  const genPassEmailBtn = document.getElementById('genPassEmail')
  const botsList = document.getElementById('botsList')
  const discoverResults = document.getElementById('discoverResults')
  const geoBotsDiv = document.getElementById('geoBots')
  const geoUsersDiv = document.getElementById('geoUsers')
  const mapBotsEl = document.getElementById('mapBots')
  const mapUsersEl = document.getElementById('mapUsers')
  let botMapRef = null
  let userMapRef = null
  const refreshAllBtn = document.getElementById('refreshAll')
  const refreshOverviewBtn = document.getElementById('refreshOverview')
  const refreshBotsBtn = document.getElementById('refreshBots')
  const discoverLanBtn = document.getElementById('discoverLan')
  const refreshGeoBtn = document.getElementById('refreshGeo')
  const createUserBtn = document.getElementById('createUser')
  const saveConnectionBtn = document.getElementById('saveConnection')
  const apiBaseList = document.getElementById('apiBaseList')
  const refreshModelsBtn = document.getElementById('refreshModels')
  const modelNameInput = document.getElementById('modelNameInput')
  const installModelBtn = document.getElementById('installModelBtn')
  const installedModelsList = document.getElementById('installedModelsList')
  const modelInstallStatus = document.getElementById('modelInstallStatus')
  const modelCatalogDiv = document.getElementById('modelCatalog')
  const startMonitorBtn = document.getElementById('startMonitorBtn')
  const stopMonitorBtn = document.getElementById('stopMonitorBtn')
  const restartMonitorBtn = document.getElementById('restartMonitorBtn')
  const monitorStatusText = document.getElementById('monitorStatusText')
  const monitorLog = document.getElementById('monitorLog')

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

  function renderDiscover(list){
    if(!discoverResults) return
    if(!list || !list.length){
      discoverResults.textContent = 'Nada encontrado en el rango';
      return;
    }
    const frag = document.createDocumentFragment();
    list.forEach(item=>{
      const row = document.createElement('div');
      row.className = 'mini-card';
      const title = document.createElement('div');
      title.className = 'mini-title';
      title.textContent = `${item.host}:${item.port}`;
      const body = document.createElement('div');
      body.className = 'mini-body';
      body.textContent = 'Respuesta /status: '+ (item.status || 'desconocido');
      const actions = document.createElement('div');
      actions.style.marginTop = '8px';
      const imp = document.createElement('button'); imp.className='btn'; imp.textContent='Importar';
      imp.addEventListener('click',()=>{
        const token = prompt('Introduce el token del bot para '+item.host);
        if(!token) return;
        const name = prompt('Nombre opcional', item.host) || item.host;
        const id = `${item.host}:${item.port}`;
        request('/devices/add', { method:'POST', body: JSON.stringify({ id, name, token }) })
          .then(()=>{ alert('Dispositivo importado'); loadBots(); })
          .catch(e=> alert('Error al importar: '+e.message));
      });
      actions.appendChild(imp);
      row.appendChild(title); row.appendChild(body); row.appendChild(actions);
      frag.appendChild(row);
    })
    discoverResults.innerHTML = '';
    discoverResults.appendChild(frag);
  }

  function getApiBase(){
    const v = apiBaseInput && apiBaseInput.value ? apiBaseInput.value.trim() : ''
    if(v) return v.replace(/\/+$/, '')
    return 'http://127.0.0.1:8081'
  }

  function authHeaders(withJson=true){
    const h = withJson ? {'Content-Type':'application/json'} : {}
    let tok = ''
    try{ tok = (apiTokenInput && apiTokenInput.value ? apiTokenInput.value.trim() : '') || (localStorage.getItem('api_token') || '') }catch(e){ tok='' }
    if(tok) h['Authorization'] = 'Bearer ' + tok
    return h
  }

  function randomPassword(len=16){
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*?';
    let out = '';
    const arr = new Uint32Array(len);
    crypto.getRandomValues(arr);
    for(let i=0;i<len;i++){ out += chars[arr[i] % chars.length]; }
    return out;
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
      const tr = document.createElement('tr'); const td=document.createElement('td'); td.colSpan=4; td.style.textAlign='center'; td.style.color='var(--muted)'; td.textContent='Sin usuarios'; tr.appendChild(td); usersTable.appendChild(tr); return
    }
    users.forEach(u=>{
      const tr = document.createElement('tr')
      const tdUser = document.createElement('td'); tdUser.textContent = u.user || '(sin nombre)'; tr.appendChild(tdUser)
      const tdAdmin = document.createElement('td'); tdAdmin.textContent = u.is_admin ? 'Sí' : 'No'; tr.appendChild(tdAdmin)
      const tdCreated = document.createElement('td'); tdCreated.textContent = fmtDate(u.created_at); tr.appendChild(tdCreated)
      const tdActions = document.createElement('td');
      const btnReset = document.createElement('button'); btnReset.className='secondary'; btnReset.textContent='Reset pass'; btnReset.addEventListener('click',()=>resetUser(u.user))
      const btnDelete = document.createElement('button'); btnDelete.className='ghost'; btnDelete.textContent='Eliminar'; btnDelete.style.marginLeft='6px'; btnDelete.addEventListener('click',()=>deleteUser(u.user))
      tdActions.appendChild(btnReset); tdActions.appendChild(btnDelete); tr.appendChild(tdActions)
      usersTable.appendChild(tr)
    })
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
    await request('/admin/users', { method:'POST', body: JSON.stringify({ user, pass, is_admin: !!(newIsAdmin && newIsAdmin.checked) }) })
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

  async function loadInstalledModels(){
    if(!installedModelsList) return
    installedModelsList.textContent = 'Cargando...'
    try{
      const res = await request('/models/list', { method: 'GET' })
      const arr = res && res.models ? res.models : []
      if(!arr.length) installedModelsList.textContent = '(ninguno)'
      else installedModelsList.textContent = arr.join(', ')
      modelInstallStatus.textContent = ''
      renderModelCatalog(arr)
    }catch(e){
      installedModelsList.textContent = 'Error: '+e.message
      renderModelCatalog([])
    }
  }

  // Monitor control functions
  async function loadMonitorStatus(){
    if(!monitorStatusText) return
    monitorStatusText.textContent = 'Consultando monitor...'
    if(monitorLog) monitorLog.textContent = 'Cargando logs...'
    try{
      const res = await request('/monitor/status', { method: 'GET' })
      monitorStatusText.textContent = res.running ? `Monitor activo (pid ${res.pid || '—'})` : 'Monitor detenido'
      if(monitorLog) monitorLog.textContent = res.log_tail || '(sin logs)'
      // also load per-service status
      try{ loadServiceControls() }catch(e){}
    }catch(e){
      monitorStatusText.textContent = 'Error consultando monitor: '+e.message
      if(monitorLog) monitorLog.textContent = ''
    }
  }

  async function loadServiceControls(){
    const container = document.getElementById('serviceControls')
    if(!container) return
    container.textContent = 'Cargando servicios...'
    try{
      const res = await request('/monitor/service/status', { method: 'GET' })
      container.innerHTML = ''
      // add Restart All button binding
      const restartAllBtn = document.getElementById('restartAllServicesBtn')
      if(restartAllBtn){ restartAllBtn.onclick = async ()=>{ if(!confirm('Reiniciar TODOS los servicios?')) return; restartAllBtn.disabled=true; restartAllBtn.textContent='Reiniciando...'; try{ await request('/monitor/service/restart_all', { method:'POST' }); setTimeout(()=>{ loadMonitorStatus() }, 1200) }catch(e){ alert('Error reiniciando todos: '+e.message) } restartAllBtn.disabled=false; restartAllBtn.textContent='Reiniciar todos' } }
      (res.services || []).forEach(s=>{
        const row = document.createElement('div')
        row.style.display='flex'; row.style.justifyContent='space-between'; row.style.alignItems='center'; row.style.marginTop='6px'
        const left = document.createElement('div'); left.textContent = `${s.name} ${s.running ? '(running pid:'+ (s.pid||'—') +')' : '(stopped)'}`
        const ctrl = document.createElement('div')
        const btn = document.createElement('button'); btn.className='secondary'; btn.textContent='Reiniciar';
        btn.addEventListener('click', async ()=>{
          try{
            btn.disabled=true; btn.textContent='Reiniciando...'
            await request('/monitor/service/restart', { method:'POST', body: JSON.stringify({ service: s.name }) })
            setTimeout(()=>{ loadMonitorStatus() }, 1200)
          }catch(e){ alert('Error reiniciando: '+e.message) }
          btn.disabled=false; btn.textContent='Reiniciar'
        })
        ctrl.appendChild(btn)
        row.appendChild(left); row.appendChild(ctrl)
        container.appendChild(row)
      })
    }catch(e){ container.textContent='Error cargando servicios: '+e.message }
  }

  async function startMonitor(){
    if(startMonitorBtn) startMonitorBtn.disabled = true
    try{
      await request('/monitor/start', { method: 'POST' })
      await loadMonitorStatus()
    }catch(e){ alert('Error iniciando monitor: '+e.message) }
    if(startMonitorBtn) startMonitorBtn.disabled = false
  }

  async function stopMonitor(){
    if(stopMonitorBtn) stopMonitorBtn.disabled = true
    try{
      await request('/monitor/stop', { method: 'POST' })
      await loadMonitorStatus()
    }catch(e){ alert('Error deteniendo monitor: '+e.message) }
    if(stopMonitorBtn) stopMonitorBtn.disabled = false
  }

  async function restartMonitor(){
    if(restartMonitorBtn) restartMonitorBtn.disabled = true
    try{
      await request('/monitor/stop', { method: 'POST' })
    }catch(e){}
    try{ await request('/monitor/start', { method: 'POST' }) }catch(e){ alert('Error reiniciando monitor: '+e.message) }
    await loadMonitorStatus()
    if(restartMonitorBtn) restartMonitorBtn.disabled = false
  }

  async function installModel(){
    const m = modelNameInput && modelNameInput.value ? modelNameInput.value.trim() : ''
    if(!m){ alert('Introduce el nombre del modelo'); return }
    if(modelInstallStatus) modelInstallStatus.textContent = 'Instalando '+m+'...'
    try{
      const res = await request('/models/install', { method: 'POST', body: JSON.stringify({ model: m }) })
      if(res && res.ok){
        modelInstallStatus.textContent = 'Instalado: '+(res.model || m)
        await loadInstalledModels()
      }else{
        modelInstallStatus.textContent = 'Respuesta: '+JSON.stringify(res)
      }
    }catch(e){ modelInstallStatus.textContent = 'Error: '+e.message }
  }

  // Predefined catalog of models to show in the UI
  const MODEL_CATALOG = [
    'gpt2',
    'distilgpt2',
    'facebook/opt-125m',
    'facebook/opt-350m',
    'EleutherAI/gpt-neo-125M',
    'google/flan-t5-small',
    'bigscience/bigscience-small-testing'
  ]

  function renderModelCatalog(installed){
    if(!modelCatalogDiv) return
    modelCatalogDiv.innerHTML = ''
    const frag = document.createDocumentFragment()
    MODEL_CATALOG.forEach(m=>{
      const row = document.createElement('div')
      row.className = 'mini-card'
      const title = document.createElement('div')
      title.className = 'mini-title'
      title.textContent = m
      const body = document.createElement('div')
      body.className = 'mini-body'
      const installedFlag = (installed || []).indexOf(m) !== -1
      body.textContent = installedFlag ? 'Estado: instalado' : 'Estado: no instalado'
      const actions = document.createElement('div')
      actions.style.marginTop = '8px'
      const btn = document.createElement('button')
      btn.className = installedFlag ? 'secondary' : 'btn'
      btn.textContent = installedFlag ? 'Reinstalar' : 'Instalar'
      btn.addEventListener('click', async ()=>{
        if(modelInstallStatus) modelInstallStatus.textContent = (installedFlag ? 'Reinstalando ' : 'Instalando ') + m + '...'
        try{
          const res = await request('/models/install', { method: 'POST', body: JSON.stringify({ model: m }) })
          if(res && res.ok){
            modelInstallStatus.textContent = 'Instalado: '+m
            await loadInstalledModels()
          }else{
            modelInstallStatus.textContent = 'Respuesta: '+JSON.stringify(res)
          }
        }catch(e){ modelInstallStatus.textContent = 'Error: '+e.message }
      })
      actions.appendChild(btn)
      row.appendChild(title); row.appendChild(body); row.appendChild(actions)
      frag.appendChild(row)
    })
    modelCatalogDiv.appendChild(frag)
  }

  async function discoverLan(){
    if(discoverResults) discoverResults.textContent = 'Buscando en LAN...';
    try{
      const res = await request('/discover/lan', { method:'GET' });
      renderDiscover(res && res.found ? res.found : []);
    }catch(e){
      if(discoverResults) discoverResults.textContent = 'Error: '+e.message;
    }
  }

  function renderGeoList(list, label){
    if(!list || !list.length) return `${label}: sin datos`;
    return `${label}: ` + list.map(it=>{
      const where = [it.city, it.country].filter(Boolean).join(', ')
      const coords = (it.lat && it.lon) ? `(${it.lat}, ${it.lon})` : ''
      return `${it.id||it.user||it.ip||'—'} ${where ? '— '+where : ''} ${coords}`
    }).join(' | ')
  }

  function buildMap(el){
    if(!el || typeof L === 'undefined') return null
    const map = L.map(el, { worldCopyJump:true })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map)
    const layer = L.layerGroup().addTo(map)
    map.setView([20, 0], 2)
    setTimeout(()=>map.invalidateSize(), 50)
    return { map, layer }
  }

  function updateMap(which, items){
    const el = which === 'bots' ? mapBotsEl : mapUsersEl
    let ref = which === 'bots' ? botMapRef : userMapRef
    if(!el) return
    if(typeof L === 'undefined'){
      el.textContent = 'Leaflet no cargó'
      return
    }
    if(!ref){
      ref = buildMap(el)
      if(which === 'bots') botMapRef = ref; else userMapRef = ref
    }
    if(!ref) return
    ref.layer.clearLayers()
    const coords = []
    ;(items || []).forEach(it=>{
      const lat = parseFloat(it.lat)
      const lon = parseFloat(it.lon)
      if(Number.isFinite(lat) && Number.isFinite(lon)){
        coords.push({ lat, lon })
        const title = it.id || it.user || it.ip || 'Desconocido'
        const where = [it.city, it.country].filter(Boolean).join(', ')
        const ip = it.ip ? `IP: ${it.ip}` : ''
        const org = it.org ? `ISP: ${it.org}` : ''
        const popup = [title, where, ip, org].filter(Boolean).join('<br>')
        L.marker([lat, lon]).addTo(ref.layer).bindPopup(popup || title)
      }
    })
    if(!coords.length){
      ref.map.setView([20, 0], 2)
      return
    }
    if(coords.length === 1){
      ref.map.setView([coords[0].lat, coords[0].lon], 5)
    }else{
      ref.map.fitBounds(coords.map(c=>[c.lat, c.lon]), { padding:[18,18] })
    }
    setTimeout(()=>ref.map.invalidateSize(), 50)
  }

  async function loadGeo(){
    if(geoBotsDiv) geoBotsDiv.textContent = 'Geo bots: cargando...';
    if(geoUsersDiv) geoUsersDiv.textContent = 'Geo usuarios: cargando...';
    try{
      const res = await request('/geo/summary', { method:'GET' });
      const bots = res && res.bots ? res.bots : []
      const users = res && res.users ? res.users : []
      if(geoBotsDiv) geoBotsDiv.textContent = renderGeoList(bots, 'Geo bots');
      if(geoUsersDiv) geoUsersDiv.textContent = renderGeoList(users, 'Geo usuarios');
      updateMap('bots', bots)
      updateMap('users', users)
    }catch(e){
      if(geoBotsDiv) geoBotsDiv.textContent = 'Geo bots: error '+e.message;
      if(geoUsersDiv) geoUsersDiv.textContent = 'Geo usuarios: error '+e.message;
    }
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
  if(discoverLanBtn) discoverLanBtn.addEventListener('click', discoverLan)
  if(refreshGeoBtn) refreshGeoBtn.addEventListener('click', loadGeo)
  if(createUserBtn) createUserBtn.addEventListener('click', createUser)
  if(saveConnectionBtn) saveConnectionBtn.addEventListener('click', saveConnection)
  if(refreshModelsBtn) refreshModelsBtn.addEventListener('click', loadInstalledModels)
  if(installModelBtn) installModelBtn.addEventListener('click', installModel)
  if(genPassEmailBtn) genPassEmailBtn.addEventListener('click', ()=>{
    const user = newUserInput && newUserInput.value ? newUserInput.value.trim() : ''
    if(!user){ alert('Introduce el correo/usuario primero'); return }
    const pwd = randomPassword(16)
    if(newPassInput) newPassInput.value = pwd
    try{
      const subject = encodeURIComponent('Tu nueva contraseña DBTeam')
      const body = encodeURIComponent('Hola,\n\nAquí tienes una contraseña generada:\n\n'+pwd+'\n\nCámbiala tras iniciar sesión.')
      window.open('mailto:'+encodeURIComponent(user)+'?subject='+subject+'&body='+body, '_blank')
    }catch(e){ alert('No se pudo abrir el cliente de correo'); }
  })
  if(apiBaseInput) apiBaseInput.addEventListener('blur', ()=>{ const v = apiBaseInput.value && apiBaseInput.value.trim(); if(v){ localStorage.setItem(API_BASE_KEY, v); saveApiBaseHistory(v) } })

  // initial load: avoid automatic network calls so the page renders even if backends are down.
  // Use the UI buttons to refresh data on demand.

  if(startMonitorBtn) startMonitorBtn.addEventListener('click', startMonitor)
  if(stopMonitorBtn) stopMonitorBtn.addEventListener('click', stopMonitor)
  if(restartMonitorBtn) restartMonitorBtn.addEventListener('click', restartMonitor)
  // load monitor status and services shortly after page load (non-blocking)
  try{ setTimeout(()=>{ loadMonitorStatus().catch(()=>{}) }, 300) }catch(e){}
})
