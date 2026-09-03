# -*- coding: utf-8 -*-
r"""Convierte las pistas de texto en un archivo ASS que quema libass.

Por que ASS y no dibujar fotogramas: libass es rapido, vectorial, y hace
karaoke, sombras y transformaciones sin que tengamos que generar PNGs. El
precio es que hay que expresar el diseno en tags, que es lo que hace este
modulo.

Tres decisiones que explican todo lo demas:

* **El reparto en lineas ya viene hecho** (`textlayer`), con las metricas reales
  del .ttf. Aca solo se posiciona: cada linea es un evento con su `\pos`, asi
  controlamos el interlineado, que ASS no permite ajustar de otro modo.
* **El revelado palabra por palabra no cambia el ancho de la linea.** Se emite
  la linea completa y las palabras que aun no toca se ponen transparentes. Si en
  vez de eso se fuera anadiendo texto, la linea se recentraria en cada palabra y
  saltaria. Es la diferencia entre parecer CapCut y parecer un karaoke roto.
* **La sombra difusa se dibuja como una copia borrosa debajo**, no con el
  `Shadow` del formato, que es un desplazamiento duro. Con `\bord0` el `\blur`
  difumina el relleno, que es justo lo que queremos.
"""
from __future__ import annotations

from pathlib import Path

from . import textlayer

# Recorrido de cada animacion como fracciones del progreso (0..1). El preview
# del editor lee esta misma tabla desde `/api/catalog`: si cambias una curva,
# cambia en los dos sitios a la vez.
ANIM = {
    "none":        [],
    "fade":        [(0.0, {"a": 0.0}), (1.0, {"a": 1.0})],
    "pop":         [(0.0, {"s": 0.70}), (0.62, {"s": 1.06}), (1.0, {"s": 1.0})],
    "zoom_in":     [(0.0, {"s": 0.80, "a": 0.0}), (1.0, {"s": 1.0, "a": 1.0})],
    "zoom_out":    [(0.0, {"s": 1.22, "a": 0.0}), (1.0, {"s": 1.0, "a": 1.0})],
    "slide_up":    [(0.0, {"dy": 0.055, "a": 0.0}), (1.0, {"dy": 0.0, "a": 1.0})],
    "slide_down":  [(0.0, {"dy": -0.055, "a": 0.0}), (1.0, {"dy": 0.0, "a": 1.0})],
    "slide_left":  [(0.0, {"dx": 0.09, "a": 0.0}), (1.0, {"dx": 0.0, "a": 1.0})],
    "slide_right": [(0.0, {"dx": -0.09, "a": 0.0}), (1.0, {"dx": 0.0, "a": 1.0})],
    "bounce":      [(0.0, {"s": 0.86}), (0.42, {"s": 1.09}), (0.7, {"s": 0.97}),
                    (0.88, {"s": 1.02}), (1.0, {"s": 1.0})],
}

REVEAL_FADE = 0.07      # cuanto tarda una palabra en aparecer, en segundos


# ------------------------------------------------------------ primitivas

def ass_color(hexstr, default="#FFFFFF"):
    """#RRGGBB -> &HBBGGRR& (ASS invierte el orden de los canales)."""
    s = (hexstr or default).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) < 6:
        s = "FFFFFF"
    r, g, b = s[0:2], s[2:4], s[4:6]
    return "&H%s%s%s&" % (b.upper(), g.upper(), r.upper())


def ass_alpha(opacity255):
    """Opacidad 0..255 -> tag de alfa ASS (que es lo contrario: 0 = opaco)."""
    a = int(round(255 - max(0, min(255, opacity255))))
    return "&H%02X&" % a


def ass_time(t):
    t = max(0.0, float(t))
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def esc(text):
    """El texto de un evento no puede llevar saltos ni llaves sueltas."""
    return (text or "").replace("\\", "\\\\").replace("{", "\\{") \
                       .replace("}", "\\}").replace("\n", " ")


