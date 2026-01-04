// Mostrar sección de creación de admin solo a owner
function showAdminCreate() {
  if (window._isOwner) {
    document.getElementById('adminCreate').style.display = '';
  }
}
document.addEventListener('DOMContentLoaded', showAdminCreate);

document.getElementById('adminCreateBtn').addEventListener('click', async () => {
  const user = document.getElementById('adminUserInput').value.trim();
  const pass = document.getElementById('adminPassInput').value;
  const msg = document.getElementById('adminCreateMsg');
  msg.textContent = '';
  if (!user || !pass) {
    msg.textContent = 'Usuario y contraseña requeridos';
    msg.style.color = '#c33';
    return;
  }
  try {
    const resp = await fetch('/admin/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (localStorage.getItem('authToken')||'') },
      body: JSON.stringify({ user, pass })
    });
    if (resp.ok) {
      msg.textContent = 'Administrador creado';
      msg.style.color = '#6c6';
    } else {
      msg.textContent = 'Error: ' + (await resp.text());
      msg.style.color = '#c33';
    }
  } catch (e) {
    msg.textContent = 'Error: ' + e;
    msg.style.color = '#c33';
  }
});
// Mostrar auditoría solo a owner/admin
let _auditLogs = [];
function renderAuditLogs(logs) {
  if (!logs.length) {
    document.getElementById('auditList').textContent = 'Sin acciones registradas.';
    return;
  }
  document.getElementById('auditList').innerHTML = logs.map(l => {
    let extra = '';
    if (l.action === 'ACCESS') {
      extra = `<span style='color:#4af'>${l.path||''}</span>`;
    }
    return `<div style="margin-bottom:6px"><b>${l.action}</b> — <span style="color:#ccc">${l.user||'-'}</span> <span style="color:#888">[${l.ip}]</span> <span style="color:#666">${new Date(l.ts*1000).toLocaleString()}</span> ${extra}</div>`;
  }).join('');
}
}

async function showOwnerAudit() {
  if (!window._isOwner) return;
  document.getElementById('ownerAudit').style.display = '';
  try {
    const resp = await fetch('/audit/lang_actions', { headers: { 'Authorization': 'Bearer ' + (localStorage.getItem('authToken')||'') } });
    if (!resp.ok) {
      document.getElementById('auditList').textContent = 'No autorizado o sin datos.';
      return;
    }
    _auditLogs = await resp.json();
    renderAuditLogs(_auditLogs);
  } catch (e) {
    document.getElementById('auditList').textContent = 'Error al cargar auditoría: ' + e;
  }
}

function filterAuditLogs() {
  let logs = _auditLogs;
  const user = document.getElementById('auditUserFilter').value.trim().toLowerCase();
  const ip = document.getElementById('auditIpFilter').value.trim();
  const action = document.getElementById('auditActionFilter').value;
  const path = document.getElementById('auditPathFilter').value.trim().toLowerCase();
  if (user) logs = logs.filter(l => (l.user||'').toLowerCase().includes(user));
  if (ip) logs = logs.filter(l => (l.ip||'').includes(ip));
  if (action) logs = logs.filter(l => l.action === action);
  if (path) logs = logs.filter(l => (l.path||'').toLowerCase().includes(path));
  renderAuditLogs(logs);
}
document.getElementById('auditFilterBtn').addEventListener('click', filterAuditLogs);
document.getElementById('auditClearBtn').addEventListener('click', () => {
  document.getElementById('auditUserFilter').value = '';
  document.getElementById('auditIpFilter').value = '';
  document.getElementById('auditActionFilter').value = '';
  renderAuditLogs(_auditLogs);
});
document.addEventListener('DOMContentLoaded', showOwnerAudit);
// Crear nuevo idioma desde la web
document.getElementById('createLangBtn').addEventListener('click', async () => {
  const code = document.getElementById('newLangInput').value.trim().toLowerCase();
  const scope = document.getElementById('newScopeInput').value;
  const msg = document.getElementById('createLangMsg');
  msg.textContent = '';
  if (!code.match(/^[a-z]{2,5}$/)) {
    msg.textContent = 'Código inválido';
    msg.style.color = '#c33';
    return;
  }
  try {
    const resp = await fetch('/translations/create_lang', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang: code, scope })
    });
    if (resp.ok) {
      msg.textContent = 'Idioma creado';
      msg.style.color = '#6c6';
    } else {
      msg.textContent = 'Error: ' + (await resp.text());
      msg.style.color = '#c33';
    }
  } catch (e) {
    msg.textContent = 'Error: ' + e;
    msg.style.color = '#c33';
  }
});

async function loadLang(code, scope = 'bot') {
  const res = await fetch(`i18n/${scope}/${code}.json`);
  if (!res.ok) {
    return null;
  }
  return await res.json();
}

