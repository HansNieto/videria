# -*- coding: utf-8 -*-
"""Control de calidad del plan de cortes contra el audio real.

Los timestamps por palabra de whisper mienten cuando hay un arranque en falso:
colapsa varios segundos de habla dudosa en una sola palabra larga, y el corte
automatico se queda con esa basura o con silencio al final. Aca no se cree en
la transcripcion: se mide el audio con silencedetect.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from . import util

SILENCE_RX = re.compile(r"silence_(start|end): (-?[\d.]+)")


def _silence_intervals(path, start, end, noise_db, min_sil):
    """Intervalos de silencio (relativos al corte) que ve ffmpeg."""
    dur = end - start
    cmd = [util.FFMPEG, "-hide_banner", "-nostats",
           "-ss", "%.3f" % start, "-to", "%.3f" % end, "-i", str(path), "-vn",
           "-af", "silencedetect=noise=%ddB:d=%.2f" % (noise_db, min_sil),
           "-f", "null", "-"]
    # silencedetect informa por stderr, asi que no sirve util.run().
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding="utf-8", errors="replace")
    txt = (proc.stderr or "") + (proc.stdout or "")
    intervals, open_at = [], None
    for kind, value in SILENCE_RX.findall(txt):
        v = float(value)
        if kind == "start":
            open_at = max(0.0, v)
        elif open_at is not None:
            intervals.append((open_at, min(v, dur)))
            open_at = None
    if open_at is not None:
        intervals.append((open_at, dur))
    return intervals, dur


def _speech_islands(intervals, dur):
    """Invierte los silencios: los tramos donde de verdad hay voz."""
    islands, cursor = [], 0.0
    for a, b in intervals:
        if a - cursor > 0.02:
            islands.append((cursor, a))
        cursor = max(cursor, b)
    if dur - cursor > 0.02:
        islands.append((cursor, dur))
    return islands


def _false_start(islands, max_island, min_gap):
    """Isla corta + pausa al arranque = intento abortado.

    Whisper nunca lo escribe (esta entrenado para limpiar titubeos), asi que
    esto no se puede detectar leyendo el texto: solo mirando el audio.
    """
    if len(islands) < 2:
        return None
    (a0, b0), (a1, _) = islands[0], islands[1]
    if (b0 - a0) <= max_island and (a1 - b0) >= min_gap:
        return {"island": [round(a0, 2), round(b0, 2)],
                "gap": round(a1 - b0, 2), "resume": round(a1, 2)}
    return None


def _false_end(islands, max_island, min_gap):
    """Isla muy corta al final tras una pausa larga: arranque de la toma siguiente.

    Umbrales duros a proposito: una frase corta despues de respirar ("que debes
    responder,") es habla legitima. Solo se avisa, nunca se recorta solo.
    """
    if len(islands) < 2:
        return None
    (_, b0), (a1, b1) = islands[-2], islands[-1]
    if (b1 - a1) <= min(max_island, 0.6) and (a1 - b0) >= max(min_gap, 0.7):
        return {"island": [round(a1, 2), round(b1, 2)],
                "gap": round(a1 - b0, 2), "ends": round(b0, 2)}
    return None


def check(project, noise_db=-45, min_sil=0.15, min_lead=0.4, min_tail=0.4,
          long_word=0.85, max_island=1.0, min_gap=0.28):
    """Revisa cada corte encendido y propone recortes concretos."""
    smap = {s["id"]: s for s in project["sources"]}
    rows, trim, suspects = [], {}, []
    enabled = [s for s in project["segments"] if s.get("enabled")]
    for i, seg in enumerate(enabled, 1):
        src = smap[seg["source"]]
        if not src.get("has_audio"):
            continue
        util.eprint("  qa %d/%d %s" % (i, len(enabled), src["name"]))
        a, b = seg["in"], seg["out"]
        intervals, dur = _silence_intervals(src["path"], a, b, noise_db, min_sil)
        lead = intervals[0][1] if intervals and intervals[0][0] <= 0.02 else 0.0
        # El ultimo silencio cuenta como cola aunque queden restos de ruido.
        tail = dur - intervals[-1][0] \
            if intervals and intervals[-1][1] >= dur - 0.25 else 0.0
        islands = _speech_islands(intervals, dur)
        row = {"id": seg["id"], "source": src["name"], "in": a, "out": b,
               "lead": round(lead, 2), "tail": round(tail, 2),
               "islands": [[round(x, 2), round(y, 2)] for x, y in islands]}

        new_in = round(a + max(0.0, lead - 0.12), 2) if lead > min_lead else a
        new_out = round(b - max(0.0, tail - 0.22), 2) if tail > min_tail else b
        why = []
        if new_in != a or new_out != b:
            why.append("aire muerto")

        fs = _false_start(islands, max_island, min_gap)
        if fs:
            new_in = max(new_in, round(a + fs["resume"] - 0.12, 2))
            row["false_start"] = fs
            why.append("arranque en falso (%.2fs de voz + %.2fs de pausa)"
                       % (fs["island"][1] - fs["island"][0], fs["gap"]))
        fe = _false_end(islands, max_island, min_gap)
        if fe:
            # Solo aviso: cortar la cola por cuenta propia se come frases buenas.
            row["false_end"] = fe

        if why and new_out - new_in > 0.2 and (new_in != a or new_out != b):
            trim[seg["id"]] = {"in": new_in, "out": new_out}
            row["suggest"] = {"in": new_in, "out": new_out,
                              "saves": round((new_in - a) + (b - new_out), 2),
                              "why": ", ".join(why)}
        rows.append(row)
        # Palabra imposiblemente larga = whisper tapo un titubeo o una pausa.
        for w in seg.get("words", []):
            span = w["e"] - w["s"]
            if span > long_word:
                suspects.append({"id": seg["id"], "source": src["name"],
                                 "word": w["w"], "start": w["s"], "end": w["e"],
                                 "span": round(span, 2)})
    saves = round(sum(r["suggest"]["saves"] for r in rows if "suggest" in r), 2)
    return {"ok": True, "checked": len(rows), "flagged": len(trim),
            "saves": saves, "cuts": rows, "suspect_words": suspects,
            "orphans": [], "decisions_trim": trim}


def _merge(ranges):
    """Une intervalos solapados."""
    out = []
    for a, b in sorted(ranges):
        if out and a <= out[-1][1] + 0.01:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _subtract(island, covered):
    """Lo que queda de una isla despues de quitarle lo que ya cubre el plan."""
    a, b = island
    holes, cursor = [], a
    for ca, cb in covered:
        if cb <= cursor or ca >= b:
            continue
        if ca > cursor:
            holes.append((cursor, min(ca, b)))
        cursor = max(cursor, cb)
        if cursor >= b:
            break
    if cursor < b:
        holes.append((cursor, b))
    return [(x, y) for x, y in holes if y - x > 0.01]


def coverage(project, noise_db=-45, min_sil=0.15, min_orphan=0.5, edge=0.1):
    """Habla del original que no entra en ningun corte del plan.

    Es la senal de una toma repetida que whisper borro: si el locutor repite la
    frase, la transcripcion del archivo completo se queda con una sola version y
    la otra no llega a ser ni un segmento apagado. Nadie la puede elegir porque
    para el plan no existe.
    """
    smap = {s["id"]: s for s in project["sources"]}
    por_fuente = {}
    for seg in project["segments"]:
        por_fuente.setdefault(seg["source"], []).append(seg)
    found, mid = [], []
    for sid, segs in por_fuente.items():
        src = smap[sid]
        if not src.get("has_audio"):
            continue
        util.eprint("  huerfanas %s" % src["name"])
        intervals, dur = _silence_intervals(src["path"], 0.0, src["duration"],
                                            noise_db, min_sil)
        islands = _speech_islands(intervals, dur)
        cubierto = _merge([[g["in"], g["out"]] for g in segs])
        for isla in islands:
            ia, ib = isla
            for a, b in _subtract(isla, cubierto):
                if b - a >= min_orphan:
                    vecinos = [g["id"] for g in segs
                               if g["out"] > a - 3.0 and g["in"] < b + 3.0]
                    found.append({"source": src["name"], "source_id": sid,
                                  "start": round(a, 2), "end": round(b, 2),
                                  "dur": round(b - a, 2), "near": vecinos})
            # Un corte encendido no deberia arrancar ni terminar a media isla:
            # eso es entrar con la palabra empezada o cortarla por la mitad.
            for g in segs:
                if not g.get("enabled"):
                    continue
                if ia + edge < g["in"] < ib - edge:
                    mid.append({"id": g["id"], "source": src["name"],
                                "side": "in", "cut": round(g["in"], 2),
                                "island": [round(ia, 2), round(ib, 2)],
                                "loose": round(g["in"] - ia, 2),
                                "suggest": round(max(0.0, ia - 0.12), 2)})
                if ia + edge < g["out"] < ib - edge:
                    mid.append({"id": g["id"], "source": src["name"],
                                "side": "out", "cut": round(g["out"], 2),
                                "island": [round(ia, 2), round(ib, 2)],
                                "loose": round(ib - g["out"], 2),
                                "suggest": round(ib + 0.22, 2)})
    return {"orphans": found, "mid_island": mid}


def listen(project, chunks, model_size="medium", language=None, pad=0.15):
    """Transcribe los tramos huerfanos sueltos.

    Aislados y cortos, whisper ya no puede 'arreglar' la frase y escribe el
    titubeo o la repeticion tal cual.
    """
    from . import transcribe as tr
    smap = {s["id"]: s for s in project["sources"]}
    bundle = tr.load_model(model_size)
    model = bundle[0] if isinstance(bundle, tuple) else bundle
    for ch in chunks:
        src = smap[ch["source_id"]]
        wav = Path(tempfile.gettempdir()) / ("vcut_orphan_%s_%d.wav"
                                             % (ch["source_id"], int(ch["start"] * 100)))
        subprocess.run([util.FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                        "-ss", "%.3f" % max(0.0, ch["start"] - pad),
                        "-to", "%.3f" % (ch["end"] + pad), "-i", src["path"],
                        "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
        segs, _ = model.transcribe(str(wav), language=language, beam_size=5,
                                   condition_on_previous_text=False)
        ch["text"] = " ".join(x.text.strip() for x in segs).strip()
        try:
            wav.unlink()
        except OSError:
            pass
    return chunks


def to_markdown(report):
    """Resumen legible para pegar en la revision."""
    lines = ["## QA de audio (silencedetect)", ""]
    lines.append("- Cortes revisados: %d | con aire muerto: %d | recuperable: %.2f s"
                 % (report["checked"], report["flagged"], report["saves"]))
    if report["flagged"]:
        lines += ["", "| id | archivo | corte | sugerido | por que |",
                  "|---|---|---|---|---|"]
        for r in report["cuts"]:
            if "suggest" not in r:
                continue
            g = r["suggest"]
            lines.append("| `%s` | %s | %.2f-%.2f | %.2f-%.2f (-%.2fs) | %s |"
                         % (r["id"], r["source"], r["in"], r["out"],
                            g["in"], g["out"], g["saves"], g["why"]))
    falsos = [r for r in report["cuts"] if "false_start" in r or "false_end" in r]
    if falsos:
        lines += ["", "### Tomas abortadas dentro del corte", "",
                  "Whisper no las escribe (limpia los titubeos), asi que en el texto",
                  "no se ven. Estas son las islas de voz que mide el audio:", ""]
        for r in falsos:
            lines.append("- `%s` %s -> islas %s"
                         % (r["id"], r["source"],
                            " ".join("%.2f-%.2f" % (x, y) for x, y in r["islands"])))
            if "false_start" in r:
                f = r["false_start"]
                lines.append("  - arranque en falso: voz en %.2f-%.2f, pausa de %.2fs, "
                             "la toma buena entra en %.2f (relativo al corte)"
                             % (f["island"][0], f["island"][1], f["gap"], f["resume"]))
            if "false_end" in r:
                f = r["false_end"]
                lines.append("  - cola sospechosa: %.2f-%.2f tras %.2fs de pausa"
                             % (f["island"][0], f["island"][1], f["gap"]))
    if report["suspect_words"]:
        lines += ["", "Palabras con duracion imposible (whisper tapo un titubeo;",
                  "escucha ese tramo antes de fiarte del corte):", ""]
        for w in report["suspect_words"]:
            lines.append("- `%s` %s @ %.2f-%.2f (%.2fs) %r"
                         % (w["id"], w["source"], w["start"], w["end"],
                            w["span"], w["word"]))
    if report.get("orphans"):
        lines += ["", "### Habla que no esta en ningun corte", "",
                  "Tramos con voz del original que el plan no cubre. Suele ser una",
                  "toma repetida que whisper borro al transcribir el archivo entero:",
                  "no existe ni como frase apagada, asi que nadie la puede elegir.", ""]
        for o in report["orphans"]:
            txt = (" -> %r" % o["text"]) if o.get("text") else ""
            lines.append("- %s %.2f-%.2f (%.2fs), pegado a %s%s"
                         % (o["source"], o["start"], o["end"], o["dur"],
                            ", ".join("`%s`" % i for i in o["near"]) or "nada", txt))
    if report.get("mid_island"):
        lines += ["", "### Cortes que entran o salen a media palabra", "",
                  "La isla de voz sigue mas alla del corte: se esta partiendo una",
                  "frase. Casi siempre significa que el corte agarro solo un pedazo",
                  "de la toma buena. Requiere tu decision, no se aplica solo:", ""]
        for m in report["mid_island"]:
            lado = "entra en" if m["side"] == "in" else "sale en"
            lines.append("- `%s` %s %s %.2f pero la isla va de %.2f a %.2f "
                         "(%.2fs de voz cortada) -> sugerido %s %.2f"
                         % (m["id"], m["source"], lado, m["cut"],
                            m["island"][0], m["island"][1], m["loose"],
                            m["side"], m["suggest"]))
    lines.append("")
    return "\n".join(lines)
