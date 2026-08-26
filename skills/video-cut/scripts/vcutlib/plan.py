# -*- coding: utf-8 -*-
"""Ensambla el proyecto, genera el informe de revision y aplica decisiones."""
from __future__ import annotations

from datetime import datetime, timezone

from . import analyze, util

SCHEMA_VERSION = 1


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_project(name, sources, utterances, groups, cfg, inputs, seq_fps, seq_size):
    project = {
        "vcut_version": SCHEMA_VERSION,
        "name": name,
        "created_at": _now(),
        "updated_at": _now(),
        "input": inputs,
        "config": dict(cfg),
        "sequence": {"fps": seq_fps, "width": seq_size[0], "height": seq_size[1]},
        "sources": sources,
        "segments": utterances,
        "groups": groups,
        "stats": {},
    }
    return rebuild(project)


def rebuild(project):
    """Recalcula posiciones en la linea de tiempo y estadisticas."""
    t = 0.0
    for seg in project["segments"]:
        seg["dur"] = round(max(0.0, seg["out"] - seg["in"]), 3)
        if seg.get("enabled"):
            seg["t"] = round(t, 3)
            t += seg["dur"]
        else:
            seg["t"] = None
    project["stats"] = analyze.stats(project["sources"], project["segments"])
    project["stats"]["timeline_duration"] = round(t, 2)
    project["updated_at"] = _now()
    return project


def timeline(project):
    """Lista ordenada de cortes activos: lo que veria un NLE."""
    out, t = [], 0.0
    for seg in project["segments"]:
        if not seg.get("enabled"):
            continue
        dur = max(0.0, seg["out"] - seg["in"])
        if dur <= 0:
            continue
        out.append({
            "id": seg["id"], "source": seg["source"],
            "in": seg["in"], "out": seg["out"], "dur": dur,
            "t_start": t, "t_end": t + dur, "text": seg.get("text", ""),
        })
        t += dur
    return out


def source_map(project):
    return {s["id"]: s for s in project["sources"]}


# ------------------------------------------------------------ informe

def to_review_markdown(project):
    """Documento compacto para que el modelo juzgue coherencia y tomas."""
    smap = source_map(project)
    st = project["stats"]
    lines = []
    a = lines.append

    a("# Revision de cortes: %s" % project["name"])
    a("")
    a("- Material bruto: **%s** en %d archivo(s)"
      % (util.sec_to_hhmmss(st["raw_duration"], 0), st["sources"]))
    a("- Propuesta automatica: **%s** (%.1f%% eliminado)"
      % (util.sec_to_hhmmss(st.get("timeline_duration", st["cut_duration"]), 0),
         st["removed_pct"]))
    a("- Frases: %d totales, %d encendidas, %d grupos de tomas repetidas"
      % (st["segments_total"], st["segments_enabled"], len(project["groups"])))
    a("")
    if project.get("notes"):
        a("## Notas de la revision anterior")
        a("")
        a(str(project["notes"]).strip())
        a("")

    a("## Tu tarea")
    a("")
    a("1. Lee el **dialogo propuesto**: debe leerse como un discurso continuo y")
    a("   con sentido. Si hay saltos, frases cortadas o ideas duplicadas, se")
    a("   eligio mal alguna toma.")
    a("2. Revisa cada **grupo de tomas**. La regla por defecto es quedarse con la")
    a("   ultima, pero manda la coherencia: si la ultima esta incompleta o la")
    a("   anterior encaja mejor con lo que sigue, elige esa.")
    a("3. Marca para apagar lo que sobre (muletillas sueltas, frases que se")
    a("   repiten sin ser el mismo grupo, comentarios fuera de guion).")
    a("4. Escribe `decisions.json` con tu veredicto y aplicalo con `vcut decide`.")
    a("")

    a("## Dialogo propuesto (lo que quedaria encendido)")
    a("")
    cur_src = None
    for seg in project["segments"]:
        if not seg.get("enabled"):
            continue
        if seg["source"] != cur_src:
            cur_src = seg["source"]
            a("")
            a("*-- %s --*" % smap[cur_src]["name"])
            a("")
        tag = ""
        if seg.get("group"):
            tag = " `[%s toma %d/%d]`" % (seg["group"], seg["take_index"], seg["take_count"])
        a("- `%s` %s%s" % (seg["id"], seg["text"], tag))
    a("")

    if project["groups"]:
        a("## Grupos de tomas repetidas")
        a("")
        for g in project["groups"]:
            a("### %s -- %d tomas (elegida ahora: `%s`, por %s)"
              % (g["id"], len(g["members"]), g["chosen"], g.get("decided_by", "auto")))
            a("")
            a("| toma | id | archivo @ tiempo | conf | score | texto |")
            a("|---|---|---|---|---|---|")
            for k, mid in enumerate(g["members"], 1):
                seg = next(s for s in project["segments"] if s["id"] == mid)
                mark = " **<-**" if mid == g["chosen"] else ""
                a("| %d | `%s`%s | %s @ %s | %.2f | %.2f | %s |"
                  % (k, mid, mark, smap[seg["source"]]["name"],
                     util.sec_to_hhmmss(seg["in"]), seg.get("conf", 0),
                     g["scores"].get(mid, 0), seg["text"].replace("|", "/")))
            a("")

    off = [s for s in project["segments"] if not s.get("enabled") and not s.get("group")]
    if off:
        a("## Apagadas por muletilla / ruido")
        a("")
        for seg in off:
            a("- `%s` (%s) %s" % (seg["id"], seg.get("reason", ""), seg["text"]))
        a("")

    a("## Formato de decisions.json")
    a("")
    a("```json")
    a('{')
    a('  "groups":  { "g001": "u0007" },')
    a('  "disable": ["u0031", "u0044"],')
    a('  "enable":  ["u0012"],')
    a('  "trim":    { "u0005": {"in": 12.40, "out": 15.90} },')
    a('  "order":   ["u0001", "u0003", "u0002"],')
    a('  "notes":   "por que se decidio asi"')
    a('}')
    a("```")
    a("")
    a("Todo es opcional. `groups` elige la toma buena; `disable`/`enable` fuerzan")
    a("frases sueltas; `trim` ajusta tiempos en segundos del archivo original;")
    a("`order` reordena la secuencia (solo hace falta si cambia el orden).")
    return "\n".join(lines)


