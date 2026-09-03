# -*- coding: utf-8 -*-
"""Empaquetar y abrir: un proyecto para pasarlo, o la herramienta entera.

Dos zips distintos, dos problemas distintos:

* **`pack --project`** mete la edicion (cortes, timeline, transcripciones) y
  *todos los assets que la edicion usa* — SFX, musica, overlays, tipografias—
  reescribiendo las rutas a rutas relativas dentro del paquete. Los videos de
  camara quedan fuera salvo que se pidan (`--media`), porque son el 99% del peso
  y el que recibe normalmente ya los tiene.
* **`pack --skill`** mete la herramienta: scripts, editor, studio, stickers y
  plantillas, con un INSTALAR.md.

Abrir un paquete es lo interesante: `project.json` guarda rutas absolutas de la
maquina que lo creo, asi que al desempaquetar hay que **volver a enlazar** cada
archivo buscandolo por nombre en la carpeta de videos que indique quien lo abre.
Lo que no se encuentra se reporta; no se inventa.
"""
from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

from . import studio, util

PACK_VERSION = 1
MANIFEST = "pack.json"

SKILL = Path(__file__).resolve().parent.parent.parent

# Lo que se copia del proyecto tal cual.
PROJECT_FILES = ["project.json", "timeline.json", "decisions.json",
                 "review.md", "qa.md", "disfluencias.md"]
PROJECT_DIRS = ["transcripts", "fonts"]

# Lo que hace falta para que el studio se vea bien sin el material original:
# el video de preview y los dibujos de la pista. Pesan ~1% de los originales.
PREVIEW_DIRS = [("cache/proxy", "proxy"), ("cache/waveform", "waveform"),
                ("cache/filmstrip", "filmstrip")]

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".mts", ".m2ts", ".webm",
             ".wmv", ".mpg", ".mpeg", ".3gp", ".flv", ".ts"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------ recolectar

def referenced_assets(tl):
    """Rutas de archivo a las que apunta el timeline (audio, overlays, seqs)."""
    out = []
    for trk in tl.get("tracks", []):
        for it in trk.get("items", []):
            if it.get("src"):
                out.append(("src", it, "src"))
            seq = it.get("seq") or {}
            if seq.get("dir"):
                out.append(("seq", it, "seq"))
    for tr in tl.get("transitions", []):
        if tr.get("sfx"):
            out.append(("sfx", tr, "sfx"))
    return out


def _seq_files(seq):
    """Los PNG de la secuencia mas su sidecar: sin el, al abrir el paquete el
    overlay no sabria de que habla y no se podria recolocar."""
    from . import overlays
    d = Path(seq.get("dir", ""))
    if not d.is_dir():
        return []
    files = sorted(f for f in d.iterdir()
                   if f.is_file() and f.suffix.lower() == ".png")
    side = d / overlays.SIDECAR
    if files and side.exists():
        files.append(side)
    return files


