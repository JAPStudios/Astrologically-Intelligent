#Requires -Version 5.1
<#
  Build a portable Windows distribution for Astrologically Intelligent.

  Output layout:
    dist\AstrologicallyIntelligent\AstrologicallyIntelligent.exe
    dist\AstrologicallyIntelligent\static\...
    dist\AstrologicallyIntelligent\scripts\...
    dist\AstrologicallyIntelligent\mcp_servers\...
    dist\AstrologicallyIntelligent\services\hwfit\data\...

  The app then keeps using its normal filesystem layout when frozen.

  Usage:
    powershell -ExecutionPolicy Bypass -File .\build-windows-portable.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Write-Step($msg) { Write-Host ""; Write-Host ("==> " + $msg) -ForegroundColor Cyan }
function Fail($msg) {
    Write-Host ""
    Write-Host ("ERROR: " + $msg) -ForegroundColor Red
    exit 1
}

Write-Step "Checking for Python"
$pyExe = $null
if (Test-Path ".\.venv\Scripts\python.exe") {
    $pyExe = (Resolve-Path ".\.venv\Scripts\python.exe").Path
} else {
    foreach ($c in @("py", "python")) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if ($cmd) { $pyExe = $cmd.Source; break }
    }
    if ($pyExe -like "*WindowsApps*python.exe") {
        $pyCmd = Get-Command py -ErrorAction SilentlyContinue
        if ($pyCmd) {
            $pyExe = $pyCmd.Source
        }
    }
}
if (-not $pyExe) {
    Fail "Python not found on PATH. Install Python 3.11+ first."
}
Write-Host ("Using Python: " + $pyExe)

Write-Step "Installing build dependencies"
& $pyExe -m pip install --quiet --require-hashes --only-binary=:all: --no-deps -r requirements-bootstrap.txt
if ($LASTEXITCODE -ne 0) { Fail "TLS build dependency bootstrap failed." }
& $pyExe -m pip install -r requirements.txt pyinstaller pystray Pillow
if ($LASTEXITCODE -ne 0) { Fail "Dependency install failed." }

Write-Step "Building portable exe bundle"
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue


& $pyExe -m PyInstaller --noconfirm --clean .\Odysseus.spec
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller build failed." }

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host "Portable app folder: $PSScriptRoot\dist\AstrologicallyIntelligent" -ForegroundColor Green
Write-Host "Distribute the whole folder (or zip it) so static assets and scripts stay with the exe." -ForegroundColor Green