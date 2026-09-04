"""Build reproducible desde una venv limpia; sólo empaqueta una lista permitida."""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2.4.1'
FFMPEG_VERSION = '8.0.1'


def make_icon():
    from PIL import Image, ImageDraw
    image = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 248, 248), radius=56, fill='#101827')
    draw.polygon([(48, 60), (95, 60), (129, 156), (168, 60), (211, 60), (150, 204), (107, 204)], fill='#729bff')
    draw.polygon([(157, 138), (197, 162), (157, 187)], fill='#91efd3')
    icon = ROOT / 'desktop/videria.ico'
    image.save(icon, sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    return icon


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ffmpeg-dir', required=True, type=Path, help='bin con ffmpeg.exe y ffprobe.exe, junto a LICENSE y README.txt en su padre')
    args = parser.parse_args()
    ffbin = args.ffmpeg_dir.resolve()
    for path in (ffbin/'ffmpeg.exe', ffbin/'ffprobe.exe', ffbin.parent/'LICENSE', ffbin.parent/'README.txt'):
        if not path.is_file():
            raise SystemExit('Falta dependencia o licencia: ' + str(path))
    version = subprocess.check_output([str(ffbin/'ffmpeg.exe'), '-version'], text=True)
    if not version.startswith('ffmpeg version ' + FFMPEG_VERSION + '-'):
        raise SystemExit('Usa el build FFmpeg 8.0.1 probado con NVENC; builds nuevos pueden exigir otro driver.')
    icon = make_icon()
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
               '--name', 'Videria', '--icon', str(icon), '--paths', str(ROOT/'desktop'),
               '--paths', str(ROOT/'skills/video-cut/scripts'), '--collect-all', 'webview',
               '--hidden-import', 'webview.platforms.edgechromium', '--hidden-import', 'webview.platforms.winforms']
    for excluded in ('PyQt5','PyQt6','PySide2','PySide6','qtpy','gi','torch','faster_whisper','pytest','IPython'):
        command += ['--exclude-module', excluded]
    for source, destination in [
        ('desktop/ui','desktop/ui'),('desktop/videria.ico','desktop'),('docs','docs'),
        ('skills/video-cut/studio','skills/video-cut/studio'),
        ('skills/video-cut/editor','skills/video-cut/editor'),
        ('skills/video-cut/assets','skills/video-cut/assets'),
        ('skills/video-cut/templates','skills/video-cut/templates'),
        ('desktop/THIRD-PARTY.md','licenses'),
    ]:
        command += ['--add-data', str(ROOT/source) + os.pathsep + destination]
    for name in ('ffmpeg.exe','ffprobe.exe'):
        command += ['--add-binary', str(ffbin/name) + os.pathsep + 'tools']
    for name in ('LICENSE','README.txt'):
        command += ['--add-data', str(ffbin.parent/name) + os.pathsep + 'licenses/ffmpeg']
    command += [str(ROOT/'desktop/main.py')]
    subprocess.run(command, cwd=ROOT, check=True)
    # Incluir avisos/licencias de las distribuciones Python utilizadas.
    from importlib.metadata import distributions
    licenses = ROOT/'dist/Videria/_internal/licenses/python'
    for dist in distributions():
        if dist.metadata['Name'].lower() in ('pip','pyinstaller','pyinstaller-hooks-contrib','setuptools'):
            continue
        for file in dist.files or []:
            if any(word in file.name.lower() for word in ('license','copying','notice')) and '.dist-info/' in str(file):
                target=licenses/dist.metadata['Name']/file.name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(dist.locate_file(file),target)
    archive = ROOT/f'dist/Videria-{VERSION}-Windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted((ROOT/'dist/Videria').rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(ROOT/'dist'))
        for name in ('Instalar-Videria.cmd','Instalar-Videria.ps1'):
            z.write(ROOT/'desktop'/name,name)
        z.write(ROOT/'docs/instalar-app.html','LEEME.html')
    digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    print(archive)


if __name__ == '__main__': main()
