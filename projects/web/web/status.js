async function loadStatus(){
  const out = document.getElementById('out');
  out.textContent = 'Consultando /status ...';
  try{
    // try multiple candidate endpoints to be robust against mounting differences
    const candidates = ['/status', '/status/', '/api/status', 'http://localhost:5500/status'];
    let res = null;
    let lastErr = null;
    for(const url of candidates){
      try{
        res = await fetch(url);
        if(res && res.ok) break;
      }catch(err){
        lastErr = err;
        res = null;
      }
    }
    if(!res){
      out.textContent = 'Error al consultar /status: no response (is the API running?)';
      if(lastErr) out.textContent += '\n' + (lastErr.message || String(lastErr));
      return;
    }
    if(!res.ok){
      // show response body when available to help debug 404/500
      let body = '';
      try{ body = await res.text(); }catch(e){}
      out.textContent = `Error al consultar /status: ${res.status} ${res.statusText}\n${body}`;
      return;
    }
    const j = await res.json();
    // update semaphore UI
    try{ updateSemaphore(j); }catch(e){}
    // analyze pages listed in the status JSON
    try{ analyzePages(j.pages || j.pages); }catch(e){}
    // build a readable display with explanations
    const lines = [];
    lines.push(`Server time: ${new Date(j.time*1000).toLocaleString()}`);
    lines.push(`Uptime (s): ${j.uptime}`);
    lines.push('\nRedis:');
    if(j.redis){
      lines.push(`  ok: ${j.redis.ok}`);
      if(j.redis.connected_clients !== undefined) lines.push(`  connected_clients: ${j.redis.connected_clients}`);
      if(j.redis.used_memory_human) lines.push(`  used_memory: ${j.redis.used_memory_human}`);
      if(j.redis.error) lines.push(`  error: ${j.redis.error}`);
    }
    lines.push('\nCounts:');
    if(j.counts){
      for(const k of Object.keys(j.counts)){
        lines.push(`  ${k}: ${j.counts[k]}`);
      }
    }
    lines.push('\nAPI info:');
    if(j.api_info){
      for(const k of Object.keys(j.api_info)){
        lines.push(`  ${k}: ${j.api_info[k]}`);
      }
    }
    lines.push('\nSupported endpoints:');
    if(j.supported_endpoints && Array.isArray(j.supported_endpoints)){
      for(const ep of j.supported_endpoints){
        lines.push(`  ${ep.method} ${ep.path} — ${ep.desc}`);
      }
    }
    if(j.pages && j.pages.length){
      lines.push('\nPages:');
      for(const p of j.pages){ lines.push(`  ${p.href} — ${p.label}`); }
    }
    if(j.i18n_stats){
      lines.push('\nI18N files:');
      for(const k of Object.keys(j.i18n_stats)){
        const s = j.i18n_stats[k];
        lines.push(`  ${k}: ${s.keys} keys, ${s.bytes} bytes`);
      }
    }
    if(j.git_sha){ lines.push(`\nGit SHA: ${j.git_sha}`); }
    if(j.git_last){
      lines.push(`Git last commit: ${j.git_last.sha}`);
      if(j.git_last.author) lines.push(`  author: ${j.git_last.author}`);
      if(j.git_last.message) lines.push(`  message: ${j.git_last.message}`);
    }
    if(j.counts && j.counts.translation_suggestions_applied_per_lang){
      lines.push('\nApplied translations per language:');
      for(const k of Object.keys(j.counts.translation_suggestions_applied_per_lang)){
        lines.push(`  ${k}: ${j.counts.translation_suggestions_applied_per_lang[k]}`);
      }
    }
    // processes
    if(j.processes && j.processes.length){
      lines.push('\nProcesses:');
      for(const p of j.processes){
        lines.push(`  ${p.name}: running=${p.running} pid=${p.pid} log=${p.log}`);
      }
    }

    // TDLib / Telegram status
    if(j.tdlib){
      lines.push('\nTDLib:');
      lines.push(`  available: ${j.tdlib.available}`);
      if(j.tdlib.client_present !== undefined) lines.push(`  client_present: ${j.tdlib.client_present}`);
      if(j.tdlib.client_type) lines.push(`  client_type: ${j.tdlib.client_type}`);
      if(j.tdlib.client_running !== undefined) lines.push(`  client_running: ${j.tdlib.client_running}`);
      if(j.tdlib.ws_connections !== undefined) lines.push(`  ws_connections: ${j.tdlib.ws_connections}`);
      if(j.tdlib.events_count !== undefined) lines.push(`  events_count: ${j.tdlib.events_count}`);
      if(j.tdlib.last_event) lines.push(`  last_event: ${JSON.stringify(j.tdlib.last_event)}`);
      if(j.tdlib.auth) lines.push(`  auth: ${JSON.stringify(j.tdlib.auth)}`);
    }

    // render UI buttons after text
    out.textContent = lines.join('\n');

    // attach buttons below
    const container = document.getElementById('processControls');
    if(container){
      container.innerHTML = '';
      if(j.processes && j.processes.length){
        for(const p of j.processes){
          const row = document.createElement('div');
          row.style.marginBottom = '6px';
          const txt = document.createElement('span');
          txt.textContent = `${p.name} — running=${p.running} pid=${p.pid}`;
          const btn = document.createElement('button');
          btn.textContent = 'Restart';
          btn.style.marginLeft = '10px';
          btn.onclick = async () => {
            btn.disabled = true;
            btn.textContent = 'Restarting...';
            try{
              const headers = { 'Content-Type': 'application/json' };
              // try to get API key from localStorage (try multiple keys)
              let apiKey = localStorage.getItem('api_token') || localStorage.getItem('token') || localStorage.getItem('x_api_key');
              if(!apiKey){
                apiKey = prompt('Introduce API Key (se almacenará en localStorage para futuros usos):');
                if(apiKey){ localStorage.setItem('api_token', apiKey); }
              }
              if(apiKey){ headers['X-API-Key'] = apiKey; }

              const resp = await fetch('/processes/restart', { method: 'POST', headers, body: JSON.stringify({ name: p.name }) });
              if(!resp.ok){
                const j = await resp.json().catch(()=>({error:resp.statusText}));
                alert('Restart failed: '+(j.detail||j.error||resp.statusText));
              } else {
                alert('Restarted '+p.name);
              }
            }catch(e){ alert('Error: '+(e.message||e)); }
            btn.disabled = false; btn.textContent = 'Restart';
            loadStatus();
          };
          row.appendChild(txt);
          row.appendChild(btn);
          container.appendChild(row);
        }
      }
    }

    if(j.explanations){
      lines.push('\nExplanations:');
      for(const k of Object.keys(j.explanations)){
        lines.push(`  ${k}: ${j.explanations[k]}`);
      }
    }
  }catch(e){
    out.textContent = 'Error de conexión: '+(e.message||e);
    try{ setSemaphoreError('API unreachable'); }catch(_){}
  }
}

