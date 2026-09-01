# Integra en Videria recursos ya revisados.
#
#   .\completar-recursos.ps1 "C:\ruta\video21-proyecto"
#
# Requisitos previos:
# - broll\plan.json revisado por una persona o agente.
# - .env junto a este script, PEXELS_API_KEY o ~/.vcut/credenciales.json.
# - motion-overlays\frames\<escena>\0000.png para integrar animaciones.

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Proyecto,

    [switch]$SoloOverlays,
    [switch]$SoloBroll
)

$ErrorActionPreference = "Continue"
$VCUT = Join-Path $PSScriptRoot "skills\video-cut\scripts\vcut.py"
if (-not (Test-Path -LiteralPath $VCUT)) {
    $VCUT = Join-Path $env:USERPROFILE ".claude\skills\video-cut\scripts\vcut.py"
}

function Morir($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }
function Avisar($msg) { Write-Host $msg -ForegroundColor Yellow }

function CargarEnvLocal {
    # Lee asignaciones simples sin ejecutar el contenido. Esto permite guardar
    # PEXELS_API_KEY en `videria\.env`, que ya esta ignorado por Git.
    $EnvFile = Join-Path $PSScriptRoot ".env"
    if (-not (Test-Path -LiteralPath $EnvFile)) { return }
    foreach ($Linea in Get-Content -LiteralPath $EnvFile) {
        $Limpia = $Linea.Trim()
        if (-not $Limpia -or $Limpia.StartsWith("#")) { continue }
        if ($Limpia -notmatch '^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { continue }
        $Nombre = $Matches[1]
        $Valor = $Matches[2].Trim()
        if ($Valor.Length -ge 2 -and
            (($Valor.StartsWith('"') -and $Valor.EndsWith('"')) -or
             ($Valor.StartsWith("'") -and $Valor.EndsWith("'")))) {
            $Valor = $Valor.Substring(1, $Valor.Length - 2)
        }
        if (-not [string]::IsNullOrWhiteSpace($Valor)) {
            [Environment]::SetEnvironmentVariable($Nombre, $Valor, "Process")
        }
    }
}

function ConfigurarFFmpeg {
    if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { return }
    $Paquetes = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (-not (Test-Path -LiteralPath $Paquetes)) { return }
    $Ffmpeg = Get-ChildItem -LiteralPath $Paquetes -Recurse -Filter "ffmpeg.exe" -File -ErrorAction SilentlyContinue |
              Where-Object { $_.FullName -match "Gyan\.FFmpeg" } | Select-Object -First 1
    if ($Ffmpeg) {
        $Bin = Split-Path $Ffmpeg.FullName -Parent
        $env:Path = "$Bin;$env:Path"
        $env:VCUT_FFMPEG = $Ffmpeg.FullName
        $Probe = Join-Path $Bin "ffprobe.exe"
        if (Test-Path -LiteralPath $Probe) { $env:VCUT_FFPROBE = $Probe }
    }
}

CargarEnvLocal
ConfigurarFFmpeg

if (-not (Test-Path -LiteralPath $VCUT)) { Morir "No encuentro vcut.py en $VCUT" }
if (-not (Test-Path -LiteralPath $Proyecto)) { Morir "No existe el proyecto: $Proyecto" }
if ($SoloOverlays -and $SoloBroll) { Morir "Usa SoloOverlays o SoloBroll, no ambos." }

if (-not $SoloBroll) {
    $Frames = Join-Path $Proyecto "motion-overlays\frames"
    $Secuencias = @()
    if (Test-Path -LiteralPath $Frames) {
        $Secuencias = @(Get-ChildItem -LiteralPath $Frames -Directory | Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName "0000.png")
        })
    }
    if ($Secuencias.Count -gt 0) {
        Write-Host "Integrando $($Secuencias.Count) animaciones..." -ForegroundColor Cyan
        python $VCUT overlays --project $Proyecto --fps 30 --place --force
        if ($LASTEXITCODE -ne 0) { Morir "Fallo al integrar las animaciones." }
    } else {
        Avisar "Todavía no hay animaciones capturadas en motion-overlays\frames."
    }
}

if (-not $SoloOverlays) {
    $Plan = Join-Path $Proyecto "broll\plan.json"
    if (-not (Test-Path -LiteralPath $Plan)) {
        Avisar "No existe broll\plan.json. Ejecuta primero nuevo-video.ps1."
    } else {
        $GlobalCred = Join-Path $env:USERPROFILE ".vcut\credenciales.json"
        $ProjectCred = Join-Path $Proyecto "credenciales.json"
        $HayClave = -not [string]::IsNullOrWhiteSpace($env:PEXELS_API_KEY) -or
                    (Test-Path -LiteralPath $GlobalCred) -or
                    (Test-Path -LiteralPath $ProjectCred)
        if ($HayClave) {
            Write-Host "Descargando y colocando B-roll revisado..." -ForegroundColor Cyan
            python $VCUT broll --project $Proyecto --plan $Plan
            if ($LASTEXITCODE -ne 0) { Morir "Fallo al descargar o colocar el B-roll." }
        } else {
            $EnvLocal = Join-Path $PSScriptRoot ".env"
            Avisar "Falta la clave de Pexels. Configúrala una sola vez en $EnvLocal"
            Avisar 'Formato: PEXELS_API_KEY=TU_CLAVE'
        }
    }
}

Write-Host "Fase de recursos terminada. Abre el Studio para revisar posiciones." -ForegroundColor Green