// Cargar idiomas disponibles para web y bot
async function loadAvailableLangs() {
  const scopes = ['web', 'bot'];
  for (const scope of scopes) {
    const sel = document.getElementById(scope === 'web' ? 'langSelectWeb' : 'langSelectBot');
    sel.innerHTML = '';
    try {
      const resp = await fetch(`i18n/${scope}/en.json`);
      if (!resp.ok) continue;
      const files = await fetch(`/i18n/list/${scope}`).then(r => r.ok ? r.json() : []);
      for (const code of files) {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = code;
        sel.appendChild(opt);
      }
    } catch {}
  }
}

// Inicializar los selects al cargar
document.addEventListener('DOMContentLoaded', loadAvailableLangs);

// Obtener idioma y scope seleccionados
function getSelectedLangScope() {
  const webLang = document.getElementById('langSelectWeb').value;
  const botLang = document.getElementById('langSelectBot').value;
  // Prioridad: si hay selección en web, usar web; si no, bot
  if (document.activeElement && document.activeElement.id === 'langSelectWeb') {
    return { code: webLang, scope: 'web' };
  }
  return { code: botLang, scope: 'bot' };
}

function renderTable(base, compare) {
  const list = document.getElementById('list');
  list.innerHTML = '';
  const table = document.createElement('table');
  table.style.width = '100%';
  table.style.borderCollapse = 'collapse';
  const thead = document.createElement('thead');
  const htr = document.createElement('tr');
  ['Key', 'Base (en)', compare ? `Compare (${compare.code})` : 'Translation'].forEach(h => {
    const th = document.createElement('th');
    th.textContent = h;
    th.style.textAlign = 'left';
    th.style.padding = '6px';
    htr.appendChild(th);
  });
  thead.appendChild(htr);
  table.appendChild(thead);

  const keys = Object.keys(base);
  for (const k of keys) {
    const tr = document.createElement('tr');
    const tdk = document.createElement('td');
    tdk.textContent = k;
    tdk.style.border = '1px solid rgba(255,255,255,0.04)';
    tdk.style.padding = '6px';

    const tbe = document.createElement('td');
    tbe.textContent = base[k] || '';
    tbe.style.border = '1px solid rgba(255,255,255,0.04)';
    tbe.style.padding = '6px';

    const tcmp = document.createElement('td');
    tcmp.textContent = (compare && compare.data && compare.data[k]) ? compare.data[k] : '';
    tcmp.style.border = '1px solid rgba(255,255,255,0.04)';
    tcmp.style.padding = '6px';

    const tbtn = document.createElement('td');
    tbtn.style.border = '1px solid rgba(255,255,255,0.04)';
    tbtn.style.padding = '6px';
    const btn = document.createElement('button');
    btn.textContent = 'Sugerir';
    btn.addEventListener('click', async () => {
      // Usar selects nuevos
      let lang, scope;
      if (document.activeElement && document.activeElement.id === 'langSelectWeb') {
        lang = document.getElementById('langSelectWeb').value;
        scope = 'web';
      } else {
        lang = document.getElementById('langSelectBot').value;
        scope = 'bot';
      }
      const value = tcmp.textContent || '';
      let author = localStorage.getItem('api_user') || localStorage.getItem('authUser');
      if (!author) {
        author = prompt('Introduce tu nombre de usuario para sugerir traducción:');
        if (author) localStorage.setItem('api_user', author);
      }
      const body = { lang, key: k, value, author, scope };
      try {
        const resp = await fetch('/translations/suggest', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
        });
        if (resp.ok) {
          const j = await resp.json();
          alert('Sugerencia enviada (id: ' + j.id + ')');
        } else {
          const t = await resp.text();
          alert('Error: ' + t);
        }
      } catch (e) {
        alert('No se pudo enviar la sugerencia: ' + e);
      }
    });
    tbtn.appendChild(btn);

    tr.appendChild(tdk);
    tr.appendChild(tbe);
    tr.appendChild(tcmp);
    tr.appendChild(tbtn);
    table.appendChild(tr);
  }
  list.appendChild(table);
}


// Cargar traducciones según el select activo
document.getElementById('loadBtn').addEventListener('click', async () => {
  const webLang = document.getElementById('langSelectWeb').value;
  const botLang = document.getElementById('langSelectBot').value;
  let code, scope;
  if (document.activeElement && document.activeElement.id === 'langSelectWeb') {
    code = webLang; scope = 'web';
  } else {
    code = botLang; scope = 'bot';
  }
  const base = await loadLang('en', scope);
  if (!base) {
    document.getElementById('list').textContent = 'No se encontró el archivo base (en.json).';
    return;
  }
  const data = await loadLang(code, scope);
  renderTable(base, data ? { code, data } : null);
});

