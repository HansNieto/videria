# -*- coding: utf-8 -*-
"""Compartir un proyecto por git: uno monta, el otro ajusta, el primero renderiza.

Es el mismo reparto que el paquete de revision, pero sin mandarse archivos a
mano. Lo que viaja por el repo:

- `project.json` y `timeline.json`, que son texto: cada push se lee como un
  diff de verdad (que zoom cambio, que texto se movio);
- `transcripts/`, que ya no hay que volver a calcular;
- `preview/`, los proxies y los dibujos de la pista, que se suben una vez;
- `assets/`, los sonidos y overlays que use la edicion.

Lo que **no** viaja: el material original (pesa cientos de veces mas), la
carpeta `cache/` y los MP4 de `exports/`.

El truco que hace que esto funcione en dos maquinas es `local.json`: esta en el
.gitignore y dice donde tiene cada una sus originales. `project.json` se
commitea con rutas relativas al proyecto, asi que el mismo archivo abre bien en
las dos. Quien no tiene originales abre igual, reproduciendo los proxies.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import media, studio, util

GITIGNORE = """# Lo que es de cada máquina, no del proyecto.
local.json
credenciales.json

# Se regenera solo, y pesa.
cache/
exports/
broll/cache/

# Respaldos automáticos.
*.bak
*.tmp
"""

GITATTRIBUTES = """* text=auto

# El workflow corre en Linux: si llega con CRLF, falla.
*.yml text eol=lf
*.sh  text eol=lf

# Nada que git deba tocar.
*.mp4 binary
*.jpg binary
*.bin binary
"""

AVISO_YML = r"""# Avisa cuando la otra persona sube una revisión.
#
# GitHub no notifica los push a secas, así que esto abre un issue mencionando a
# quien tiene que renderizar. Llega por correo y al móvil.
#
# Todo lo que viene del commit (el mensaje, los archivos) entra por `env:` y no
# interpolado dentro del script: un mensaje con comillas rompería el comando, y
# uno escrito con mala idea podría ejecutar algo.
name: Aviso de revisión

on:
  push:
    branches: [main, master, revision]
    paths:
      - 'timeline.json'
      - 'project.json'

permissions:
  contents: read
  issues: write

jobs:
  avisar:
    # Los push propios no tienen que avisarse a uno mismo.
    if: github.actor != '%(duenio)s'
    runs-on: ubuntu-latest
    steps:
      - name: Abrir el aviso
        env:
          GH_TOKEN: ${{ github.token }}
          REPO: ${{ github.repository }}
          QUIEN: ${{ github.actor }}
          SHA: ${{ github.sha }}
          MENSAJE: ${{ github.event.head_commit.message }}
          TOCADOS: ${{ join(github.event.head_commit.modified, ', ') }}
        run: |
          {
            echo "@%(duenio)s hay cambios para renderizar."
            echo
            echo "> $MENSAJE"
            echo
            echo "Tocó: \`$TOCADOS\`"
            echo
            echo '```'
            echo 'git -C tu/proyecto pull'
            echo 'python $VCUT render --project tu/proyecto'
            echo '```'
            echo
            echo "[Ver el cambio](https://github.com/$REPO/commit/$SHA)"
          } > cuerpo.md
          gh issue create --repo "$REPO"             --title "Revisión lista de $QUIEN"             --assignee "%(duenio)s"             --body-file cuerpo.md
"""


LEEME = """# %(nombre)s

Proyecto de vídeo compartido. Se edita con
[vcut](https://github.com/%(duenio)s/videria); el material original **no está
aquí** (pesa demasiado): lo que hay son los proxies, que es el mismo vídeo a
menor resolución. Alcanza para ajustar todo.

## La primera vez

```bash
git clone %(url)s mi-revision
cd mi-revision
python $VCUT studio --project .
```

`$VCUT` es `~/.claude/skills/video-cut/scripts/vcut.py`. Si no tenés vcut,
está en https://github.com/%(duenio)s/videria con su instalador.

## Cada vez que trabajás

```bash
git pull                                  # traé lo último antes de tocar nada
python $VCUT studio --project .           # ajustá: cortes, zooms, textos, sonidos
                                          # Ctrl+S en el studio para guardar
git add -A && git commit -m "ajusté los zooms del principio"
git push
```

Al hacer push se abre solo un aviso para quien renderiza. No hace falta
escribirle.

## Lo que no podés hacer desde aquí

El botón **Renderizar** te lo va a impedir, y con razón: sin el material
original el MP4 saldría de los proxies, a 540p estirado. Para ver cómo va,
usá el **borrador** (tecla `B`), que para eso está.

## Si dos tocan a la vez

`timeline.json` es un archivo grande y git no sabe fusionarlo por vos. La regla
es simple: **uno a la vez**. Antes de empezar, `git pull`; al terminar, `push`.
Si aun así choca, gana quien tenga el trabajo más reciente y el otro rehace.
"""


def _escribir(ruta, texto):
    """Escribe con LF pase lo que pase."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline=chr(10)) as f:
        f.write(texto)


def _git(args, cwd, check=True):
    r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args),
                                           (r.stderr or r.stdout).strip()[:200]))
    return (r.stdout or "").strip()