function setSemaphoreColor(color, label){
  const dot = document.getElementById('semaforo-dot');
  const lab = document.getElementById('semaforo-label');
  if(dot) dot.style.background = color;
  if(lab) lab.textContent = label;
}

function setSemaphoreError(msg){
  setSemaphoreColor('#e74c3c', msg || 'Error');
  const r = document.getElementById('semaforo-redis'); if(r) r.textContent = 'error';
  const t = document.getElementById('semaforo-tdlib'); if(t) t.textContent = 'error';
  const p = document.getElementById('semaforo-procs'); if(p) p.textContent = 'error';
  const b = document.getElementById('semaforo-bot'); if(b) b.textContent = 'error';
}

function updateSemaphore(j){
  // compute per-component statuses
  const redisOk = j && j.redis && j.redis.ok === true;
  const tdlib = j && j.tdlib ? j.tdlib : null;
  const tdAvailable = tdlib && tdlib.available;
  const tdRunning = tdlib && (tdlib.client_running === true || tdlib.client_present === true);
  const procs = j && j.processes ? j.processes : [];
  const procsRunning = procs.length ? procs.filter(p=>p.running).length : 0;
  const procsTotal = procs.length;
  const botSet = j && j.api_info && j.api_info.bot_token_set;

  // overall status: red if Redis down or no processes running, yellow if tdlib available but not running or bot missing, green otherwise
  let overall = 'unknown';
  let color = '#999';
  if(!redisOk || (procsTotal>0 && procsRunning===0)){
    overall = 'CRITICAL'; color = '#e74c3c';
  } else if((tdAvailable && !tdRunning) || !botSet){
    overall = 'WARNING'; color = '#f1c40f';
  } else {
    overall = 'OK'; color = '#2ecc71';
  }

  setSemaphoreColor(color, overall);

  // details
  const rEl = document.getElementById('semaforo-redis'); if(rEl) rEl.textContent = redisOk ? 'OK' : 'DOWN';
  const tEl = document.getElementById('semaforo-tdlib');
  if(tEl) tEl.textContent = tdAvailable ? (tdRunning ? 'Running' : 'Stopped') : 'Unavailable';
  const pEl = document.getElementById('semaforo-procs'); if(pEl) pEl.textContent = procsTotal ? `${procsRunning}/${procsTotal}` : 'none';
  const bEl = document.getElementById('semaforo-bot'); if(bEl) bEl.textContent = botSet ? 'configured' : 'missing';
}

