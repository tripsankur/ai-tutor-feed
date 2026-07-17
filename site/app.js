
function epKey(id){return 'aitutor-done-'+id}
function isDone(id){return localStorage.getItem(epKey(id))==='1'}
function setDone(id,v){v?localStorage.setItem(epKey(id),'1'):localStorage.removeItem(epKey(id));paint()}
function toggleDone(id){setDone(id,!isDone(id))}
function paint(){
  document.querySelectorAll('[data-ep]').forEach(el=>{
    el.classList.toggle('done',isDone(el.dataset.ep));
  });
  document.querySelectorAll('.btn.complete').forEach(b=>{
    const on=isDone(b.dataset.ep);b.classList.toggle('on',on);
    b.textContent=on?'✓ Completed':'Mark complete';
  });
  document.querySelectorAll('.card').forEach(c=>{
    const eps=[...c.querySelectorAll('[data-ep]')];if(!eps.length)return;
    const done=eps.filter(e=>isDone(e.dataset.ep)).length;
    const bar=c.querySelector('.bar>div');if(bar)bar.style.width=(100*done/eps.length)+'%';
    const pct=c.querySelector('.pct');if(pct)pct.textContent=done+'/'+eps.length;
  });
}
document.addEventListener('DOMContentLoaded',paint);
