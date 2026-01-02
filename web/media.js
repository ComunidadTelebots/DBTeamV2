document.addEventListener('DOMContentLoaded', ()=>{
  const userInput = document.getElementById('mediaUser')
  const refreshBtn = document.getElementById('mediaRefresh')
  const listDiv = document.getElementById('mediaList')
  const msg = document.getElementById('mediaMsg')

  function setMsg(t){ if(msg) msg.textContent = t }

  async function load(){
    if(!listDiv) return
    listDiv.textContent = 'Cargando...'
    try{
      const qs = userInput && userInput.value ? ('?user='+encodeURIComponent(userInput.value)) : ''
      const res = await fetch('/media/files'+qs)
      const j = await res.json()
      const arr = j.files || []
      if(!arr.length){ listDiv.innerHTML = '<div style="color:var(--muted)">No hay archivos</div>'; return }
      const table = document.createElement('table'); table.className='table'
      const thead = document.createElement('thead'); thead.innerHTML = '<tr><th>Nombre</th><th>Tamaño</th><th>Modificado</th><th>Usuario</th><th>Acciones</th></tr>'
      table.appendChild(thead)
      const tbody = document.createElement('tbody')
      arr.forEach(f=>{
        const tr = document.createElement('tr')
        const tdName = document.createElement('td'); tdName.textContent = f.path; tr.appendChild(tdName)
        const tdSize = document.createElement('td'); tdSize.textContent = (f.size!=null? (f.size+' B') : '—'); tr.appendChild(tdSize)
        const tdM = document.createElement('td'); tdM.textContent = (f.mtime? new Date(f.mtime*1000).toLocaleString() : '—'); tr.appendChild(tdM)
        const tdU = document.createElement('td'); tdU.textContent = f.owner || '-'; tr.appendChild(tdU)
        const tdA = document.createElement('td')
        const dl = document.createElement('a'); dl.className='secondary'; dl.textContent='Descargar'; dl.href = f.url; dl.target = '_blank'; tdA.appendChild(dl)
        const assignBtn = document.createElement('button'); assignBtn.className='ghost'; assignBtn.style.marginLeft='8px'; assignBtn.textContent='Asignar';
        assignBtn.addEventListener('click', async ()=>{
          const u = prompt('Usuario al que asignar:', f.owner||'')
          if(!u) return
          try{
            const r = await fetch('/media/assign',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ path: f.path, user: u }) })
            const jj = await r.json()
            if(r.ok && jj.ok){ setMsg('Asignado'); load() } else { setMsg('Error asignando') }
          }catch(e){ setMsg('Error: '+e.message) }
        })
        tdA.appendChild(assignBtn)
        tr.appendChild(tdA)
        tbody.appendChild(tr)
      })
      table.appendChild(tbody)
      listDiv.innerHTML = ''
      listDiv.appendChild(table)
    }catch(e){ listDiv.textContent = 'Error: '+e.message }
  }

  if(refreshBtn) refreshBtn.addEventListener('click', load)
  setTimeout(()=>{ load().catch(()=>{}) }, 200)
})
