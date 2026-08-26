# -*- coding: utf-8 -*-
"""Render final: de las dos capas a un MP4, en una sola pasada de ffmpeg.

Forma del grafo:

    por clip:  -ss/-t -> fps -> encuadre -> velocidad -> zoompan -> look
    concat  :  todos los clips, video y audio a la vez
    post    :  transiciones (efectos por ventana) -> overlays -> ASS
    audio   :  voz + musica con ducking + SFX -> amix -> loudnorm

Dos decisiones que explican el resto:

**Las transiciones no consumen tiempo.** Son efectos centrados en el corte, no
mezclas de dos clips. Un `xfade` real solapa material y acorta la secuencia, y
entonces cada texto, cada zoom y cada SFX posterior tendria que recalcularse
contra un total que cambia. Con efectos por ventana, la duracion de la
secuencia es exactamente la suma de los clips, y todo lo demas encaja sin
ceder. Es tambien lo que hacen de verdad las transiciones de TikTok: un golpe
en el corte, no un fundido.

**El zoom se hace con `zoompan` sobre material a doble resolucion.** El clip se
encuadra primero a canvas*ZMAX; asi `z=1` es el plano entero y `z=2` son
pixeles reales del original, no interpolados. Con material 4K vertical y salida
1080x1920 el zoom sale gratis en calidad.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from . import assbuild, media, studio, textlayer, util

# ------------------------------------------------------------ transiciones

# `kind`: "geom" mueve la camara (entra en el zoompan de post), "fx" es un
# filtro con ventana. `steps` es en cuantos escalones se aproxima una rampa
# cuando el filtro no acepta expresiones por fotograma.
TRANSITIONS = {
    "punch_zoom": {"label": "Punch zoom", "kind": "geom", "dur": 0.30,
                   "sfx": "3_impacto.wav",
                   "hint": "Golpe de zoom centrado en el corte."},
    "shake":      {"label": "Sacudida", "kind": "geom", "dur": 0.30,
                   "sfx": "1_whoosh.wav",
                   "hint": "Temblor de camara; el corte pasa desapercibido."},
    "whip":       {"label": "Whip pan", "kind": "geom", "dur": 0.26,
                   "sfx": "2_swish.wav",
                   "hint": "Barrido lateral con arrastre."},
    "flash":      {"label": "Flash", "kind": "fx", "dur": 0.20,
                   "sfx": "5_clic.wav", "steps": 1,
                   "hint": "Destello blanco. El mas discreto."},
    "blur":       {"label": "Desenfoque", "kind": "fx", "dur": 0.28,
                   "sfx": "4_riser.wav", "steps": 4,
                   "hint": "Pierde foco y lo recupera."},
    "glitch":     {"label": "Glitch RGB", "kind": "fx", "dur": 0.24,
                   "sfx": "6_glitch.wav", "steps": 3,
                   "hint": "Separacion de canales, aire digital."},
    "pixelize":   {"label": "Pixelado", "kind": "fx", "dur": 0.26,
                   "sfx": "8_succion.wav", "steps": 4,
                   "hint": "Se deshace en bloques y vuelve."},
    "fade_black": {"label": "Fundido a negro", "kind": "fx", "dur": 0.36,
                   "sfx": None, "steps": 1,
                   "hint": "Separa dos ideas. El unico que corta el ritmo."},
}


def transitions_catalog():
    return [dict(id=k, **v) for k, v in TRANSITIONS.items()]


# ------------------------------------------------------------ expresiones

def _ease(p, ease):
    """Curva de easing como expresion de ffmpeg. `p` ya es una expresion 0..1."""
    if ease == "hold":
        return "0"
    if ease == "in":
        return "pow(%s,2)" % p
    if ease == "out":
        return "(1-pow(1-(%s),2))" % p
    if ease == "expo":
        return "if(lte(%s,0),0,pow(2,10*((%s)-1)))" % (p, p)
    if ease == "back":
        return "(1+2.70158*pow((%s)-1,3)+1.70158*pow((%s)-1,2))" % (p, p)
    if ease == "inout":
        return "if(lt(%s,0.5),2*pow(%s,2),1-2*pow(1-(%s),2))" % (p, p, p)
    return "(%s)" % p


# En cuantos tramos rectos se hornea una curva bezier. Las expresiones de
# ffmpeg no tienen bucles, asi que no hay forma de resolver el bezier dentro
# del filtro: se muestrea la curva aqui. Con 18 puntos el error contra la
# curva exacta queda por debajo de 0,002 de escala, invisible a 30 fps.
BEZ_STEPS = 18


def _bez1(a, b, u):
    """Coordenada de un bezier cubico con extremos en 0 y 1."""
    m = 1.0 - u
    return 3.0 * m * m * u * a + 3.0 * m * u * u * b + u * u * u


def _bake_bezier(pts):
    """Parte en rectas los tramos con ease bezier. Devuelve (t, v, ease).

    Se muestrea por parametro, no por tiempo: cada punto cae exactamente sobre
    la curva y no hay que invertir nada. Con las x de las manijas dentro de
    0..1 el tiempo nunca retrocede.
    """
    out = []
    for i, pt in enumerate(pts):
        bez = studio.ease_bezier(pt[2]) if i else None
        if not bez:
            out.append(pt)
            continue
        t0, v0 = pts[i - 1][0], pts[i - 1][1]
        t1, v1 = pt[0], pt[1]
        dv = abs(v1 - v0)
        if dv < 1e-4:
            # Este canal no se mueve en el tramo: la curva no cambia nada y
            # hornearla solo engordaria el filtro. El paneo suele caer aqui.
            out.append((t1, v1, "linear"))
            continue
        x1, y1, x2, y2 = bez
        # Un salto chico no necesita 18 escalones para verse limpio.
        steps = max(6, min(BEZ_STEPS, int(round(BEZ_STEPS * dv / 0.3))))
        for s in range(1, steps + 1):
            u = s / float(steps)
            out.append((t0 + _bez1(x1, x2, u) * (t1 - t0),
                        v0 + _bez1(y1, y2, u) * (v1 - v0), "linear"))
    return out


def piecewise(kfs, key, default, tvar="it"):
    """Expresion por tramos a partir de keyframes ordenados por `t`.

    Antes del primer keyframe mantiene su valor, despues del ultimo tambien: un
    zoom nunca se va a un valor que el usuario no puso.
    """
    pts = [(float(k.get("t") or 0.0), float(k.get(key, default) if k.get(key) is not None else default),
            k.get("ease") or "inout") for k in kfs]
    pts = _bake_bezier(pts)
    if not pts:
        return "%.6f" % default
    if len(pts) == 1:
        return "%.6f" % pts[0][1]
    expr = "%.6f" % pts[-1][1]
    for i in range(len(pts) - 2, -1, -1):
        t0, v0, _e0 = pts[i]
        t1, v1, _e1 = pts[i + 1]
        ease = pts[i + 1][2]
        if t1 - t0 < 1e-6:
            continue
        p = "((%s-%.6f)/%.6f)" % (tvar, t0, t1 - t0)
        seg = "(%.6f+(%.6f)*%s)" % (v0, v1 - v0, _ease(p, ease))
        expr = "if(lt(%s,%.6f),%s,%s)" % (tvar, t1, seg, expr)
    return "if(lt(%s,%.6f),%.6f,%s)" % (tvar, pts[0][0], pts[0][1], expr)


def _tri(t0, dur, tvar="t"):
    """Envolvente triangular 0-1-0 sobre la ventana. 1 justo en el corte."""
    return "(1-abs(2*((%s)-%.4f)/%.4f-1))" % (tvar, t0, dur)


# ------------------------------------------------------------ utilidades

def _esc_path(p):
    """Ruta dentro de un argumento de filtro (Windows necesita escapar C:)."""
    s = str(p).replace("\\", "/")
    return s.replace(":", "\\:").replace("'", "\\'").replace("[", "\\[") \
            .replace("]", "\\]").replace(",", "\\,")


def _db(x):
    return "%.4f" % (10 ** (float(x) / 20.0))


def _usable_seq(item):
    """La secuencia de PNG de un overlay, si sigue estando en el disco."""
    seq = item.get("seq") or {}
    d = seq.get("dir")
    if not d:
        return None
    first = int(seq.get("first") or 0)
    if not (Path(d) / ("%04d.png" % first)).exists():
        return None
    return seq


def cover(tw, th):
    """Cadena que llena tw x th recortando lo que sobre."""
    return ("scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos,"
            "crop=%d:%d" % (tw, th, tw, th))


def contain(tw, th, bg="black"):
    return ("scale=%d:%d:force_original_aspect_ratio=decrease:flags=lanczos,"
            "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:%s" % (tw, th, tw, th, bg))


# ------------------------------------------------------------ video por clip

def clip_chain(clip, canvas, fit):
    """Filtros de un clip, de la entrada a un stream listo para concatenar."""
    W, H = int(canvas["width"]), int(canvas["height"])
    fps = float(canvas["fps"])
    cfg = clip["cfg"]
    kfs = studio.zoom_kfs(cfg)
    zooming = not studio.zoom_is_flat(kfs)
    z = studio.ZMAX if zooming else 1.0
    tw, th = int(W * z), int(H * z)
    tw -= tw % 2
    th -= th % 2

    parts = ["setpts=PTS-STARTPTS", "fps=%.4f" % fps]
    parts.append(cover(tw, th) if (cfg.get("fit") or fit) == "cover"
                 else contain(tw, th))
    if cfg.get("flip"):
        parts.append("hflip")
    spd = clip["speed"]
    if abs(spd - 1.0) > 1e-3:
        # El zoom y el texto ya estan en tiempo de salida, asi que la velocidad
        # tiene que aplicarse antes que el zoompan.
        parts.append("setpts=PTS/%.6f" % spd)
        parts.append("fps=%.4f" % fps)
    if zooming:
        zexpr = piecewise(kfs, "scale", 1.0)
        pxexpr = piecewise(kfs, "x", 0.0)
        pyexpr = piecewise(kfs, "y", 0.0)
        parts.append(
            "zoompan=z='clip(%s,1,%.3f)'"
            ":x='in_w/2-(in_w/zoom/2)+(%s)*(in_w/2-(in_w/zoom/2))'"
            ":y='in_h/2-(in_h/zoom/2)+(%s)*(in_h/2-(in_h/zoom/2))'"
            ":d=1:s=%dx%d:fps=%.4f" % (zexpr, studio.ZMAX, pxexpr, pyexpr,
                                       W, H, fps))
    look = cfg.get("look") or {}
    eqp = []
    if abs(float(look.get("brightness") or 0)) > 1e-3:
        eqp.append("brightness=%.4f" % float(look["brightness"]))
    if abs(float(look.get("contrast") or 1) - 1) > 1e-3:
        eqp.append("contrast=%.4f" % float(look["contrast"]))
    if abs(float(look.get("saturation") or 1) - 1) > 1e-3:
        eqp.append("saturation=%.4f" % float(look["saturation"]))
    if eqp:
        parts.append("eq=" + ":".join(eqp))
    temp = float(look.get("temp") or 0)
    if abs(temp) > 1e-3:
        # Positivo calienta: sube rojo y baja azul, en partes iguales.
        parts.append("colorbalance=rs=%.3f:bs=%.3f" % (temp * 0.3, -temp * 0.3))
    vig = float(look.get("vignette") or 0)
    if vig > 1e-3:
        parts.append("vignette=angle=PI/%.2f" % max(2.5, 6.0 - vig * 3.0))
    parts.append("setsar=1")
    if not zooming:
        parts.append("scale=%d:%d:flags=lanczos" % (W, H))
    return ",".join(parts)


def clip_audio_chain(clip, has_audio):
    parts = ["asetpts=PTS-STARTPTS", "aresample=48000:async=1:first_pts=0"]
    spd = clip["speed"]
    if abs(spd - 1.0) > 1e-3:
        # atempo aguanta 0.5x-2x por instancia; fuera de eso se encadena.
        left = spd
        while left > 2.0 + 1e-6:
            parts.append("atempo=2.0")
            left /= 2.0
        while left < 0.5 - 1e-6:
            parts.append("atempo=0.5")
            left /= 0.5
        if abs(left - 1.0) > 1e-3:
            parts.append("atempo=%.6f" % left)
    cfg = clip["cfg"]
    if cfg.get("mute") or not has_audio:
        parts.append("volume=0")
    elif abs(float(cfg.get("volume") or 0)) > 1e-3:
        parts.append("volume=%s" % _db(cfg["volume"]))
    parts.append("aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo")
    return ",".join(parts)


# ------------------------------------------------------------ transiciones

GEOM_ZMAX = 1.6


def geom_stage(trans, canvas):
    """Un solo zoompan que resuelve punch zoom, sacudida y whip.

    Se anade solo si hay alguna transicion geometrica: zoompan reescala todos
    los fotogramas, asi que ponerlo cuando no hace falta seria pagar calidad
    por nada. El reloj de zoompan es `it`, no `t`.
    """
    W, H = int(canvas["width"]), int(canvas["height"])
    fps = float(canvas["fps"])
    tv = "it"
    zt, xt, yt = [], [], []
    for tr in trans:
        spec = TRANSITIONS.get(tr["type"])
        if not spec or spec["kind"] != "geom":
            continue
        t0, t1, d = tr["t0"], tr["t1"], tr["dur"]
        s = max(0.1, min(2.0, tr["strength"]))
        env = _tri(t0, d, tv)
        win = "between(%s,%.4f,%.4f)" % (tv, t0, t1)
        if tr["type"] == "punch_zoom":
            zt.append("%s*%.4f*%s" % (win, 0.22 * s, env))
        elif tr["type"] == "shake":
            zt.append("%s*%.4f*%s" % (win, 0.09 * s, env))
            xt.append("%s*%.4f*%s*sin((%s-%.4f)*118)"
                      % (win, 0.55 * s, env, tv, t0))
            yt.append("%s*%.4f*%s*sin((%s-%.4f)*151)"
                      % (win, 0.45 * s, env, tv, t0))
        elif tr["type"] == "whip":
            tc, half = tr["t"], max(1e-3, d / 2.0)
            # Rampa rapida de zoom: sin margen no hay sitio donde barrer.
            zt.append("%s*%.4f*min(1,6*min(%s-%.4f,%.4f-%s)/%.4f)"
                      % (win, 0.28 * s, tv, t0, t1, tv, d))
            xt.append("between(%s,%.4f,%.4f)*%.4f*((%s-%.4f)/%.4f)"
                      % (tv, t0, tc, 0.95 * s, tv, t0, half))
            xt.append("between(%s,%.4f,%.4f)*%.4f*(1-(%s-%.4f)/%.4f)"
                      % (tv, tc, t1, -0.95 * s, tv, tc, half))
    if not (zt or xt or yt):
        return None
    z = "1" + ("+" + "+".join(zt) if zt else "")
    px = "+".join(xt) if xt else "0"
    py = "+".join(yt) if yt else "0"
    return ("zoompan=z='clip(%s,1,%.3f)'"
            ":x='in_w/2-(in_w/zoom/2)+(%s)*(in_w/2-(in_w/zoom/2))'"
            ":y='in_h/2-(in_h/zoom/2)+(%s)*(in_h/2-(in_h/zoom/2))'"
            ":d=1:s=%dx%d:fps=%.4f"
            % (z, GEOM_ZMAX, px, py, W, H, fps))


def fx_stages(trans, canvas):
    """Filtros por ventana, agrupados por valor para no encadenar de mas."""
    fps = float(canvas["fps"])
    frame = 1.0 / max(1.0, fps)
    buckets = {}      # (filtro, valor) -> [ventanas]
    bright, desat = [], []

    for tr in trans:
        spec = TRANSITIONS.get(tr["type"])
        if not spec or spec["kind"] != "fx":
            continue
        t0, t1, d = tr["t0"], tr["t1"], tr["dur"]
        s = max(0.1, min(2.0, tr["strength"]))
        steps = int(spec.get("steps") or 1)

        if tr["type"] == "flash":
            bright.append("between(t,%.4f,%.4f)*%.3f*%s"
                          % (t0, t1, 0.95 * s, _tri(t0, d)))
            continue
        if tr["type"] == "fade_black":
            # NO con el filtro `fade`: `fade=t=in:st=X` deja en negro TODO lo
            # anterior a X, no solo su ventana, asi que un fundido en el
            # segundo 30 apaga los primeros 30 segundos del video. Medido.
            # Con `eq` por fotograma el efecto se queda donde debe.
            win = "between(t,%.4f,%.4f)*%s" % (t0, t1, _tri(t0, d))
            bright.append("(-1)*" + win)
            desat.append(win)
            continue

        # Rampa por escalones: el filtro no acepta expresiones por fotograma,
        # asi que se aproxima con varias instancias con ventanas anidadas.
        for k in range(steps):
            lo = k / float(steps)
            hi = (k + 1) / float(steps)
            # Ventana simetrica: el escalon k cubre los tramos donde la
            # envolvente esta entre lo y hi, a la ida y a la vuelta.
            a0 = t0 + (d / 2.0) * lo
            a1 = t0 + (d / 2.0) * hi
            b0 = t1 - (d / 2.0) * hi
            b1 = t1 - (d / 2.0) * lo
            level = (lo + hi) / 2.0
            wins = ["between(t,%.4f,%.4f)" % (a0, max(a1, a0 + frame)),
                    "between(t,%.4f,%.4f)" % (min(b0, b1 - frame), b1)]
            if tr["type"] == "blur":
                val = ("gblur", "sigma=%.2f:steps=2" % (18.0 * s * level))
            elif tr["type"] == "pixelize":
                px = max(2, int(round(2 + 46 * s * level)))
                val = ("pixelize", "w=%d:h=%d" % (px, px))
            elif tr["type"] == "glitch":
                sh = max(1, int(round(26 * s * level)))
                val = ("rgbashift", "rh=%d:bh=-%d:gv=%d:edge=smear"
                       % (sh, sh, sh // 2))
            else:
                continue
            buckets.setdefault(val, []).extend(wins)

    out = []
    if bright or desat:
        args = ["brightness='%s'" % ("+".join(bright) if bright else "0")]
        if desat:
            # Bajar solo el brillo dejaria la crominancia intacta y el negro
            # saldria teñido; hay que apagar tambien la saturacion.
            args.append("saturation='max(0,1-(%s))'" % "+".join(desat))
        out.append("eq=" + ":".join(args) + ":eval=frame")
    for (name, args), wins in buckets.items():
        out.append("%s=%s:enable='%s'" % (name, args, "+".join(wins)))
    return out


# ------------------------------------------------------------ grafo completo

class Job:
    """Todo lo que hace falta para lanzar un render, ya resuelto."""

    def __init__(self, project, tl, project_dir, out_path, draft=False,
                 use_proxy=None, range_=None):
        self.project = project
        self.tl = tl
        self.dir = Path(project_dir)
        self.out = Path(out_path)
        self.draft = draft
        self.res = studio.resolve(project, tl)
        self.canvas = dict(self.res["canvas"])
        self.rcfg = dict(studio.DEFAULT_RENDER)
        self.rcfg.update(tl.get("render") or {})
        self.range = range_
        self.use_proxy = (draft if use_proxy is None else use_proxy)
        if draft:
            h = int(self.rcfg.get("draft_height") or 720)
            if self.canvas["height"] > h:
                k = h / float(self.canvas["height"])
                self.canvas["width"] = int(self.canvas["width"] * k) // 2 * 2
                self.canvas["height"] = h // 2 * 2
        self.warnings = []
        self.clips = self._clips()
        self.total = round(sum(c["dur"] for c in self.clips), 4)

    def _clips(self):
        clips = [dict(c) for c in self.res["clips"]]
        if not self.range:
            return clips
        a, b = self.range
        out = []
        for c in clips:
            if c["t1"] <= a or c["t0"] >= b:
                continue
            c = dict(c)
            lo = max(a, c["t0"])
            hi = min(b, c["t1"])
            c["in"] = round(c["in"] + (lo - c["t0"]) * c["speed"], 4)
            c["out"] = round(c["out"] - (c["t1"] - hi) * c["speed"], 4)
            c["dur"] = round(hi - lo, 4)
            c["t0"], c["t1"] = round(lo - a, 4), round(hi - a, 4)
            out.append(c)
        return out

    # ---------------------------------------------------- entradas

    def source_path(self, sid):
        src = next((s for s in self.project["sources"] if s["id"] == sid), None)
        if not src:
            raise RuntimeError("falta el archivo %s" % sid)
        if self.use_proxy and src.get("proxy") and Path(src["proxy"]).exists():
            return src["proxy"], src
        return src["path"], src

    def build(self, ass_path=None):
        """Devuelve (cmd, info). No lanza nada."""
        W, H = int(self.canvas["width"]), int(self.canvas["height"])
        fps = float(self.canvas["fps"])
        fit = self.rcfg.get("fit") or "cover"
        cmd = [util.FFMPEG, "-hide_banner", "-y", "-nostdin"]
        graph = []
        vlabels, alabels = [], []
        idx = 0

        for c in self.clips:
            path, src = self.source_path(c["source"])
            if not Path(path).exists():
                raise RuntimeError("no existe %s" % path)
            src_dur = c["dur"] * c["speed"]
            cmd += ["-ss", "%.4f" % c["in"], "-t", "%.4f" % src_dur, "-i", str(path)]
            graph.append("[%d:v]%s[v%d]" % (idx, clip_chain(c, self.canvas, fit), idx))
            has_a = bool(src.get("has_audio"))
            if has_a:
                graph.append("[%d:a]%s[a%d]" % (idx, clip_audio_chain(c, True), idx))
            else:
                # Silencio del mismo largo: concat exige que todos los clips
                # traigan pista de audio.
                graph.append("aevalsrc=0:d=%.4f:s=48000:c=stereo,"
                             "aformat=sample_fmts=fltp:channel_layouts=stereo[a%d]"
                             % (c["dur"], idx))
            vlabels.append("[v%d]" % idx)
            alabels.append("[a%d]" % idx)
            idx += 1

        if not vlabels:
            raise RuntimeError("no hay clips activos: nada que renderizar")

        if len(vlabels) == 1:
            graph.append("%snull[vc]" % vlabels[0])
            graph.append("%sanull[ac]" % alabels[0])
        else:
            pairs = "".join(v + a for v, a in zip(vlabels, alabels))
            graph.append("%sconcat=n=%d:v=1:a=1[vc][ac]"
                         % (pairs, len(vlabels)))

        vcur = "vc"
        trans = [t for t in self.res["transitions"]
                 if not self.range or (self.range[0] <= t["t"] <= self.range[1])]
        if self.range:
            trans = [dict(t, t=t["t"] - self.range[0],
                          t0=t["t0"] - self.range[0], t1=t["t1"] - self.range[0])
                     for t in trans]

        geom = geom_stage(trans, self.canvas)
        if geom:
            graph.append("[%s]%s[vg]" % (vcur, geom))
            vcur = "vg"
        fx = fx_stages(trans, self.canvas)
        if fx:
            graph.append("[%s]%s[vfx]" % (vcur, ",".join(fx)))
            vcur = "vfx"

        # ------------------------------------------------ overlays
        ovl = [it for it in self.res["items"] if it.get("track_kind") == "overlay"]
        for n, it in enumerate(ovl):
            src = it.get("src")
            if not src or not Path(src).exists():
                self.warnings.append("overlay sin archivo: %s" % (src or it.get("id")))
                continue
            t = it["t"] - (self.range[0] if self.range else 0.0)
            if t + it["dur"] <= 0 or (self.total and t >= self.total):
                continue
            seq = _usable_seq(it)
            if seq:
                # La secuencia de PNG manda sobre el WebM: ffmpeg escribe alfa
                # en WebM pero no lo lee, y el overlay saldria sobre un
                # rectangulo negro.
                cmd += ["-framerate", "%.4f" % float(seq.get("fps") or 30.0),
                        "-start_number", str(int(seq.get("first") or 0)),
                        "-i", str(Path(seq["dir"]) / "%04d.png")]
            else:
                if it.get("seq"):
                    self.warnings.append(
                        "%s: falta la secuencia de PNG, uso el WebM y se pierde "
                        "la transparencia" % (it.get("id") or src))
                is_img = Path(src).suffix.lower() in (".png", ".jpg", ".jpeg",
                                                      ".webp", ".bmp")
                if is_img:
                    cmd += ["-loop", "1", "-t", "%.4f" % it["dur"], "-i", str(src)]
                elif it.get("loop"):
                    cmd += ["-stream_loop", "-1", "-t", "%.4f" % it["dur"],
                            "-i", str(src)]
                else:
                    cmd += ["-i", str(src)]
            sc = float(it.get("scale") or 1.0)
            chain = ["format=yuva420p", "setpts=PTS-STARTPTS+%.4f/TB" % max(0.0, t)]
            if abs(sc - 1.0) > 1e-3:
                chain.append("scale=iw*%.4f:ih*%.4f:flags=lanczos" % (sc, sc))
            op = float(it.get("opacity") if it.get("opacity") is not None else 1.0)
            if op < 0.999:
                chain.append("colorchannelmixer=aa=%.3f" % max(0.0, op))
            fade = float(it.get("fade") or 0.0)
            if fade > 0.01:
                chain.append("fade=t=in:st=%.4f:d=%.4f:alpha=1" % (max(0.0, t), fade))
                chain.append("fade=t=out:st=%.4f:d=%.4f:alpha=1"
                             % (max(0.0, t + it["dur"] - fade), fade))
            graph.append("[%d:v]%s[o%d]" % (idx, ",".join(chain), n))
            xf = float(it.get("x") if it.get("x") is not None else 0.5)
            yf = float(it.get("y") if it.get("y") is not None else 0.5)
            graph.append("[%s][o%d]overlay=x='main_w*%.4f-overlay_w/2'"
                         ":y='main_h*%.4f-overlay_h/2':eof_action=pass"
                         ":enable='between(t,%.4f,%.4f)'[vo%d]"
                         % (vcur, n, xf, yf, max(0.0, t), t + it["dur"], n))
            vcur = "vo%d" % n
            idx += 1

        # ------------------------------------------------ texto
        if ass_path and Path(ass_path).exists():
            fdir = self.font_dir()
            graph.append("[%s]ass=filename='%s':fontsdir='%s'[vt]"
                         % (vcur, _esc_path(ass_path), _esc_path(fdir)))
            vcur = "vt"

        graph.append("[%s]format=yuv420p[vout]" % vcur)

        # ------------------------------------------------ audio
        acur = "ac"
        auds = [it for it in self.res["items"] if it.get("track_kind") == "audio"]
        mixes, ducked = [], []
        for n, it in enumerate(auds):
            src = it.get("src")
            if not src or not Path(src).exists():
                self.warnings.append("audio sin archivo: %s" % (src or it.get("id")))
                continue
            t = it["t"] - (self.range[0] if self.range else 0.0)
            if t + it["dur"] <= 0:
                continue
            if it.get("loop"):
                cmd += ["-stream_loop", "-1"]
            cmd += ["-ss", "%.4f" % float(it.get("in") or 0.0),
                    "-t", "%.4f" % it["dur"], "-i", str(src)]
            gain = float(it.get("gain") or 0.0) + float(it.get("track_gain") or 0.0)
            ch = ["asetpts=PTS-STARTPTS", "aresample=48000",
                  "aformat=sample_fmts=fltp:channel_layouts=stereo"]
            fi = float(it.get("fade_in") or 0.0)
            fo = float(it.get("fade_out") or 0.0)
            if fi > 0.01:
                ch.append("afade=t=in:st=0:d=%.4f" % fi)
            if fo > 0.01:
                ch.append("afade=t=out:st=%.4f:d=%.4f" % (max(0.0, it["dur"] - fo), fo))
            if abs(gain) > 1e-3:
                ch.append("volume=%s" % _db(gain))
            ch.append("adelay=%d|%d" % (int(max(0.0, t) * 1000), int(max(0.0, t) * 1000)))
            ch.append("apad")
            graph.append("[%d:a]%s,atrim=0:%.4f[m%d]"
                         % (idx, ",".join(ch), self.total, n))
            (ducked if it.get("duck") else mixes).append("[m%d]" % n)
            idx += 1

        if ducked:
            # El ducking necesita la voz dos veces: una como referencia del
            # compresor y otra en la mezcla.
            graph.append("[ac]asplit=2[acmix][acref]")
            if len(ducked) == 1:
                graph.append("%sanull[duckin]" % ducked[0])
            else:
                graph.append("%samix=inputs=%d:normalize=0[duckin]"
                             % ("".join(ducked), len(ducked)))
            graph.append("[duckin][acref]sidechaincompress=threshold=0.055"
                         ":ratio=9:attack=12:release=340:makeup=1[ducked]")
            mixes.append("[ducked]")
            acur = "acmix"
        if mixes:
            graph.append("[%s]%samix=inputs=%d:normalize=0:dropout_transition=0"
                         ":duration=first[amx]" % (acur, "".join(mixes),
                                                   len(mixes) + 1))
            acur = "amx"
        apost = ["aresample=48000"]
        if self.rcfg.get("loudnorm") and not self.draft:
            apost.append("loudnorm=I=%.1f:TP=-1.5:LRA=11"
                         % float(self.rcfg.get("loudnorm_i") or -14.0))
        apost.append("aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo")
        graph.append("[%s]%s[aout]" % (acur, ",".join(apost)))

        cmd += ["-filter_complex", ";".join(graph),
                "-map", "[vout]", "-map", "[aout]"]
        cmd += self.encoder_args()
        cmd += ["-r", "%.4f" % fps, "-t", "%.4f" % self.total,
                "-movflags", "+faststart", str(self.out)]
        return cmd, {"clips": len(self.clips), "total": self.total,
                     "canvas": self.canvas, "overlays": len(ovl),
                     "audio_items": len(auds), "transitions": len(trans),
                     "warnings": self.warnings}

    def encoder_args(self):
        q = int(self.rcfg.get("quality") or 20)
        enc = self.rcfg.get("encoder") or "auto"
        if enc == "auto":
            enc = "nvenc" if media.nvenc_available() else "x264"
        ab = self.rcfg.get("audio_bitrate") or "192k"
        if enc == "nvenc":
            preset = "p1" if self.draft else "p5"
            v = ["-c:v", "h264_nvenc", "-preset", preset, "-rc", "vbr",
                 "-cq", str(q + (6 if self.draft else 0)), "-b:v", "0",
                 "-profile:v", "high", "-bf", "2"]
        else:
            preset = "ultrafast" if self.draft else "medium"
            v = ["-c:v", "libx264", "-preset", preset,
                 "-crf", str(q + (6 if self.draft else 0)),
                 "-profile:v", "high"]
        return v + ["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", ab, "-ar", "48000"]

    def font_dir(self):
        """Copia a `cache/fonts` solo las fuentes que el ASS necesita.

        libass en Windows resuelve por DirectWrite y ve todas las del sistema;
        el fontsdir es lo que garantiza que las del proyecto (o las de
        MoneyPrinterTurbo) tambien esten disponibles con su nombre real.
        """
        dest = self.dir / "cache" / "fonts"
        dest.mkdir(parents=True, exist_ok=True)
        wanted = set()
        for st in (self.tl.get("styles") or {}).values():
            for k in ("font", "keyword_font"):
                if st.get(k):
                    wanted.add(st[k])
        for it in self.res["items"]:
            ov = it.get("override") or {}
            for k in ("font", "keyword_font"):
                if ov.get(k):
                    wanted.add(ov[k])
        for name in wanted:
            p = textlayer.find_font(name, self.dir)
            if not p:
                self.warnings.append("no encuentro la fuente %s" % name)
                continue
            tgt = dest / Path(p).name
            if not tgt.exists() or tgt.stat().st_mtime < Path(p).stat().st_mtime:
                try:
                    shutil.copy2(p, tgt)
                except OSError as exc:
                    self.warnings.append("no pude copiar %s (%s)" % (p, exc))
        return dest


# ------------------------------------------------------------ ejecucion

_PROG = re.compile(r"^(\w+)=(.*)$")


def run(cmd, total, on_progress=None, log_path=None, on_start=None):
    """Lanza ffmpeg leyendo su avance por stdout.

    El stderr va a un archivo, no a otra tuberia: leyendo las dos en serie, un
    render con muchos avisos llena el buffer de stderr y ffmpeg se queda
    bloqueado esperando que alguien lo vacie.
    """
    full = [str(c) for c in cmd]
    full = full[:1] + ["-progress", "pipe:1", "-loglevel", "error"] + full[1:]
    log = Path(log_path) if log_path else None
    errf = open(log, "w", encoding="utf-8", errors="replace") if log \
        else subprocess.PIPE
    proc = subprocess.Popen(full, stdout=subprocess.PIPE, stderr=errf,
                            encoding="utf-8", errors="replace", bufsize=1)
    if on_start:
        on_start(proc)
    last = 0.0
    for line in proc.stdout:
        m = _PROG.match(line.strip())
        if m and m.group(1) == "out_time_ms":
            try:
                last = int(m.group(2)) / 1e6
            except ValueError:
                continue
            if on_progress and total > 0:
                on_progress(min(1.0, last / total), last)
    proc.wait()
    if log:
        errf.close()
        err = log.read_text(encoding="utf-8", errors="replace").strip()
    else:
        err = (proc.stderr.read() or "").strip()
    if proc.returncode != 0:
        tail = "\n".join(err.splitlines()[-14:])
        raise RuntimeError("ffmpeg fallo (exit %d):\n%s" % (proc.returncode, tail))
    return err


def _exigir_originales(project, draft):
    """El final no puede salir de los proxies sin que nadie lo note.

    En un proyecto compartido por git, quien solo revisa tiene los proxies y
    no el material. Su render de borrador es legitimo; el final, no: saldria a
    540p estirado y solo se veria al abrir el MP4.
    """
    if draft:
        return
    sin = [s.get("name") or s.get("id") for s in project.get("sources", [])
           if s.get("tiene_original") is False]
    if sin:
        raise RuntimeError(
            "esta máquina no tiene el material original de %d clips (%s%s). "
            "El render final saldría de los proxies, a menor calidad. Usá "
            "--draft para un borrador, o hacé el final donde estén los vídeos."
            % (len(sin), ", ".join(str(x) for x in sin[:3]),
               "…" if len(sin) > 3 else ""))


def render(project, tl, project_dir, out_path, draft=False, range_=None,
           on_progress=None, on_stage=None, on_start=None):
    """Render completo. Devuelve un dict con lo que se hizo."""
    pdir = Path(project_dir)
    job = Job(project, tl, pdir, out_path, draft=draft, range_=range_)
    if on_stage:
        on_stage("texto")
    ass = pdir / "cache" / "burn.ass"
    res = dict(job.res)
    _exigir_originales(project, draft)
    res["canvas"] = job.canvas
    if range_:
        # El ASS se genera con los tiempos del tramo, no de la secuencia entera.
        # Un item que empezo antes del tramo se recorta conservando su final: si
        # solo se moviera a 0 con su duracion entera, se solaparia con el que si
        # empieza dentro y se verian los dos textos encimados.
        shifted = []
        for it in res["items"]:
            t = it["t"] - range_[0]
            if t + it["dur"] <= 0 or t >= job.total:
                continue
            cut = -t if t < 0 else 0.0
            r = dict(it, t=max(0.0, t), dur=round(it["dur"] - cut, 4))
            if cut > 0 and r.get("lines"):
                r["lines"] = [[dict(w, s=round((+w.get("s") or 0) - cut, 3),
                                    e=round((+w.get("e") or 0) - cut, 3))
                               for w in ln] for ln in it["lines"]]
            shifted.append(r)
        res["items"] = shifted
    ainfo = assbuild.build(tl, res, pdir, ass)
    if on_stage:
        on_stage("video")
    cmd, info = job.build(ass if ainfo["events"] else None)
    (pdir / "cache").mkdir(parents=True, exist_ok=True)
    # Windows corta la linea de comandos en 32 KB. Un proyecto con muchos
    # keyframes bezier (que se hornean en tramos rectos) llega ahi, asi que el
    # filtro grande se manda por archivo.
    if "-filter_complex" in cmd:
        i = cmd.index("-filter_complex")
        if len(cmd[i + 1]) > 16000:
            fg = pdir / "cache" / "filtergraph.txt"
            fg.write_text(cmd[i + 1], encoding="utf-8")
            cmd[i:i + 2] = ["-filter_complex_script", str(fg)]
    (pdir / "cache" / "last_render_cmd.txt").write_text(
        "\n".join(str(c) for c in cmd), encoding="utf-8")
    run(cmd, job.total, on_progress,
        log_path=pdir / "cache" / "last_render.log", on_start=on_start)
    info["ass"] = ainfo
    info["out"] = str(job.out)
    info["draft"] = draft
    info["size"] = job.out.stat().st_size if job.out.exists() else 0
    return info
