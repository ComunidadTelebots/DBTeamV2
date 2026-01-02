const API_BASE = 'http://127.0.0.1:8082'
let importedPanels = []

function ensurePanelStylesheet(){
  let el = document.getElementById('panelStylesheet')
  if(!el){ el = document.createElement('link'); el.id='panelStylesheet'; el.rel='stylesheet'; document.head.appendChild(el) }
  return el
}

async function loadPanels(){
  try{
    const res = await fetch('/panels/panels.json')
    const list = await res.json()
    const container = document.getElementById('panelsList')
    container.innerHTML = ''
    list.forEach(p=>{
      const div = document.createElement('div')
      div.className = 'panel-preview'
      div.innerHTML = `<strong>${p.name}</strong><div style="font-size:12px;color:#ccc">${p.description}</div>`
      const btn = document.createElement('button')
      btn.textContent = 'Apply'
      btn.style.marginTop='6px'
      btn.onclick = ()=>applyPanel(p)
      div.appendChild(btn)
      container.appendChild(div)
    })
  }catch(e){document.getElementById('panelsList').textContent='Failed to load panels'}
}

function applyPanel(p){
  const el = ensurePanelStylesheet()
  // support both remote css path or in-memory content
  if(p.css && p.css.startsWith('/')){
    el.href = p.css
  }else if(p.css && p.css.startsWith('data:')){
    el.href = p.css
  }else if(typeof p.css === 'string'){
    // unknown — set as inline
    const styleId = 'panelInline'
    let s = document.getElementById(styleId)
    if(!s){ s = document.createElement('style'); s.id = styleId; document.head.appendChild(s) }
    s.textContent = p.css
  }
}

document.getElementById('btnImportPanel').addEventListener('click', async ()=>{
  const f = document.getElementById('importPanelFile').files[0]
  if(!f) return alert('Select a CSS file')
  const txt = await f.text()
  // create blob URL and apply
  const blob = new Blob([txt], {type:'text/css'})
  const url = URL.createObjectURL(blob)
  applyPanel({css: url, name: f.name, description: 'Imported panel'})
  alert('Panel imported and applied')
})

async function api(path, opts){
  const res = await fetch(API_BASE + path, Object.assign({credentials:'same-origin'}, opts))
  if(!res.ok) throw new Error(await res.text())
  return res.json()
}

async function loadScenes(){
  try{
    const data = await api('/stream/scenes')
    const ul = document.getElementById('scenesList')
    ul.innerHTML = ''
    data.scenes.forEach(s=>{
      const li = document.createElement('li')
      li.className = 'scene'
      const title = document.createElement('span')
      title.textContent = s.name
      title.style.marginRight = '8px'
      title.onclick = ()=>selectScene(s)
      li.appendChild(title)

      const controls = document.createElement('span')
      controls.style.float = 'right'
      // start/stop quick buttons
      const btnStartSmall = document.createElement('button')
      btnStartSmall.textContent = '▶'
      btnStartSmall.title = 'Start scene'
      btnStartSmall.onclick = (e)=>{e.stopPropagation(); startScene(s)}
      const btnStopSmall = document.createElement('button')
      btnStopSmall.textContent = '■'
      btnStopSmall.title = 'Stop scene'
      btnStopSmall.onclick = (e)=>{e.stopPropagation(); stopScene(s)}
      const btnEdit = document.createElement('button')
      btnEdit.textContent = '✎'
      btnEdit.title = 'Edit'
      btnEdit.onclick = (e)=>{e.stopPropagation(); openEditor(s)}
      const btnDelete = document.createElement('button')
      btnDelete.textContent = '🗑'
      btnDelete.title = 'Delete'
      btnDelete.onclick = (e)=>{e.stopPropagation(); deleteScene(s)}
      [btnStartSmall, btnStopSmall, btnEdit, btnDelete].forEach(b=>{b.style.marginLeft='4px';controls.appendChild(b)})
      li.appendChild(controls)
      ul.appendChild(li)
    })
  }catch(e){console.error(e)}
}

let currentScene = null
function selectScene(s){
  currentScene = s
  document.querySelectorAll('li.scene').forEach(el=>el.classList.remove('active'))
  const list = [...document.querySelectorAll('li.scene')]
  const node = list.find(n=>n.textContent===s.name)
  if(node) node.classList.add('active')
  document.getElementById('previewArea').textContent = 'Scene: ' + s.name
  document.getElementById('sourcesList').textContent = JSON.stringify(s.obs_raw || {}, null, 2)
  // load into editor
  document.getElementById('editorArea').value = JSON.stringify(s, null, 2)
}

