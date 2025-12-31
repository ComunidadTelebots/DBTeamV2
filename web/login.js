// Minimal login logic: try authenticate against python_api /auth (POST {user, pass})
// If API returns {token} store in localStorage as `api_token`.
(function(){
  const inputUser = document.getElementById('inputUser');
  const inputPass = document.getElementById('inputPass');
  const btn = document.getElementById('btnLogin');
  const btnUseKey = document.getElementById('btnUseKey');
  const msg = document.getElementById('msg');

  function show(text){ msg.textContent = text }

  btn.addEventListener('click', async ()=>{
    show('Autenticando...');
    try{
      // Read API base from the page (allows custom port)
      const apiBaseInput = document.getElementById('apiBaseLogin');
      const apiBaseVal = apiBaseInput && apiBaseInput.value ? apiBaseInput.value.replace(/\/+$/, '') : 'http://127.0.0.1:5500';
      // Try same-origin first, then fallback to the configured API base
      let res = null;
      try{
        res = await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user: inputUser.value, pass: inputPass.value })
        });
      }catch(e){
        // network error — fall through to fallback attempt
      }
      if(!res || !res.ok){
        try{
          res = await fetch(apiBaseVal + '/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: inputUser.value, pass: inputPass.value })
          });
        }catch(e){
          res = null;
        }
      }
      if(!res || !res.ok){
        show('Credenciales inválidas o servidor inaccesible');
        return;
      }
      const data = await res.json();
      if(data.token){
        localStorage.setItem('api_token', data.token);
        show('Autenticado. Redirigiendo...');
        setTimeout(()=> location.href = '/', 600);
      }else{
        show('Respuesta inesperada del servidor');
      }
    }catch(e){
      show('Error de conexión');
    }
  });

  btnUseKey.addEventListener('click', ()=>{
    const key = prompt('Pega tu API Key:');
    if(key){ localStorage.setItem('api_token', key); show('API Key guardada. Redirigiendo...'); setTimeout(()=> location.href='/',600) }
  });

  // Registration flow
  const btnRegister = document.getElementById('btnRegister');
  const registerRow = document.getElementById('registerRow');
  const isAdminChk = document.getElementById('isAdmin');
  let registerMode = false;
  btnRegister.addEventListener('click', async ()=>{
    if(!registerMode){
      // switch to register mode
      registerMode = true;
      registerRow.style.display = 'block';
      btnRegister.textContent = 'Confirmar registro';
      btnLogin.textContent = 'Cancelar';
      return;
    }

    // perform registration
    show('Registrando...');
      try{
        const apiBaseInput = document.getElementById('apiBaseLogin');
        const apiBaseVal = apiBaseInput && apiBaseInput.value ? apiBaseInput.value.replace(/\/+$/, '') : 'http://127.0.0.1:5500';
      const payload = { user: inputUser.value, pass: inputPass.value, is_admin: !!(isAdminChk && isAdminChk.checked) };
      let res = null;
      try{
        res = await fetch('/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      }catch(e){}
      if(!res || !res.ok){
        try{ res = await fetch(apiBaseVal + '/auth/register', { method:'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }catch(e){}
      }
      if(!res){ show('Servidor de registro inaccesible'); return; }
      if(res.status === 409){ show('El usuario ya existe'); return; }
      if(!res.ok){ show('Error de registro'); return; }
      // registration ok — auto-login
      show('Registro correcto — iniciando sesión...');
      const loginRes = await fetch((location.origin+'/auth/login'), { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ user: inputUser.value, pass: inputPass.value }) }).catch(()=>null);
      let final = loginRes;
      if(!final || !final.ok){
        try{ final = await fetch(apiBaseVal + '/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ user: inputUser.value, pass: inputPass.value }) }); }catch(e){ final = null }
      }
      if(final && final.ok){ const data = await final.json(); localStorage.setItem('api_token', data.token); show('Registrado e identificado.'); setTimeout(()=> location.href='/',600); }
      else { show('Registro OK pero no se pudo iniciar sesión automáticamente'); }
    }catch(e){ show('Error de registro'); }
    finally{
      // reset UI
      registerMode = false;
      registerRow.style.display = 'none';
      btnRegister.textContent = 'Registrarse';
      btnLogin.textContent = 'Entrar';
    }
  });
})();
