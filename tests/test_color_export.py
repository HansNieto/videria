import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/video-cut/scripts'))
from vcutlib import color, export_options, render, server, studio


class ColorExportTests(unittest.TestCase):
    def test_hdr_and_sdr_are_not_mapped_twice(self):
        hdr=color.to_sdr({'color_transfer':'arib-std-b67','color_primaries':'bt2020'})
        self.assertLess(hdr.index('format=gbrpf32le'),hdr.index('tonemap='))
        self.assertIn('transfer=bt709:matrix=bt709',hdr)
        self.assertIn('tonemap=',color.to_sdr({'color_transfer':'smpte2084'}))
        self.assertNotIn('tonemap=',color.to_sdr({'color_transfer':'bt709'}))

    def test_export_does_not_mutate_canvas_and_validates(self):
        canvas={'width':1080,'height':1920,'fps':30}
        self.assertEqual(export_options.canvas_for(canvas,{'resolution':720,'fps':60}),
                         {'width':720,'height':1280,'fps':60})
        self.assertEqual(canvas,{'width':1080,'height':1920,'fps':30})
        for raw in ({'fps':float('nan')},{'fps':999},{'resolution':True},{'encoder':'-bad'},[] ,{'color':'hdr'}):
            with self.assertRaises(ValueError): export_options.validate(raw)

    def test_free_positions_and_range_duration(self):
        project={'sources':[{'id':'s','name':'s'}],'segments':[
            {'id':'a','source':'s','in':0,'out':4,'enabled':True},
            {'id':'b','source':'s','in':0,'out':2,'enabled':True}]}
        tl={'canvas':{'width':1080,'height':1920,'fps':30},
            'clips':{'a':{'start':0},'b':{'start':1,'track':'v2'}},
            'tracks':[{'id':'v2','kind':'video','z':10,'items':[]},
                      {'id':'ov','kind':'overlay','z':20,'items':[{'id':'o','t':6,'dur':2}]}],
            'transitions':[{'at_seg':'b','type':'flash'}]}
        resolved=studio.resolve(project,tl)
        self.assertEqual(resolved['total'],8)
        self.assertEqual(resolved['clips'][1]['t0'],1)
        self.assertEqual(resolved['clips'][1]['z'],10)
        self.assertEqual(resolved['transitions'],[])
        job=render.Job(project,tl,'.','test.mp4',range_=(2,5))
        self.assertEqual(job.total,3)
        self.assertEqual(job.clips[0]['t0'],0)
        self.assertEqual(job.clips[0]['effect_offset'],2)

    def test_bad_export_options_rejected_before_starting_job(self):
        app=server.create_app('.')
        result=app.test_client().post('/api/render',json={'options':{'fps':10000}})
        self.assertEqual(result.status_code,400)

    def test_subtitles_do_not_overlap_when_clips_overlap(self):
        import copy
        tl={'canvas':{'width':1080,'height':1920,'fps':30},'clips':{},'transitions':[],
            'tracks':[{'id':'t_sub','kind':'text','items':[
                {'id':'one','t':0,'dur':3}, {'id':'two','t':2,'dur':3}]}]}
        original=copy.deepcopy(tl)
        resolved=studio.resolve({'sources':[],'segments':[]},tl)
        self.assertEqual(resolved['items'][0]['t_end'],2)
        self.assertEqual(resolved['items'][1]['t'],2)
        self.assertEqual(tl,original)


if __name__=='__main__': unittest.main()
