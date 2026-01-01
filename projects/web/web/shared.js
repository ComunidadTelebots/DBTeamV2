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
});
