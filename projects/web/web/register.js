// Minimal registration script: calls /auth/register then /auth/login to obtain token
document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const user = document.getElementById('user').value.trim();
  const pass = document.getElementById('pass').value;
  const msg = document.getElementById('msg');
  msg.textContent = '';
  try {
    const baseConfigured = (window.__API_BASE__ && window.__API_BASE__.trim()) || '';
    // try same-origin first
    let regResp = null;
    try{
      regResp = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user, pass })
      });
    }catch(e){ regResp = null }
    // fallback to configured or default API host
      if(!regResp || !regResp.ok){
      const base = baseConfigured || 'http://127.0.0.1:5500';
      try{
        regResp = await fetch(base + '/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user, pass })
        });
      }catch(e){ regResp = null }
    }
    if (!regResp || !regResp.ok) {
      const j = await (regResp ? regResp.json().catch(()=>({error:regResp.statusText})) : Promise.resolve({error:'no response'}));
      msg.textContent = j.error || 'Registro fallido';
      return;
    }
    // auto-login: try same-origin then fallback
    let loginResp = null;
    try{ loginResp = await fetch('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user, pass }) }); }catch(e){ loginResp = null }
    if(!loginResp || !loginResp.ok){
      const base = baseConfigured || 'http://127.0.0.1:5500';
      try{ loginResp = await fetch(base + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user, pass }) }); }catch(e){ loginResp = null }
    }
    if (!loginResp.ok) {
      msg.textContent = 'Registro correcto, pero login automático falló.';
      return;
    }
    const data = await loginResp.json();
    if (data && data.token) {
      localStorage.setItem('token', data.token);
      window.location.href = 'index.html';
    } else {
      msg.textContent = 'Registro correcto, token no recibido.';
    }
  } catch (err) {
    msg.textContent = err.message || String(err);
  }
});