async function fetchWithTimeout(url, ms = 3000){
  const controller = new AbortController();
  const id = setTimeout(()=>controller.abort(), ms);
  try{
    const res = await fetch(url, { signal: controller.signal });
    clearTimeout(id);
    return res;
  }catch(e){ clearTimeout(id); throw e; }
}

async function analyzePages(pages){
  const container = document.getElementById('pages-list');
  if(!container) return;
  container.innerHTML = '';
  if(!pages || !pages.length){
    container.innerHTML = '<div style="color:#666">No hay páginas listadas.</div>';
    return;
  }
  // concurrent checks
  const checks = pages.map(p=>({ href: p.href || p, label: p.label || p.href || p }));
  const results = await Promise.all(checks.map(async (c)=>{
    const el = document.createElement('div');
    el.style.display = 'flex'; el.style.alignItems = 'center'; el.style.gap = '8px';
    const dot = document.createElement('div'); dot.style.width='12px'; dot.style.height='12px'; dot.style.borderRadius='50%'; dot.style.background='#999';
    const txt = document.createElement('div'); txt.style.flex='1'; txt.textContent = c.label + ' ('+c.href+')';
    const status = document.createElement('div'); status.style.minWidth='140px'; status.style.textAlign='right'; status.textContent = 'checking...';
    el.appendChild(dot); el.appendChild(txt); el.appendChild(status);
    container.appendChild(el);

    // try multiple candidate locations for the page
    const candidates = [c.href, '/'+c.href.replace(/^\/+/, ''), location.origin + '/' + c.href.replace(/^\/+/, '')];
    let ok = false; let usedUrl = ''; let code = null; let timeMs = null; let errMsg = null;
    for(const url of candidates){
      try{
        const t0 = Date.now();
        const r = await fetchWithTimeout(url, 3000);
        timeMs = Date.now()-t0;
        if(r){ code = r.status; usedUrl = url; if(r.ok) {
          // read body and extract <title>
          let title = '';
          try{
            const txt = await r.text();
            const m = txt.match(/<title[^>]*>([^<]*)<\/title>/i);
            if(m && m[1]) title = m[1].trim();
          }catch(e){ /* ignore */ }
          ok = true; dot.style.background = '#2ecc71';
          status.textContent = `OK ${code} — ${timeMs} ms` + (title? ` — "${title}"` : '');
          break;
        } else { /* continue to next */ } }
      }catch(e){ errMsg = e.message || String(e); }
    }
    if(!ok){ dot.style.background = '#e74c3c'; status.textContent = `Error ${code || ''} ${errMsg || ''}`; }
    return { href: c.href, ok, code, timeMs, errMsg };
  }));
  return results;
}
window.addEventListener('load', ()=>{ loadStatus(); setInterval(loadStatus, 5000); });
