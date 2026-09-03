# -*- coding: utf-8 -*-
"""Libreria de stickers: SVG en el disco, PNG con alfa para la timeline.

Por que SVG y no PNG dibujados a mano: los stickers hay que poder retocarlos.
Este modulo escribe un `.svg` por sticker en `stickers/` (editable, o sustituible
por uno propio) y los rasteriza a `assets/stickers/*.png` con Chrome, que es el
unico rasterizador de SVG disponible en este equipo — ni ffmpeg ni PIL leen SVG,
comprobado. Es el mismo Chrome que usa `motion-overlays` para capturar.

Los colores y los grosores salen de los tokens de `motion-overlays`, para que un
sticker y un overlay puestos en el mismo plano parezcan de la misma familia. La
diferencia es que estos llevan **sombra oscura**: los overlays se disenaron para
ir sobre video oscuro, y un sticker tiene que leerse tambien sobre una pared
blanca a mediodia.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import util

SKILL = util.skill_root()
SRC_DIR = SKILL / "stickers"
OUT_DIR = SKILL / "assets" / "stickers"

# Tokens de motion-overlays 1.2.1.
C = {
    "line": "#FFFFFF",
    "ink": "#0B1220",
    "accent": "#5B8CFF",
    "accent2": "#8B7CFF",
    "ok": "#2FD08A",
    "warn": "#FFB020",
    "bad": "#FF5D5D",
    "gold": "#F2C14E",
}

VIEW = 360          # lienzo de trabajo de cada sticker
RENDER_SCALE = 3    # 1080 px de lado: sobra para un lienzo de 1080 de ancho

CHROME_CANDIDATES = [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    return shutil.which("chrome") or shutil.which("chromium") or None


# ------------------------------------------------------------ piezas

def _shadow(dy=6, blur=10, op=0.55):
    return ("filter: drop-shadow(0 %dpx %dpx rgba(11,18,32,%.2f));"
            % (dy, blur, op))


def _flecha(rot, color):
    """Flecha gruesa. `rot` en grados, 0 = hacia arriba."""
    return """<g transform="rotate(%d 180 180)">
  <path d="M180 300 L180 96" stroke="%s" stroke-width="34"
        stroke-linecap="round" fill="none"/>
  <path d="M92 168 L180 76 L268 168" stroke="%s" stroke-width="34"
        stroke-linejoin="round" stroke-linecap="round" fill="none"/>
