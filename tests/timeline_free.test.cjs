const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const sandbox = {structuredClone, console, document:{getElementById:()=>null}};
sandbox.window=sandbox; vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../skills/video-cut/studio/js/state.js'),'utf8'),sandbox);
const {state:st,S} = sandbox.ST;
sandbox.ST.app={renderAll(){},toast(){}};
S.project={sources:[],segments:[{id:'a',source:'s1',in:0,out:4,enabled:true},{id:'b',source:'s1',in:4,out:8,enabled:true}]};
S.tl={canvas:{width:1080,height:1920,fps:30},clips:{},tracks:[{id:'ov',kind:'overlay',z:10,items:[
  {id:'o1',t:1,dur:2},{id:'o2',anchor:{seg:'b',offset:1},dur:2}
]}],transitions:[]};
st.resolve(); assert.equal(S.total,8);
st.push();
let lane = st.placeClip('b',1,'_video'); st.resolve();
assert.equal(st.clipOf('b').t0,1); assert.equal(st.clipOf('a').t0,0);
assert.notEqual(lane.id,'_video'); assert.equal(st.clipAt(2).seg,'b');
assert.equal(st.clipAt(0.5).seg,'a'); assert.equal(st.clipAt(4.5).seg,'b');
assert.equal(S.total,5); assert.equal(S.items.find(x=>x.id==='o2').t,2);
st.undo(); assert.equal(st.clipOf('b').t0,4); assert.equal(S.total,8);
st.redo(); assert.equal(st.clipOf('b').t0,1);
st.placeClip('b',9,'_video'); st.resolve();
assert.equal(st.clipOf('a').t0,0); assert.equal(st.clipOf('b').t0,9);
assert.equal(st.clipAt(7),null); assert.equal(S.total,13);
S.pps=100; S.t=7;
// Start is far from an edge, end is close: must snap using the end.
let snap=st.snapTime('b',3.05,3.98);
assert.equal(snap.edge,7); assert.equal(snap.time,3.02);
assert.equal(st.snapTime('b',3.05,3.98,false).time,3.05);
const newLane=st.placeItem('o2',1.2,'ov'); st.resolve();
assert.notEqual(newLane.id,'ov'); assert.equal(st.findItem('o2').it.anchor,undefined);
assert.equal(S.items.find(x=>x.id==='o2').t,1.2);
st.placeItem('o2',20,newLane.id); st.resolve(); assert.equal(S.total,22);
st.detachAnchors('a'); S.project.segments[0].enabled=false; st.resolve();
assert.equal(st.clipOf('b').t0,9); assert.equal(S.total,22);
st.track('_video').hidden=true; st.resolve(); assert.equal(st.clipAt(10),null);
assert.equal(st.delTrack('_video'),false);
console.log('PASS: free movement, auto tracks, z-order, gaps, both-edge snapping, Alt, independent items, undo/redo and deletion.');
