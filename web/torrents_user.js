document.addEventListener('DOMContentLoaded', ()=>{
  const userInput = document.getElementById('userName')
  const refresh = document.getElementById('refresh')
  const listDiv = document.getElementById('list')
  const msg = document.getElementById('msg')

  function setMsg(t){ if(msg) msg.textContent = t }

  async function load(){
    const user = (userInput && userInput.value) ? userInput.value.trim() : null
    if(!user){ setMsg('Introduce un usuario'); return }
    setMsg('Cargando...')
    listDiv.textContent = ''
    try{
      const headers = {}
      try{ const tok = localStorage.getItem('api_token'); if(tok) headers['Authorization'] = 'Bearer ' + tok }catch(e){}
      try{ const apiu = localStorage.getItem('api_user'); if(apiu) headers['X-User'] = apiu }catch(e){}
      // Prefer server-side filtered call when we have a Bearer token, otherwise
      // fetch all files and filter client-side to avoid requiring auth for testing.
      let res, j
      // prefer direct streamer when running behind dev proxy on :8000
      const base = (window && window.location && (window.location.port === '8000' || (window.location.host||'').indexOf(':8000') !== -1)) ? 'http://127.0.0.1:8082' : ''
      if(headers['Authorization']){
        res = await fetch(base + '/media/files?user='+encodeURIComponent(user), { headers })
        j = await res.json()
        if(!res.ok){ setMsg('Error: '+(j && (j.error||j.detail) || res.status)); return }
      } else {
        res = await fetch(base + '/media/files')
        j = await res.json()
      }
      let arr = j.files || []
      if(!headers['Authorization'] && user){ arr = arr.filter(x => x.owner == user) }
      if(!arr.length){ listDiv.innerHTML = '<div style="color:var(--muted)">No hay torrents descargados para este usuario</div>'; setMsg(''); return }
      const table = document.createElement('table'); table.className='table'
      const thead = document.createElement('thead'); thead.innerHTML = '<tr><th>Nombre</th><th>Tamaño</th><th>Modificado</th><th>Acciones</th></tr>'
      table.appendChild(thead)
      const tbody = document.createElement('tbody')
      // build quick lookup for possible MP4 companions
      const byBase = {}
      arr.forEach(it => {
        try{
          const base = it.path.replace(/\.[^/.]+$/, '')
          if(!byBase[base]) byBase[base] = []
          byBase[base].push(it)
        }catch(e){}
      })

      arr.forEach(f=>{
        const tr = document.createElement('tr')
        const tdName = document.createElement('td'); tdName.textContent = f.path; tr.appendChild(tdName)
        const tdSize = document.createElement('td'); tdSize.textContent = (f.size!=null? (f.size+' B') : '—'); tr.appendChild(tdSize)
        const tdM = document.createElement('td'); tdM.textContent = (f.mtime? new Date(f.mtime*1000).toLocaleString() : '—'); tr.appendChild(tdM)
        const tdA = document.createElement('td')
        const dl = document.createElement('a'); dl.className='secondary'; dl.textContent='Descargar'; dl.href = f.url; dl.target = '_blank'; tdA.appendChild(dl)
        // Add "Ver MP4" action when a matching .mp4 exists
        try{
          const base = f.path.replace(/\.[^/.]+$/, '')
          const candidates = byBase[base] || []
          const mp = candidates.find(x => x.path.toLowerCase().endsWith('.mp4'))
          if(mp){
            const viewBtn = document.createElement('button'); viewBtn.className='primary'; viewBtn.style.marginLeft='8px'; viewBtn.textContent='Ver MP4'
            viewBtn.addEventListener('click', ()=>{
              const streamPath = '/media/stream/' + mp.path
              showDownloadProgress(streamPath, mp.path)
            })
            tdA.appendChild(viewBtn)
          }
        }catch(e){}
        tr.appendChild(tdA)
        tbody.appendChild(tr)
      })
      table.appendChild(tbody)
      listDiv.appendChild(table)
      setMsg('')
    }catch(e){ setMsg('Error: '+e.message) }
  }

  if(refresh) refresh.addEventListener('click', load)
  // auto-fill user from query param ?user=
  const params = new URLSearchParams(window.location.search)
  const q = params.get('user')
  if(q && userInput){ userInput.value = q; setTimeout(load,200) }
})

