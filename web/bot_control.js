let backendUrl = '';
let backendKey = '';

function joinUrl(path){
  if(!path) return '';
  if(/^https?:\/\//i.test(path)) return path;
  if(!backendUrl) return path;
  try{ return backendUrl.replace(/\/$/, '') + path; }catch(e){ return path; }
}

async function api(path, opts={}){
  const url = joinUrl(path);
  const headers = Object.assign({}, opts.headers||{});
  if(backendKey && !headers['Authorization']){
    headers['Authorization'] = 'Bearer ' + backendKey;
  }
  const res = await fetch(url, Object.assign({credentials:'same-origin'}, opts, { headers }));
  if(!res.ok){
    const txt = await res.text().catch(()=>'');
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

async function checkCommandUsage() {
  try {
    const res = await api(`/bot/command_usage/${groupId}`);
    if(res.most_used && res.most_used.count > 50) { // Umbral de uso alto
      el('command_warning').style.display = 'block';
      el('command_warning').innerText = `Advertencia: El comando '${res.most_used.command}' se ha usado ${res.most_used.count} veces recientemente.`;
    } else {
      el('command_warning').style.display = 'none';
    }
  } catch(e) { el('command_warning').innerText = 'Error al consultar uso de comandos.'; }
}

async function loadBlockedCommands() {
  try {
    const res = await api(`/bot/blocked_commands/${groupId}`);
    const tbody = el('blocked_commands_table').querySelector('tbody');
    tbody.innerHTML = '';
    if(res && res.length) {
      res.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${row.user_id}</td><td>${row.command}</td><td>${row.unblock_time ? new Date(row.unblock_time*1000).toLocaleString() : '-'} </td><td><button data-user="${row.user_id}" data-command="${row.command}" class="unblock_cmd_btn">Desbloquear</button></td>`;
        tbody.appendChild(tr);
      });
      // Añadir eventos a los botones
      tbody.querySelectorAll('.unblock_cmd_btn').forEach(btn => {
        btn.onclick = async ()=>{
          const userId = btn.getAttribute('data-user');
          const command = btn.getAttribute('data-command');
          try{
            await api(`/bot/unblock_command/${groupId}/${userId}/${command}`,{method:'POST'});
            el('unblock_command_res').innerText = `Comando '${command}' desbloqueado para el usuario ${userId}.`;
            loadBlockedCommands();
          }catch(e){ el('unblock_command_res').innerText = 'Error: '+e.message; }
        };
      });
    } else {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="4">No hay comandos bloqueados.</td>';
      tbody.appendChild(tr);
    }
  } catch(e) {
    el('blocked_commands_table').querySelector('tbody').innerHTML = '<tr><td colspan="4">Error al cargar bloqueos.</td></tr>';
  }
}

let telegramStatsHistory = [];
function drawTelegramStatsGraph() {
  const canvas = el('telegram_stats_graph');
  if(!canvas) return;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle = '#0077cc';
  ctx.beginPath();
  telegramStatsHistory.forEach((v,i) => {
    const x = i * (canvas.width/60);
    const y = canvas.height - (v/40)*canvas.height;
    if(i===0) ctx.moveTo(x,y);
    else ctx.lineTo(x,y);
  });
  ctx.stroke();
}
async function loadTelegramStats(repeat=true) {
  try {
    const res = await api('/bot/telegram_stats');
    let html = '';
    html += `<b>Mensajes en el último segundo:</b> ${res.last_second}<br>`;
    html += `<b>Mensajes en el último minuto:</b> ${res.last_minute}<br>`;
    html += `<b>Límite global:</b> ${res.limit} msg/segundo<br>`;
    const pct = ((res.last_second/res.limit)*100).toFixed(1);
    html += `<b>Porcentaje usado:</b> ${pct}%`;
    if(pct > 80) html += `<br><span style='color:red;font-weight:bold;'>¡Advertencia: Uso alto del límite!</span>`;
    el('telegram_stats_content').innerHTML = html;
    telegramStatsHistory.push(res.last_second);
    if(telegramStatsHistory.length > 60) telegramStatsHistory = telegramStatsHistory.slice(-60);
    drawTelegramStatsGraph();
  } catch(e) {
    el('telegram_stats_content').innerText = 'Error al cargar estadísticas.';
  }
  if(repeat) setTimeout(()=>loadTelegramStats(true),1000);
}

async function loadBotsLimits() {
  try {
    const res = await api('/bot/bots_limits');
    const tbody = el('bots_limits_table').querySelector('tbody');
    tbody.innerHTML = '';
    if(res && res.length) {
      res.forEach(row => {
        const pct = ((row.last_second/row.limit)*100).toFixed(1);
        let alert = '';
        if(pct > 80) alert = "<span style='color:red;font-weight:bold;'>¡Alerta!</span>";
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${row.bot_name}</td><td>${row.last_second}</td><td>${row.limit}</td><td>${pct}% ${alert}</td>`;
        tbody.appendChild(tr);
      });
    } else {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="4">No hay datos de bots.</td>';
      tbody.appendChild(tr);
    }
  } catch(e) {
    el('bots_limits_table').querySelector('tbody').innerHTML = '<tr><td colspan="4">Error al cargar límites.</td></tr>';
  }
}
// Llamar al cargar el panel
loadTelegramStats();
loadBotsLimits();

document.addEventListener('DOMContentLoaded', ()=>{
  // restore backend config
  try{ backendUrl = localStorage.getItem('bc_backend_url') || ''; const u = el('backend_url'); if(u) u.value = backendUrl; }catch(e){}
  try{ backendKey = localStorage.getItem('bc_backend_key') || ''; const k = el('backend_key'); if(k) k.value = backendKey; }catch(e){}
  try{ const saveBtn = el('btn_save_backend'); if(saveBtn) saveBtn.addEventListener('click', ()=>{
    backendUrl = (el('backend_url')?.value||'').trim();
    backendKey = (el('backend_key')?.value||'').trim();
    try{ if(backendUrl) localStorage.setItem('bc_backend_url', backendUrl); else localStorage.removeItem('bc_backend_url'); }catch(e){}
    try{ if(backendKey) localStorage.setItem('bc_backend_key', backendKey); else localStorage.removeItem('bc_backend_key'); }catch(e){}
    el('verify_res').innerText = 'Backend guardado';
  }); }catch(e){}

  el('btn_refresh').addEventListener('click', refreshAccounts);
  el('btn_verify').addEventListener('click', verifyToken);
  el('btn_add').addEventListener('click', addDevice);
  el('btn_start').addEventListener('click', startBot);
  el('btn_stop').addEventListener('click', stopBot);
  el('btn_processes').addEventListener('click', refreshProcesses);
  el('quick_ban').onclick = async ()=>{
    const userId = el('quick_user_id').value.trim();
    if(!userId) return el('quick_res').innerText = 'Introduce el ID de usuario.';
    try{
      await api(`/bot/ban_user/${groupId}/${userId}`,{method:'POST'});
      el('quick_res').innerText = 'Usuario baneado.';
    }catch(e){ el('quick_res').innerText = 'Error: '+e.message; }
  };
  el('quick_mute').onclick = async ()=>{
    const userId = el('quick_user_id').value.trim();
    if(!userId) return el('quick_res').innerText = 'Introduce el ID de usuario.';
    try{
      await api(`/bot/mute_user/${groupId}/${userId}`,{method:'POST'});
      el('quick_res').innerText = 'Usuario muteado.';
    }catch(e){ el('quick_res').innerText = 'Error: '+e.message; }
  };
  el('quick_promote').onclick = async ()=>{
    const userId = el('quick_user_id').value.trim();
    if(!userId) return el('quick_res').innerText = 'Introduce el ID de usuario.';
    try{
      await api(`/bot/set_role/${groupId}/${userId}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({role:'admin'})});
      el('quick_res').innerText = 'Usuario promovido a admin.';
    }catch(e){ el('quick_res').innerText = 'Error: '+e.message; }
  };
  el('quick_perms').onclick = async ()=>{
    const userId = el('quick_user_id').value.trim();
    if(!userId) return el('quick_res').innerText = 'Introduce el ID de usuario.';
    // Redirigir a panel de edición de permisos (ajusta la URL si es necesario)
    window.location.href = `/owner.html?edit_perms=1&group=${encodeURIComponent(groupId)}&user=${encodeURIComponent(userId)}`;
  };
  el('quick_reply').onclick = async ()=>{
    const userId = el('quick_user_id').value.trim();
    const comment = prompt('Respuesta/comentario para la intervención:');
    if(!userId || !comment) return el('quick_res').innerText = 'Introduce el ID y comentario.';
    try{
      await api(`/admin/request_intervention/${groupId}/reply`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({user_id:userId,comment})});
      el('quick_res').innerText = 'Respuesta enviada.';
    }catch(e){ el('quick_res').innerText = 'Error: '+e.message; }
  };
  el('block_command_btn').onclick = async ()=>{
    const userId = el('block_user_id').value.trim();
    const command = el('block_command_name').value.trim();
    if(!userId || !command) return el('block_command_res').innerText = 'Introduce usuario y comando.';
    try{
      await api(`/bot/block_command/${groupId}/${userId}/${command}`,{method:'POST'});
      el('block_command_res').innerText = `Comando '${command}' bloqueado para el usuario ${userId}.`;
    }catch(e){ el('block_command_res').innerText = 'Error: '+e.message; }
  };
  refreshAccounts();
  refreshProcesses();
  checkCommandUsage();
  loadBlockedCommands();
  loadTelegramStats();
  loadBotsLimits();
});
