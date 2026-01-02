document.addEventListener('DOMContentLoaded', function(){
  const chatWindow = document.getElementById('chatWindow')
  const chatInput = document.getElementById('chatInput')
  const sendChatBtn = document.getElementById('sendChatBtn')
  const chatModelSelect = document.getElementById('chatModelSelect')
  const modelsList = document.getElementById('modelsList')
  const fillExampleBtn = document.getElementById('fillExampleBtn')
  const examplePrompt = document.getElementById('examplePrompt')
  const clearChatBtn = document.getElementById('clearChatBtn')

  function headers(){ return {'Content-Type':'application/json'} }
  function getApiBase(){ const el = document.getElementById('apiBase'); if(el && el.value) return el.value.replace(/\/$/,''); return 'http://127.0.0.1:8081' }

  // Catalog of popular open-source models
  const KNOWN_MODELS = [
    'gpt2', 'distilgpt2', 'bigscience/bloom-560m', 'EleutherAI/gpt-neo-125M', 'EleutherAI/gpt-neo-1.3B',
    'EleutherAI/gpt-j-6B', 'facebook/opt-125m', 'facebook/opt-350m', 'facebook/opt-1.3b',
    'bigscience/bigscience-small-testing', 'tiiuae/falcon-7b', 'openlm-research/open_llama_3b',
    'huggingface/CodeGen-350M-mono', 'google/flan-t5-small'
  ]

  function appendMessage(role, text){
    const box = document.createElement('div'); box.style.marginBottom='12px'; box.style.display='flex'; box.style.flexDirection='column'
    const who = document.createElement('div'); who.style.fontWeight='700'; who.style.marginBottom='6px'; who.textContent = (role==='user'?'Tú':'Modelo')
    const msg = document.createElement('div'); msg.textContent = text; msg.style.whiteSpace='pre-wrap'; msg.style.padding='10px'; msg.style.borderRadius='8px'; msg.style.boxShadow='0 1px 2px rgba(0,0,0,0.06)'
    // color selection: prefer per-user color for user role; assistant uses owner color
    try{
      const users = JSON.parse(localStorage.getItem('user_colors') || '{}')
      if(role === 'user'){
        const key = localStorage.getItem('chat_user') || 'me'
        const c = (users && users[key]) ? users[key] : '#dbeeff'
        msg.style.background = c; msg.style.color = (contrastYIQ(c)==='dark'? '#000' : '#022'); msg.style.alignSelf = 'flex-end'
      } else {
        const owner = localStorage.getItem('owner_color') || getComputedStyle(document.documentElement).getPropertyValue('--owner-color') || '#1e6fff'
        msg.style.background = owner; msg.style.color = (contrastYIQ(owner)==='dark' ? '#000' : '#fff'); msg.style.alignSelf = 'flex-start'
      }
    }catch(e){
      if(role === 'user'){ msg.style.background = '#dbeeff'; msg.style.color = '#022'; msg.style.alignSelf = 'flex-end' }
      else { msg.style.background = '#e6f0ff'; msg.style.color = '#022'; msg.style.alignSelf = 'flex-start' }
    }

    function contrastYIQ(hexcolor){ try{ const c = hexcolor.replace('#',''); const r=parseInt(c.substr(0,2),16); const g=parseInt(c.substr(2,2),16); const b=parseInt(c.substr(4,2),16); const yiq = ((r*299)+(g*587)+(b*114))/1000; return (yiq >= 128) ? 'dark' : 'light'; }catch(e){return 'light'} }
    box.appendChild(who); box.appendChild(msg); chatWindow.appendChild(box); chatWindow.scrollTop = chatWindow.scrollHeight
  }

  async function loadModels(){
    modelsList.innerHTML = ''
    chatModelSelect.innerHTML = ''
    try{
      const r = await fetch(getApiBase() + '/models/list')
      if(!r.ok) throw new Error('no models')
      const js = await r.json(); const arr = js.models || []
      if(arr.length===0){
        modelsList.textContent='(no hay modelos instalados)'
        const opt = document.createElement('option'); opt.value='gpt2'; opt.textContent='gpt2 (default)'; chatModelSelect.appendChild(opt); return
      }
      // combine installed models with known catalog, installed first
      const combined = Array.from(new Set([...(arr || []), ...KNOWN_MODELS]))
      combined.forEach(m=>{
        const div = document.createElement('div'); div.style.padding='6px 0'; div.textContent = m
        if((arr||[]).indexOf(m) !== -1){ const tag = document.createElement('span'); tag.textContent=' INSTALLED'; tag.style.color='green'; tag.style.marginLeft='8px'; tag.style.fontWeight='600'; div.appendChild(tag) }
        const opt = document.createElement('option'); opt.value = m; opt.textContent = m; chatModelSelect.appendChild(opt)
        modelsList.appendChild(div)
      })
      // prefer gpt2 as default if present
      try{ const opt = Array.from(chatModelSelect.options).find(o=>o.value === 'gpt2'); if(opt) chatModelSelect.value = 'gpt2' }catch(e){}
    }catch(e){ modelsList.textContent='(no disponible)'; const opt = document.createElement('option'); opt.value='gpt2'; opt.textContent='gpt2 (default)'; chatModelSelect.appendChild(opt) }
  }

  async function sendMessage(){
    const text = (chatInput.value || '').trim(); if(!text) return
    const model = (chatModelSelect.value || 'gpt2')
    appendMessage('user', text)
    chatInput.value = ''
    // call models/run
    try{
      const res = await fetch(getApiBase() + '/models/run', { method:'POST', headers: headers(), body: JSON.stringify({ model: model, prompt: text }) })
      if(!res.ok){ const t = await res.text(); appendMessage('assistant', 'Error: '+t); return }
      const js = await res.json()
      let out = ''
      if(js && js.result){
        if(Array.isArray(js.result) && js.result.length>0 && js.result[0].generated_text) out = js.result[0].generated_text
        else out = JSON.stringify(js.result)
      } else {
        out = JSON.stringify(js)
      }
      appendMessage('assistant', out)
    }catch(e){ appendMessage('assistant', 'Error: '+(e.message||e)) }
  }

  sendChatBtn && sendChatBtn.addEventListener('click', sendMessage)
  chatInput && chatInput.addEventListener('keydown', (e)=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendMessage() } })
  fillExampleBtn && fillExampleBtn.addEventListener('click', ()=>{ chatInput.value = examplePrompt.value || '' })
  clearChatBtn && clearChatBtn.addEventListener('click', ()=>{ chatWindow.innerHTML = '' })

  // initial
  loadModels()
})
