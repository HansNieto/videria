#!/usr/bin/env bash
# Copia las skills de este repo a la carpeta de skills de Claude Code.
#
#   bash instalar.sh
#
# Si ya existe una skill con el mismo nombre no la pisa: la guarda como
# <nombre>.bak-<fecha> y despues copia la nueva.

set -euo pipefail

aqui="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
origen="$aqui/skills"
destino="$HOME/.claude/skills"

[ -d "$origen" ] || { echo "No encuentro la carpeta skills/ junto a este script."; exit 1; }

mkdir -p "$destino"
echo "Destino: $destino"
echo

for ruta in "$origen"/*/; do
  skill="$(basename "$ruta")"
  target="$destino/$skill"

  if [ -e "$target" ]; then
    backup="$target.bak-$(date +%Y%m%d-%H%M%S)"
    mv "$target" "$backup"
    printf '  %-18s ya estaba -> respaldo en %s\n' "$skill" "$(basename "$backup")"
  fi

  cp -r "$ruta" "$target"
  printf '  %-18s instalada (%s archivos)\n' "$skill" "$(find "$target" -type f | wc -l | tr -d ' ')"
done

echo
echo "Listo. Comprobacion rapida de lo que hace falta:"
echo

ver() {
  if command -v "$2" >/dev/null 2>&1; then
    printf '  [ok]    %s\n' "$1"
  else
    printf '  [falta] %s  ->  %s\n' "$1" "$3"
  fi
}

ver "python"  "python"  "python.org (o usa python3)"
ver "ffmpeg"  "ffmpeg"  "brew install ffmpeg / apt install ffmpeg"
ver "ffprobe" "ffprobe" "brew install ffmpeg / apt install ffmpeg"

py="$(command -v python || command -v python3 || true)"
if [ -n "$py" ]; then
  faltan=""
  for m in flask numpy PIL faster_whisper; do
    "$py" -c "import $m" >/dev/null 2>&1 || faltan="$faltan $m"
  done
  if [ -n "$faltan" ]; then
    pip="$(echo "$faltan" | sed 's/PIL/pillow/; s/faster_whisper/faster-whisper/')"
    printf '  [falta] modulos de python  ->  pip install%s\n' "$pip"
  else
    printf '  [ok]    flask, numpy, pillow, faster-whisper\n'
  fi
fi

echo
echo 'Para arrancar:  python "$HOME/.claude/skills/video-cut/scripts/vcut.py" run "/ruta/videos" --project "/ruta/proyecto"'