// Live rendering: parse editor JSON and render to previewArea
let _liveTimer = null
function renderSceneToPreview(scene){
  const area = document.getElementById('previewArea')
  // keep a background content area
  area.innerHTML = ''
  const bg = document.createElement('div')
  bg.className = 'stage-content'
  bg.style.width = '100%'
  bg.style.height = '100%'
  bg.style.display = 'flex'
  bg.style.alignItems = 'center'
  bg.style.justifyContent = 'center'
  bg.innerHTML = `<div style="text-align:center;color:#bbb"><h2>${scene.name||'Scene'}</h2><div style="font-size:12px">Preview</div></div>`
  area.appendChild(bg)

  const overlay = document.createElement('div')
  overlay.className = 'live-overlay'
  area.appendChild(overlay)

  const sources = scene.sources || (scene.obs_raw && scene.obs_raw.sources) || []
  // if obs_raw is from simple import that has list of sources by name, try to map
  const normalized = Array.isArray(sources) ? sources : []
  normalized.forEach((src, i)=>{
    try{
      const el = document.createElement('div')
      el.className = 'live-source'
      // position
      const left = (src.x !== undefined) ? (''+src.x+'%') : (src.left||src.l||'10%')
      const top = (src.y !== undefined) ? (''+src.y+'%') : (src.top||src.t||'10%')
      if(typeof left === 'number') el.style.left = left + '%'; else el.style.left = left
      if(typeof top === 'number') el.style.top = top + '%'; else el.style.top = top

      if(src.type === 'text' || src.text){
        const t = document.createElement('div')
        t.className = 'live-text'
        t.textContent = src.text || src.content || src.name || ''
        t.style.fontSize = (src.size||src.fontSize||20) + 'px'
        if(src.color) t.style.color = src.color
        el.appendChild(t)
      } else if(src.type === 'image' || src.url){
        const img = document.createElement('img')
        img.className = 'live-image'
        img.src = src.url || src.src || src.value
        img.style.maxWidth = (src.maxWidth||'40%')
        el.appendChild(img)
      } else if(src.type === 'panel' || src.panel){
        // simple panel injection: support 'classic' and 'modern'
        const p = (src.panel || src.id || '').toLowerCase()
        if(p.includes('classic')){
          const wrapper = document.createElement('div')
          wrapper.className = 'panel-lower-third applied-panel'
          wrapper.style.pointerEvents='none'
          wrapper.innerHTML = `<div class="box"><div class="title">${src.title||'Panel Title'} <span class="accent">LIVE</span></div><div class="subtitle">${src.subtitle||''}</div></div>`
          el.appendChild(wrapper)
        } else if(p.includes('modern')){
          const wrapper = document.createElement('div')
          wrapper.className = 'panel-modern applied-panel'
          wrapper.style.pointerEvents='none'
          wrapper.innerHTML = `<h4>${src.title||'Modern'}</h4><p>${src.subtitle||''}</p><div class="tag">${src.tag||''}</div>`
          el.appendChild(wrapper)
        }
      } else {
        // fallback: show JSON
        const t = document.createElement('pre')
        t.style.color = '#ccc'
        t.textContent = JSON.stringify(src, null, 2)
        el.appendChild(t)
      }
      overlay.appendChild(el)
    }catch(e){console.error('render src', e)}
  })
}

// make live-source elements draggable; update editor JSON on drop
function _makeDraggable(container){
  let drag = null
  container.addEventListener('pointerdown', (ev)=>{
    const t = ev.target.closest('.live-source')
    if(!t) return
    ev.preventDefault()
    drag = {el: t, startX: ev.clientX, startY: ev.clientY, origLeft: parseFloat(t.style.left||0), origTop: parseFloat(t.style.top||0)}
    t.setPointerCapture(ev.pointerId)
  })
  container.addEventListener('pointermove', (ev)=>{
    if(!drag) return
    const dx = ev.clientX - drag.startX
    const dy = ev.clientY - drag.startY
    // convert px delta to percent relative to container
    const rect = container.getBoundingClientRect()
    const pxLeft = (drag.origLeft.toString().endsWith('%')) ? (parseFloat(drag.origLeft)/100*rect.width) : drag.origLeft
    const pxTop = (drag.origTop.toString().endsWith('%')) ? (parseFloat(drag.origTop)/100*rect.height) : drag.origTop
    const newLeftPx = pxLeft + dx
    const newTopPx = pxTop + dy
    const newLeftPct = Math.max(0, Math.min(100, (newLeftPx/rect.width)*100))
    const newTopPct = Math.max(0, Math.min(100, (newTopPx/rect.height)*100))
    drag.el.style.left = newLeftPct + '%'
    drag.el.style.top = newTopPct + '%'
  })
  container.addEventListener('pointerup', (ev)=>{
    if(!drag) return
    try{
      const rect = container.getBoundingClientRect()
      const left = parseFloat(drag.el.style.left)
      const top = parseFloat(drag.el.style.top)
      // update editor JSON: find matching source by index based on order
      const idx = Array.from(container.querySelectorAll('.live-source')).indexOf(drag.el)
      const txt = document.getElementById('editorArea').value
      const obj = JSON.parse(txt || '{}')
      obj.sources = obj.sources || (obj.obs_raw && obj.obs_raw.sources) || []
      if(idx >= 0 && idx < obj.sources.length){
        obj.sources[idx].x = left
        obj.sources[idx].y = top
        document.getElementById('editorArea').value = JSON.stringify(obj, null, 2)
      }
    }catch(e){console.error('drag end', e)}
    drag = null
  })
}

