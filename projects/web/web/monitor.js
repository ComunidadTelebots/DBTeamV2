document.addEventListener('DOMContentLoaded', function(){
  const apiBaseEl = document.getElementById('apiBaseMon')
  const apiKeyEl = document.getElementById('apiKeyMon')
  const startBtn = document.getElementById('start')
  const stopBtn = document.getElementById('stop')
  const stream = document.getElementById('stream')
  let timer = null

  function escapeHtml(s){ try{ if(s==null) return ''; return String(s).replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])) }catch(e){ return '' } }

  function appendItem(obj){
    try{
      const el = document.createElement('div')
      el.style.borderBottom = '1px solid rgba(255,255,255,0.02)'
      el.style.padding = '8px 6px'
      const time = new Date().toLocaleTimeString()
      el.innerHTML = `<div style="font-size:0.9rem;color:var(--muted)">${time}</div><pre style="margin:6px 0;color:var(--text);white-space:pre-wrap">${escapeHtml(JSON.stringify(obj, null, 2))}</pre>`
      if(stream) stream.insertBefore(el, stream.firstChild)
    }catch(e){ console.debug('appendItem error', e) }
  }

  async function poll(){
    try{
      const base = (apiBaseEl && apiBaseEl.value) ? apiBaseEl.value.trim().replace(/\/$/, '') : ''
      if(!base){ appendItem({error:'no_api_base', message:'API base no configurada'}); return }
      const url = base + '/messages'
      const headers = { 'Content-Type': 'application/json' }
      const k = (apiKeyEl && apiKeyEl.value)?apiKeyEl.value.trim():''
      if(k) headers['Authorization'] = 'Bearer ' + k
      // timeout via AbortController
      const controller = new AbortController()
      const timeout = setTimeout(()=> controller.abort(), 5000)
      const res = await fetch(url, { headers, signal: controller.signal })
      clearTimeout(timeout)
      if(!res.ok){ const txt = await res.text().catch(()=>'<no body>'); appendItem({error: res.status, text: txt}); return }
      const arr = await res.json()
      if(!Array.isArray(arr)){ appendItem({warning:'unexpected_payload', payload: arr}); return }
      // show most recent first (up to 20)
      const slice = arr.slice(-20)
      slice.reverse().forEach(i => appendItem(i))
    }catch(e){
      if(e.name === 'AbortError') appendItem({error:'timeout', message:'La petición tardó demasiado'})
      else appendItem({error: 'network', message: e.toString()})
    }
  }

  if(startBtn) startBtn.addEventListener('click', ()=>{
    if(timer) return
    poll()
    timer = setInterval(poll, 2000)
    if(startBtn) startBtn.disabled = true
    if(stopBtn) stopBtn.disabled = false
  })

  if(stopBtn) stopBtn.addEventListener('click', ()=>{
    if(timer) clearInterval(timer)
    timer = null
    if(startBtn) startBtn.disabled = false
    if(stopBtn) stopBtn.disabled = true
  })

  if(stopBtn) stopBtn.disabled = true
  // Ensure bubble toggle works on this page even if app.js handlers missed it
  (function attachBubbleHandlers(){
    try{
      const bt = document.getElementById('bubbleToggle')
      const body = document.getElementById('bubbleBody')
      const bc = document.getElementById('bubbleClose')
      if(bt && body){
        bt.addEventListener('click', ()=>{
          if(body.classList.contains('open')) body.classList.remove('open')
          else body.classList.add('open')
        })
      }
      if(bc && body){ bc.addEventListener('click', ()=>{ body.classList.remove('open') }) }
    }catch(e){ console.debug('attachBubbleHandlers error', e) }
  })()
  // load pages list into pagesList container
  async function loadPagesList(){
    const container = document.getElementById('pagesList')
    if(!container) return
    container.innerHTML = ''
    try{
      const res = await fetch('pages.json')
      let pages = []
      if(res.ok) pages = await res.json()
      if(!pages || !Array.isArray(pages) || pages.length===0){ container.textContent = '(no hay páginas)'; return }
      pages.forEach(p=>{
        const a = document.createElement('a')
        a.href = p.href
        a.textContent = p.label || p.href
        a.className = 'secondary'
        a.style.display = 'inline-block'
        a.style.padding = '6px 10px'
        a.target = '_blank'
        container.appendChild(a)
      })
    }catch(e){ container.textContent = '(error cargando páginas)'; console.debug('loadPagesList error', e) }
  }

  // try load on start
  setTimeout(()=>{ loadPagesList().catch(()=>{}) }, 300)
  // --- API key helpers: save/clear from localStorage and auto-fill ---
  try{
    const saveBtn = document.getElementById('saveApiKey')
    const clearBtn = document.getElementById('clearApiKey')
    const k = localStorage.getItem('dbteam_api_key')
    if(k && apiKeyEl) apiKeyEl.value = k
    if(saveBtn){ saveBtn.addEventListener('click', ()=>{ if(apiKeyEl && apiKeyEl.value){ localStorage.setItem('dbteam_api_key', apiKeyEl.value.trim()); alert('API key guardada en localStorage') } }) }
    if(clearBtn){ clearBtn.addEventListener('click', ()=>{ localStorage.removeItem('dbteam_api_key'); if(apiKeyEl) apiKeyEl.value=''; alert('API key borrada') }) }
  }catch(e){ console.debug('apiKey helpers error', e) }
  // --- Bot control handlers ---
  try{
    const btnRestart = document.getElementById('btnRestart')
    const ctrlToken = document.getElementById('ctrlToken')
    const ctrlMin = document.getElementById('ctrlMin')
    const ctrlMax = document.getElementById('ctrlMax')
    const ctrlResult = document.getElementById('ctrlResult')
    async function doRestart(){
      const base = (apiBaseEl && apiBaseEl.value) ? apiBaseEl.value.trim().replace(/\/$/, '') : ''
      if(!base){ alert('API base no configurada'); return }
      const k = (apiKeyEl && apiKeyEl.value)?apiKeyEl.value.trim():''
      const body = { action: 'restart' }
      if(ctrlToken && ctrlToken.value) body.token = ctrlToken.value.trim()
      if(ctrlMin && ctrlMin.value) body.min_interval = ctrlMin.value.trim()
      if(ctrlMax && ctrlMax.value) body.max_concurrent = ctrlMax.value.trim()
      try{
        const res = await fetch(base + '/control', { method: 'POST', headers: Object.assign({'Content-Type':'application/json'}, k?{'Authorization':'Bearer '+k}:{ }), body: JSON.stringify(body) })
        const j = await res.json().catch(()=>({ok:false}))
        if(!res.ok) ctrlResult.textContent = 'Error: '+ (j.error || res.status)
        else ctrlResult.textContent = 'Respuesta: '+ (j.status || JSON.stringify(j))
      }catch(e){ ctrlResult.textContent = 'Network error' }
    }
    if(btnRestart) btnRestart.addEventListener('click', doRestart)
  }catch(e){ console.debug('bot control handlers error', e) }
})
