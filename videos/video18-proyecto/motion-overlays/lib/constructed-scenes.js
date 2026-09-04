/* Escenas 3D construidas por capas para Videria. Configuración: SCENE_CONFIG. */
(function(){
  'use strict';
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const color=n=>['sticker-blue','sticker-cyan','sticker-red'].includes(n.color)?n.color:'sticker-blue';
  function node(n,i){
    const beat=(.08+i*.58).toFixed(2), c=color(n), symbol=esc(n.symbol), label=esc(n.label||'');
    const small=String(n.symbol||'').length>3?' small':'';
    if(n.shape==='card') return `<g class="o node ${n.emphasis?'emphasis':''}" data-beat="${beat}" transform="translate(${n.x},${n.y})"><rect class="piece sticker-depth" x="-118" y="-73" width="236" height="146" rx="32" transform="translate(0,15)"/><rect class="piece sticker-rim" x="-118" y="-73" width="236" height="146" rx="32"/><rect class="piece ${c}" x="-103" y="-58" width="206" height="116" rx="23"/><path class="piece sticker-shine" d="M-80,-45 H66 Q85,-45 89,-25 H-91 Q-90,-38 -80,-45 Z"/><text class="piece v17-label v17-symbol${small}" x="0" y="1" text-anchor="middle">${symbol}</text><text class="piece v17-label" x="0" y="42" text-anchor="middle">${label}</text></g>`;
    if(n.shape==='tag') return `<g class="o node ${n.emphasis?'emphasis':''}" data-beat="${beat}" transform="translate(${n.x},${n.y})"><path class="piece sticker-depth" d="M-112,-62 H62 L126,0 L62,78 H-112 Q-138,78 -138,52 V-36 Q-138,-62 -112,-62 Z"/><path class="piece sticker-rim" d="M-112,-76 H62 L126,-14 L62,64 H-112 Q-138,64 -138,38 V-50 Q-138,-76 -112,-76 Z"/><path class="piece ${c}" d="M-103,-61 H54 L107,-13 L53,49 H-103 Q-122,49 -122,30 V-42 Q-122,-61 -103,-61 Z"/><path class="piece sticker-shine" d="M-96,-50 H43 L69,-25 H-111 V-37 Q-111,-50 -96,-50 Z"/><circle class="piece sticker-rim" cx="66" cy="-13" r="12"/><text class="piece v17-label v17-symbol${small}" x="-22" y="0" text-anchor="middle">${symbol}</text><text class="piece v17-label" x="-22" y="39" text-anchor="middle">${label}</text></g>`;
    return `<g class="o node ${n.emphasis?'emphasis':''}" data-beat="${beat}" transform="translate(${n.x},${n.y})"><circle class="piece sticker-depth" cy="15" r="99"/><circle class="piece sticker-rim" r="96"/><circle class="piece ${c}" r="82"/><path class="piece sticker-shine" d="M-55,-54 A79,79 0 0 1 54,-56 A66,66 0 0 0 -55,-54 Z"/><text class="piece v17-label v17-symbol${small}" x="0" y="2" text-anchor="middle">${symbol}</text><text class="piece v17-label" x="0" y="49" text-anchor="middle">${label}</text></g>`;
  }
  function route(a,b,i){
    const x1=Number(a.x)+88,x2=Number(b.x)-88,y1=Number(a.y),y2=Number(b.y),mid=((x1+x2)/2).toFixed(1),beat=(.34+i*.58).toFixed(2);
    const d=`M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`;
    return `<g class="o route" data-beat="${beat}"><path class="piece route-line sticker-route-depth" d="${d}"/><path class="piece route-line sticker-route" d="${d}"/><path class="piece route-arrow sticker-cyan" d="M${x2-18},${y2-22} L${x2+21},${y2} L${x2-18},${y2+22} Z"/></g>`;
  }
  function start(){
    const cfg=window.SCENE_CONFIG;if(!cfg||!cfg.nodes)throw new Error('Falta SCENE_CONFIG');
    const edges=cfg.edges||cfg.nodes.slice(0,-1).map((_,i)=>[i,i+1]);
    const svg=document.querySelector('svg.canvas');
    svg.innerHTML=`<g class="module" transform="translate(540,500)">${edges.map((e,i)=>route(cfg.nodes[e[0]],cfg.nodes[e[1]],i)).join('')}${cfg.nodes.map(node).join('')}</g>`;
    Overlay.scene({id:cfg.id||'scene',style:'s-sticker3d',build(tl){
      const nodes=[...document.querySelectorAll('.o.node')],routes=[...document.querySelectorAll('.o.route')];
      gsap.set('.o,.piece',{autoAlpha:0});gsap.set('.piece',{transformOrigin:'50% 50%'});
      nodes.forEach(n=>{const at=+n.dataset.beat,p=[...n.querySelectorAll(':scope > .piece')];tl.set(n,{autoAlpha:1},at);p.forEach((el,j)=>{const line=el.classList.contains('route-line');if(line)tl.fromTo(el,{autoAlpha:0,drawSVG:'0%'},{autoAlpha:1,drawSVG:'100%',duration:.24,ease:'power2.out'},at+j*.075);else tl.fromTo(el,{autoAlpha:0,scale:j<2?.3:.52,y:j===0?14:0},{autoAlpha:1,scale:1,y:0,duration:j<2?.30:.24,ease:j<2?'brand':'settle'},at+j*.075);});});
      routes.forEach(r=>{const at=+r.dataset.beat;tl.set(r,{autoAlpha:1},at).fromTo(r.querySelectorAll('.route-line'),{autoAlpha:0,drawSVG:'0%'},{autoAlpha:1,drawSVG:'100%',duration:.44,stagger:.05,ease:'power2.inOut'},at).fromTo(r.querySelector('.route-arrow'),{autoAlpha:0,scale:.2},{autoAlpha:1,scale:1,duration:.2,ease:'settle'},at+.35);});
      tl.to('.emphasis',{scale:1.06,duration:.15,yoyo:true,repeat:1,ease:'power2.out',transformOrigin:'50% 50%'},3.55).to({}, {duration:.01},4.16).to('.route-arrow,.v17-label',{autoAlpha:0,scale:.65,duration:.18,stagger:.012,ease:'swift'},4.2).to('.route-line',{drawSVG:'0%',autoAlpha:0,duration:.27,stagger:.012,ease:'swift'},4.3).to('.sticker-shine',{autoAlpha:0,duration:.18,ease:'swift'},4.4).to('.sticker-blue,.sticker-cyan,.sticker-red',{autoAlpha:0,scale:.42,duration:.22,stagger:.015,ease:'swift'},4.48).to('.sticker-rim',{autoAlpha:0,scale:.3,duration:.21,stagger:.012,ease:'swift'},4.59).to('.sticker-depth',{autoAlpha:0,scale:.25,duration:.2,stagger:.012,ease:'swift'},4.7).set('.o',{autoAlpha:0},5.01);
    }});
  }
  window.BuiltScene={start};
})();

