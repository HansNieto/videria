# -*- coding: utf-8 -*-
"""Transcripcion con faster-whisper: timestamps por palabra + VAD."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from . import util

_MODEL_CACHE = {}


# Whisper es seq2seq con modelo de lenguaje: esta entrenado para producir texto
# legible, asi que repara los arranques en falso. Cebarlo con un prompt lleno de
# titubeos cambia lo que espera oir y los transcribe.
#
# Medido sobre IMG_0423.MOV (dos tomas abortadas antes de la buena):
#   prompt de vocabulario -> "es definir que debe saber de tu negocio"
#   prompt disfluente     -> "Es saber que... es definir que debe saber..."
#
# No alucina titubeos donde no los hay (comprobado en 4 tomas limpias), pero SI
# cambia el registro: en una toma limpia paso "necesitas" a "necesita". Por eso
# esta pasada NO sustituye a la normal, se guarda aparte y solo se usa para
# localizar titubeos y tomas repetidas. El texto legible sigue saliendo de la
# pasada con el prompt de vocabulario.
VERBATIM_PROMPT = (
    "Eh... o sea, es que... este... es, es decir, mmm, "
    "a ver, no, espera, es defin... es definir."
)


def _audio_fingerprint(path):
    st = Path(path).stat()
    return hashlib.sha1(
        ("%s|%d|%d" % (str(path).lower(), st.st_size, int(st.st_mtime))).encode()
    ).hexdigest()[:16]


def extract_audio(src_path, out_wav):
    """Audio mono 16 kHz PCM: lo que whisper quiere, sin remuestreos internos."""
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    util.run([
        util.FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src_path),
        "-vn", "-sn", "-dn",
        "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(out_wav),
    ])
    return out_wav


def _warmup(model):
    """Fuerza una inferencia minima.

    ctranslate2 carga cuBLAS/cuDNN recien en el primer computo, no al construir
    el modelo: sin este warm-up un equipo sin esas DLL reventaria a mitad de la
    transcripcion en vez de caer a CPU.
    """
    import numpy as np
    seg, _info = model.transcribe(np.zeros(16000, dtype=np.float32),
                                  language="en", vad_filter=False)
    list(seg)


def load_model(size="medium", device="auto", compute_type=None):
    """Carga (y cachea) el modelo. Cae a CPU si la GPU no coopera."""
    from faster_whisper import WhisperModel

    key = (size, device, compute_type)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]

    # Un solo intento por dispositivo: si CUDA no tiene sus DLL, reintentar con
    # otro compute_type no falla rapido, se queda colgado cargando kernels.
    attempts = []
    if device in ("auto", "cuda"):
        attempts.append(("cuda", compute_type or "float16"))
    if device in ("auto", "cpu"):
        attempts.append(("cpu", compute_type or "int8"))

    last_err, gpu_failed = None, False
    for dev, ct in attempts:
        try:
            util.eprint("  cargando whisper '%s' en %s (%s)..." % (size, dev, ct))
            model = WhisperModel(size, device=dev, compute_type=ct)
            _warmup(model)
            _MODEL_CACHE[key] = (model, dev, ct)
            return _MODEL_CACHE[key]
        except Exception as exc:  # noqa: BLE001 - cualquier fallo debe degradar, no matar
            last_err = exc
            msg = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
            util.eprint("    no se pudo (%s/%s): %s" % (dev, ct, msg))
            if dev == "cuda":
                gpu_failed = True
                if "cublas" in msg.lower() or "cudnn" in msg.lower():
                    util.eprint("    -> faltan las DLL de CUDA. Para usar la GPU:")
                    util.eprint("       pip install nvidia-cublas-cu12 nvidia-cudnn-cu12")

    if gpu_failed and device == "cuda":
        raise RuntimeError("La GPU no esta disponible: %s" % last_err)
    raise RuntimeError("No se pudo cargar faster-whisper: %s" % last_err)


def transcribe_source(source, work_dir, model_bundle, language=None,
                      initial_prompt=None, beam_size=5, force=False, suffix=""):
    """Transcribe un source y devuelve el dict de transcripcion (con cache).

    `suffix` permite guardar pasadas alternativas del mismo audio sin pisar la
    principal: la verbatim escribe en "<id>.verbatim.json".
    """
    work_dir = Path(work_dir)
    out_json = work_dir / "transcripts" / ("%s%s.json" % (source["id"], suffix))
    fp = _audio_fingerprint(source["path"])

    if out_json.exists() and not force:
        cached = util.read_json(out_json, {})
        if cached.get("fingerprint") == fp:
            util.eprint("  = %s ya transcrito (cache)" % source["name"])
            return cached

    if not source.get("has_audio"):
        data = {"source": source["id"], "fingerprint": fp, "language": language or "",
                "duration": source["duration"], "segments": [], "no_audio": True}
        util.write_json(out_json, data)
        return data

    model, dev, _ct = model_bundle
    wav = work_dir / "audio" / ("%s.wav" % source["id"])
    extract_audio(source["path"], wav)

    try:
        segments_iter, info = model.transcribe(
            str(wav),
            language=language,
            task="transcribe",
            beam_size=beam_size,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 400,
                "speech_pad_ms": 200,
            },
            # Evita que whisper "invente" repeticiones: queremos solo las reales.
            condition_on_previous_text=False,
            initial_prompt=initial_prompt,
        )

        segments = []
        for i, seg in enumerate(segments_iter):
            words = []
            for w in (seg.words or []):
                txt = (w.word or "").strip()
                if not txt:
                    continue
                words.append({
                    "w": txt,
                    "s": round(float(w.start), 3),
                    "e": round(float(w.end), 3),
                    "p": round(float(w.probability or 0), 3),
                })
            text = (seg.text or "").strip()
            if not text and not words:
                continue
            segments.append({
                "i": i,
                "start": round(float(seg.start), 3),
                "end": round(float(seg.end), 3),
                "text": text,
                "avg_logprob": round(float(getattr(seg, "avg_logprob", 0) or 0), 4),
                "no_speech_prob": round(float(getattr(seg, "no_speech_prob", 0) or 0), 4),
                "words": words,
            })
    finally:
        try:
            os.remove(wav)
        except OSError:
            pass

    data = {
        "source": source["id"],
        "name": source["name"],
        "fingerprint": fp,
        "language": getattr(info, "language", language) or (language or ""),
        "language_probability": round(float(getattr(info, "language_probability", 0) or 0), 3),
        "duration": source["duration"],
        "device": dev,
        "segments": segments,
    }
    util.write_json(out_json, data)
    n_words = sum(len(s["words"]) for s in segments)
    util.eprint("  + %s: %d segmentos, %d palabras" % (source["name"], len(segments), n_words))
    return data


def transcribe_all(sources, work_dir, model_size="medium", language=None,
                   device="auto", compute_type=None, initial_prompt=None,
                   beam_size=5, force=False, suffix=""):
    """Transcribe todos los sources; fija el idioma detectado en el primero."""
    pending = [s for s in sources if s.get("has_audio")]
    if not pending:
        return {}

    bundle = load_model(model_size, device=device, compute_type=compute_type)
    results = {}
    detected = language
    for s in sources:
        data = transcribe_source(s, work_dir, bundle, language=detected,
                                 initial_prompt=initial_prompt,
                                 beam_size=beam_size, force=force,
                                 suffix=suffix)
        results[s["id"]] = data
        if not detected and data.get("language"):
            detected = data["language"]
            util.eprint("  idioma detectado: %s (se fija para el resto)" % detected)
    return results