def _identidad(pdir, duenio):
    """Sin `user.email` configurado, `git commit` falla y no dice nada útil.

    Se mira la del sistema y, si no hay, se pone una para este repo con el
    formato de correo oculto de GitHub, que es el que no filtra tu dirección.
    """
    quien = _git(["config", "user.email"], pdir, check=False)
    if quien:
        return None
    correo = "%s@users.noreply.github.com" % duenio
    _git(["config", "user.name", duenio], pdir)
    _git(["config", "user.email", correo], pdir)
    return correo


def _hay(cmd):
    try:
        subprocess.run([cmd, "--version"], capture_output=True, check=True)
        return True
    except Exception:                                    # noqa: BLE001
        return False


def preparar(project_dir, duenio, nombre=None, url=None):
    """Deja el proyecto listo para commitear: rutas, .gitignore, aviso y LEEME."""
    pdir = Path(project_dir).resolve()
    project = util.read_json(pdir / "project.json")
    if project is None:
        raise RuntimeError("no hay project.json en %s" % pdir)
    studio.resolve_paths(project, pdir)

    hechos = {"avisos": []}

    # Recupera cachés locales cuando un proyecto fue renombrado o movido antes
    # de convertirlo a formato compartible. El nombre del archivo por fuente es
    # estable y evita guardar la ruta absoluta de la máquina que hizo la preedición.
    for s in project.get("sources", []):
        for key, sub in (("proxy", "proxy"), ("waveform", "waveform")):
            value = s.get(key)
            if value and not Path(value).exists():
                candidate = pdir / "cache" / sub / Path(value).name
                if candidate.is_file():
                    s[key] = str(candidate)
        filmstrip = s.get("filmstrip")
        value = filmstrip.get("url") if isinstance(filmstrip, dict) else filmstrip
        if value and not Path(value).exists():
            candidate = pdir / "cache" / "filmstrip" / Path(value).name
            if candidate.is_file():
                s["filmstrip"] = (dict(filmstrip, url=str(candidate))
                                  if isinstance(filmstrip, dict) else str(candidate))

    # Sin proxies no hay nada que compartir: el otro veria clips en negro.
    sin_proxy = [s.get("name") for s in project.get("sources", [])
                 if not (s.get("proxy") and Path(s["proxy"]).exists())]
    if sin_proxy:
        hechos["avisos"].append(
            "%d clips sin proxy (%s%s). Corré `vcut media --proxy-all` antes "
            "de subir, o el otro los verá en negro."
            % (len(sin_proxy), ", ".join(str(x) for x in sin_proxy[:3]),
               "…" if len(sin_proxy) > 3 else ""))

    # Los proxies pasan a vivir dentro del proyecto, en preview/, que es lo que
    # se commitea. En cache/ estarian ignorados.
    movidos = 0
    destino = pdir / "preview" / "proxy"
    for s in project.get("sources", []):
        prox = s.get("proxy")
        if not prox or not Path(prox).exists():
            continue
        destino.mkdir(parents=True, exist_ok=True)
        nuevo = media.build_review_proxy(s, destino)
        s["proxy"] = str(nuevo)
        for stale in destino.glob("%s-*.mp4" % s["id"]):
            if stale.resolve() != nuevo.resolve():
                stale.unlink()
        movidos += 1
    for clave, sub, ext in (("waveform", "waveform", ".bin"),
                            ("filmstrip", "filmstrip", ".jpg")):
        for s in project.get("sources", []):
            v = s.get(clave)
            ruta = v.get("url") if isinstance(v, dict) else v
            if not ruta or not Path(ruta).exists():
                continue
            p = Path(ruta)
            fuera = pdir / "preview" / sub
            if p.parent.resolve() == fuera.resolve():
                continue
            fuera.mkdir(parents=True, exist_ok=True)
            nuevo = fuera / p.name
            if not nuevo.exists():
                nuevo.write_bytes(p.read_bytes())
            s[clave] = dict(v, url=str(nuevo)) if isinstance(v, dict) else str(nuevo)
    hechos["preview"] = movidos

    # Esto separa las rutas: lo de dentro queda relativo en project.json y los
    # originales se van a local.json.
    studio.save_project(pdir, project, backup=True)
    timeline = studio.load(pdir, project, create=False)
    if timeline is not None:
        studio.save(pdir, timeline)
    overlay_index_path = pdir / "assets" / "overlays" / "index.json"
    overlay_index = util.read_json(overlay_index_path)
    if isinstance(overlay_index, dict):
        for entry in overlay_index.values():
            seq = entry.get("seq") if isinstance(entry, dict) else None
            if isinstance(seq, dict) and seq.get("dir"):
                seq["dir"] = studio.portable_asset(seq["dir"], pdir)
        util.write_json(overlay_index_path, overlay_index)

    # Estos tres archivos siempre con LF. El workflow corre en un runner de
    # Linux: un retorno de carro al final de cada linea le cambiaria el
    # nombre al archivo del cuerpo y el aviso fallaria. En Windows, escribir
    # texto sin decir nada traduce a CRLF.
    _escribir(pdir / ".gitignore", GITIGNORE)
    _escribir(pdir / ".gitattributes", GITATTRIBUTES)
    wf = pdir / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    _escribir(wf / "aviso.yml", AVISO_YML % {"duenio": duenio})
    _escribir(pdir / "LEEME.md",
              LEEME % {"nombre": nombre or project.get("name") or pdir.name,
                       "duenio": duenio, "url": url or "<url-del-repo>"})
    hechos["archivos"] = [".gitignore", ".gitattributes",
                          ".github/workflows/aviso.yml", "LEEME.md"]
    return hechos, project