def _lerp(a, b, p):
    return a + (b - a) * p


def sample_anim(kfs, p):
    """Estado de una animacion en el progreso p (0..1)."""
    st = {"s": 1.0, "a": 1.0, "dx": 0.0, "dy": 0.0}
    if not kfs:
        return st
    p = max(0.0, min(1.0, p))
    prev = kfs[0]
    for cur in kfs:
        if p <= cur[0]:
            span = cur[0] - prev[0]
            q = 0.0 if span <= 1e-6 else (p - prev[0]) / span
            for k in st:
                a = prev[1].get(k, st[k])
                b = cur[1].get(k, a)
                st[k] = _lerp(a, b, q)
            return st
        prev = cur
    for k in st:
        st[k] = kfs[-1][1].get(k, st[k])
    return st


def kfs_for(kind, out=False):
    """Keyframes de una animacion. La de salida es la de entrada al reves."""
    kfs = ANIM.get(kind or "none") or []
    if not kfs:
        return []
    if not out:
        return kfs
    return [(round(1.0 - p, 6), vals) for p, vals in reversed(kfs)]


# ------------------------------------------------------------ estilos

PLAIN_SUBFAMILY = ("", "regular", "book", "normal", "roman")


def font_family(name, project_dir=None):
    """Nombre con el que libass encuentra ESTE archivo, no un primo suyo.

    Medido: con `Fontname: Inter` y `Bold: -1`, libass (DirectWrite) devuelve un
    Inter regular engordado a mano, no Inter Black, aunque Inter Black sea el
    unico Inter del `fontsdir`. Con `Fontname: Inter Black` y `Bold: 0` sale la
    fuente real. Por eso el nombre incluye la subfamilia cuando no es Regular:
    es la unica forma de que el render use la misma fuente que midio PIL.
    """
    path = textlayer.find_font(name, project_dir)
    if not path:
        return "Arial", 0
    try:
        from PIL import ImageFont
        fam, sub = ImageFont.truetype(str(path), 32).getname()
    except (OSError, ValueError):
        return Path(str(path)).stem, 0
    fam = fam or Path(str(path)).stem
    sub = (sub or "").strip()
    if sub.lower() in PLAIN_SUBFAMILY:
        return fam, 0
    return "%s %s" % (fam, sub), 0


def merged_style(tl, item):
    """Estilo del item: el preset mas lo que el item pisa encima."""
    styles = tl.get("styles") or {}
    base = dict(styles.get(item.get("style") or "capcut")
                or (next(iter(styles.values())) if styles else {}))
    ov = item.get("override") or {}
    for k, v in ov.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            merged = dict(base[k])
            merged.update(v)
            base[k] = merged
        elif v is not None:
            base[k] = v
    return base


# ------------------------------------------------------------ documento

