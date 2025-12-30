document.addEventListener('DOMContentLoaded', function(){
  const endpointEl = document.getElementById('endpoint')
  const apiBaseEl = document.getElementById('apiBase')
  const providerEl = document.getElementById('provider')
  const chatIdEl = document.getElementById('chat_id')
  const sendAsEl = document.getElementById('sendAs')
  const promptEl = document.getElementById('prompt')
  const submitBtn = document.getElementById('submit')
  const clearBtn = document.getElementById('clear')
  const responseEl = document.getElementById('response')

  clearBtn.addEventListener('click', ()=>{
    promptEl.value = ''
    responseEl.textContent = '(esperando)'
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
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        if(!res.ok){ const t = await res.text(); responseEl.textContent = 'Error: ' + res.status + '\n' + t; return }
        var text = await res.text()
      } else if(sendAs === 'bot'){
        if(!chatId){ alert('Introduce chat_id para enviar como bot'); return }
        const url = apiBase.replace(/\/$/, '') + '/send'
        const payload = { chat_id: chatId, text: prompt }
        const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
        if(!res.ok){ const t = await res.text(); responseEl.textContent = 'Error: ' + res.status + '\n' + t; return }
        var text = await res.text()
      } else if(sendAs === 'user'){
        if(!chatId){ alert('Introduce chat_id para enviar como usuario'); return }
        const url = apiBase.replace(/\/$/, '') + '/send_user'
        const payload = { chat_id: chatId, text: prompt }
        const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
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