def init(project_dir, duenio, privado=True, crear=True, nombre=None):
    """Prepara, hace el primer commit y (si se puede) crea el repo en GitHub."""
    pdir = Path(project_dir).resolve()
    if not _hay("git"):
        raise RuntimeError("no encuentro git en el PATH")

    hechos, project = preparar(pdir, duenio, nombre=nombre)

    if not (pdir / ".git").is_dir():
        _git(["init", "-b", "main"], pdir)
        hechos["git"] = "repo nuevo"
    else:
        hechos["git"] = "ya era un repo"

    puesta = _identidad(pdir, duenio)
    if puesta:
        hechos["avisos"].append(
            "git no tenía identidad configurada en esta máquina; para este "
            "repo queda como %s <%s>" % (duenio, puesta))

    _git(["add", "-A"], pdir)
    if _git(["status", "--porcelain"], pdir):
        _git(["commit", "-m", "Proyecto de vídeo listo para revisar"], pdir)
        hechos["commit"] = _git(["rev-parse", "--short", "HEAD"], pdir, check=False)
    else:
        hechos["commit"] = None

    hechos["remoto"] = None
    if crear and _hay("gh"):
        nom = nombre or pdir.name
        r = subprocess.run(
            ["gh", "repo", "create", nom,
             "--private" if privado else "--public",
             "--source", ".", "--remote", "origin", "--push",
             "--description", "Proyecto de vídeo de vcut: proxies y timeline, "
                              "sin el material original"],
            cwd=str(pdir), capture_output=True, text=True)
        if r.returncode == 0:
            hechos["remoto"] = (r.stdout or r.stderr).strip().splitlines()[0]
            url = hechos["remoto"]
            _escribir(pdir / "LEEME.md",
                      LEEME % {"nombre": nombre or project.get("name") or pdir.name,
                               "duenio": duenio, "url": url})
            _git(["add", "LEEME.md"], pdir)
            _git(["commit", "-m", "LEEME con la url del repo"], pdir, check=False)
            _git(["push", "-q", "origin", "main"], pdir, check=False)
        else:
            hechos["avisos"].append(
                "no pude crear el repo en GitHub: %s"
                % (r.stderr or r.stdout).strip()[:160])
    elif crear:
        hechos["avisos"].append("no encuentro `gh`; creá el repo a mano y hacé "
                                "`git remote add origin <url> && git push -u origin main`")
    return hechos


def estado(project_dir):
    """Que hay sin subir, y si esta puesto lo que hace falta."""
    pdir = Path(project_dir).resolve()
    if not (pdir / ".git").is_dir():
        return {"repo": False,
                "nota": "este proyecto todavía no es un repo: `vcut repo init`"}
    sucio = _git(["status", "--porcelain"], pdir, check=False)
    project = util.read_json(pdir / "project.json") or {}
    studio.resolve_paths(project, pdir)
    con = sum(1 for s in project.get("sources", []) if s.get("tiene_original"))
    return {
        "repo": True,
        "rama": _git(["rev-parse", "--abbrev-ref", "HEAD"], pdir, check=False),
        "remoto": _git(["remote", "get-url", "origin"], pdir, check=False) or None,
        "sin_subir": [l[3:] for l in sucio.splitlines()][:20],
        "originales": "%d de %d fuentes" % (con, len(project.get("sources", []))),
        "puede_renderizar_final": con == len(project.get("sources", [])) and con > 0,
        "aviso_configurado": (pdir / ".github" / "workflows" / "aviso.yml").exists(),
    }
