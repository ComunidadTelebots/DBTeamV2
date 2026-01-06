// Simple gate: if no api_token in localStorage, redirect to login (except login/register pages)
(function(){
  try{
    const page = (location.pathname.split('/').pop() || '').toLowerCase();
    const allow = new Set(['login.html','register.html','']);
    const hasToken = !!localStorage.getItem('api_token');
    if(!hasToken && !allow.has(page)){
      location.replace('login.html');
      return;
    }
  }catch(e){ /* non-fatal */ }
})();

document.addEventListener('DOMContentLoaded',()=>{
  // Insert bot shortcut into header actions (global)
  try {
    const BOT_USERNAME = 'cintiaandrea_bot';
    const headerActions = document.querySelector('.header-actions');
    if (headerActions) {
      const a = document.createElement('a');
      a.href = `https://t.me/${BOT_USERNAME}`;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.className = 'btn';
      a.style.marginRight = '8px';
      a.textContent = 'Abrir bot';
      headerActions.insertBefore(a, headerActions.firstChild);
      // Theme editor button
      const themeBtn = document.createElement('button');
      themeBtn.className = 'btn ghost';
      themeBtn.style.marginRight = '8px';
      themeBtn.id = 'themeEditorBtn';
      themeBtn.textContent = 'Tema';
      headerActions.insertBefore(themeBtn, headerActions.firstChild);

      // Logout button when authenticated
      const hasToken = !!localStorage.getItem('api_token');
      if (hasToken) {
        // hide default login/register links
        headerActions.querySelectorAll('a[href="login.html"],a[href="register.html"]').forEach(el=>{ el.style.display='none'; });
        const logoutBtn = document.createElement('button');
        logoutBtn.className = 'btn ghost';
        logoutBtn.textContent = 'Cerrar sesión';
        logoutBtn.addEventListener('click', () => {
          try { localStorage.removeItem('api_token'); } catch (e) {}
          location.replace('login.html');
        });
        // Insert logout at the end for clarity
        headerActions.appendChild(logoutBtn);
      }
    }
  } catch (e) {
    // non-fatal
  }
  // Ensure header nav has a link to telegram.html
  try {
    const nav = document.querySelector('.main-nav');
    if (nav) {
      const exists = Array.from(nav.querySelectorAll('a')).some(a => a.getAttribute('href') === 'telegram.html');
      if (!exists) {
        const li = document.createElement('a');
        li.href = 'telegram.html';
        li.textContent = 'Telegram';
        nav.appendChild(li);
      }
      const ownerExists = Array.from(nav.querySelectorAll('a')).some(a => a.getAttribute('href') === 'owner.html');
      if (!ownerExists) {
        const li = document.createElement('a');
        li.href = 'owner.html';
        li.textContent = 'Owner';
        nav.appendChild(li);
      }
    }
  } catch (e) {}
  const btns = document.querySelectorAll('.nav-toggle');
  btns.forEach(b=>b.addEventListener('click',()=>{
    const nav = document.querySelector('.main-nav');
    if(!nav) return;
    nav.classList.toggle('open');
  }));
  // auto-hide mobile nav when clicking a link
  document.addEventListener('click',e=>{
    if(e.target.tagName==='A' && e.target.closest('.main-nav')){
      const nav=document.querySelector('.main-nav'); if(nav) nav.classList.remove('open');
    }
  });
  // Make file inputs accept .tdesktop-theme site-wide for theme uploads
  try{
    const fileInputs = document.querySelectorAll('input[type=file]');
    fileInputs.forEach(fi=>{
      try{
        const cur = fi.getAttribute('accept') || '';
        const add = '.tdesktop-theme';
        if(cur.indexOf(add) === -1){
          const sep = cur && cur.trim() !== '' ? ',' : '';
          fi.setAttribute('accept', cur + sep + add);
        }
      }catch(e){}
    })
  }catch(e){}
  // Theme editor modal and logic
  try{
    function loadThemeSettings(){
      const owner = localStorage.getItem('owner_color') || null;
      let users = {};
      try{ users = JSON.parse(localStorage.getItem('user_colors') || '{}') }catch(e){}
      return { owner: owner, users: users }
    }
    function saveThemeSettings(s){ if(s.owner) localStorage.setItem('owner_color', s.owner); localStorage.setItem('user_colors', JSON.stringify(s.users||{})); applyThemeSettings(s) }
    function applyThemeSettings(s){ try{ const owner = (s && s.owner) ? s.owner : (localStorage.getItem('owner_color') || null); if(owner) document.documentElement.style.setProperty('--owner-color', owner); const accent = owner || getComputedStyle(document.documentElement).getPropertyValue('--owner-color'); if(accent) document.documentElement.style.setProperty('--accent', accent); }catch(e){} }
    // create modal
    const themeModalId = 'themeEditorModal'
    function openThemeEditor(){
      if(document.getElementById(themeModalId)) return;
      const cur = loadThemeSettings();
      const modal = document.createElement('div'); modal.id = themeModalId; modal.style.position='fixed'; modal.style.left='0'; modal.style.top='0'; modal.style.right='0'; modal.style.bottom='0'; modal.style.zIndex=12000; modal.style.display='flex'; modal.style.alignItems='center'; modal.style.justifyContent='center'; modal.style.background='rgba(0,0,0,0.5)';
      const box = document.createElement('div'); box.style.background = getComputedStyle(document.documentElement).getPropertyValue('--card') || '#111'; box.style.padding='18px'; box.style.borderRadius='10px'; box.style.minWidth='360px'; box.style.color = getComputedStyle(document.documentElement).getPropertyValue('--text') || '#fff';
      const title = document.createElement('h3'); title.textContent = 'Editor de colores'; title.style.marginTop='0'; box.appendChild(title);
      const ownerLabel = document.createElement('div'); ownerLabel.textContent = 'Color principal (owner):'; ownerLabel.style.marginTop='8px'; box.appendChild(ownerLabel);
      const ownerInput = document.createElement('input'); ownerInput.type='color'; ownerInput.value = cur.owner || '#2563eb'; ownerInput.style.width='56px'; ownerInput.style.height='36px'; ownerInput.style.border='0'; ownerInput.style.marginTop='6px'; box.appendChild(ownerInput);
      const usersLabel = document.createElement('div'); usersLabel.textContent = 'Colores por usuario (JSON: {"username":"#rrggbb"})'; usersLabel.style.marginTop='12px'; box.appendChild(usersLabel);
      const usersArea = document.createElement('textarea'); usersArea.style.width='100%'; usersArea.style.height='120px'; usersArea.style.marginTop='6px'; usersArea.value = JSON.stringify(cur.users||{}, null, 2); box.appendChild(usersArea);
      const actions = document.createElement('div'); actions.style.display='flex'; actions.style.justifyContent='flex-end'; actions.style.gap='8px'; actions.style.marginTop='10px';
      const btnCancel = document.createElement('button'); btnCancel.className='btn ghost'; btnCancel.textContent='Cancelar'; btnCancel.addEventListener('click', ()=> modal.remove());
      const btnReset = document.createElement('button'); btnReset.className='btn ghost'; btnReset.textContent='Restaurar por defecto'; btnReset.addEventListener('click', ()=>{
        // Prevent duplicate confirm widget
        if(modal.querySelector('#themeResetConfirm')) return;
        const confirmDiv = document.createElement('div'); confirmDiv.id = 'themeResetConfirm'; confirmDiv.style.marginTop='10px'; confirmDiv.style.padding='10px'; confirmDiv.style.borderRadius='8px'; confirmDiv.style.display='flex'; confirmDiv.style.flexDirection='column'; confirmDiv.style.gap='8px'; confirmDiv.style.background = 'rgba(255,255,255,0.02)';
        const msg = document.createElement('div'); msg.textContent = '¿Qué quieres restaurar?'; msg.style.fontWeight='600'; confirmDiv.appendChild(msg);
        const row = document.createElement('div'); row.style.display='flex'; row.style.gap='8px'; row.style.justifyContent='flex-end';
        const onlyOwner = document.createElement('button'); onlyOwner.className='btn ghost'; onlyOwner.textContent = 'Solo owner'; onlyOwner.addEventListener('click', ()=>{
          try{ localStorage.removeItem('owner_color'); }catch(e){}
          document.documentElement.style.setProperty('--owner-color', '#2563eb');
          document.documentElement.style.setProperty('--accent', '#2563eb');
          try{ showToast('Color owner restablecido','success') }catch(e){}
          modal.remove();
        });
        const onlyUsers = document.createElement('button'); onlyUsers.className='btn ghost'; onlyUsers.textContent = 'Solo usuarios'; onlyUsers.addEventListener('click', ()=>{
          try{ localStorage.removeItem('user_colors'); }catch(e){}
          try{ showToast('Colores de usuarios restablecidos','success') }catch(e){}
          modal.remove();
        });
        const allBtn = document.createElement('button'); allBtn.className='btn'; allBtn.textContent = 'Todo'; allBtn.addEventListener('click', ()=>{
          try{ localStorage.removeItem('owner_color'); localStorage.removeItem('user_colors'); }catch(e){}
          document.documentElement.style.setProperty('--owner-color', '#2563eb');
          document.documentElement.style.setProperty('--accent', '#2563eb');
          try{ showToast('Tema restablecido','success') }catch(e){}
          modal.remove();
        });
        const cancelBtn = document.createElement('button'); cancelBtn.className='btn ghost'; cancelBtn.textContent='Cancelar'; cancelBtn.addEventListener('click', ()=>{ confirmDiv.remove(); });
        row.appendChild(cancelBtn); row.appendChild(onlyUsers); row.appendChild(onlyOwner); row.appendChild(allBtn);
        confirmDiv.appendChild(row);
        // insert confirmDiv before actions so it's visible
        box.insertBefore(confirmDiv, actions);
      });
      const btnSave = document.createElement('button'); btnSave.className='btn'; btnSave.textContent='Guardar'; btnSave.addEventListener('click', ()=>{
        let parsed = {};
        try{ parsed = JSON.parse(usersArea.value || '{}') }catch(e){ alert('JSON inválido en colores por usuario'); return }
        const settings = { owner: ownerInput.value, users: parsed }
        saveThemeSettings(settings)
        modal.remove();
        showToast('Tema guardado','success');
      });
      actions.appendChild(btnCancel); actions.appendChild(btnReset); actions.appendChild(btnSave); box.appendChild(actions);
      modal.appendChild(box); document.body.appendChild(modal);
    }
    // wire button
    const themeBtnEl = document.getElementById('themeEditorBtn'); if(themeBtnEl) themeBtnEl.addEventListener('click', openThemeEditor);
    // apply on load
    applyThemeSettings(loadThemeSettings());
  }catch(e){}

  var ownerLinks = document.querySelectorAll('nav.main-nav a[href="owner.html"]');
  ownerLinks.forEach(function(link) {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      // Puedes mostrar un mensaje, modal, o simplemente no hacer nada
      alert('Acceso al panel Owner deshabilitado desde este menú.');
    });
  });
});
