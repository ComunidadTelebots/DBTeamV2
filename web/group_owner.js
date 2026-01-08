(function(){
  // Small helpers (use localStorage auth token)
  function getApiBase(){ try{ const el = document.getElementById && document.getElementById('apiBase'); const v = el && el.value ? el.value.trim() : ''; if(v) return v.replace(/\/$/,''); }catch(e){} try{ if(window && window.location && (window.location.port === '8000' || (window.location.host||'').indexOf(':8000')!==-1)) return 'http://127.0.0.1:8082' }catch(e){} return '' }
  function authHeaders(withJson=true){ const h = withJson ? {'Content-Type':'application/json'} : {}; const tok = localStorage.getItem('authToken') || localStorage.getItem('api_token') || ''; if(tok) h['Authorization']='Bearer '+tok; return h }
  async function request(path, opts={}){ const base = getApiBase(); const headers = Object.assign({}, authHeaders(opts.body!==undefined?true:false), opts.headers||{}); const res = await fetch((base||'')+path, Object.assign({}, opts, { headers })); const text = await res.text(); let data=null; try{ data = text ? JSON.parse(text) : null }catch(e){ data = null } if(!res.ok){ const detail = (data && (data.detail || data.error)) ? (data.detail || data.error) : (text || 'request failed'); throw new Error(detail) } return data }

  // Group/ban related functions (prefixed with go_ to avoid collisions)
  async function go_loadUnifiedChats(){
    const panel = document.getElementById('unifiedChatsPanel'); if(!panel) return; panel.innerHTML = 'Cargando...';
    try{
      let apiId = localStorage.getItem('tdlibApiId')||''; let apiHash = localStorage.getItem('tdlibApiHash')||''; if(!apiId||!apiHash){ /* don't prompt when used as submodule */ }
      const classicResp = await fetch('/bot/groups', { headers: authHeaders() });
      const tdlibResp = await fetch('/tdlib/chats', { headers: authHeaders() });
      let html = '';

      if(classicResp.ok){
        const js = await classicResp.json(); const chats = js.groups || [];
        if(chats.length){ html += `<div style='margin-bottom:10px'><b>Bots clásicos</b></div>`;
          chats.forEach(chat=>{
            html += `<div style='margin-bottom:10px;padding:8px 10px;background:#222;border-radius:8px'>` + `<b>${chat.title||chat.id}</b> <span style='color:#888'>(${chat.type||''})</span><br/>`;
            if(chat.members && chat.members.length){ html += `<div style='margin-top:4px;font-size:0.97em;color:#ccc'>Miembros: ${chat.members.length}</div>`;
              chat.members.slice(0,3).forEach(m=>{
                const isAdmin = m.is_admin || (m.role && (''+m.role).toLowerCase().indexOf('admin')!==-1) || (m.rights && (m.rights.is_admin || m.rights.is_creator));
                const isCurrent = window._webSession && window._webSession.telegram_id == m.id;
                html += '<div style="display:inline-block;margin-right:8px">' + (m.username||m.id||'[user]');
                if(isAdmin) html += " <span style='color:#ffb86b'>(admin)</span>";
                if(isCurrent) html += " <span style='color:#6cf'>(tú)</span>";
                // determine current user's rights for this chat
                const currentMember = (chat.members||[]).find(x=>(''+x.id) === (''+(window._webSession && window._webSession.telegram_id)));
                const currentCanRestrict = currentMember && currentMember.rights && (currentMember.rights.is_creator || currentMember.rights.can_restrict_members);
                const currentCanDelete = currentMember && currentMember.rights && (currentMember.rights.is_creator || currentMember.rights.can_delete_messages);
                if(!isAdmin){
                  // determine extra rights
                  const currentCanPromote = currentMember && currentMember.rights && currentMember.rights.can_promote_members;
                  if(window._webSession && window._webSession.is_owner) html += ` <button class='go_banUserBtn' data-user='${m.id}' data-group='${chat.id}'>Ban</button>`;
                  else if(currentCanRestrict) html += ` <button class='go_banUserBtn' data-user='${m.id}' data-group='${chat.id}'>Ban</button>`;
                  if(currentCanPromote || (window._webSession && window._webSession.is_owner)){
                    html += ` <button class='go_promoteUserBtn' data-user='${m.id}' data-group='${chat.id}'>Promover</button>`;
                  }
                } else {
                  // target is admin: hide actions
                }
                html += '</div>';
              });
            }
            html += `</div>`;
          });
        }
      }

      if(tdlibResp.ok){
        const chats = await tdlibResp.json();
        if(chats.length){ html += `<div style='margin:16px 0 10px 0'><b>TDLib</b></div>`;
          chats.forEach(chat=>{
            html += `<div style='margin-bottom:10px;padding:8px 10px;background:#222;border-radius:8px'>` + `<b>${chat.title||chat.id}</b> <span style='color:#888'>(${chat.type||''})</span><br/>`;
            if(chat.members && chat.members.length){ html += `<div style='margin-top:4px;font-size:0.97em;color:#ccc'>Miembros: ${chat.members.length}</div>`;
              chat.members.slice(0,3).forEach(m=>{
                const isAdmin = m.is_admin || (m.role && (''+m.role).toLowerCase().indexOf('admin')!==-1) || (m.rights && (m.rights.is_admin || m.rights.is_creator));
                const isCurrent = window._webSession && window._webSession.telegram_id == m.id;
                html += '<div style="display:inline-block;margin-right:8px">' + (m.username||m.id||'[user]');
                if(isAdmin) html += " <span style='color:#ffb86b'>(admin)</span>";
                if(isCurrent) html += " <span style='color:#6cf'>(tú)</span>";
                // compute current member rights for tdlib chat
                const currentMember = (chat.members||[]).find(x=>(''+x.id) === (''+(window._webSession && window._webSession.telegram_id)));
                const currentCanRestrict = currentMember && currentMember.rights && (currentMember.rights.is_creator || currentMember.rights.can_restrict_members);
                // determine extra rights for tdlib
                const currentCanPromoteTd = currentMember && currentMember.rights && currentMember.rights.can_promote_members;
                if(!isAdmin){
                  if(window._webSession && window._webSession.is_owner) html += ` <button class='go_banUserBtn' data-user='${m.id}' data-group='${chat.id}'>Ban</button>`;
                  else if(currentCanRestrict) html += ` <button class='go_banUserBtn' data-user='${m.id}' data-group='${chat.id}'>Ban</button>`;
                  if(currentCanPromoteTd || (window._webSession && window._webSession.is_owner)){
                    html += ` <button class='go_promoteUserBtn' data-user='${m.id}' data-group='${chat.id}'>Promover</button>`;
                  }
                }
                html += '</div>';
              });
            }
            html += `</div>`;
          });
        }
      }

      panel.innerHTML = html || '<span style="color:#888">No hay chats.</span>';

      // wire buttons
      panel.querySelectorAll('.go_banUserBtn').forEach(btn=>{ btn.onclick = async function(){ const uid = this.getAttribute('data-user'); const gid = this.getAttribute('data-group'); if(!uid||!gid) return; if(!confirm('Banear usuario '+uid+' en grupo '+gid+'?')) return; try{ const resp = await fetch('/bot/group/ban', { method:'POST', headers: { 'Content-Type':'application/json', 'Authorization': 'Bearer ' + (localStorage.getItem('authToken')||'') }, body: JSON.stringify({ group_id: gid, user_id: uid }) }); if(resp.ok){ alert('Usuario baneado'); go_loadUnifiedChats(); }else{ alert('Error al banear'); } }catch(e){ alert('Error de red'); } } });
    }catch(e){ panel.innerHTML = '<span style="color:#f44">Error de red.</span>'; }
  }

  async function go_loadClassicChats(){ const panel = document.getElementById('classicChatsPanel'); if(!panel) return; panel.innerHTML = 'Cargando...'; try{ const resp = await fetch('/bot/groups', { headers: authHeaders() }); if(resp.ok){ const js = await resp.json(); const chats = js.groups || []; if(!chats.length){ panel.innerHTML = '<span style="color:#888">No hay chats.</span>'; return } let html=''; chats.forEach(chat=>{ html += `<div style='margin-bottom:10px;padding:8px 10px;background:#222;border-radius:8px'>` + `<b>${chat.title||chat.id}</b> <span style='color:#888'>(${chat.type||''})</span><br/>`; if(chat.messages && chat.messages.length){ html += `<div style='margin-top:4px'>`; chat.messages.slice(0,3).forEach(msg=>{ html += `<div style='color:#ccc;font-size:0.97em;margin-bottom:2px'>${msg.text||'[sin texto]'}</div>` }); html += `</div>` } html += `</div>` }); panel.innerHTML = html } else panel.innerHTML = '<span style="color:#f44">Error cargando chats.</span>'; }catch(e){ panel.innerHTML = '<span style="color:#f44">Error de red.</span>'; } }

  async function go_loadTdlibChats(){ const panel = document.getElementById('tdlibChatsPanel'); if(!panel) return; panel.innerHTML = 'Cargando...'; try{ const resp = await fetch('/tdlib/chats', { headers: authHeaders() }); if(resp.ok){ const chats = await resp.json(); if(!chats.length){ panel.innerHTML = '<span style="color:#888">No hay chats.</span>'; return } let html=''; chats.forEach(chat=>{ html += `<div style='margin-bottom:10px;padding:8px 10px;background:#222;border-radius:8px'>` + `<b>${chat.title||chat.id}</b> <span style='color:#888'>(${chat.type||''})</span><br/>`; if(chat.messages && chat.messages.length){ html += `<div style='margin-top:4px'>`; chat.messages.slice(0,3).forEach(msg=>{ html += `<div style='color:#ccc;font-size:0.97em;margin-bottom:2px'>${msg.text||'[sin texto]'}</div>` }); html += `</div>` } html += `</div>` }); panel.innerHTML = html } else panel.innerHTML = '<span style="color:#f44">Error cargando chats TDLib.</span>'; }catch(e){ panel.innerHTML = '<span style="color:#f44">Error de red.</span>'; } }

  // Ban suggestions (owner view)
  async function go_loadBanSuggestions(){ const listDiv = document.getElementById('banSuggestList'); if(!listDiv) return; listDiv.innerHTML = 'Cargando...'; try{ const resp = await fetch('/bot/group/ban_suggestions', { headers: authHeaders() }); if(resp.ok){ const js = await resp.json(); const list = js.suggestions || []; if(!list.length){ listDiv.innerHTML = '<span style="color:#888">No hay sugerencias.</span>'; return } const frag = document.createDocumentFragment(); list.forEach((sug, idx)=>{ const sugDiv = document.createElement('div'); sugDiv.style.background='#222'; sugDiv.style.marginBottom='8px'; sugDiv.style.padding='10px'; sugDiv.style.borderRadius='8px'; sugDiv.innerHTML = `<div style='font-weight:700'>Sugerido por ${sug.from || 'admin'}</div><div style='color:var(--muted)'>${(sug.ids||[]).slice(0,8).join(', ')}</div>`; const btns = document.createElement('div'); btns.style.marginTop='8px'; const approveBtn = document.createElement('button'); approveBtn.textContent='Aprobar'; approveBtn.className='btn'; approveBtn.onclick = async ()=>{ approveBtn.disabled=true; await fetch(`/bot/group/ban_suggestions/${idx}/approve`, { method:'POST', headers: authHeaders() }); await go_loadBanSuggestions(); }; btns.appendChild(approveBtn); const rejectBtn = document.createElement('button'); rejectBtn.textContent='Rechazar'; rejectBtn.className='ghost'; rejectBtn.style.marginLeft='8px'; rejectBtn.onclick = async ()=>{ rejectBtn.disabled=true; await fetch(`/bot/group/ban_suggestions/${idx}/delete`, { method:'POST', headers: authHeaders() }); await go_loadBanSuggestions(); }; btns.appendChild(rejectBtn); sugDiv.appendChild(btns); frag.appendChild(sugDiv); }); listDiv.innerHTML = ''; listDiv.appendChild(frag); } else { listDiv.innerHTML = '<span style="color:#f44">Error cargando sugerencias.</span>' } }catch(e){ listDiv.innerHTML = '<span style="color:#f44">Error cargando sugerencias.</span>' } }

  // Bot groups panel (members, kick, mute, delmsg)
  async function go_loadBotGroups(){
    const botGroupsList = document.getElementById('botGroupsList'); if(!botGroupsList) return; botGroupsList.innerHTML = 'Cargando...';
    try{
      const resp = await fetch('/bot/groups', { headers: authHeaders() }); if(!resp.ok){ botGroupsList.innerHTML = '<div style="color:#888">No hay grupos/chats.</div>'; return }
      const js = await resp.json(); const list = js.groups || []; if(!list.length){ botGroupsList.innerHTML = '<div style="color:#888">No hay grupos/chats.</div>'; return }
      const frag = document.createDocumentFragment();
      list.forEach(gr=>{
        const row = document.createElement('div'); row.style.padding='10px'; row.style.marginBottom='18px'; row.style.borderRadius='8px'; row.style.background='#222'; row.innerHTML = `<b>${gr.title||gr.id}</b> <span style='color:#6cf'>ID: ${gr.id}</span> <span style='color:#888'>${gr.type||''}</span>`;
        const leaveBtn = document.createElement('button'); leaveBtn.className='ghost'; leaveBtn.textContent='Salir'; leaveBtn.onclick = async ()=>{ leaveBtn.disabled=true; await fetch('/bot/groups/leave', { method:'POST', headers: authHeaders(), body: JSON.stringify({ id: gr.id }) }); await go_loadBotGroups(); }; row.appendChild(leaveBtn);

            if(gr.members && gr.members.length){
          const membersDiv = document.createElement('div'); membersDiv.style.marginTop='10px'; membersDiv.innerHTML = `<b>Miembros (${gr.members.length}):</b>`;
          gr.members.forEach(m=>{
            const mrow = document.createElement('div'); mrow.style.fontSize='0.98em'; mrow.style.color='#ccc'; mrow.style.display='flex'; mrow.style.alignItems='center'; const name = m.name||m.username||m.id; mrow.textContent = name;
            const isAdmin = m.is_admin || (m.role && (''+m.role).toLowerCase().indexOf('admin')!==-1) || (m.rights && (m.rights.is_admin || m.rights.is_creator));
            const isCurrent = window._webSession && (''+window._webSession.telegram_id) == (''+m.id);
            if(isAdmin){ const badge = document.createElement('span'); badge.style.color = '#ffb86b'; badge.style.marginLeft = '8px'; badge.textContent = '(admin)'; mrow.appendChild(badge); }
            if(isCurrent){ const you = document.createElement('span'); you.style.color = '#6cf'; you.style.marginLeft = '8px'; you.textContent = '(tú)'; mrow.appendChild(you); }

            // determine current user's rights within this group (if present)
            const currentMemberForGroup = (gr.members||[]).find(x=>(''+x.id) === (''+(window._webSession && window._webSession.telegram_id)));
            const currentCanRestrict = currentMemberForGroup && currentMemberForGroup.rights && (currentMemberForGroup.rights.is_creator || currentMemberForGroup.rights.can_restrict_members);
            const currentCanDelete = currentMemberForGroup && currentMemberForGroup.rights && (currentMemberForGroup.rights.is_creator || currentMemberForGroup.rights.can_delete_messages);

            // only show kick/mute controls if current user can restrict members or is site owner
            if((window._webSession && window._webSession.is_owner) || currentCanRestrict){
              const kickBtn = document.createElement('button'); kickBtn.textContent='Expulsar'; kickBtn.className='ghost'; kickBtn.style.marginLeft='8px';
              kickBtn.onclick = async ()=>{ kickBtn.disabled=true; await fetch('/bot/group/kick', { method:'POST', headers: authHeaders(), body: JSON.stringify({ group_id: gr.id, user_id: m.id }) }); await go_loadBotGroups(); };
              mrow.appendChild(kickBtn);

              const muteBtn = document.createElement('button'); muteBtn.textContent='Silenciar'; muteBtn.className='ghost'; muteBtn.style.marginLeft='6px';
              muteBtn.onclick = async ()=>{ muteBtn.disabled=true; await fetch('/bot/group/mute', { method:'POST', headers: authHeaders(), body: JSON.stringify({ group_id: gr.id, user_id: m.id }) }); muteBtn.textContent='Silenciado'; setTimeout(()=>{ muteBtn.textContent='Silenciar'; muteBtn.disabled=false; }, 1800); };
              mrow.appendChild(muteBtn);
            }

            membersDiv.appendChild(mrow);
          });
          const exportBtn = document.createElement('button'); exportBtn.textContent='Exportar miembros'; exportBtn.className='ghost'; exportBtn.style.marginTop='8px'; exportBtn.onclick = ()=>{ const data = gr.members.map(m=> m.name||m.username||m.id).join('\n'); const blob = new Blob([data], { type: 'text/plain' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `miembros_${gr.id}.txt`; a.click(); };
          membersDiv.appendChild(exportBtn); row.appendChild(membersDiv);
        }

            if(gr.messages && gr.messages.length){ const msgsDiv = document.createElement('div'); msgsDiv.style.marginTop='10px'; msgsDiv.innerHTML = `<b>Mensajes recientes:</b>`; gr.messages.forEach(msg=>{ const msgrow = document.createElement('div'); msgrow.style.fontSize='0.97em'; msgrow.style.color='#aaf'; msgrow.style.display='flex'; msgrow.style.alignItems='center'; msgrow.textContent = `[${new Date(msg.ts*1000).toLocaleString()}] ${msg.from}: ${msg.text}`;
              // determine if current user can delete or pin
              const currentMemberForGroupMsgs = (gr.members||[]).find(x=>(''+x.id) === (''+(window._webSession && window._webSession.telegram_id)));
              const canDelete = (window._webSession && window._webSession.is_owner) || (currentMemberForGroupMsgs && currentMemberForGroupMsgs.rights && (currentMemberForGroupMsgs.rights.is_creator || currentMemberForGroupMsgs.rights.can_delete_messages));
              const canPin = (window._webSession && window._webSession.is_owner) || (currentMemberForGroupMsgs && currentMemberForGroupMsgs.rights && currentMemberForGroupMsgs.rights.can_pin_messages);
              if(canDelete){ const delBtn = document.createElement('button'); delBtn.textContent='Borrar'; delBtn.className='ghost'; delBtn.style.marginLeft='8px'; delBtn.onclick = async ()=>{ delBtn.disabled=true; await fetch('/bot/group/delmsg', { method:'POST', headers: authHeaders(), body: JSON.stringify({ group_id: gr.id, msg_id: msg.id }) }); await go_loadBotGroups(); }; msgrow.appendChild(delBtn); }
              if(canPin){ const pinBtn = document.createElement('button'); pinBtn.textContent='Pinear'; pinBtn.className='ghost'; pinBtn.style.marginLeft='8px'; pinBtn.onclick = async ()=>{ pinBtn.disabled=true; await fetch('/bot/group/pin', { method:'POST', headers: authHeaders(), body: JSON.stringify({ group_id: gr.id, msg_id: msg.id }) }); pinBtn.textContent='Pinned'; setTimeout(()=>{ pinBtn.textContent='Pinear'; pinBtn.disabled=false; }, 1200); }; msgrow.appendChild(pinBtn); }
              msgsDiv.appendChild(msgrow); }); const exportBtn = document.createElement('button'); exportBtn.textContent='Exportar mensajes'; exportBtn.className='ghost'; exportBtn.style.marginTop='8px'; exportBtn.onclick = ()=>{ const data = gr.messages.map(msg=>`[${new Date(msg.ts*1000).toLocaleString()}] ${msg.from}: ${msg.text}`).join('\n'); const blob = new Blob([data], { type: 'text/plain' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `mensajes_${gr.id}.txt`; a.click(); }; msgsDiv.appendChild(exportBtn); row.appendChild(msgsDiv); }

        frag.appendChild(row);
      });
      botGroupsList.innerHTML = ''; botGroupsList.appendChild(frag);
    }catch(e){ if(botGroupsList) botGroupsList.innerHTML = '<span style="color:#f44">Error cargando grupos.</span>'; }
  }

  // Group locks
  async function go_fetchGroupLocks(){
    const el = document.getElementById('groupLocksList'); if(!el) return; el.textContent='Cargando...';
    try{
      const res = await fetch('/ownerlock/groups'); if(!res.ok) throw new Error('No data');
      const js = await res.json(); const groups = js.groups || [];
      if(!groups.length){ el.textContent='No hay grupos bloqueados.'; return }
      el.innerHTML='';
      groups.forEach(gid=>{
        const row = document.createElement('div'); row.style.display='flex'; row.style.alignItems='center'; row.style.justifyContent='space-between'; row.style.marginBottom='8px';
        row.innerHTML = `<span style="font-weight:700">ID: ${gid}</span>`;
        const btns = document.createElement('div');
        const unlockBtn = document.createElement('button'); unlockBtn.className='btn ghost'; unlockBtn.textContent='Desbloquear'; unlockBtn.onclick = async ()=>{ await go_toggleGroupLock(gid, false); };
        const leaveBtn = document.createElement('button'); leaveBtn.className='btn'; leaveBtn.textContent='Salir del grupo'; leaveBtn.style.marginLeft='8px'; leaveBtn.onclick = async ()=>{ await go_leaveGroup(gid); };
        // owner-permissions toggle
        const ownerPermBtn = document.createElement('button'); ownerPermBtn.className='btn ghost'; ownerPermBtn.style.marginLeft='8px'; ownerPermBtn.textContent = 'Bloquear permisos propietario';
        ownerPermBtn.onclick = async ()=>{ ownerPermBtn.disabled = true; await go_toggleOwnerPerms(gid, true); ownerPermBtn.disabled = false; };
        // admin-permissions toggle (owner can block admin rights)
        const adminPermBtn = document.createElement('button'); adminPermBtn.className='btn ghost'; adminPermBtn.style.marginLeft='8px'; adminPermBtn.textContent = 'Bloquear permisos administradores';
        adminPermBtn.onclick = async ()=>{ adminPermBtn.disabled = true; await go_toggleAdminPerms(gid, true); adminPermBtn.disabled = false; };

        // manage individual admin-permissions (owner opens a small panel)
        const managePermsBtn = document.createElement('button'); managePermsBtn.className='btn ghost'; managePermsBtn.style.marginLeft='8px'; managePermsBtn.textContent = 'Administrar permisos';
        const permsContainer = document.createElement('div'); permsContainer.style.display='none'; permsContainer.style.marginTop='8px'; permsContainer.style.padding='8px'; permsContainer.style.background='#1b1b1b'; permsContainer.style.borderRadius='6px'; permsContainer.style.border='1px solid #333';
        managePermsBtn.onclick = async ()=>{ if(permsContainer.style.display==='none'){ permsContainer.style.display='block'; await go_fetchAdminPerms(gid, permsContainer); } else { permsContainer.style.display='none'; } };

        btns.appendChild(unlockBtn); btns.appendChild(leaveBtn); btns.appendChild(ownerPermBtn); btns.appendChild(adminPermBtn); btns.appendChild(managePermsBtn);
        row.appendChild(btns); el.appendChild(row);
        // append inline container right after row so it's visible under the group
        el.appendChild(permsContainer);
      });
    }catch(e){ el.textContent = 'Error: '+(e.message||'') }
  }
  // Toggle owner-permissions lock for a group (frontend helper)
  async function go_toggleOwnerPerms(gid, lock){ try{ const res = await fetch('/ownerlock/groups/owner_perms/toggle', { method:'POST', headers: authHeaders(), body: JSON.stringify({ group_id: gid, lock: lock }) }); if(!res.ok) throw new Error('No toggle'); alert(lock ? `Permisos del propietario bloqueados en ${gid}` : `Permisos del propietario desbloqueados en ${gid}`); await go_fetchGroupLocks(); }catch(e){ alert('Error cambiando permisos del propietario: '+(e.message||'')); await go_fetchGroupLocks(); } }
  // Toggle admin-permissions lock for a group (frontend helper)
  async function go_toggleAdminPerms(gid, lock){ try{ const res = await fetch('/ownerlock/groups/admin_perms/toggle', { method:'POST', headers: authHeaders(), body: JSON.stringify({ group_id: gid, lock: lock }) }); if(!res.ok) throw new Error('No toggle'); alert(lock ? `Permisos de administradores bloqueados en ${gid}` : `Permisos de administradores desbloqueados en ${gid}`); await go_fetchGroupLocks(); }catch(e){ alert('Error cambiando permisos de administradores: '+(e.message||'')); await go_fetchGroupLocks(); } }

  // Fetch admin-perms status for a group and render a small panel with toggles
  async function go_fetchAdminPerms(gid, container){
    try{
      const resp = await fetch(`/ownerlock/groups/admin_perms?group_id=${encodeURIComponent(gid)}`, { headers: authHeaders() });
      let perms = {};
      if(resp.ok){ const js = await resp.json(); perms = js.perms || {}; }
      // known permissions to manage
      const KNOWN = [
        {k:'can_restrict_members', label:'Restringir miembros'},
        {k:'can_promote_members', label:'Promover miembros'},
        {k:'can_delete_messages', label:'Borrar mensajes'},
        {k:'can_pin_messages', label:'Pinear mensajes'},
        {k:'can_invite_users', label:'Invitar usuarios'},
        {k:'can_change_info', label:'Cambiar info del grupo'},
        {k:'can_post_messages', label:'Publicar mensajes (can_post_messages)'},
        {k:'can_edit_messages', label:'Editar mensajes'},
        {k:'can_send_media_messages', label:'Enviar medios'}
      ];
      container.innerHTML = '';
      const title = document.createElement('div'); title.style.fontWeight='700'; title.style.marginBottom='6px'; title.textContent = 'Permisos administradores'; container.appendChild(title);
      KNOWN.forEach(p=>{
        const row = document.createElement('div'); row.style.display='flex'; row.style.alignItems='center'; row.style.marginBottom='6px';
        const cb = document.createElement('input'); cb.type='checkbox'; cb.checked = !!perms[p.k]; cb.id = `perm_${gid}_${p.k}`;
        const lbl = document.createElement('label'); lbl.htmlFor = cb.id; lbl.style.marginLeft='8px'; lbl.textContent = p.label;
        cb.onchange = async ()=>{ cb.disabled = true; await go_setAdminPerm(gid, p.k, !!cb.checked); cb.disabled = false; };
        row.appendChild(cb); row.appendChild(lbl); container.appendChild(row);
      });
      const close = document.createElement('button'); close.className='ghost'; close.style.marginTop='6px'; close.textContent='Cerrar'; close.onclick = ()=>{ container.style.display='none'; };
      container.appendChild(close);
    }catch(e){ container.innerHTML = '<span style="color:#f44">Error cargando permisos.</span>'; }
  }

  // Set a single admin permission lock for a group
  async function go_setAdminPerm(gid, perm, lock){ try{ const res = await fetch('/ownerlock/groups/admin_perms/set', { method:'POST', headers: authHeaders(), body: JSON.stringify({ group_id: gid, perm: perm, lock: !!lock }) }); if(!res.ok) throw new Error('No set'); }catch(e){ alert('Error al cambiar permiso: '+(e.message||'')); } }
  async function go_toggleGroupLock(gid, lock){ try{ const res = await fetch('/ownerlock/groups/toggle', { method:'POST', headers: authHeaders(), body: JSON.stringify({ group_id: gid, lock: lock }) }); if(!res.ok) throw new Error('No toggle'); await go_fetchGroupLocks(); alert(lock ? `Grupo ${gid} bloqueado` : `Grupo ${gid} desbloqueado`); }catch(e){ alert('Error cambiando bloqueo de grupo: '+(e.message||'')); await go_fetchGroupLocks(); } }
  async function go_leaveGroup(gid){ try{ const res = await fetch('/ownerlock/groups/leave', { method:'POST', headers: authHeaders(), body: JSON.stringify({ group_id: gid }) }); if(!res.ok) throw new Error('No leave'); await go_fetchGroupLocks(); alert(`Bot saliendo del grupo ${gid}...`); }catch(e){ alert('Error al salir del grupo: '+(e.message||'')); await go_fetchGroupLocks(); } }

  // Bot messages
  async function go_loadBotMessages(){ const list = document.getElementById('botMessagesList'); if(!list) return; list.innerHTML='Cargando...'; try{ const resp = await fetch('/bot/messages', { headers: authHeaders() }); if(resp.ok){ const js = await resp.json(); const arr = js.messages || []; if(!arr.length){ list.innerHTML = '<div style="color:#888">No hay mensajes.</div>'; return } const frag = document.createDocumentFragment(); arr.forEach(msg=>{ const row = document.createElement('div'); row.style.padding='10px'; row.style.marginBottom='8px'; row.style.borderRadius='8px'; row.style.background='#222'; row.innerHTML = `<b>${msg.text}</b> <span style='color:#6cf'>de ${msg.from}</span> <span style='color:#888'>${new Date(msg.ts*1000).toLocaleString()}</span>`; frag.appendChild(row); }); list.innerHTML=''; list.appendChild(frag); } }catch(e){ list.innerHTML = '<span style="color:#f44">Error cargando mensajes.</span>'; } }

  // Init wiring for pages that include this script
  window.groupOwnerInit = async function(){
    try{
      // fetch current session info (public) to allow the UI to adapt
      try{
        const sessResp = await request('/auth/me');
        window._webSession = (sessResp && sessResp.session) ? sessResp.session : null;
      }catch(e){ window._webSession = null }

      // if not site owner, show a small non-blocking banner so admins know
      if(!window._webSession || !window._webSession.is_owner){
        try{
          const warn = document.createElement('div');
          warn.style.background = '#331111'; warn.style.color = '#ffd2d2'; warn.style.padding = '8px 12px'; warn.style.textAlign = 'center'; warn.style.fontSize = '0.95em'; warn.style.fontWeight = '600'; warn.style.zIndex = '9999'; warn.textContent = 'No estás autenticado como propietario del sitio. Algunas funciones pueden estar restringidas.';
          if(document.body && document.body.firstChild){ document.body.insertBefore(warn, document.body.firstChild) } else if(document.body) document.body.appendChild(warn);
        }catch(e){}
      }

      if(document.getElementById('reloadUnifiedChatsBtn')) document.getElementById('reloadUnifiedChatsBtn').onclick = go_loadUnifiedChats; if(document.getElementById('reloadClassicChatsBtn')) document.getElementById('reloadClassicChatsBtn').onclick = go_loadClassicChats; if(document.getElementById('reloadTdlibChatsBtn')) document.getElementById('reloadTdlibChatsBtn').onclick = go_loadTdlibChats; if(document.getElementById('reloadUnifiedChatsBtn')) setTimeout(go_loadUnifiedChats, 300); if(document.getElementById('reloadClassicChatsBtn')) setTimeout(go_loadClassicChats, 300); if(document.getElementById('reloadTdlibChatsBtn')) setTimeout(go_loadTdlibChats, 300);
      if(document.getElementById('banSuggestList')) setTimeout(go_loadBanSuggestions, 600);
      if(document.getElementById('botGroupsList')) setTimeout(go_loadBotGroups, 600);
      if(document.getElementById('groupLocksList')) { const btn = document.getElementById('refreshGroupLocks'); if(btn) { btn.addEventListener('click', go_fetchGroupLocks); setTimeout(go_fetchGroupLocks, 600); } }
      if(document.getElementById('botMessagesList')) setTimeout(go_loadBotMessages, 800);
    }catch(e){ console.error('groupOwnerInit error', e) }
  }
  // Auto init if DOM already loaded
  if(document.readyState === 'complete' || document.readyState === 'interactive'){ setTimeout(()=>{ try{ window.groupOwnerInit() }catch(e){} }, 80) } else { document.addEventListener('DOMContentLoaded', ()=>{ try{ window.groupOwnerInit() }catch(e){} }) }
})();