// attach draggable behavior when preview area changed
const previewAreaObserver = new MutationObserver(()=>{
  const overlay = document.querySelector('.live-overlay')
  if(overlay) _makeDraggable(overlay)
})
previewAreaObserver.observe(document.getElementById('previewArea'), {childList:true, subtree:true})

function _tryRenderEditor(){
  const txt = document.getElementById('editorArea').value
  try{
    const obj = JSON.parse(txt)
    renderSceneToPreview(obj)
  }catch(e){/* ignore parse errors while typing */}
}

// editor auto-live
document.getElementById('editorArea').addEventListener('input', ()=>{
  const auto = document.getElementById('autoLive').checked
  if(!auto) return
  if(_liveTimer) clearTimeout(_liveTimer)
  _liveTimer = setTimeout(_tryRenderEditor, 400)
})

document.getElementById('btnApplyLive').addEventListener('click', ()=>{
  _tryRenderEditor()
  // optionally save to backend
  try{
    const txt = document.getElementById('editorArea').value
    const obj = JSON.parse(txt)
    if(obj && obj.name){
      fetch(API_BASE + '/stream/scenes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(obj)}).catch(()=>{})
    }
  }catch(e){}
})

document.getElementById('btnImport').addEventListener('click', async ()=>{
  const f = document.getElementById('importFile').files[0]
  if(!f) return alert('Select a file')
  const fd = new FormData()
  fd.append('file', f)
  try{
    const res = await fetch(API_BASE + '/stream/import_obs', {method:'POST', body:fd})
    const j = await res.json()
    if(res.ok){
      await loadScenes()
      alert('Imported: ' + j.imported.join(', '))
    }else{
      alert('Import failed: ' + JSON.stringify(j))
    }
  }catch(e){console.error(e); alert('Import error')}
})

document.getElementById('btnImportRSS').addEventListener('click', async ()=>{
  const url = document.getElementById('importRssUrl').value.trim()
  if(!url) return alert('Enter RSS URL')
  try{
    const res = await fetch(API_BASE + '/stream/import_rss', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url})})
    const j = await res.json()
    if(res.ok){
      await loadScenes()
      alert('Imported feed: '+ j.imported + ' ('+ j.count + ' items)')
    }else{
      alert('Import failed: ' + JSON.stringify(j))
    }
  }catch(e){console.error(e); alert('Import RSS error')}
})

document.getElementById('btnStart').addEventListener('click', async ()=>{
  if(!currentScene) return alert('Select a scene')
  const platform = document.getElementById('platformSelect').value
  try{
    const j = await api('/stream/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({scene: currentScene.name, platform})})
    document.getElementById('streamStatus').textContent = 'Running ('+j.pid+')'
  }catch(e){console.error(e); alert('Start failed')}
})

document.getElementById('btnStop').addEventListener('click', async ()=>{
  if(!currentScene) return alert('Select a scene')
  try{
    await api('/stream/stop', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({scene: currentScene.name})})
    document.getElementById('streamStatus').textContent = 'Stopped'
  }catch(e){console.error(e); alert('Stop failed')}
})