def pack_project(project_dir, out_path, with_media=False, preview=False,
                 on_step=None):
    """Escribe el .zip del proyecto y devuelve el informe."""
    pdir = Path(project_dir).resolve()
    project = util.read_json(pdir / "project.json")
    if project is None:
        raise RuntimeError("no hay project.json en %s" % pdir)
    studio.resolve_paths(project, pdir)
    tl = util.read_json(studio.path_of(pdir)) or {}
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "vcut_pack": PACK_VERSION,
        "created_at": _now(),
        "name": project.get("name") or pdir.name,
        "origin": str(pdir),
        "has_media": bool(with_media),
        # Un paquete de revision: sin material original, pero con todo lo que
        # el studio necesita para verse. Quien lo abre ajusta y devuelve; el
        # render final se hace en la maquina que tiene los originales.
        "preview": bool(preview),
        "sequence": project.get("sequence"),
        "stats": project.get("stats"),
        "media": [],
        "assets": {},
        "warnings": [],
    }

    # Los assets se copian a `assets/<categoria>/<archivo>` y las rutas del
    # timeline se reescriben a esa ruta relativa: asi el paquete se abre en
    # cualquier maquina sin tocar nada a mano.
    tl_out = util.read_json(studio.path_of(pdir)) or {}
    amap = {}

    def asset_target(src):
        p = Path(src)
        kind = "audio" if p.suffix.lower() in (".wav", ".mp3", ".m4a", ".aac",
                                               ".ogg", ".flac", ".opus") else "media"
        return "assets/%s/%s" % (kind, p.name)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in PROJECT_FILES:
            f = pdir / name
            if f.exists():
                z.write(f, name)
        for d in PROJECT_DIRS:
            base = pdir / d
            if not base.is_dir():
                continue
            for f in sorted(base.rglob("*")):
                if f.is_file():
                    z.write(f, str(Path(d) / f.relative_to(base)).replace("\\", "/"))

        # ------- assets del timeline
        for kind, holder, key in referenced_assets(tl_out):
            if key == "seq":
                seq = holder["seq"]
                files = _seq_files(seq)
                if not files:
                    manifest["warnings"].append(
                        "sin secuencia para %s" % (holder.get("id") or "?"))
                    continue
                name = Path(seq["dir"]).name
                rel = "assets/seq/%s" % name
                if on_step:
                    on_step("%s (%d archivos)" % (name, len(files)))
                for f in files:
                    z.write(f, "%s/%s" % (rel, f.name))
                holder["seq"] = dict(seq, dir=rel)
                manifest["assets"][rel] = {"kind": "seq", "files": len(files)}
                continue
            src = holder.get(key)
            if not src:
                continue
            p = Path(src)
            if not p.exists():
                manifest["warnings"].append("falta el asset %s" % src)
                continue
            rel = amap.get(str(p).lower())
            if rel is None:
                rel = asset_target(p)
                z.write(p, rel)
                amap[str(p).lower()] = rel
                manifest["assets"][rel] = {"kind": kind, "size": p.stat().st_size}
                if on_step:
                    on_step(p.name)
            holder[key] = rel

        # ------- tipografias que usan los estilos
        from . import textlayer
        for st in (tl_out.get("styles") or {}).values():
            for k in ("font", "keyword_font"):
                fname = st.get(k)
                if not fname:
                    continue
                fp = textlayer.find_font(fname, pdir)
                if not fp:
                    manifest["warnings"].append("no encuentro la fuente %s" % fname)
                    continue
                rel = "fonts/%s" % Path(fp).name
                if rel not in manifest["assets"]:
                    z.write(fp, rel)
                    manifest["assets"][rel] = {"kind": "font"}

        # ------- originales
        for s in project.get("sources", []):
            entry = {"id": s["id"], "name": s["name"], "size": s.get("size"),
                     "duration": s.get("duration"), "path": s.get("path")}
            if with_media and s.get("path") and Path(s["path"]).exists():
                rel = "media/%s" % Path(s["path"]).name
                if on_step:
                    on_step(s["name"])
                z.write(s["path"], rel)
                entry["packed"] = rel
            manifest["media"].append(entry)

        # ------- preview: proxies, ondas y miniaturas
        if preview:
            faltan = [s["name"] for s in project.get("sources", [])
                      if not (s.get("proxy") and Path(s["proxy"]).exists())]
            if faltan:
                manifest["warnings"].append(
                    "sin proxy: %s. Genéralos con `vcut media --proxy-all` "
                    "o esos clips se verán en negro." % ", ".join(faltan[:6]))
            for origen, destino in PREVIEW_DIRS:
                base = pdir / origen
                if not base.is_dir():
                    continue
                n = 0
                for f in sorted(base.rglob("*")):
                    if f.is_file():
                        z.write(f, "preview/%s/%s" % (destino, f.name))
                        n += 1
                if n and on_step:
                    on_step("%s (%d archivos)" % (destino, n))
                manifest["assets"]["preview/%s" % destino] = {"kind": "preview",
                                                              "files": n}

        z.writestr("timeline.json", util.json_dumps(tl_out))
        z.writestr(MANIFEST, util.json_dumps(manifest))
        z.writestr("LEEME.md", _readme(manifest))

    return {"zip": str(out), "size": out.stat().st_size,
            "assets": len(manifest["assets"]), "media": len(manifest["media"]),
            "con_media": bool(with_media), "avisos": manifest["warnings"]}


def _readme(m):
    if m.get("preview"):
        return _readme_preview(m)
    return """# %s

Paquete de vcut studio (v%d), creado el %s.

- Videos originales incluidos: **%s**
- Assets incluidos: %d (sonidos, overlays, tipografias)

## Abrirlo

```bash
python vcut.py unpack "este-archivo.vcutpack" --project "C:/ruta/proyecto-nuevo" %s
python vcut.py media  --project "C:/ruta/proyecto-nuevo" --proxy-all --height 1080
python vcut.py studio --project "C:/ruta/proyecto-nuevo"
```

`unpack` vuelve a enlazar los videos buscandolos **por nombre** dentro de
`--media`. Los que no encuentre se listan; el proyecto abre igual y esos clips
se veran en negro hasta que aparezcan los archivos.

## Lo que hay dentro

| ruta | que es |
|---|---|
| `project.json` | los cortes: que trozo de que archivo y en que orden |
| `timeline.json` | la capa creativa: texto, zooms, transiciones, audio |
| `transcripts/` | la transcripcion con tiempos por palabra (no hay que re-transcribir) |
| `assets/` | sonidos, overlays y secuencias de PNG que usa la edicion |
| `fonts/` | las tipografias de los estilos de texto |
| `media/` | los videos originales, solo si se empaqueto con --media |
""" % (m["name"], m["vcut_pack"], m["created_at"][:10],
       "si" if m["has_media"] else "no (hay que indicar la carpeta al abrir)",
       len(m["assets"]),
       "" if m["has_media"] else '--media "C:/ruta/a/los/videos"')


