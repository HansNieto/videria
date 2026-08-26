# -*- coding: utf-8 -*-
"""Genera los 8 SFX que usan las transiciones, con ffmpeg y nada mas.

Se sintetizan aqui a proposito: asi el paquete no arrastra audio descargado de
ninguna libreria y se puede redistribuir sin preguntarle la licencia a nadie.
Los nombres son los que espera `render.TRANSITIONS`; cambiarlos deja las
transiciones mudas.

    python generar-sfx.py            # escribe los .wav que falten
    python generar-sfx.py --force    # los rehace todos

Si preferis los tuyos, no toques esto: dejalos en una carpeta `transiciones/`,
`sfx/` o `audio_reales/` dentro del proyecto. La libreria busca primero ahi y
solo cae a estos cuando no encuentra uno con ese nombre.

El barrido de frecuencia se hace cruzando tres bandas de ruido con envolventes
desplazadas en el tiempo, porque los filtros de ffmpeg no aceptan una frecuencia
que varie con `t`. El oido lo lee igual como un barrido.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SR = 48000


def bandas(dur, bandas_spec, color="pink", amp=0.9):
    """Ruido repartido en bandas, cada una con su propia envolvente.

    `bandas_spec` es una lista de (frecuencia, ancho, expresion_de_volumen).
    La expresion usa `t` en segundos y se evalua por fotograma de audio.
    """
    partes = ["anoisesrc=d=%.3f:c=%s:a=%.3f:r=%d[n]" % (dur, color, amp, SR)]
    etiquetas = []
    partes.append("[n]asplit=%d%s" % (len(bandas_spec),
                                      "".join("[b%d]" % i for i in range(len(bandas_spec)))))
    for i, (f, w, env) in enumerate(bandas_spec):
        partes.append("[b%d]bandpass=f=%d:w=%d:t=h,volume=volume='%s':eval=frame[v%d]"
                      % (i, f, w, env, i))
        etiquetas.append("[v%d]" % i)
    partes.append("%samix=inputs=%d:normalize=0[mix]" % ("".join(etiquetas), len(etiquetas)))
    return partes, "[mix]"


# Cada entrada: (archivo, duracion, cadena de filtros, etiqueta de salida).
# `sine`, `anoisesrc` y `aevalsrc` son fuentes; el resto es envolvente y color.
def recetas():
    r = {}

    # 1. Whoosh — barrido de aire de grave a agudo y de vuelta.
    partes, out = bandas(0.45, [
        (400,  600,  "max(0,1-abs((t-0.10)/0.12))"),
        (1600, 1800, "max(0,1-abs((t-0.22)/0.13))"),
        (5000, 4000, "max(0,1-abs((t-0.33)/0.14))"),
    ])
    r["1_whoosh.wav"] = (0.45, partes, out)

    # 2. Swish — el mismo gesto, mas corto y mas brillante. Para el whip pan.
    partes, out = bandas(0.30, [
        (900,  900,  "max(0,1-abs((t-0.08)/0.09))"),
        (3500, 3000, "max(0,1-abs((t-0.16)/0.10))"),
        (8000, 6000, "max(0,1-abs((t-0.23)/0.10))"),
    ])
    r["2_swish.wav"] = (0.30, partes, out)

    # 3. Impacto — golpe seco: click de ataque sobre un cuerpo grave que cae.
    r["3_impacto.wav"] = (0.38, [
        "sine=f=58:d=0.38:r=%d,volume=volume='exp(-14*t)':eval=frame[low]" % SR,
        "anoisesrc=d=0.38:c=white:a=0.8:r=%d,"
        "lowpass=f=2500,volume=volume='exp(-70*t)':eval=frame[click]" % SR,
        "[low][click]amix=inputs=2:normalize=0,volume=2.0[mix]",
    ], "[mix]")

    # 4. Riser — tension que sube. Es el unico largo; el desenfoque lo pide.
    r["4_riser.wav"] = (0.80, [
        "aevalsrc='sin(2*PI*(180+900*(t/0.8)^2)*t)':d=0.80:s=%d[sweep]" % SR,
        "anoisesrc=d=0.80:c=pink:a=0.5:r=%d,highpass=f=1200[air]" % SR,
        "[sweep][air]amix=inputs=2:normalize=0,"
        "volume=volume='pow(t/0.8,1.8)':eval=frame[mix]",
    ], "[mix]")

    # 5. Clic — el mas discreto, para el flash. Casi solo transitorio.
    r["5_clic.wav"] = (0.07, [
        "anoisesrc=d=0.07:c=white:a=0.9:r=%d,"
        "highpass=f=1800,volume=volume='exp(-90*t)':eval=frame[mix]" % SR,
    ], "[mix]")

    # 6. Glitch — tres rafagas cortadas a cuchillo, con aire digital.
    r["6_glitch.wav"] = (0.26, [
        "anoisesrc=d=0.26:c=white:a=0.85:r=%d," % SR +
        "bandpass=f=3000:w=4000:t=h,"
        "volume=volume='"
        "if(lt(t,0.03),1,if(lt(t,0.07),0,if(lt(t,0.11),0.9,"
        "if(lt(t,0.15),0,if(lt(t,0.19),0.7,0)))))':eval=frame[mix]",
    ], "[mix]")

    # 7. Boom — el mas grave de todos. No lo usa ninguna transicion por
    #    defecto, pero esta para arrastrarlo a mano desde la libreria.
    r["7_boom.wav"] = (0.70, [
        "sine=f=42:d=0.70:r=%d,volume=volume='exp(-6*t)':eval=frame[low]" % SR,
        "sine=f=84:d=0.70:r=%d,volume=volume='0.4*exp(-11*t)':eval=frame[harm]" % SR,
        "[low][harm]amix=inputs=2:normalize=0,volume=2.2[mix]",
    ], "[mix]")

    # 8. Succion — el barrido al reves: entra agudo y se hunde. Para el pixelado.
    partes, out = bandas(0.40, [
        (6000, 5000, "max(0,1-abs((t-0.07)/0.10))"),
        (2000, 2000, "max(0,1-abs((t-0.19)/0.12))"),
        (450,  700,  "max(0,1-abs((t-0.31)/0.13))"),
    ])
    r["8_succion.wav"] = (0.40, partes, out)

    return r


PICO_OBJETIVO = -1.5     # dBFS. Los ocho tienen que pegar parejo.


def _pico(ruta):
    """Pico en dBFS que mide ffmpeg. Devuelve None si no lo encuentra."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(ruta),
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    for linea in (r.stderr or "").splitlines():
        if "max_volume:" in linea:
            try:
                return float(linea.split("max_volume:")[1].split("dB")[0])
            except ValueError:
                return None
    return None


