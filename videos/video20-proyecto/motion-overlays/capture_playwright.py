from pathlib import Path
import argparse
from playwright.sync_api import sync_playwright

p=argparse.ArgumentParser();p.add_argument('files',nargs='*');p.add_argument('--all',action='store_true');p.add_argument('--fps',type=float,default=30);a=p.parse_args();root=Path.cwd();files=[Path(x) for x in a.files]
if a.all: files=sorted(x for x in root.glob('[0-9][0-9]_*.html') if not x.name.startswith('00'))
if not files: raise SystemExit('Indica HTML o usa --all')
chrome=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True,executable_path=str(chrome),args=['--hide-scrollbars','--force-color-profile=srgb','--allow-file-access-from-files'])
 for f in files:
  page=b.new_page(viewport={'width':1080,'height':1920});page.goto(f.resolve().as_uri()+'?paused=1&loop=0',wait_until='load',timeout=15000);page.wait_for_function('window.Overlay&&Overlay.duration>0',timeout=15000);dur=float(page.evaluate('Overlay.duration'));total=round(dur*a.fps)+1;dest=root/'frames'/f.stem;dest.mkdir(parents=True,exist_ok=True);print(f'{f.stem}: {dur:.2f}s · {total} frames')
  for i in range(total):
   page.evaluate('t=>Overlay.seek(t)',i/a.fps);page.screenshot(path=str(dest/f'{i:04d}.png'),omit_background=True)
  audit=page.evaluate('Overlay.audit()');print('  audit=',audit);page.close()
 b.close()
