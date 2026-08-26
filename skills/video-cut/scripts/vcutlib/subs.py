# -*- coding: utf-8 -*-
"""Subtitulos automaticos desde la transcripcion, en tarjetas apiladas.

Una **tarjeta** es un item de texto: hasta `max_lines` lineas que se acumulan
ancladas por su borde superior, con las palabras entrando una a una. Es el
mismo comportamiento que la skill `subtitulo`, pero aca las tarjetas quedan
como items editables del timeline en vez de quemarse a ciegas.

Cada tarjeta se ancla al segmento del que salio (`anchor`), asi que si mas
tarde se recorta o se reordena ese clip, su texto lo sigue sin recalcular nada.
Los tiempos de palabra dentro de la tarjeta son **relativos al inicio de la
tarjeta**, para que arrastrarla no descoloque el revelado.
"""
from __future__ import annotations

from . import studio, textlayer, util

LEAD = 0.06          # cuanto antes de la primera palabra aparece la tarjeta
TAIL = 0.30          # cuanto se queda despues de la ultima
MIN_DUR = 0.45
GAP_SPLIT = 0.55     # hueco que cierra una tarjeta (igual que `analyze.pause`)
MAX_CHUNK_WORDS = 14


def _chunks(words, max_gap=GAP_SPLIT, max_words=MAX_CHUNK_WORDS):
    """Parte el habla en tramos candidatos a tarjeta: puntuacion, huecos, largo."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        txt = (w.get("w") or "").strip()
        nxt = words[i + 1] if i + 1 < len(words) else None
        gap = (float(nxt["s"]) - float(w["e"])) if nxt else 0.0
        if (textlayer.is_sentence_end(txt) or gap > max_gap
                or len(cur) >= max_words or nxt is None):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def _split_lines(lines, max_lines):
    """Agrupa lineas en tarjetas de como mucho `max_lines` lineas."""
    if max_lines <= 1:
        return [[ln] for ln in lines]
    return [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]


def cards_for_clip(clip, seg, style, canvas_w, project_dir=None,
                   keywords=None, no_keywords=False):
    """Tarjetas de un clip ya resuelto. Devuelve items sin id."""
    words = []
    for w in seg.get("words") or []:
        s, e = float(w.get("s") or 0), float(w.get("e") or 0)
        if e <= clip["in"] or s >= clip["out"]:
            continue
        s = max(s, clip["in"])
        e = min(e, clip["out"])
        if e - s <= 0.001:
            e = s + 0.03
        # A tiempo de SALIDA: la velocidad del clip tambien afecta al texto.
        spd = clip["speed"]
        words.append({"w": (w.get("w") or "").strip(),
                      "s": (s - clip["in"]) / spd,
                      "e": (e - clip["in"]) / spd})
    words = [w for w in words if w["w"]]
    if not words:
        return []

    max_lines = int(style.get("max_lines") or 3)
    only_key = bool(style.get("stack_only_with_keyword"))
    forced = {util.normalize(k) for k in (keywords or []) if k}

    out = []
    for chunk in _chunks(words):
        key_idx = None
        if not no_keywords:
            if forced:
                for i, w in enumerate(chunk):
                    if util.normalize(w["w"]) in forced:
                        key_idx = i
                        break
            if key_idx is None and not forced:
                key_idx = textlayer.pick_keyword(chunk)
        lines = textlayer.wrap(chunk, style, canvas_w, key_idx, project_dir)
        # Sin palabra clave el apilado no aporta: una linea por tarjeta se lee
        # mas rapido y deja el plano limpio (asi esta calibrado el estilo).
        groups = _split_lines(lines, 1 if (only_key and key_idx is None) else max_lines)
        for grp in groups:
            flat = [w for ln in grp for w in ln]
            if not flat:
                continue
            t0 = max(0.0, float(flat[0]["s"]) - LEAD)
            t1 = float(flat[-1]["e"]) + TAIL
            t1 = min(t1, clip["dur"])
            if t1 - t0 < MIN_DUR:
                t1 = min(clip["dur"], t0 + MIN_DUR)
            rel = [[{"w": w["w"], "s": round(w["s"] - t0, 3),
                     "e": round(w["e"] - t0, 3), "key": bool(w.get("key"))}
                    for w in ln] for ln in grp]
            out.append({
                "kind": "text",
                "auto": True,
                "style": None,               # lo pone quien llama
                "anchor": {"seg": clip["seg"], "offset": round(t0, 3)},
                "dur": round(max(MIN_DUR, t1 - t0), 3),
                "lines": rel,
                "text": " ".join(w["w"] for w in flat),
                "x": None, "y": None,
            })

    # Que una tarjeta no pise a la siguiente: el apilado ya es la forma de
    # mostrar dos ideas a la vez, solapar dos tarjetas seria ruido.
    for a, b in zip(out, out[1:]):
        limit = b["anchor"]["offset"] - 0.02
        if a["anchor"]["offset"] + a["dur"] > limit:
            a["dur"] = round(max(0.2, limit - a["anchor"]["offset"]), 3)
    return out


def generate(project, tl, style_name="capcut", track_id="t_sub",
             project_dir=None, keywords=None, no_keywords=False,
             replace=True, only_segs=None):
    """Rellena la pista de subtitulos desde la transcripcion.

    `replace` borra las tarjetas generadas antes (las que tienen `auto`), pero
    nunca las que el usuario creo o edito a mano (`auto` en false).
    """
    trk = studio.track(tl, track_id)
    if trk is None:
        raise ValueError("no existe la pista %s" % track_id)
    style = tl["styles"].get(style_name)
    if style is None:
        raise ValueError("no existe el estilo %s" % style_name)

    res = studio.resolve(project, tl)
    segmap = {s["id"]: s for s in project["segments"]}
    canvas_w = int(tl["canvas"]["width"])

    if replace:
        keep = [it for it in trk["items"] if not it.get("auto")]
        if only_segs:
            keep += [it for it in trk["items"]
                     if it.get("auto")
                     and (it.get("anchor") or {}).get("seg") not in only_segs]
        trk["items"] = keep

    made = 0
    for clip in res["clips"]:
        if only_segs and clip["seg"] not in only_segs:
            continue
        seg = segmap.get(clip["seg"])
        if not seg:
            continue
        for card in cards_for_clip(clip, seg, style, canvas_w, project_dir,
                                   keywords, no_keywords):
            card["id"] = studio.new_id(tl, "s")
            card["style"] = style_name
            trk["items"].append(card)
            made += 1

    trk["items"].sort(key=_sort_key(res))
    return made


def _sort_key(res):
    order = {c["seg"]: c["index"] for c in res["clips"]}
    def key(it):
        a = it.get("anchor") or {}
        return (order.get(a.get("seg"), 9999), float(a.get("offset") or it.get("t") or 0))
    return key


def relayout(tl, style_name=None, project_dir=None, track_id="t_sub"):
    """Vuelve a partir en lineas las tarjetas con el estilo actual.

    Se usa cuando cambia la tipografia, el cuerpo o el ancho de la caja: el
    reparto de palabras cambia, pero los tiempos de cada palabra no.
    """
    trk = studio.track(tl, track_id)
    if trk is None:
        return 0
    canvas_w = int(tl["canvas"]["width"])
    n = 0
    for it in trk["items"]:
        if it.get("kind") != "text" or not it.get("lines"):
            continue
        sname = style_name or it.get("style") or "capcut"
        style = tl["styles"].get(sname)
        if not style:
            continue
        flat = [w for ln in it["lines"] for w in ln]
        key_idx = next((i for i, w in enumerate(flat) if w.get("key")), None)
        lines = textlayer.wrap(flat, style, canvas_w, key_idx, project_dir)
        max_lines = int(style.get("max_lines") or 3)
        it["lines"] = lines[:max_lines] if len(lines) > max_lines else lines
        if style_name:
            it["style"] = style_name
        n += 1
    return n
