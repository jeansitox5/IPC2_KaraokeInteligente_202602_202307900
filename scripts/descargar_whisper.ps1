# descargar_whisper.ps1
# Descarga whisper.cpp (whisper-cli.exe + DLLs) y el modelo multilingüe ggml-base-q5_1.bin
# en src\karaoke\resources\whisper, para que Briefcase los incluya en el instalador .msi.
#
# Uso (desde la raíz del proyecto):
#     powershell -ExecutionPolicy Bypass -File scripts\descargar_whisper.ps1

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # acelera Invoke-WebRequest

$raiz    = Split-Path -Parent $PSScriptRoot
$destino = Join-Path $raiz "src\karaoke\resources\whisper"
$temp    = Join-Path $env:TEMP "karaoke_whisper"
New-Item -ItemType Directory -Force $destino, $temp | Out-Null

# ---------------------------------------------------------------- whisper.cpp
$zip = Join-Path $temp "whisper-bin-x64.zip"
$urls = @(
    "https://github.com/ggml-org/whisper.cpp/releases/latest/download/whisper-bin-x64.zip",
    "https://github.com/ggml-org/whisper.cpp/releases/download/v1.8.2/whisper-bin-x64.zip"
)
$descargado = $false
foreach ($url in $urls) {
    try {
        Write-Host "Descargando whisper.cpp: $url"
        Invoke-WebRequest -Uri $url -OutFile $zip
        $descargado = $true
        break
    } catch {
        Write-Host "  No se pudo, probando otra dirección..."
    }
}
if (-not $descargado) { throw "No se pudo descargar whisper-bin-x64.zip" }

$extraido = Join-Path $temp "extraido"
if (Test-Path $extraido) { Remove-Item -Recurse -Force $extraido }
Expand-Archive -Path $zip -DestinationPath $extraido

$cli = Get-ChildItem -Path $extraido -Recurse -Filter "whisper-cli.exe" | Select-Object -First 1
if (-not $cli) { throw "El zip no contiene whisper-cli.exe" }
Copy-Item $cli.FullName $destino -Force
Get-ChildItem -Path $cli.DirectoryName -Filter "*.dll" | Copy-Item -Destination $destino -Force
Write-Host "whisper-cli.exe y DLLs copiados."

# Runtime de Visual C++ (por si la PC del usuario no lo tiene instalado)
foreach ($dll in "msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll") {
    $origen = Join-Path $env:WINDIR "System32\$dll"
    if (Test-Path $origen) { Copy-Item $origen $destino -Force }
}

# ---------------------------------------------------------------- modelo
$modelo = Join-Path $destino "ggml-base-q5_1.bin"
if (-not (Test-Path $modelo)) {
    Write-Host "Descargando modelo ggml-base-q5_1.bin (~60 MB)..."
    Invoke-WebRequest -Uri "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q5_1.bin" -OutFile $modelo
}

# ---------------------------------------------------------------- verificación
Write-Host ""
Write-Host "Contenido de $destino :"
Get-ChildItem $destino | Format-Table Name, Length
& (Join-Path $destino "whisper-cli.exe") -h *> $null
if ($LASTEXITCODE -eq 0) { Write-Host "OK: whisper-cli.exe funciona." -ForegroundColor Green }
else { Write-Host "ATENCION: whisper-cli.exe devolvió código $LASTEXITCODE" -ForegroundColor Yellow }