def _readme_preview(m):
    return """# %s — paquete de revision

Creado el %s. **No trae los videos originales**: trae los proxies, que es el
mismo material a menor resolucion. Pesa unas 50 veces menos y el editor se ve
igual.

Con esto podes ajustar todo —cortes, zooms, textos, subtitulos, transiciones,
sonidos— sin necesitar una maquina potente: aca no se transcribe ni se
generan proxies, que es lo que cuesta. El render final lo hace quien tiene los
originales.

## Abrirlo

```bash
python vcut.py unpack "este-archivo.vcutpack" --project "C:/ruta/mi-revision"
python vcut.py studio --project "C:/ruta/mi-revision"
```

No hace falta `--media`: los proxies ya vienen dentro y se enlazan solos.

## Devolverlo

Cuando termines, `Ctrl+S` en el studio y:

```bash
python vcut.py pack --project "C:/ruta/mi-revision" --out "revisado.vcutpack"
```

Eso deja un paquete liviano con tus cambios. Quien te lo mando lo mete en su
proyecto con:

```bash
python vcut.py merge "revisado.vcutpack" --project "C:/su/proyecto"
```

Sus originales no se tocan: del paquete solo entran las decisiones (los cortes
y la capa creativa), nunca las rutas del material.

## Un aviso

El boton **Renderizar** aca sacaria un MP4 desde los proxies, o sea a menor
calidad. Sirve para verlo, no para publicar. El bueno lo saca la otra maquina.
""" % (m["name"], m["created_at"][:10])


# ------------------------------------------------------------ abrir

def unpack_project(zip_path, project_dir, media_dir=None, on_step=None):
    """Extrae el paquete y vuelve a enlazar rutas. Devuelve el informe."""
    zp = Path(zip_path)
    pdir = Path(project_dir).resolve()
    pdir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        if MANIFEST not in names:
            raise RuntimeError("%s no parece un paquete de vcut" % zp.name)
        manifest = util.json_loads(z.read(MANIFEST).decode("utf-8"))
        if on_step:
            on_step("extrayendo %d archivos" % len(names))
        z.extractall(pdir)

    project = util.read_json(pdir / "project.json")
    tl = util.read_json(pdir / "timeline.json")
    if project is None:
        raise RuntimeError("el paquete no trae project.json")

    rep = {"nombre": manifest.get("name"), "enlazados": [], "sin_enlazar": [],
           "assets": 0, "avisos": list(manifest.get("warnings") or [])}

    # ------- originales
    es_preview = bool(manifest.get("preview"))
    project["preview_only"] = es_preview
    index = _media_index(media_dir) if media_dir else {}
    for s in project.get("sources", []):
        # En un paquete de revision el proxy hace de material: el studio
        # reproduce `proxy or path`, asi que enganchando los dos al mismo
        # archivo todo funciona sin tener los originales delante.
        if es_preview:
            prox = pdir / "preview" / "proxy" / ("%s.mp4" % s["id"])
            if prox.exists():
                s["origen"] = s.get("path")
                s["path"] = str(prox.resolve())
                s["proxy"] = str(prox.resolve())
                onda = pdir / "preview" / "waveform" / ("%s.bin" % s["id"])
                if onda.exists():
                    s["waveform"] = str(onda.resolve())
                tira = pdir / "preview" / "filmstrip" / ("%s.jpg" % s["id"])
                if tira.exists():
                    # `filmstrip` es un dict con la geometria de la tira (cols,
                    # tw, interval...). Solo cambia donde vive el JPG: si se
                    # reemplaza entero, la timeline no sabe como recortarlo.
                    meta = s.get("filmstrip")
                    if isinstance(meta, dict):
                        s["filmstrip"] = dict(meta, url=str(tira.resolve()))
                    else:
                        s["filmstrip"] = str(tira.resolve())
                rep["enlazados"].append({"id": s["id"], "name": s["name"],
                                         "desde": "el proxy del paquete"})
                continue
            rep["sin_enlazar"].append({"id": s["id"], "name": s["name"],
                                       "motivo": "el paquete no trae su proxy"})
            continue

        packed = next((m.get("packed") for m in manifest.get("media", [])
                       if m["id"] == s["id"]), None)
        if packed and (pdir / packed).exists():
            s["path"] = str((pdir / packed).resolve())
            rep["enlazados"].append({"id": s["id"], "name": s["name"],
                                     "desde": "el paquete"})
            continue
        hit = index.get(s["name"].lower())
        if hit:
            s["path"] = str(hit)
            rep["enlazados"].append({"id": s["id"], "name": s["name"],
                                     "desde": str(hit.parent)})
        else:
            rep["sin_enlazar"].append({"id": s["id"], "name": s["name"],
                                       "tamano": s.get("size")})
        # Los assets de preview del emisor no sirven aca.
        s["proxy"] = None
        s["waveform"] = None
        s["filmstrip"] = None

    studio.save_project(pdir, project)

    # ------- rutas del timeline
    if tl:
        for _kind, holder, key in referenced_assets(tl):
            if key == "seq":
                d = holder["seq"].get("dir") or ""
                if not Path(d).is_absolute():
                    holder["seq"] = dict(holder["seq"],
                                         dir=str((pdir / d).resolve()))
                    rep["assets"] += 1
                continue
            src = holder.get(key) or ""
            if src and not Path(src).is_absolute():
                holder[key] = str((pdir / src).resolve())
                rep["assets"] += 1
            elif src and not Path(src).exists():
                rep["avisos"].append("ruta que ya no existe: %s" % src)
        util.write_json(studio.path_of(pdir), tl)

    rep["proyecto"] = str(pdir)
    rep["siguiente"] = ("vcut media --project \"%s\" --proxy-all --height 1080  "
                        "y luego  vcut studio --project \"%s\"" % (pdir, pdir))
    return rep


