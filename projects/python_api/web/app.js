document.addEventListener('DOMContentLoaded', function(){
  console.log('app.js: DOMContentLoaded')
  // Insert lightweight spinner CSS once
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
  const CACHE_TTL = 60 * 1000 // 60 seconds

  function createSpinner(){ const sp = document.createElement('span'); sp.className='inline-spinner'; return sp }
  function getCachedDevices(){ try{ const raw = localStorage.getItem(DEVICES_CACHE_KEY); if(!raw) return null; const obj = JSON.parse(raw); if(!obj.ts || (Date.now() - obj.ts) > CACHE_TTL) return null; return obj.data }catch(e){ return null } }
  function setCachedDevices(data){ try{ localStorage.setItem(DEVICES_CACHE_KEY, JSON.stringify({ ts: Date.now(), data })) }catch(e){} }
  function escapeHtml(s){ try{ if(s==null) return ''; return String(s).replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])) }catch(e){ return '' } }
  const endpointEl = document.getElementById('endpoint')
  const apiBaseEl = document.getElementById('apiBase')
  const providerEl = document.getElementById('provider')
  const chatIdEl = document.getElementById('chat_id')
  const sendAsEl = document.getElementById('sendAs')
  const promptEl = document.getElementById('prompt')
  const deviceSelectEl = document.getElementById('deviceSelect')
  const refreshDevicesBtn = document.getElementById('refreshDevices')
  const submitBtn = document.getElementById('submit')
  const clearBtn = document.getElementById('clear')
  const responseEl = document.getElementById('response')
   const apiKeyEl = document.getElementById('apiKey')
  // restore session token from localStorage if present
  const savedToken = (localStorage && localStorage.getItem) ? localStorage.getItem('web_session_token') : null
  if(savedToken && apiKeyEl) apiKeyEl.value = savedToken
