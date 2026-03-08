Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$fletExe = Join-Path $projectRoot ".venv\Scripts\flet.exe"
if (-not (Test-Path $fletExe)) {
    throw "Flet CLI not found at $fletExe. Create/activate .venv and install dependencies first."
}

$distDir = Join-Path $projectRoot "build\desktop"
$bundleDir = Join-Path $distDir "FuelCellHMIDemo"
$zipPath = Join-Path $projectRoot "build\FuelCellHMIDemo-win.zip"

if (Test-Path $bundleDir) {
    Remove-Item $bundleDir -Recurse -Force
}
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $fletExe pack .\main.py `
    -D `
    -n FuelCellHMIDemo `
    --distpath .\build\desktop `
    --product-name "Fuel Cell HMI Demo" `
    --file-description "Fuel Cell HMI Demo App" `
    --product-version "1.0.0" `
    --file-version "1.0.0.0" `
    --company-name "NexAutomation" `
    --copyright "(c) 2026 NexAutomation" `
    -y

Compress-Archive -Path "$bundleDir\*" -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "Build complete:"
Write-Host "  Bundle: $bundleDir"
Write-Host "  Zip:    $zipPath"
