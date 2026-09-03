'use strict';
const $ = id => document.getElementById(id);
let session;
function message(text, bad = false) { $('status').textContent = text; $('status').classList.toggle('error', bad); }
async function post(action, payload = {}) {
  const r = await fetch('/desktop/' + action, {method:'POST', headers:{'Content-Type':'application/json','X-Videria-Token':session.token},body:JSON.stringify(payload)});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || 'No se pudo completar la acción. HTTP ' + r.status);
  return data;
}
async function busy(button, fn) {
  button.disabled = true;
  try { await fn(); } catch(e) { message(e.message, true); }
  finally { button.disabled = false; }
}
function button(label, fn, primary = false) {
  const b = document.createElement('button'); b.textContent = label;
  if(primary) b.className = 'primary';
  b.onclick = () => busy(b, fn); return b;
}
async function refresh() {
  const r = await fetch('/desktop/projects');
  if(!r.ok) throw new Error('No se pudo cargar la biblioteca. Cierra y vuelve a abrir Videria.');
  session = await r.json(); $('version').textContent = 'v' + session.version;
  $('destination').textContent = session.projects_dir;
  $('projects').replaceChildren();
  for(const p of session.projects) {
    const card = document.createElement('article'); card.className = 'card';
    const top = document.createElement('div'); top.className = 'card-top';
    const icon = document.createElement('span'); icon.className='video-icon'; icon.textContent='▶';
    const tag = document.createElement('span'); tag.className='tag'; tag.textContent = p.available ? (p.git ? 'Proyecto compartido' : 'Proyecto local') : 'Carpeta no disponible';
    top.append(icon,tag);
    const body = document.createElement('div'); body.className='card-body';
    const h = document.createElement('h2'); h.textContent = p.name;
    const path = document.createElement('p'); path.className = 'path'; path.textContent = p.path;
    const actions = document.createElement('div'); actions.className='card-actions';
    if(p.available) {
      actions.append(button('Editar', async()=>{ message('Abriendo ' + p.name + '…'); const d = await post('open',{id:p.id}); location.href=d.url; },true));
      actions.append(button('Carpeta',()=>post('reveal',{id:p.id})));
      if(p.git) actions.append(button('Recibir cambios',async()=>{
        if(!confirm('¿Recibir la última revisión de ' + p.name + '? No continúes si tienes este proyecto abierto en otra ventana.')) return;
        message('Recibiendo cambios de GitHub…'); const d=await post('pull',{id:p.id}); await refresh(); message('Proyecto actualizado. ' + d.message);
      }));
    }
    body.append(h,path,actions); card.append(top,body); $('projects').append(card);
  }
  if(!session.projects.length) { const p=document.createElement('p');p.className='empty';p.textContent='Todavía no hay proyectos. Agrega una carpeta existente o descarga la preedición de GitHub.';$('projects').append(p); }
}
$('add').onclick = () => busy($('add'),async()=>{
  if(session.native_picker) { const d=await post('register');if(!d.cancelled){await refresh();message('Proyecto agregado. Pulsa Editar.');} }
  else $('folderDialog').showModal();
});
$('clone').onclick=()=>$('cloneDialog').showModal();
$('refresh').onclick=()=>busy($('refresh'),refresh);
for(const b of document.querySelectorAll('[data-close]'))b.onclick=()=>b.closest('dialog').close();
$('folderForm').onsubmit=e=>{e.preventDefault();$('folderDialog').close();busy($('add'),async()=>{await post('register',{path:$('folderPath').value});await refresh();message('Proyecto agregado.');});};
$('cloneForm').onsubmit=e=>{e.preventDefault();$('cloneDialog').close();busy($('clone'),async()=>{message('Descargando proyecto. Los videos pueden tardar unos minutos…');await post('clone',{url:$('repoUrl').value});await refresh();message('Descarga completa. Pulsa Editar.');});};
refresh().catch(e=>message(e.message,true));
