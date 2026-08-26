# -*- coding: utf-8 -*-
"""Del stream de palabras a frases, silencios fuera y tomas repetidas agrupadas."""
from __future__ import annotations

from difflib import SequenceMatcher

from . import util

DEFAULTS = {
    "pause": 0.55,       # un hueco mayor a esto corta la frase (y es silencio a quitar)
    "pad_in": 0.12,      # aire antes de la primera palabra
    "pad_out": 0.22,     # aire despues de la ultima (cierre de frase, respiracion)
    "min_dur": 0.18,     # frases mas cortas que esto no valen como corte
    "max_utt": 14.0,     # frases mas largas se parten por su hueco mayor
    "lookahead": 8,      # cuantas frases adelante se buscan repeticiones
    "window": 90.0,      # segundos de habla dentro de los que una retoma cuenta
    "sim_ratio": 0.68,   # similitud global para considerar "misma toma"
    "contain": 0.80,     # cuanto de la frase corta aparece en la larga
    "prefix": 0.60,      # prefijo comun para detectar arranques fallidos
}


# ------------------------------------------------------------ frases

def _flatten_words(transcript):
    words = []
    for seg in transcript.get("segments", []):
        for w in seg.get("words", []):
            if w["e"] <= w["s"]:
                w = dict(w, e=w["s"] + 0.06)
            words.append(w)
    words.sort(key=lambda w: (w["s"], w["e"]))
    # Corrige solapes minimos que whisper deja entre palabras.
    for a, b in zip(words, words[1:]):
        if a["e"] > b["s"]:
            a["e"] = max(a["s"] + 0.02, b["s"] - 0.005)
    return words


def _split_by_pause(words, pause):
    chunks, cur = [], []
    for w in words:
        if cur and (w["s"] - cur[-1]["e"]) > pause:
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def _split_long(chunk, max_utt):
    """Parte recursivamente por el hueco interno mayor si la frase es larguisima."""
    if not chunk or (chunk[-1]["e"] - chunk[0]["s"]) <= max_utt or len(chunk) < 4:
        return [chunk]
    best_i, best_gap = None, 0.0
    for i in range(1, len(chunk)):
        gap = chunk[i]["s"] - chunk[i - 1]["e"]
        if gap > best_gap:
            best_gap, best_i = gap, i
    if best_i is None or best_gap < 0.12:
        return [chunk]
    return _split_long(chunk[:best_i], max_utt) + _split_long(chunk[best_i:], max_utt)


def build_utterances(sources, transcripts, cfg):
    """Lista global de frases con tiempos ya padded y sin silencios."""
    out = []
    counter = 0
    for src in sources:
        tr = transcripts.get(src["id"]) or {}
        words = _flatten_words(tr)
        if not words:
            continue
        chunks = []
        for c in _split_by_pause(words, cfg["pause"]):
            chunks.extend(_split_long(c, cfg["max_utt"]))

        dur = src["duration"]
        raw = []
        for c in chunks:
            if not c:
                continue
            text = " ".join(w["w"] for w in c).strip()
            text = " ".join(text.split())
            if not util.tokens(text):
                continue
            raw.append({"words": c, "start": c[0]["s"], "end": c[-1]["e"], "text": text})

        # Padding: aire alrededor del habla, sin invadir la frase vecina.
        for i, u in enumerate(raw):
            lo = 0.0 if i == 0 else raw[i - 1]["end"]
            hi = dur if i == len(raw) - 1 else raw[i + 1]["start"]
            u["in"] = max(0.0, lo, u["start"] - cfg["pad_in"])
            u["out"] = min(dur, hi, u["end"] + cfg["pad_out"])
        # Si un corte interno quedo muy junto, se reparte el solape a medias.
        for i in range(1, len(raw)):
            if raw[i]["in"] < raw[i - 1]["out"]:
                mid = (raw[i]["in"] + raw[i - 1]["out"]) / 2.0
                raw[i - 1]["out"] = mid
                raw[i]["in"] = mid
        for u in raw:
            u["in"] = round(max(0.0, u["in"]), 3)
            u["out"] = round(min(dur, max(u["out"], u["in"] + 0.05)), 3)

        for u in raw:
            if (u["out"] - u["in"]) < cfg["min_dur"]:
                continue
            counter += 1
            probs = [w.get("p", 0) for w in u["words"] if w.get("p")]
            out.append({
                "id": "u%04d" % counter,
                "source": src["id"],
                "source_index": src["index"],
                "in": u["in"],
                "out": u["out"],
                "speech_in": round(u["start"], 3),
                "speech_out": round(u["end"], 3),
                "text": u["text"],
                "conf": round(sum(probs) / len(probs), 3) if probs else 0.0,
                "words": [{"w": w["w"], "s": w["s"], "e": w["e"]} for w in u["words"]],
                "kind": "filler" if util.is_filler_text(u["text"]) else "speech",
                "enabled": not util.is_filler_text(u["text"]),
                "group": None,
                "take_index": 0,
                "take_count": 0,
                "locked": False,
                "reason": "",
            })
    return out


