# Monta un video nuevo de principio a fin y abre el studio.
#
#   .\nuevo-video.ps1 "C:\ruta\a\los\videos"
#   .\nuevo-video.ps1 "C:\ruta\videos" -Nombre tiktok-3 -Plantilla limpio
#
# Hace: ordenar -> transcribir -> cortar silencios y tomas repetidas ->
# proxies -> subtitulos + zooms + transiciones -> abrir el editor.

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Videos,

    # Nombre de la carpeta del proyecto. Por defecto, el de la carpeta de videos.
    [string]$Nombre = "",

    # tiktok (con transiciones y golpes) o limpio (solo subtitulos y un empuje).
    [string]$Plantilla = "tiktok",

    # tiny | base | small | medium | large-v3. medium es el equilibrio bueno.
    [string]$Modelo = "medium",

    # Codigo ISO del idioma. Los videos de Videria son en espanol; fijarlo evita
    # que un primer clip vacio haga que Whisper detecte ingles para todo el lote.
    [string]$Idioma = "es",

    # name (por nombre de archivo) o date (por fecha de grabacion).
    [string]$Orden = "name",

    # Salta el paso de plantilla y deja el proyecto solo con los cortes.
    [switch]$SoloCortes,

    # No abrir el navegador al terminar.
    [switch]$NoAbrir
)

# OJO: no poner ErrorActionPreference = Stop. vcut escribe su progreso en
# stderr, y Windows PowerShell 5.1 convierte cualquier stderr de un ejecutable
# nativo en un error terminante. El exito se comprueba con $LASTEXITCODE.
$ErrorActionPreference = "Continue"
$VCUT = Join-Path $env:USERPROFILE ".claude\skills\video-cut\scripts\vcut.py"

function Morir($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

if (-not (Test-Path $VCUT)) { Morir "No encuentro vcut.py en $VCUT" }
if (-not (Test-Path $Videos)) { Morir "No existe la carpeta de videos: $Videos" }

if (-not $Nombre) { $Nombre = Split-Path $Videos -Leaf }
$Proyecto = Join-Path (Split-Path $Videos -Parent) "$Nombre-proyecto"

$reloj = [Diagnostics.Stopwatch]::StartNew()
function Paso($n, $texto) {
    Write-Host ""
    Write-Host ("[{0}] {1}   ({2:mm\:ss} transcurridos)" -f $n, $texto, $reloj.Elapsed) -ForegroundColor Cyan
}

Write-Host "Videos   : $Videos"
Write-Host "Proyecto : $Proyecto"
Write-Host "Plantilla: $(if ($SoloCortes) { '(ninguna)' } else { $Plantilla })"

# 1. Ordenar + transcribir + cortar + proxies. Es el paso largo: la
#    transcripcion va por CPU en esta maquina, cuenta ~1 min por minuto de
#    material con el modelo medium.
Paso 1 "Transcribiendo y cortando (lo lento; podes ir a por un cafe)"
python $VCUT run $Videos --project $Proyecto --sort $Orden --model $Modelo `
    --lang $Idioma --proxy-all --height 640
if ($LASTEXITCODE -ne 0) { Morir "fallo el paso run" }

# 2. Contrastar los cortes con el audio real y recortar el aire que sobra.
Paso 2 "Revisando los cortes contra el audio"
python $VCUT qa --project $Proyecto --write
python $VCUT decide --project $Proyecto

if (-not $SoloCortes) {
    # 3. Subtitulos, zooms, transiciones y overlays de una vez.
    Paso 3 "Aplicando la plantilla '$Plantilla'"
    python $VCUT template apply --project $Proyecto --name $Plantilla
    if ($LASTEXITCODE -ne 0) { Morir "fallo la plantilla" }
}

$reloj.Stop()
Write-Host ""
Write-Host ("Listo en {0:mm\:ss}." -f $reloj.Elapsed) -ForegroundColor Green
Write-Host "Revisa antes de editar:"
Write-Host "  $Proyecto\review.md   <- el dialogo que quedo"
Write-Host "  $Proyecto\qa.md       <- lo que dice el audio"
Write-Host ""
Write-Host "Cuando termines de editar:"
Write-Host "  python `"$VCUT`" render --project `"$Proyecto`" --draft   (borrador)"
Write-Host "  python `"$VCUT`" render --project `"$Proyecto`"           (final)"

if (-not $NoAbrir) {
    Paso 4 "Abriendo el studio"
    python $VCUT studio --project $Proyecto
}
