# -*- coding: utf-8 -*-
"""B-roll automatico: video de stock elegido por lo que se esta diciendo.

Un video de alguien hablando a camara se hace largo. Esto lo corta con planos
de recurso: lee la transcripcion, saca de cada tramo las dos palabras que de
verdad lo describen, busca un clip en Pexels y lo deja colocado justo encima de
esa frase, como un item de la pista de overlays.

Tres decisiones que explican el resto del archivo:

1. **El clip se normaliza al descargarlo**, no al renderizar. Se recorta al
   encuadre del proyecto (cover), se le quita el audio y se deja a la duracion
   pedida. Asi el item entra en el render y en el preview sin tocar ninguno de
   los dos: para ellos es un overlay mas, del tamano exacto del lienzo.
2. **Las palabras se eligen por rareza**, no por frecuencia. Una palabra que
   aparece en todos los tramos ("negocio", si el video va de negocios) no
   distingue nada; la que aparece en dos describe *ese* tramo.
3. **Nada se coloca a ciegas.** Si la busqueda no devuelve nada decente, ese
   tramo se queda sin b-roll y se reporta. Un plano de recurso que no viene a
   cuento se nota mas que la falta de plano.

La clave de Pexels se saca, por este orden, de la variable de entorno
`PEXELS_API_KEY`, de `<proyecto>/credenciales.json` o de `~/.vcut/credenciales.json`.
Nunca se escribe en el proyecto ni se imprime.
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from . import render, studio, util

API = "https://api.pexels.com"
TIMEOUT = 30
UA = "vcut/1.0 (+https://github.com/HansNieto/videria)"

# Palabras que no describen nada por si solas. Es la lista de `overlays.py` mas
# los verbos y muletillas que salen en cualquier frase hablada.
STOP = set("""
a al ante antes como con contra de del desde donde durante en entre hacia hasta
la las lo los mediante para por que se segun sin so sobre tras un una unas uno
unos y o u e es esta estan hay ser estar tener hacer poder decir ir ver dar
saber querer llegar pasar deber poner parecer quedar creer hablar llevar dejar
seguir encontrar llamar venir pensar salir volver tomar conocer vivir sentir
mirar contar empezar esperar buscar existir entrar trabajar escribir perder
producir ocurrir entender pedir recibir recordar terminar permitir aparecer
conseguir comenzar servir sacar necesitar mantener resultar leer caer cambiar
presentar crear abrir considerar oir acabar convertir ganar formar traer partir
morir aceptar realizar suponer comprender lograr explicar preguntar tocar
reconocer estudiar alcanzar nacer dirigir correr utilizar pagar ayudar gustar
disenar conectar aplicar aprender atender responder comprar vender usar activar
integrar automatizar configurar instalar descargar registrar mostrar indicar
significar implicar depender funcionar generar detectar revisar validar cerrar
resolver decidir delegar documentar organizar gestionar medir probar ajustar
elegir evitar reducir aumentar mejorar sumar restar contratar despedir
muy mas menos tan tanto todo todos toda todas nada nadie algo alguien cada
mismo misma propio propia otro otra otros otras cuando cuanto porque pero sino
aunque mientras entonces luego despues ahora aqui alli asi bien mal solo sola
si no ni ya tambien tampoco siempre nunca casi cosa cosas vez veces parte
manera forma tipo caso ejemplo momento tiempo dia dias ano anos gente persona
personas hoy manana ayer aca alla eso esto esa ese esos esas aquel aquella
mi tu su nuestro vuestro me te le nos os les yo el ella ellos ellas usted
""".split())

MIN_LARGO = 4          # letras. "ver" o "dos" no son una busqueda.
MIN_PALABRAS = 1       # sin al menos una palabra util no se busca nada

# Los infinitivos de arriba no atrapan las conjugaciones, y "debe" o "quieres"
# no describen ninguna imagen. En vez de escribir la tabla entera de la
# conjugacion castellana, se prueba al reves: se le quita la terminacion a la
# palabra y se mira si el resto mas -ar/-er/-ir es un verbo conocido.
VERBOS = set(w for w in STOP if w.endswith(("ar", "er", "ir")) and len(w) > 3)

TERMINACIONES = (
    "andose", "iendose", "aramos", "ieramos", "abamos", "iamos", "aremos",
    "eremos", "iremos", "asteis", "isteis", "ariamos", "eriamos", "iriamos",
    "ando", "iendo", "aron", "ieron", "aban", "ian", "amos", "emos", "imos",
    "aste", "iste", "aria", "eria", "iria", "aran", "eran", "iran", "ados",
    "idos", "adas", "idas", "ara", "iera", "ase", "iese", "aba", "ado", "ido",
    "ada", "ida", "are", "ere", "ire", "as", "es", "an", "en", "os", "is",
    "io", "ia", "e", "a", "o",
)
# Enclíticos: "pasarle", "hacerlo", "decirnos" siguen siendo verbos.
ENCLITICOS = ("selo", "sela", "seles", "melo", "mela", "telo", "tela",
              "nosla", "noslo", "le", "les", "la", "las", "lo", "los",
              "me", "te", "se", "nos")

# Los que no siguen ninguna regla. Solo las formas que de verdad se hablan.
IRREGULARES = set("""
soy eres somos sois son fui fuiste fue fuimos fueron sea seas seamos sean
estoy estas estamos estais estan estuve estuvo estuvimos esten
tengo tienes tiene tenemos teneis tienen tuve tuvo tuvimos tuvieron tenga
quiero quieres quiere queremos quieren quise quiso quisieron quiera
puedo puedes puede podemos podeis pueden pude pudo pudimos pudieron pueda
hago haces hace hacemos haceis hacen hice hizo hicimos hicieron haga
voy vas vamos vais van fuera fueras hubiera hubo habia habian
he has ha hemos habeis han haya hayas hayan habre habras habra habremos habran
digo dices dice decimos dicen dije dijo dijimos dijeron diga
veo ves vemos veis ven vio vimos vieron vea doy das damos dan dio dieron
se sabes sabe sabemos saben supe supo sepa pongo pones pone ponemos ponen
vengo vienes viene venimos vienen vino vinieron salgo sales sale salimos salen
""".split())


def _es_adverbio(t):
    """Los -mente no se pueden fotografiar. "simplemente", "completamente"."""
    return len(t) > 7 and t.endswith("mente")


def _es_verbo(t):
    """Heuristica: ¿esta palabra es una forma verbal?

    Se equivoca a favor de conservar: si duda, dice que no, porque perder un
    sustantivo bueno cuesta mas que colar un verbo.
    """
    if t in IRREGULARES:
        return True
    if t in VERBOS or t.endswith(("ar", "er", "ir")) and t[:-2] + t[-2:] in VERBOS:
        return True
    for enc in ENCLITICOS:
        if t.endswith(enc) and len(t) - len(enc) >= 4:
            raiz = t[:-len(enc)]
            if raiz in VERBOS or raiz.endswith(("ar", "er", "ir")):
                return True
    for term in TERMINACIONES:
        if not t.endswith(term) or len(t) - len(term) < 2:
            continue
        raiz = t[:-len(term)]
        if raiz in VERBOS:                      # futuro: aprender|as, dira|n
            return True
        if any(raiz + suf in VERBOS for suf in ("ar", "er", "ir")):
            return True
    return False


# ------------------------------------------------------------ credenciales

def api_key(project_dir=None, provider="pexels"):
    """La clave, o None. Entorno primero: es lo que no deja rastro en disco."""
    env = os.environ.get("%s_API_KEY" % provider.upper())
    if env and env.strip():
        return env.strip()
    campo = "%s_api_key" % provider
    candidatos = []
    if project_dir:
        candidatos.append(Path(project_dir) / "credenciales.json")
    candidatos.append(Path.home() / ".vcut" / "credenciales.json")
    for p in candidatos:
        if p.exists():
            datos = util.read_json(p, {}) or {}
            v = (datos.get(campo) or "").strip()
            if v:
                return v
    return None


def donde_va_la_clave(project_dir=None):
    """Texto para el error: donde puede ponerla quien no la tiene."""
    destino = (Path(project_dir) / "credenciales.json") if project_dir \
        else (Path.home() / ".vcut" / "credenciales.json")
    return ('falta la clave de Pexels. Consiguela gratis en '
            'https://www.pexels.com/api/ y ponla en la variable de entorno '
            'PEXELS_API_KEY, o en %s como {"pexels_api_key": "..."}' % destino)


# ------------------------------------------------------------ palabras clave

def _idf(segmentos):
    """En cuantos tramos aparece cada palabra. Sirve para medir su rareza."""
    doc = Counter()
    for s in segmentos:
        for w in set(_palabras(s.get("text", ""))):
            doc[w] += 1
    return doc


def _palabras(texto):
    return [t for t in util.tokens(texto or "")
            if t not in STOP and len(t) >= MIN_LARGO and not t.isdigit()
            and not _es_verbo(t) and not _es_adverbio(t)]


def consulta(texto, doc_freq, total, n=2):
    """Las `n` palabras que mejor describen este tramo.

    Se puntua rareza (idf) por frecuencia dentro del tramo. Empata a favor de
    la palabra mas larga, que en castellano suele ser la mas concreta.
    """
    tf = Counter(_palabras(texto))
    if len(tf) < MIN_PALABRAS:
        return ""
    puntos = {}
    for w, c in tf.items():
        idf = math.log((total + 1) / float(doc_freq.get(w, 0) + 1)) + 1.0
        puntos[w] = (c ** 0.5) * idf + len(w) * 0.01
    mejores = sorted(puntos, key=lambda w: -puntos[w])[:n]
    # Se devuelven en el orden en que se dijeron: "factura electronica" busca
    # mejor que "electronica factura".
    orden = {w: i for i, w in enumerate(tf)}
    return " ".join(sorted(mejores, key=lambda w: orden.get(w, 0)))


# ------------------------------------------------------------ api de pexels

def _get(url, key):
    req = urllib.request.Request(url, headers={"Authorization": key,
                                               "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError("Pexels rechaza la clave (HTTP %d)" % e.code)
        if e.code == 429:
            raise RuntimeError("Pexels dice que te pasaste de peticiones "
                               "(HTTP 429). Esperá un rato.")
        raise RuntimeError("Pexels devolvio HTTP %d" % e.code)
    except urllib.error.URLError as e:
        raise RuntimeError("no se pudo hablar con Pexels: %s" % e.reason)


def buscar(query, key, vertical=True, kind="video", per_page=10, locale="es-ES"):
    """Resultados crudos de Pexels para una consulta."""
    params = {"query": query, "per_page": per_page,
              "orientation": "portrait" if vertical else "landscape"}
    if locale:
        params["locale"] = locale
    ruta = "/videos/search" if kind == "video" else "/v1/search"
    url = "%s%s?%s" % (API, ruta, urllib.parse.urlencode(params))
    datos = _get(url, key)
    return datos.get("videos" if kind == "video" else "photos", []) or []


def elegir(resultados, canvas, dur_min, kind="video"):
    """El mejor candidato: bastante largo, y del tamano justo por encima.

    Un archivo enorme solo cuesta descarga: se recorta al lienzo igual. Se
    prefiere el mas chico que todavia cubra el alto del proyecto.
    """
    H = int(canvas.get("height") or 1920)
    for r in resultados:
        if kind != "video":
            return {"url": (r.get("src") or {}).get("large2x") or (r.get("src") or {}).get("original"),
                    "autor": r.get("photographer") or "", "pagina": r.get("url") or "",
                    "dur": None}
        if float(r.get("duration") or 0) + 0.01 < dur_min:
            continue
        files = [f for f in (r.get("video_files") or [])
                 if (f.get("file_type") or "").endswith("mp4") and f.get("link")]
        if not files:
            continue
        cubren = [f for f in files if int(f.get("height") or 0) >= H]
        elegido = min(cubren, key=lambda f: int(f["height"])) if cubren \
            else max(files, key=lambda f: int(f.get("height") or 0))
        return {"url": elegido["link"], "dur": float(r.get("duration") or 0),
                "autor": (r.get("user") or {}).get("name") or "",
                "pagina": r.get("url") or ""}
    return None


# ------------------------------------------------------------ descarga

def descargar(url, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 1024:
        return destino
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r, \
            open(tmp, "wb") as f:
        while True:
            trozo = r.read(1 << 16)
            if not trozo:
                break
            f.write(trozo)
    tmp.replace(destino)
    return destino


def normalizar(origen, destino, canvas, dur, empieza=0.0):
    """Recorta al encuadre del proyecto, quita el audio y deja `dur` segundos.

    Se hace aqui y no en el render para que el item sea un overlay corriente:
    del tamano del lienzo, sin sonido y ya recortado.
    """
    W, H = int(canvas["width"]), int(canvas["height"])
    fps = float(canvas.get("fps") or 30.0)
    destino.parent.mkdir(parents=True, exist_ok=True)
    vf = render.cover(W, H) + ",fps=%.4f" % fps
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-ss", "%.3f" % max(0.0, empieza), "-t", "%.3f" % dur,
           "-i", str(origen), "-an", "-vf", vf,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destino)]
    subprocess.run(cmd, check=True, capture_output=True)
    return destino


# ------------------------------------------------------------ el plan

def _slug(texto, largo=28):
    s = util.normalize(texto or "broll")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:largo] or "broll")


def plan(project, tl, cada=3, maximo=8, dur=2.6, min_dur_clip=2.0):
    """Que tramos llevarian b-roll y con que se buscaria cada uno.

    No toca la red: sirve para ver el plan antes de gastar peticiones, y es lo
    que se prueba en los tests.
    """
    segs = [s for s in project.get("segments", []) if s.get("enabled")]
    doc = _idf(segs)
    total = max(1, len(segs))
    res = studio.resolve(project, tl)
    por_seg = {c["seg"]: c for c in res["clips"]}

    salida = []
    for i, s in enumerate(segs):
        if cada > 0 and i % cada != 0:
            continue
        clip = por_seg.get(s.get("id"))
        if not clip or clip["dur"] < min_dur_clip:
            continue
        q = consulta(s.get("text", ""), doc, total)
        if not q:
            continue
        # El plano de recurso no se come el clip entero: entra un poco despues
        # de que arranque la frase y sale antes de que termine.
        d = min(dur, clip["dur"] - 0.6)
        if d < 1.0:
            continue
        salida.append({
            "seg": clip["seg"], "query": q, "dur": round(d, 3),
            "offset": round(max(0.0, (clip["dur"] - d) / 2.0), 3),
            "texto": (s.get("text") or "")[:90],
        })
        if maximo and len(salida) >= maximo:
            break
    return salida


def colocar(tl, entradas, track_id="t_ovl", fade=0.35, reemplazar=True):
    """Mete los clips ya normalizados en la pista de overlays."""
    trk = studio.track(tl, track_id)
    if trk is None:
        raise ValueError("no existe la pista %s" % track_id)
    if reemplazar:
        trk["items"] = [it for it in trk["items"] if not it.get("broll")]
    puestos = []
    for e in entradas:
        item = {
            "id": studio.new_id(tl, "b"),
            "kind": "overlay", "broll": True, "auto": True,
            "src": str(e["path"]),
            "anchor": {"seg": e["seg"], "offset": float(e["offset"])},
            "dur": float(e["dur"]),
            "x": 0.5, "y": 0.5, "scale": 1.0,
            "opacity": 1.0, "fade": fade, "loop": False,
            "stock": {"query": e["query"], "autor": e.get("autor", ""),
                      "pagina": e.get("pagina", ""), "fuente": "pexels"},
        }
        trk["items"].append(item)
        puestos.append(item)
    return puestos


def creditos(project_dir, entradas):
    """Pexels pide citar al autor. Se deja escrito y no hay que acordarse."""
    p = Path(project_dir) / "broll" / "CREDITOS.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    lineas = ["# Créditos del b-roll", "",
              "Vídeo de stock de [Pexels](https://www.pexels.com). "
              "La licencia es de uso libre y no exige atribución, pero pedirla "
              "la piden, y cuesta nada.", ""]
    for e in entradas:
        autor = e.get("autor") or "(sin autor)"
        pagina = e.get("pagina") or ""
        lineas.append("- `%s` — %s · %s · búsqueda: *%s*"
                      % (Path(e["path"]).name, autor, pagina, e["query"]))
    p.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return p