def _media_index(media_dir):
    """nombre de archivo en minusculas -> ruta, buscando en profundidad."""
    base = Path(media_dir).expanduser().resolve()
    out = {}
    if not base.exists():
        return out
    for f in base.rglob("*"):
        if f.is_file() and f.suffix.lower() in VIDEO_EXT:
            out.setdefault(f.name.lower(), f)
    return out


# ------------------------------------------------------------ la herramienta

SKILL_SKIP_DIRS = {"__pycache__", ".git", "node_modules"}
SKILL_SKIP_SUFFIX = {".bak", ".tmp", ".pyc", ".log"}


def pack_skill(out_path, on_step=None):
    """Zip de la skill entera, lista para que otro la descomprima y la use."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(SKILL.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(SKILL)
            if any(part in SKILL_SKIP_DIRS for part in rel.parts):
                continue
            if f.suffix.lower() in SKILL_SKIP_SUFFIX:
                continue
            z.write(f, "video-cut/%s" % str(rel).replace("\\", "/"))
            n += 1
            if on_step and n % 40 == 0:
                on_step("%d archivos" % n)
        z.writestr("INSTALAR.md", _install_md())
    return {"zip": str(out), "size": out.stat().st_size, "archivos": n}


def _install_md():
    return """# Instalar vcut studio

## 1. Copiar la skill

Descomprime este zip y mueve la carpeta `video-cut` a:

- Windows: `C:/Users/<TU-USUARIO>/.claude/skills/video-cut`
- macOS / Linux: `~/.claude/skills/video-cut`

## 2. Lo que hace falta tener

| que | para que | como |
|---|---|---|
| **Python 3.10+** | todo | python.org |
| **ffmpeg y ffprobe** en el PATH | cortar, render, proxies | `winget install Gyan.FFmpeg` / `brew install ffmpeg` |
| **flask, numpy, pillow** | editor, ondas, medir texto | `pip install flask numpy pillow` |
| **faster-whisper** | transcribir | `pip install faster-whisper` |
| Chrome o Edge | rasterizar los stickers | ya lo tienes |

Los stickers vienen ya rasterizados. Si cambias un SVG:
`python vcut.py stickers --force`.

## 3. Probar

```bash
VCUT="$HOME/.claude/skills/video-cut/scripts/vcut.py"

# de cero, con una carpeta de videos
python $VCUT run "C:/ruta/videos" --project "C:/ruta/proyecto"
python $VCUT template apply --project "C:/ruta/proyecto" --name tiktok
python $VCUT studio --project "C:/ruta/proyecto"

# o abriendo un paquete que te hayan pasado
python $VCUT unpack "algo.vcutpack" --project "C:/ruta/proyecto" --media "C:/ruta/videos"
```

## 4. Un aviso sobre la GPU

La transcripcion usa CPU si faltan las DLL de CUDA. Para acelerarla ~10x:
`pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`. El render usa NVENC si el
driver lo permite, y si no cae a libx264 solo. Las dos cosas se detectan
probando, no hay que configurar nada.

Todo lo demas esta en `SKILL.md` y en `references/`.
"""