</g>""" % (rot, color, color)


def _pastilla(texto, fill, tinta, ancho=None):
    n = max(3, len(texto))
    w = ancho or min(336, 74 + n * 30)
    x = (360 - w) / 2
    return """<rect x="%.0f" y="132" width="%.0f" height="96" rx="48"
        fill="%s"/>
  <text x="180" y="196" text-anchor="middle" fill="%s"
        font-family="Inter Black, Arial Black, Arial, sans-serif"
        font-size="52" font-weight="900" letter-spacing="1.5">%s</text>""" % (
        x, w, fill, tinta, texto)


def _circulo_num(n, color):
    return """<circle cx="180" cy="180" r="128" fill="%s"/>
  <text x="180" y="230" text-anchor="middle" fill="%s"
        font-family="Inter Black, Arial Black, Arial, sans-serif"
        font-size="150" font-weight="900">%s</text>""" % (color, C["ink"], n)


# Cada entrada: (nombre, cuerpo svg, sombra opcional). El cuerpo se dibuja en un
# lienzo de 360x360 con el origen arriba a la izquierda.
def catalog():
    a, ok, bad, warn, gold, line, ink = (C["accent"], C["ok"], C["bad"],
                                         C["warn"], C["gold"], C["line"], C["ink"])
    items = [
        ("flecha-arriba", _flecha(0, line), "flechas"),
        ("flecha-abajo", _flecha(180, line), "flechas"),
        ("flecha-derecha", _flecha(90, line), "flechas"),
        ("flecha-izquierda", _flecha(270, line), "flechas"),
        ("flecha-abajo-azul", _flecha(180, a), "flechas"),
        ("flecha-curva", """<path d="M74 96 C 74 232, 168 288, 268 268"
     stroke="%s" stroke-width="26" fill="none" stroke-linecap="round"/>
  <path d="M214 232 L280 268 L226 314" stroke="%s" stroke-width="26"
     fill="none" stroke-linejoin="round" stroke-linecap="round"/>""" % (line, line),
         "flechas"),
        ("resalte-circulo", """<ellipse cx="180" cy="180" rx="150" ry="112"
     transform="rotate(-8 180 180)" stroke="%s" stroke-width="16"
     fill="none" stroke-linecap="round" stroke-dasharray="640 90"/>""" % warn,
         "resaltes"),
        ("resalte-doble", """<ellipse cx="180" cy="180" rx="152" ry="110"
     transform="rotate(-7 180 180)" stroke="%s" stroke-width="13" fill="none"
     stroke-linecap="round" stroke-dasharray="600 120"/>
  <ellipse cx="180" cy="180" rx="140" ry="99" transform="rotate(4 180 180)"
     stroke="%s" stroke-width="9" fill="none" stroke-linecap="round"
     stroke-dasharray="520 160" opacity=".75"/>""" % (a, a), "resaltes"),
        ("subrayado", """<path d="M28 208 C 120 176, 250 176, 332 200"
     stroke="%s" stroke-width="26" fill="none" stroke-linecap="round"/>""" % warn,
         "resaltes"),
        ("corchete", """<path d="M244 44 L120 44 L120 316 L244 316"
     stroke="%s" stroke-width="22" fill="none" stroke-linecap="round"
     stroke-linejoin="round"/>""" % line, "resaltes"),
        ("check", """<circle cx="180" cy="180" r="130" fill="%s"/>
  <path d="M112 184 L162 234 L252 132" stroke="%s" stroke-width="30"
     fill="none" stroke-linecap="round" stroke-linejoin="round"/>""" % (ok, ink),
         "estado"),
        ("cruz", """<circle cx="180" cy="180" r="130" fill="%s"/>
  <path d="M124 124 L236 236 M236 124 L124 236" stroke="%s" stroke-width="30"
     fill="none" stroke-linecap="round"/>""" % (bad, ink), "estado"),
        ("exclamacion", """<path d="M180 40 L318 300 L42 300 Z" fill="%s"/>
  <path d="M180 138 L180 216" stroke="%s" stroke-width="26"
     stroke-linecap="round"/>
  <circle cx="180" cy="258" r="15" fill="%s"/>""" % (warn, ink, ink), "estado"),
        ("interrogacion", """<circle cx="180" cy="180" r="130" fill="%s"/>
  <text x="180" y="248" text-anchor="middle" fill="%s"
     font-family="Inter Black, Arial Black, Arial, sans-serif"
     font-size="176" font-weight="900">?</text>""" % (a, ink), "estado"),
        ("num-1", _circulo_num(1, line), "numeros"),
        ("num-2", _circulo_num(2, line), "numeros"),
        ("num-3", _circulo_num(3, line), "numeros"),
        ("num-1-azul", _circulo_num(1, a), "numeros"),
        ("num-2-azul", _circulo_num(2, a), "numeros"),
        ("num-3-azul", _circulo_num(3, a), "numeros"),
        ("etiqueta-nuevo", _pastilla("NUEVO", a, ink), "etiquetas"),
        ("etiqueta-ojo", _pastilla("OJO", warn, ink), "etiquetas"),
        ("etiqueta-tip", _pastilla("TIP", ok, ink), "etiquetas"),
        ("etiqueta-gratis", _pastilla("GRATIS", gold, ink), "etiquetas"),
        ("etiqueta-clave", _pastilla("CLAVE", line, ink), "etiquetas"),
        ("etiqueta-paso-1", _pastilla("PASO 1", line, ink), "etiquetas"),
        ("etiqueta-paso-2", _pastilla("PASO 2", line, ink), "etiquetas"),
        ("etiqueta-paso-3", _pastilla("PASO 3", line, ink), "etiquetas"),
        ("bocadillo", """<path d="M40 60 h280 a24 24 0 0 1 24 24 v150
     a24 24 0 0 1 -24 24 h-142 l-70 58 v-58 h-68 a24 24 0 0 1 -24 -24 v-150
     a24 24 0 0 1 24 -24 z" fill="%s"/>
  <circle cx="122" cy="158" r="15" fill="%s"/>
  <circle cx="180" cy="158" r="15" fill="%s"/>
  <circle cx="238" cy="158" r="15" fill="%s"/>""" % (line, ink, ink, ink),
         "otros"),
        ("nota", """<rect x="46" y="52" width="268" height="240" rx="14"
     fill="%s"/>
  <path d="M84 118 h180 M84 166 h180 M84 214 h116" stroke="%s"
     stroke-width="14" stroke-linecap="round" opacity=".35"/>""" % (gold, ink),
         "otros"),
        ("foco", """<path d="M180 62 a86 86 0 0 1 52 154 v28 h-104 v-28
     a86 86 0 0 1 52 -154 z" fill="%s"/>
  <path d="M140 268 h80 M148 300 h64" stroke="%s" stroke-width="20"
     stroke-linecap="round"/>""" % (gold, gold), "otros"),
        ("rayo", """<path d="M206 34 L104 196 h68 L146 326 L256 152 h-70 z"
     fill="%s"/>""" % warn, "otros"),
        ("fuego", """<path d="M180 30 C 236 106, 286 130, 286 208
     a106 106 0 0 1 -212 0 C 74 152, 128 148, 148 96 C 168 130, 154 156, 180 30 z"
     fill="%s"/>
  <path d="M180 168 C 206 202, 216 212, 216 236 a36 36 0 0 1 -72 0
     C 144 214, 162 200, 180 168 z" fill="%s"/>""" % (bad, gold), "otros"),
        ("estrella", """<path d="M180 40 L216 140 L322 140 L236 202
     L268 306 L180 242 L92 306 L124 202 L38 140 L144 140 z" fill="%s"/>"""
         % gold, "otros"),
        ("reloj", """<circle cx="180" cy="180" r="126" fill="none" stroke="%s"
     stroke-width="24"/>
  <path d="M180 106 L180 184 L238 214" stroke="%s" stroke-width="24"
     fill="none" stroke-linecap="round" stroke-linejoin="round"/>""" % (line, line),
         "otros"),
        ("moneda", """<circle cx="180" cy="180" r="126" fill="%s"/>
  <text x="180" y="238" text-anchor="middle" fill="%s"
     font-family="Inter Black, Arial Black, Arial, sans-serif"
     font-size="150" font-weight="900">$</text>""" % (gold, ink), "otros"),
        ("clic", """<path d="M116 82 L116 262 L160 220 L192 300 L232 282
     L200 204 L262 196 z" fill="%s" stroke="%s" stroke-width="14"
     stroke-linejoin="round"/>""" % (line, ink), "otros"),
        ("sube", """<path d="M46 268 L138 176 L196 234 L316 114" stroke="%s"
     stroke-width="26" fill="none" stroke-linecap="round"
     stroke-linejoin="round"/>
  <path d="M244 108 L322 108 L322 186" stroke="%s" stroke-width="26"
     fill="none" stroke-linecap="round" stroke-linejoin="round"/>""" % (ok, ok),
         "otros"),
        ("mas", """<path d="M180 84 L180 276 M84 180 L276 180" stroke="%s"
     stroke-width="34" stroke-linecap="round"/>""" % line, "otros"),
        ("igual", """<path d="M76 146 h208 M76 214 h208" stroke="%s"
     stroke-width="34" stroke-linecap="round"/>""" % line, "otros"),
        ("puntos-3", """<circle cx="72" cy="180" r="26" fill="%s"/>
  <circle cx="180" cy="180" r="26" fill="%s"/>
  <circle cx="288" cy="180" r="26" fill="%s"/>""" % (line, line, a), "otros"),
    ]
    return [{"name": n, "body": b, "group": g} for n, b, g in items]