class AssDoc:
    def __init__(self, canvas):
        self.w = int(canvas["width"])
        self.h = int(canvas["height"])
        self.styles = {}
        self.events = []

    def style_for(self, style, project_dir):
        """Un estilo ASS por combinacion de fuente/cuerpo/color que aparezca."""
        fam, bold = font_family(style.get("font"), project_dir)
        size = float(style.get("size") or 80) * self.w / 1080.0
        spacing = float(style.get("letter_spacing") or 0) * self.w / 1080.0
        key = (fam, bold, round(size, 1), style.get("color") or "#FFFFFF",
               round(spacing, 2))
        name = self.styles.get(key)
        if name:
            return name
        name = "s%d" % (len(self.styles) + 1)
        self.styles[key] = name
        return name

    def add(self, layer, t0, t1, style_name, text):
        if t1 - t0 < 0.012:      # menos de un tercio de frame: no se ve
            return
        self.events.append((layer, t0, t1, style_name, text))

    def dumps(self):
        head = [
            "[Script Info]",
            "; generado por vcut studio - no editar a mano",
            "ScriptType: v4.00+",
            "PlayResX: %d" % self.w,
            "PlayResY: %d" % self.h,
            "WrapStyle: 2",              # nosotros ya partimos las lineas
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: TV.709",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,"
            " OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut,"
            " ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow,"
            " Alignment, MarginL, MarginR, MarginV, Encoding",
        ]
        for (fam, bold, size, color, spacing), name in self.styles.items():
            head.append(
                "Style: %s,%s,%.1f,%s,%s,&H00000000,&H00000000,%d,0,0,0,"
                "100,100,%.2f,0,1,0,0,8,0,0,0,1"
                % (name, fam, size, ass_color(color), ass_color(color),
                   bold, spacing))
        head += ["", "[Events]",
                 "Format: Layer, Start, End, Style, Name, MarginL, MarginR,"
                 " MarginV, Effect, Text"]
        body = []
        for layer, t0, t1, sname, text in sorted(self.events,
                                                 key=lambda e: (e[1], e[0])):
            body.append("Dialogue: %d,%s,%s,%s,,0,0,0,,%s"
                        % (layer, ass_time(t0), ass_time(t1), sname, text))
        return "\n".join(head + body) + "\n"


# ------------------------------------------------------------ geometria

def _states(item, style):
    """Momentos en los que cambia lo que se ve, en tiempo relativo al item.

    Con revelado por palabra hay un estado por palabra; sin revelado, uno solo.
    """
    lines = item.get("lines") or []
    flat = []
    for li, ln in enumerate(lines):
        for w in ln:
            flat.append((li, w))
    dur = float(item.get("dur") or 0)
    if not flat:
        return [], []
    reveal = (item.get("reveal") or style.get("reveal") or "none")
    if reveal != "word":
        return flat, [(0.0, dur, len(flat))]
    out = []
    for i, (_li, w) in enumerate(flat):
        s = max(0.0, float(w.get("s") or 0.0))
        e = dur if i + 1 >= len(flat) else max(s, float(flat[i + 1][1].get("s") or 0.0))
        if e - s < 0.005 and i + 1 < len(flat):
            continue                     # dos palabras marcadas al mismo tiempo
        out.append((min(s, dur), min(e, dur), i + 1))
    if out and out[0][0] > 0.001:
        out.insert(0, (0.0, out[0][0], 0))
    return flat, out


def geom(item, style, W, H, metrics):
    """Ancla horizontal, y de cada linea, y alineacion ASS.

    `box.y` es donde va el borde SUPERIOR de la primera linea. Las siguientes
    crecen hacia abajo: por eso el apilado no mueve lo que ya estaba escrito.
    """
    box = style.get("box") or {}
    bx = float(item.get("x") if item.get("x") is not None else box.get("x", 0.5))
    by = float(item.get("y") if item.get("y") is not None else box.get("y", 0.66))
    align = style.get("align") or "center"
    bw = float(box.get("w") or 0.86) * W
    if align == "left":
        an, ax = 7, bx * W - bw / 2.0
    elif align == "right":
        an, ax = 9, bx * W + bw / 2.0
    else:
        an, ax = 8, bx * W
    top = by * H
    ys, acc = [], 0.0
    for m in metrics["lines"]:
        ys.append(top + acc)
        acc += m["h"]
    return an, ax, ys


