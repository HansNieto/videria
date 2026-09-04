param([switch]$NoLaunch)
$ErrorActionPreference = 'Stop'
$version = '2.4.1'
$source = Join-Path $PSScriptRoot 'Videria'
if (-not (Test-Path -LiteralPath (Join-Path $source 'Videria.exe'))) {
    throw 'Primero extrae TODO el ZIP y luego ejecuta Instalar-Videria.cmd.'
}
$installBase = Join-Path $env:LOCALAPPDATA 'Programs\Videria'
$destination = [IO.Path]::GetFullPath((Join-Path $installBase "app-$version"))
if (-not $destination.StartsWith([IO.Path]::GetFullPath($installBase) + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Destino no valido' }
$running = Get-Process Videria -ErrorAction SilentlyContinue
if ($running) { throw 'Cierra Videria antes de instalar o actualizar. No se modificaron tus proyectos.' }
# Las versiones anteriores se conservan para poder volver atras. No se tocan proyectos.
New-Item -ItemType Directory -Path $destination -Force | Out-Null
Get-ChildItem -LiteralPath $source | Copy-Item -Destination $destination -Recurse -Force
$exe = Join-Path $destination 'Videria.exe'
$shellLink = New-Object -ComObject WScript.Shell
$desktopDir = [Environment]::GetFolderPath('Desktop')
$programsDir = [Environment]::GetFolderPath('Programs')
foreach ($folder in @($desktopDir, $programsDir)) {
    $link = $shellLink.CreateShortcut((Join-Path $folder 'Videria.lnk'))
    $link.TargetPath = $exe
    $link.WorkingDirectory = $destination
    $link.IconLocation = "$exe,0"
    $link.Description = 'Videria - editor de video y proyectos'
    $link.Save()
}
Write-Host "Videria $version instalada. Abre el icono Videria del Escritorio."
Write-Host 'Tus proyectos y originales no se movieron ni se reemplazaron.'
if (-not $NoLaunch) { Start-Process -FilePath $exe -WindowStyle Hidden }
