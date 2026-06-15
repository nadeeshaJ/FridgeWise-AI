# Start FridgeWise API for emulator or physical device testing.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Starting FridgeWise API on http://0.0.0.0:8000"
Write-Host ""
Write-Host "Physical device: use Settings in the app and set your PC LAN IP, e.g.:"
Write-Host "  http://192.168.x.x:8000"
Write-Host ""
Write-Host "Find IPv4 with: ipconfig"
Write-Host ""

python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
