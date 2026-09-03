// Ejecuta el compositor real: detecta ReferenceError que un chequeo de sintaxis no ve.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const noop = () => {};
const context2d = new Proxy({}, {get:(o,k)=>k in o ? o[k] : noop});
const nodes = new Map();
function node(id) {
  if(!nodes.has(id)) nodes.set(id,{style:{},classList:{toggle:noop,add:noop,remove:noop},clientWidth:500,clientHeight:800,getContext:()=>context2d});
  return nodes.get(id);
}
const sandbox = {document:{getElementById:node},console}; sandbox.window=sandbox;
vm.createContext(sandbox);
const base=path.join(__dirname,'../skills/video-cut/studio/js');
for(const file of ['state.js','player.js']) vm.runInContext(fs.readFileSync(path.join(base,file),'utf8'),sandbox,{filename:file});
const ST=sandbox.ST;
ST.S.project={sources:[],segments:[{id:'a',source:'s1',in:0,out:4,enabled:true},{id:'b',source:'s1',in:4,out:8,enabled:true}]};
ST.S.tl={canvas:{width:1080,height:1920,fps:30},clips:{b:{gap_before:2}},tracks:[],transitions:[],render:{}};
ST.S.cat={}; ST.state.resolve();
for(const time of [0,2,4.5,6,9.9,10]) {
  ST.S.t=time;
  for(const mode of ['select','frame']){
    ST.S.mode=mode;
    for(const guides of [false,true]){
      ST.S.guides=guides;ST.S.safe=guides;ST.S.tiktokUi=guides;
      assert.doesNotThrow(()=>ST.player.paint(),`paint t=${time},mode=${mode},guides=${guides}`);
    }
  }
}
assert.equal(ST.S.total,10);
console.log('PASS: compositor con clip, hueco, final, encuadre y guías (24 casos).');