async function startScene(s){
  try{ const j = await api('/stream/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({scene: s.name, platform: 'test'})}); alert('Started '+s.name+' pid:'+j.pid); refreshStatus() }catch(e){console.error(e); alert('Start failed')}
}
async function stopScene(s){
  try{ await api('/stream/stop', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({scene: s.name})}); alert('Stopped '+s.name); refreshStatus() }catch(e){console.error(e); alert('Stop failed')}
}

function openEditor(s){
  selectScene(s)
  document.getElementById('editorArea').focus()
}

document.getElementById('btnSave').addEventListener('click', async ()=>{
  const txt = document.getElementById('editorArea').value
  try{
    const obj = JSON.parse(txt)
    if(!obj.name){
      if(currentScene && currentScene.name) obj.name = currentScene.name
      else obj.name = prompt('Scene name')||''
    }
    if(!obj.name) return alert('Name required')
    await api('/stream/scenes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(obj)})
    await loadScenes()
    alert('Saved')
  }catch(e){console.error(e); alert('Invalid JSON')}
})

document.getElementById('btnDelete').addEventListener('click', async ()=>{
  if(!currentScene) return alert('Select a scene')
  if(!confirm('Delete scene '+currentScene.name+'?')) return
  try{
    await fetch(API_BASE + '/stream/scene/' + encodeURIComponent(currentScene.name), {method:'DELETE'})
    currentScene = null
    document.getElementById('editorArea').value = ''
    await loadScenes()
    alert('Deleted')
  }catch(e){console.error(e); alert('Delete failed')}
})

document.getElementById('btnDuplicate').addEventListener('click', async ()=>{
  if(!currentScene) return alert('Select a scene')
  const copyName = prompt('Duplicate name', currentScene.name + ' copy')
  if(!copyName) return
  const newObj = Object.assign({}, currentScene, {name: copyName})
  try{
    await api('/stream/scenes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(newObj)})
    await loadScenes()
    alert('Duplicated')
  }catch(e){console.error(e); alert('Duplicate failed')}
})

document.getElementById('btnNew').addEventListener('click', async ()=>{
  const name = prompt('New scene name')
  if(!name) return
  const obj = {name, obs_raw:{}}
  try{ await api('/stream/scenes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(obj)}); await loadScenes(); alert('Created') }catch(e){console.error(e); alert('Create failed')}
})

document.getElementById('btnAIGen').addEventListener('click', async ()=>{
  const prompt = document.getElementById('aiPrompt').value.trim()
  if(!prompt) return alert('Enter an AI prompt')
  try{
    const body = {prompt}
    if(currentScene && currentScene.name) body.scene = currentScene.name
    const res = await fetch(API_BASE + '/stream/ai_generate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
    const j = await res.json()
    if(res.ok){
      // append generated text into editor
      const area = document.getElementById('editorArea')
      area.value = (area.value ? area.value + "\n\n" : "") + j.text
      alert('AI generated and appended to editor')
    }else{
      alert('AI error: ' + JSON.stringify(j))
    }
  }catch(e){console.error(e); alert('AI request failed')}
})

async function refreshStatus(){
  try{
    const j = await api('/stream/status')
    j.scenes.forEach(s=>{
      if(currentScene && s.name===currentScene.name){
        document.getElementById('streamStatus').textContent = s.running?('Running ('+s.pid+')'):'Stopped'
      }
    })
  }catch(e){}
}

loadScenes()
setInterval(refreshStatus, 3000)
loadPanels()

// Live settings handlers
document.getElementById('btnLoadSettings').addEventListener('click', async ()=>{
  try{
    const j = await api('/stream/settings')
    const s = j.settings || {}
    document.getElementById('liveTitle').value = s.title || ''
    document.getElementById('liveDescription').value = s.description || ''
    document.getElementById('livePlatform').value = s.platform || 'rtmp'
    document.getElementById('liveTarget').value = s.target || ''
  }catch(e){console.error(e); alert('Load settings failed')}
})

document.getElementById('btnSaveSettings').addEventListener('click', async ()=>{
  const payload = {
    title: document.getElementById('liveTitle').value.trim(),
    description: document.getElementById('liveDescription').value.trim(),
    platform: document.getElementById('livePlatform').value,
    target: document.getElementById('liveTarget').value.trim()
  }
  try{
    await api('/stream/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
    alert('Settings saved')
  }catch(e){console.error(e); alert('Save failed')}
})

async function loadApiKey(){
  try{
    const res = await api('/stream/apikey')
    document.getElementById('liveApiKey').value = res.key || ''
  }catch(e){console.error(e)}
}

document.getElementById('btnGenKey').addEventListener('click', async ()=>{
  if(!confirm('Regenerate API key? This will replace the existing key.')) return
  try{
    const res = await fetch(API_BASE + '/stream/apikey', {method:'POST'})
    const j = await res.json()
    if(res.ok){ document.getElementById('liveApiKey').value = j.key; alert('API key regenerated') }
    else alert('Regenerate failed')
  }catch(e){console.error(e); alert('API key request failed')}
})

// load key on start
loadApiKey()