document.addEventListener('DOMContentLoaded', () => {
  // Minimal, robust bubble & resources loader
  function escapeHtml(s){ try{ if(s==null) return ''; return String(s).replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])) }catch(e){ return '' } }

  function ensureBubble(){ if(document.getElementById('bubblePanel')) return
    const html = `
      <aside class="bubble-panel" id="bubblePanel" aria-hidden="true">
        <button class="bubble-toggle" id="bubbleToggle" aria-label="Abrir panel"><img src="logo.svg" alt="logo" class="bubble-logo"/></button>
        <div class="bubble-body" id="bubbleBody">
          <div class="bubble-header"><div class="bubble-title">DBTeam</div><button id="bubbleClose" class="bubble-close">✕</button></div>
          <nav class="bubble-nav"><a href="chat.html">Chat</a><a href="monitor.html">Monitor</a><a href="#" id="linkSettings">Ajustes</a></nav>
          <div id="bubbleNotifications" style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.02)"></div>
          <div id="bubbleResources" style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.02)"></div>
          <div class="bubble-footer"><button id="logoutBtn" class="secondary">Salir</button></div>
        </div>
      </aside>`
    const wrapper = document.createElement('div'); wrapper.innerHTML = html; document.body.appendChild(wrapper)
  }

  function openBubble(){ const b = document.getElementById('bubbleBody'); if(b) b.classList.add('open'); renderResources() }
  function closeBubble(){ const b = document.getElementById('bubbleBody'); if(b) b.classList.remove('open') }

  ensureBubble()

  // toggle handlers
  document.addEventListener('click', (ev)=>{
    const t = ev.target
    if(t.closest && t.closest('.bubble-toggle')){ const body = document.getElementById('bubbleBody'); if(body && body.classList.contains('open')) closeBubble(); else openBubble(); }
    if(t.closest && t.closest('.bubble-close')) closeBubble()
  })

  // render resources (pages + devices placeholder)
  async function renderResources(){
    await renderNotifications()
    const container = document.getElementById('bubbleResources'); if(!container) return
    container.innerHTML = '<div style="color:var(--muted);font-size:0.9rem;margin-bottom:6px">Recursos</div>'
    // pages
    const pagesWrap = document.createElement('div'); pagesWrap.style.marginTop='8px'
    pagesWrap.innerHTML = '<div style="font-size:0.85rem;color:var(--muted)">Páginas web:</div>'
    container.appendChild(pagesWrap)
    try{
      const res = await fetch('pages.json')
      let pages = []
      if(res.ok) pages = await res.json()
      if(!pages || !Array.isArray(pages) || pages.length===0){ pages = [{href:'index.html',label:'Inicio'},{href:'chat.html',label:'Chat'},{href:'monitor.html',label:'Monitor'}] }
      pages.forEach(p=>{
        const a = document.createElement('a'); a.href = p.href; a.textContent = p.label||p.href; a.className='secondary'; a.style.display='inline-block'; a.style.margin='6px 6px 0 0'; a.target='_blank'
        const icon = document.createElement('img'); icon.src = 'logo.svg'; icon.alt=''; icon.style.width='18px'; icon.style.height='18px'; icon.style.verticalAlign='middle'; icon.style.marginRight='6px'
        const span = document.createElement('span'); span.style.verticalAlign='middle'; span.textContent = p.label||p.href
        const wrapper = document.createElement('div'); wrapper.style.display='inline-flex'; wrapper.style.alignItems='center'; wrapper.style.margin='6px'
        wrapper.appendChild(icon); wrapper.appendChild(span)
        a.innerHTML = ''
        a.appendChild(wrapper)
        pagesWrap.appendChild(a)
      })
    }catch(e){ const p = document.createElement('div'); p.style.color='var(--muted)'; p.textContent='(no hay páginas)'; pagesWrap.appendChild(p) }

    // devices placeholder (non-blocking)
    const devWrap = document.createElement('div'); devWrap.style.marginTop='10px'; devWrap.innerHTML = '<div style="font-size:0.85rem;color:var(--muted)">Dispositivos:</div><div style="color:var(--muted)">(usa Monitor/Chat para gestionar)</div>'
    container.appendChild(devWrap)
  }

  // Notifications
  async function fetchNotifications(){
    try{
      const headers = {}
      if(window && window.ADMIN_TOKEN) headers['X-ADMIN-TOKEN'] = window.ADMIN_TOKEN
      const res = await fetch('/web/notifications', { headers })
      if(!res.ok) return []
      const j = await res.json()
      return j.notifications || []
    }catch(e){ return [] }
  }

  async function renderNotifications(){
    const container = document.getElementById('bubbleNotifications'); if(!container) return
    container.innerHTML = '<div style="color:var(--muted);font-size:0.9rem;margin-bottom:6px">Notificaciones</div>'
    const list = document.createElement('div'); list.id='notificationsList'; list.style.maxHeight='220px'; list.style.overflow='auto'
    container.appendChild(list)
    const notes = await fetchNotifications()
    if(!notes || notes.length===0){ list.innerHTML = '<div style="color:var(--muted)">Sin notificaciones</div>'; return }
    notes.forEach(n=>{
      const item = document.createElement('div'); item.className='notification-item'; item.style.padding='8px 0'; item.style.borderBottom='1px solid rgba(255,255,255,0.02)'
      const title = document.createElement('div'); title.style.fontWeight='600'; title.style.fontSize='0.95rem'; title.textContent = n.title || 'Notificación'
      const txt = document.createElement('div'); txt.style.fontSize='0.85rem'; txt.style.color='var(--muted)'; txt.textContent = n.text || ''
      const meta = document.createElement('div'); meta.style.fontSize='0.75rem'; meta.style.color='var(--muted)'; meta.textContent = n.ts ? new Date(n.ts*1000).toLocaleString() : ''
      item.appendChild(title); item.appendChild(txt); item.appendChild(meta)
      list.appendChild(item)
    })
    // mark read: collect raw values (server provides `_raw`)
    try{
      const raws = notes.map(n=> n._raw).filter(Boolean)
      if(raws.length>0){
        const headers = {'Content-Type':'application/json'}
        if(window && window.ADMIN_TOKEN) headers['X-ADMIN-TOKEN'] = window.ADMIN_TOKEN
        fetch('/web/notifications/mark_read', { method: 'POST', headers, body: JSON.stringify({ raws }) }).catch(()=>{})
      }
    }catch(e){}
  }

  // Poll notifications periodically in background
  setInterval(()=>{ const b = document.getElementById('bubbleBody'); if(b && b.classList.contains('open')) renderNotifications() }, 5000)

  // Ensure initial resources are available if bubble already open
  const body = document.getElementById('bubbleBody'); if(body && body.classList.contains('open')) renderResources()

})
  const faviconInput = document.getElementById('faviconInput')

  // optional: wire favicon input if present
  try{
    if(faviconInput){
      // placeholder handler: preview or upload can be implemented here
      faviconInput.addEventListener('change', ()=>{})
    }
  }catch(e){}

});
