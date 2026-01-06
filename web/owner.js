    // --- Panel unificado de chats y ban ---
    async function loadUnifiedChats() {
      const panel = document.getElementById('unifiedChatsPanel');
      panel.innerHTML = 'Cargando...';
      let apiId = localStorage.getItem('tdlibApiId') || '';
      let apiHash = localStorage.getItem('tdlibApiHash') || '';
      if (!apiId || !apiHash) {
        apiId = prompt('Introduce tu Telegram api_id para TDLib:');
        if (!apiId) { panel.innerHTML = '<span style=\"color:#f44\">Debes introducir api_id para ver chats.</span>'; return; }
        apiHash = prompt('Introduce tu Telegram api_hash para TDLib:');
        if (!apiHash) { panel.innerHTML = '<span style=\"color:#f44\">Debes introducir api_hash para ver chats.</span>'; return; }
        localStorage.setItem('tdlibApiId', apiId);
        localStorage.setItem('tdlibApiHash', apiHash);
      }
      try {
        // Obtener chats de bots clásicos
        const classicResp = await fetch('/bot/groups', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
        // Obtener chats de TDLib
        const tdlibResp = await fetch('/tdlib/chats', { headers: { 'x-tdlib-api-id': apiId, 'x-tdlib-api-hash': apiHash, 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
        let html = '';
        if (classicResp.ok) {
          const js = await classicResp.json();
          const chats = js.groups || [];
          if (chats.length) {
            html += `<div style='margin-bottom:10px'><b>Bots clásicos</b></div>`;
            chats.forEach(chat => {
              html += `<div style='margin-bottom:10px;padding:8px 10px;background:#222;border-radius:8px'>`;
              html += `<b>${chat.title || chat.id}</b> <span style='color:#888'>(${chat.type || ''})</span><br/>`;
              if (chat.members && chat.members.length) {
                html += `<div style='margin-top:4px;font-size:0.97em;color:#ccc'>Miembros: ${chat.members.length}</div>`;
                chat.members.slice(0,3).forEach(m => {
                  html += `<div style='display:inline-block;margin-right:8px'>${m.username || m.id || '[user]'}` +
                    ` <button class='banUserBtn' data-user='${m.id}'>Ban</button></div>`;
                });
              }
              html += `</div>`;
            });
          }
        }
        if (tdlibResp.ok) {
          const chats = await tdlibResp.json();
          if (chats.length) {
            html += `<div style='margin:16px 0 10px 0'><b>TDLib</b></div>`;
            chats.forEach(chat => {
              html += `<div style='margin-bottom:10px;padding:8px 10px;background:#222;border-radius:8px'>`;
              html += `<b>${chat.title || chat.id}</b> <span style='color:#888'>(${chat.type || ''})</span><br/>`;
              if (chat.members && chat.members.length) {
                html += `<div style='margin-top:4px;font-size:0.97em;color:#ccc'>Miembros: ${chat.members.length}</div>`;
                chat.members.slice(0,3).forEach(m => {
                  html += `<div style='display:inline-block;margin-right:8px'>${m.username || m.id || '[user]'}` +
                    ` <button class='banUserBtn' data-user='${m.id}'>Ban</button></div>`;
                });
              }
              html += `</div>`;
            });
          }
        }
        panel.innerHTML = html || '<span style="color:#888">No hay chats.</span>';
        // Asignar eventos a los botones de ban
        panel.querySelectorAll('.banUserBtn').forEach(btn => {
          btn.onclick = async function() {
            const userId = this.getAttribute('data-user');
            if (!userId) return;
            if (!confirm('¿Banear usuario ' + userId + '?')) return;
            try {
              const resp = await fetch('/group/ban', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                body: JSON.stringify({ group_id: userId })
              });
              if (resp.ok) {
                alert('Usuario baneado');
                loadUnifiedChats();
              } else {
                alert('Error al banear');
              }
            } catch (e) {
              alert('Error de red');
            }
          };
        });
      } catch (e) {
        panel.innerHTML = '<span style="color:#f44">Error de red.</span>';
      }
    }
    document.getElementById('reloadUnifiedChatsBtn').onclick = loadUnifiedChats;
    loadUnifiedChats();
  // --- Panel tipo chat: Bots clásicos ---
  async function loadClassicChats() {
    const panel = document.getElementById('classicChatsPanel');
    panel.innerHTML = 'Cargando...';
    try {
      const resp = await fetch('/bot/groups', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
      if (resp.ok) {
        const js = await resp.json();
        const chats = js.groups || [];
        if (!chats.length) { panel.innerHTML = '<span style="color:#888">No hay chats.</span>'; return; }
        let html = '';
        chats.forEach(chat => {
          html += `<div style='margin-bottom:10px;padding:8px 10px;background:#222;border-radius:8px'>`;
          html += `<b>${chat.title || chat.id}</b> <span style='color:#888'>(${chat.type || ''})</span><br/>`;
          if (chat.messages && chat.messages.length) {
            html += `<div style='margin-top:4px'>`;
            chat.messages.slice(0,3).forEach(msg => {
              html += `<div style='color:#ccc;font-size:0.97em;margin-bottom:2px'>${msg.text || '[sin texto]'}</div>`;
            });
            html += `</div>`;
          }
          html += `</div>`;
        });
        panel.innerHTML = html;
      } else {
        panel.innerHTML = '<span style="color:#f44">Error cargando chats.</span>';
      }
    } catch (e) {
      panel.innerHTML = '<span style="color:#f44">Error de red.</span>';
    }
  }
  document.getElementById('reloadClassicChatsBtn').onclick = loadClassicChats;
  loadClassicChats();

  // --- Panel tipo chat: TDLib ---
  async function loadTdlibChats() {
    const panel = document.getElementById('tdlibChatsPanel');
    panel.innerHTML = 'Cargando...';
    let apiId = localStorage.getItem('tdlibApiId') || '';
    let apiHash = localStorage.getItem('tdlibApiHash') || '';
    if (!apiId || !apiHash) {
      apiId = prompt('Introduce tu Telegram api_id para TDLib:');
      if (!apiId) { panel.innerHTML = '<span style=\"color:#f44\">Debes introducir api_id para ver chats TDLib.</span>'; return; }
      apiHash = prompt('Introduce tu Telegram api_hash para TDLib:');
      if (!apiHash) { panel.innerHTML = '<span style=\"color:#f44\">Debes introducir api_hash para ver chats TDLib.</span>'; return; }
      localStorage.setItem('tdlibApiId', apiId);
      localStorage.setItem('tdlibApiHash', apiHash);
    }
    try {
      const resp = await fetch('/tdlib/chats', { headers: { 'x-tdlib-api-id': apiId, 'x-tdlib-api-hash': apiHash, 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
      if (resp.ok) {
        const chats = await resp.json();
        if (!chats.length) { panel.innerHTML = '<span style="color:#888">No hay chats.</span>'; return; }
        let html = '';
        chats.forEach(chat => {
          html += `<div style='margin-bottom:10px;padding:8px 10px;background:#222;border-radius:8px'>`;
          html += `<b>${chat.title || chat.id}</b> <span style='color:#888'>(${chat.type || ''})</span><br/>`;
          if (chat.messages && chat.messages.length) {
            html += `<div style='margin-top:4px'>`;
            chat.messages.slice(0,3).forEach(msg => {
              html += `<div style='color:#ccc;font-size:0.97em;margin-bottom:2px'>${msg.text || '[sin texto]'}</div>`;
            });
            html += `</div>`;
          }
          html += `</div>`;
        });
        panel.innerHTML = html;
      } else {
        panel.innerHTML = '<span style="color:#f44">Error cargando chats TDLib.</span>';
      }
    } catch (e) {
      panel.innerHTML = '<span style="color:#f44">Error de red.</span>';
    }
  }
  document.getElementById('reloadTdlibChatsBtn').onclick = loadTdlibChats;
  loadTdlibChats();
document.addEventListener('DOMContentLoaded', ()=>{
  // --- Panel bots clásicos ---
  async function loadClassicBots() {
    const panel = document.getElementById('userBotsPanel');
    panel.innerHTML = 'Cargando...';
    try {
      const resp = await fetch('/bot/userbots', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
      if (resp.ok) {
        const js = await resp.json();
        const list = js.bots || [];
        if (!list.length) { panel.innerHTML = '<span style="color:#888">No hay bots de usuarios.</span>'; return; }
        const frag = document.createDocumentFragment();
        list.forEach(bot => {
          const botDiv = document.createElement('div');
          botDiv.style.background = '#222';
          botDiv.style.marginBottom = '16px';
          botDiv.style.padding = '12px';
          botDiv.style.borderRadius = '8px';
          botDiv.innerHTML = `<b>Usuario:</b> ${bot.owner} <span style='color:#6cf'>Bot: ${bot.name || bot.id}</span>`;
          const settingsDiv = document.createElement('div');
          settingsDiv.style.fontSize = '0.97em';
          settingsDiv.style.color = '#ccc';
          settingsDiv.innerHTML = `<b>Ajustes:</b> ${JSON.stringify(bot.settings || bot.info || {})}`;
          botDiv.appendChild(settingsDiv);
          frag.appendChild(botDiv);
        });
        panel.innerHTML = '';
        panel.appendChild(frag);
      }
    } catch (e) {
      panel.innerHTML = '<span style="color:#f44">Error cargando bots.</span>';
    }
  }
  document.getElementById('reloadClassicBotsBtn').onclick = loadClassicBots;
  loadClassicBots();

  // --- Panel TDLib ---
  async function loadTdlibClients() {
    const panel = document.getElementById('tdlibClientsPanel');
    panel.innerHTML = 'Cargando...';
    let apiId = localStorage.getItem('tdlibApiId') || '';
    let apiHash = localStorage.getItem('tdlibApiHash') || '';
    if (!apiId || !apiHash) {
      apiId = prompt('Introduce tu Telegram api_id para TDLib:');
      if (!apiId) { panel.innerHTML = '<span style="color:#f44">Debes introducir api_id para ver clientes TDLib.</span>'; return; }
      apiHash = prompt('Introduce tu Telegram api_hash para TDLib:');
      if (!apiHash) { panel.innerHTML = '<span style="color:#f44">Debes introducir api_hash para ver clientes TDLib.</span>'; return; }
      localStorage.setItem('tdlibApiId', apiId);
      localStorage.setItem('tdlibApiHash', apiHash);
    }
    try {
      const resp = await fetch('/tdlib/userclients', { headers: { 'x-tdlib-api-id': apiId, 'x-tdlib-api-hash': apiHash, 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
      if (resp.ok) {
        const js = await resp.json();
        const list = js.clients || [];
        if (!list.length) { panel.innerHTML = '<span style="color:#888">No hay clientes TDLib.</span>'; return; }
        const frag = document.createDocumentFragment();
        list.forEach(client => {
          const clientDiv = document.createElement('div');
          clientDiv.style.background = '#222';
          clientDiv.style.marginBottom = '16px';
          clientDiv.style.padding = '12px';
          clientDiv.style.borderRadius = '8px';
          clientDiv.innerHTML = `<b>Owner:</b> ${client.owner || '-'} <span style='color:#6cf'>TDLib: ${client.name || client.id}</span>`;
          const infoDiv = document.createElement('div');
          infoDiv.style.fontSize = '0.97em';
          infoDiv.style.color = '#ccc';
          infoDiv.innerHTML = `<b>Info:</b> ${JSON.stringify(client.info || {})}`;
          clientDiv.appendChild(infoDiv);
          frag.appendChild(clientDiv);
        });
        panel.innerHTML = '';
        panel.appendChild(frag);
      } else {
        panel.innerHTML = '<span style="color:#f44">Error cargando clientes TDLib.</span>';
      }
    } catch (e) {
      panel.innerHTML = '<span style="color:#f44">Error de red.</span>';
    }
  }
  document.getElementById('reloadTdlibClientsBtn').onclick = loadTdlibClients;
  loadTdlibClients();

  // --- Estadísticas bots clásicos ---
  async function loadClassicStats() {
    const panel = document.getElementById('classicStatsPanel');
    panel.innerHTML = 'Cargando...';
    try {
      const resp = await fetch('/bot/stats', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
      if (resp.ok) {
        const js = await resp.json();
        let html = '';
        if (js.processes) {
          html += `<div><b>Procesos:</b> <pre>${JSON.stringify(js.processes, null, 2)}</pre></div>`;
        }
        if (js.devices) {
          html += `<div><b>Dispositivos:</b> <pre>${JSON.stringify(js.devices, null, 2)}</pre></div>`;
        }
        if (js.messages_count !== undefined) {
          html += `<div><b>Mensajes:</b> ${js.messages_count}</div>`;
        }
        if (js.server_uptime !== undefined) {
          html += `<div><b>Uptime:</b> ${js.server_uptime}s</div>`;
        }
        panel.innerHTML = html;
      } else {
        panel.innerHTML = '<span style="color:#f44">Error cargando estadísticas.</span>';
      }
    } catch (e) {
      panel.innerHTML = '<span style="color:#f44">Error de red.</span>';
    }
  }
  document.getElementById('reloadClassicStatsBtn').onclick = loadClassicStats;
  loadClassicStats();

  // --- Estadísticas TDLib ---
  async function loadTdlibStats() {
    const panel = document.getElementById('tdlibStatsPanel');
    panel.innerHTML = 'Cargando...';
    let apiId = localStorage.getItem('tdlibApiId') || '';
    let apiHash = localStorage.getItem('tdlibApiHash') || '';
    if (!apiId || !apiHash) {
      apiId = prompt('Introduce tu Telegram api_id para TDLib:');
      if (!apiId) { panel.innerHTML = '<span style="color:#f44">Debes introducir api_id para ver estadísticas TDLib.</span>'; return; }
      apiHash = prompt('Introduce tu Telegram api_hash para TDLib:');
      if (!apiHash) { panel.innerHTML = '<span style="color:#f44">Debes introducir api_hash para ver estadísticas TDLib.</span>'; return; }
      localStorage.setItem('tdlibApiId', apiId);
      localStorage.setItem('tdlibApiHash', apiHash);
    }
    try {
      const chatsResp = await fetch('/tdlib/chats', { headers: { 'x-tdlib-api-id': apiId, 'x-tdlib-api-hash': apiHash, 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
      const messagesResp = await fetch('/tdlib/messages', { headers: { 'x-tdlib-api-id': apiId, 'x-tdlib-api-hash': apiHash, 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
      let html = '';
      if (chatsResp.ok) {
        const chats = await chatsResp.json();
        html += `<div><b>Chats:</b> <pre>${JSON.stringify(chats, null, 2)}</pre></div>`;
      }
      if (messagesResp.ok) {
        const messages = await messagesResp.json();
        html += `<div><b>Eventos/Mensajes recientes:</b> <pre>${JSON.stringify(messages, null, 2)}</pre></div>`;
      }
      panel.innerHTML = html;
    } catch (e) {
      panel.innerHTML = '<span style="color:#f44">Error de red.</span>';
    }
  }
  document.getElementById('reloadTdlibStatsBtn').onclick = loadTdlibStats;
  loadTdlibStats();

  // ...resto de la lógica existente...
});
                                                                                                                // Panel de historial de acciones de ban para owner
                                                                                                                if (localStorage.getItem('role') === 'owner') {
                                                                                                                  const banHistoryPanel = document.createElement('div');
                                                                                                                  banHistoryPanel.id = 'banHistoryPanel';
                                                                                                                  banHistoryPanel.style.margin = '32px 0';
                                                                                                                  banHistoryPanel.innerHTML = `<h2 style='color:#6cf'>Historial de acciones de ban</h2><div id='banHistoryList'>Cargando...</div>`;
                                                                                                                  document.body.appendChild(banHistoryPanel);
                                                                                                                  async function loadBanHistory() {
                                                                                                                    const listDiv = document.getElementById('banHistoryList');
                                                                                                                    listDiv.innerHTML = 'Cargando...';
                                                                                                                    try {
                                                                                                                      const resp = await fetch('/bot/group/ban_history', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
                                                                                                                      if (resp.ok) {
                                                                                                                        const js = await resp.json();
                                                                                                                        const list = js.history || [];
                                                                                                                        if (!list.length) { listDiv.innerHTML = '<span style="color:#888">No hay historial.</span>'; return; }
                                                                                                                        const frag = document.createDocumentFragment();
                                                                                                                        list.forEach((h, idx) => {
                                                                                                                          const hDiv = document.createElement('div');
                                                                                                                          hDiv.style.background = '#222';
                                                                                                                          hDiv.style.marginBottom = '12px';
                                                                                                                          hDiv.style.padding = '10px';
                                                                                                                          hDiv.style.borderRadius = '8px';
                                                                                                                          hDiv.innerHTML = `<b>Acción:</b> ${h.action} <span style='color:#6cf'>IDs: ${h.ids.length}</span> <span style='color:#888'>De: ${h.from}</span> <span style='color:#aaa'>${new Date(h.ts*1000).toLocaleString()}</span>`;
                                                                                                                          frag.appendChild(hDiv);
                                                                                                                        });
                                                                                                                        // Botón exportar historial
                                                                                                                        const exportBtn = document.createElement('button');
                                                                                                                        exportBtn.textContent = 'Exportar historial';
                                                                                                                        exportBtn.className = 'ghost';
                                                                                                                        exportBtn.style.marginTop = '12px';
                                                                                                                        exportBtn.onclick = () => {
                                                                                                                          const data = list.map(h => `${h.action} | ${h.ids.join(',')} | ${h.from} | ${new Date(h.ts*1000).toLocaleString()}`).join('\n');
                                                                                                                          const blob = new Blob([data], { type: 'text/plain' });
                                                                                                                          const a = document.createElement('a');
                                                                                                                          a.href = URL.createObjectURL(blob);
                                                                                                                          a.download = 'ban_historial.txt';
                                                                                                                          a.click();
                                                                                                                        };
                                                                                                                        frag.appendChild(exportBtn);
                                                                                                                        listDiv.innerHTML = '';
                                                                                                                        listDiv.appendChild(frag);
                                                                                                                      }
                                                                                                                    } catch (e) {
                                                                                                                      listDiv.innerHTML = '<span style="color:#f44">Error cargando historial.</span>';
                                                                                                                    }
                                                                                                                  }
                                                                                                                  loadBanHistory();
                                                                                                                }

                                                                                                                // Panel de notificaciones de ban para admin de grupo
                                                                                                                if (localStorage.getItem('role') === 'admin') {
                                                                                                                  const banNotifPanel = document.createElement('div');
                                                                                                                  banNotifPanel.id = 'banNotifPanel';
                                                                                                                  banNotifPanel.style.margin = '32px 0';
                                                                                                                  banNotifPanel.innerHTML = `<h2 style='color:#6cf'>Notificaciones de ban</h2><div id='banNotifList'>Cargando...</div>`;
                                                                                                                  document.body.appendChild(banNotifPanel);
                                                                                                                  async function loadBanNotifs() {
                                                                                                                    const listDiv = document.getElementById('banNotifList');
                                                                                                                    listDiv.innerHTML = 'Cargando...';
                                                                                                                    try {
                                                                                                                      const resp = await fetch('/bot/group/ban_notifications', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
                                                                                                                      if (resp.ok) {
                                                                                                                        const js = await resp.json();
                                                                                                                        const list = js.notifications || [];
                                                                                                                        if (!list.length) { listDiv.innerHTML = '<span style="color:#888">No hay notificaciones.</span>'; return; }
                                                                                                                        const frag = document.createDocumentFragment();
                                                                                                                        list.forEach((n, idx) => {
                                                                                                                          const nDiv = document.createElement('div');
                                                                                                                          nDiv.style.background = '#222';
                                                                                                                          nDiv.style.marginBottom = '12px';
                                                                                                                          nDiv.style.padding = '10px';
                                                                                                                          nDiv.style.borderRadius = '8px';
                                                                                                                          nDiv.innerHTML = `<b>Acción:</b> ${n.action} <span style='color:#6cf'>IDs: ${n.ids.length}</span> <span style='color:#aaa'>${new Date(n.ts*1000).toLocaleString()}</span>`;
                                                                                                                          frag.appendChild(nDiv);
                                                                                                                        });
                                                                                                                        // Botón exportar notificaciones
                                                                                                                        const exportBtn = document.createElement('button');
                                                                                                                        exportBtn.textContent = 'Exportar notificaciones';
                                                                                                                        exportBtn.className = 'ghost';
                                                                                                                        exportBtn.style.marginTop = '12px';
                                                                                                                        exportBtn.onclick = () => {
                                                                                                                          const data = list.map(n => `${n.action} | ${n.ids.join(',')} | ${new Date(n.ts*1000).toLocaleString()}`).join('\n');
                                                                                                                          const blob = new Blob([data], { type: 'text/plain' });
                                                                                                                          const a = document.createElement('a');
                                                                                                                          a.href = URL.createObjectURL(blob);
                                                                                                                          a.download = 'ban_notificaciones.txt';
                                                                                                                          a.click();
                                                                                                                        };
                                                                                                                        frag.appendChild(exportBtn);
                                                                                                                        listDiv.innerHTML = '';
                                                                                                                        listDiv.appendChild(frag);
                                                                                                                      }
                                                                                                                    } catch (e) {
                                                                                                                      listDiv.innerHTML = '<span style="color:#f44">Error cargando notificaciones.</span>';
                                                                                                                    }
                                                                                                                  }
                                                                                                                  loadBanNotifs();
                                                                                                                }
                                                                                                              // Panel de sugerencias de ban para owner
                                                                                                              if (localStorage.getItem('role') === 'owner') {
                                                                                                                const banSuggestPanel = document.createElement('div');
                                                                                                                banSuggestPanel.id = 'banSuggestPanel';
                                                                                                                banSuggestPanel.style.margin = '32px 0';
                                                                                                                banSuggestPanel.innerHTML = `<h2 style='color:#6cf'>Sugerencias de ban de admins</h2><div id='banSuggestList'>Cargando...</div>`;
                                                                                                                document.body.appendChild(banSuggestPanel);
                                                                                                                async function loadUserBots() {
                                                                                                                  const listDiv = document.getElementById('userBotsList');
                                                                                                                  const botType = document.getElementById('botTypeSelector')?.value || 'telegram';
                                                                                                                  listDiv.innerHTML = 'Cargando...';
                                                                                                                  let url = '/bot/userbots';
                                                                                                                  let headers = { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') };
                                                                                                                  if (botType === 'tdlib') {
                                                                                                                    url = '/tdlib/userclients';
                                                                                                                    // Pedir api_id y api_hash de Telegram
                                                                                                                    let apiId = localStorage.getItem('tdlibApiId') || '';
                                                                                                                    let apiHash = localStorage.getItem('tdlibApiHash') || '';
                                                                                                                    if (!apiId || !apiHash) {
                                                                                                                      apiId = prompt('Introduce tu Telegram api_id para TDLib:');
                                                                                                                      if (!apiId) {
                                                                                                                        listDiv.innerHTML = '<span style="color:#f44">Debes introducir api_id para ver clientes TDLib.</span>';
                                                                                                                        return;
                                                                                                                      }
                                                                                                                      apiHash = prompt('Introduce tu Telegram api_hash para TDLib:');
                                                                                                                      if (!apiHash) {
                                                                                                                        listDiv.innerHTML = '<span style="color:#f44">Debes introducir api_hash para ver clientes TDLib.</span>';
                                                                                                                        return;
                                                                                                                      }
                                                                                                                      localStorage.setItem('tdlibApiId', apiId);
                                                                                                                      localStorage.setItem('tdlibApiHash', apiHash);
                                                                                                                    }
                                                                                                                    headers['x-tdlib-api-id'] = apiId;
                                                                                                                    headers['x-tdlib-api-hash'] = apiHash;
                                                                                                                  }
                                                                                                                  try {
                                                                                                                    const resp = await fetch(url, { headers });
                                                                                                                    if (resp.ok) {
                                                                                                                      const js = await resp.json();
                                                                                                                      const list = js.bots || js.clients || [];
                                                                                                                      if (!list.length) { listDiv.innerHTML = '<span style="color:#888">No hay bots/clientes de este tipo.</span>'; return; }
                                                                                                                      const frag = document.createDocumentFragment();
                                                                                                                      list.forEach(bot => {
                                                                                                                        const botDiv = document.createElement('div');
                                                                                                                        botDiv.style.background = '#222';
                                                                                                                        botDiv.style.marginBottom = '16px';
                                                                                                                        botDiv.style.padding = '12px';
                                                                                                                        botDiv.style.borderRadius = '8px';
                                                                                                                        botDiv.innerHTML = `<b>Usuario:</b> ${bot.owner || bot.user || '-'} <span style='color:#6cf'>${botType === 'tdlib' ? 'Cliente TDLib' : 'Bot'}: ${bot.name || bot.id}</span>`;
                                                                                                                        const settingsDiv = document.createElement('div');
                                                                                                                        settingsDiv.style.fontSize = '0.97em';
                                                                                                                        settingsDiv.style.color = '#ccc';
                                                                                                                        settingsDiv.innerHTML = `<b>Ajustes:</b> ${JSON.stringify(bot.settings || bot.info || {})}`;
                                                                                                                        botDiv.appendChild(settingsDiv);
                                                                                                                        frag.appendChild(botDiv);
                                                                                                                      });
                                                                                                                      listDiv.innerHTML = '';
                                                                                                                      listDiv.appendChild(frag);
                                                                                                                    } else {
                                                                                                                      listDiv.innerHTML = '<span style="color:#f44">Error cargando bots/clientes.</span>';
                                                                                                                    }
                                                                                                                  } catch (e) {
                                                                                                                    listDiv.innerHTML = '<span style="color:#f44">Error de red.</span>';
                                                                                                                  }
                                                                                                                }
                                                                                                                // Recarga al cambiar el selector
                                                                                                                const botTypeSelector = document.getElementById('botTypeSelector');
                                                                                                                if (botTypeSelector) botTypeSelector.onchange = loadUserBots;
                                                                                                                loadUserBots();
                                                                                                                        btns.appendChild(approveBtn);
                                                                                                                        const rejectBtn = document.createElement('button'); rejectBtn.textContent = 'Rechazar'; rejectBtn.className = 'ghost'; rejectBtn.style.marginLeft = '8px';
                                                                                                                        rejectBtn.onclick = async () => {
                                                                                                                          rejectBtn.disabled = true;
                                                                                                                          await fetch(`/bot/group/ban_suggestions/${idx}/delete`, { method: 'POST', headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
                                                                                                                          await loadBanSuggestions();
                                                                                                                        };
                                                                                                                        btns.appendChild(rejectBtn);
                                                                                                                        sugDiv.appendChild(btns);
                                                                                                                        frag.appendChild(sugDiv);
                                                                                                                      });
                                                                                                                      listDiv.innerHTML = '';
                                                                                                                      listDiv.appendChild(frag);
                                                                                                                    }
                                                                                                                  } catch (e) {
                                                                                                                    listDiv.innerHTML = '<span style="color:#f44">Error cargando sugerencias.</span>';
                                                                                                                  }
                                                                                                                }
                                                                                                                loadBanSuggestions();
                                                                                                              }
                                                                                                            // Panel de grupos y chats del bot
                                                                                                            const botGroupsPanel = document.getElementById('botGroupsPanel');
                                                                                                            const botGroupsList = document.getElementById('botGroupsList');
                                                                                                            async function loadBotGroups() {
                                                                                                                      // Panel para bans globales (owner)
                                                                                                                      if (botGroupsPanel && localStorage.getItem('role') === 'owner') {
                                                                                                                        let globalBanDiv = document.getElementById('globalBanPanel');
                                                                                                                        if (!globalBanDiv) {
                                                                                                                          globalBanDiv = document.createElement('div');
                                                                                                                          globalBanDiv.id = 'globalBanPanel';
                                                                                                                          globalBanDiv.style.margin = '18px 0 24px 0';
                                                                                                                          globalBanDiv.innerHTML = `<b>Ban global (todos los bots):</b> <input type='file' id='globalBanFileInput' accept='.txt'> <select id='globalBanApiType'><option value=''>Local</option><option value='cas.ban'>CAS</option></select> <button id='globalBanImportBtn'>Aplicar</button> <span id='globalBanImportMsg' style='color:#f44;margin-left:10px;'></span>`;
                                                                                                                          botGroupsPanel.insertBefore(globalBanDiv, botGroupsPanel.firstChild);
                                                                                                                          document.getElementById('globalBanImportBtn').onclick = async () => {
                                                                                                                            const fileInput = document.getElementById('globalBanFileInput');
                                                                                                                            const msgSpan = document.getElementById('globalBanImportMsg');
                                                                                                                            if (!fileInput.files.length) { msgSpan.textContent = 'Selecciona un archivo.'; return; }
                                                                                                                            const file = fileInput.files[0];
                                                                                                                            const text = await file.text();
                                                                                                                            const ids = text.split(/\r?\n/).map(x => x.trim()).filter(x => x);
                                                                                                                            const apiType = document.getElementById('globalBanApiType').value;
                                                                                                                            if (!ids.length) { msgSpan.textContent = 'Archivo vacío.'; return; }
                                                                                                                            msgSpan.textContent = 'Aplicando...';
                                                                                                                            try {
                                                                                                                              const resp = await fetch('/bot/group/importban', {
                                                                                                                                method: 'POST',
                                                                                                                                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                                                body: JSON.stringify({ ids, api: apiType, global: true })
                                                                                                                              });
                                                                                                                              if (resp.ok) {
                                                                                                                                msgSpan.textContent = '¡Aplicado!';
                                                                                                                                setTimeout(()=>{ msgSpan.textContent = ''; }, 1800);
                                                                                                                                await loadBotGroups();
                                                                                                                              } else {
                                                                                                                                msgSpan.textContent = 'Error al aplicar.';
                                                                                                                              }
                                                                                                                            } catch (e) {
                                                                                                                              msgSpan.textContent = 'Error de red.';
                                                                                                                            }
                                                                                                                          };
                                                                                                                        }
                                                                                                                      }

                                                                                                                      // Panel para sugerencias de ban por admin de grupo
                                                                                                                      if (botGroupsPanel && localStorage.getItem('role') === 'admin') {
                                                                                                                        let suggestBanDiv = document.getElementById('suggestBanPanel');
                                                                                                                        if (!suggestBanDiv) {
                                                                                                                          suggestBanDiv = document.createElement('div');
                                                                                                                          suggestBanDiv.id = 'suggestBanPanel';
                                                                                                                          suggestBanDiv.style.margin = '18px 0 24px 0';
                                                                                                                          suggestBanDiv.innerHTML = `<b>Sugerir lista de ban al owner:</b> <input type='file' id='suggestBanFileInput' accept='.txt'> <button id='suggestBanBtn'>Sugerir</button> <span id='suggestBanMsg' style='color:#f44;margin-left:10px;'></span>`;
                                                                                                                          botGroupsPanel.insertBefore(suggestBanDiv, botGroupsPanel.firstChild);
                                                                                                                          document.getElementById('suggestBanBtn').onclick = async () => {
                                                                                                                            const fileInput = document.getElementById('suggestBanFileInput');
                                                                                                                            const msgSpan = document.getElementById('suggestBanMsg');
                                                                                                                            if (!fileInput.files.length) { msgSpan.textContent = 'Selecciona un archivo.'; return; }
                                                                                                                            const file = fileInput.files[0];
                                                                                                                            const text = await file.text();
                                                                                                                            const ids = text.split(/\r?\n/).map(x => x.trim()).filter(x => x);
                                                                                                                            if (!ids.length) { msgSpan.textContent = 'Archivo vacío.'; return; }
                                                                                                                            msgSpan.textContent = 'Enviando sugerencia...';
                                                                                                                            try {
                                                                                                                              const resp = await fetch('/bot/group/suggestban', {
                                                                                                                                method: 'POST',
                                                                                                                                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                                                body: JSON.stringify({ ids })
                                                                                                                              });
                                                                                                                              if (resp.ok) {
                                                                                                                                msgSpan.textContent = '¡Sugerido!';
                                                                                                                                setTimeout(()=>{ msgSpan.textContent = ''; }, 1800);
                                                                                                                              } else {
                                                                                                                                msgSpan.textContent = 'Error al sugerir.';
                                                                                                                              }
                                                                                                                            } catch (e) {
                                                                                                                              msgSpan.textContent = 'Error de red.';
                                                                                                                            }
                                                                                                                          };
                                                                                                                        }
                                                                                                                      }
                                                                                                                  // Opción para importar lista de ban
                                                                                                                  if (botGroupsPanel) {
                                                                                                                    let importDiv = document.getElementById('banImportPanel');
                                                                                                                    if (!importDiv) {
                                                                                                                      importDiv = document.createElement('div');
                                                                                                                      importDiv.id = 'banImportPanel';
                                                                                                                      importDiv.style.margin = '18px 0 24px 0';
                                                                                                                      importDiv.innerHTML = `<b>Importar lista de ban:</b> <input type='file' id='banFileInput' accept='.txt'> <button id='banImportBtn'>Importar</button> <span id='banImportMsg' style='color:#f44;margin-left:10px;'></span>`;
                                                                                                                        importDiv.innerHTML = `<b>Importar lista de ban:</b> <input type='file' id='banFileInput' accept='.txt'> <select id='banApiType'><option value=''>Local</option><option value='cas.ban'>CAS</option></select> <button id='banImportBtn'>Importar</button> <span id='banImportMsg' style='color:#f44;margin-left:10px;'></span>`;
                                                                                                                      botGroupsPanel.insertBefore(importDiv, botGroupsPanel.firstChild);
                                                                                                                      document.getElementById('banImportBtn').onclick = async () => {
                                                                                                                        const fileInput = document.getElementById('banFileInput');
                                                                                                                        const msgSpan = document.getElementById('banImportMsg');
                                                                                                                        if (!fileInput.files.length) { msgSpan.textContent = 'Selecciona un archivo.'; return; }
                                                                                                                        const file = fileInput.files[0];
                                                                                                                        const text = await file.text();
                                                                                                                        const ids = text.split(/\r?\n/).map(x => x.trim()).filter(x => x);
                                                                                                                        const apiType = document.getElementById('banApiType').value;
                                                                                                                        if (!ids.length) { msgSpan.textContent = 'Archivo vacío.'; return; }
                                                                                                                        msgSpan.textContent = 'Importando...';
                                                                                                                        // Enviar lista de ban al backend
                                                                                                                        try {
                                                                                                                          const resp = await fetch('/bot/group/importban', {
                                                                                                                            method: 'POST',
                                                                                                                            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                                            body: JSON.stringify({ ids, api: apiType })
                                                                                                                          });
                                                                                                                          if (resp.ok) {
                                                                                                                            msgSpan.textContent = '¡Importado!';
                                                                                                                            setTimeout(()=>{ msgSpan.textContent = ''; }, 1800);
                                                                                                                            await loadBotGroups();
                                                                                                                          } else {
                                                                                                                            msgSpan.textContent = 'Error al importar.';
                                                                                                                          }
                                                                                                                        } catch (e) {
                                                                                                                          msgSpan.textContent = 'Error de red.';
                                                                                                                        }
                                                                                                                      };
                                                                                                                    }
                                                                                                                  }
                                                                                                              if (!botGroupsList) return;
                                                                                                              botGroupsList.innerHTML = 'Cargando...';
                                                                                                              try {
                                                                                                                const resp = await fetch('/bot/groups', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
                                                                                                                if (resp.ok) {
                                                                                                                  const js = await resp.json();
                                                                                                                  const list = js.groups || [];
                                                                                                                  if (!list.length) {
                                                                                                                    botGroupsList.innerHTML = '<div style="color:#888">No hay grupos/chats.</div>';
                                                                                                                    return;
                                                                                                                  }
                                                                                                                  const frag = document.createDocumentFragment();
                                                                                                                  list.forEach(gr => {
                                                                                                                    const row = document.createElement('div');
                                                                                                                    row.style.padding = '10px';
                                                                                                                    row.style.marginBottom = '18px';
                                                                                                                    row.style.borderRadius = '8px';
                                                                                                                    row.style.background = '#222';
                                                                                                                    row.innerHTML = `<b>${gr.title || gr.id}</b> <span style='color:#6cf'>ID: ${gr.id}</span> <span style='color:#888'>${gr.type}</span>`;
                                                                                                                    const leaveBtn = document.createElement('button'); leaveBtn.className = 'ghost'; leaveBtn.textContent = 'Salir';
                                                                                                                    leaveBtn.onclick = async () => {
                                                                                                                      leaveBtn.disabled = true;
                                                                                                                      await fetch('/bot/groups/leave', {
                                                                                                                        method: 'POST',
                                                                                                                        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                                        body: JSON.stringify({ id: gr.id })
                                                                                                                      });
                                                                                                                      await loadBotGroups();
                                                                                                                    };
                                                                                                                    row.appendChild(leaveBtn);


                                                                                                                    // Miembros con opciones extra
                                                                                                                    if (gr.members && gr.members.length) {
                                                                                                                      const membersDiv = document.createElement('div');
                                                                                                                      membersDiv.style.marginTop = '10px';
                                                                                                                      membersDiv.innerHTML = `<b>Miembros (${gr.members.length}):</b>`;
                                                                                                                      gr.members.forEach(m => {
                                                                                                                        const mrow = document.createElement('div');
                                                                                                                        mrow.style.fontSize = '0.98em';
                                                                                                                        mrow.style.color = '#ccc';
                                                                                                                        mrow.style.display = 'flex';
                                                                                                                        mrow.style.alignItems = 'center';
                                                                                                                        mrow.textContent = `${m.name || m.username || m.id}`;
                                                                                                                        // Expulsar
                                                                                                                        const kickBtn = document.createElement('button');
                                                                                                                        kickBtn.textContent = 'Expulsar';
                                                                                                                        kickBtn.className = 'ghost';
                                                                                                                        kickBtn.style.marginLeft = '8px';
                                                                                                                        kickBtn.onclick = async () => {
                                                                                                                          kickBtn.disabled = true;
                                                                                                                          await fetch('/bot/group/kick', {
                                                                                                                            method: 'POST',
                                                                                                                            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                                            body: JSON.stringify({ group_id: gr.id, user_id: m.id })
                                                                                                                          });
                                                                                                                          await loadBotGroups();
                                                                                                                        };
                                                                                                                        mrow.appendChild(kickBtn);
                                                                                                                        // Silenciar
                                                                                                                        const muteBtn = document.createElement('button');
                                                                                                                        muteBtn.textContent = 'Silenciar';
                                                                                                                        muteBtn.className = 'ghost';
                                                                                                                        muteBtn.style.marginLeft = '6px';
                                                                                                                        muteBtn.onclick = async () => {
                                                                                                                          muteBtn.disabled = true;
                                                                                                                          await fetch('/bot/group/mute', {
                                                                                                                            method: 'POST',
                                                                                                                            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                                            body: JSON.stringify({ group_id: gr.id, user_id: m.id })
                                                                                                                          });
                                                                                                                          muteBtn.textContent = 'Silenciado';
                                                                                                                          setTimeout(()=>{ muteBtn.textContent = 'Silenciar'; muteBtn.disabled = false; }, 1800);
                                                                                                                        };
                                                                                                                        mrow.appendChild(muteBtn);
                                                                                                                        membersDiv.appendChild(mrow);
                                                                                                                      });
                                                                                                                      // Exportar miembros
                                                                                                                      const exportBtn = document.createElement('button');
                                                                                                                      exportBtn.textContent = 'Exportar miembros';
                                                                                                                      exportBtn.className = 'ghost';
                                                                                                                      exportBtn.style.marginTop = '8px';
                                                                                                                      exportBtn.onclick = () => {
                                                                                                                        const data = gr.members.map(m => m.name || m.username || m.id).join('\n');
                                                                                                                        const blob = new Blob([data], { type: 'text/plain' });
                                                                                                                        const a = document.createElement('a');
                                                                                                                        a.href = URL.createObjectURL(blob);
                                                                                                                        a.download = `miembros_${gr.id}.txt`;
                                                                                                                        a.click();
                                                                                                                      };
                                                                                                                      membersDiv.appendChild(exportBtn);
                                                                                                                      row.appendChild(membersDiv);
                                                                                                                    }

                                                                                                                    // Mensajes recientes con opciones extra
                                                                                                                    if (gr.messages && gr.messages.length) {
                                                                                                                      const msgsDiv = document.createElement('div');
                                                                                                                      msgsDiv.style.marginTop = '10px';
                                                                                                                      msgsDiv.innerHTML = `<b>Mensajes recientes:</b>`;
                                                                                                                      gr.messages.forEach(msg => {
                                                                                                                        const msgrow = document.createElement('div');
                                                                                                                        msgrow.style.fontSize = '0.97em';
                                                                                                                        msgrow.style.color = '#aaf';
                                                                                                                        msgrow.style.display = 'flex';
                                                                                                                        msgrow.style.alignItems = 'center';
                                                                                                                        msgrow.textContent = `[${new Date(msg.ts*1000).toLocaleString()}] ${msg.from}: ${msg.text}`;
                                                                                                                        // Borrar mensaje
                                                                                                                        const delBtn = document.createElement('button');
                                                                                                                        delBtn.textContent = 'Borrar';
                                                                                                                        delBtn.className = 'ghost';
                                                                                                                        delBtn.style.marginLeft = '8px';
                                                                                                                        delBtn.onclick = async () => {
                                                                                                                          delBtn.disabled = true;
                                                                                                                          await fetch('/bot/group/delmsg', {
                                                                                                                            method: 'POST',
                                                                                                                            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                                            body: JSON.stringify({ group_id: gr.id, msg_id: msg.id })
                                                                                                                          });
                                                                                                                          await loadBotGroups();
                                                                                                                        };
                                                                                                                        msgrow.appendChild(delBtn);
                                                                                                                        msgsDiv.appendChild(msgrow);
                                                                                                                      });
                                                                                                                      // Exportar mensajes
                                                                                                                      const exportBtn = document.createElement('button');
                                                                                                                      exportBtn.textContent = 'Exportar mensajes';
                                                                                                                      exportBtn.className = 'ghost';
                                                                                                                      exportBtn.style.marginTop = '8px';
                                                                                                                      exportBtn.onclick = () => {
                                                                                                                        const data = gr.messages.map(msg => `[${new Date(msg.ts*1000).toLocaleString()}] ${msg.from}: ${msg.text}`).join('\n');
                                                                                                                        const blob = new Blob([data], { type: 'text/plain' });
                                                                                                                        const a = document.createElement('a');
                                                                                                                        a.href = URL.createObjectURL(blob);
                                                                                                                        a.download = `mensajes_${gr.id}.txt`;
                                                                                                                        a.click();
                                                                                                                      };
                                                                                                                      msgsDiv.appendChild(exportBtn);
                                                                                                                      row.appendChild(msgsDiv);
                                                                                                                    }

                                                                                                                    frag.appendChild(row);
                                                                                                                  });
                                                                                                                  botGroupsList.innerHTML = '';
                                                                                                                  botGroupsList.appendChild(frag);
                                                                                                                }
                                                                                                              } catch (e) {
                                                                                                                botGroupsList.innerHTML = '<span style="color:#f44">Error cargando grupos.</span>';
                                                                                                              }
                                                                                                            }
                                                                                                            if (botGroupsPanel) loadBotGroups();

                                                                                                            // Panel de mensajes recibidos por el bot
                                                                                                            const botMessagesPanel = document.getElementById('botMessagesPanel');
                                                                                                            const botMessagesList = document.getElementById('botMessagesList');
                                                                                                            async function loadBotMessages() {
                                                                                                              if (!botMessagesList) return;
                                                                                                              botMessagesList.innerHTML = 'Cargando...';
                                                                                                              try {
                                                                                                                const resp = await fetch('/bot/messages', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
                                                                                                                if (resp.ok) {
                                                                                                                  const js = await resp.json();
                                                                                                                  const list = js.messages || [];
                                                                                                                  if (!list.length) {
                                                                                                                    botMessagesList.innerHTML = '<div style="color:#888">No hay mensajes.</div>';
                                                                                                                    return;
                                                                                                                  }
                                                                                                                  const frag = document.createDocumentFragment();
                                                                                                                  list.forEach(msg => {
                                                                                                                    const row = document.createElement('div');
                                                                                                                    row.style.padding = '10px';
                                                                                                                    row.style.marginBottom = '8px';
                                                                                                                    row.style.borderRadius = '8px';
                                                                                                                    row.style.background = '#222';
                                                                                                                    row.innerHTML = `<b>${msg.text}</b> <span style='color:#6cf'>de ${msg.from}</span> <span style='color:#888'>${new Date(msg.ts*1000).toLocaleString()}</span>`;
                                                                                                                    frag.appendChild(row);
                                                                                                                  });
                                                                                                                  botMessagesList.innerHTML = '';
                                                                                                                  botMessagesList.appendChild(frag);
                                                                                                                }
                                                                                                              } catch (e) {
                                                                                                                botMessagesList.innerHTML = '<span style="color:#f44">Error cargando mensajes.</span>';
                                                                                                              }
                                                                                                            }
                                                                                                            if (botMessagesPanel) loadBotMessages();
                                                                                                          // Panel de traducciones aplicadas
                                                                                                          const appliedTranslationsPanel = document.getElementById('appliedTranslationsPanel');
                                                                                                          const appliedTranslationsList = document.getElementById('appliedTranslationsList');

                                                                                                          async function loadAppliedTranslations() {
                                                                                                            if (!appliedTranslationsList) return;
                                                                                                            appliedTranslationsList.innerHTML = 'Cargando...';
                                                                                                            try {
                                                                                                              const resp = await fetch('/translations/applied', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
                                                                                                              if (resp.ok) {
                                                                                                                const js = await resp.json();
                                                                                                                const list = js.translations || [];
                                                                                                                if (!list.length) {
                                                                                                                  appliedTranslationsList.innerHTML = '<div style="color:#888">No hay traducciones aplicadas.</div>';
                                                                                                                  return;
                                                                                                                }
                                                                                                                const frag = document.createDocumentFragment();
                                                                                                                list.forEach(tr => {
                                                                                                                  const row = document.createElement('div');
                                                                                                                  row.style.padding = '10px';
                                                                                                                  row.style.marginBottom = '8px';
                                                                                                                  row.style.borderRadius = '8px';
                                                                                                                  row.style.background = '#222';
                                                                                                                  row.innerHTML = `<b>${tr.text}</b> <span style='color:#6cf'>por ${tr.by}</span> <span style='color:#888'>${new Date(tr.ts*1000).toLocaleString()}</span>`;
                                                                                                                  const rejectBtn = document.createElement('button'); rejectBtn.className = 'ghost'; rejectBtn.textContent = 'Rechazar';
                                                                                                                  rejectBtn.onclick = async () => {
                                                                                                                    rejectBtn.disabled = true;
                                                                                                                    await fetch('/translations/reject', {
                                                                                                                      method: 'POST',
                                                                                                                      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                                      body: JSON.stringify({ id: tr.id })
                                                                                                                    });
                                                                                                                    await loadAppliedTranslations();
                                                                                                                  };
                                                                                                                  row.appendChild(rejectBtn);
                                                                                                                  frag.appendChild(row);
                                                                                                                });
                                                                                                                appliedTranslationsList.innerHTML = '';
                                                                                                                appliedTranslationsList.appendChild(frag);
                                                                                                              }
                                                                                                            } catch (e) {
                                                                                                              appliedTranslationsList.innerHTML = '<span style="color:#f44">Error cargando traducciones.</span>';
                                                                                                            }
                                                                                                          }
                                                                                                          if (appliedTranslationsPanel) loadAppliedTranslations();
                                                                                                        // --- Minichat y notificación para owner ---
                                                                                                        const ownerMiniChatPanel = document.getElementById('ownerMiniChatPanel');
                                                                                                        const ownerMiniChatMessages = document.getElementById('ownerMiniChatMessages');
                                                                                                        const ownerMiniChatInput = document.getElementById('ownerMiniChatInput');
                                                                                                        const ownerMiniChatSendBtn = document.getElementById('ownerMiniChatSendBtn');
                                                                                                        const ownerMiniChatStatus = document.getElementById('ownerMiniChatStatus');
                                                                                                        const ownerNotifyCreatorTelegramBtn = document.getElementById('ownerNotifyCreatorTelegramBtn');
                                                                                                        const ownerNotifyCreatorEmailBtn = document.getElementById('ownerNotifyCreatorEmailBtn');

                                                                                                        async function loadOwnerMiniChat() {
                                                                                                          if (!ownerMiniChatMessages) return;
                                                                                                          try {
                                                                                                            const resp = await fetch('/mini_chat/messages', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
                                                                                                            if (resp.ok) {
                                                                                                              const js = await resp.json();
                                                                                                              ownerMiniChatMessages.innerHTML = '';
                                                                                                              (js.messages || []).forEach(msg => {
                                                                                                                const div = document.createElement('div');
                                                                                                                div.style.marginBottom = '6px';
                                                                                                                div.innerHTML = `<span style='color:#6cf'>${msg.from}</span>: ${msg.text} <span style='color:#888;font-size:0.92em'>${new Date(msg.ts*1000).toLocaleString()}</span>`;
                                                                                                                ownerMiniChatMessages.appendChild(div);
                                                                                                              });
                                                                                                            }
                                                                                                          } catch (e) {
                                                                                                            ownerMiniChatMessages.innerHTML = '<span style="color:#f44">Error cargando mensajes.</span>';
                                                                                                          }
                                                                                                        }
                                                                                                        async function sendOwnerMiniChat() {
                                                                                                          const txt = ownerMiniChatInput.value.trim();
                                                                                                          if (!txt) return;
                                                                                                          ownerMiniChatSendBtn.disabled = true;
                                                                                                          ownerMiniChatStatus.textContent = 'Enviando...';
                                                                                                          try {
                                                                                                            const resp = await fetch('/mini_chat/send', {
                                                                                                              method: 'POST',
                                                                                                              headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                              body: JSON.stringify({ text: txt })
                                                                                                            });
                                                                                                            if (resp.ok) {
                                                                                                              ownerMiniChatInput.value = '';
                                                                                                              ownerMiniChatStatus.textContent = 'Mensaje enviado.';
                                                                                                              await loadOwnerMiniChat();
                                                                                                            } else {
                                                                                                              ownerMiniChatStatus.textContent = 'Error al enviar.';
                                                                                                            }
                                                                                                          } catch (e) {
                                                                                                            ownerMiniChatStatus.textContent = 'Error de conexión.';
                                                                                                          }
                                                                                                          ownerMiniChatSendBtn.disabled = false;
                                                                                                          setTimeout(() => { ownerMiniChatStatus.textContent = ''; }, 2500);
                                                                                                        }
                                                                                                        if (ownerMiniChatSendBtn) ownerMiniChatSendBtn.onclick = sendOwnerMiniChat;
                                                                                                        if (ownerMiniChatPanel) loadOwnerMiniChat();
                                                                                                        if (ownerNotifyCreatorTelegramBtn) ownerNotifyCreatorTelegramBtn.onclick = async () => {
                                                                                                          const lastMsg = ownerMiniChatInput.value.trim();
                                                                                                          if (!lastMsg) { alert('Escribe un mensaje para notificar.'); return; }
                                                                                                          ownerNotifyCreatorTelegramBtn.disabled = true;
                                                                                                          try {
                                                                                                            await fetch('/mini_chat/notify_telegram', {
                                                                                                              method: 'POST',
                                                                                                              headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                              body: JSON.stringify({ text: lastMsg })
                                                                                                            });
                                                                                                            alert('Notificado por Telegram');
                                                                                                          } catch (e) { alert('Error al notificar.'); }
                                                                                                          ownerNotifyCreatorTelegramBtn.disabled = false;
                                                                                                        };
                                                                                                        if (ownerNotifyCreatorEmailBtn) ownerNotifyCreatorEmailBtn.onclick = async () => {
                                                                                                          const lastMsg = ownerMiniChatInput.value.trim();
                                                                                                          if (!lastMsg) { alert('Escribe un mensaje para notificar.'); return; }
                                                                                                          ownerNotifyCreatorEmailBtn.disabled = true;
                                                                                                          try {
                                                                                                            await fetch('/mini_chat/notify_email', {
                                                                                                              method: 'POST',
                                                                                                              headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('authToken') },
                                                                                                              body: JSON.stringify({ text: lastMsg })
                                                                                                            });
                                                                                                            alert('Notificado por Email');
                                                                                                          } catch (e) { alert('Error al notificar.'); }
                                                                                                          ownerNotifyCreatorEmailBtn.disabled = false;
                                                                                                        };
                                                                                                      // --- Solicitudes de admin de traducciones ---
                                                                                                      const transAdminCreateBtn = document.getElementById('transAdminCreateBtn');
                                                                                                      const transAdminUserInput = document.getElementById('transAdminUserInput');
                                                                                                      const transAdminPassInput = document.getElementById('transAdminPassInput');
                                                                                                      const transAdminCreateMsg = document.getElementById('transAdminCreateMsg');
                                                                                                      const transAdminRequestsPanel = document.getElementById('transAdminRequestsPanel');

                                                                                                      async function submitTransAdminRequest() {
                                                                                                        const user = transAdminUserInput.value.trim();
                                                                                                        const pass = transAdminPassInput.value.trim();
                                                                                                        if (!user || !pass) {
                                                                                                          transAdminCreateMsg.textContent = 'Usuario y contraseña requeridos.';
                                                                                                          return;
                                                                                                        }
                                                                                                        transAdminCreateMsg.textContent = 'Enviando solicitud...';
                                                                                                        try {
                                                                                                          await request('/trans_admin/request', { method: 'POST', body: JSON.stringify({ user, pass }) });
                                                                                                          transAdminCreateMsg.textContent = 'Solicitud enviada. Espera aprobación del owner.';
                                                                                                          transAdminPassInput.value = '';
                                                                                                        } catch (e) {
                                                                                                          transAdminCreateMsg.textContent = 'Error: ' + (e.message || e);
                                                                                                        }
                                                                                                        setTimeout(() => { transAdminCreateMsg.textContent = ''; }, 3500);
                                                                                                      }
                                                                                                      if (transAdminCreateBtn) transAdminCreateBtn.onclick = submitTransAdminRequest;

                                                                                                      // Panel para owner: ver y aprobar/rechazar solicitudes
                                                                                                      async function loadTransAdminRequests() {
                                                                                                        if (!transAdminRequestsPanel) return;
                                                                                                        transAdminRequestsPanel.innerHTML = '<div style="color:var(--muted)">Cargando solicitudes...</div>';
                                                                                                        try {
                                                                                                          const res = await request('/trans_admin/requests', { method: 'GET' });
                                                                                                          const list = res.requests || [];
                                                                                                          if (!list.length) {
                                                                                                            transAdminRequestsPanel.innerHTML = '<div style="color:var(--muted)">Sin solicitudes pendientes.</div>';
                                                                                                            return;
                                                                                                          }
                                                                                                          const frag = document.createDocumentFragment();
                                                                                                          list.forEach(req => {
                                                                                                            const row = document.createElement('div');
                                                                                                            row.style.padding = '10px';
                                                                                                            row.style.marginBottom = '8px';
                                                                                                            row.style.borderRadius = '8px';
                                                                                                            row.style.background = '#181818';
                                                                                                            row.style.color = '#fff';
                                                                                                            row.innerHTML = `<b>${req.user}</b> solicitado por <span style='color:#6cf'>${req.by}</span> <span style='color:#888'>${new Date(req.ts*1000).toLocaleString()}</span> <span style='color:#fc0'>[${req.status}]</span>`;
                                                                                                            if (req.status === 'pending') {
                                                                                                              const approveBtn = document.createElement('button'); approveBtn.className = 'btn'; approveBtn.textContent = 'Aprobar';
                                                                                                              approveBtn.onclick = async () => {
                                                                                                                approveBtn.disabled = true;
                                                                                                                await request('/trans_admin/approve', { method: 'POST', body: JSON.stringify({ id: req.id, approve: true }) });
                                                                                                                await loadTransAdminRequests();
                                                                                                              };
                                                                                                              const rejectBtn = document.createElement('button'); rejectBtn.className = 'ghost'; rejectBtn.textContent = 'Rechazar';
                                                                                                              rejectBtn.onclick = async () => {
                                                                                                                rejectBtn.disabled = true;
                                                                                                                await request('/trans_admin/approve', { method: 'POST', body: JSON.stringify({ id: req.id, approve: false }) });
                                                                                                                await loadTransAdminRequests();
                                                                                                              };
                                                                                                              row.appendChild(approveBtn); row.appendChild(rejectBtn);
                                                                                                            }
                                                                                                            frag.appendChild(row);
                                                                                                          });
                                                                                                          transAdminRequestsPanel.innerHTML = '';
                                                                                                          transAdminRequestsPanel.appendChild(frag);
                                                                                                        } catch (e) {
                                                                                                          transAdminRequestsPanel.innerHTML = '<div style="color:#f44">Error: ' + (e.message || e) + '</div>';
                                                                                                        }
                                                                                                      }

                                                                                                      // Llamar loadTransAdminRequests si el usuario es owner (puedes mejorar con tu lógica de sesión)
                                                                                                      if (window._isOwner && transAdminRequestsPanel) {
                                                                                                        loadTransAdminRequests();
                                                                                                      }
                                                                                                    // --- NUEVOS FORMULARIOS DE CREACIÓN DE USUARIOS Y ADMINISTRADORES ---
                                                                                                    const userCreateBtn = document.getElementById('userCreateBtn');
                                                                                                    const userUserInput = document.getElementById('userUserInput');
                                                                                                    const userPassInput = document.getElementById('userPassInput');
                                                                                                    const userCreateMsg = document.getElementById('userCreateMsg');

                                                                                                    const adminCreateBtn = document.getElementById('adminCreateBtn');
                                                                                                    const adminUserInput = document.getElementById('adminUserInput');
                                                                                                    const adminPassInput = document.getElementById('adminPassInput');
                                                                                                    const adminCreateMsg = document.getElementById('adminCreateMsg');

                                                                                                    const transAdminCreateBtn = document.getElementById('transAdminCreateBtn');
                                                                                                    const transAdminUserInput = document.getElementById('transAdminUserInput');
                                                                                                    const transAdminPassInput = document.getElementById('transAdminPassInput');
                                                                                                    const transAdminCreateMsg = document.getElementById('transAdminCreateMsg');

                                                                                                    async function createUser(type) {
                                                                                                      let user = '', pass = '', msgEl = null, endpoint = '', body = {};
                                                                                                      if (type === 'normal') {
                                                                                                        user = userUserInput.value.trim();
                                                                                                        pass = userPassInput.value.trim();
                                                                                                        msgEl = userCreateMsg;
                                                                                                        endpoint = '/admin/users';
                                                                                                        body = { user, pass, is_admin: false, is_trans_admin: false };
                                                                                                      } else if (type === 'admin') {
                                                                                                        user = adminUserInput.value.trim();
                                                                                                        pass = adminPassInput.value.trim();
                                                                                                        msgEl = adminCreateMsg;
                                                                                                        endpoint = '/admin/users';
                                                                                                        body = { user, pass, is_admin: true, is_trans_admin: false };
                                                                                                      } else if (type === 'trans_admin') {
                                                                                                        user = transAdminUserInput.value.trim();
                                                                                                        pass = transAdminPassInput.value.trim();
                                                                                                        msgEl = transAdminCreateMsg;
                                                                                                        endpoint = '/admin/users';
                                                                                                        body = { user, pass, is_admin: false, is_trans_admin: true };
                                                                                                      }
                                                                                                      if (!user || !pass) {
                                                                                                        if (msgEl) msgEl.textContent = 'Usuario y contraseña requeridos.';
                                                                                                        return;
                                                                                                      }
                                                                                                      msgEl.textContent = 'Creando...';
                                                                                                      try {
                                                                                                        await request(endpoint, { method: 'POST', body: JSON.stringify(body) });
                                                                                                        msgEl.textContent = 'Usuario creado correctamente.';
                                                                                                        if (type === 'normal') userPassInput.value = '';
                                                                                                        if (type === 'admin') adminPassInput.value = '';
                                                                                                        if (type === 'trans_admin') transAdminPassInput.value = '';
                                                                                                      } catch (e) {
                                                                                                        msgEl.textContent = 'Error: ' + (e.message || e);
                                                                                                      }
                                                                                                      setTimeout(() => { msgEl.textContent = ''; }, 3500);
                                                                                                    }

                                                                                                    if (userCreateBtn) userCreateBtn.onclick = () => createUser('normal');
                                                                                                    if (adminCreateBtn) adminCreateBtn.onclick = () => createUser('admin');
                                                                                                    if (transAdminCreateBtn) transAdminCreateBtn.onclick = () => createUser('trans_admin');
                                                                                                  const editBotToken = document.getElementById('editBotToken');
                                                                                    // --- Modal edición bot usuario ---
                                                                                    const editUserBotModal = document.getElementById('editUserBotModal');
                                                                                    const editBotName = document.getElementById('editBotName');
                                                                                    const editBotStatus = document.getElementById('editBotStatus');
                                                                                    const editBotAvatar = document.getElementById('editBotAvatar');
                                                                                    const editBotInfo = document.getElementById('editBotInfo');
                                                                                    const saveEditUserBotBtn = document.getElementById('saveEditUserBotBtn');
                                                                                    const cancelEditUserBotBtn = document.getElementById('cancelEditUserBotBtn');
                                                                                    let editingBotIdx = null;

                                                                                    function showEditUserBotModal(idx) {
                                                                                      if (!editUserBotModal) return;
                                                                                      editingBotIdx = idx;
                                                                                      const bot = userBots[idx];
                                                                                      editBotName.value = bot.name || '';
                                                                                      editBotStatus.value = bot.status || '';
                                                                                      editBotAvatar.value = bot.avatar || '';
                                                                                      editBotToken.value = bot.token || '';
                                                                                      editBotInfo.value = bot.info || '';
                                                                                      editUserBotModal.style.display = 'flex';
                                                                                    }
                                                                                    function hideEditUserBotModal() {
                                                                                      editUserBotModal.style.display = 'none';
                                                                                      editingBotIdx = null;
                                                                                    }
                                                                                    if (cancelEditUserBotBtn) cancelEditUserBotBtn.onclick = hideEditUserBotModal;
                                                                                    if (saveEditUserBotBtn) saveEditUserBotBtn.onclick = async ()=>{
                                                                                      if (editingBotIdx === null) return;
                                                                                      userBots[editingBotIdx].name = editBotName.value.trim();
                                                                                      userBots[editingBotIdx].status = editBotStatus.value.trim();
                                                                                      userBots[editingBotIdx].avatar = editBotAvatar.value.trim();
                                                                                      userBots[editingBotIdx].token = editBotToken.value.trim();
                                                                                      userBots[editingBotIdx].info = editBotInfo.value.trim();
                                                                                      await saveUserBots();
                                                                                      renderUserBots();
                                                                                      hideEditUserBotModal();
                                                                                    };
                                                                      const apiBaseInput = document.getElementById('apiBase');
                                                                      const telegramTokenInput = document.getElementById('telegramTokenInput');
                                                                      const addUserBotByTokenBtn = document.getElementById('addUserBotByTokenBtn');
                                                                      // Auto-load user bots on page load
                                                                      loadUserBots();
                                                                      if (addUserBotByTokenBtn) addUserBotByTokenBtn.onclick = async ()=>{
                                                                        const token = telegramTokenInput && telegramTokenInput.value ? telegramTokenInput.value.trim() : '';
                                                                        if (!token) { alert('Introduce el token de Telegram'); return; }
                                                                        try {
                                                                          const base = getApiBase();
                                                                          const res = await fetch(base + '/api/get_telegram_bot_info', {
                                                                            method: 'POST',
                                                                            headers: { 'Content-Type': 'application/json' },
                                                                            body: JSON.stringify({ token })
                                                                          });
                                                                          const js = await res.json();
                                                                          if (js.blocked) {
                                                                            let msg = 'Este bot ha sido bloqueado por la API de Telegram y no puede ser agregado.';
                                                                            if (js.error) msg += '\n\nMotivo: ' + js.error;
                                                                            msg += '\n\n¿Cómo arreglarlo?\n';
                                                                            msg += '- Verifica que el bot no haya sido eliminado o restringido por Telegram.\n';
                                                                            msg += '- Asegúrate de que el token es correcto y el bot está activo.\n';
                                                                            msg += '- Si el bot fue bloqueado por abuso, revisa las políticas de Telegram y contacta soporte si es necesario.\n';
                                                                            msg += '- Puedes crear un nuevo bot desde @BotFather y usar el nuevo token.\n';
                                                                            alert(msg);
                                                                            return;
                                                                          }
                                                                          if (!js.ok) throw new Error(js.error || 'No se pudo obtener datos del bot');
                                                                          userBots.push({
                                                                            name: js.name || js.username || js.id,
                                                                            status: js.status || 'Activo',
                                                                            statusColor: 'green',
                                                                            avatar: js.avatar || '/logo.svg',
                                                                            info: `Bot Telegram @${js.username || ''} (ID: ${js.id})`,
                                                                            token: token
                                                                          });
                                                                          await saveUserBots();
                                                                          renderUserBots();
                                                                          telegramTokenInput.value = '';
                                                                        } catch (e) {
                                                                          alert('Error: ' + e.message);
                                                                        }
                                                                      };
                                                        // --- Panel de bots de usuario ---
                                                        const userBotsPanel = document.getElementById('userBotsPanel');
                                                        const addUserBotBtn = document.getElementById('addUserBotBtn');

                                                        // Array editable en frontend, sincronizado con backend
                                                        let userBots = [];

                                                        async function loadUserBots() {
                                                          try {
                                                            const base = getApiBase();
                                                            const res = await fetch(base + '/api/get_user_bots');
                                                            if (!res.ok) throw new Error('No data');
                                                            const js = await res.json();
                                                            userBots = js.bots || [];
                                                          } catch (e) {
                                                            userBots = [
                                                              { name: 'MiBot1', status: 'Activo', statusColor: 'green', avatar: '/logo.svg', info: 'Bot de usuario para tareas personales.' },
                                                              { name: 'MiBot2', status: 'En espera', statusColor: 'orange', avatar: '/logo.svg', info: 'Bot secundario de usuario.' }
                                                            ];
                                                          }
                                                          renderUserBots();
                                                        }

                                                        async function saveUserBots() {
                                                          try {
                                                            const base = getApiBase();
                                                            await fetch(base + '/api/set_user_bots', {
                                                              method: 'POST',
                                                              headers: { 'Content-Type': 'application/json' },
                                                              body: JSON.stringify({ bots: userBots })
                                                            });
                                                          } catch (e) {}
                                                        }

                                                        function renderUserBots() {
                                                          if (!userBotsPanel) return;
                                                          userBotsPanel.innerHTML = '';
                                                          userBots.forEach((bot, idx) => {
                                                            const botDiv = document.createElement('div');
                                                            botDiv.style.display = 'flex';
                                                            botDiv.style.flexDirection = 'column';
                                                            botDiv.style.alignItems = 'center';
                                                            botDiv.style.gap = '8px';
                                                            botDiv.style.marginBottom = '8px';
                                                            botDiv.innerHTML = `
                                                              <img src="${bot.avatar}" alt="Bot avatar" class="user-bot-avatar" data-bot-idx="${idx}" style="width:54px;height:54px;border-radius:50%;border:2px solid #e5e7eb;background:#fff;object-fit:cover;box-shadow:0 2px 8px #0002;cursor:pointer" />
                                                              <span style="font-weight:700">${bot.name}</span>
                                                              <span style="color:${bot.statusColor};font-size:0.95rem">${bot.status}</span>
                                                              <div style="display:flex;gap:6px;margin-top:4px">
                                                                <button class="btn ghost" style="font-size:0.95rem" data-del-idx="${idx}">Eliminar</button>
                                                                <button class="btn" style="font-size:0.95rem" data-edit-idx="${idx}">Editar</button>
                                                              </div>
                                                            `;
                                                            userBotsPanel.appendChild(botDiv);
                                                          });
                                                          // Wire click resumen
                                                          userBotsPanel.querySelectorAll('.user-bot-avatar').forEach(img => {
                                                            img.onclick = ()=>{
                                                              const idx = img.getAttribute('data-bot-idx');
                                                              showUserBotSummary(idx);
                                                            };
                                                          });
                                                          // Wire eliminar
                                                          userBotsPanel.querySelectorAll('button[data-del-idx]').forEach(btn => {
                                                            btn.onclick = async ()=>{
                                                              const idx = parseInt(btn.getAttribute('data-del-idx'));
                                                              if (!isNaN(idx)) {
                                                                if (confirm('¿Eliminar este bot de usuario?')) {
                                                                  userBots.splice(idx, 1);
                                                                  await saveUserBots();
                                                                  renderUserBots();
                                                                }
                                                              }
                                                            };
                                                          });
                                                          // Wire editar
                                                          userBotsPanel.querySelectorAll('button[data-edit-idx]').forEach(btn => {
                                                            btn.onclick = ()=>{
                                                              const idx = parseInt(btn.getAttribute('data-edit-idx'));
                                                              if (!isNaN(idx)) {
                                                                showEditUserBotModal(idx);
                                                              }
                                                            };
                                                          });
                                                        }

                                                        function showUserBotSummary(idx) {
                                                          if (!botSummaryModal) return;
                                                          const bot = userBots[idx];
                                                          botSummaryAvatar.src = bot.avatar;
                                                          botSummaryName.textContent = bot.name;
                                                          botSummaryStatus.textContent = bot.status;
                                                          botSummaryStatus.style.color = bot.statusColor;
                                                          botSummaryInfo.textContent = bot.info;
                                                          botSummaryModal.style.display = 'flex';
                                                        }

                                                        if (addUserBotBtn) addUserBotBtn.onclick = async ()=>{
                                                          // Simple prompt para demo
                                                          const name = prompt('Nombre del nuevo bot:');
                                                          if (!name) return;
                                                          userBots.push({ name, status: 'Activo', statusColor: 'green', avatar: '/logo.svg', info: 'Nuevo bot de usuario.' });
                                                          await saveUserBots();
                                                          renderUserBots();
                                                        };

                                                        loadUserBots();
                                          // --- Modal resumen bot ---
                                          const botSummaryModal = document.getElementById('botSummaryModal');
                                          const botSummaryAvatar = document.getElementById('botSummaryAvatar');
                                          const botSummaryName = document.getElementById('botSummaryName');
                                          const botSummaryStatus = document.getElementById('botSummaryStatus');
                                          const botSummaryInfo = document.getElementById('botSummaryInfo');
                                          const closeBotSummaryBtn = document.getElementById('closeBotSummaryBtn');

                                          function showBotSummary(bot) {
                                            if (!botSummaryModal) return;
                                            // Ejemplo: datos por nombre
                                            let info = {
                                              'DBTeamBot': {
                                                avatar: '/logo.svg',
                                                name: 'DBTeamBot',
                                                status: 'Activo',
                                                statusColor: 'green',
                                                info: 'Bot principal para gestión y notificaciones.'
                                              },
                                              'MediaBot': {
                                                avatar: '/logo.svg',
                                                name: 'MediaBot',
                                                status: 'En espera',
                                                statusColor: 'orange',
                                                info: 'Bot secundario para gestión de medios.'
                                              }
                                            };
                                            let d = info[bot] || info['DBTeamBot'];
                                            botSummaryAvatar.src = d.avatar;
                                            botSummaryName.textContent = d.name;
                                            botSummaryStatus.textContent = d.status;
                                            botSummaryStatus.style.color = d.statusColor;
                                            botSummaryInfo.textContent = d.info;
                                            botSummaryModal.style.display = 'flex';
                                          }
                                          // Cerrar modal
                                          if (closeBotSummaryBtn) closeBotSummaryBtn.onclick = ()=>{ botSummaryModal.style.display = 'none'; };
                                          // Click en avatar bot
                                          document.querySelectorAll('.bot-avatar').forEach(img => {
                                            img.onclick = ()=>{
                                              const bot = img.getAttribute('data-bot');
                                              showBotSummary(bot);
                                            };
                                          });
                            // --- Grupos y usuarios activos en vivo ---
                            const liveGroupsUsers = document.getElementById('liveGroupsUsers');

                            async function loadLiveGroupsUsers() {
                              if (!liveGroupsUsers) return;
                              liveGroupsUsers.innerHTML = '<div style="color:var(--muted)">Cargando información en vivo...</div>';
                              try {
                                const base = getApiBase();
                                // Ejemplo: endpoint /api/live_groups_users (debería implementarse en backend)
                                const res = await fetch(base + '/api/live_groups_users');
                                if (!res.ok) throw new Error('No data');
                                const js = await res.json();
                                const groups = js.groups || [];
                                const users = js.users || [];
                                let html = '';
                                html += `<div style="font-weight:700;margin-bottom:6px">Grupos activos (${groups.length}):</div>`;
                                if (groups.length) {
                                  html += '<ul style="margin-bottom:10px">';
                                  groups.forEach(g => {
                                    html += `<li><strong>${g.name || g.id}</strong> <span style="color:var(--muted)">(ID: ${g.id})</span> <span style="color:green">${g.status||'activo'}</span></li>`;
                                  });
                                  html += '</ul>';
                                } else {
                                  html += '<div style="color:var(--muted)">No hay grupos activos.</div>';
                                }
                                html += `<div style="font-weight:700;margin-bottom:6px">Usuarios activos (${users.length}):</div>`;
                                if (users.length) {
                                  html += '<ul>';
                                  users.forEach(u => {
                                    html += `<li><strong>${u.name || u.username || u.id}</strong> <span style="color:var(--muted)">(ID: ${u.id})</span> <span style="color:blue">${u.status||'online'}</span></li>`;
                                  });
                                  html += '</ul>';
                                } else {
                                  html += '<div style="color:var(--muted)">No hay usuarios activos.</div>';
                                }
                                liveGroupsUsers.innerHTML = html;
                              } catch (e) {
                                liveGroupsUsers.innerHTML = '<div style="color:var(--muted)">Error cargando datos en vivo.</div>';
                              }
                            }
                            // Actualizar cada 10s
                            setInterval(loadLiveGroupsUsers, 10000);
                            loadLiveGroupsUsers();
              // Display channels/groups in main section
              const notifChannelDisplay = document.getElementById('notifChannelDisplay');
              const mainChannelDisplay = document.getElementById('mainChannelDisplay');
              const affiliatesDisplay = document.getElementById('affiliatesDisplay');

              async function loadChannelsSection() {
                // Notif channel
                try {
                  const base = getApiBase();
                  const res = await fetch(base + '/ownerlock/tgchannel', { method: 'GET' });
                  if (res.ok) {
                    const js = await res.json();
                    if (notifChannelDisplay) notifChannelDisplay.textContent = js.channel || '(no configurado)';
                  }
                } catch (e) { if (notifChannelDisplay) notifChannelDisplay.textContent = '(error)'; }
                // Main channel (backend)
                try {
                  const base = getApiBase();
                  const res = await fetch(base + '/api/get_main_channel', { method: 'GET' });
                  if (res.ok) {
                    const js = await res.json();
                    if (mainChannelDisplay) mainChannelDisplay.textContent = js.channel || '(no configurado)';
                    if (mainChannelInput) mainChannelInput.value = js.channel || '';
                  }
                } catch (e) { if (mainChannelDisplay) mainChannelDisplay.textContent = '(error)'; if (mainChannelInput) mainChannelInput.value = ''; }
                // Affiliates (backend)
                try {
                  const base = getApiBase();
                  const res = await fetch(base + '/api/get_affiliate_channels', { method: 'GET' });
                  if (res.ok) {
                    const js = await res.json();
                    if (affiliatesDisplay) affiliatesDisplay.textContent = js.channels || '(no configurados)';
                    if (affiliatesInput) affiliatesInput.value = js.channels || '';
                  }
                } catch (e) { if (affiliatesDisplay) affiliatesDisplay.textContent = '(error)'; if (affiliatesInput) affiliatesInput.value = ''; }
              }
              loadChannelsSection();
                          // Guardar canales principales y afiliados en backend
                          const saveChannelsBtn = document.getElementById('saveChannelsBtn');
                          const mainChannelInput = document.getElementById('mainChannelInput');
                          const affiliatesInput = document.getElementById('affiliatesInput');

                          async function saveChannelsSection() {
                            const main = mainChannelInput && mainChannelInput.value ? mainChannelInput.value.trim() : '';
                            const aff = affiliatesInput && affiliatesInput.value ? affiliatesInput.value.trim() : '';
                            const base = getApiBase();
                            try {
                              await fetch(base + '/api/set_main_channel', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ channel: main })
                              });
                              await fetch(base + '/api/set_affiliate_channels', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ channels: aff })
                              });
                              loadChannelsSection();
                              pushNotification('Canales guardados correctamente.', 'success');
                            } catch (e) {
                              pushNotification('Error guardando canales: ' + e.message, 'error');
                            }
                          }
                          if (saveChannelsBtn) saveChannelsBtn.onclick = saveChannelsSection;
            // Load saved Telegram channel on sidebar open
            async function loadTgChannel() {
              if (!tgChannelInput) return;
              try {
                const base = getApiBase();
                const res = await fetch(base + '/ownerlock/tgchannel', { method: 'GET' });
                if (!res.ok) return;
                const js = await res.json();
                if (js.channel) tgChannelInput.value = js.channel;
                tgChannelStatus.textContent = js.channel ? 'Canal guardado: ' + js.channel : '';
              } catch (e) {}
            }
            if (openSidebarBtn) openSidebarBtn.onclick = ()=>{ showSidebar(true); loadTgChannel(); };
            loadTgChannel();
          // Telegram channel save logic
          const tgChannelInput = document.getElementById('tgChannelInput');
          const saveTgChannelBtn = document.getElementById('saveTgChannelBtn');
          const tgChannelStatus = document.getElementById('tgChannelStatus');

          async function saveTgChannel() {
            if (!tgChannelInput) return;
            const val = tgChannelInput.value.trim();
            if (!val) { tgChannelStatus.textContent = 'Introduce el canal.'; return; }
            // Pedir user_id (Telegram) para confirmar que es owner/admin
            let user_id = localStorage.getItem('telegram_user_id') || '';
            if (!user_id) {
              user_id = prompt('Introduce tu user_id de Telegram para verificar que eres owner/admin del canal:');
              if (!user_id) { tgChannelStatus.textContent = 'Se requiere user_id.'; return; }
              localStorage.setItem('telegram_user_id', user_id);
            }
            try {
              const base = getApiBase();
              const res = await fetch(base + '/ownerlock/tgchannel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channel: val, user_id })
              });
              const js = await res.json();
              if (!res.ok || !js.ok) throw new Error(js.error || 'No se pudo guardar');
              tgChannelStatus.textContent = 'Canal guardado y verificado correctamente.';
            } catch (e) {
              tgChannelStatus.textContent = 'Error: ' + e.message;
            }
          }
          if (saveTgChannelBtn) saveTgChannelBtn.onclick = saveTgChannel;
        // Backend notifications fetch
        async function fetchBackendNotifications() {
          if (!notificationList) return;
          try {
            const base = getApiBase();
            const res = await fetch(base + '/notifications');
            if (!res.ok) throw new Error('No notifications');
            const js = await res.json();
            const notifs = js.notifications || [];
            notificationList.innerHTML = '';
            notifs.reverse().forEach(n => {
              const row = document.createElement('div');
              row.style.padding = '10px';
              row.style.marginBottom = '8px';
              row.style.borderRadius = '8px';
              row.style.background = n.type==='error' ? '#ffeded' : (n.type==='success' ? '#e6ffe6' : 'var(--panel,#222)');
              row.style.color = n.type==='error' ? '#c00' : (n.type==='success' ? '#080' : 'var(--muted)');
              row.innerHTML = `<span style="font-size:0.95rem;color:#888">${n.ts}</span><br>${n.msg}`;
              notificationList.appendChild(row);
            });
          } catch (e) {
            // fallback: show nothing
          }
        }
        setInterval(fetchBackendNotifications, 10000);
        fetchBackendNotifications();
      // Sidebar notification logic
      const notificationSidebar = document.getElementById('notificationSidebar');
      const openSidebarBtn = document.getElementById('openSidebarBtn');
      const closeSidebarBtn = document.getElementById('closeSidebarBtn');
      const notificationList = document.getElementById('notificationList');

      function showSidebar(open=true) {
        if (!notificationSidebar) return;
        notificationSidebar.style.right = open ? '0' : '-340px';
      }
      if (openSidebarBtn) openSidebarBtn.onclick = ()=>showSidebar(true);
      if (closeSidebarBtn) closeSidebarBtn.onclick = ()=>showSidebar(false);

      function pushNotification(msg, type='info') {
        if (!notificationList) return;
        const row = document.createElement('div');
        row.style.padding = '10px';
        row.style.marginBottom = '8px';
        row.style.borderRadius = '8px';
        row.style.background = type==='error' ? '#ffeded' : (type==='success' ? '#e6ffe6' : 'var(--panel,#222)');
        row.style.color = type==='error' ? '#c00' : (type==='success' ? '#080' : 'var(--muted)');
        row.textContent = msg;
        notificationList.prepend(row);
        showSidebar(true);
      }
    const refreshGroupLocksBtn = document.getElementById('refreshGroupLocks');
    const groupLocksList = document.getElementById('groupLocksList');

    async function fetchGroupLocks() {
      if (!groupLocksList) return;
      groupLocksList.textContent = 'Cargando...';
      try {
        const base = getApiBase();
        const res = await fetch(base + '/ownerlock/groups');
        if (!res.ok) throw new Error('No data');
        const js = await res.json();
        const groups = js.groups || [];
        if (!groups.length) {
          groupLocksList.textContent = 'No hay grupos bloqueados.';
          return;
        }
        groupLocksList.innerHTML = '';
        groups.forEach(gid => {
          const row = document.createElement('div');
          row.style.display = 'flex';
          row.style.alignItems = 'center';
          row.style.justifyContent = 'space-between';
          row.style.marginBottom = '8px';
          row.innerHTML = `<span style="font-weight:700">ID: ${gid}</span>`;
          const btns = document.createElement('div');
          const unlockBtn = document.createElement('button'); unlockBtn.className = 'btn ghost'; unlockBtn.textContent = 'Desbloquear';
          unlockBtn.onclick = async () => {
            await toggleGroupLock(gid, false);
          };
          const leaveBtn = document.createElement('button'); leaveBtn.className = 'btn'; leaveBtn.textContent = 'Salir del grupo'; leaveBtn.style.marginLeft = '8px';
          leaveBtn.onclick = async () => {
            await leaveGroup(gid);
          };
          btns.appendChild(unlockBtn); btns.appendChild(leaveBtn);
          row.appendChild(btns);
          groupLocksList.appendChild(row);
        });
      } catch (e) {
        groupLocksList.textContent = 'Error: ' + e.message;
      }
    }

    async function toggleGroupLock(gid, lock) {
      try {
        const base = getApiBase();
        const res = await fetch(base + '/ownerlock/groups/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ group_id: gid, lock: lock })
        });
        if (!res.ok) throw new Error('No toggle');
        await fetchGroupLocks();
        pushNotification(lock ? `Grupo ${gid} bloqueado (solo owner puede usar comandos)` : `Grupo ${gid} desbloqueado (todos pueden usar comandos)`, lock ? 'info' : 'success');
      } catch (e) {
        pushNotification('Error cambiando bloqueo de grupo: ' + e.message, 'error');
        await fetchGroupLocks();
      }
    }

    async function leaveGroup(gid) {
      try {
        const base = getApiBase();
        const res = await fetch(base + '/ownerlock/groups/leave', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ group_id: gid })
        });
        if (!res.ok) throw new Error('No leave');
        await fetchGroupLocks();
        pushNotification(`Bot saliendo del grupo ${gid}...`, 'info');
      } catch (e) {
        pushNotification('Error al salir del grupo: ' + e.message, 'error');
        await fetchGroupLocks();
      }
    }

    if (refreshGroupLocksBtn) {
      refreshGroupLocksBtn.addEventListener('click', fetchGroupLocks);
      setTimeout(fetchGroupLocks, 500);
    }
  const ownerLockToggle = document.getElementById('ownerLockToggle')
  const ownerLockStatus = document.getElementById('ownerLockStatus')
    async function fetchOwnerLockStatus() {
      try {
        const base = getApiBase();
        const res = await fetch(base + '/ownerlock/status');
        if (!res.ok) throw new Error('No status');
        const js = await res.json();
        ownerLockToggle.checked = js.locked;
        ownerLockStatus.textContent = js.locked ? 'Estado: activado (solo owner)' : 'Estado: desactivado (todos)';
      } catch (e) {
        ownerLockStatus.textContent = 'Estado: desconocido';
        ownerLockToggle.checked = false;
      }
    }

    async function setOwnerLock(state) {
      try {
        const base = getApiBase();
        const res = await fetch(base + '/ownerlock/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ locked: state })
        });
        if (!res.ok) throw new Error('No toggle');
        await fetchOwnerLockStatus();
      } catch (e) {
        alert('Error cambiando modo owner-only: ' + e.message);
        await fetchOwnerLockStatus();
      }
    }

    if (ownerLockToggle) {
      ownerLockToggle.addEventListener('change', () => {
        setOwnerLock(ownerLockToggle.checked);
      });
      setTimeout(fetchOwnerLockStatus, 500);
    }
  const apiTokenInput = document.getElementById('apiToken')
  const connectionStatus = document.getElementById('connectionStatus')
  const statusSummary = document.getElementById('statusSummary')
  const botStatsSummary = document.getElementById('botStatsSummary')
  const sessionSummary = document.getElementById('sessionSummary')
  const usersTable = document.getElementById('usersTable')
  const newUserInput = document.getElementById('newUser')
  const newPassInput = document.getElementById('newPass')
  const newIsAdmin = document.getElementById('newIsAdmin')
  const genPassEmailBtn = document.getElementById('genPassEmail')
  const botsList = document.getElementById('botsList')
  const discoverResults = document.getElementById('discoverResults')
  const geoBotsDiv = document.getElementById('geoBots')
  const geoUsersDiv = document.getElementById('geoUsers')
  const mapBotsEl = document.getElementById('mapBots')
  const mapUsersEl = document.getElementById('mapUsers')
  let botMapRef = null
  let userMapRef = null
  const refreshAllBtn = document.getElementById('refreshAll')
  const refreshOverviewBtn = document.getElementById('refreshOverview')
  const refreshBotsBtn = document.getElementById('refreshBots')
  const discoverLanBtn = document.getElementById('discoverLan')
  const refreshGeoBtn = document.getElementById('refreshGeo')
  const refreshTorrentsBtn = document.getElementById('refreshTorrents')
  const torrentFileInput = document.getElementById('torrentFile')
  const assignUserInput = document.getElementById('assignUser')
  const viewUserPanelBtn = document.getElementById('viewUserPanel')
  const uploadTorrentBtn = document.getElementById('uploadTorrentBtn')
  const torrentSearchInput = document.getElementById('torrentSearch')
  const torrentSearchBtn = document.getElementById('torrentSearchBtn')
  const torrentClearBtn = document.getElementById('torrentClearBtn')
  const myTorrentsBtn = document.getElementById('myTorrentsBtn')
  let lastTorrents = []
  const torrentTargetSelect = document.getElementById('torrentTargetSelect')
  async function loadTorrentTargets(){
    if(!torrentTargetSelect) return
    try{
      const res = await request('/devices', { method: 'GET' })
      const list = Array.isArray(res) ? res : (res && res.devices) ? res.devices : []
      // preserve local option
      torrentTargetSelect.innerHTML = ''
      const optLocal = document.createElement('option'); optLocal.value='local'; optLocal.textContent='Local (este servidor)'; torrentTargetSelect.appendChild(optLocal)
      list.forEach(d=>{
        const o = document.createElement('option')
        o.value = d.id || d.name || ''
        o.textContent = (d.name ? d.name + ' (' + (d.id||'') + ')' : (d.id||''))
        torrentTargetSelect.appendChild(o)
      })
    }catch(e){ /* ignore silently */ }
  }
  const createUserBtn = document.getElementById('createUser')
  const saveConnectionBtn = document.getElementById('saveConnection')
  const apiBaseList = document.getElementById('apiBaseList')
  const refreshModelsBtn = document.getElementById('refreshModels')
  const modelNameInput = document.getElementById('modelNameInput')
  const installModelBtn = document.getElementById('installModelBtn')
  const installedModelsList = document.getElementById('installedModelsList')
  const modelInstallStatus = document.getElementById('modelInstallStatus')
  const modelCatalogDiv = document.getElementById('modelCatalog')
  const startMonitorBtn = document.getElementById('startMonitorBtn')
  const stopMonitorBtn = document.getElementById('stopMonitorBtn')
  const restartMonitorBtn = document.getElementById('restartMonitorBtn')
  const monitorStatusText = document.getElementById('monitorStatusText')
  const monitorLog = document.getElementById('monitorLog')

  const API_BASE_KEY = 'bot_api_base'

  function setConnection(text, ok){
    if(!connectionStatus) return
    connectionStatus.textContent = text
    connectionStatus.style.color = ok ? 'var(--success, #22c55e)' : 'var(--muted)'
  }

  function loadApiBaseHistory(){
    if(!apiBaseList) return
    apiBaseList.innerHTML = ''
    const defaults = ['http://127.0.0.1:8000','http://localhost:8000','http://0.0.0.0:8000','https://cas.chat']
    const hist = []
    defaults.forEach(v=>{ const o = document.createElement('option'); o.value=v; apiBaseList.appendChild(o) })
    try{
      const saved = JSON.parse(localStorage.getItem(API_BASE_KEY+'_history') || '[]')
      saved.forEach(v=>{ const o = document.createElement('option'); o.value=v; apiBaseList.appendChild(o) })
    }catch(e){}
  }

  function saveApiBaseHistory(val){
    if(!val) return
    let hist = []
    try{ hist = JSON.parse(localStorage.getItem(API_BASE_KEY+'_history') || '[]') }catch(e){ hist = [] }
    hist = [val, ...hist.filter(x=>x && x!==val)].slice(0,10)
    try{ localStorage.setItem(API_BASE_KEY+'_history', JSON.stringify(hist)) }catch(e){}
    loadApiBaseHistory()
  }

  function renderDiscover(list){
    if(!discoverResults) return
    if(!list || !list.length){
      discoverResults.textContent = 'Nada encontrado en el rango';
      return;
    }
    const frag = document.createDocumentFragment();
    list.forEach(item=>{
      const row = document.createElement('div');
      row.className = 'mini-card';
      const title = document.createElement('div');
      title.className = 'mini-title';
      title.textContent = `${item.host}:${item.port}`;
      const body = document.createElement('div');
      body.className = 'mini-body';
      body.textContent = 'Respuesta /status: '+ (item.status || 'desconocido');
      const actions = document.createElement('div');
      actions.style.marginTop = '8px';
      const imp = document.createElement('button'); imp.className='btn'; imp.textContent='Importar';
      imp.addEventListener('click',()=>{
        const token = prompt('Introduce el token del bot para '+item.host);
        if(!token) return;
        const name = prompt('Nombre opcional', item.host) || item.host;
        const id = `${item.host}:${item.port}`;
        request('/devices/add', { method:'POST', body: JSON.stringify({ id, name, token }) })
          .then(()=>{ alert('Dispositivo importado'); loadBots(); })
          .catch(e=> alert('Error al importar: '+e.message));
      });
      actions.appendChild(imp);
      row.appendChild(title); row.appendChild(body); row.appendChild(actions);
      frag.appendChild(row);
    })
    discoverResults.innerHTML = '';
    discoverResults.appendChild(frag);
  }

  function getApiBase(){
    const v = apiBaseInput && apiBaseInput.value ? apiBaseInput.value.trim() : ''
    if(v) return v.replace(/\/+$/, '')
    // If served from the dev proxy on :8000, prefer direct streamer backend
    try{
      if(window && window.location && (window.location.port === '8000' || (window.location.host || '').indexOf(':8000') !== -1)){
        return 'http://127.0.0.1:8082'
      }
    }catch(e){}
    // default to relative paths so a local dev proxy can handle API routing
    return ''
  }

  function authHeaders(withJson=true){
    const h = withJson ? {'Content-Type':'application/json'} : {}
    let tok = ''
    try{ tok = (apiTokenInput && apiTokenInput.value ? apiTokenInput.value.trim() : '') || (localStorage.getItem('api_token') || '') }catch(e){ tok='' }
    if(tok) h['Authorization'] = 'Bearer ' + tok
    return h
  }

  function randomPassword(len=16){
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*?';
    let out = '';
    const arr = new Uint32Array(len);
    crypto.getRandomValues(arr);
    for(let i=0;i<len;i++){ out += chars[arr[i] % chars.length]; }
    return out;
  }

  async function request(path, opts={}){
    const base = getApiBase()
    const headers = Object.assign({}, authHeaders(opts.body !== undefined ? true : false), opts.headers||{})
    const res = await fetch(base + path, Object.assign({}, opts, { headers }))
    const text = await res.text()
    let data = null
    try{ data = text ? JSON.parse(text) : null }catch(e){ data = null }
    if(!res.ok){
      const detail = (data && (data.detail || data.error)) ? (data.detail || data.error) : (text || 'request failed')
      throw new Error(detail)
    }
    return data
  }

  function fmtDate(ts){ if(!ts) return '—'; try{ return new Date(ts*1000).toLocaleString() }catch(e){ return String(ts) }
  }
  function fmtUptime(sec){ if(!sec && sec!==0) return '—'; const d=Math.floor(sec/86400); const h=Math.floor((sec%86400)/3600); const m=Math.floor((sec%3600)/60); return `${d}d ${h}h ${m}m`; }

  function humanFileSize(bytes){ if(bytes==null) return '—'; const thresh=1024; if(Math.abs(bytes)<thresh) return bytes+' B'; const units=['KB','MB','GB','TB']; let u=-1; do{ bytes/=thresh; ++u }while(Math.abs(bytes)>=thresh && u<units.length-1); return bytes.toFixed(1)+' '+units[u] }

  // Utility: debounce a function (used for interactive search)
  function debounce(fn, wait=250){ let timer = null; return function(...args){ if(timer) clearTimeout(timer); timer = setTimeout(()=>{ try{ fn.apply(this, args) }catch(e){ console.error(e) } }, wait) } }

  async function loadTorrents(){
    const container = document.getElementById('torrentsList')
    if(!container) return
    container.textContent = 'Cargando...'
    try{
      const res = await request('/stream/torrents', { method: 'GET' })
      const list = (res && res.torrents) ? res.torrents : []
      lastTorrents = list
      if(!list.length){ container.innerHTML = '<div class="mini-body" style="color:var(--muted)">No hay torrents</div>'; return }
      renderTorrentList(list, container)
    }catch(e){ container.textContent = 'Error: '+e.message }
  }

  function renderTorrentList(list, container){
    if(!container) container = document.getElementById('torrentsList')
    container.innerHTML = ''
    const table = document.createElement('table'); table.className='table';
    const thead = document.createElement('thead'); thead.innerHTML = '<tr><th>Archivo</th><th>Tamaño</th><th>Modificado</th><th>Acciones</th></tr>'
    table.appendChild(thead)
    const tbody = document.createElement('tbody')
    list.forEach(t=>{
      const tr = document.createElement('tr')
      const tdName = document.createElement('td'); tdName.textContent = t.name || '—'; tr.appendChild(tdName)
      const tdSize = document.createElement('td'); tdSize.textContent = humanFileSize(t.size); tr.appendChild(tdSize)
      const tdM = document.createElement('td'); tdM.textContent = t.mtime ? fmtDate(t.mtime) : '—'; tr.appendChild(tdM)
      const tdAct = document.createElement('td');
      const a = document.createElement('a'); a.className='secondary'; a.textContent='Descargar';
      const base = getApiBase();
      const torrentUrl = base.replace(/\/+$/,'') + '/torrents/' + encodeURIComponent(t.name)
      a.href = torrentUrl
      a.target = '_blank'
      tdAct.appendChild(a)
      // View in WebTorrent
      const viewBtn = document.createElement('button'); viewBtn.className='secondary'; viewBtn.style.marginLeft='8px'; viewBtn.textContent = 'Ver';
      viewBtn.addEventListener('click', ()=>{
        const url = '/multimedia.html?torrent=' + encodeURIComponent(torrentUrl)
        window.open(url, '_blank')
      })
      tdAct.appendChild(viewBtn)
      const sendBtn = document.createElement('button'); sendBtn.className='btn'; sendBtn.style.marginLeft='8px'; sendBtn.textContent='Enviar';
      sendBtn.addEventListener('click', async ()=>{
        if(!confirm('Enviar '+t.name+' por Telegram?')) return
        try{
          sendBtn.disabled=true; sendBtn.textContent='Enviando...'
          await request('/admin/send_torrent', { method:'POST', body: JSON.stringify({ name: t.name }) })
          alert('Pedido de envío iniciado')
        }catch(e){ alert('Error: '+e.message) }
        sendBtn.disabled=false; sendBtn.textContent='Enviar'
      })
      tdAct.appendChild(sendBtn)
      // Add "Ver MP4" button if a matching MP4 exists alongside this torrent
      try{
        const nameBase = (t.name || '').replace(/\.[^/.]+$/, '')
        if(nameBase){
            const mp4Path = 'torrents/' + nameBase + '.mp4'
            const mp4Url = (base.replace(/\/+$/, '') || '') + '/media/stream/' + encodeURIComponent(mp4Path)
            const viewMp4Btn = document.createElement('button'); viewMp4Btn.className='primary'; viewMp4Btn.style.marginLeft='8px'; viewMp4Btn.textContent='Ver MP4';
            viewMp4Btn.style.display = 'none'
            viewMp4Btn.addEventListener('click', ()=>{ showDownloadProgress(mp4Url, mp4Path) })
          tdAct.appendChild(viewMp4Btn)
          // probe existence: try HEAD, fallback to GET with Range for servers that don't support HEAD
          fetch(mp4Url, { method: 'HEAD' }).then(r=>{ if(r && (r.ok || r.status===206)){ viewMp4Btn.style.display='inline-block' } else {
            // fallback
            fetch(mp4Url, { method: 'GET', headers: { 'Range': 'bytes=0-0' } }).then(r2=>{ if(r2 && (r2.ok || r2.status===206)) viewMp4Btn.style.display='inline-block' }).catch(()=>{})
          } }).catch(()=>{
            fetch(mp4Url, { method: 'GET', headers: { 'Range': 'bytes=0-0' } }).then(r2=>{ if(r2 && (r2.ok || r2.status===206)) viewMp4Btn.style.display='inline-block' }).catch(()=>{})
          })
        }
      }catch(e){}
      tr.appendChild(tdAct)
      tbody.appendChild(tr)
    })
    table.appendChild(tbody)
    container.appendChild(table)
  }

  // Show modal with progress bar and poll for download progress.
  async function showDownloadProgress(streamUrl, mediaPath){
    const overlay = document.createElement('div'); overlay.style.position='fixed'; overlay.style.left=0; overlay.style.top=0; overlay.style.right=0; overlay.style.bottom=0; overlay.style.background='rgba(0,0,0,0.6)'; overlay.style.display='flex'; overlay.style.alignItems='center'; overlay.style.justifyContent='center'; overlay.style.zIndex=9999;
    const box = document.createElement('div'); box.style.background='var(--card)'; box.style.padding='18px'; box.style.borderRadius='10px'; box.style.width='480px'; box.style.maxWidth='90%'; box.style.color='var(--text)';
    const title = document.createElement('div'); title.style.fontWeight='700'; title.style.marginBottom='8px'; title.innerText='Progreso de descarga';
    const progBar = document.createElement('div'); progBar.style.height='12px'; progBar.style.background='rgba(255,255,255,0.06)'; progBar.style.borderRadius='8px'; progBar.style.overflow='hidden'; progBar.style.marginBottom='8px';
    const progFill = document.createElement('div'); progFill.style.height='100%'; progFill.style.width='0%'; progFill.style.background='#06b6d4'; progFill.style.transition='width 300ms'; progBar.appendChild(progFill);
    const progText = document.createElement('div'); progText.style.fontSize='0.95rem'; progText.style.color='var(--muted)'; progText.style.marginBottom='12px'; progText.innerText='Comprobando...';
    const actions = document.createElement('div'); actions.style.display='flex'; actions.style.justifyContent='flex-end'; actions.style.gap='8px';
    const openBtn = document.createElement('button'); openBtn.className='btn'; openBtn.textContent='Abrir reproducción'; openBtn.disabled = true;
    const closeBtn = document.createElement('button'); closeBtn.className='ghost'; closeBtn.textContent='Cerrar';
    actions.appendChild(closeBtn); actions.appendChild(openBtn);
    box.appendChild(title); box.appendChild(progBar); box.appendChild(progText); box.appendChild(actions); overlay.appendChild(box); document.body.appendChild(overlay);

    let stop = false; closeBtn.addEventListener('click', ()=>{ stop=true; overlay.remove() });
    openBtn.addEventListener('click', ()=>{ window.open('/multimedia.html?file='+encodeURIComponent(streamUrl),'_blank'); stop=true; overlay.remove() });

    async function checkBotProgress(nameBase){
      try{
        const r = await fetch('http://127.0.0.1:8081/torrents');
        if(!r.ok) return null;
        const j = await r.json(); const list = j.torrents || [];
        for(const t of list){ if(t.name && t.name.indexOf(nameBase) !== -1){ return t.progress != null ? Math.round((t.progress||0)*100) : null } }
      }catch(e){ }
      return null
    }

    async function getExpectedSize(path){
      try{ const r = await request('/media/files'); const arr = r.files || []; for(const it of arr){ if(it.path === path) return it.size || null } }catch(e){}
      return null
    }

    const nameBase = mediaPath.replace(/\.[^/.]+$/, '').replace(/^torrents\//, '');
    let expected = await getExpectedSize(mediaPath)
    let lastPercent = 0
    while(!stop){
      const botP = await checkBotProgress(nameBase)
      if(botP != null){ progFill.style.width = botP + '%'; progText.innerText = botP + '%'; lastPercent = botP; if(botP >= 100){ openBtn.disabled=false; progText.innerText='Completado'; break } }
      else {
        try{
          const h = await fetch(streamUrl, { method: 'HEAD' })
          if(h && (h.ok || h.status===206)){
            const cur = parseInt(h.headers.get('Content-Length') || h.headers.get('content-length') || '0') || 0
            if(!expected){ expected = await getExpectedSize(mediaPath) }
            if(expected){ const p = Math.min(100, Math.round((cur / expected) * 100)); progFill.style.width = p + '%'; progText.innerText = p + '%  —  ' + (cur?cur+' bytes':'0 B') + ' de ' + expected + ' bytes'; lastPercent = p; if(p>=100){ openBtn.disabled=false; progText.innerText='Completado'; break } }
            else { progText.innerText = (cur?cur+' bytes descargados':'0 B'); progFill.style.width = lastPercent + '%'; }
          }
        }catch(e){ }
      }
      await new Promise(r=>setTimeout(r, 2000));
    }
    if(!stop){ openBtn.disabled = false }
  }

  function renderUsers(users){
    if(!usersTable) return
    usersTable.innerHTML = ''
    if(!users || !users.length){
      const tr = document.createElement('tr'); const td=document.createElement('td'); td.colSpan=4; td.style.textAlign='center'; td.style.color='var(--muted)'; td.textContent='Sin usuarios'; tr.appendChild(td); usersTable.appendChild(tr); return
    }
    users.forEach(u=>{
      const tr = document.createElement('tr')
      const tdUser = document.createElement('td'); tdUser.textContent = u.user || '(sin nombre)'; tr.appendChild(tdUser)
      const tdAdmin = document.createElement('td'); tdAdmin.textContent = u.is_admin ? 'Sí' : 'No'; tr.appendChild(tdAdmin)
      const tdCreated = document.createElement('td'); tdCreated.textContent = fmtDate(u.created_at); tr.appendChild(tdCreated)
      const tdActions = document.createElement('td');
      const btnReset = document.createElement('button'); btnReset.className='secondary'; btnReset.textContent='Reset pass'; btnReset.addEventListener('click',()=>resetUser(u.user))
      const btnDelete = document.createElement('button'); btnDelete.className='ghost'; btnDelete.textContent='Eliminar'; btnDelete.style.marginLeft='6px'; btnDelete.addEventListener('click',()=>deleteUser(u.user))
      tdActions.appendChild(btnReset); tdActions.appendChild(btnDelete); tr.appendChild(tdActions)
      usersTable.appendChild(tr)
    })
  }

  function renderStatus(data){
    if(!statusSummary || !sessionSummary) return
    if(!data){ statusSummary.textContent='Sin datos'; sessionSummary.textContent='Sin datos'; return }
    const redisOk = data.redis && data.redis.ok
    const mem = data.redis ? data.redis.used_memory_human : null
    const uptime = fmtUptime(data.uptime)
    statusSummary.textContent = `Uptime ${uptime || '—'} | Redis ${redisOk ? 'OK' : 'Error'}${mem ? ' ('+mem+')' : ''} | Páginas ${data.pages ? data.pages.length : 0}`
    const counts = data.counts || {}
    sessionSummary.textContent = `Usuarios ${counts.users ?? '—'} | Sesiones ${counts.sessions ?? '—'} | Mensajes ${counts.messages ?? '—'} | Devices ${counts.devices ?? '—'}`
  }

  function renderBotStats(stats){
    if(!botStatsSummary) return
    if(!stats){ botStatsSummary.textContent='Sin datos'; return }
    const parts = []
    if(stats.messages_count!=null) parts.push(`Mensajes ${stats.messages_count}`)
    if(stats.tdlib_events_count!=null) parts.push(`TDLib ${stats.tdlib_events_count}`)
    if(stats.server_uptime!=null) parts.push(`Uptime ${fmtUptime(stats.server_uptime)}`)
    if(stats.processes && Array.isArray(stats.processes)){
      const running = stats.processes.filter(p=>p && p.running).map(p=>p.name || 'proc').join(', ')
      if(running) parts.push(`Procesos: ${running}`)
    }
    botStatsSummary.textContent = parts.join(' | ') || 'Sin datos'
  }

  function renderBots(accounts){
    if(!botsList) return
    botsList.innerHTML = ''
    const accs = accounts && accounts.accounts ? accounts.accounts : accounts
    if(!accs || !accs.length){
      const div = document.createElement('div'); div.className='mini-body'; div.style.color='var(--muted)'; div.textContent='Sin bots registrados'; botsList.appendChild(div); return
    }
    accs.forEach(acc=>{
      const card = document.createElement('div'); card.className='mini-card'
      const title = document.createElement('div'); title.className='mini-title'; title.textContent = acc.name || acc.id || 'Bot'
      const body = document.createElement('div'); body.className='mini-body'
      const id = document.createElement('div'); id.textContent = `ID: ${acc.id || '—'}`; body.appendChild(id)
      const token = document.createElement('div'); token.style.color='var(--muted)'; token.textContent = `Token: ${acc.token_masked || (acc.has_token ? 'oculto' : 'no')}`; body.appendChild(token)
      if(acc.getMe){
        const gm = acc.getMe
        const uname = gm.username ? '@'+gm.username : ''
        const line = document.createElement('div'); line.textContent = `getMe: ${gm.first_name || gm.title || ''} ${uname}`; body.appendChild(line)
      } else if(acc.getMe_error){
        const err = document.createElement('div'); err.style.color='var(--muted)'; err.textContent = `getMe error: ${acc.getMe_error}`; body.appendChild(err)
      }
      const actions = document.createElement('div'); actions.style.marginTop='8px';
      const del = document.createElement('button'); del.className='ghost'; del.textContent='Eliminar'; del.addEventListener('click',()=>deleteBot(acc.id))
      actions.appendChild(del)
      card.appendChild(title); card.appendChild(body); card.appendChild(actions);
      botsList.appendChild(card)
    })
  }

  async function createUser(){
    const user = newUserInput && newUserInput.value ? newUserInput.value.trim() : ''
    const pass = newPassInput && newPassInput.value ? newPassInput.value.trim() : ''
    if(!user || !pass){ alert('Usuario y contraseña requeridos'); return }
    await request('/admin/users', { method:'POST', body: JSON.stringify({ user, pass, is_admin: !!(newIsAdmin && newIsAdmin.checked) }) })
    alert('Usuario creado')
    newPassInput.value=''
    await loadUsers()
  }

  async function resetUser(user){
    if(!user) return
    const pass = prompt('Nueva contraseña para '+user)
    if(!pass) return
    await request('/admin/users/reset', { method:'POST', body: JSON.stringify({ user, pass }) })
    alert('Contraseña reiniciada')
  }

  async function deleteUser(user){
    if(!user) return
    if(!confirm('¿Eliminar usuario '+user+'?')) return
    await request('/admin/users/'+encodeURIComponent(user), { method:'DELETE' })
    await loadUsers()
  }

  async function deleteBot(id){
    if(!id) return
    if(!confirm('¿Eliminar bot/dispositivo '+id+'?')) return
    await request('/devices/'+encodeURIComponent(id), { method:'DELETE' })
    await loadBots()
  }

  async function loadUsers(){
    try{
      const data = await request('/admin/users')
      renderUsers(data ? data.users : [])
      setConnection('API OK', true)
    }catch(e){
      renderUsers([])
      setConnection('Error usuarios: '+e.message, false)
    }
  }

  async function loadOverview(){
    try{
      const data = await request('/admin/overview')
      if(data){
        if(data.users) renderUsers(data.users)
        if(data.status) renderStatus(data.status)
        if(data.bot_stats) renderBotStats(data.bot_stats)
        if(data.bot_accounts) renderBots(data.bot_accounts)
        setConnection('API OK', true)
        return
      }
    }catch(e){
      setConnection('Fallo /admin/overview: '+e.message, false)
    }
    // fallback calls
    try{ const s = await request('/status', { method:'GET', headers: authHeaders(false) }); renderStatus(s) }catch(e){ renderStatus(null) }
    try{ const bs = await request('/bot/stats', { method:'GET' }); renderBotStats(bs) }catch(e){ renderBotStats(null) }
    try{ const ba = await request('/bot/accounts', { method:'GET' }); renderBots(ba) }catch(e){ renderBots([]) }
  }

  async function loadBots(){
    try{ const ba = await request('/bot/accounts', { method:'GET' }); renderBots(ba); setConnection('API OK', true) }catch(e){ renderBots([]); setConnection('Error bots: '+e.message, false) }
  }

  async function loadInstalledModels(){
    if(!installedModelsList) return
    installedModelsList.textContent = 'Cargando...'
    try{
      const res = await request('/models/list', { method: 'GET' })
      const arr = res && res.models ? res.models : []
      if(!arr.length) installedModelsList.textContent = '(ninguno)'
      else installedModelsList.textContent = arr.join(', ')
      modelInstallStatus.textContent = ''
      renderModelCatalog(arr)
    }catch(e){
      installedModelsList.textContent = 'Error: '+e.message
      renderModelCatalog([])
    }
  }

  // Monitor control functions
  async function loadMonitorStatus(){
    if(!monitorStatusText) return
    monitorStatusText.textContent = 'Consultando monitor...'
    if(monitorLog) monitorLog.textContent = 'Cargando logs...'
    try{
      const res = await request('/monitor/status', { method: 'GET' })
      monitorStatusText.textContent = res.running ? `Monitor activo (pid ${res.pid || '—'})` : 'Monitor detenido'
      if(monitorLog) monitorLog.textContent = res.log_tail || '(sin logs)'
      // also load per-service status
      try{ loadServiceControls() }catch(e){}
    }catch(e){
      monitorStatusText.textContent = 'Error consultando monitor: '+e.message
      if(monitorLog) monitorLog.textContent = ''
    }
  }

  async function loadServiceControls(){
    const container = document.getElementById('serviceControls')
    if(!container) return
    container.textContent = 'Cargando servicios...'
    try{
      const res = await request('/monitor/service/status', { method: 'GET' })
      container.innerHTML = ''
      // add Restart All button binding
      const restartAllBtn = document.getElementById('restartAllServicesBtn')
      if(restartAllBtn){ restartAllBtn.onclick = async ()=>{ if(!confirm('Reiniciar TODOS los servicios?')) return; restartAllBtn.disabled=true; restartAllBtn.textContent='Reiniciando...'; try{ await request('/monitor/service/restart_all', { method:'POST' }); setTimeout(()=>{ loadMonitorStatus() }, 1200) }catch(e){ alert('Error reiniciando todos: '+e.message) } restartAllBtn.disabled=false; restartAllBtn.textContent='Reiniciar todos' } }
      (res.services || []).forEach(s=>{
        const row = document.createElement('div')
        row.style.display='flex'; row.style.justifyContent='space-between'; row.style.alignItems='center'; row.style.marginTop='6px'
        const left = document.createElement('div')
        // build status and metrics display
        const running = s.running ? true : false
        const statusLine = running ? `running (pid:${s.pid||'—'})` : '(stopped)'
        const metrics = []
        try{ if(s.cpu_percent!=null) metrics.push(`CPU ${Number(s.cpu_percent).toFixed(1)}%`) }catch(e){}
        try{ if(s.memory_rss!=null) metrics.push(`Mem ${humanFileSize(s.memory_rss)}`) }catch(e){}
        try{ if(s.uptime_seconds!=null) metrics.push(`Uptime ${fmtUptime(s.uptime_seconds)}`) }catch(e){}
        left.innerHTML = `<div style="font-weight:700">${s.name}</div><div class="small muted">${statusLine}${metrics.length? ' — '+metrics.join(' | '):''}</div>`
        const ctrl = document.createElement('div')
        const btn = document.createElement('button'); btn.className='secondary'; btn.textContent='Reiniciar';
        btn.addEventListener('click', async ()=>{
          try{
            btn.disabled=true; btn.textContent='Reiniciando...'
            await request('/monitor/service/restart', { method:'POST', body: JSON.stringify({ service: s.name }) })
            setTimeout(()=>{ loadMonitorStatus() }, 1200)
          }catch(e){ alert('Error reiniciando: '+e.message) }
          btn.disabled=false; btn.textContent='Reiniciar'
        })
        ctrl.appendChild(btn)
        row.appendChild(left); row.appendChild(ctrl)
        container.appendChild(row)
      })

      // Docker section
      try{
        const dock = res.docker || []
        const hdr = document.createElement('div'); hdr.style.marginTop='10px'; hdr.style.fontWeight='700'; hdr.textContent='Containers Docker'
        container.appendChild(hdr)
        if(!dock || (Array.isArray(dock) && dock.length===0)){
          const empty = document.createElement('div'); empty.className='mini-body'; empty.style.color='var(--muted)'; empty.textContent='No hay contenedores detectados'; container.appendChild(empty)
        } else if(dock.error){
          const err = document.createElement('div'); err.className='mini-body'; err.style.color='var(--muted)'; err.textContent='Docker error: '+dock.error; container.appendChild(err)
        } else {
          dock.forEach(c=>{
            const row = document.createElement('div'); row.className='mini-card'; row.style.marginTop='6px'
            const title = document.createElement('div'); title.className='mini-title'; title.textContent = c.name || c.id || 'container'
            const body = document.createElement('div'); body.className='mini-body'
            const parts = []
            if(c.status) parts.push(c.status)
            if(c.cpu_percent!=null) parts.push('CPU '+(Number(c.cpu_percent).toFixed?Number(c.cpu_percent).toFixed(1):c.cpu_percent)+'%')
            if(c.memory_rss!=null) parts.push('Mem '+humanFileSize(c.memory_rss))
            row.appendChild(title); row.appendChild(body); container.appendChild(row)
          })
        }
      }catch(e){ /* ignore */ }

      // Kubernetes section
      try{
        const k8s = res.k8s || []
        const hdr2 = document.createElement('div'); hdr2.style.marginTop='10px'; hdr2.style.fontWeight='700'; hdr2.textContent='Kubernetes Pods'
        container.appendChild(hdr2)
        if(!k8s || (Array.isArray(k8s) && k8s.length===0)){
          const empty = document.createElement('div'); empty.className='mini-body'; empty.style.color='var(--muted)'; empty.textContent='No se detectaron pods o no hay acceso a K8s'; container.appendChild(empty)
        } else if(k8s.error){
          const err = document.createElement('div'); err.className='mini-body'; err.style.color='var(--muted)'; err.textContent='K8s error: '+k8s.error; container.appendChild(err)
        } else {
          k8s.slice(0,40).forEach(pod=>{
            const row = document.createElement('div'); row.className='mini-card'; row.style.marginTop='6px'
            const title = document.createElement('div'); title.className='mini-title'; title.textContent = (pod.namespace?pod.namespace+'/':'') + (pod.name || pod.namespace || 'pod')
            const body = document.createElement('div'); body.className='mini-body'
            const parts = []
            if(pod.status) parts.push(pod.status)
            if(pod.cpu) parts.push('CPU '+pod.cpu)
            if(pod.mem) parts.push('Mem '+pod.mem)
            if(pod.age_seconds!=null) parts.push('Age '+fmtUptime(pod.age_seconds))
            body.textContent = parts.join(' | ')
            row.appendChild(title); row.appendChild(body); container.appendChild(row)
          })
        }
      }catch(e){ /* ignore */ }
    }catch(e){ container.textContent='Error cargando servicios: '+e.message }
  }

  async function startMonitor(){
    if(startMonitorBtn) startMonitorBtn.disabled = true
    try{
      await request('/monitor/start', { method: 'POST' })
      await loadMonitorStatus()
    }catch(e){ alert('Error iniciando monitor: '+e.message) }
    if(startMonitorBtn) startMonitorBtn.disabled = false
  }

  async function stopMonitor(){
    if(stopMonitorBtn) stopMonitorBtn.disabled = true
    try{
      await request('/monitor/stop', { method: 'POST' })
      await loadMonitorStatus()
    }catch(e){ alert('Error deteniendo monitor: '+e.message) }
    if(stopMonitorBtn) stopMonitorBtn.disabled = false
  }

  async function restartMonitor(){
    if(restartMonitorBtn) restartMonitorBtn.disabled = true
    try{
      await request('/monitor/stop', { method: 'POST' })
    }catch(e){}
    try{ await request('/monitor/start', { method: 'POST' }) }catch(e){ alert('Error reiniciando monitor: '+e.message) }
    await loadMonitorStatus()
    if(restartMonitorBtn) restartMonitorBtn.disabled = false
  }

  async function installModel(){
    const m = modelNameInput && modelNameInput.value ? modelNameInput.value.trim() : ''
    if(!m){ alert('Introduce el nombre del modelo'); return }
    if(modelInstallStatus) modelInstallStatus.textContent = 'Instalando '+m+'...'
    try{
      const res = await request('/models/install', { method: 'POST', body: JSON.stringify({ model: m }) })
      if(res && res.ok){
        modelInstallStatus.textContent = 'Instalado: '+(res.model || m)
        await loadInstalledModels()
      }else{
        modelInstallStatus.textContent = 'Respuesta: '+JSON.stringify(res)
      }
    }catch(e){ modelInstallStatus.textContent = 'Error: '+e.message }
  }

  // Predefined catalog of models to show in the UI
  const MODEL_CATALOG = [
    'gpt2',
    'distilgpt2',
    'facebook/opt-125m',
    'facebook/opt-350m',
    'EleutherAI/gpt-neo-125M',
    'google/flan-t5-small',
    'bigscience/bigscience-small-testing'
  ]

  function renderModelCatalog(installed){
    if(!modelCatalogDiv) return
    modelCatalogDiv.innerHTML = ''
    const frag = document.createDocumentFragment()
    MODEL_CATALOG.forEach(m=>{
      const row = document.createElement('div')
      row.className = 'mini-card'
      const title = document.createElement('div')
      title.className = 'mini-title'
      title.textContent = m
      const body = document.createElement('div')
      body.className = 'mini-body'
      const installedFlag = (installed || []).indexOf(m) !== -1
      body.textContent = installedFlag ? 'Estado: instalado' : 'Estado: no instalado'
      const actions = document.createElement('div')
      actions.style.marginTop = '8px'
      const btn = document.createElement('button')
      btn.className = installedFlag ? 'secondary' : 'btn'
      btn.textContent = installedFlag ? 'Reinstalar' : 'Instalar'
      btn.addEventListener('click', async ()=>{
        if(modelInstallStatus) modelInstallStatus.textContent = (installedFlag ? 'Reinstalando ' : 'Instalando ') + m + '...'
        try{
          const res = await request('/models/install', { method: 'POST', body: JSON.stringify({ model: m }) })
          if(res && res.ok){
            modelInstallStatus.textContent = 'Instalado: '+m
            await loadInstalledModels()
          }else{
            modelInstallStatus.textContent = 'Respuesta: '+JSON.stringify(res)
          }
        }catch(e){ modelInstallStatus.textContent = 'Error: '+e.message }
      })
      actions.appendChild(btn)
      row.appendChild(title); row.appendChild(body); row.appendChild(actions)
      frag.appendChild(row)
    })
    modelCatalogDiv.appendChild(frag)
  }

  async function discoverLan(){
    if(discoverResults) discoverResults.textContent = 'Buscando en LAN...';
    try{
      const res = await request('/discover/lan', { method:'GET' });
      renderDiscover(res && res.found ? res.found : []);
    }catch(e){
      if(discoverResults) discoverResults.textContent = 'Error: '+e.message;
    }
  }

  function renderGeoList(list, label){
    if(!list || !list.length) return `${label}: sin datos`;
    return `${label}: ` + list.map(it=>{
      const where = [it.city, it.country].filter(Boolean).join(', ')
      const coords = (it.lat && it.lon) ? `(${it.lat}, ${it.lon})` : ''
      return `${it.id||it.user||it.ip||'—'} ${where ? '— '+where : ''} ${coords}`
    }).join(' | ')
  }

  function buildMap(el){
    if(!el || typeof L === 'undefined') return null
    const map = L.map(el, { worldCopyJump:true })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map)
    const layer = L.layerGroup().addTo(map)
    map.setView([20, 0], 2)
    setTimeout(()=>map.invalidateSize(), 50)
    return { map, layer }
  }

  function updateMap(which, items){
    const el = which === 'bots' ? mapBotsEl : mapUsersEl
    let ref = which === 'bots' ? botMapRef : userMapRef
    if(!el) return
    if(typeof L === 'undefined'){
      el.textContent = 'Leaflet no cargó'
      return
    }
    if(!ref){
      ref = buildMap(el)
      if(which === 'bots') botMapRef = ref; else userMapRef = ref
    }
    if(!ref) return
    ref.layer.clearLayers()
    const coords = []
    ;(items || []).forEach(it=>{
      const lat = parseFloat(it.lat)
      const lon = parseFloat(it.lon)
      if(Number.isFinite(lat) && Number.isFinite(lon)){
        coords.push({ lat, lon })
        const title = it.id || it.user || it.ip || 'Desconocido'
        const where = [it.city, it.country].filter(Boolean).join(', ')
        const ip = it.ip ? `IP: ${it.ip}` : ''
        const org = it.org ? `ISP: ${it.org}` : ''
        const popup = [title, where, ip, org].filter(Boolean).join('<br>')
        L.marker([lat, lon]).addTo(ref.layer).bindPopup(popup || title)
      }
    })
    if(!coords.length){
      ref.map.setView([20, 0], 2)
      return
    }
    if(coords.length === 1){
      ref.map.setView([coords[0].lat, coords[0].lon], 5)
    }else{
      ref.map.fitBounds(coords.map(c=>[c.lat, c.lon]), { padding:[18,18] })
    }
    setTimeout(()=>ref.map.invalidateSize(), 50)
  }

  async function loadGeo(){
    if(geoBotsDiv) geoBotsDiv.textContent = 'Geo bots: cargando...';
    if(geoUsersDiv) geoUsersDiv.textContent = 'Geo usuarios: cargando...';
    try{
      const res = await request('/geo/summary', { method:'GET' });
      const bots = res && res.bots ? res.bots : []
      const users = res && res.users ? res.users : []
      if(geoBotsDiv) geoBotsDiv.textContent = renderGeoList(bots, 'Geo bots');
      if(geoUsersDiv) geoUsersDiv.textContent = renderGeoList(users, 'Geo usuarios');
      updateMap('bots', bots)
      updateMap('users', users)
    }catch(e){
      if(geoBotsDiv) geoBotsDiv.textContent = 'Geo bots: error '+e.message;
      if(geoUsersDiv) geoUsersDiv.textContent = 'Geo usuarios: error '+e.message;
    }
  }

  function saveConnection(){
    const base = apiBaseInput && apiBaseInput.value ? apiBaseInput.value.trim() : ''
    const tok = apiTokenInput && apiTokenInput.value ? apiTokenInput.value.trim() : ''
    if(base) localStorage.setItem(API_BASE_KEY, base)
    if(tok) localStorage.setItem('api_token', tok)
    if(base) saveApiBaseHistory(base)
    alert('Conexión guardada')
  }

  // init values
  try{ const saved = localStorage.getItem(API_BASE_KEY); if(saved && apiBaseInput) apiBaseInput.value = saved }catch(e){}
  try{ const tok = localStorage.getItem('api_token'); if(tok && apiTokenInput && !apiTokenInput.value) apiTokenInput.value = tok }catch(e){}
  loadApiBaseHistory()

  // wire events
  if(refreshAllBtn) refreshAllBtn.addEventListener('click', ()=>{ loadOverview(); loadUsers(); })
  if(refreshOverviewBtn) refreshOverviewBtn.addEventListener('click', loadOverview)
  if(refreshBotsBtn) refreshBotsBtn.addEventListener('click', loadBots)
  if(discoverLanBtn) discoverLanBtn.addEventListener('click', discoverLan)
  if(refreshGeoBtn) refreshGeoBtn.addEventListener('click', loadGeo)
  if(refreshTorrentsBtn) refreshTorrentsBtn.addEventListener('click', loadTorrents)
  if(uploadTorrentBtn) uploadTorrentBtn.addEventListener('click', uploadTorrent)
  if(torrentSearchBtn) torrentSearchBtn.addEventListener('click', ()=>{
    try{
      const q = torrentSearchInput && torrentSearchInput.value ? torrentSearchInput.value.trim().toLowerCase() : ''
      const container = document.getElementById('torrentsList')
      if(!q){ renderTorrentList(lastTorrents, container); return }
      const filtered = (lastTorrents || []).filter(t=> (t.name||'').toLowerCase().indexOf(q) !== -1 )
      if(!filtered.length){ container.innerHTML = '<div class="mini-body" style="color:var(--muted)">No hay torrents que coincidan</div>'; return }
      renderTorrentList(filtered, container)
    }catch(e){ console.error(e) }
  })
  if(torrentClearBtn) torrentClearBtn.addEventListener('click', ()=>{ if(torrentSearchInput) torrentSearchInput.value=''; renderTorrentList(lastTorrents) })
  if(myTorrentsBtn) myTorrentsBtn.addEventListener('click', ()=>{
    // try to read logged user from localStorage, otherwise prompt
    let user = null
    try{ user = localStorage.getItem('api_user') || '' }catch(e){ user = '' }
    if(!user){ user = prompt('Introduce tu usuario para ver tus torrents:') || '' }
    if(!user) return
    window.open('/torrents_user.html?user=' + encodeURIComponent(user), '_blank')
  })
  if(torrentSearchInput){
    const doFilter = ()=>{
      try{
        const q = torrentSearchInput && torrentSearchInput.value ? torrentSearchInput.value.trim().toLowerCase() : ''
        const container = document.getElementById('torrentsList')
        if(!q){ renderTorrentList(lastTorrents, container); return }
        const filtered = (lastTorrents || []).filter(t=> (t.name||'').toLowerCase().indexOf(q) !== -1 )
        if(!filtered.length){ container.innerHTML = '<div class="mini-body" style="color:var(--muted)">No hay torrents que coincidan</div>'; return }
        renderTorrentList(filtered, container)
      }catch(e){ console.error(e) }
    }
    torrentSearchInput.addEventListener('input', debounce(doFilter, 200))
    torrentSearchInput.addEventListener('keydown', (ev)=>{ if(ev.key === 'Enter'){ ev.preventDefault(); doFilter() } })
  }
  if(createUserBtn) createUserBtn.addEventListener('click', createUser)
  if(saveConnectionBtn) saveConnectionBtn.addEventListener('click', saveConnection)
  if(refreshModelsBtn) refreshModelsBtn.addEventListener('click', loadInstalledModels)
  if(installModelBtn) installModelBtn.addEventListener('click', installModel)
  if(genPassEmailBtn) genPassEmailBtn.addEventListener('click', ()=>{
    const user = newUserInput && newUserInput.value ? newUserInput.value.trim() : ''
    if(!user){ alert('Introduce el correo/usuario primero'); return }
    const pwd = randomPassword(16)
    if(newPassInput) newPassInput.value = pwd
    try{
      const subject = encodeURIComponent('Tu nueva contraseña DBTeam')
      const body = encodeURIComponent('Hola,\n\nAquí tienes una contraseña generada:\n\n'+pwd+'\n\nCámbiala tras iniciar sesión.')
      window.open('mailto:'+encodeURIComponent(user)+'?subject='+subject+'&body='+body, '_blank')
    }catch(e){ alert('No se pudo abrir el cliente de correo'); }
  })
  if(apiBaseInput) apiBaseInput.addEventListener('blur', ()=>{ const v = apiBaseInput.value && apiBaseInput.value.trim(); if(v){ localStorage.setItem(API_BASE_KEY, v); saveApiBaseHistory(v) } })

  // initial load: avoid automatic network calls so the page renders even if backends are down.
  // Use the UI buttons to refresh data on demand.

  if(startMonitorBtn) startMonitorBtn.addEventListener('click', startMonitor)
  if(stopMonitorBtn) stopMonitorBtn.addEventListener('click', stopMonitor)
  if(restartMonitorBtn) restartMonitorBtn.addEventListener('click', restartMonitor)
  // load monitor status and services shortly after page load (non-blocking)
  try{ setTimeout(()=>{ loadMonitorStatus().catch(()=>{}) }, 300) }catch(e){}
  try{ setTimeout(()=>{ loadTorrents().catch(()=>{}) }, 600) }catch(e){}
  try{ setTimeout(()=>{ loadTorrentTargets().catch(()=>{}) }, 300) }catch(e){}
  
  async function uploadTorrent(){
    if(!torrentFileInput || !torrentFileInput.files || !torrentFileInput.files.length){ alert('Selecciona un archivo .torrent'); return }
    const file = torrentFileInput.files[0]
    const fd = new FormData()
    fd.append('file', file)
    // include optional target device id so backend or future handlers know destination
    try{ const target = torrentTargetSelect && torrentTargetSelect.value ? torrentTargetSelect.value : 'local'; fd.append('device_id', target) }catch(e){}
    const btn = uploadTorrentBtn
    try{
      if(btn) { btn.disabled=true; btn.textContent='Subiendo...' }
      const base = getApiBase()
      const headers = authHeaders(false)
      // ensure we do NOT set Content-Type when sending FormData (browser will set the boundary)
      try{ if(headers['Content-Type']) delete headers['Content-Type'] }catch(e){}
      // include assign_user if provided
      try{ const assign = assignUserInput && assignUserInput.value ? assignUserInput.value.trim() : null; if(assign) fd.append('assign_user', assign) }catch(e){}
      const res = await fetch((base || '') + '/stream/upload_torrent', { method: 'POST', body: fd, headers })
      if(!res.ok){ const txt = await res.text(); console.error('upload error', res.status, txt); throw new Error(txt || res.statusText) }
      alert('Torrent subido correctamente')
      torrentFileInput.value = ''
      await loadTorrents()
    }catch(e){ alert('Error al subir: '+e.message) }
    finally{ if(btn){ btn.disabled=false; btn.textContent='Subir' } }
  }
  if(viewUserPanelBtn) viewUserPanelBtn.addEventListener('click', ()=>{
    const u = assignUserInput && assignUserInput.value ? assignUserInput.value.trim() : ''
    if(!u){ alert('Introduce el usuario en el campo "Asignar a usuario" para abrir su panel'); return }
    const url = '/torrents_user.html?user='+encodeURIComponent(u)
    window.open(url, '_blank')
  })
  // Panel de usuarios expulsados y regiones bloqueadas
  if (localStorage.getItem('role') === 'owner') {
    const bannedPanel = document.createElement('div');
    bannedPanel.id = 'bannedPanel';
    bannedPanel.style.margin = '32px 0';
    bannedPanel.innerHTML = `<h2 style='color:#c0392b'>Usuarios expulsados y regiones bloqueadas</h2><div id='bannedList'>Cargando...</div><div id='regionStatsOwner'></div>`;
    document.body.appendChild(bannedPanel);
    async function loadBannedUsers() {
      const listDiv = document.getElementById('bannedList');
      const regionDiv = document.getElementById('regionStatsOwner');
      listDiv.innerHTML = 'Cargando...';
      try {
        const resp = await fetch('/admin/banned_users', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
        if (resp.ok) {
          const data = await resp.json();
          const users = data.users || [];
          if (!users.length) { listDiv.innerHTML = '<span style="color:#888">No hay usuarios expulsados.</span>'; regionDiv.innerHTML = ''; return; }
          let html = '<table style="width:100%;margin-top:12px"><thead><tr><th>Usuario</th><th>Motivo</th><th>Región</th></tr></thead><tbody>';
          users.forEach(u => {
            html += `<tr><td>${u.user}</td><td>${u.reason}</td><td>${u.region || 'unknown'}</td></tr>`;
          });
          html += '</tbody></table>';
          listDiv.innerHTML = html;
          if (data.top_regions && data.top_regions.length) {
            let rhtml = '<h3>Regiones más bloqueadas</h3><ul>';
            for (const [region, count] of data.top_regions) {
              rhtml += `<li><strong>${region}</strong>: ${count} expulsados</li>`;
            }
            rhtml += '</ul>';
            regionDiv.innerHTML = rhtml;
          } else {
            regionDiv.innerHTML = '';
          }
        }
      } catch (e) {
        listDiv.innerHTML = '<span style="color:#f44">Error cargando expulsados.</span>';
        regionDiv.innerHTML = '';
      }
    }
    loadBannedUsers();
  }
  // Panel de gestión de grupos para owner/admin
  if (["owner","admin"].includes(localStorage.getItem('role'))) {
    const TG_PERMISSIONS = [
      'can_send_messages',
      'can_send_media_messages',
      'can_send_polls',
      'can_send_other_messages',
      'can_add_web_page_previews',
      'can_change_info',
      'can_invite_users',
      'can_pin_messages',
      'can_manage_topics',
      'can_manage_video_chats',
      'can_manage_chat',
      'can_delete_messages',
      'can_restrict_members',
      'can_promote_members',
      'can_manage_voice_chats'
    ];
    const groupAdminPanel = document.createElement('div');
    groupAdminPanel.id = 'groupAdminPanel';
    groupAdminPanel.style.margin = '32px 0';
    groupAdminPanel.innerHTML = `<h2 style='color:#6cf'>Administrar grupos</h2><div id='groupAdminList'>Cargando...</div>`;
    document.body.appendChild(groupAdminPanel);
    async function loadGroupAdmin() {
      const listDiv = document.getElementById('groupAdminList');
      listDiv.innerHTML = 'Cargando...';
      try {
        const resp = await fetch('/bot/groups', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
        if (resp.ok) {
          const js = await resp.json();
          const groups = js.groups || [];
          if (!groups.length) { listDiv.innerHTML = '<span style="color:#888">No hay grupos.</span>'; return; }
          const frag = document.createDocumentFragment();
          for (const g of groups) {
            // Verificar permisos del usuario logueado en el grupo
            let canEdit = false;
            try {
              const userId = localStorage.getItem('userId');
              const pResp = await fetch(`/bot/get_permissions/${g.id}/${userId}`, { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
              if (pResp.ok) {
                const perms = (await pResp.json()).permissions || {};
                if (TG_PERMISSIONS.some(p => perms[p])) canEdit = true;
              }
            } catch {}
            const gDiv = document.createElement('div');
            gDiv.style.background = '#222';
            gDiv.style.marginBottom = '16px';
            gDiv.style.padding = '12px';
            gDiv.style.borderRadius = '8px';
            gDiv.innerHTML = `<b>Grupo:</b> ${g.title || g.id}`;
            // Miembros y acciones
            const membersDiv = document.createElement('div');
            membersDiv.style.fontSize = '0.97em';
            membersDiv.style.color = '#ccc';
            membersDiv.innerHTML = 'Miembros: Cargando...';
            gDiv.appendChild(membersDiv);
            frag.appendChild(gDiv);
            // Cargar miembros y bans
            fetch(`/bot/group_bans/${g.id}`, { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } })
              .then(r => r.json())
              .then(data => {
                const bans = data.bans || [];
                const members = data.members || [];
                let html = '<b>Baneados:</b><br>';
                for (const b of bans) html += `- ${b.user_id} (${b.reason || ''})<br>`;
                html += '<b>Miembros:</b><br>';
                for (const m of members) {
                  html += `<span>${m.user_id} ${m.name || ''}</span> `;
                  html += `<button onclick="banUser('${g.id}','${m.user_id}')">Banear</button> `;
                  html += `<button onclick="muteUser('${g.id}','${m.user_id}')">Mutear</button> `;
                  // Permisos individuales
                  const perms = m.permissions || {};
                  html += '<span style="margin-left:8px">Permisos:</span>';
                  TG_PERMISSIONS.forEach(p => {
                    html += `<label style='margin-left:4px'><input type='checkbox' ${perms[p] ? 'checked' : ''} ${canEdit ? '' : 'disabled'} onchange="changePerm('${g.id}','${m.user_id}','${p}',this.checked)">${p.replace(/_/g,' ')}</label>`;
                  });
                  // Subir a admin si tiene permisos
                  if (Object.values(perms).filter(Boolean).length >= 3 && m.role !== 'admin' && canEdit) {
                    html += `<button onclick="changeRole('${g.id}','${m.user_id}','admin')" style='margin-left:8px'>Subir a admin</button>`;
                  }
                  html += `<select onchange="changeRole('${g.id}','${m.user_id}',this.value)" ${canEdit ? '' : 'disabled'}><option value="">Rol</option><option value="admin" ${m.role==='admin'?'selected':''}>Admin</option><option value="user" ${m.role==='user'?'selected':''}>Usuario</option></select><br>`;
                }
                membersDiv.innerHTML = html;
              });
          }
          listDiv.innerHTML = '';
          listDiv.appendChild(frag);
        }
      } catch (e) {
        listDiv.innerHTML = '<span style="color:#f44">Error cargando grupos.</span>';
      }
    }
    window.banUser = async function(groupId, userId) {
      await fetch(`/bot/ban_user/${groupId}/${userId}`, { method:'POST', headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
      loadGroupAdmin();
    }
    window.muteUser = async function(groupId, userId) {
      await fetch(`/bot/mute_user/${groupId}/${userId}`, { method:'POST', headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
      loadGroupAdmin();
    }
    window.changeRole = async function(groupId, userId, role) {
      if (!role) return;
      await fetch(`/bot/set_role/${groupId}/${userId}`, { method:'POST', headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken'), 'Content-Type':'application/json' }, body: JSON.stringify({ role }) });
      loadGroupAdmin();
    }
    window.changePerm = async function(groupId, userId, perm, value) {
      await fetch(`/bot/set_permission/${groupId}/${userId}`, { method:'POST', headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken'), 'Content-Type':'application/json' }, body: JSON.stringify({ permission: perm, value }) });
      loadGroupAdmin();
    }
    loadGroupAdmin();
  }
  // Panel de solicitudes de intervención de grupo para admin web
  if (["owner","admin"].includes(localStorage.getItem('role'))) {
    const interventionPanel = document.createElement('div');
    interventionPanel.id = 'interventionPanel';
    interventionPanel.style.margin = '32px 0';
    interventionPanel.innerHTML = `<h2 style='color:#6cf'>Solicitudes de intervención en grupos</h2><div id='interventionList'>Cargando...</div>`;
    document.body.appendChild(interventionPanel);
    async function loadInterventions() {
      const listDiv = document.getElementById('interventionList');
      listDiv.innerHTML = 'Cargando...';
      try {
        const resp = await fetch('/admin/request_intervention', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
        if (resp.ok) {
          const js = await resp.json();
          const list = js.requests || [];
          if (!list.length) { listDiv.innerHTML = '<span style="color:#888">No hay solicitudes pendientes.</span>'; return; }
          const frag = document.createDocumentFragment();
          list.forEach(req => {
            const rDiv = document.createElement('div');
            rDiv.style.background = '#222';
            rDiv.style.marginBottom = '12px';
            rDiv.style.padding = '10px';
            rDiv.style.borderRadius = '8px';
            rDiv.innerHTML = `<b>Grupo:</b> ${req.chat_title || req.chat_id}<br><b>Usuario:</b> ${req.username || req.user_id}<br><b>Motivo:</b> ${req.motivo}<br><b>Fecha:</b> ${new Date(req.ts*1000).toLocaleString()}`;
            rDiv.innerHTML += `<br><button onclick="markInterventionAttended('${req.id}')">Marcar como atendida</button>`;
            rDiv.innerHTML += ` <button onclick="openGroupPanel('${req.chat_id}')">Ir al panel del grupo</button>`;
            frag.appendChild(rDiv);
          });
          listDiv.innerHTML = '';
          listDiv.appendChild(frag);
        }
      } catch (e) {
        listDiv.innerHTML = '<span style="color:#f44">Error cargando solicitudes.</span>';
      }
    }
    window.markInterventionAttended = async function(id) {
      const comment = prompt('Comentario para la intervención (opcional):');
      await fetch(`/admin/request_intervention/${id}/attend`, {
        method:'POST',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken'), 'Content-Type':'application/json' },
        body: JSON.stringify({ comment })
      });
      loadInterventions();
      loadInterventionHistory();
    }
    window.openGroupPanel = function(chatId) {
      // Redirige al panel del grupo/bot correspondiente (ajusta la URL según tu estructura)
      window.location.href = `/bot_control.html?group=${encodeURIComponent(chatId)}`;
    }
    loadInterventions();
  }
  // Panel de historial de intervenciones para admin web
  if (["owner","admin"].includes(localStorage.getItem('role'))) {
    const interventionHistoryPanel = document.createElement('div');
    interventionHistoryPanel.id = 'interventionHistoryPanel';
    interventionHistoryPanel.style.margin = '32px 0';
    interventionHistoryPanel.innerHTML = `<h2 style='color:#6cf'>Historial de intervenciones en grupos</h2><div id='interventionHistoryList'>Cargando...</div>`;
    document.body.appendChild(interventionHistoryPanel);
    async function loadInterventionHistory() {
      const listDiv = document.getElementById('interventionHistoryList');
      listDiv.innerHTML = 'Cargando...';
      try {
        const resp = await fetch('/admin/request_intervention/history', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('authToken') } });
        if (resp.ok) {
          const js = await resp.json();
          const list = js.history || [];
          if (!list.length) { listDiv.innerHTML = '<span style="color:#888">No hay historial de intervenciones.</span>'; return; }
          const frag = document.createDocumentFragment();
          list.forEach(req => {
            const rDiv = document.createElement('div');
            rDiv.style.background = '#222';
            rDiv.style.marginBottom = '12px';
            rDiv.style.padding = '10px';
            rDiv.style.borderRadius = '8px';
            rDiv.innerHTML = `<b>Grupo:</b> ${req.chat_title || req.chat_id}<br><b>Usuario:</b> ${req.username || req.user_id}<br><b>Motivo:</b> ${req.motivo}<br><b>Fecha:</b> ${new Date(req.ts*1000).toLocaleString()}<br><b>Estado:</b> ${req.attended ? 'Atendida' : 'Pendiente'}`;
            if (req.comment) rDiv.innerHTML += `<br><b>Comentario:</b> ${req.comment}`;
            frag.appendChild(rDiv);
          });
          listDiv.innerHTML = '';
          listDiv.appendChild(frag);
        }
      } catch (e) {
        listDiv.innerHTML = '<span style="color:#f44">Error cargando historial.</span>';
      }
    }
    loadInterventionHistory();
  }
})
// --- Bubble Panel global ---
(function(){
  if (!localStorage.getItem('authToken')) return;
  if (document.getElementById('userBubblePanel')) return;
  const bubbleHTML = `
  <div class=\"bubble-panel\" id=\"userBubblePanel\" style=\"display:flex\">
    <button class=\"bubble-toggle\" id=\"bubbleToggle\" aria-label=\"Abrir menú rápido\">
      <img src=\"logo.svg\" class=\"bubble-logo\" alt=\"Panel\" />
    </button>
    <div class=\"bubble-body\" id=\"bubbleBody\">
      <div class=\"bubble-header\">
        <span class=\"bubble-title\">Panel rápido</span>
        <button class=\"bubble-close\" id=\"bubbleClose\">×</button>
      </div>
      <nav class=\"bubble-nav\">
        <a href=\"chat.html\">Chat</a>
        <a href=\"monitor.html\">Monitor</a>
        <a href=\"telegram.html\">Telegram</a>
        <a href=\"traducciones.html\">Traducciones</a>
        <a href=\"status.html\">Estado</a>
        <a href=\"links.html\">Enlaces</a>
      </nav>
      <div class=\"bubble-footer\">
        <a href=\"logout.html\" style=\"color:var(--muted);font-size:0.95em\">Cerrar sesión</a>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', bubbleHTML);
  const toggle = document.getElementById('bubbleToggle');
  const body = document.getElementById('bubbleBody');
  const close = document.getElementById('bubbleClose');
  toggle.onclick = () => body.classList.toggle('open');
  close.onclick = () => body.classList.remove('open');
  document.addEventListener('click', function(e) {
    if (!body.contains(e.target) && !toggle.contains(e.target)) {
      body.classList.remove('open');
    }
  });
})();
