#!/usr/bin/env node
/* ==========================================================================
   motion-overlays — captura frame a frame con alfa
   Requiere: npm i -D puppeteer   (en la carpeta del proyecto)

   Uso:
     node capture.mjs 01_dependencia.html
     node capture.mjs 01_dependencia.html --fps 30
     node capture.mjs 01_dependencia.html --bg green      (para croma, sin alfa)
     node capture.mjs --all                                (todos los NN_*.html)

   Salida: frames/<nombre>/0000.png … (1920x1080, fondo transparente)
   Después, ffmpeg (ver references/render-capcut.md).
   ========================================================================== */
import puppeteer from 'puppeteer';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const argv = process.argv.slice(2);
const flag = (n, d = null) => {
  const i = argv.indexOf('--' + n);
  return i === -1 ? d : (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : true);
};

const fps = Number(flag('fps', 60));
const bg = flag('bg', null);                 // green | magenta → sin alfa
const outRoot = String(flag('out', 'frames'));
const all = argv.includes('--all');

let files = argv.filter(a => a.endsWith('.html') && !a.startsWith('--'));
if (all) files = fs.readdirSync('.').filter(f => /^\d{2}[-_].+\.html$/.test(f) && !f.startsWith('00'));
if (!files.length) {
  console.error('Indica un archivo .html o usa --all');
  process.exit(1);
}

const browser = await puppeteer.launch({
  headless: 'new',
  args: ['--hide-scrollbars', '--force-color-profile=srgb', '--allow-file-access-from-files']
});

for (const file of files) {
  const name = path.basename(file, '.html');
  const dir = path.join(outRoot, name);
  fs.mkdirSync(dir, { recursive: true });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });

  const url = pathToFileURL(path.resolve(file)).href +
              '?paused=1&loop=0' + (bg && bg !== true ? '&bg=' + bg : '');
  await page.goto(url, { waitUntil: 'networkidle0' });
  await page.waitForFunction('window.Overlay && window.Overlay.duration > 0', { timeout: 15000 });

  const duration = await page.evaluate(() => window.Overlay.duration);
  const total = Math.round(duration * fps) + 1;
  process.stdout.write(`${name}: ${duration.toFixed(2)}s · ${total} frames @ ${fps}fps\n`);

  for (let i = 0; i < total; i++) {
    await page.evaluate(t => window.Overlay.seek(t), i / fps);
    await page.evaluate(() => new Promise(r =>
      requestAnimationFrame(() => requestAnimationFrame(r))));
    await page.screenshot({
      path: path.join(dir, String(i).padStart(4, '0') + '.png'),
      omitBackground: !bg
    });
    if (i % 30 === 0) process.stdout.write(`  ${i}/${total}\r`);
  }
  await page.close();

  console.log(`  → ${dir}`);
  console.log(`  ffmpeg -framerate ${fps} -i ${dir}/%04d.png -c:v prores_ks ` +
              `-profile:v 4444 -pix_fmt yuva444p10le ${name}.mov`);
}

await browser.close();
