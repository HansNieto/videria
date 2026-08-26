"""
Aplica el estilo de subtítulo apilado y renderiza el vídeo.

Uso:
    python aplicar_estilo.py --tema "El calentamiento global"
    python aplicar_estilo.py --guion guion.txt --terminos "glacier,drought"
    python aplicar_estilo.py --solo-config          (ajusta config.toml y sale)

Los valores del estilo salen de medir los fotogramas de referencia, no de
estimarlos: ver ESTILO más abajo y los comentarios de cada campo.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

RAIZ = Path.home() / "MoneyPrinterTurbo"
SALIDA_POR_DEFECTO = Path(__file__).resolve().parents[3]

# Estilo medido sobre los fotogramas de referencia (CapCut, vídeo 9:16).
ESTILO = {
    "subtitle_karaoke_enabled": True,
    # Fuente de la palabra clave. Dancing Script sustituye a "Danza de Hielo"
    # (Frost Dance), que es de pago. Para cambiarla basta poner el .ttf en
    # resource/fonts y editar este valor.
    "subtitle_keyword_font": "DancingScript-Bold.ttf",
    # Azul muestreado de los fotogramas de referencia.
    "subtitle_keyword_color": "#4A90E0",
    # Dancing Script tiene la altura de x en 32px donde Inter Black la tiene en
    # 45px al mismo cuerpo. 1.41 las iguala; 1.5 deja la clave algo mayor, como
    # en la referencia.
    "subtitle_keyword_size_ratio": 1.5,
    # Desplazamiento del borde superior de la primera línea respecto al CENTRO
    # del vídeo. Positivo baja. +300 es donde cae el texto en la referencia.
    "subtitle_vertical_offset": 300,
    # Filas de texto en pantalla, no grupos: un grupo largo ocupa dos filas.
    "subtitle_lines_per_card": 3,
    # El apilado es un recurso de énfasis: sólo se acumulan líneas alrededor de
    # una palabra resaltada. Sin clave, cada grupo aparece solo, que se lee más
    # rápido y deja el plano limpio.
    "subtitle_stack_only_with_keyword": True,
    "subtitle_word_reveal": True,
    "subtitle_shadow_opacity": 190,
    "subtitle_shadow_blur": 9.0,
    # A cuerpo 80 en 1080px de ancho caben ~22 caracteres. Con 18 y el margen
    # interno de +6 el tope real es 24, así que casi nunca hay que partir filas.
    "subtitle_karaoke_target_words": 3,
    "subtitle_karaoke_max_words": 4,
    "subtitle_karaoke_max_chars": 18,
    "subtitle_highlight_amount": 6,
}

# Modelos verificados con la key de Gemini del proyecto. "gemini-flash-latest"
# es el alias que más se satura: da 503 con frecuencia. Los pinneados aguantan.
MODELO_LLM = "gemini-3.6-flash"
MODELOS_ALTERNATIVOS = ("gemini-3.5-flash", "gemini-3.1-flash-lite")


_APLICAR = """
import json, sys
from app.config import config
valores = json.loads(sys.argv[1])
for clave, valor in valores.items():
    config.app[clave] = valor
config.save_config()
print("estilo aplicado en", config.config_file)
"""


def aplicar_config() -> int:
    """
    Escribe el estilo en config.toml a través del entorno de MoneyPrinterTurbo.

    No se puede importar ``app.config`` desde aquí: sus dependencias (loguru,
    toml, pydantic) viven en el venv que gestiona uv, no en el Python del
    sistema. Por eso la escritura se delega a un subproceso ``uv run``, y así
    este helper sólo necesita la librería estándar.
    """
    import json

    valores = dict(ESTILO)
    valores["llm_provider"] = "gemini"
    valores["gemini_model_name"] = MODELO_LLM
    resultado = subprocess.run(
        ["uv", "run", "--no-sync", "python", "-c", _APLICAR, json.dumps(valores)],
        cwd=RAIZ,
        env=dict(os.environ, PYTHONUTF8="1"),
    )
    return resultado.returncode


def renderizar(args: argparse.Namespace) -> int:
    tarea = str(uuid.uuid4())
    comando = [
        "uv", "run", "--no-sync", "python", "cli.py",
        "--task-id", tarea,
        "--video-language", "es",
        "--voice-name", args.voz,
        "--font-name", "Inter-Black.ttf",
        "--font-size", str(args.cuerpo),
        "--stop-at", "video",
    ]
    if args.guion:
        comando += ["--video-script", Path(args.guion).read_text(encoding="utf-8")]
        comando += ["--video-subject", args.tema or "video"]
    else:
        comando += ["--video-subject", args.tema]
        comando += ["--paragraph-number", str(args.parrafos)]
    if args.terminos:
        comando += ["--video-terms", args.terminos]
    if args.prompt:
        comando += ["--video-script-prompt", args.prompt]

    entorno = dict(os.environ, PYTHONUTF8="1")
    print(f"renderizando, task_id={tarea}")
    resultado = subprocess.run(comando, cwd=RAIZ, env=entorno)
    if resultado.returncode != 0:
        print(
            "FALLO. Si el log dice 503 UNAVAILABLE es saturación temporal de "
            f"Gemini, no un problema de la key: reintenta o usa uno de "
            f"{', '.join(MODELOS_ALTERNATIVOS)}.",
            file=sys.stderr,
        )
        return resultado.returncode

    origen = RAIZ / "storage" / "tasks" / tarea / "final-1.mp4"
    if not origen.is_file():
        print("el render terminó sin producir final-1.mp4", file=sys.stderr)
        return 1

    destino = Path(args.salida) / f"{args.nombre or tarea[:8]}.mp4"
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origen, destino)
    print(f"VIDEO={destino}")
    print(f"SRT={origen.parent / 'subtitle.srt'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tema", help="tema del vídeo (lo escribe el LLM)")
    parser.add_argument("--guion", help="ruta a un .txt con el guion ya escrito")
    parser.add_argument("--terminos", help="keywords de Pexels separadas por coma")
    parser.add_argument("--prompt", help="instrucción extra para el guion")
    parser.add_argument("--voz", default="es-MX-DaliaNeural-Female")
    parser.add_argument("--parrafos", type=int, default=2)
    parser.add_argument("--cuerpo", type=int, default=80)
    parser.add_argument("--salida", default=str(SALIDA_POR_DEFECTO))
    parser.add_argument("--nombre", help="nombre del archivo de salida, sin .mp4")
    parser.add_argument("--solo-config", action="store_true")
    args = parser.parse_args()

    if not (RAIZ / "cli.py").is_file():
        print(f"no encuentro MoneyPrinterTurbo en {RAIZ}", file=sys.stderr)
        return 1

    if aplicar_config() != 0:
        print("no pude escribir el estilo en config.toml", file=sys.stderr)
        return 1
    if args.solo_config:
        return 0
    if not args.tema and not args.guion:
        print("hace falta --tema o --guion", file=sys.stderr)
        return 1
    return renderizar(args)


if __name__ == "__main__":
    raise SystemExit(main())