def construir(nombre, dur, partes, out, destino):
    # Cola comun: estereo y un pelo de fundido en los dos extremos para que no
    # chasquee al entrar ni al salir.
    cola = ("%safade=t=in:st=0:d=0.004,afade=t=out:st=%.3f:d=0.02,"
            "aformat=sample_fmts=s16:channel_layouts=stereo:sample_rates=%d[out]"
            % (out, max(0.0, dur - 0.02), SR))
    graph = ";".join(partes + [cola])
    crudo = destino / ("~%s" % nombre)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-filter_complex", graph,
                    "-map", "[out]", "-t", "%.3f" % dur, str(crudo)], check=True)

    # Segunda pasada: cada receta sale a un nivel distinto (el ruido filtrado
    # queda muy por debajo de un seno), asi que se mide y se sube al mismo pico.
    pico = _pico(crudo)
    ganancia = 0.0 if pico is None else (PICO_OBJETIVO - pico)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(crudo),
                    "-af", "volume=%.2fdB,alimiter=limit=0.94" % ganancia,
                    str(destino / nombre)], check=True)
    crudo.unlink(missing_ok=True)
    return ganancia


def main():
    ap = argparse.ArgumentParser(description="Sintetiza los SFX de las transiciones.")
    ap.add_argument("--force", action="store_true", help="rehacer los que ya existen")
    ap.add_argument("--out", default=str(AQUI), help="carpeta de salida")
    args = ap.parse_args()

    destino = Path(args.out)
    destino.mkdir(parents=True, exist_ok=True)

    hechos = 0
    for nombre, (dur, partes, out) in sorted(recetas().items()):
        if (destino / nombre).exists() and not args.force:
            print("  ya estaba   %s" % nombre)
            continue
        g = construir(nombre, dur, partes, out, destino)
        print("  generado    %s  (%.2f s, %+.1f dB)" % (nombre, dur, g))
        hechos += 1

    print("\n%d archivos nuevos en %s" % (hechos, destino))
    return 0


if __name__ == "__main__":
    sys.exit(main())