def svg_text(body):
    return """<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"
     viewBox="0 0 %d %d">
<g style="%s">
  %s
</g>
</svg>
""" % (VIEW, VIEW, VIEW, VIEW, _shadow(), body)


def write_svgs(force=False):
    """Escribe los .svg del catalogo. No pisa uno editado a mano salvo force."""
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    written, kept = [], []
    for s in catalog():
        f = SRC_DIR / ("%s.svg" % s["name"])
        if f.exists() and not force:
            kept.append(f.name)
            continue
        f.write_text(svg_text(s["body"]), encoding="utf-8")
        written.append(f.name)
    manifest = {s["name"]: s["group"] for s in catalog()}
    util.write_json(SRC_DIR / "grupos.json", manifest)
    return written, kept


# ------------------------------------------------------------ rasterizado

_PAGE = """<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;background:transparent}
img{display:block;width:%dpx;height:%dpx}</style>
<img id="i" src="%s">
<script>window.__listo = new Promise(r => {
  const i = document.getElementById('i');
  if (i.complete) r(true); else { i.onload = () => r(true); i.onerror = () => r(false); }
});</script>
"""


def rasterize(svgs, out_dir=None, scale=RENDER_SCALE, force=False, chrome=None):
    """SVG -> PNG con alfa, todos en una sola instancia de Chrome."""
    out_dir = Path(out_dir or OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    pend = []
    for svg in svgs:
        png = out_dir / (Path(svg).stem + ".png")
        if png.exists() and not force and png.stat().st_mtime >= Path(svg).stat().st_mtime:
            continue
        pend.append((Path(svg), png))
    if not pend:
        return []

    exe = chrome or find_chrome()
    if not exe:
        raise RuntimeError("no encuentro Chrome ni Edge para rasterizar los SVG")
    side = int(VIEW * scale)
    tmp = out_dir / "_tmp"
    tmp.mkdir(exist_ok=True)
    done = []
    for svg, png in pend:
        html = tmp / (svg.stem + ".html")
        html.write_text(_PAGE % (VIEW, VIEW, svg.resolve().as_uri()),
                        encoding="utf-8")
        cmd = [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--hide-scrollbars", "--force-color-profile=srgb",
               "--allow-file-access-from-files",
               "--default-background-color=00000000",
               "--force-device-scale-factor=%d" % int(scale),
               "--window-size=%d,%d" % (VIEW, VIEW),
               "--screenshot=%s" % png.resolve(),
               "--user-data-dir=%s" % (tmp / "prof").resolve(),
               html.resolve().as_uri()]
        subprocess.run(cmd, capture_output=True)
        if png.exists() and png.stat().st_size > 200:
            done.append({"name": png.stem, "path": str(png), "side": side})
    shutil.rmtree(tmp, ignore_errors=True)
    return done


def build(force=False, scale=RENDER_SCALE, on_step=None):
    """Escribe los SVG que falten y rasteriza lo que haga falta."""
    written, kept = write_svgs(force=force)
    svgs = sorted(SRC_DIR.glob("*.svg"))
    if on_step:
        on_step("%d svg (%d nuevos), rasterizando…" % (len(svgs), len(written)))
    pngs = rasterize(svgs, force=force, scale=scale)
    return {"svg_dir": str(SRC_DIR), "png_dir": str(OUT_DIR),
            "svg": len(svgs), "nuevos": written, "conservados": len(kept),
            "rasterizados": [p["name"] for p in pngs],
            "grupos": json.loads((SRC_DIR / "grupos.json").read_text(encoding="utf-8"))}