# ------------------------------------------------------------ decisiones

def apply_decisions(project, decisions):
    """Aplica el veredicto del modelo (o del humano) sobre el proyecto."""
    segs = {s["id"]: s for s in project["segments"]}
    groups = {g["id"]: g for g in project["groups"]}
    report = {"groups": 0, "disabled": 0, "enabled": 0, "trimmed": 0,
              "reordered": False, "warnings": []}

    for gid, choice in (decisions.get("groups") or {}).items():
        g = groups.get(gid)
        if not g:
            report["warnings"].append("grupo desconocido: %s" % gid)
            continue
        if choice not in g["members"]:
            report["warnings"].append("%s no pertenece a %s" % (choice, gid))
            continue
        g["chosen"] = choice
        g["decided_by"] = "modelo"
        report["groups"] += 1

    analyze.apply_groups(project["segments"], project["groups"])

    for sid in (decisions.get("disable") or []):
        if sid in segs:
            segs[sid]["enabled"] = False
            segs[sid]["locked"] = True
            segs[sid]["reason"] = "apagada por revision"
            report["disabled"] += 1
        else:
            report["warnings"].append("segmento desconocido: %s" % sid)

    for sid in (decisions.get("enable") or []):
        if sid in segs:
            segs[sid]["enabled"] = True
            segs[sid]["locked"] = True
            segs[sid]["reason"] = "encendida por revision"
            report["enabled"] += 1
        else:
            report["warnings"].append("segmento desconocido: %s" % sid)

    smap = source_map(project)
    for sid, tr in (decisions.get("trim") or {}).items():
        seg = segs.get(sid)
        if not seg:
            report["warnings"].append("segmento desconocido en trim: %s" % sid)
            continue
        dur = smap[seg["source"]]["duration"]
        new_in = float(tr.get("in", seg["in"]))
        new_out = float(tr.get("out", seg["out"]))
        seg["in"] = round(max(0.0, min(new_in, dur - 0.05)), 3)
        seg["out"] = round(max(seg["in"] + 0.05, min(new_out, dur)), 3)
        report["trimmed"] += 1

    order = decisions.get("order")
    if order:
        known = [sid for sid in order if sid in segs]
        rest = [s["id"] for s in project["segments"] if s["id"] not in set(known)]
        project["segments"] = [segs[sid] for sid in known] + [segs[sid] for sid in rest]
        report["reordered"] = True

    if decisions.get("notes"):
        project["notes"] = decisions["notes"]

    rebuild(project)
    return report
