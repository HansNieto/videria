# -*- coding: utf-8 -*-
"""Exporta la linea de tiempo a formatos de NLE. Nunca recodifica nada."""
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from . import plan, util


def _rat(seconds, num, den):
    """Segundos -> tiempo racional de FCPXML, alineado a frame."""
    if seconds is None:
        return "0s"
    frames = int(round(float(seconds) * den / float(num)))
    if frames == 0:
        return "0s"
    return "%d/%ds" % (frames * num, den)


def _tc_to_sec(tc, fps):
    """'01:00:00:00' -> segundos. Devuelve 0 si el timecode no sirve."""
    try:
        parts = tc.replace(";", ":").split(":")
        if len(parts) != 4:
            return 0.0
        hh, mm, ss, ff = (int(p) for p in parts)
        return hh * 3600 + mm * 60 + ss + (ff / float(fps or 30))
    except (ValueError, AttributeError):
        return 0.0


# ------------------------------------------------------------ FCPXML

def export_fcpxml(project, out_path):
    """FCPXML 1.9: lo importan DaVinci Resolve, Final Cut y Premiere (2023+)."""
    seq = project["sequence"]
    smap = plan.source_map(project)
    items = plan.timeline(project)

    seq_num, seq_den = util.fps_fraction(seq["fps"])

    root = ET.Element("fcpxml", {"version": "1.9"})
    resources = ET.SubElement(root, "resources")

    formats, fmt_ids = {}, {}
    rid = [0]

    def next_id():
        rid[0] += 1
        return "r%d" % rid[0]

    def format_for(fps, w, h):
        key = (round(fps or seq["fps"], 3), w or seq["width"], h or seq["height"])
        if key in formats:
            return formats[key]
        num, den = util.fps_fraction(key[0])
        fid = next_id()
        ET.SubElement(resources, "format", {
            "id": fid,
            "name": "FFVideoFormat%dp%g" % (key[2], key[0]),
            "frameDuration": "%d/%ds" % (num, den),
            "width": str(key[1]),
            "height": str(key[2]),
            "colorSpace": "1-1-1 (Rec. 709)",
        })
        formats[key] = (fid, num, den)
        return formats[key]

    seq_fmt = format_for(seq["fps"], seq["width"], seq["height"])

    assets = {}
    for s in project["sources"]:
        fid, num, den = format_for(s["fps"], s["width"], s["height"])
        aid = next_id()
        attrs = {
            "id": aid,
            "name": Path(s["name"]).stem,
            "start": "0s",
            "duration": _rat(s["duration"], num, den),
            "hasVideo": "1" if s.get("has_video") else "0",
            "hasAudio": "1" if s.get("has_audio") else "0",
        }
        if s.get("has_video"):
            attrs["format"] = fid
        if s.get("has_audio"):
            attrs["audioSources"] = "1"
            attrs["audioChannels"] = "2"
        asset = ET.SubElement(resources, "asset", attrs)
        ET.SubElement(asset, "media-rep", {
            "kind": "original-media",
            "src": Path(s["path"]).as_uri(),
        })
        assets[s["id"]] = (aid, fid, num, den)
        fmt_ids[s["id"]] = fid

    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", {"name": "vcut"})
    proj = ET.SubElement(event, "project", {"name": project["name"]})

    # Los offsets salen de la suma de duraciones YA redondeadas a frame: si se
    # redondeara cada uno por su cuenta, el spine acumularia huecos de un frame.
    frames = [max(1, int(round(it["dur"] * seq_den / float(seq_num)))) for it in items]
    total_frames = sum(frames)

    sequence = ET.SubElement(proj, "sequence", {
        "format": seq_fmt[0],
        "duration": "%d/%ds" % (total_frames * seq_num, seq_den),
        "tcStart": "0s",
        "tcFormat": "NDF",
        "audioLayout": "stereo",
        "audioRate": "48k",
    })
    spine = ET.SubElement(sequence, "spine")

    offset = 0
    for it, nf in zip(items, frames):
        aid, fid, num, den = assets[it["source"]]
        clip = ET.SubElement(spine, "asset-clip", {
            "ref": aid,
            "name": smap[it["source"]]["name"],
            "offset": ("%d/%ds" % (offset * seq_num, seq_den)) if offset else "0s",
            "start": _rat(it["in"], num, den),
            "duration": "%d/%ds" % (nf * seq_num, seq_den),
            "format": fid,
            "tcFormat": "NDF",
        })
        if it["text"]:
            ET.SubElement(clip, "note").text = it["text"][:240]
        offset += nf

    xml = minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(indent="  ")
    body = xml.split("?>", 1)[1].lstrip()
    doc = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n' + body
    Path(out_path).write_text(doc, encoding="utf-8")
    return out_path


# ------------------------------------------------------------ EDL