def _anim_block(kfs, p0, p1, ms_span, cx, cy, W, H, allow_alpha):
    r"""Tags de un evento que cubre el tramo de progreso [p0, p1].

    Los tiempos de `\t` son relativos al evento, y un evento puede caer en
    medio de la animacion (el revelado por palabra parte la tarjeta en muchos
    eventos cortos). Por eso todo se expresa en progreso y se remapea a ms.
    """
    if not kfs or ms_span <= 0:
        return "\\pos(%.1f,%.1f)" % (cx, cy)
    span = max(1e-6, p1 - p0)

    def ms_at(p):
        return max(0, min(ms_span, int(round((p - p0) / span * ms_span))))

    a0 = sample_anim(kfs, p0)
    a1 = sample_anim(kfs, p1)
    tags = []
    moved = (abs(a0["dx"]) > 1e-4 or abs(a0["dy"]) > 1e-4
             or abs(a1["dx"]) > 1e-4 or abs(a1["dy"]) > 1e-4)
    if moved:
        # ASS solo interpola posicion con \move, y solo en un tramo lineal.
        tags.append("\\move(%.1f,%.1f,%.1f,%.1f,0,%d)"
                    % (cx + a0["dx"] * W, cy + a0["dy"] * H,
                       cx + a1["dx"] * W, cy + a1["dy"] * H, ms_span))
    else:
        tags.append("\\pos(%.1f,%.1f)" % (cx, cy))

    if abs(a0["s"] - 1.0) > 1e-3 or abs(a1["s"] - 1.0) > 1e-3:
        # La escala si acepta \t encadenados, asi que el rebote sale entero.
        tags.append("\\fscx%.1f\\fscy%.1f" % (a0["s"] * 100, a0["s"] * 100))
        prev_p = p0
        for p, vals in kfs:
            if "s" not in vals or p <= p0 + 1e-6:
                continue
            end = min(p, p1)
            v = sample_anim(kfs, end)["s"] * 100
            tags.append("\\t(%d,%d,\\fscx%.1f\\fscy%.1f)"
                        % (ms_at(prev_p), ms_at(end), v, v))
            prev_p = p
            if p >= p1 - 1e-6:
                break

    if allow_alpha and (a0["a"] < 0.999 or a1["a"] < 0.999):
        tags.append("\\alpha%s" % ass_alpha(int(a0["a"] * 255)))
        tags.append("\\t(0,%d,\\alpha%s)"
                    % (ms_span, ass_alpha(int(a1["a"] * 255))))
    return "".join(tags)


def _geo_for(s0, s1, dur, d_in, d_out, anim_in, anim_out, cx, cy, W, H,
             allow_alpha):
    """Elige que animacion toca en el tramo [s0, s1] del item."""
    ms = max(1, int(round((s1 - s0) * 1000)))
    if anim_in != "none" and d_in > 0.01 and s0 < d_in - 1e-6:
        return _anim_block(kfs_for(anim_in), s0 / d_in, min(1.0, s1 / d_in),
                           ms, cx, cy, W, H, allow_alpha)
    if anim_out != "none" and d_out > 0.01 and s1 > dur - d_out + 1e-6:
        w0 = dur - d_out
        return _anim_block(kfs_for(anim_out, out=True),
                           max(0.0, (s0 - w0) / d_out),
                           min(1.0, (s1 - w0) / d_out),
                           ms, cx, cy, W, H, allow_alpha)
    return "\\pos(%.1f,%.1f)" % (cx, cy)


# ------------------------------------------------------------ eventos

def _line_text(ln, shown, s0, size, ratio, bfam, kfam, color, kcolor,
               reveal, force_alpha=None):
    """Una linea completa, con las palabras que aun no toca transparentes."""
    parts = []
    vis_alpha = force_alpha or "&H00&"
    for j, w in enumerate(ln):
        pre = " " if j else ""
        tags = []
        if j < shown:
            if reveal == "word" and j == shown - 1:
                # La palabra que acaba de entrar hace un fundido corto: es lo
                # que separa "aparece" de "parpadea".
                tags.append("\\alpha&HFF&\\t(0,%d,\\alpha%s)"
                            % (max(1, int(round(REVEAL_FADE * 1000))), vis_alpha))
            else:
                tags.append("\\alpha%s" % vis_alpha)
        else:
            tags.append("\\alpha&HFF&")
        if w.get("key"):
            tags.append("\\fn%s\\fs%.1f\\1c%s" % (kfam, size * ratio, kcolor))
        elif j and ln[j - 1].get("key"):
            # Volver a la fuente y el cuerpo de la linea tras la palabra clave.
            tags.append("\\fn%s\\fs%.1f\\1c%s" % (bfam, size, color))
        parts.append("%s{%s}%s" % (pre, "".join(tags), esc(w.get("w"))))
    return "".join(parts)


