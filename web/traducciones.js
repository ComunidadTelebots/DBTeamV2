async function loadLang(code) {
  const res = await fetch(`i18n/${code}.json`);
  if (!res.ok) {
    return null;
  }
  return await res.json();
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
      const lang = document.getElementById('langSelect').value;
      const value = tcmp.textContent || '';
      const body = { lang, key: k, value };
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

document.getElementById('loadBtn').addEventListener('click', async () => {
  const code = document.getElementById('langSelect').value;
  const base = await loadLang('en');
  if (!base) {
    document.getElementById('list').textContent = 'No se encontró el archivo base (en.json).';
    return;
  }
  const data = await loadLang(code);
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
  const base = await loadLang('en');
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
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${code}_edited.json`;
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
  items.forEach(it => {
    const tr = document.createElement('tr');
    const k = document.createElement('td'); k.textContent = it.key; k.style.padding='6px';
    const v = document.createElement('td'); v.textContent = it.value; v.style.padding='6px';
    const a = document.createElement('td');
    const apply = document.createElement('button'); apply.textContent = 'Aplicar';
    apply.addEventListener('click', async () => {
      try {
        const resp = await fetch('/translations/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: it.id }) });
        if (resp.ok) {
          alert('Sugerencia aplicada');
          fetchSuggestions();
        } else {
          alert('Error al aplicar: ' + await resp.text());
        }
      } catch (e) { alert('Error: ' + e); }
    });
    a.appendChild(apply);
    tr.appendChild(k); tr.appendChild(v); tr.appendChild(a);
    table.appendChild(tr);
  });
  container.appendChild(table);
}

document.getElementById('refreshSuggestions').addEventListener('click', fetchSuggestions);

