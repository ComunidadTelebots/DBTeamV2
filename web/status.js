async function loadStatus(){
  const out = document.getElementById('out');
  out.textContent = 'Consultando /status ...';
  try{
    const res = await fetch('/status');
    if(!res.ok){
      out.textContent = `Error al consultar /status: ${res.status} ${res.statusText}`;
      return;
    }
    const j = await res.json();
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
  }
}
window.addEventListener('load', ()=>{ loadStatus(); setInterval(loadStatus, 5000); });
