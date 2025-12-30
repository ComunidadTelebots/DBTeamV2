document.addEventListener('DOMContentLoaded', function(){
  const endpointEl = document.getElementById('endpoint')
  const providerEl = document.getElementById('provider')
  const promptEl = document.getElementById('prompt')
  const submitBtn = document.getElementById('submit')
  const clearBtn = document.getElementById('clear')
  const responseEl = document.getElementById('response')

  clearBtn.addEventListener('click', ()=>{
    promptEl.value = ''
    responseEl.textContent = '(esperando)'
  })

  submitBtn.addEventListener('click', async ()=>{
    const endpoint = endpointEl.value.trim()
    if(!endpoint){ alert('Introduce un endpoint válido'); return }
    const provider = providerEl.value
    const prompt = promptEl.value.trim()
    if(!prompt){ alert('Escribe el prompt'); return }

    responseEl.textContent = 'Enviando...'
    try{
      const payload = { prompt: prompt }
      if(provider) payload.provider = provider

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if(!res.ok){
        const t = await res.text()
        responseEl.textContent = 'Error: ' + res.status + '\n' + t
        return
      }

      const text = await res.text()
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
