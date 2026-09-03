"""Opt-in real-camera HDR/color and CPU/GPU integration. Only writes build/."""
import copy
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/video-cut/scripts'))
from vcutlib import color, media, render, studio, util


def pixels(path, at):
    return np.frombuffer(util.run_bytes([util.FFMPEG, '-v', 'error', '-ss', str(at),
        '-i', str(path), '-frames:v', '1', '-pix_fmt', 'yuv420p10le', '-f', 'rawvideo', '-']), dtype='<u2').astype(float)


def main():
    original = ROOT / 'videos/video17/IMG_0120.MOV'
    if not original.exists():
        print('SKIP: optional local camera original unavailable'); return
    pdir = ROOT / 'build/original-color-qa'; pdir.mkdir(parents=True, exist_ok=True)
    source = dict(util.probe(original), id='hdr', name=original.name, path=str(original))
    project = {'name': 'QA HDR · copia de prueba', 'sources': [source],
        'sequence': {'width': 1080, 'height': 1920, 'fps': 30},
        'segments': [{'id': 'h', 'source': 'hdr', 'in': 1, 'out': 5, 'enabled': True}]}
    tl = studio.new_timeline(project); tl['render']['loudnorm'] = False
    util.write_json(pdir/'project.json', project)
    util.write_json(pdir/'local.json', {'sources': {'hdr': {'path': str(original)}}})
    studio.save(pdir, tl)
    baseline = pixels(original, 1.5)
    stats = {}
    for enc in ('x264', 'nvenc'):
        if enc == 'nvenc' and not media.nvenc_available('hevc'):
            raise AssertionError('NVIDIA HEVC 10-bit encoder unavailable on this QA machine')
        dest = pdir/f'original-{enc}.mp4'
        start = time.perf_counter()
        info = render.render(project, tl, pdir, dest, options={'encoder': enc, 'quality': 18})
        elapsed = time.perf_counter() - start
        p = util.probe(dest)
        assert p['color_transfer'] == source['color_transfer'] == 'arib-std-b67'
        assert p['color_primaries'] == 'bt2020' and p['color_space'] == 'bt2020nc'
        assert p['pix_fmt'] == 'yuv420p10le' and p['vcodec'] == 'hevc'
        actual = pixels(dest, 0.5)
        mae = np.abs(baseline - actual).mean()
        assert mae < 5, f'Neutral source color changed: MAE {mae}/1023'
        stats[enc] = {'seconds': round(elapsed, 3), 'yuv_mae_1023': round(mae, 3), 'bytes': dest.stat().st_size}
        print(enc, stats[enc], flush=True)
    print('GPU speedup:', stats['x264']['seconds']/stats['nvenc']['seconds'], flush=True)
    # An edited HDR shot must keep ten bits through zoom, transitions, color,
    # transparent SDR artwork, and subtitle composition (not just final tags).
    from PIL import Image
    sticker = pdir/'alpha.png'; Image.new('RGBA',(80,80),(255,50,30,128)).save(sticker)
    edited = copy.deepcopy(tl)
    edited['clips'] = {'h': {'zoom': {'kf': [{'t':0,'scale':1},{'t':4,'scale':1.3}]},
                            'look': {'brightness':0.01,'saturation':0,'temp':-0.1,'vignette':0.1}}}
    edited['tracks'].append({'id':'o','kind':'overlay','z':20,'items':[
        {'id':'sticker','src':str(sticker),'t':0,'dur':4,'x':0.5,'y':0.15,'scale':1,'opacity':0.7,'fade':0.2}]})
    text_track = next(t for t in edited['tracks'] if t['id']=='t_sub')
    text_track['items'] = [{'id':'test-sub','t':0,'dur':4,'lines':[[{'w':'Prueba','s':0,'e':2},{'w':'HDR','s':2,'e':4}]],'style':'sub'}]
    edited['canvas']={'width':360,'height':640,'fps':30}
    render.render(project, edited, pdir, pdir/'edited-hdr.mp4', options={'encoder':'nvenc','quality':18})
    assert pixels(pdir/'edited-hdr.mp4',1.5)[:360*640].mean() > 200, 'Camera disappeared behind transparent layer'
    # FFmpeg reports every implicit format conversion at verbose log level.
    job = render.Job(project, edited, pdir, pdir/'format-check.mp4', options={'encoder':'nvenc'})
    job.res['transitions'] = [dict(type='flash', t=1, t0=0.8, t1=1.2, dur=0.4, strength=0.5),
                              dict(type='shake', t=2, t0=1.8, t1=2.2, dur=0.4, strength=0.5)]
    cmd, _ = job.build(pdir/'cache/burn.ass')
    import subprocess, re
    check = subprocess.run(cmd[:1]+['-loglevel','verbose']+cmd[1:], capture_output=True,
        encoding='utf-8',errors='replace', creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (pdir/'format-check.log').write_text(check.stderr,encoding='utf-8')
    assert check.returncode == 0, check.stderr[-3000:]
    bad = [ln for ln in check.stderr.splitlines() if '->' in ln and re.search(r'fmt:(yuv420p|yuva420p|gbrp|rgba|bgra|argb)(?:\s|$)',ln.split('->')[-1])]
    assert not bad, '8-bit conversion in HDR graph: '+str(bad)
    stats['formats'] = '10-bit camera retained through zoom, effects, overlays and ASS'
    util.write_json(pdir/'results.json', stats)
    print('PASS: original HLG/color; CPU vs GPU; 10-bit editing and transparency',flush=True)


if __name__ == '__main__': main()
