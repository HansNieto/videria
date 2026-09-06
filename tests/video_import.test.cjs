const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');

const sandbox = {
  structuredClone, console, fetch: async () => { throw new Error('unexpected fetch'); },
  document: {
    getElementById: () => null,
    createElement: () => ({}),
    querySelectorAll: () => [],
  },
};
sandbox.window = sandbox;
vm.createContext(sandbox);
const js = (name) => vm.runInContext(fs.readFileSync(
  path.join(__dirname, '../skills/video-cut/studio/js/', name), 'utf8'), sandbox);
js('state.js');

const {S, state: st} = sandbox.ST;
sandbox.ST.text = {wrap: () => []};
sandbox.ST.app = {renderAll() {}, toast() {}, onSelect() {}};
sandbox.ST.player = {seek(t) { S.t = t; }};
S.project = {
  sources: [{id:'s001', name:'base.mp4', duration:4, has_audio:true}],
  segments: [{id:'u0001', source:'s001', in:0, out:4, enabled:true, text:''}],
  groups: [],
};
S.sources = {s001:S.project.sources[0]};
S.tl = {counter:0, canvas:{width:1080,height:1920,fps:30}, clips:{},
  tracks:[{id:'_video',kind:'video',name:'Vídeo',z:0,items:[]}], transitions:[]};
st.resolve();
js('library.js');

const extra = {id:'s002',name:'extra.mp4',duration:2.5,has_audio:true,has_video:true};
const added = sandbox.ST.library.addVideoClip(extra, 4, '_video');
assert.equal(added.source, 's002');
assert.equal(st.clipOf(added.id).track, '_video');
assert.equal(st.clipOf(added.id).t0, 4);
assert.equal(S.sources.s002.has_audio, true);

const overlap = {id:'s003',name:'encima.mp4',duration:1.5,has_audio:true,has_video:true};
const overSeg = sandbox.ST.library.addVideoClip(overlap, 1, '_video');
assert.notEqual(st.clipOf(overSeg.id).track, '_video');
assert.equal(st.clipAt(1.2).source, 's003');
assert.ok(S.tl.tracks.filter((x) => x.kind === 'video').length >= 2);

console.log('PASS: imported videos become real clips with audio and overlapping creates a video layer.');