# ------------------------------------------------------------ tomas repetidas

def _similarity(a, b):
    """(ratio global, contencion, prefijo/largo del corto, prefijo en tokens)."""
    if not a or not b:
        return 0.0, 0.0, 0.0, 0
    sm = SequenceMatcher(None, a, b, autojunk=False)
    ratio = sm.ratio()
    short_len = min(len(a), len(b))
    matched = sum(blk.size for blk in sm.get_matching_blocks())
    contain = matched / short_len if short_len else 0.0
    pref = 0
    for x, y in zip(a, b):
        if x != y:
            break
        pref += 1
    return ratio, contain, (pref / short_len if short_len else 0.0), pref


def _same_take(a_toks, b_toks, cfg):
    ratio, contain, pref_ratio, pref = _similarity(a_toks, b_toks)
    short_len = min(len(a_toks), len(b_toks))
    if ratio >= cfg["sim_ratio"]:
        return True, "repeticion", ratio
    if short_len >= 3 and contain >= cfg["contain"]:
        return True, "contenida", contain
    if 2 <= short_len <= 7 and pref >= 2 and pref_ratio >= cfg["prefix"]:
        return True, "arranque-fallido", pref_ratio
    return False, "", max(ratio, contain)


def _score(u):
    """Que tan 'buena' es una toma: completa, segura y sin muletillas."""
    toks = util.tokens(u["text"])
    if not toks:
        return 0.0
    n = len(toks)
    fillers = sum(1 for t in toks if t in util.FILLERS)
    length_score = min(n / 12.0, 1.0)
    clean = 1.0 - (fillers / n)
    return round(0.45 * length_score + 0.35 * u.get("conf", 0) + 0.20 * clean, 4)


def detect_takes(utterances, cfg):
    """Agrupa frases que son la misma toma repetida. Devuelve la lista de grupos."""
    toks = [util.tokens(u["text"]) for u in utterances]
    clock, acc = [], 0.0
    for u in utterances:
        clock.append(acc)
        acc += (u["out"] - u["in"])

    parent = list(range(len(utterances)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    links = {}
    for i in range(len(utterances)):
        if utterances[i]["kind"] == "filler":
            continue
        for j in range(i + 1, min(i + 1 + cfg["lookahead"], len(utterances))):
            if utterances[j]["kind"] == "filler":
                continue
            if clock[j] - clock[i] > cfg["window"]:
                break
            same, why, sc = _same_take(toks[i], toks[j], cfg)
            if same:
                union(i, j)
                links[(utterances[i]["id"], utterances[j]["id"])] = (why, round(sc, 3))

    buckets = {}
    for idx in range(len(utterances)):
        buckets.setdefault(find(idx), []).append(idx)

    groups = []
    gid = 0
    for root in sorted(buckets):
        members = sorted(buckets[root])
        if len(members) < 2:
            continue
        gid += 1
        group_id = "g%03d" % gid
        scores = {utterances[m]["id"]: _score(utterances[m]) for m in members}
        ids = [utterances[m]["id"] for m in members]
        last_id = ids[-1]
        best_id = max(ids, key=lambda i2: (scores[i2], ids.index(i2)))
        for pos, m in enumerate(members, 1):
            utterances[m]["group"] = group_id
            utterances[m]["take_index"] = pos
            utterances[m]["take_count"] = len(members)
        groups.append({
            "id": group_id,
            "kind": "repeated_take",
            "members": ids,
            "texts": [utterances[m]["text"] for m in members],
            "scores": scores,
            "last": last_id,
            "best_scored": best_id,
            "chosen": last_id,
            "decided_by": "auto:last",
            "links": [{"from": k[0], "to": k[1], "why": v[0], "score": v[1]}
                      for k, v in links.items()
                      if k[0] in ids and k[1] in ids],
        })
    return groups


def apply_groups(utterances, groups):
    """Enciende solo la toma elegida de cada grupo."""
    chosen = {g["id"]: g["chosen"] for g in groups}
    for u in utterances:
        gid = u.get("group")
        if not gid:
            continue
        if u["id"] == chosen.get(gid):
            u["enabled"] = True
            u["reason"] = "toma elegida (%d/%d)" % (u["take_index"], u["take_count"])
        else:
            u["enabled"] = False
            u["reason"] = "toma descartada (%d/%d)" % (u["take_index"], u["take_count"])
    for u in utterances:
        if not u.get("reason"):
            u["reason"] = "muletilla" if u["kind"] == "filler" else "habla"
    return utterances


def stats(sources, utterances):
    total_raw = sum(s["duration"] for s in sources)
    kept = sum(u["out"] - u["in"] for u in utterances if u["enabled"])
    return {
        "sources": len(sources),
        "raw_duration": round(total_raw, 2),
        "cut_duration": round(kept, 2),
        "removed": round(total_raw - kept, 2),
        "removed_pct": round(100.0 * (total_raw - kept) / total_raw, 1) if total_raw else 0.0,
        "segments_total": len(utterances),
        "segments_enabled": sum(1 for u in utterances if u["enabled"]),
    }
