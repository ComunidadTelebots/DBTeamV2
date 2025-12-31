document.addEventListener('DOMContentLoaded', function(){
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

  // Telegram Login Widget callback (global)
  window.onTelegramAuth = async function(user){
    // send auth payload to backend to verify signature
    try{
      const apiBase = apiBaseEl.value.trim()
      if(!apiBase) { alert('Introduce la URL base de la API para autenticar'); return }
      const url = apiBase.replace(/\/$/, '') + '/auth'
      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type':'application/json' }, body: JSON.stringify(user) })
      if(!res.ok){ const t = await res.text(); alert('Auth failed: '+res.status+' '+t); return }
      const j = await res.json()
      if(j && j.token){
        if(apiKeyEl) apiKeyEl.value = j.token
        if(localStorage && localStorage.setItem) localStorage.setItem('web_session_token', j.token)
        // refresh devices now that we're authenticated
        fetchDevices(apiBase)
        alert('Autenticado como ' + (user.first_name || user.username || user.id))
      }
    }catch(e){ alert('Error auth: '+e.toString()) }
  }

  clearBtn.addEventListener('click', ()=>{
    promptEl.value = ''
    responseEl.textContent = '(esperando)'
  })

  async function fetchDevices(apiBase) {
    deviceSelectEl.innerHTML = '<option value="">(usar BOT_TOKEN por defecto)</option>'
    if(!apiBase) return
    try{
      const url = apiBase.replace(/\/$/, '') + '/devices'
       const headers = { 'Content-Type': 'application/json' }
       const apiKey = (apiKeyEl && apiKeyEl.value) ? apiKeyEl.value.trim() : ''
       if(apiKey) headers['Authorization'] = 'Bearer ' + apiKey
       const res = await fetch(url, { headers })
      if(!res.ok) return
      const list = await res.json()
      list.forEach(d => {
        const opt = document.createElement('option')
        opt.value = d.id || d.name || ''
        opt.textContent = (d.name ? d.name + ' (' + opt.value + ')' : opt.value)
        deviceSelectEl.appendChild(opt)
      })
    }catch(e){ /* ignore */ }
  }

  refreshDevicesBtn.addEventListener('click', ()=>{
    const apiBase = apiBaseEl.value.trim()
    fetchDevices(apiBase)
  })

  // initial fetch (use default value)
  fetchDevices(apiBaseEl.value.trim())

  // Add device handler
  const addDeviceBtn = document.getElementById('addDevice')
  const newDeviceIdEl = document.getElementById('new_device_id')
  const newDeviceNameEl = document.getElementById('new_device_name')
  const newDeviceTokenEl = document.getElementById('new_device_token')
  addDeviceBtn.addEventListener('click', async ()=>{
    const apiBase = apiBaseEl.value.trim()
    if(!apiBase){ alert('Introduce la URL base de la API'); return }
    const id = (newDeviceIdEl && newDeviceIdEl.value) ? newDeviceIdEl.value.trim() : ''
    const token = (newDeviceTokenEl && newDeviceTokenEl.value) ? newDeviceTokenEl.value.trim() : ''
    if(!id || !token){ alert('ID y token son obligatorios'); return }
    const name = (newDeviceNameEl && newDeviceNameEl.value) ? newDeviceNameEl.value.trim() : ''
    const url = apiBase.replace(/\/$/, '') + '/devices/add'
    const headers = { 'Content-Type': 'application/json' }
    const apiKey = (apiKeyEl && apiKeyEl.value) ? apiKeyEl.value.trim() : ''
    if(apiKey) headers['Authorization'] = 'Bearer ' + apiKey
    try{
      const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify({ id: id, name: name, token: token }) })
      if(!res.ok){ const t = await res.text(); alert('Error: '+res.status+' '+t); return }
      alert('Dispositivo añadido')
      // refresh device list
      fetchDevices(apiBase)
      newDeviceIdEl.value = ''
      newDeviceNameEl.value = ''
      newDeviceTokenEl.value = ''
    }catch(e){ alert('Error de red: '+e.toString()) }
  })

  submitBtn.addEventListener('click', async ()=>{
    const apiBase = apiBaseEl.value.trim()
    const endpoint = endpointEl.value.trim()
    if(!apiBase){ alert('Introduce la URL base de la API (por ejemplo http://localhost:8081)'); return }
    const provider = providerEl.value
    const chatId = chatIdEl.value.trim()
    const sendAs = sendAsEl.value
    const prompt = promptEl.value.trim()
    if(!prompt){ alert('Escribe el prompt'); return }

    responseEl.textContent = 'Enviando...'
    try{
      if(sendAs === 'ai'){
        const payload = { prompt: prompt }
        if(provider) payload.provider = provider
        const res = await fetch(endpoint, {
          method: 'POST',
           headers: (function(){ const h = { 'Content-Type':'application/json' }; const k = (apiKeyEl && apiKeyEl.value)?apiKeyEl.value.trim():''; if(k) h['Authorization']='Bearer '+k; return h })(),
          body: JSON.stringify(payload)
        })
        if(!res.ok){ const t = await res.text(); responseEl.textContent = 'Error: ' + res.status + '\n' + t; return }
        var text = await res.text()
      } else if(sendAs === 'bot'){
        if(!chatId){ alert('Introduce chat_id para enviar como bot'); return }
        const url = apiBase.replace(/\/$/, '') + '/send'
        const payload = { chat_id: chatId, text: prompt }
        if(deviceSelectEl && deviceSelectEl.value) payload.device_id = deviceSelectEl.value
          const headers = { 'Content-Type': 'application/json' }
          const apiKey = (apiKeyEl && apiKeyEl.value) ? apiKeyEl.value.trim() : ''
          if(apiKey) headers['Authorization'] = 'Bearer ' + apiKey
          const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify(payload) })
        if(!res.ok){ const t = await res.text(); responseEl.textContent = 'Error: ' + res.status + '\n' + t; return }
        var text = await res.text()
      } else if(sendAs === 'user'){
        if(!chatId){ alert('Introduce chat_id para enviar como usuario'); return }
        const url = apiBase.replace(/\/$/, '') + '/send_user'
        const payload = { chat_id: chatId, text: prompt }
        if(deviceSelectEl && deviceSelectEl.value) payload.device_id = deviceSelectEl.value
          const headers = { 'Content-Type': 'application/json' }
          const apiKey = (apiKeyEl && apiKeyEl.value) ? apiKeyEl.value.trim() : ''
          if(apiKey) headers['Authorization'] = 'Bearer ' + apiKey
          const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify(payload) })
        if(!res.ok){ const t = await res.text(); responseEl.textContent = 'Error: ' + res.status + '\n' + t; return }
        var text = await res.text()
      }

      // `text` contains either raw text or JSON
      
      // continue with previous parsing logic
      // Many local LLM endpoints return raw text; others return JSON.
      try{
        const parsed = JSON.parse(text)
        // Try common shapes
        if(typeof parsed === 'object'){
          if(parsed.text) responseEl.textContent = parsed.text
          else if(parsed.output) responseEl.textContent = JSON.stringify(parsed.output, null, 2)
          else responseEl.textContent = JSON.stringify(parsed, null, 2)
        } else {
          responseEl.textContent = String(parsed)
        }
      } catch(e){
        responseEl.textContent = text
      }

    } catch(err){
      responseEl.textContent = 'Error de red: ' + err.toString()
    }
  })

})
