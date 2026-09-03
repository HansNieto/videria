"""Opt-in FFmpeg integration: synthetic layers and an optional local HDR clip.

Run with VCUT_FFMPEG / VCUT_FFPROBE pointing to the bundled tools. All output
lives in build/qa-v220 or build/color-tests, never in a user's project.
"""
import copy
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/video-cut/scripts'))
from vcutlib import color, media, render, studio, util


def frame(path, at, width=64, height=64):
    return util.run_bytes([util.FFMPEG,'-v','error','-ss',str(at),'-i',str(path),
        '-frames:v','1','-vf',f'scale={width}:{height}','-pix_fmt','rgb24','-f','rawvideo','-'])


def main():
    pdir=ROOT/'build/qa-v220'; pdir.mkdir(parents=True,exist_ok=True)
    sources=[]
    for sid,shade,freq in [('s1','red',440),('s2','blue',880)]:
        movie=pdir/(sid+'.mp4')
        if not movie.exists():
            util.run([util.FFMPEG,'-y','-f','lavfi','-i',f'color=c={shade}:s=360x640:r=30:d=4',
                '-f','lavfi','-i',f'sine=frequency={freq}:sample_rate=48000','-t','4',
                '-c:v','libx264','-preset','ultrafast','-c:a','aac']+color.SDR_TAGS+[str(movie)])
        sources.append(dict(util.probe(movie),id=sid,name=movie.name,path=str(movie),proxy=str(movie)))
    project={'name':'QA capas y exportación · NO ES TU VÍDEO','sources':sources,
        'sequence':{'width':1080,'height':1920,'fps':30},'segments':[
            {'id':'a','source':'s1','in':0,'out':4,'enabled':True,'text':'ROJO'},
            {'id':'b','source':'s2','in':0,'out':2,'enabled':True,'text':'AZUL'}]}
    tl=studio.new_timeline(project)
    tl['clips']={'a':{'start':0},'b':{'start':1,'track':'v2'}}
    tl['tracks'].append({'id':'v2','kind':'video','name':'Vídeo superior','z':10,'items':[]})
    tl['render']['encoder']='x264'; tl['render']['loudnorm']=False
    util.write_json(pdir/'project.json',project)
    util.write_json(pdir/'local.json',{'sources':{s['id']:{'path':s['path']} for s in sources}})
    studio.save(pdir,tl)
    snapshot=copy.deepcopy(tl)
    out=pdir/'layers-720p60.mp4'
    info=render.render(project,tl,pdir,out,options={'resolution':720,'fps':60,'encoder':'x264','quality':23})
    result=util.probe(out)
    assert (result['width'],result['height'],result['fps'])==(720,1280,60)
    assert abs(result['duration']-4)<0.05 and result['color_space']=='bt709'
    assert snapshot==tl, 'Export modified the project canvas!'
    import numpy as np
    for t,channel in [(0.5,0),(1.5,2),(3.5,0)]:
        mean=np.frombuffer(frame(out,t),dtype=np.uint8).reshape(-1,3).mean(axis=0)
        assert mean[channel]>180 and mean[(channel+1)%3]<40, (t,mean)
    print('PASS: render 720x1280 / 60 FPS, 4s; top blue layer and red restored; Rec.709; project unchanged',flush=True)
    # A late item extends the timeline; the gap must remain black, not compact.
    tl['clips']['b']['start']=6
    gapout=pdir/'gap-range.mp4'
    render.render(project,tl,pdir,gapout,range_=(3,7),options={'resolution':720,'fps':24,'encoder':'x264'})
    black=np.frombuffer(frame(gapout,2),dtype=np.uint8).mean()
    assert black<3, black
    assert abs(util.probe(gapout)['duration']-4)<0.06
    print('PASS: gaps and range export retain absolute timing',flush=True)

    original=ROOT/'videos/video17/IMG_0120.MOV'
    if original.exists():
        target=ROOT/'build/color-tests'; target.mkdir(exist_ok=True)
        source=dict(util.probe(original),id='hdr',name=original.name,path=str(original))
        hdrpj={'name':'HDR QA','sources':[source],'sequence':{'width':1080,'height':1920,'fps':30},
               'segments':[{'id':'h','source':'hdr','in':1,'out':3,'enabled':True}]}
        hdrtl=studio.new_timeline(hdrpj); hdrtl['render']['loudnorm']=False
        proxy=media.build_proxy(source,target,height=1920)
        export=target/'same-frame-export.mp4'
        render.render(hdrpj,hdrtl,target,export,options={'quality':18,'encoder':'x264'})
        a=np.frombuffer(frame(proxy,1.5,108,192),dtype=np.uint8).astype(float)
        b=np.frombuffer(frame(export,0.5,108,192),dtype=np.uint8).astype(float)
        mae=np.abs(a-b).mean()
        assert mae<8, mae
        print(f'PASS: real HDR original -> preview vs render matching frame MAE={mae:.3f}/255',flush=True)
        util.run([util.FFMPEG,'-y','-ss','0.5','-i',str(export),'-frames:v','1','-update','1',str(target/'corrected-frame.png')])


if __name__=='__main__': main()
