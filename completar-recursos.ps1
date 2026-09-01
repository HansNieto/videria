# Integra en Videria recursos ya revisados.
#
#   .\completar-recursos.ps1 "C:\ruta\video21-proyecto"
#
# Requisitos previos:
# - broll\plan.json revisado por una persona o agente.
# - PEXELS_API_KEY o ~/.vcut/credenciales.json para descargar B-roll.
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
            Avisar "Falta la clave de Pexels. Configúrala una sola vez en $GlobalCred"
            Avisar 'Formato: {"pexels_api_key":"TU_CLAVE"}'
        }
    }
}

Write-Host "Fase de recursos terminada. Abre el Studio para revisar posiciones." -ForegroundColor Green