def export_edl(project, out_path):
    """CMX3600. Una pista de video + audio, cortes duros, sin efectos."""
    fps = project["sequence"]["fps"]
    fps_i = max(int(round(fps or 30)), 1)
    smap = plan.source_map(project)
    lines = ["TITLE: %s" % project["name"][:60].upper(), "FCM: NON-DROP FRAME", ""]

    rec = 0  # frames de grabacion acumulados: origen y destino deben durar igual
    for n, it in enumerate(plan.timeline(project), 1):
        src = smap[it["source"]]
        base = _tc_to_sec(src.get("start_timecode", ""), src["fps"])
        reel = (Path(src["name"]).stem.upper()[:8] or "AX").ljust(8)
        nf = max(1, int(round(it["dur"] * fps_i)))
        src_in = int(round((base + it["in"]) * fps_i))
        lines.append("%03d  %s %s  C        %s %s %s %s" % (
            n, reel, "AA/V",
            util.sec_to_tc(src_in / fps_i, fps),
            util.sec_to_tc((src_in + nf) / fps_i, fps),
            util.sec_to_tc(rec / fps_i, fps),
            util.sec_to_tc((rec + nf) / fps_i, fps),
        ))
        rec += nf
        lines.append("* FROM CLIP NAME: %s" % src["name"])
        if it["text"]:
            lines.append("* COMMENT: %s" % it["text"][:70])
        lines.append("")

    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ------------------------------------------------------------ listas simples

def export_cutlist(project, out_path):
    items = plan.timeline(project)
    smap = plan.source_map(project)
    data = {
        "project": project["name"],
        "sequence": project["sequence"],
        "duration": round(sum(i["dur"] for i in items), 3),
        "cuts": [{
            "n": n,
            "file": smap[it["source"]]["path"],
            "in": round(it["in"], 3),
            "out": round(it["out"], 3),
            "duration": round(it["dur"], 3),
            "timeline_in": round(it["t_start"], 3),
            "text": it["text"],
        } for n, it in enumerate(items, 1)],
    }
    util.write_json(out_path, data)
    return out_path


def export_csv(project, out_path):
    items = plan.timeline(project)
    smap = plan.source_map(project)
    fps = project["sequence"]["fps"]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["n", "archivo", "in_s", "out_s", "dur_s", "in_tc", "out_tc",
                    "timeline_tc", "texto"])
        for n, it in enumerate(items, 1):
            w.writerow([n, smap[it["source"]]["name"], "%.3f" % it["in"],
                        "%.3f" % it["out"], "%.3f" % it["dur"],
                        util.sec_to_tc(it["in"], fps), util.sec_to_tc(it["out"], fps),
                        util.sec_to_tc(it["t_start"], fps), it["text"]])
    return out_path


def export_srt(project, out_path):
    """Subtitulos ya conformados a la linea de tiempo cortada."""
    def stamp(t):
        return util.sec_to_hhmmss(t, 3).replace(".", ",")

    blocks = []
    for n, it in enumerate(plan.timeline(project), 1):
        if not it["text"]:
            continue
        blocks.append("%d\n%s --> %s\n%s\n" % (n, stamp(it["t_start"]),
                                               stamp(it["t_end"]), it["text"]))
    Path(out_path).write_text("\n".join(blocks), encoding="utf-8")
    return out_path


def export_ffmpeg_script(project, out_path):
    """Script opcional de corte sin recomprimir. NO se ejecuta: queda a mano."""
    items = plan.timeline(project)
    smap = plan.source_map(project)
    out_dir = Path(out_path).parent / "flat"
    lines = [
        "# Corte plano sin recomprimir (-c copy).",
        "# Los cortes se pegan al keyframe mas cercano: sirve de preview,",
        "# el master exacto es el FCPXML / el proyecto de vcut.",
        "$ErrorActionPreference = 'Stop'",
        "New-Item -ItemType Directory -Force '%s' | Out-Null" % out_dir,
        "",
    ]
    parts = []
    for n, it in enumerate(items, 1):
        piece = out_dir / ("part_%04d.mp4" % n)
        parts.append(piece)
        lines.append("ffmpeg -hide_banner -loglevel error -y -ss %.3f -to %.3f -i \"%s\" "
                     "-c copy -avoid_negative_ts make_zero \"%s\""
                     % (it["in"], it["out"], smap[it["source"]]["path"], piece))
    concat = out_dir / "concat.txt"
    lines += [
        "",
        "@(%s) | Set-Content -Encoding utf8 '%s'"
        % (", ".join("\"file '%s'\"" % p for p in parts), concat),
        "ffmpeg -hide_banner -y -f concat -safe 0 -i \"%s\" -c copy \"%s\""
        % (concat, out_dir / "plano.mp4"),
    ]
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return out_path


EXPORTERS = {
    "fcpxml": (export_fcpxml, ".fcpxml"),
    "edl": (export_edl, ".edl"),
    "cutlist": (export_cutlist, ".cutlist.json"),
    "csv": (export_csv, ".csv"),
    "srt": (export_srt, ".srt"),
    "ffmpeg": (export_ffmpeg_script, ".ps1"),
}


def export(project, fmt, out_dir, basename=None):
    if fmt not in EXPORTERS:
        raise ValueError("Formato desconocido: %s (usa %s)"
                         % (fmt, ", ".join(sorted(EXPORTERS))))
    fn, ext = EXPORTERS[fmt]
    base = basename or project["name"]
    safe = "".join(c for c in base if c.isalnum() or c in " -_").strip() or "vcut"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return fn(project, out_dir / (safe + ext))