def text_events(doc, item, style, project_dir):
    """Eventos de un item de texto: sombra y texto, por linea y por estado."""
    lines = item.get("lines") or []
    if not lines:
        return
    W, H = doc.w, doc.h
    scale = W / 1080.0
    metrics = textlayer.line_metrics(lines, style, W, project_dir)
    an, ax, ys = geom(item, style, W, H, metrics)
    base_name = doc.style_for(style, project_dir)

    size = float(style.get("size") or 80) * scale
    ratio = float(style.get("keyword_size_ratio") or 1.0)
    kfam, _kb = font_family(style.get("keyword_font") or style.get("font"),
                            project_dir)
    bfam, _ = font_family(style.get("font"), project_dir)
    color = ass_color(style.get("color"))
    kcolor = ass_color(style.get("keyword_color"), "#4A90E0")

    sh = style.get("shadow") or {}
    sh_op = int(sh.get("opacity") or 0)
    sh_blur = float(sh.get("blur") or 0) * scale
    sh_dx = float(sh.get("dx") or 0) * scale
    sh_dy = float(sh.get("dy") or 0) * scale
    sh_col = ass_color(sh.get("color"), "#000000")
    bord = float(style.get("outline") or 0) * scale
    bcol = ass_color(style.get("outline_color"), "#000000")

    _flat, states = _states(item, style)
    if not states:
        return
    reveal = (item.get("reveal") or style.get("reveal") or "none")
    dur = float(item["dur"])
    t_abs = float(item["t"])
    anim_in = item.get("anim_in") or style.get("anim_in") or "none"
    anim_out = item.get("anim_out") or style.get("anim_out") or "none"
    adur = float(item.get("anim_dur") or style.get("anim_dur") or 0.22)
    d_in = min(adur, dur * 0.5)
    d_out = min(adur, dur * 0.5)
    # Con revelado por palabra el alfa ya lo maneja el revelado: si encima lo
    # tocara la animacion de entrada, los dos se pelearian por el mismo tag.
    allow_alpha = (reveal != "word")

    first_of, n = {}, 0
    for li, ln in enumerate(lines):
        first_of[li] = n
        n += len(ln)

    # Tres niveles por pista: fondo, sombra y texto. Así el orden vertical de
    # las capas del Studio coincide con el render final.
    base_layer = max(0, int(float(item.get("z") or 0)) * 3)
    layer = base_layer + 2

    for li, ln in enumerate(lines):
        cy = ys[li]
        # La animacion de entrada de cada linea empieza cuando esa linea
        # aparece, no cuando arranca la tarjeta: en el apilado cada linea entra
        # por su cuenta, y si no se midiera asi, la segunda y la tercera se
        # perderian la animacion entera.
        base_t = float(ln[0].get("s") or 0.0) if reveal == "word" else 0.0
        # Estados fusionados: mientras esta linea no cambie y no haya animacion
        # en curso, un solo evento en vez de uno por palabra.
        runs = []
        for (s0, s1, nrev) in states:
            shown = max(0, min(len(ln), nrev - first_of[li]))
            if shown <= 0:
                continue
            animating = (s0 < base_t + d_in + 1e-6) or (s1 > dur - d_out - 1e-6)
            if (runs and not animating and not runs[-1][3]
                    and runs[-1][2] == shown and abs(runs[-1][1] - s0) < 1e-6):
                runs[-1][1] = s1
            else:
                runs.append([s0, s1, shown, animating])

        for s0, s1, shown, _an in runs:
            if s1 - s0 < 0.012:
                continue
            body = _line_text(ln, shown, s0, size, ratio, bfam, kfam,
                              color, kcolor, reveal)
            if sh_op > 0:
                # La sombra es el mismo texto, desplazado y borroso, debajo. Se
                # anima igual para que no se despegue del texto.
                sgeo = _geo_for(s0 - base_t, s1 - base_t, dur - base_t,
                                d_in, d_out, anim_in, anim_out,
                                ax + sh_dx, cy + sh_dy, W, H, allow_alpha)
                sbody = _line_text(ln, shown, s0, size, ratio, bfam, kfam,
                                   sh_col, sh_col, reveal,
                                   force_alpha=ass_alpha(sh_op))
                doc.add(base_layer + 1, t_abs + s0, t_abs + s1, base_name,
                        "{\\an%d%s\\bord0\\shad0\\blur%.1f\\1c%s}%s"
                        % (an, sgeo, sh_blur, sh_col, sbody))
            geo = _geo_for(s0 - base_t, s1 - base_t, dur - base_t,
                           d_in, d_out, anim_in, anim_out,
                           ax, cy, W, H, allow_alpha)
            common = "\\an%d%s\\bord%.1f\\shad0" % (an, geo, bord)
            if bord > 0:
                common += "\\3c%s" % bcol
            doc.add(layer, t_abs + s0, t_abs + s1, base_name,
                    "{%s}%s" % (common, body))


