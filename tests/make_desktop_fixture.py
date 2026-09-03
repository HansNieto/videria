"""Material sintético para pruebas que nunca toca videos 17–20."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'desktop'))
from main import configure_ffmpeg
configure_ffmpeg()
from vcutlib import studio, util

pdir=ROOT/'build/qa-project'
pdir.mkdir(parents=True,exist_ok=True)
movie=pdir/'test.mp4'
if not movie.exists():
    util.run([util.FFMPEG,'-y','-f','lavfi','-i','testsrc2=size=540x960:rate=30',
              '-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','8',
              '-c:v','libx264','-preset','ultrafast','-crf','25','-c:a','aac','-pix_fmt','yuv420p',movie])
source=dict(util.probe(movie),id='s1',name='test.mp4',path=str(movie),proxy=str(movie))
project={'name':'QA · botones (no es un video real)','sources':[source],
         'sequence':{'fps':30,'width':1080,'height':1920},
         'segments':[{'id':'a','source':'s1','in':0,'out':4,'enabled':True,'text':'Primer clip de prueba'},
                     {'id':'b','source':'s1','in':4,'out':8,'enabled':True,'text':'Segundo clip de prueba'}]}
util.write_json(pdir/'local.json',{'sources':{'s1':{'path':str(movie)}}})
util.write_json(pdir/'project.json',project)
tl=studio.new_timeline(project)
studio.save(pdir,tl)
print(pdir)
