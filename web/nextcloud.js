document.addEventListener('DOMContentLoaded', ()=>{
  const userInput = document.getElementById('ncUser')
  const fileInput = document.getElementById('ncFile')
  const uploadBtn = document.getElementById('ncUpload')
  const refreshBtn = document.getElementById('ncRefresh')
  const listDiv = document.getElementById('ncList')
  const msg = document.getElementById('ncMsg')

  function setMsg(t){ if(msg) msg.textContent = t }

  async function loadFiles(){
    if(!listDiv) return
    listDiv.textContent = 'Cargando...'
    try{
      const qs = userInput && userInput.value ? ('?user='+encodeURIComponent(userInput.value)) : ''
      const res = await fetch('/nextcloud/files'+qs)
      const j = await res.json()
      const arr = j.files || []
      if(!arr.length){ listDiv.innerHTML = '<div style="color:var(--muted)">No hay archivos</div>'; return }
      const table = document.createElement('table'); table.className='table'
      const thead = document.createElement('thead'); thead.innerHTML = '<tr><th>Nombre</th><th>Tamaño</th><th>Modificado</th><th>Acciones</th></tr>'
      table.appendChild(thead)
      const tbody = document.createElement('tbody')
        arr.forEach(f=>{
        const tr = document.createElement('tr')
        const tdName = document.createElement('td'); tdName.textContent = f.name; tr.appendChild(tdName)
        const tdSize = document.createElement('td'); tdSize.textContent = (f.size!=null? (f.size+' B') : '—'); tr.appendChild(tdSize)
        const tdM = document.createElement('td'); tdM.textContent = (f.mtime? new Date(f.mtime*1000).toLocaleString() : '—'); tr.appendChild(tdM)
        const tdA = document.createElement('td')
        const dl = document.createElement('a'); dl.className='secondary'; dl.textContent='Descargar'; dl.href = f.url; dl.target = '_blank'; tdA.appendChild(dl)
        if(f.user){
          const uspan = document.createElement('span'); uspan.style.marginLeft='8px'; uspan.style.color='var(--muted)'; uspan.textContent='('+f.user+')'; tdA.appendChild(uspan);
        }
        const del = document.createElement('button'); del.className='ghost'; del.style.marginLeft='8px'; del.textContent='Eliminar';
        del.addEventListener('click', async ()=>{
          if(!confirm('Eliminar '+f.name+'?')) return
          try{
            const payload = { name: f.name }
            if(f.user) payload.user = f.user
            const r = await fetch('/nextcloud/delete',{ method:'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) })
            const j = await r.json()
            if(r.ok && j.ok){ setMsg('Eliminado'); loadFiles() } else { setMsg('Error eliminando') }
          }catch(e){ setMsg('Error: '+e.message) }
        })
        tdA.appendChild(del)
        tr.appendChild(tdA)
        tbody.appendChild(tr)
      })
      table.appendChild(tbody)
      listDiv.innerHTML = ''
      listDiv.appendChild(table)
    }catch(e){ listDiv.textContent = 'Error: '+e.message }
  }

  async function upload(){
    if(!fileInput || !fileInput.files || !fileInput.files.length){ alert('Selecciona un archivo'); return }
    const f = fileInput.files[0]
    const fd = new FormData(); fd.append('file', f)
    if(userInput && userInput.value) fd.append('user', userInput.value)
    try{
      uploadBtn.disabled=true; uploadBtn.textContent='Subiendo...'
      const res = await fetch('/nextcloud/upload', { method:'POST', body: fd })
      const j = await res.json()
      if(res.ok && j.ok){ setMsg('Subido: '+j.name); loadFiles() } else { setMsg('Error: '+(j.error||'upload failed')) }
    }catch(e){ setMsg('Error: '+e.message) }
    finally{ uploadBtn.disabled=false; uploadBtn.textContent='Subir' }
  }

  if(uploadBtn) uploadBtn.addEventListener('click', upload)
  if(refreshBtn) refreshBtn.addEventListener('click', loadFiles)
  try{ setTimeout(()=>{ loadFiles().catch(()=>{}) }, 200) }catch(e){}
})
