# -*- coding: utf-8 -*-
"""Traer de vuelta la edicion que hizo otra persona sobre un paquete de revision.

El reparto es: la maquina fuerte transcribe, corta y genera proxies; la otra
solo ajusta. Para que eso funcione hay que poder devolver el trabajo sin que se
pierdan los originales, y ahi esta el detalle: **el proyecto que vuelve apunta a
los proxies**. Si se copiara entero encima del bueno, el render final saldria de
video de 540p y nadie se daria cuenta hasta ver el MP4.

Asi que no se copia el proyecto: se copian **las decisiones**.

- de `project.json` vuelven los `segments` (los cortes) y `decisions.json`;
- de `timeline.json` vuelve todo, que es la capa creativa entera;
- las `sources` **no vuelven nunca**: mandan las de esta maquina, que son las
  que apuntan al material real.

Los assets que la otra persona haya sumado (un sonido, un b-roll, un overlay)
se copian al proyecto y sus rutas se reescriben, porque en esa maquina vivian
en otro sitio.
"""
from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from . import pack, studio, util


def _abrir(origen):
    """Devuelve (carpeta, temporal) tanto para un .vcutpack como para una carpeta."""
    p = Path(origen).expanduser()
    if p.is_dir():
        return p, None
    if not p.exists():
        raise RuntimeError("no existe %s" % p)
    tmp = Path(tempfile.mkdtemp(prefix="vcut-merge-"))
    with zipfile.ZipFile(p) as z:
        z.extractall(tmp)
    return tmp, tmp


def _mismo_proyecto(destino, entrante):
    """Que las dos partes hablen del mismo material.

    Se comparan los ids y los nombres de las fuentes. Coincidir en ids pero no
    en nombres significa que alguien renombro archivos: se avisa y se sigue.
    """
    a = {s["id"]: s.get("name") for s in destino.get("sources", [])}
    b = {s["id"]: s.get("name") for s in entrante.get("sources", [])}
    if not b:
        return ["el proyecto que vuelve no trae fuentes"]
    comunes = set(a) & set(b)
    if not comunes:
        raise RuntimeError(
            "no es el mismo proyecto: ninguna fuente coincide. "
            "Comprobá que el paquete salió de este proyecto.")
    avisos = []
    if len(comunes) < len(b):
        avisos.append("el paquete trae %d fuentes que aquí no existen"
                      % (len(b) - len(comunes)))
    if len(comunes) < len(a):
        avisos.append("aquí hay %d fuentes que el paquete no conocía"
                      % (len(a) - len(comunes)))
    distintos = [i for i in comunes if (a[i] or "").lower() != (b[i] or "").lower()]
    if distintos:
        avisos.append("%d fuentes cambiaron de nombre (%s)"
                      % (len(distintos), ", ".join(sorted(distintos)[:4])))
    return avisos


def _indice_local(pdir):
    """Los archivos que este proyecto ya usa, por nombre.

    Sin esto, cada viaje de ida y vuelta duplicaría los mismos sonidos y
    overlays dentro de `assets/recibidos/`: en la otra máquina viven en otra
    ruta, así que se ven como archivos nuevos aunque sean los de siempre.
    """
    idx = {}
    tl_viejo = util.read_json(studio.path_of(pdir), {}) or {}
    for _kind, holder, key in pack.referenced_assets(tl_viejo):
        if key == "seq":
            d = Path((holder.get("seq") or {}).get("dir") or "")
            if d.is_dir():
                idx["seq:" + d.name.lower()] = d
            continue
        q = Path(holder.get(key) or "")
        if q.name and q.exists():
            idx[q.name.lower()] = q
    for sub in ("assets", "audio"):
        base = pdir / sub
        if base.is_dir():
            for f in base.rglob("*"):
                if f.is_file():
                    idx.setdefault(f.name.lower(), f)
    return idx


def _traer_assets(tl, origen_dir, pdir, rep):
    """Copia a este proyecto los archivos que la otra persona sumó."""
    destino_base = pdir / "assets" / "recibidos"
    idx = _indice_local(pdir)
    for _kind, holder, key in pack.referenced_assets(tl):
        if key == "seq":
            seq = holder.get("seq") or {}
            d = Path(seq.get("dir") or "")
            if not d.is_absolute():
                d = origen_dir / d
            if not d.is_dir():
                continue
            ya = idx.get("seq:" + d.name.lower())
            if ya:
                holder["seq"] = dict(seq, dir=str(ya.resolve()))
                rep["assets_reusados"] += 1
                continue
            fuera = destino_base / d.name
            if not fuera.exists():
                shutil.copytree(d, fuera)
                rep["assets_nuevos"].append(str(fuera.relative_to(pdir)))
            holder["seq"] = dict(seq, dir=str(fuera.resolve()))
            continue
        src = holder.get(key)
        if not src:
            continue
        p = Path(src)
        if not p.is_absolute():
            p = origen_dir / p
        ya = idx.get(p.name.lower())
        if ya:
            # El mismo archivo que ya teníamos, solo que allá vivía en otro
            # sitio. Se apunta al de casa y no se duplica nada.
            holder[key] = str(ya.resolve())
            rep["assets_reusados"] += 1
            continue
        if p.exists() and pdir not in p.resolve().parents:
            fuera = destino_base / p.name
            if not fuera.exists():
                fuera.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, fuera)
                rep["assets_nuevos"].append(str(fuera.relative_to(pdir)))
            holder[key] = str(fuera.resolve())
        elif p.exists():
            holder[key] = str(p.resolve())
        else:
            rep["avisos"].append("no vino el archivo %s" % p.name)


def merge_back(origen, project_dir, con_cortes=True, on_step=None):
    """Mete la edicion que vuelve en el proyecto de esta maquina."""
    pdir = Path(project_dir).resolve()
    destino = util.read_json(pdir / "project.json")
    if destino is None:
        raise RuntimeError("no hay project.json en %s" % pdir)
    studio.resolve_paths(destino, pdir)

    carpeta, temporal = _abrir(origen)
    try:
        entrante = util.read_json(carpeta / "project.json")
        tl_nuevo = util.read_json(carpeta / "timeline.json")
        if entrante is None or tl_nuevo is None:
            raise RuntimeError("el paquete no trae project.json y timeline.json")

        rep = {"avisos": _mismo_proyecto(destino, entrante),
               "assets_nuevos": [], "assets_reusados": 0,
               "cortes": 0, "items": 0}

        if on_step:
            on_step("copiando los archivos que sumó la otra máquina")
        _traer_assets(tl_nuevo, carpeta, pdir, rep)

        # Los cortes: solo los segmentos, nunca las fuentes.
        if con_cortes and entrante.get("segments"):
            destino["segments"] = entrante["segments"]
            rep["cortes"] = len(entrante["segments"])
            dec = carpeta / "decisions.json"
            if dec.exists():
                shutil.copy2(dec, pdir / "decisions.json")
        studio.save_project(pdir, destino, backup=True)

        # La capa creativa vuelve entera.
        rep["items"] = sum(len(t.get("items") or []) for t in tl_nuevo.get("tracks", []))
        util.write_json(studio.path_of(pdir), tl_nuevo, backup=True)

        rep["proyecto"] = str(pdir)
        rep["respaldos"] = [str(pdir / "project.json.bak"),
                            str(studio.path_of(pdir)) + ".bak"]
        return rep
    finally:
        if temporal:
            shutil.rmtree(temporal, ignore_errors=True)
