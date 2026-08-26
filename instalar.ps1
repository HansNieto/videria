# Copia las skills de este repo a la carpeta de skills de Claude Code.
#
#   .\instalar.ps1
#
# Si ya existe una skill con el mismo nombre no la pisa a lo bruto: la guarda
# como <nombre>.bak-<fecha> y despues copia la nueva.

$ErrorActionPreference = "Stop"

$origen  = Join-Path $PSScriptRoot "skills"
$destino = Join-Path $env:USERPROFILE ".claude\skills"

if (-not (Test-Path $origen)) {
    Write-Host "No encuentro la carpeta skills\ junto a este script." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $destino | Out-Null
Write-Host "Destino: $destino`n"

foreach ($skill in Get-ChildItem $origen -Directory) {
    $target = Join-Path $destino $skill.Name

    if (Test-Path $target) {
        $sello  = Get-Date -Format "yyyyMMdd-HHmmss"
        $backup = "$target.bak-$sello"
        Move-Item $target $backup
        Write-Host ("  {0,-18} ya estaba -> respaldo en {1}" -f $skill.Name, (Split-Path $backup -Leaf)) -ForegroundColor Yellow
    }

    Copy-Item $skill.FullName $target -Recurse
    $n = (Get-ChildItem $target -Recurse -File).Count
    Write-Host ("  {0,-18} instalada ({1} archivos)" -f $skill.Name, $n) -ForegroundColor Green
}

Write-Host "`nListo. Comprobacion rapida de lo que hace falta:`n"

function Ver($nombre, $comando, $comoInstalar) {
    if (Get-Command $comando -ErrorAction SilentlyContinue) {
        Write-Host ("  [ok]    {0}" -f $nombre) -ForegroundColor Green
    } else {
        Write-Host ("  [falta] {0}  ->  {1}" -f $nombre, $comoInstalar) -ForegroundColor Yellow
    }
}

Ver "python"  "python"  "python.org"
Ver "ffmpeg"  "ffmpeg"  "winget install Gyan.FFmpeg"
Ver "ffprobe" "ffprobe" "winget install Gyan.FFmpeg"

$faltan = @()
foreach ($m in @("flask", "numpy", "PIL", "faster_whisper")) {
    python -c "import $m" 2>$null
    if ($LASTEXITCODE -ne 0) { $faltan += $m }
}
if ($faltan.Count) {
    $pip = $faltan -replace "^PIL$", "pillow" -replace "^faster_whisper$", "faster-whisper"
    Write-Host ("  [falta] modulos de python  ->  pip install {0}" -f ($pip -join " ")) -ForegroundColor Yellow
} else {
    Write-Host "  [ok]    flask, numpy, pillow, faster-whisper" -ForegroundColor Green
}

Write-Host "`nPara arrancar:  .\nuevo-video.ps1 `"C:\ruta\a\los\videos`""
