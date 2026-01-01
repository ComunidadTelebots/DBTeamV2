async function api(path, opts={}){
  const res = await fetch(path, Object.assign({credentials:'same-origin'}, opts));
  if(!res.ok){
    const txt = await res.text().catch(()=>'');
    throw new Error(res.status+': '+txt);
  }
  const ct = res.headers.get('content-type')||'';
  if(ct.includes('application/json')) return res.json();
  return res.text();
}

function el(id){ return document.getElementById(id); }

async function refreshAccounts(){
  const cont = el('accounts_container');
  cont.innerText = 'Cargando...';
  try{
    const list = await api('/bot/accounts');
    if(!Array.isArray(list)){
      cont.innerText = JSON.stringify(list, null, 2);
      return;
    }
    if(list.length===0){
      cont.innerText = 'No hay cuentas registradas.';
      return;
    }
    const table = document.createElement('table');
    const thead = document.createElement('thead');
    thead.innerHTML = '<tr><th>id</th><th>name</th><th>mask</th><th>me</th></tr>';
    table.appendChild(thead);
    const tb = document.createElement('tbody');
    list.forEach(it=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${it.id||''}</td><td>${it.name||''}</td><td>${it.masked_token||''}</td><td>${it.me? (it.me.username||it.me.first_name||'ok') : (it.error||'')}</td>`;
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    cont.innerHTML = '';
    cont.appendChild(table);
  }catch(err){
    cont.innerText = 'Error: '+err.message;
  }
}

async function verifyToken(){
  const token = el('token').value.trim();
  const dev = el('dev_id').value.trim();
  const name = el('dev_name').value.trim();
  if(!token){ el('verify_res').innerText='Introduce un token.'; return; }
  el('verify_res').innerText = 'Verificando...';
  try{
    const body = {token, id: dev||undefined, name: name||undefined};
    const res = await api('/bot/verify',{method:'POST', body: JSON.stringify(body), headers:{'content-type':'application/json'}});
    el('verify_res').innerText = JSON.stringify(res, null, 2);
    refreshAccounts();
  }catch(err){ el('verify_res').innerText = 'Error: '+err.message }
}

async function addDevice(){
  const token = el('token').value.trim();
  const dev = el('dev_id').value.trim();
  const name = el('dev_name').value.trim();
  if(!token){ el('verify_res').innerText='Introduce un token.'; return; }
  el('verify_res').innerText = 'Adding...';
  try{
    const body = {token, id: dev||undefined, name: name||undefined, verify:false};
    const res = await api('/bot/devices/add',{method:'POST', body: JSON.stringify(body), headers:{'content-type':'application/json'}});
    el('verify_res').innerText = JSON.stringify(res, null, 2);
    refreshAccounts();
  }catch(err){ el('verify_res').innerText = 'Error: '+err.message }
}

async function startBot(){
  el('process_res').innerText = 'Starting...';
  try{
    const res = await api('/bot/start',{method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({cmd:'python_bot'})});
    el('process_res').innerText = JSON.stringify(res, null, 2);
  }catch(err){ el('process_res').innerText = 'Error: '+err.message }
}

async function stopBot(){
  el('process_res').innerText = 'Stopping...';
  try{
    const res = await api('/processes/stop',{method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({name:'python_bot'})});
    el('process_res').innerText = JSON.stringify(res, null, 2);
  }catch(err){ el('process_res').innerText = 'Error: '+err.message }
}

async function refreshProcesses(){
  el('process_res').innerText = 'Cargando...';
  try{
    const res = await api('/processes/list');
    el('process_res').innerText = JSON.stringify(res, null, 2);
  }catch(err){ el('process_res').innerText = 'Error: '+err.message }
}

document.addEventListener('DOMContentLoaded', ()=>{
  el('btn_refresh').addEventListener('click', refreshAccounts);
  el('btn_verify').addEventListener('click', verifyToken);
  el('btn_add').addEventListener('click', addDevice);
  el('btn_start').addEventListener('click', startBot);
  el('btn_stop').addEventListener('click', stopBot);
  el('btn_processes').addEventListener('click', refreshProcesses);
  refreshAccounts();
  refreshProcesses();
});