// shared progress modal used by torrents_user.js
async function showDownloadProgress(streamUrl, mediaPath){
  const overlay = document.createElement('div'); overlay.style.position='fixed'; overlay.style.left=0; overlay.style.top=0; overlay.style.right=0; overlay.style.bottom=0; overlay.style.background='rgba(0,0,0,0.6)'; overlay.style.display='flex'; overlay.style.alignItems='center'; overlay.style.justifyContent='center'; overlay.style.zIndex=9999;
  const box = document.createElement('div'); box.style.background='var(--card)'; box.style.padding='18px'; box.style.borderRadius='10px'; box.style.width='480px'; box.style.maxWidth='90%'; box.style.color='var(--text)';
  const title = document.createElement('div'); title.style.fontWeight='700'; title.style.marginBottom='8px'; title.innerText='Progreso de descarga';
  const progBar = document.createElement('div'); progBar.style.height='12px'; progBar.style.background='rgba(255,255,255,0.06)'; progBar.style.borderRadius='8px'; progBar.style.overflow='hidden'; progBar.style.marginBottom='8px';
  const progFill = document.createElement('div'); progFill.style.height='100%'; progFill.style.width='0%'; progFill.style.background='#06b6d4'; progFill.style.transition='width 300ms'; progBar.appendChild(progFill);
  const progText = document.createElement('div'); progText.style.fontSize='0.95rem'; progText.style.color='var(--muted)'; progText.style.marginBottom='12px'; progText.innerText='Comprobando...';
  const actions = document.createElement('div'); actions.style.display='flex'; actions.style.justifyContent='flex-end'; actions.style.gap='8px';
  const openBtn = document.createElement('button'); openBtn.className='btn'; openBtn.textContent='Abrir reproducción'; openBtn.disabled = true;
  const closeBtn = document.createElement('button'); closeBtn.className='ghost'; closeBtn.textContent='Cerrar';
  actions.appendChild(closeBtn); actions.appendChild(openBtn);
  box.appendChild(title); box.appendChild(progBar); box.appendChild(progText); box.appendChild(actions); overlay.appendChild(box); document.body.appendChild(overlay);

  let stop = false; closeBtn.addEventListener('click', ()=>{ stop=true; overlay.remove() });
  openBtn.addEventListener('click', ()=>{ window.open('/multimedia.html?file='+encodeURIComponent(streamUrl),'_blank'); stop=true; overlay.remove() });

  async function checkBotProgress(nameBase){
    try{
      const r = await fetch('http://127.0.0.1:8081/torrents');
      if(!r.ok) return null;
      const j = await r.json(); const list = j.torrents || [];
      for(const t of list){ if(t.name && t.name.indexOf(nameBase) !== -1){ return t.progress != null ? Math.round((t.progress||0)*100) : null } }
    }catch(e){ }
    return null
  }

  async function getExpectedSize(path){
    try{ const r = await fetch('/media/files'); if(!r.ok) return null; const j = await r.json(); const arr = j.files || []; for(const it of arr){ if(it.path === path) return it.size || null } }catch(e){}
    return null
  }

  const nameBase = mediaPath.replace(/\.[^/.]+$/, '').replace(/^torrents\//, '');
  let expected = await getExpectedSize(mediaPath)
  let lastPercent = 0
  while(!stop){
    const botP = await checkBotProgress(nameBase)
    if(botP != null){ progFill.style.width = botP + '%'; progText.innerText = botP + '%'; lastPercent = botP; if(botP >= 100){ openBtn.disabled=false; progText.innerText='Completado'; break } }
    else {
      try{
        const h = await fetch(streamUrl, { method: 'HEAD' })
        if(h && (h.ok || h.status===206)){
          const cur = parseInt(h.headers.get('Content-Length') || h.headers.get('content-length') || '0') || 0
          if(!expected){ expected = await getExpectedSize(mediaPath) }
          if(expected){ const p = Math.min(100, Math.round((cur / expected) * 100)); progFill.style.width = p + '%'; progText.innerText = p + '%  —  ' + (cur?cur+' bytes':'0 B') + ' de ' + expected + ' bytes'; lastPercent = p; if(p>=100){ openBtn.disabled=false; progText.innerText='Completado'; break } }
          else { progText.innerText = (cur?cur+' bytes descargados':'0 B'); progFill.style.width = lastPercent + '%'; }
        }
      }catch(e){ }
    }
    await new Promise(r=>setTimeout(r, 2000));
  }
  if(!stop){ openBtn.disabled = false }
}
