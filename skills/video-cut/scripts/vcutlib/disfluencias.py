"""Compara la transcripcion legible con la verbatim y saca lo que whisper limpio.

El problema de fondo: whisper es seq2seq con modelo de lenguaje y repara los
arranques en falso, asi que buscar el titubeo en el texto no sirve porque no
esta. `vcut qa` lo detecta midiendo el audio con silencedetect; esto lo detecta
por otra via, comparando dos transcripciones del mismo audio con prompts
distintos.

Las dos vias son complementarias. silencedetect ve islas de voz pero no sabe
QUE se dijo; la comparacion de transcripciones dice las palabras exactas que la
pasada legible se comio, que es lo que hace falta para decidir si una toma
abortada merece apagarse o si el corte esta partiendo la buena.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from pathlib import Path

from . import util

_LIMPIA = re.compile(r"[^\w\s']", re.UNICODE)


def _normaliza(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return _LIMPIA.sub(" ", sin_tildes)


def _palabras(datos: dict) -> list[dict]:
    salida = []
    for seg in datos.get("segments", []):
        for w in seg.get("words", []):
            texto = str(w.get("w", "")).strip()
            if texto:
                salida.append({"w": texto, "s": w.get("s"), "e": w.get("e")})
    return salida


def comparar(legible: dict, verbatim: dict, minimo: int = 2) -> list[dict]:
    """Tramos presentes en la verbatim que la legible no tiene.

    Se comparan las secuencias de palabras normalizadas con difflib. Las
    inserciones del lado verbatim son exactamente lo que la pasada legible
    reparo: arranques en falso, repeticiones y muletillas.
    """
    pl, pv = _palabras(legible), _palabras(verbatim)
    if not pl or not pv:
        return []

    a = [_normaliza(w["w"]).strip() for w in pl]
    b = [_normaliza(w["w"]).strip() for w in pv]
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)

    hallazgos = []
    for etiqueta, i1, i2, j1, j2 in matcher.get_opcodes():
        if etiqueta not in ("insert", "replace"):
            continue
        extra = pv[j1:j2]
        if len(extra) < minimo:
            continue
        texto = " ".join(w["w"] for w in extra)
        if not _normaliza(texto).strip():
            continue
        inicio = next((w["s"] for w in extra if w["s"] is not None), None)
        fin = next((w["e"] for w in reversed(extra) if w["e"] is not None), None)
        # Contexto por el lado legible: donde encajaria el tramo.
        contexto = " ".join(w["w"] for w in pl[max(0, i1 - 3):i1 + 3])
        hallazgos.append({
            "inicio": inicio,
            "fin": fin,
            "palabras": len(extra),
            "texto": texto,
            "tipo": "sustituido" if etiqueta == "replace" else "omitido",
            "contexto": contexto,
        })
    return hallazgos


def informe(work_dir, sources, minimo: int = 2) -> dict:
    """Escribe disfluencias.md y devuelve el resumen."""
    work_dir = Path(work_dir)
    carpeta = work_dir / "transcripts"
    filas, sin_verbatim = [], []

    for source in sources:
        sid = source["id"]
        legible = util.read_json(carpeta / ("%s.json" % sid), {})
        ruta_v = carpeta / ("%s.verbatim.json" % sid)
        if not ruta_v.exists():
            sin_verbatim.append(source["name"])
            continue
        for h in comparar(legible, util.read_json(ruta_v, {}), minimo=minimo):
            h["archivo"] = source["name"]
            filas.append(h)

    lineas = ["## Lo que la transcripcion legible se comio", ""]
    if sin_verbatim:
        lineas += [
            "Falta la pasada verbatim de: " + ", ".join(sin_verbatim),
            "",
            "Generala con `vcut transcribe --verbatim`.",
            "",
        ]
    if not filas:
        lineas += ["No hay diferencias entre las dos pasadas.", ""]
    else:
        lineas += [
            "Cada fila es texto que la pasada verbatim oyo y la legible reparo.",
            "Los tiempos son del archivo ORIGINAL, no de la linea de tiempo.",
            "",
            "| archivo | en | palabras | texto omitido | contexto |",
            "|---|---|---|---|---|",
        ]
        for h in sorted(filas, key=lambda x: (x["archivo"], x["inicio"] or 0)):
            en = "%.2f" % h["inicio"] if h["inicio"] is not None else "?"
            lineas.append(
                "| `%s` | %s | %d | %s | %s |"
                % (h["archivo"], en, h["palabras"], h["texto"], h["contexto"])
            )
        lineas += [
            "",
            "### Como leerlo",
            "",
            "Un tramo omitido al principio de una toma es un **arranque en",
            "falso**: conviene entrar despues. Si el mismo texto aparece dos",
            "veces seguidas es una **toma repetida** que la pasada legible",
            "fusiono, y hay que elegir cual se queda. Contrasta con `qa.md`,",
            "que mide el audio: si los dos coinciden en el mismo punto, la",
            "correccion es segura.",
            "",
        ]

    destino = work_dir / "disfluencias.md"
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return {
        "hallazgos": len(filas),
        "sin_verbatim": sin_verbatim,
        "md": str(destino),
    }
