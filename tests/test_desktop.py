import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'desktop'), str(ROOT/'skills/video-cut/scripts')]
from host import DesktopHost, ProjectLibrary, github_url
from vcutlib import studio, util


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root/'video17-proyecto'
        self.project.mkdir()
        (self.project/'project.json').write_text(json.dumps({'name':'QA','sources':[], 'segments':[]}), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_discover_register_and_reopen(self):
        lib = ProjectLibrary(self.root/'settings', [self.root])
        self.assertEqual(len(lib.list()),1)
        key=lib.register(self.project/'project.json')
        self.assertEqual(len(lib.list()),1)
        self.assertEqual(ProjectLibrary(self.root/'settings').get(key),self.project.resolve())
        with self.assertRaises(ValueError): lib.register(self.root)

    def test_local_host_token_validation_and_dirty_pull(self):
        host=DesktopHost(self.root/'settings',ROOT/'desktop/ui',roots=[self.root],projects_dir=self.root/'clones')
        client=host.app.test_client()
        try:
            info=client.get('/desktop/projects',base_url='http://127.0.0.1').get_json()
            self.assertEqual(info['version'],'2.3.0')
            self.assertEqual(client.post('/desktop/open',json={'id':info['projects'][0]['id']},base_url='http://127.0.0.1').status_code,403)
            self.assertEqual(client.get('/desktop/projects',base_url='http://malicious.example').status_code,403)
            for path in ('/','/help/instalar-app.html'):
                with client.get(path,base_url='http://127.0.0.1') as response:
                    self.assertEqual(response.status_code,200)
            headers={'X-Videria-Token':info['token']}
            (self.project/'.git').mkdir()
            with patch('host.git_run',return_value=' M timeline.json') as git:
                r=client.post('/desktop/pull',json={'id':info['projects'][0]['id']},headers=headers,base_url='http://127.0.0.1')
                self.assertEqual(r.status_code,400)
                self.assertIn('Hay cambios locales',r.get_json()['error'])
                self.assertEqual(git.call_count,1) # nunca ejecuta pull
            with patch('host.git_run') as git:
                host.projects_dir.mkdir(); (host.projects_dir/'demo').mkdir()
                r=client.post('/desktop/clone',json={'url':'https://github.com/a/demo'},headers=headers,base_url='http://127.0.0.1')
                self.assertEqual(r.status_code,400)
                git.assert_not_called()
        finally:
            host.http.server_close()

    def test_git_url_restricts_provider_credentials_and_traversal(self):
        self.assertEqual(github_url('https://github.com/HansNieto/videria-video17.git'),('https://github.com/HansNieto/videria-video17.git','videria-video17'))
        for value in ['file:///etc/passwd','https://key@github.com/a/b','https://github.com/a/..','https://evil.example/a/b','https://github.com/a/b?token=123','--upload-pack=evil']:
            with self.assertRaises(ValueError): github_url(value)

    def test_project_asset_paths_round_trip_across_computers(self):
        asset=self.project/'assets/importados/sticker.png'; asset.parent.mkdir(parents=True); asset.write_bytes(b'fixture')
        tl=studio.new_timeline({'sources':[],'segments':[]})
        tl['tracks'][0]['items']=[{'id':'x','src':str(asset)}]
        studio.save(self.project,tl)
        raw=json.loads((self.project/'timeline.json').read_text(encoding='utf-8'))
        self.assertEqual(raw['tracks'][0]['items'][0]['src'],'assets/importados/sticker.png')
        reopened=studio.load(self.project,{'sources':[],'segments':[]})
        self.assertEqual(reopened['tracks'][0]['items'][0]['src'],str(asset))
        legacy=r'C:\Users\OtraPersona\video17-proyecto\assets\importados\sticker.png'
        self.assertEqual(studio.resolve_asset(legacy,self.project),str(asset))

    def test_bundled_assets_and_legacy_skill_paths(self):
        sticker=util.skill_root()/'assets/sfx/3_impacto.wav'
        self.assertTrue(sticker.is_file())
        legacy=r'C:\Users\OtraPersona\.claude\skills\video-cut\assets\sfx\3_impacto.wav'
        self.assertEqual(studio.resolve_asset(legacy,self.project),str(sticker))
        self.assertEqual(studio.portable_asset(str(sticker),self.project),'@skill/assets/sfx/3_impacto.wav')
        self.assertEqual(studio.resolve_asset('@skill/assets/sfx/3_impacto.wav',self.project),str(sticker))
        with self.assertRaises(ValueError): studio.resolve_asset('@skill/../../secret',self.project)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows short paths')
    def test_windows_short_asset_path_is_saved_relative(self):
        import ctypes
        asset = self.project/'assets/importados/nombre de sticker largo.png'
        asset.parent.mkdir(parents=True)
        asset.write_bytes(b'fixture')
        short = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(str(asset), short, len(short))
        self.assertGreater(length, 0)
        self.assertEqual(studio.portable_asset(short.value,self.project),
                         'assets/importados/nombre de sticker largo.png')


if __name__=='__main__': unittest.main()