def bg_events(doc, item, style, project_dir):
    """Caja de fondo de un item (estilos tipo etiqueta).

    Es un rectangulo vectorial dibujado con las medidas reales del texto, no el
    `BorderStyle: 3` del formato: asi el preview puede dibujar exactamente el
    mismo rectangulo. Esquinas rectas, porque redondearlas en ASS obligaria a
    generar beziers que el preview tendria que replicar a mano.
    """
    bg = style.get("bg") or {}
    if not bg or int(bg.get("opacity") or 0) <= 0:
        return
    lines = item.get("lines") or []
    if not lines:
        return
    W, H = doc.w, doc.h
    scale = W / 1080.0
    metrics = textlayer.line_metrics(lines, style, W, project_dir)
    an, ax, ys = geom(item, style, W, H, metrics)
    pad = float(bg.get("pad") or 0) * scale
    bw = max(m["w"] for m in metrics["lines"]) + pad * 2
    bh = metrics["total_h"] + pad * 2
    if an == 7:
        x0 = ax - pad
    elif an == 9:
        x0 = ax - bw + pad
    else:
        x0 = ax - bw / 2.0
    y0 = ys[0] - pad
    name = doc.style_for(style, project_dir)
    draw = "m 0 0 l %.0f 0 l %.0f %.0f l 0 %.0f" % (bw, bw, bh, bh)
    base_layer = max(0, int(float(item.get("z") or 0)) * 3)
    doc.add(base_layer, float(item["t"]), float(item["t"]) + float(item["dur"]), name,
            "{\\an7\\pos(%.1f,%.1f)\\bord0\\shad0\\1c%s\\1a%s\\p1}%s{\\p0}"
            % (x0, y0, ass_color(bg.get("color"), "#FFFFFF"),
               ass_alpha(int(bg.get("opacity") or 255)), draw))


def build(tl, res, project_dir, out_path):
    """Escribe el ASS de todas las pistas de texto visibles."""
    doc = AssDoc(res["canvas"])
    n = 0
    for item in res["items"]:
        if item.get("track_kind") != "text":
            continue
        style = merged_style(tl, item)
        bg_events(doc, item, style, project_dir)
        text_events(doc, item, style, project_dir)
        n += 1
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # BOM: sin el, algunos builds de libass leen el ASS como latin-1 y se
    # comen los acentos.
    out.write_text(doc.dumps(), encoding="utf-8-sig")
    return {"path": str(out), "items": n, "events": len(doc.events),
            "fonts": sorted({k[0] for k in doc.styles})}
