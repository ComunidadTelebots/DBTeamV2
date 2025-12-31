document.addEventListener('DOMContentLoaded',()=>{
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
