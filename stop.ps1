# Windows PowerShell equivalent of stop.sh
Set-Location $PSScriptRoot
if (Test-Path .dashboard.pid) {
    $procId = [int](Get-Content .dashboard.pid)
    try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host "Dashboard stopped." } catch {}
    Remove-Item .dashboard.pid
}
Get-NetTCPConnection -LocalPort 8500 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction Stop } catch {} }
Write-Host "Done."