document.getElementById('downloadBtn').addEventListener('click', async () => {
  const code = document.getElementById('langSelect').value;
  const res = await fetch(`i18n/${code}.json`);
  if (!res.ok) return alert('No se encontró el archivo.');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${code}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

// On load show all base strings
document.addEventListener('DOMContentLoaded', async () => {
  const scope = document.getElementById('scopeSelect') ? document.getElementById('scopeSelect').value : 'bot';
  const base = await loadLang('en', scope);
  if (!base) {
    document.getElementById('list').textContent = 'No se encontró el archivo base (en.json).';
    return;
  }
  renderTable(base, null);
});

// Edit mode and export
document.getElementById('editToggle').addEventListener('change', (e) => {
  const editable = e.target.checked;
  // make translation column editable
  const rows = document.querySelectorAll('#list table tr');
  rows.forEach((tr, idx) => {
    // skip header
    if (idx === 0) return;
    const tds = tr.querySelectorAll('td');
    if (tds.length >= 3) {
      const cell = tds[2];
      cell.contentEditable = editable;
      cell.style.background = editable ? 'rgba(255,255,255,0.02)' : '';
    }
  });
});

document.getElementById('exportBtn').addEventListener('click', () => {
  const table = document.querySelector('#list table');
  if (!table) return alert('No hay datos para exportar');
  const rows = table.querySelectorAll('tr');
  // header row is first
  const data = {};
  for (let i = 1; i < rows.length; i++) {
    const cols = rows[i].querySelectorAll('td');
    if (cols.length >= 3) {
      const key = cols[0].textContent.trim();
      const val = cols[2].textContent.trim();
      data[key] = val;
    }
  }
  const code = document.getElementById('langSelect').value;
  const scope = document.getElementById('scopeSelect') ? document.getElementById('scopeSelect').value : 'bot';
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${scope}_${code}_edited.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});


async function fetchSuggestions() {
  try {
    const resp = await fetch('/translations/suggestions');
    if (!resp.ok) {
      document.getElementById('suggestionsTable').textContent = 'No autorizado o no disponible.';
      return;
    }
    const data = await resp.json();
    renderSuggestions(data);
  } catch (e) {
    document.getElementById('suggestionsTable').textContent = 'Error al obtener sugerencias: ' + e;
  }
}

function renderSuggestions(items) {
  const container = document.getElementById('suggestionsTable');
  container.innerHTML = '';
  if (!items || !items.length) {
    container.textContent = 'No hay sugerencias pendientes.';
    return;
  }
  const table = document.createElement('table');
  table.style.width = '100%';
  // Cabecera
  const thead = document.createElement('thead');
  const htr = document.createElement('tr');
  ['Clave', 'Valor', 'Autor', 'Estado', 'Aprobado por', 'Acción'].forEach(h => {
    const th = document.createElement('th');
    th.textContent = h;
    th.style.padding = '6px';
    htr.appendChild(th);
  });
  thead.appendChild(htr);
  table.appendChild(thead);
  // Determinar si el usuario es owner/admin
  let isOwner = false;
  if (typeof window.checkOwner === 'function') {
    // checkOwner es async, pero para render rápido usamos un flag global si existe
    isOwner = window._isOwner === true;
  }
  items.forEach(it => {
    const tr = document.createElement('tr');
    const k = document.createElement('td'); k.textContent = it.key; k.style.padding='6px';
    const v = document.createElement('td'); v.textContent = it.value; v.style.padding='6px';
    const author = document.createElement('td'); author.textContent = it.author || '-'; author.style.padding='6px';
    const status = document.createElement('td'); status.textContent = it.status || '-'; status.style.padding='6px';
    const approver = document.createElement('td');
    if (it.applied_by && it.applied_by.username) {
      approver.textContent = it.applied_by.username;
    } else if (it.applied_by && it.applied_by.api_key) {
      approver.textContent = 'API';
    } else {
      approver.textContent = '-';
    }
    approver.style.padding='6px';
    const a = document.createElement('td');
    if (it.status === 'pending' && isOwner) {
      const apply = document.createElement('button'); apply.textContent = 'Aplicar';
      apply.addEventListener('click', async () => {
        try {
          // include scope when applying
          const scope = document.getElementById('scopeSelect') ? document.getElementById('scopeSelect').value : 'bot';
          const resp = await fetch('/translations/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: it.id, scope }) });
          if (resp.ok) {
            alert('Sugerencia aplicada');
            fetchSuggestions();
          } else {
            alert('Error al aplicar: ' + await resp.text());
          }
        } catch (e) { alert('Error: ' + e); }
      });
      a.appendChild(apply);
    } else {
      a.textContent = '-';
    }
    tr.appendChild(k); tr.appendChild(v); tr.appendChild(author); tr.appendChild(status); tr.appendChild(approver); tr.appendChild(a);
    table.appendChild(tr);
  });
  container.appendChild(table);
}

document.getElementById('refreshSuggestions').addEventListener('click', fetchSuggestions);

